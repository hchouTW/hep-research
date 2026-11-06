// NewSource.hh: the analytic source of a new specification (g4sim plan, Section 6.3). Reads the record of core/simulation/source_density.py with
// frames already resolved to world coordinates, so what is sampled is what source-density/1 states. G4SIM_SOURCE_CONTROL=wide_energy is the
// negative test of Section 15.1: the sampled energy is 10% above the record's.
#ifndef G4SIM_NEWSOURCE_HH
#define G4SIM_NEWSOURCE_HH

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

#include "G4Event.hh"
#include "G4IonTable.hh"
#include "G4ParticleGun.hh"
#include "G4ParticleTable.hh"
#include "G4PhysicalConstants.hh"
#include "G4SystemOfUnits.hh"
#include "G4ThreeVector.hh"
#include "G4VUserPrimaryGeneratorAction.hh"
#include "MiniJson.hh"
#include "NewBuild.hh"
#include "Randomize.hh"
#include "SimSeed.hh"

namespace g4sim {

inline G4ThreeVector Vector(const Value& rows) {
  const auto& v = rows.array("vector");
  return {Decimal(v[0]), Decimal(v[1]), Decimal(v[2])};
}

class NewSource : public G4VUserPrimaryGeneratorAction {
 public:
  NewSource(const Value& source, long long seed, long long firstEvent, std::FILE* primaries)
      : fSource(source), fSeed(seed), fFirst(firstEvent), fPrimaries(primaries), fGun(1) {
    const char* control = std::getenv("G4SIM_SOURCE_CONTROL");
    fScale = control && std::string(control) == "wide_energy" ? 1.1 : 1.;
  }

  void GeneratePrimaries(G4Event* event) override {
    const long long global = fFirst + event->GetEventID();
    ReseedEvent(fSeed, global);
    if (!fParticle) fParticle = Particle();
    const double energy = Energy(global) * fScale;
    const G4ThreeVector position = Position();
    const G4ThreeVector direction = Direction(position);
    fGun.SetParticleDefinition(fParticle);
    fGun.SetParticleEnergy(energy * MeV);
    fGun.SetParticlePosition(position * mm);
    fGun.SetParticleMomentumDirection(direction);
    fGun.GeneratePrimaryVertex(event);
    if (fPrimaries) std::fprintf(fPrimaries, "%lld,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g\n", global, energy, position.x(), position.y(), position.z(), direction.x(), direction.y(), direction.z());
  }

 private:
  G4ParticleDefinition* Particle() const {
    const Value& particle = fSource.at("particle", "source");
    if (particle.isObject()) return G4IonTable::GetIonTable()->GetIon(static_cast<int>(particle.at("z", "particle").num), static_cast<int>(particle.at("a", "particle").num), 0.);
    auto* found = G4ParticleTable::GetParticleTable()->FindParticle(particle.str);
    if (!found) throw std::runtime_error("unknown particle " + particle.str);
    return found;
  }

  double Energy(long long global) const {
    const Value& block = fSource.at("energy", "source");
    const std::string& kind = block.at("kind", "energy").str;
    const auto number = [&](const char* key) { return block.at(key, "energy").num; };
    if (kind == "uniform") return number("min_MeV") + G4UniformRand() * (number("max_MeV") - number("min_MeV"));
    if (kind == "log_uniform") return number("min_MeV") * std::pow(number("max_MeV") / number("min_MeV"), G4UniformRand());
    if (kind == "power_law") {
      const double low = number("min_MeV"), high = number("max_MeV"), index = number("index"), u = G4UniformRand();
      if (index == 1.) return low * std::pow(high / low, u);
      const double a = std::pow(low, 1. - index), b = std::pow(high, 1. - index);
      return std::pow(a + u * (b - a), 1. / (1. - index));
    }
    if (kind == "gaussian") {
      const double low = number("low_MeV"), high = block.at("high_MeV", "energy").isNumber() ? number("high_MeV") : HUGE_VAL;
      for (;;) {
        const double value = G4RandGauss::shoot(number("mean_MeV"), number("sigma_MeV"));
        if (value >= low && value <= high) return value;
      }
    }
    const auto& energies = block.at("energies_MeV", "energy").array("energies_MeV");
    if (kind == "cycle") return energies[static_cast<std::size_t>(global % static_cast<long long>(energies.size()))].num;
    const auto& probabilities = block.at("probabilities", "energy").array("probabilities");
    double u = G4UniformRand();
    for (std::size_t i = 0; i < energies.size(); ++i)
      if ((u -= probabilities[i].num) < 0.) return energies[i].num;
    return energies.back().num;
  }

  G4ThreeVector Position() const {
    const Value& block = fSource.at("position", "source");
    const std::string& kind = block.at("kind", "position").str;
    const G4ThreeVector centre = Vector(block.at("centre_mm", "position"));
    if (kind == "box_uniform") {
      const G4ThreeVector size = Vector(block.at("size_mm", "position"));
      return centre + G4ThreeVector((G4UniformRand() - .5) * size.x(), (G4UniformRand() - .5) * size.y(), (G4UniformRand() - .5) * size.z());
    }
    if (kind == "disk_uniform") {
      const double r = block.at("radius_mm", "position").num * std::sqrt(G4UniformRand()), phi = CLHEP::twopi * G4UniformRand();
      return centre + G4ThreeVector(r * std::cos(phi), r * std::sin(phi), 0.);
    }
    if (kind == "gaussian_spot") {
      const auto& sigma = block.at("sigma_mm", "position").array("sigma_mm");
      return centre + G4ThreeVector(G4RandGauss::shoot(0., sigma[0].num), G4RandGauss::shoot(0., sigma[1].num), 0.);
    }
    if (kind == "sphere_surface") return centre + block.at("radius_mm", "position").num * Isotropic();
    return centre;
  }

  static G4ThreeVector Isotropic() {
    const double z = 2. * G4UniformRand() - 1., phi = CLHEP::twopi * G4UniformRand(), s = std::sqrt(1. - z * z);
    return {s * std::cos(phi), s * std::sin(phi), z};
  }

  G4ThreeVector Direction(const G4ThreeVector& position) const {
    const Value& block = fSource.at("direction", "source");
    const std::string& kind = block.at("kind", "direction").str;
    if (kind == "fixed") return Vector(block.at("vector", "direction"));
    if (kind == "isotropic") return Isotropic();
    if (kind == "from_point") return (position - Vector(block.at("point_mm", "direction"))).unit();
    const double phi = CLHEP::twopi * G4UniformRand();
    double cosine;
    if (kind == "cone") {
      const double limit = std::cos(block.at("half_angle_deg", "direction").num * deg);
      cosine = 1. - G4UniformRand() * (1. - limit);
    } else {
      cosine = std::sqrt(G4UniformRand());  // cosine_law
    }
    const double s = std::sqrt(1. - cosine * cosine);
    G4ThreeVector out(s * std::cos(phi), s * std::sin(phi), cosine);
    out.rotateUz(Vector(block.at("axis", "direction")));
    return out;
  }

  const Value& fSource;
  long long fSeed, fFirst;
  std::FILE* fPrimaries;
  G4ParticleGun fGun;
  G4ParticleDefinition* fParticle = nullptr;
  double fScale = 1.;
};

}  // namespace g4sim

#endif
