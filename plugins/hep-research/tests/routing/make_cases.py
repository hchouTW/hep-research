"""Writes tests/routing/cases.json (routing cases for task M5.3). Edit the table here, then rerun (--stdout prints instead)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inputs import INPUTS  # noqa: E402

# (id, lang, kind, prompt, expected, triggers, not_skill, journey, extra)
C = [
 # detector-response
 ("dr-direct-1", "en", "direct", "Measure the muon trigger efficiency with tag-and-probe and give me the per-bin uncertainty.", "detector-response", ["tag-and-probe"], None, None, {}),
 ("dr-direct-2", "zh-Hant", "direct", "請幫我建立這個量能器的響應矩陣，並檢查 data/MC agreement。", "detector-response", ["response matrices", "data/MC agreement"], None, None, {}),
 ("dr-neighbor-1", "en", "neighboring", "Unfold this measured spectrum with the response matrix I already have.", "hep-statistics", ["unfolding"], "detector-response", None, {}),
 ("dr-negative-1", "en", "negative", "Design the background estimate for my dilepton measurement using control regions.", "hep-analysis", ["background estimation", "control regions"], "detector-response", None, {}),
 # hep-analysis
 ("an-direct-1", "en", "direct", "Review this measurement spec: is the estimand clear and are the systematic uncertainties complete?", "hep-analysis", ["estimand", "systematic uncertainties", "measurement review"], None, None, {}),
 ("an-direct-2", "zh-Hant", "direct", "我要設計一個中微子截面量測的事件選擇與 cutflows，還有 blinding policy。", "hep-analysis", ["cutflows", "blinding policy"], None, None, {}),
 ("an-neighbor-1", "en", "neighboring", "Set a CLs upper limit on the signal strength from these yields.", "hep-statistics", ["CLs"], "hep-analysis", None, {}),
 ("an-negative-1", "zh-Hant", "negative", "我的分析程式在讀取 ROOT 檔時 crashes，請幫我除錯。", "hep-computing", ["crashes", "ROOT/PyROOT"], "hep-analysis", None, {}),
 # hep-computing
 ("co-direct-1", "en", "direct", "My ROOT macro has a memory leak after 10^6 events; find it.", "hep-computing", ["memory leaks", "ROOT/PyROOT"], None, None, {}),
 ("co-direct-2", "en", "direct", "Split this event generation into chunks for batch submission, with resubmission and a merge that does not double count.", "hep-computing", ["batch submission, merging and recovery"], None, None, {}),
 ("co-neighbor-1", "en", "neighboring", "Is this extracted cross section physically consistent with the tree-level prediction?", "hep-theory", ["cross sections"], "hep-computing", None, {}),
 ("co-negative-1", "zh-Hant", "negative", "請幫我推導這個衰變寬度的解析式，並說明近似的適用範圍。", "hep-theory", ["decay rates", "validity domains"], "hep-computing", None, {}),
 # hep-statistics
 ("st-direct-1", "en", "direct", "Give me a Feldman-Cousins interval for zero observed events with background 0.8.", "hep-statistics", ["Feldman-Cousins", "low or zero counts"], None, None, {}),
 ("st-direct-2", "zh-Hant", "direct", "兩個實驗量測同一觀測量，有共同的系統誤差，請做 combinations across datasets。", "hep-statistics", ["combinations across datasets or experiments"], None, None, {}),
 ("st-neighbor-1", "en", "neighboring", "Which selection cuts should define my signal region?", "hep-analysis", ["event/candidate selection"], "hep-statistics", None, {}),
 ("st-negative-1", "en", "negative", "Derive the prediction for this new-physics coupling so I can fit it later.", "hep-theory", ["predictions"], "hep-statistics", None, {}),
 # hep-theory
 ("th-direct-1", "en", "direct", "Derive the tree-level e+e- -> mu+mu- cross section with explicit conventions and check the limits.", "hep-theory", ["cross sections", "conventions"], None, None, {}),
 ("th-direct-2", "zh-Hant", "direct", "請說明這個 NLO 計算的 scale envelopes 該如何給出理論誤差。", "hep-theory", ["scale envelopes"], None, None, {}),
 ("th-neighbor-1", "en", "neighboring", "Fit the coupling of my model to these published data points with their covariance.", "hep-statistics", ["fits"], "hep-theory", None, {}),
 ("th-negative-1", "en", "negative", "Write the results section of the paper from these fit outputs.", "research-communication", ["drafting or revising paper sections"], "hep-theory", None, {}),
 # physics-ml
 ("ml-direct-1", "en", "direct", "Train a jet classifier in PyTorch with grouped splits by run so nothing leaks.", "physics-ml", ["grouped train/validation/test splits and leakage checks"], None, None, {}),
 ("ml-direct-2", "zh-Hant", "direct", "我的模擬太慢，想用 PyTorch 做 surrogates，並檢查 domain shift。", "physics-ml", ["surrogates", "domain shift"], None, None, {}),
 ("ml-neighbor-1", "en", "neighboring", "Is the likelihood-free inference built on my network statistically valid, with coverage?", "hep-statistics", ["coverage"], "physics-ml", None, {}),
 ("ml-negative-1", "en", "negative", "My C++ CMake build fails to link ROOT libraries.", "hep-computing", ["CMake builds"], "physics-ml", None, {}),
 # research-communication
 ("rc-direct-1", "en", "direct", "Check whether this INSPIRE citation really supports the 2.1% number in my draft.", "research-communication", ["citations", "INSPIRE-HEP"], None, None, {}),
 ("rc-direct-2", "zh-Hant", "direct", "請幫我回覆審稿人的 referee reports，並修改摘要。", "research-communication", ["referee reports", "abstracts"], None, None, {}),
 ("rc-neighbor-1", "en", "neighboring", "Is this Feynman diagram physically allowed at tree level?", "hep-theory", ["amplitudes"], "research-communication", None, {}),
 ("rc-negative-1", "en", "negative", "Run the template fit for the paper's main result.", "hep-statistics", ["template fits"], "research-communication", None, {}),
 # hep-statistics reinforcement (S12)
 ("st-impacts-1", "en", "direct", "Show me the pulls, constraints and impacts of the nuisance parameters after my profile likelihood fit.", "hep-statistics", ["nuisance parameters", "profile likelihood"], None, None, {}),
 ("st-lee-1", "zh-Hant", "direct", "我在質量掃描中看到 3.5σ 的局部超出，請做 look-elsewhere effects 的修正並給出全域顯著性。", "hep-statistics", ["significance and look-elsewhere effects"], None, None, {}),
 ("st-sensitivity-1", "en", "direct", "What median discovery significance should I expect for 5 signal events over 20 background, using Asimov datasets?", "hep-statistics", ["toys and asimov datasets"], None, None, {}),
 ("st-gof-1", "zh-Hant", "direct", "我的 template fits 有很多 bin 只有幾個事件，goodness of fit 該怎麼算？", "hep-statistics", ["goodness of fit", "template fits"], None, None, {}),
 ("st-bayes-1", "en", "direct", "My MCMC chains give R-hat 1.08; can I report these Bayesian posteriors?", "hep-statistics", ["bayesian posteriors (priors, samplers, convergence)"], None, None, {}),
 ("st-sweights-1", "en", "neighboring", "Fit the decay-time distribution with sWeights from my mass fit and give an uncertainty that covers.", "hep-statistics", ["unbinned fits"], "hep-analysis", None, {}),
 ("st-nsbi-1", "zh-Hant", "neighboring", "我們用神經網路估計似然比（NSBI）做推論，最後區間的 coverage 要怎麼驗證？", "hep-statistics", ["coverage"], "physics-ml", None, {}),
 ("st-publish-1", "en", "neighboring", "Prepare our likelihoods for HEPData as a background-only workspace plus signal patches so others can reuse the fit.", "hep-statistics", ["likelihoods"], "research-communication", None, {}),
 # batch schedulers (work order B13)
 ("co-batch-sbatch-1", "en", "direct", "Write an sbatch job array that runs my 500 toy fits in chunks with reproducible seeds, and merge the outputs without double counting.", "hep-computing", ["Slurm and HTCondor job arrays", "batch submission, merging and recovery"], None, None, {}),
 ("co-batch-held-1", "zh-Hant", "direct", "我的 HTCondor 工作被 hold 住了，原因寫超過記憶體上限，該怎麼處理後再重新提交？", "hep-computing", ["held or evicted jobs"], None, None, {}),
 ("co-batch-evicted-1", "en", "direct", "Some of my HTCondor jobs were evicted and restarted, and now the merged histogram seems to count those chunks twice.", "hep-computing", ["held or evicted jobs", "batch submission, merging and recovery"], None, None, {}),
 ("co-batch-pilot-1", "zh-Hant", "direct", "我要在 Slurm 上跑 2000 個 chunk，記憶體和 walltime 要怎麼設定？要先跑一個 pilot 嗎？", "hep-computing", ["pilot sizing"], None, None, {}),
 ("co-batch-gpu-1", "en", "direct", "Submit my classifier training as single-node GPU jobs on our Slurm cluster, one job per learning rate, and collect the results.", "hep-computing", ["Slurm and HTCondor job arrays"], None, None, {"chain": ["hep-computing", "physics-ml"], "note": "submission is hep-computing; the model, training and validation hand to physics-ml"}),
 ("co-batch-negative-1", "en", "negative", "My 2000 toy pseudo-experiments finished on the batch cluster. Does my 95% CL Feldman-Cousins interval have the right coverage?", "hep-statistics", ["Feldman-Cousins", "coverage"], "hep-computing", None, {}),
 # journeys
 ("j01", "en", "journey", "Plan the time-dependent helium flux and He/p ratio measurement for AMS-02 across two periods.", "hep-analysis", ["exposure"], None, "J1", {"profiles": ["experiment:ams-02"], "chain": ["hep-analysis", "detector-response", "hep-statistics", "research-communication"]}),
 ("j02", "zh-Hant", "journey", "研究 AMS-02 RICH 的速度解析度隨電荷的變化。", "detector-response", ["Cherenkov/RICH", "resolution"], None, "J2", {"profiles": ["experiment:ams-02"], "chain": ["detector-response", "hep-statistics"]}),
 ("j03", "en", "journey", "Measure the corrected angular distribution at my e+e- collider with its own luminosity and response.", "hep-analysis", ["luminosity"], None, "J3", {"chain": ["hep-analysis", "detector-response", "hep-statistics"]}),
 ("j04", "en", "journey", "Compute the tree-level cross section with all conventions stated and check it numerically.", "hep-theory", ["cross sections", "consistency checks"], None, "J4", {"profiles": [], "chain": ["hep-theory", "hep-computing", "hep-theory"]}),
 ("j05", "en", "journey", "Fold my prediction through the detector response and fit a normalization scale.", "hep-theory", ["predictions"], None, "J5", {"chain": ["hep-theory", "hep-statistics", "research-communication"]}),
 ("j06", "zh-Hant", "journey", "用已發表的資料比較我的模型（comparing a model with published data），不需要偵測器細節。", "hep-theory", ["comparing a model with an experiment's published data"], None, "J6", {"chain": ["hep-theory", "hep-statistics"], "loads": "dataset records only"}),
 ("j07", "en", "journey", "Recast the published search with its efficiency maps to constrain my model.", "hep-theory", ["recasting a published analysis"], None, "J7", {"chain": ["hep-theory", "detector-response", "hep-statistics"]}),
 ("j08", "en", "journey", "Run a convergence study of this integral and cross-check the symbolic result numerically.", "hep-computing", ["convergence and tolerance studies"], None, "J8", {"chain": ["hep-computing", "hep-theory"]}),
 ("j09", "zh-Hant", "journey", "訓練一個分類器並宣告 surrogates 的有效範圍，之後用於推論。", "physics-ml", ["surrogates"], None, "J9", {"chain": ["physics-ml", "hep-statistics"]}),
 ("j10", "en", "journey", "Draft the paper section and figures with claim-to-result links and honest status.", "research-communication", ["claim-to-result links"], None, "J10", {"chain": ["research-communication"]}),
 ("j11", "en", "journey", "Use our collaboration's private calibration constants from my local profile in the efficiency study.", "detector-response", ["calibration"], None, "J11", {"chain": ["detector-response"], "note": "local profile via project config; nothing enters the plugin"}),
 ("j12", "en", "journey", "Set up a lattice QCD global analysis of form factors.", "hep-theory", [], None, "J12", {"chain": ["hep-theory", "hep-statistics"], "limited_support": True}),
 # special categories
 ("ams-computing-1", "en", "ams-computing", "My AMS-02 reconstruction script segfaults when reading the ntuple.", "hep-computing", ["crashes"], "hep-analysis", None, {"note": "experiment name does not route; the code problem does"}),
 ("ams-computing-2", "zh-Hant", "ams-computing", "AMS 的資料處理程式在 batch submission 後合併結果重複計算。", "hep-computing", ["batch submission, merging and recovery"], "hep-analysis", None, {}),
 ("theory-no-exp-1", "en", "theory-no-experiment", "Derive the decay rate of a scalar to two fermions; no experiment involved.", "hep-theory", ["decay rates"], None, None, {"profiles": []}),
 ("recast-1", "zh-Hant", "recasting", "請重新詮釋（recasting a published analysis）這個 LHC 搜尋結果以限制我的模型。", "hep-theory", ["recasting a published analysis"], None, None, {"chain": ["hep-theory", "detector-response", "hep-statistics"]}),
 ("out-of-v1-1", "en", "out-of-v1", "Fit cosmic-ray propagation parameters with GALPROP across all species.", "hep-statistics", [], None, None, {"limited_support": True}),
 ("out-of-v1-2", "zh-Hant", "out-of-v1", "幫我做 SMEFT 全域擬合。", "hep-theory", [], None, None, {"limited_support": True}),  # hep-theory claims EFT global fits
 ("underspec-1", "en", "underspecified", "Compare the two experiments.", "ask", [], None, None, {"note": "ask which datasets and observables; never pick experiments"}),
 ("underspec-2", "zh-Hant", "underspecified", "比較這兩個實驗的結果。", "ask", [], None, None, {}),
]

cases = []
for cid, lang, kind, prompt, exp, trig, notsk, journey, extra in C:
    d = {"id": cid, "lang": lang, "kind": kind, "prompt": prompt, "expected_primary": exp, "trigger_terms": trig}
    if notsk:
        d["not"] = notsk
    if journey:
        d["journey"] = journey
    d.update(extra)
    if cid in INPUTS:
        d["inputs"] = INPUTS[cid]
    cases.append(d)
TEXT = json.dumps({"note": "Routing cases (task M5.3). Static check: tools/check_routing_static.py. "
                           "A live check needs approval for paid model calls.", "cases": cases}, indent=1, ensure_ascii=False) + "\n"

if __name__ == "__main__":
    # --stdout prints the generated file instead of writing it (used by the tests)
    if "--stdout" in sys.argv[1:]:
        sys.stdout.write(TEXT)
    else:
        (Path(__file__).resolve().parent / "cases.json").write_text(TEXT, encoding="utf-8")
