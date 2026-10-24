"""Th13: the cosmic-ray phenomenology pages. cosmic-ray-phenomenology.md (codes and transport conventions, production
cross-section sets and their nuisance schemes, global-fit structure, sources), solar-modulation-models.md (models beyond
the force field, LIS dependence, inputs and lag, alignment with Bartels-rotation data) and cosmic-ray-new-physics.md
(dark matter and pulsars without overclaiming). Each stays under the 24 KB soft budget, links only to files that exist
and is linked from the propagation entry page; the phenomenology page names bartels_rotation.py, states the
diffusion-coefficient conventions with a correct unit conversion and lists every source with a read date and the
unverified items; the global-fit statistics stay in hep-statistics and the excess interpretation outside v1."""
import math
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REFS = ROOT / "skills" / "hep-theory" / "references"
PHENO, MOD, NEWPHYS = (REFS / n for n in ("cosmic-ray-phenomenology.md", "solar-modulation-models.md",
                                          "cosmic-ray-new-physics.md"))
PAGES = (PHENO, MOD, NEWPHYS)
PHENO_SECTIONS = ("## Propagation codes and transport parameters", "## Secondary production cross sections",
                  "## Solar modulation beyond the force field", "## Global propagation fits: what hep-theory supplies",
                  "## What to report", "## Sources read")


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def section(text: str, head: str) -> str:
    start = text.index(head)
    nxt = text.find("\n## ", start + 3)
    return text[start:nxt if nxt > 0 else len(text)]


class Structure(unittest.TestCase):
    def test_sizes_and_links(self):
        for page in PAGES:
            text = read(page)
            with self.subTest(page=page.name):
                self.assertLessEqual(len(text.encode()), 24576)
                self.assertIsNone(re.search(r"experiment:[a-z0-9-]+", text))
                for target in re.findall(r"\]\(([^)#]+)", text):
                    if not target.startswith("http"):
                        self.assertTrue((REFS / target).is_file(), target)

    def test_pages_are_reachable(self):
        entry = read(REFS / "cosmic-ray-propagation.md")
        self.assertIn("(cosmic-ray-phenomenology.md)", entry)
        pheno = read(PHENO)
        self.assertIn("(solar-modulation-models.md)", pheno)
        self.assertIn("(cosmic-ray-new-physics.md)", pheno)
        for page in (MOD, NEWPHYS):
            self.assertIn("(cosmic-ray-phenomenology.md)", read(page))

    def test_phenomenology_sections_in_order(self):
        text = read(PHENO)
        pos = [text.index(h) for h in PHENO_SECTIONS]
        self.assertEqual(pos, sorted(pos))
        self.assertTrue((ROOT / "skills" / "hep-theory" / "scripts" / "bartels_rotation.py").is_file())


class Codes(unittest.TestCase):
    def test_diffusion_conventions_and_unit_conversion(self):
        sec = section(read(PHENO), PHENO_SECTIONS[0])
        for phrase in ("4 GV", "R0 = 1 GV", "K10 = K0 10^delta", "4^delta", "D_pp D_xx"):
            self.assertIn(phrase, sec)
        kpc_cm, myr_s = 648000 / math.pi * 1.495978707e13 * 1e3, 1e6 * 365.25 * 86400
        self.assertAlmostEqual(kpc_cm ** 2 / myr_s / 1e29, 3.017, places=3)
        self.assertIn("3.017e29 cm^2/s", sec)


class CrossSections(unittest.TestCase):
    def test_sets_schemes_and_alternatives(self):
        sec = section(read(PHENO), PHENO_SECTIONS[1])
        for name in ("Webber", "Silberberg-Tsao", "opt12", "opt22", "OPT12up22", "Kamae", "AAfrag"):
            self.assertIn(name, sec)
        self.assertIn("N_eff = 1 + x (N_proxy - 1)", sec)
        self.assertIn("sigma = sigma_default A (T/A)^delta", sec)
        self.assertIn("model-alternative", sec)
        self.assertIn("preprint", sec)


class Modulation(unittest.TestCase):
    def test_models_lis_inputs_and_alignment(self):
        text = read(MOD)
        for phrase in ("phi depends on the LIS", "phi series are recalibrated", "H(-qA)", "A > 0 denotes", "model R",
                       "1832-02-08", "bartels_rotation.py average", "Joint fits of several periods"):
            self.assertIn(phrase, text)


class GlobalFitsAndNewPhysics(unittest.TestCase):
    def test_division_of_labour(self):
        fits = section(read(PHENO), PHENO_SECTIONS[3])
        self.assertIn("hep-statistics owns", fits)
        self.assertIn("outside-v1", fits)
        self.assertIn("`parametric`", fits)
        self.assertIn("`model-alternative`", fits)

    def test_new_physics_states_limits(self):
        text = read(NEWPHYS)
        self.assertIn("outside v1", text)
        self.assertIn("hep-citations", text)
        self.assertIn("never \"evidence for dark matter\"", text)
        example = text[text.index("<!-- example"):text.index("<!-- /example -->")]
        self.assertIn("4.5 sigma", example)  # the excess is reported together with its later reassessment
        self.assertIn("below 1 sigma", example)
        # Profumo et al. 2018 vary the diffusion radially; "two-zone" was a summary's wording (VALIDATION TH13-SOURCES)
        for phrase in ("Halo height", "Transport family", "dipole anisotropy", "radially dependent diffusion"):
            self.assertIn(phrase, text)


class Sources(unittest.TestCase):
    def test_sources_dated_cover_all_pages_and_list_unverified(self):
        pheno = read(PHENO)
        src = section(pheno, PHENO_SECTIONS[5])
        self.assertIn("2026-10-20", src)
        self.assertIn("Not verified and therefore not used", src)
        listed = set(re.findall(r"arXiv:(\d{4}\.\d{4,5}|astro-ph/\d+)", src))
        self.assertGreaterEqual(len(listed), 35)
        for page in PAGES:
            cited = set(re.findall(r"arXiv:(\d{4}\.\d{4,5})", read(page)))
            with self.subTest(page=page.name):
                self.assertLessEqual(cited - listed, set())


if __name__ == "__main__":
    unittest.main()
