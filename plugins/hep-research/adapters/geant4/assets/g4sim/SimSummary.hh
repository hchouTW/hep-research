// g4sim/SimSummary.hh: per-block accumulators of declared observables and the simulation-summary/1 JSON writer
// (adapters/geant4, Geant4 program A2.1, A2.3). C++17 standard library only.
//
// The C++ twin of core/simulation/summary.py, which stays the reference (a test oracle since A2): event i (the global
// event number minus the logical run's first event) belongs to block floor(i / B); events with i >= K B are ignored and
// counted; each observable accumulates only the events its selection keeps: n, per-bin counts with separate underflow
// and overflow, count_if (x > threshold), and Neumaier-compensated sum and sum of squares, min and max. Blocks of
// several threads or jobs merge by block number. Selection rules follow the Python operators: a missing column fails;
// numbers compare with numbers and strings with strings; across types == fails, != holds and an ordering fails.
// From adapter 0.5.0 (Geant4 program C2.1) an observable declared with values keeps each block's raw selected values,
// written in event order when no block holds more than values_max of them (else values_omitted), merge rule concat.
#ifndef G4SIM_SIMSUMMARY_HH
#define G4SIM_SIMSUMMARY_HH

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace g4sim {

struct SummaryError : std::runtime_error {
  using std::runtime_error::runtime_error;
};

// One value of a per-event row: a number or a string.
struct Cell {
  bool isNumber = true;
  double num = 0.;
  std::string str;
  static Cell Number(double v) { return Cell{true, v, {}}; }
  static Cell Text(const std::string& s) { return Cell{false, 0., s}; }
};
using Row = std::map<std::string, Cell>;

struct Condition {
  std::string column, op;
  Cell value;
};

struct ObservableDecl {
  std::string name, source_column;
  std::vector<Condition> selection;
  double lo = 0., hi = 0., width = 0.;
  std::vector<double> thresholds;
  bool values = false;
  long valuesMax = 10000;
};

// Neumaier's variant of Kahan summation.
struct Neumaier {
  double s = 0., c = 0.;
  void Add(double x) {
    double t = s + x;
    c += std::fabs(s) >= std::fabs(x) ? (s - t) + x : (x - t) + s;
    s = t;
  }
  double Value() const { return s + c; }
};

struct Block {
  long events = 0, n = 0, underflow = 0, overflow = 0;
  std::vector<long> hist, countIf;
  Neumaier sum, sumsq;
  bool any = false;
  double min = 0., max = 0.;
  std::vector<std::pair<long, double>> vals;  // (event, value) when the observable keeps values
};

inline int BinCount(const ObservableDecl& o) {
  double n = (o.hi - o.lo) / o.width;
  long k = std::lround(n);
  if (k < 1 || std::fabs(n - k) > 1e-9 * std::max(1.0, n))
    throw SummaryError("observable " + o.name + ": (hi - lo) / width must be a positive integer");
  return static_cast<int>(k);
}

inline bool Holds(const Cell& v, const std::string& op, const Cell& ref) {
  if (v.isNumber != ref.isNumber) {
    if (op == "==") return false;
    if (op == "!=") return true;
    if (op == "contains" || op == "!contains") {
      // str(b) in str(a): only string columns are compared this way in practice; a number column never contains text
      return op == "!contains";
    }
    return false;
  }
  if (op == "contains") return !v.isNumber && v.str.find(ref.str) != std::string::npos;
  if (op == "!contains") return v.isNumber || v.str.find(ref.str) == std::string::npos;
  if (v.isNumber) {
    double a = v.num, b = ref.num;
    if (op == "==") return a == b;
    if (op == "!=") return a != b;
    if (op == "<") return a < b;
    if (op == "<=") return a <= b;
    if (op == ">") return a > b;
    if (op == ">=") return a >= b;
  } else {
    const std::string &a = v.str, &b = ref.str;
    if (op == "==") return a == b;
    if (op == "!=") return a != b;
    if (op == "<") return a < b;
    if (op == "<=") return a <= b;
    if (op == ">") return a > b;
    if (op == ">=") return a >= b;
  }
  throw SummaryError("unknown selection operator " + op);
}

inline bool Selected(const Row& row, const std::vector<Condition>& sel) {
  for (const auto& c : sel) {
    auto it = row.find(c.column);
    if (it == row.end() || !Holds(it->second, c.op, c.value)) return false;
  }
  return true;
}

// A JSON string literal (quotes, backslashes and control characters escaped).
inline std::string JsonQuote(const std::string& s) {
  std::string out = "\"";
  for (char c : s) {
    auto u = static_cast<unsigned char>(c);
    if (c == '"' || c == '\\') {
      out += '\\';
      out += c;
    } else if (c == '\n') {
      out += "\\n";
    } else if (c == '\t') {
      out += "\\t";
    } else if (c == '\r') {
      out += "\\r";
    } else if (u < 0x20) {
      char buf[8];
      std::snprintf(buf, sizeof buf, "\\u%04x", u);
      out += buf;
    } else {
      out += c;
    }
  }
  return out + "\"";
}

// A double that reads back to the same value (17 significant digits); integers stay integers.
inline std::string JsonNum(double x) {
  char buf[40];
  if (std::isfinite(x) && x == std::floor(x) && std::fabs(x) < 1e15) {
    std::snprintf(buf, sizeof buf, "%.1f", x);
  } else {
    std::snprintf(buf, sizeof buf, "%.17g", x);
  }
  return buf;
}

class SummaryAccumulator {
 public:
  SummaryAccumulator() = default;
  SummaryAccumulator(std::vector<ObservableDecl> obs, long blockSize, long blocks, long firstEvent)
      : fObs(std::move(obs)), fB(blockSize), fK(blocks), fFirst(firstEvent) {
    if (fB < 1 || fK < 1) throw SummaryError("block size B and block count K must be positive integers");
    Reset();
  }
  void Reset() {
    fBlocks.assign(fObs.size(), std::vector<Block>(static_cast<std::size_t>(fK)));
    for (std::size_t o = 0; o < fObs.size(); ++o) {
      int nb = BinCount(fObs[o]);
      for (auto& b : fBlocks[o]) {
        b = Block();
        b.hist.assign(static_cast<std::size_t>(nb), 0);
        b.countIf.assign(fObs[o].thresholds.size(), 0);
      }
    }
    fEvents.assign(static_cast<std::size_t>(fK), 0);
    fIgnored = 0;
  }
  bool Empty() const { return fObs.empty(); }
  const std::vector<ObservableDecl>& Observables() const { return fObs; }

  // Accumulate one event with global event number `event`.
  void Fill(long event, const Row& row) {
    long i = event - fFirst;
    if (i < 0) throw SummaryError("event " + std::to_string(event) + " is before the logical run's first event");
    long b = i / fB;
    if (b >= fK) {
      ++fIgnored;
      return;
    }
    ++fEvents[static_cast<std::size_t>(b)];
    for (std::size_t o = 0; o < fObs.size(); ++o) {
      const ObservableDecl& d = fObs[o];
      if (!Selected(row, d.selection)) continue;
      auto it = row.find(d.source_column);
      if (it == row.end() || !it->second.isNumber || !std::isfinite(it->second.num))
        throw SummaryError("event " + std::to_string(event) + ": column " + d.source_column + " is not a finite number");
      double x = it->second.num;
      Block& blk = fBlocks[o][static_cast<std::size_t>(b)];
      ++blk.n;
      blk.sum.Add(x);
      blk.sumsq.Add(x * x);
      if (!blk.any || x < blk.min) blk.min = x;
      if (!blk.any || x > blk.max) blk.max = x;
      blk.any = true;
      if (d.values) blk.vals.emplace_back(event, x);
      double j = std::floor((x - d.lo) / d.width);
      if (j < 0) ++blk.underflow;
      else if (j >= static_cast<double>(blk.hist.size())) ++blk.overflow;
      else ++blk.hist[static_cast<std::size_t>(j)];
      for (std::size_t t = 0; t < d.thresholds.size(); ++t)
        if (x > d.thresholds[t]) ++blk.countIf[t];
    }
  }

  // Merge another accumulator of the same logical run (same observables, blocks, binning) block by block.
  void Merge(const SummaryAccumulator& other) {
    if (other.fObs.size() != fObs.size() || other.fK != fK || other.fB != fB)
      throw SummaryError("accumulators of different observables or blocks do not merge");
    for (std::size_t o = 0; o < fObs.size(); ++o)
      for (std::size_t b = 0; b < fBlocks[o].size(); ++b) {
        Block& a = fBlocks[o][b];
        const Block& c = other.fBlocks[o][b];
        if (a.hist.size() != c.hist.size()) throw SummaryError("histograms with different binnings do not merge");
        a.n += c.n;
        a.underflow += c.underflow;
        a.overflow += c.overflow;
        for (std::size_t j = 0; j < a.hist.size(); ++j) a.hist[j] += c.hist[j];
        for (std::size_t t = 0; t < a.countIf.size(); ++t) a.countIf[t] += c.countIf[t];
        a.sum.Add(c.sum.s);
        a.sum.Add(c.sum.c);
        a.sumsq.Add(c.sumsq.s);
        a.sumsq.Add(c.sumsq.c);
        a.vals.insert(a.vals.end(), c.vals.begin(), c.vals.end());
        if (c.any) {
          a.min = a.any ? std::min(a.min, c.min) : c.min;
          a.max = a.any ? std::max(a.max, c.max) : c.max;
          a.any = true;
        }
      }
    for (std::size_t b = 0; b < fEvents.size(); ++b) fEvents[b] += other.fEvents[b];
    fIgnored += other.fIgnored;
  }

  // simulation-summary/1; `runJson` is the JSON object of the run identity (without the block fields, which are
  // added here), `producerJson` the producer object.
  std::string Json(const std::string& runJson, const std::string& producerJson) const {
    long inBlocks = 0;
    for (long e : fEvents) inBlocks += e;
    bool anyValues = false;
    std::ostringstream o;
    std::string run = runJson.empty() || runJson == "{}" ? "{" : runJson.substr(0, runJson.rfind('}')) + ", ";
    o << "{\"summary_version\": \"simulation-summary/1\", \"run\": " << run << "\"first_event\": " << fFirst
      << ", \"block_size\": " << fB << ", \"blocks\": " << fK << ", \"events_in_blocks\": " << inBlocks
      << ", \"events_ignored\": " << fIgnored << ", \"producer\": " << producerJson << "}, \"observables\": [";
    for (std::size_t i = 0; i < fObs.size(); ++i) {
      const ObservableDecl& d = fObs[i];
      o << (i ? ", " : "") << "{\"name\": " << Quote(d.name) << ", \"source_column\": " << Quote(d.source_column)
        << ", \"selection\": [";
      for (std::size_t c = 0; c < d.selection.size(); ++c) {
        const Condition& s = d.selection[c];
        o << (c ? ", " : "") << "{\"column\": " << Quote(s.column) << ", \"op\": " << Quote(s.op)
          << ", \"value\": " << (s.value.isNumber ? Num(s.value.num) : Quote(s.value.str)) << "}";
      }
      o << "], \"bins\": {\"lo\": " << Num(d.lo) << ", \"hi\": " << Num(d.hi) << ", \"width\": " << Num(d.width)
        << "}, \"thresholds\": [";
      for (std::size_t t = 0; t < d.thresholds.size(); ++t) o << (t ? ", " : "") << Num(d.thresholds[t]);
      o << "], \"blocks\": [";
      std::size_t biggest = 0;
      for (const Block& k : fBlocks[i]) biggest = std::max(biggest, k.vals.size());
      bool keep = d.values && static_cast<long>(biggest) <= d.valuesMax;
      anyValues = anyValues || d.values;
      for (std::size_t b = 0; b < fBlocks[i].size(); ++b) {
        const Block& k = fBlocks[i][b];
        o << (b ? ", " : "") << "{\"block\": " << b << ", \"events\": " << fEvents[b] << ", \"n\": " << k.n
          << ", \"hist\": [";
        for (std::size_t j = 0; j < k.hist.size(); ++j) o << (j ? ", " : "") << k.hist[j];
        o << "], \"underflow\": " << k.underflow << ", \"overflow\": " << k.overflow << ", \"count_if\": [";
        for (std::size_t t = 0; t < k.countIf.size(); ++t) o << (t ? ", " : "") << k.countIf[t];
        o << "], \"sum\": " << Num(k.sum.Value()) << ", \"sumsq\": " << Num(k.sumsq.Value())
          << ", \"min\": " << (k.any ? Num(k.min) : "null") << ", \"max\": " << (k.any ? Num(k.max) : "null");
        if (keep) {
          std::vector<std::pair<long, double>> v = k.vals;
          std::stable_sort(v.begin(), v.end(), [](const auto& p, const auto& q) { return p.first < q.first; });
          o << ", \"values\": [";
          for (std::size_t j = 0; j < v.size(); ++j) o << (j ? ", " : "") << Num(v[j].second);
          o << "]";
        }
        o << "}";
      }
      o << "]";
      if (d.values) {
        o << ", \"values_max\": " << d.valuesMax;
        if (keep)
          o << ", \"quantile_method\": \"hyndman-fan-7\"";
        else
          o << ", \"values_omitted\": " << Quote("a block holds " + std::to_string(biggest) +
                                                 " values, more than values_max " + std::to_string(d.valuesMax));
      }
      o << "}";
    }
    o << "], \"merge\": {\"events\": \"sum\", \"n\": \"sum\", \"hist\": \"hist\", \"underflow\": \"sum\", "
         "\"overflow\": \"sum\", \"count_if\": \"sum\", \"sum\": \"sum\", \"sumsq\": \"sum\", \"min\": \"min\", "
         "\"max\": \"max\"" << (anyValues ? ", \"values\": \"concat\"" : "") << "}}\n";
    return o.str();
  }

  static std::string Quote(const std::string& s) { return JsonQuote(s); }
  static std::string Num(double x) { return JsonNum(x); }

 private:
  std::vector<ObservableDecl> fObs;
  long fB = 1, fK = 1, fFirst = 0;
  std::vector<std::vector<Block>> fBlocks;
  std::vector<long> fEvents;
  long fIgnored = 0;
};

}  // namespace g4sim

#endif
