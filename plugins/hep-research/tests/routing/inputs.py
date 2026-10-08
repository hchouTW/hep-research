"""Synthetic input files for live routing cases (routing round after G5).

Each case that says "this", "my" or "these" gets small files in a fresh project directory, so a live run tests
routing instead of stopping for missing inputs. Every file is SYNTHETIC and says so; none is real data.
"""
import json

TAG = "SYNTHETIC routing fixture: invented values, not data from any experiment."

def _csv(header, rows):
    return f"# {TAG}\n{header}\n" + "\n".join(rows) + "\n"

INPUTS = {
 "co-companion-ws-1": {
  "CMakeLists.txt": f"# {TAG}\ncmake_minimum_required(VERSION 3.20)\nproject(histtool CXX)\nadd_executable(histtool main.cpp)\ntarget_link_libraries(histtool ROOT::Hist)\n",
  "main.cpp": f"// {TAG}\n#include <TH1D.h>\nint main() {{ TH1D h(\"h\", \"h\", 10, 0, 1); h.Fill(0.5); return 0; }}\n",
  "hep-research.project.json": json.dumps({"schema_version": "1.0.0", "plugin_version": ">=0.5", "local_profile_paths": ["./profiles/ams-02-private"],
                                           "experiments": [{"profile": "experiment:ams-02-private", "version": "1.1.0"}], "theory": []}, indent=1) + "\n",
  "profiles/ams-02-private/profile.json": json.dumps({"_note": TAG + " A stand-in for a companion-managed local profile; no companion content.",
                                                      "id": "experiment:ams-02-private", "kind": "experiment", "version": "1.1.0"}, indent=1) + "\n"},
 "dr-direct-1": {"tnp_counts.csv": _csv("pt_lo,pt_hi,probes,passing_probes", ["20,30,1200,1104", "30,50,2400,2280", "50,100,900,873"])},
 "dr-direct-2": {"calo_scan.csv": _csv("beam_energy_GeV,mean_reco_GeV,sigma_reco_GeV,data_or_mc", ["10,9.6,0.62,data", "10,9.7,0.58,mc", "50,48.9,1.71,data", "50,49.2,1.60,mc"])},
 "dr-neighbor-1": {"measured_spectrum.csv": _csv("bin,lo,hi,counts", ["0,0,10,520", "1,10,20,310", "2,20,40,140"]),
                    "response_matrix.csv": _csv("reco_bin,true0,true1,true2", ["0,0.80,0.12,0.01", "1,0.15,0.75,0.10", "2,0.01,0.10,0.82"])},
 "dr-negative-1": {"analysis_note.md": f"<!-- {TAG} -->\n# Dilepton measurement (draft)\nSignal region: two opposite-sign muons, m_ll in 200-1000 GeV.\nMain backgrounds: Drell-Yan, ttbar, fakes. No background method chosen yet.\n"},
 "an-direct-1": {"measurement_spec.md": f"<!-- {TAG} -->\n# Measurement spec\nObservable: number of events with two jets above 30 GeV.\nResult: 'the rate'.\nSystematics: jet energy scale.\n"},
 "an-neighbor-1": {"yields.json": f'{{"_note": "{TAG}", "observed": 7, "background": 4.2, "background_unc": 0.9, "signal_mu1": 3.1}}\n'},
 "an-negative-1": {"read_tree.py": f"# {TAG}\nimport ROOT\nf = ROOT.TFile.Open('events.root')\nt = f.Get('Events')\nfor ev in t:\n    print(ev.Muon_pt[0])  # crashes on events with no muon\n"},
 "co-direct-1": {"loop.C": f"// {TAG}\nvoid loop() {{\n  for (int i = 0; i < 1000000; ++i) {{\n    TH1F* h = new TH1F(Form(\"h%d\", i), \"\", 10, 0, 1);\n    h->Fill(0.5);\n  }}\n}}\n"},
 "co-direct-2": {"generate.py": f"# {TAG}\nimport sys, json, random\nn = int(sys.argv[1]); random.seed(int(sys.argv[2]))\nprint(json.dumps({{'n': n, 'sum': sum(random.random() for _ in range(n))}}))\n"},
 "co-neighbor-1": {"result.md": f"<!-- {TAG} -->\nExtracted sigma(e+e- -> mu+mu-) at sqrt(s) = 10 GeV: 0.92 +- 0.03 nb.\nTree-level QED expectation quoted by the student: 0.87 nb.\n"},
 "co-negative-1": {"process.md": f"<!-- {TAG} -->\n過程：純量粒子 S（質量 M）衰變為一對狄拉克費米子，Yukawa 耦合 y。\n"},
 "st-neighbor-1": {"analysis_summary.md": f"<!-- {TAG} -->\nSearch for a 1 TeV resonance decaying to two b-jets. Available variables: m_jj, b-tag score, delta_eta_jj, jet pT.\n"},
 "st-negative-1": {"model.md": f"<!-- {TAG} -->\nModel: a new vector boson Z' with mass 2 TeV coupling to muons with strength g'. Observable: dimuon mass spectrum.\n"},
 "th-neighbor-1": {"published_points.csv": _csv("x,y,stat,syst_corr", ["1,10.2,0.5,0.3", "2,8.1,0.4,0.25", "3,6.3,0.4,0.2"]),
                    "covariance.csv": _csv("i,j,cov", ["0,0,0.34", "1,1,0.2225", "2,2,0.2", "0,1,0.075", "1,2,0.05", "0,2,0.06"]),
                    "model.md": f"<!-- {TAG} -->\nPrediction y(x; g) = g^2 * 12 / (1 + 0.2 x).\n"},
 "th-negative-1": {"fit_outputs.json": f'{{"_note": "{TAG}", "status": ["synthetic"], "mu": 1.02, "mu_err": [0.11, 0.12], "chi2": 9.8, "ndf": 9}}\n'},
 "ml-direct-1": {"jets.csv": _csv("run,event,pt,eta,n_constituents,label", ["1001,1,45.2,0.3,23,1", "1001,2,38.1,-1.2,17,0", "1002,1,52.7,2.0,31,1"])},
 "ml-neighbor-1": {"lfi_notes.md": f"<!-- {TAG} -->\nA neural ratio estimator trained on 1e5 simulated samples gives a 68% interval for theta of [0.8, 1.3]. No coverage test yet.\n"},
 "ml-negative-1": {"CMakeLists.txt": f"# {TAG}\ncmake_minimum_required(VERSION 3.16)\nproject(ana CXX)\nadd_executable(ana main.cpp)\n"},
 "rc-direct-1": {"draft.md": f"<!-- {TAG} -->\nThe trigger efficiency uncertainty is 2.1% [INSPIRE: Example:2020abc].\n"},
 "rc-direct-2": {"referee_report.md": f"<!-- {TAG} -->\n審稿人一：摘要沒有說明系統誤差的主要來源。審稿人二：圖三缺少誤差帶。\n"},
 "rc-neighbor-1": {"diagram.md": f"<!-- {TAG} -->\nDiagram: e- e+ annihilate into a photon, which produces a single muon (no antimuon) at tree level.\n"},
 "rc-negative-1": {"fit_config.json": f'{{"_note": "{TAG}", "templates": ["signal.csv", "background.csv"], "data": "data.csv", "poi": "mu"}}\n',
                    "signal.csv": _csv("bin,count", ["0,3", "1,8", "2,4"]), "background.csv": _csv("bin,count", ["0,40", "1,30", "2,20"]),
                    "data.csv": _csv("bin,count", ["0,45", "1,37", "2,25"])},
 "j04": {"process.md": f"<!-- {TAG} -->\nProcess: e+ e- -> mu+ mu- through one photon at sqrt(s) = 10 GeV, unpolarized beams.\n"},
 "j05": {"prediction.csv": _csv("bin,lo,hi,sigma_pb", ["0,-1,0,370", "1,0,1,375"]),
          "response.json": f'{{"_note": "{TAG}", "level_in": "particle", "level_out": "detector", "matrix": [[0.9,0.05],[0.05,0.9]], "efficiency_included": true}}\n',
          "observed.csv": _csv("bin,counts", ["0,3410", "1,3460"])},
 "j08": {"integral.md": f"<!-- {TAG} -->\nI(a) = integral_0^1 x^a log(x) dx, symbolic result -1/(a+1)^2. Check at a = 0.5 and a = 3.\n"},
 "j10": {"results.json": f'{{"_note": "{TAG}", "status": ["synthetic"], "sigma_pb": 745.6, "stat": 6.6, "syst": 14.9}}\n'},
 "j11": {"hep-research.project.json": '{\n "schema_version": "1.0.0",\n "plugin_version": ">=0.1,<1.0",\n "local_profile_paths": ["private-profile"]\n}\n',
          "private-profile/README.md": f"<!-- {TAG} -->\nLocal profile with calibration constants (invented).\n",
          "private-profile/calibration.csv": _csv("channel,gain", ["0,1.02", "1,0.98"])},
 "ams-computing-1": {"reco_ntuple.py": f"# {TAG}\nimport ctypes\nbuf = (ctypes.c_float * 10)()\nfor i in range(100):\n    buf[i] = 0.0  # writes past the buffer\n"},
 "ams-computing-2": {"merge.sh": f"# {TAG}\ncat out/job_*.txt out/job_*_retry.txt > merged.txt\n"},
 "co-batch-sbatch-1": {"toy_fit.py": f"# {TAG}\nimport sys, json, random\nstart, stop, seed = map(int, sys.argv[1:4])\nrandom.seed(seed)\nprint(json.dumps({{'n': stop - start}}))\n"},
 "co-batch-held-1": {"events.log": f"# {TAG}\n012 (1234.007.000) 2026-10-03 10:00:00 Job was held.\n\tJob exceeded its memory request (synthetic)\n\tCode 34 Subcode 0\n...\n"},
 "co-batch-evicted-1": {"merge.sh": f"# {TAG}\ncat out/*.json > merged.json\n"},
 # a two-bin pyhf workspace with a normalization and a shape nuisance, and the profile likelihood fit already done
 "st-impacts-1": {
  "workspace.json": json.dumps({"_note": TAG, "version": "1.0.0",
                                "channels": [{"name": "sr", "samples": [
                                    {"name": "signal", "data": [3.0, 5.0], "modifiers": [{"name": "mu", "type": "normfactor", "data": None}]},
                                    {"name": "background", "data": [20.0, 12.0], "modifiers": [
                                        {"name": "bkg_norm", "type": "normsys", "data": {"hi": 1.1, "lo": 0.9}},
                                        {"name": "jes", "type": "histosys", "data": {"hi_data": [21.5, 12.4], "lo_data": [18.6, 11.7]}}]}]}],
                                "observations": [{"name": "sr", "data": [25.0, 18.0]}],
                                "measurements": [{"name": "meas", "config": {"poi": "mu", "parameters": []}}]}, indent=1) + "\n",
  "fit_result.json": json.dumps({"_note": TAG, "fit": "maximum likelihood on workspace.json (pyhf 0.7.6), observed data", "bestfit": {"mu": 1.275, "bkg_norm": 0.053, "jes": 0.052},
                                 "uncertainty": {"mu": 0.845, "bkg_norm": 0.972, "jes": 0.977}}, indent=1) + "\n"},
}
