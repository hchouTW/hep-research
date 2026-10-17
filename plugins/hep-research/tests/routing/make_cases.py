"""Writes tests/routing/cases.json (routing cases). Edit the table here, then rerun (--stdout prints instead)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inputs import INPUTS  # noqa: E402

# (id, lang, kind, prompt, expected, triggers, not_skill, journey, extra)
C = [
 # hep-detector
 ("dr-direct-1", "en", "direct", "Measure the muon trigger efficiency with tag-and-probe and give me the per-bin uncertainty.", "hep-detector", ["tag-and-probe"], None, None, {}),
 ("dr-direct-2", "zh-Hant", "direct", "請幫我建立這個量能器的響應矩陣，並檢查 data/MC agreement。", "hep-detector", ["response matrices", "data/MC agreement"], None, None, {}),
 ("dr-neighbor-1", "en", "neighboring", "Unfold this measured spectrum with the response matrix I already have.", "hep-statistics", ["unfolding"], "hep-detector", None, {}),
 ("dr-negative-1", "en", "negative", "Design the background estimate for my dilepton measurement using control regions.", "hep-measurement", ["background estimation", "control regions"], "hep-detector", None, {}),
 # hep-measurement
 ("an-direct-1", "en", "direct", "Review this measurement spec: is the estimand clear and are the systematic uncertainties complete?", "hep-measurement", ["estimand", "systematic uncertainties", "measurement review"], None, None, {}),
 ("an-direct-2", "zh-Hant", "direct", "我要設計一個中微子截面量測的事件選擇與 cutflows，還有 blinding policy。", "hep-measurement", ["cutflows", "blinding policy"], None, None, {}),
 ("an-neighbor-1", "en", "neighboring", "Set a CLs upper limit on the signal strength from these yields.", "hep-statistics", ["CLs"], "hep-measurement", None, {}),
 ("an-negative-1", "zh-Hant", "negative", "我的分析程式在讀取 ROOT 檔時 crashes，請幫我除錯。", "hep-computing", ["crashes", "ROOT/PyROOT"], "hep-measurement", None, {}),
 # hep-measurement boundaries (ANA-P4-5): one en and one zh-Hant case per boundary
 ("an-b-eff-1", "en", "direct", "How should the trigger and selection efficiencies enter the correction chain of my flux measurement, each with its own denominator?", "hep-measurement", ["correction chains"], None, None, {"set": "ANA-P4-5"}),
 ("an-b-eff-2", "zh-Hant", "neighboring", "請用 tag-and-probe 量測這個 muon 的重建效率，並給出每個 bin 的不確定度。", "hep-detector", ["tag-and-probe"], "hep-measurement", None, {"set": "ANA-P4-5"}),
 ("an-b-blind-1", "en", "direct", "Help me design the blinding policy for my search: which regions and observables stay masked until unblinding?", "hep-measurement", ["blinding policy"], None, None, {"set": "ANA-P4-5"}),
 ("an-b-blind-2", "zh-Hant", "neighboring", "請幫我檢查這些輸出、logs 和 caches 有沒有洩漏盲區的數值（advisory blinding checks）。", "hep-computing", ["advisory blinding checks of outputs, logs and caches"], "hep-measurement", None, {"set": "ANA-P4-5"}),
 ("an-b-closure-1", "en", "direct", "Design the closure test for my ABCD background estimation in a validation region.", "hep-measurement", ["background estimation", "ABCD"], None, None, {"set": "ANA-P4-5"}),
 ("an-b-closure-2", "zh-Hant", "neighboring", "我的 template fits 已經完成，請計算 goodness of fit 並給出 p 值。", "hep-statistics", ["template fits", "goodness of fit"], "hep-measurement", None, {"set": "ANA-P4-5"}),
 ("an-b-syst-1", "en", "direct", "Write the evaluation plan for the physical sources of systematic uncertainties in my cross-section measurement.", "hep-measurement", ["systematic uncertainties and their evaluation plan"], None, None, {"set": "ANA-P4-5"}),
 ("an-b-syst-2", "zh-Hant", "neighboring", "請把這些系統誤差做 covariance assembly and validation，並檢查矩陣是否半正定。", "hep-statistics", ["covariance assembly and validation"], "hep-measurement", None, {"set": "ANA-P4-5"}),
 ("an-b-cutflow-1", "en", "direct", "Design the cutflows for my dimuon selection: which cuts, in which order, and with which denominators?", "hep-measurement", ["cutflows"], None, None, {"set": "ANA-P4-5"}),
 ("an-b-cutflow-2", "zh-Hant", "neighboring", "請用 RDataFrame 寫出這個 cutflow 的程式碼，並輸出每一步的加權事件數。", "hep-computing", ["RDataFrame"], "hep-measurement", None, {"set": "ANA-P4-5"}),
 ("an-b-level-1", "en", "direct", "Should my spectrum be reported at detector level or unfolded to particle level? Help me with the observable definition.", "hep-measurement", ["observable definition"], None, None, {"set": "ANA-P4-5"}),
 ("an-b-level-2", "zh-Hant", "neighboring", "請幫我做帶正則化的 unfolding，並檢查結果的 coverage（unfolding with regularization and coverage）。", "hep-statistics", ["unfolding with regularization and coverage"], "hep-measurement", None, {"set": "ANA-P4-5"}),
 ("an-b-review-1", "en", "direct", "Here is our analysis note on the dilepton cross section; give me a verdict-first measurement review.", "hep-measurement", ["verdict-first measurement review"], None, None, {"set": "ANA-P4-5"}),
 ("an-b-review-2", "zh-Hant", "direct", "這是我們的分析筆記，請做 measurement review，先給結論再列出缺陷。", "hep-measurement", ["measurement review"], None, None, {"set": "ANA-P4-5"}),
 # hep-computing
 ("co-direct-1", "en", "direct", "My ROOT macro has a memory leak after 10^6 events; find it.", "hep-computing", ["memory leaks", "ROOT/PyROOT"], None, None, {}),
 ("co-direct-2", "en", "direct", "Split this event generation into chunks for batch submission, with resubmission and a merge that does not double count.", "hep-computing", ["batch submission, merging and recovery"], None, None, {}),
 ("co-neighbor-1", "en", "neighboring", "Is this extracted cross section physically consistent with the tree-level prediction?", "hep-theory", ["cross sections"], "hep-computing", None, {}),
 ("co-negative-1", "zh-Hant", "negative", "請幫我推導這個衰變寬度的解析式，並說明近似的適用範圍。", "hep-theory", ["decay rates", "validity domains"], "hep-computing", None, {}),
 # hep-statistics
 ("st-direct-1", "en", "direct", "Give me a Feldman-Cousins interval for zero observed events with background 0.8.", "hep-statistics", ["Feldman-Cousins", "low or zero counts"], None, None, {}),
 ("st-direct-2", "zh-Hant", "direct", "兩個實驗量測同一觀測量，有共同的系統誤差，請做 combinations across datasets。", "hep-statistics", ["combinations across datasets or experiments"], None, None, {}),
 ("st-neighbor-1", "en", "neighboring", "Which selection cuts should define my signal region?", "hep-measurement", ["event/candidate selection"], "hep-statistics", None, {}),
 ("st-negative-1", "en", "negative", "Derive the prediction for this new-physics coupling so I can fit it later.", "hep-theory", ["predictions"], "hep-statistics", None, {}),
 # hep-theory
 ("th-direct-1", "en", "direct", "Derive the tree-level e+e- -> mu+mu- cross section with explicit conventions and check the limits.", "hep-theory", ["cross sections", "conventions"], None, None, {}),
 ("th-direct-2", "zh-Hant", "direct", "請說明這個 NLO 計算的 scale envelopes 該如何給出理論誤差。", "hep-theory", ["scale envelopes"], None, None, {}),
 ("th-neighbor-1", "en", "neighboring", "Fit the coupling of my model to these published data points with their covariance.", "hep-statistics", ["fits"], "hep-theory", None, {}),
 ("th-negative-1", "en", "negative", "Write the results section of the paper from these fit outputs.", "hep-communication", ["drafting or revising paper sections"], "hep-theory", None, {}),
 ("th-selection-1", "en", "direct", "Is pi0 -> gamma gamma gamma allowed? Which rule forbids it?", "hep-theory", ["selection rules"], None, None, {}),
 ("th-selection-2", "zh-Hant", "direct", "π0 → γγγ 這個衰變允許嗎？是哪一條 selection rules 禁止它？", "hep-theory", ["selection rules"], None, None, {}),
 ("th-scheme-1", "en", "direct", "Convert the MS-bar bottom mass m_b(m_b) to the pole mass; state the schemes and the loop order.", "hep-theory", ["schemes"], None, None, {}),
 ("th-scheme-2", "zh-Hant", "direct", "請把 MS-bar 的 b 夸克質量換算成 pole mass，並說明使用的 schemes 與迴圈階數。", "hep-theory", ["schemes"], None, None, {}),
 # hep-ml
 ("ml-direct-1", "en", "direct", "Train a jet classifier in PyTorch with grouped splits by run so nothing leaks.", "hep-ml", ["grouped train/validation/test splits and leakage checks"], None, None, {}),
 ("ml-direct-2", "zh-Hant", "direct", "我的模擬太慢，想用 PyTorch 做 surrogates，並檢查 domain shift。", "hep-ml", ["surrogates", "domain shift"], None, None, {}),
 ("ml-neighbor-1", "en", "neighboring", "Is the likelihood-free inference built on my network statistically valid, with coverage?", "hep-statistics", ["coverage"], "hep-ml", None, {}),
 ("ml-negative-1", "en", "negative", "My C++ CMake build fails to link ROOT libraries.", "hep-computing", ["CMake builds"], "hep-ml", None, {}),
 # hep-ml audit WP2.1 (ML-R19): task types without a case, en and zh-Hant each
 ("ml-pml-anomaly-1", "en", "direct", "Train an unsupervised anomaly detector on background-only events to search for new physics, with signal-injection tests.", "hep-ml", ["weak supervision"], None, None, {"set": "PML"}),
 ("ml-pml-anomaly-2", "zh-Hant", "direct", "想用只含背景的事件訓練無監督的 anomaly detection 模型找新物理，並做訊號注入測試（weak supervision 相關）。", "hep-ml", ["weak supervision"], None, None, {"set": "PML"}),
 ("ml-pml-cwola-1", "en", "direct", "Set up CWoLa weak supervision: train a classifier of signal region against sidebands in data, k-folded.", "hep-ml", ["weak supervision"], None, None, {"set": "PML"}),
 ("ml-pml-cwola-2", "zh-Hant", "direct", "用 CWoLa（weak supervision）在資料中訓練訊號區對旁帶的分類器，並做 k-fold。", "hep-ml", ["weak supervision"], None, None, {"set": "PML"}),
 ("ml-pml-gnn-1", "en", "direct", "Train a graph neural network that classifies hit-graph edges for ML track finding in our tracker.", "hep-ml", ["classifiers and regressors"], None, None, {"set": "PML"}),
 ("ml-pml-gnn-2", "zh-Hant", "direct", "訓練一個圖神經網路對 hit 圖的邊做分類，用來做機器學習徑跡重建（classifiers and regressors）。", "hep-ml", ["classifiers and regressors"], None, None, {"set": "PML"}),
 ("ml-pml-decor-1", "en", "direct", "My jet tagger sculpts the background mass distribution; add mass decorrelation with DisCo and measure the sculpting.", "hep-ml", ["mass decorrelation"], None, None, {"set": "PML"}),
 ("ml-pml-decor-2", "zh-Hant", "direct", "我的 jet 標記器會扭曲背景質量分布，請加入 mass decorrelation（DisCo）並量化扭曲程度。", "hep-ml", ["mass decorrelation"], None, None, {"set": "PML"}),
 ("ml-pml-syst-1", "en", "direct", "Make my classifier robust to the jet energy scale uncertainty with systematic-aware training.", "hep-ml", ["systematic-aware training"], None, None, {"set": "PML"}),
 ("ml-pml-syst-2", "zh-Hant", "direct", "請用 systematic-aware training 讓分類器對噴流能量標度的不確定度不敏感。", "hep-ml", ["systematic-aware training"], None, None, {"set": "PML"}),
 ("ml-pml-multi-1", "en", "direct", "Train a multiclass PyTorch network that separates ttbar, W+jets and QCD events, with per-class working points.", "hep-ml", ["classifiers and regressors", "working points"], None, None, {"set": "PML"}),
 ("ml-pml-multi-2", "zh-Hant", "direct", "訓練一個多類別 PyTorch 分類器區分 ttbar、W+jets 與 QCD 事件，並為每個類別設定 working points。", "hep-ml", ["classifiers and regressors", "working points"], None, None, {"set": "PML"}),
 ("ml-pml-omnifold-1", "en", "direct", "Train the OmniFold classifiers that reweight my simulation to data at detector and particle level.", "hep-ml", ["classifiers and regressors"], None, None, {"set": "PML", "note": "training the reweighting classifiers is hep-ml; unfolding validity and coverage hand to hep-statistics (no neighbouring case: the hep-statistics description names no hep-ml exception, and changing it is out of scope)"}),
 ("ml-pml-omnifold-2", "zh-Hant", "direct", "請訓練 OmniFold 的分類器（classifiers and regressors），在偵測器層與粒子層把模擬重新加權到資料。", "hep-ml", ["classifiers and regressors"], None, None, {"set": "PML", "note": "training the reweighting classifiers is hep-ml; unfolding validity and coverage hand to hep-statistics (no neighbouring case: the hep-statistics description names no hep-ml exception, and changing it is out of scope)"}),
 ("ml-pml-surrogate-1", "en", "direct", "Replace my slow detector simulation step with neural surrogates and flag queries outside the training domain.", "hep-ml", ["surrogates"], None, None, {"set": "PML"}),
 ("ml-pml-gen-2", "zh-Hant", "direct", "用 normalizing flow 做量能器簇射的 generative models and fast simulation，並用物理量驗證。", "hep-ml", ["generative models and fast simulation"], None, None, {"set": "PML"}),
 ("ml-pml-sbi-2", "zh-Hant", "direct", "用神經後驗估計做 ML-assisted or simulation-based inference (training side)，模型參數由模擬產生。", "hep-ml", ["ML-assisted or simulation-based inference"], None, None, {"set": "PML"}),
 ("co-companion-ws-1", "en", "direct", "This CMakeLists.txt does not find ROOT when I configure the build; fix it.", "hep-computing", ["CMake builds"], None, None, {"profiles": [], "note": "ordinary work in a project that binds a companion profile through local_profile_paths: no companion preflight and no profile read"}),
 # hep-communication
 ("rc-direct-1", "en", "direct", "Check whether this INSPIRE citation really supports the 2.1% number in my draft.", "hep-communication", ["citations", "INSPIRE-HEP"], None, None, {}),
 ("rc-direct-2", "zh-Hant", "direct", "請幫我回覆審稿人的 referee reports，並修改摘要。", "hep-communication", ["referee reports", "abstracts"], None, None, {}),
 ("rc-ams-paper-1", "en", "direct", "What data period and rigidity range does the AMS-02 nitrogen flux paper report?", "hep-communication", ["what a paper states"], None, None, {"profiles": ["experiment:ams-02"], "note": "publication-record question"}),
 ("rc-ams-exists-1", "en", "direct", "A colleague cites an AMS-02 paper observing antihelium-4. Is that paper real?", "hep-communication", ["whether a paper exists"], None, None, {"profiles": ["experiment:ams-02"], "note": "publication-record question"}),
 ("rc-ams-latest-1", "en", "direct", "What has AMS-02 published most recently on cosmic-ray nuclei?", "hep-communication", ["what a named experiment published"], None, None, {"profiles": ["experiment:ams-02"], "note": "publication-record question"}),
 ("rc-ams-latest-2", "en", "direct", "Is the 2016 AMS-02 boron-to-carbon ratio paper still the latest result I should cite?", "hep-communication", ["which result is the latest"], None, None, {"profiles": ["experiment:ams-02"], "note": "currency question (T33 shape)"}),
 ("rc-ams-support-1", "en", "direct", "Does the AMS-02 hardening of the proton and helium spectra prove a second source population?", "hep-communication", ["whether a result supports a claim or interpretation"], None, None, {"profiles": ["experiment:ams-02"], "note": "claim-support question (T40 shape)"}),
 ("rc-neighbor-1", "en", "neighboring", "Is this Feynman diagram physically allowed at tree level?", "hep-theory", ["amplitudes"], "hep-communication", None, {}),
 ("rc-negative-1", "en", "negative", "Run the template fit for the paper's main result.", "hep-statistics", ["template fits"], "hep-communication", None, {}),
 # hep-statistics reinforcement (S12)
 ("st-impacts-1", "en", "direct", "Show me the pulls, constraints and impacts of the nuisance parameters after my profile likelihood fit.", "hep-statistics", ["nuisance parameters", "profile likelihood"], None, None, {}),
 ("st-lee-1", "zh-Hant", "direct", "我在質量掃描中看到 3.5σ 的局部超出，請做 look-elsewhere effects 的修正並給出全域顯著性。", "hep-statistics", ["significance and look-elsewhere effects"], None, None, {}),
 ("st-sensitivity-1", "en", "direct", "What median discovery significance should I expect for 5 signal events over 20 background, using Asimov datasets?", "hep-statistics", ["toys and asimov datasets"], None, None, {}),
 ("st-gof-1", "zh-Hant", "direct", "我的 template fits 有很多 bin 只有幾個事件，goodness of fit 該怎麼算？", "hep-statistics", ["goodness of fit", "template fits"], None, None, {}),
 ("st-bayes-1", "en", "direct", "My MCMC chains give R-hat 1.08; can I report these Bayesian posteriors?", "hep-statistics", ["bayesian posteriors (priors, samplers, convergence)"], None, None, {}),
 ("st-sweights-1", "en", "neighboring", "Fit the decay-time distribution with sWeights from my mass fit and give an uncertainty that covers.", "hep-statistics", ["unbinned fits"], "hep-measurement", None, {}),
 ("st-nsbi-1", "zh-Hant", "neighboring", "我們用神經網路估計似然比（NSBI）做推論，最後區間的 coverage 要怎麼驗證？", "hep-statistics", ["coverage"], "hep-ml", None, {}),
 ("st-publish-1", "en", "neighboring", "Prepare our likelihoods for HEPData as a background-only workspace plus signal patches so others can reuse the fit.", "hep-statistics", ["likelihoods"], "hep-communication", None, {}),
 # batch schedulers
 ("co-batch-sbatch-1", "en", "direct", "Write an sbatch job array that runs my 500 toy fits in chunks with reproducible seeds, and merge the outputs without double counting.", "hep-computing", ["Slurm and HTCondor job arrays", "batch submission, merging and recovery"], None, None, {}),
 ("co-batch-held-1", "zh-Hant", "direct", "我的 HTCondor 工作被 hold 住了，原因寫超過記憶體上限，該怎麼處理後再重新提交？", "hep-computing", ["held or evicted jobs"], None, None, {}),
 ("co-batch-evicted-1", "en", "direct", "Some of my HTCondor jobs were evicted and restarted, and now the merged histogram seems to count those chunks twice.", "hep-computing", ["held or evicted jobs", "batch submission, merging and recovery"], None, None, {}),
 ("co-batch-pilot-1", "zh-Hant", "direct", "我要在 Slurm 上跑 2000 個 chunk，記憶體和 walltime 要怎麼設定？要先跑一個 pilot 嗎？", "hep-computing", ["pilot sizing"], None, None, {}),
 ("co-batch-gpu-1", "en", "direct", "Submit my classifier training as single-node GPU jobs on our Slurm cluster, one job per learning rate, and collect the results.", "hep-computing", ["Slurm and HTCondor job arrays"], None, None, {"chain": ["hep-computing", "hep-ml"], "note": "submission is hep-computing; the model, training and validation hand to hep-ml"}),
 ("co-batch-negative-1", "en", "negative", "My 2000 toy pseudo-experiments finished on the batch cluster. Does my 95% CL Feldman-Cousins interval have the right coverage?", "hep-statistics", ["Feldman-Cousins", "coverage"], "hep-computing", None, {}),
 # journeys
 ("j01", "en", "journey", "Plan the time-dependent helium flux and He/p ratio measurement for AMS-02 across two periods.", "hep-measurement", ["exposure"], None, "J1", {"profiles": ["experiment:ams-02"], "chain": ["hep-measurement", "hep-detector", "hep-statistics", "hep-communication"]}),
 ("j02", "zh-Hant", "journey", "研究 AMS-02 RICH 的速度解析度隨電荷的變化。", "hep-detector", ["Cherenkov/RICH", "resolution"], None, "J2", {"profiles": ["experiment:ams-02"], "chain": ["hep-detector", "hep-statistics"]}),
 ("j03", "en", "journey", "Measure the corrected angular distribution at my e+e- collider with its own luminosity and response.", "hep-measurement", ["luminosity"], None, "J3", {"chain": ["hep-measurement", "hep-detector", "hep-statistics"]}),
 ("j04", "en", "journey", "Compute the tree-level cross section with all conventions stated and check it numerically.", "hep-theory", ["cross sections", "consistency checks"], None, "J4", {"profiles": [], "chain": ["hep-theory", "hep-computing", "hep-theory"]}),
 ("j05", "en", "journey", "Fold my prediction through the detector response and fit a normalization scale.", "hep-detector", ["folding a prediction through the response"], None, "J5", {"chain": ["hep-detector", "hep-statistics", "hep-communication"], "note": "T1: the prediction exists, so the chain starts at the fold (routing-contract ownership table)"}),
 ("j06", "zh-Hant", "journey", "用已發表的資料比較我的模型（comparing a model with published data），不需要偵測器細節。", "hep-theory", ["comparing a model with an experiment's published data"], None, "J6", {"chain": ["hep-theory", "hep-statistics"], "loads": "dataset records only"}),
 ("j07", "en", "journey", "Recast the published search with its efficiency maps to constrain my model.", "hep-theory", ["recasting a published analysis"], None, "J7", {"chain": ["hep-theory", "hep-detector", "hep-statistics"]}),
 ("j08", "en", "journey", "Run a convergence study of this integral and cross-check the symbolic result numerically.", "hep-computing", ["convergence and tolerance studies"], None, "J8", {"chain": ["hep-computing", "hep-theory"]}),
 ("j09", "zh-Hant", "journey", "訓練一個分類器並宣告 surrogates 的有效範圍，之後用於推論。", "hep-ml", ["surrogates"], None, "J9", {"chain": ["hep-ml", "hep-statistics"]}),
 ("j10", "en", "journey", "Draft the paper section and figures with claim-to-result links and honest status.", "hep-communication", ["claim-to-result links"], None, "J10", {"chain": ["hep-communication"]}),
 ("j11", "en", "journey", "Use our collaboration's private calibration constants from my local profile in the efficiency study.", "hep-detector", ["calibration"], None, "J11", {"chain": ["hep-detector"], "note": "local profile via project config; nothing enters the plugin"}),
 ("j12", "en", "journey", "Set up a lattice QCD global analysis of form factors.", "hep-theory", [], None, "J12", {"chain": ["hep-theory", "hep-statistics"], "limited_support": True}),
 # special categories
 ("ams-computing-1", "en", "ams-computing", "My AMS-02 reconstruction script segfaults when reading the ntuple.", "hep-computing", ["crashes"], "hep-measurement", None, {"note": "experiment name does not route; the code problem does"}),
 ("ams-computing-2", "zh-Hant", "ams-computing", "AMS 的資料處理程式在 batch submission 後合併結果重複計算。", "hep-computing", ["batch submission, merging and recovery"], "hep-measurement", None, {}),
 ("theory-no-exp-1", "en", "theory-no-experiment", "Derive the decay rate of a scalar to two fermions; no experiment involved.", "hep-theory", ["decay rates"], None, None, {"profiles": []}),
 ("recast-1", "zh-Hant", "recasting", "請重新詮釋（recasting a published analysis）這個 LHC 搜尋結果以限制我的模型。", "hep-theory", ["recasting a published analysis"], None, None, {"chain": ["hep-theory", "hep-detector", "hep-statistics"]}),
 ("out-of-v1-1", "en", "out-of-v1", "Fit cosmic-ray propagation parameters with GALPROP across all species.", "hep-statistics", [], None, None, {"limited_support": True}),
 ("out-of-v1-2", "zh-Hant", "out-of-v1", "幫我做 SMEFT 全域擬合。", "hep-theory", [], None, None, {"limited_support": True, "also_accept": ["hep-statistics"]}),  # hep-theory claims EFT global fits; both give the notice
 ("underspec-1", "en", "underspecified", "Compare the two experiments.", "ask", [], None, None, {"note": "ask which datasets and observables; never pick experiments"}),
 ("underspec-2", "zh-Hant", "underspecified", "比較這兩個實驗的結果。", "ask", [], None, None, {}),
 # EIC profile: facility, experiment, theory with no profile, underspecified
 ("eic-facility-1", "en", "direct", "Which beam species and polarizations does the EIC provide, and where are its design energies specified? I am planning a measurement there.", "hep-measurement", ["measurement"], None, None, {"profiles": ["experiment:eic"], "note": "facility module of the eic profile; design targets only, no number is shipped"}),
 ("epic-detector-1", "zh-Hant", "direct", "請說明 EIC 的 ePIC 偵測器概念：磁鐵、tracking、calorimetry、particle identification 與資料擷取。", "hep-detector", ["tracking", "calorimetry", "particle identification"], None, None, {"profiles": ["experiment:eic"], "note": "ePIC-scoped detector module only"}),
 ("eic-dis-theory-1", "en", "theory-no-experiment", "Write down the DIS variables x, y and Q^2 from the lepton and hadron four-momenta and the identity that links them to sqrt(s).", "hep-theory", ["derivations", "conventions"], None, None, {"profiles": [], "note": "generic DIS kinematics; reading any experiment profile is a loading violation"}),
 ("eic-underspec-1", "en", "underspecified", "What is the tracking resolution at the EIC?", "ask", [], None, None, {"note": "must ask which detector concept, geometry release and configuration, and whether a projection or a measurement is meant"}),
 # at least 15 cases per skill, scored separately ("set": "T3")
 ('dr-t3-1', 'en', 'direct', 'How should I align the silicon tracker with cosmic-ray and collision tracks, and check that the alignment did not bias the momentum scale?', 'hep-detector', ['calibration and alignment'], None, None, {"set": "T3"}),
 ('dr-t3-2', 'zh-Hant', 'direct', 'TOF 的時間解析度要怎麼從資料中量測？請分開核心和尾巴。', 'hep-detector', ['TOF', 'timing'], None, None, {"set": "T3"}),
 ('dr-t3-3', 'en', 'direct', 'Set up a Geant4 detector simulation of a lead-glass calorimeter test beam and compare it with the beam data.', 'hep-detector', ['detector simulation (Geant4)'], None, None, {"set": "T3"}),
 ('dr-t3-4', 'zh-Hant', 'direct', '如何用 truth matching 評估 tracking 的效率與假徑跡率？', 'hep-detector', ['truth matching', 'tracking'], None, None, {"set": "T3"}),
 ('dr-t3-5', 'en', 'direct', 'Which conditions tag and calibration version produced my reconstructed sample, and how do I record that provenance?', 'hep-detector', ['conditions and their provenance'], None, None, {"set": "T3"}),
 ('dr-t3-6', 'zh-Hant', 'direct', 'TRD 的電子與質子分離能力（particle identification）要怎麼評估？', 'hep-detector', ['TRD', 'particle identification'], None, None, {"set": "T3"}),
 ('dr-t3-7', 'en', 'direct', 'Explain signal formation and readout in a silicon strip sensor, including charge sharing between strips.', 'hep-detector', ['signal formation and readout'], None, None, {"set": "T3"}),
 ('dr-t3-8', 'zh-Hant', 'direct', '請說明 muon systems 的觸發與重建，以及 muon 動量解析度如何量測。', 'hep-detector', ['muon systems'], None, None, {"set": "T3"}),
 ('dr-t3-9', 'en', 'direct', 'Give me a parametrized electron efficiency and smearing so a theorist can recast our search.', 'hep-detector', ['parametrized response for recasting'], None, None, {"set": "T3"}),
 ('an-t3-1', 'en', 'direct', 'Set up an ABCD background estimate for the multijet background in my search and say which closure checks it needs.', 'hep-measurement', ['background estimation', 'ABCD'], None, None, {"set": "T3"}),
 ('an-t3-2', 'zh-Hant', 'direct', '我的宇宙線通量量測要怎麼計算 exposure 與 live time？', 'hep-measurement', ['exposure', 'live time'], None, None, {"set": "T3"}),
 ('an-t3-3', 'en', 'direct', 'Which systematic uncertainties should my W cross-section measurement evaluate, and how should each one be evaluated?', 'hep-measurement', ['systematic uncertainties', 'evaluation plan'], None, None, {"set": "T3"}),
 ('an-t3-4', 'zh-Hant', 'direct', '請幫我定義 Z→ee 量測的 estimand 與 observable definition。', 'hep-measurement', ['estimand', 'observable definition'], None, None, {"set": "T3"}),
 ('an-t3-5', 'en', 'direct', 'Use mass sidebands to estimate the combinatorial background under my peak.', 'hep-measurement', ['sidebands', 'background estimation'], None, None, {"set": "T3"}),
 ('an-t3-6', 'zh-Hant', 'direct', '我們要在解盲前先定 blinding policy，哪些區域要保持盲化？', 'hep-measurement', ['blinding policy'], None, None, {"set": "T3"}),
 ('an-t3-7', 'en', 'direct', 'Lay out the correction chain from raw counts to a fiducial cross section: efficiency, acceptance and luminosity.', 'hep-measurement', ['correction chains', 'acceptance'], None, None, {"set": "T3"}),
 ('an-t3-8', 'en', 'direct', 'Give me a verdict-first measurement review of a plan in which the analyst who tunes the selection also sees the blinded offset.', 'hep-measurement', ['measurement review'], None, None, {"set": "T3"}),
 ('co-t3-1', 'zh-Hant', 'direct', '用 uproot/awkward 讀取巢狀的 jagged arrays 很慢，怎麼改善 performance？', 'hep-computing', ['uproot/awkward', 'performance'], None, None, {"set": "T3"}),
 ('co-t3-2', 'en', 'direct', 'Write a run manifest that records the environment, inputs and seeds for this production.', 'hep-computing', ['environment and run manifests'], None, None, {"set": "T3"}),
 ('co-t3-3', 'en', 'direct', 'Port my event loop to RDataFrame and check that the outputs are identical.', 'hep-computing', ['RDataFrame'], None, None, {"set": "T3"}),
 ('co-cmp-crash-1', 'en', 'direct', 'My compiled ROOT analysis crashes with a segmentation violation; valgrind reports an invalid read in my code. Help me find it.', 'hep-computing', ['crashes', 'ROOT/PyROOT'], None, None, {"set": "CMP"}),
 ('co-cmp-perf-1', 'en', 'direct', 'Profile my RDataFrame job: it takes three hours per file and I need it under thirty minutes.', 'hep-computing', ['RDataFrame', 'performance'], None, None, {"set": "CMP"}),
 ('co-cmp-ode-1', 'zh-Hant', 'direct', '我用 solve_ivp 解這組 ODE，請幫我做 convergence and tolerance studies，確認結果穩定。', 'hep-computing', ['ODEs', 'convergence and tolerance studies'], None, None, {"set": "CMP"}),
 ('th-t3-1', 'en', 'direct', 'Which PDF set and alpha_s value should my NLO Drell-Yan prediction use, and how do I quote the PDF uncertainty?', 'hep-theory', ['PDFs', 'theory uncertainties'], None, None, {"set": "T3"}),
 ('th-t3-2', 'zh-Hant', 'direct', '請說明 SMEFT 的運算子基底與正規化慣例（SMEFT conventions）。', 'hep-theory', ['SMEFT conventions'], None, None, {"set": "T3"}),
 ('ml-t3-1', 'en', 'direct', 'Build a generative model for fast simulation of calorimeter showers in PyTorch.', 'hep-ml', ['generative models and fast simulation'], None, None, {"set": "T3"}),
 ('ml-t3-2', 'zh-Hant', 'direct', '我的 PyTorch 訓練在第 3 個 epoch 出現 NaN，請幫我 debugging NaNs and shapes。', 'hep-ml', ['debugging NaNs and shapes'], None, None, {"set": "T3"}),
 ('ml-t3-3', 'en', 'direct', 'Set up distributed training across four GPUs for my particle-flow network in PyTorch.', 'hep-ml', ['distributed training'], None, None, {"set": "T3"}),
 ('ml-t3-4', 'zh-Hant', 'direct', '分類器輸出的機率沒有校準，該怎麼做 calibration of model outputs？', 'hep-ml', ['calibration of model outputs'], None, None, {"set": "T3"}),
 ('ml-t3-5', 'en', 'direct', 'Train a regressor in PyTorch that predicts the jet energy correction from the jet constituents.', 'hep-ml', ['classifiers and regressors'], None, None, {"set": "T3"}),
 ('ml-t3-6', 'en', 'direct', 'Export my trained PyTorch tagger to ONNX and make sure the checkpoint reloads identically.', 'hep-ml', ['checkpoints', 'export'], None, None, {"set": "T3"}),
 ('ml-t3-7', 'zh-Hant', 'direct', '我的 DataLoader 很慢，GPU 一直在等資料，PyTorch 的 data loading 該怎麼優化？', 'hep-ml', ['data loading'], None, None, {"set": "T3"}),
 ('ml-t3-8', 'en', 'direct', 'Turn on mixed precision for my transformer jet tagger without breaking the loss.', 'hep-ml', ['mixed precision'], None, None, {"set": "T3"}),
 ('ml-t3-9', 'zh-Hant', 'direct', '神經網路回歸的 uncertainty estimation 要用 ensemble 還是 MC dropout？', 'hep-ml', ['uncertainty estimation'], None, None, {"set": "T3"}),
 ('ml-t3-10', 'en', 'direct', 'Set up simulation-based inference with a neural posterior estimator for my model parameters in PyTorch.', 'hep-ml', ['ML-assisted or simulation-based inference'], None, None, {"set": "T3"}),
 ('ml-t3-11', 'zh-Hant', 'direct', 'PyTorch 的 training loops 要怎麼寫才能完全重現？', 'hep-ml', ['training loops'], None, None, {"set": "T3"}),
 ('ml-t3-12', 'en', 'direct', 'My classifier trained on simulation underperforms on data; measure the domain shift and suggest a fix.', 'hep-ml', ['domain shift'], None, None, {"set": "T3"}),
 ('rc-t3-1', 'en', 'direct', 'Build a literature matrix of recent W mass measurements with their methods and uncertainties.', 'hep-communication', ['literature matrices and reviews'], None, None, {"set": "T3"}),
 ('rc-t3-2', 'zh-Hant', 'direct', '請幫我把分析流程畫成 diagrams，輸出可編輯的原始檔。', 'hep-communication', ['diagrams'], None, None, {"set": "T3"}),
 ('rc-t3-3', 'en', 'direct', 'Turn my thesis results into a 15-minute conference talk and a poster version.', 'hep-communication', ['talks and posters'], None, None, {"set": "T3"}),
 ('rc-t3-4', 'zh-Hant', 'direct', '幫我寫研究計畫書（proposals）的動機與方法章節。', 'hep-communication', ['proposals'], None, None, {"set": "T3"}),
 ('rc-t3-5', 'en', 'direct', 'Write handover notes for the student who takes over my analysis next month.', 'hep-communication', ['handover notes'], None, None, {"set": "T3"}),
 ('rc-t3-6', 'en', 'direct', 'Improve the captions and layout of the figures and tables in chapter 4 of my thesis.', 'hep-communication', ['captions', 'figures and tables'], None, None, {"set": "T3"}),
 ('dr-t3-neg', 'zh-Hant', 'negative', '我已有驗證過的響應矩陣，請選擇 unfolding 的正則化強度並檢查 coverage。', 'hep-statistics', ['unfolding', 'coverage'], 'hep-detector', None, {"set": "T3"}),
 ('st-t3-neg', 'zh-Hant', 'negative', "請推導這個 Z' 模型在 LHC 的截面 predictions，之後再拿去擬合。", 'hep-theory', ['predictions', 'cross sections'], 'hep-statistics', None, {"set": "T3"}),
 ('th-t3-neg', 'en', 'negative', "Set a 95% CL CLs limit on my model's coupling from published yields of 12 observed over 9.5 expected.", 'hep-statistics', ['CLs'], 'hep-theory', None, {"set": "T3"}),
 ('ml-t3-neg', 'zh-Hant', 'negative', '我的 CMake builds 在連結 ROOT 函式庫時失敗，與機器學習無關。', 'hep-computing', ['CMake builds'], 'hep-ml', None, {"set": "T3"}),
 ('rc-t3-neg', 'zh-Hant', 'negative', '這張 Feynman 圖在樹圖階是否物理上允許？', 'hep-theory', ['Feynman diagram is allowed'], 'hep-communication', None, {"set": "T3"}),
 ('co-t3-neg', 'en', 'negative', 'My code runs fine; which event selection cuts should define the signal region of my dimuon search?', 'hep-measurement', ['event/candidate selection'], 'hep-computing', None, {"set": "T3"}),
 ('an-t3-neg', 'en', 'negative', 'Train a PyTorch classifier for my signal selection with grouped train/validation/test splits by run.', 'hep-ml', ['grouped train/validation/test splits and leakage checks'], 'hep-measurement', None, {"set": "T3"}),
 # T4 (hep-communication plan): handoffs by the question asked, not by the library or the document in play
 ('rc-t4-code-1', 'en', 'negative', 'The script that produces Figure 3 of my paper crashes on the new ntuple format; fix it.', 'hep-computing', ['crashes'], 'hep-communication', None, {"set": "T4"}),
 ('rc-t4-stat-1', 'en', 'negative', 'Before I write "evidence for" in the abstract: compute the global significance of my 3.4σ local excess with the look-elsewhere effect.', 'hep-statistics', ['significance and look-elsewhere effects'], 'hep-communication', None, {"set": "T4"}),
 ('rc-t4-ml-1', 'zh-Hant', 'negative', '論文裡宣稱分類器比基線好 3%，請用不同 seed 做 uncertainty estimation，檢查這個改善是否真實。', 'hep-ml', ['uncertainty estimation'], 'hep-communication', None, {"set": "T4"}),
 ('rc-t4-det-1', 'en', 'negative', 'For the detector section of the paper, measure the tracking resolution of our silicon tracker from the data.', 'hep-detector', ['resolution'], 'hep-communication', None, {"set": "T4"}),
 ('rc-t4-review-1', 'en', 'direct', "Write the code-review part of my referee report: does the released repository do what the paper says it does?", 'hep-communication', ['referee reports'], None, None, {"set": "T4"}),
 ('rc-t4-reuse-1', 'zh-Hant', 'direct', '上次已經查證過這篇 citations 的 INSPIRE-HEP 紀錄，這次改稿能直接沿用嗎？', 'hep-communication', ['citations', 'INSPIRE-HEP'], None, None, {"set": "T4", "note": "reuse keeps the old verification date; a time-sensitive claim is rechecked"}),
 # T19: Simplified Chinese, Japanese and German
 ('t19-zhs-1', 'zh-Hans', 'direct', '请用 tag-and-probe 测量 muon 触发效率，并给出每个 bin 的不确定度。', 'hep-detector', ['tag-and-probe'], None, None, {"set": "T19"}),
 ('t19-zhs-2', 'zh-Hans', 'direct', '我想对这个能谱做 unfolding，并检查 coverage。', 'hep-statistics', ['unfolding', 'coverage'], None, None, {"set": "T19"}),
 ('t19-zhs-3', 'zh-Hans', 'direct', '请推导 e+e- → μ+μ- 的树图截面（cross sections），并写清楚 conventions。', 'hep-theory', ['cross sections', 'conventions'], None, None, {"set": "T19"}),
 ('t19-zhs-4', 'zh-Hans', 'direct', '我的 ROOT 宏在处理 10^6 个事件后出现 memory leaks，帮我找原因。', 'hep-computing', ['memory leaks'], None, None, {"set": "T19"}),
 ('t19-zhs-5', 'zh-Hans', 'direct', '请帮我改写论文的摘要（abstracts）和图注（captions）。', 'hep-communication', ['abstracts', 'captions'], None, None, {"set": "T19"}),
 ('t19-ja-1', 'ja', 'direct', 'tag-and-probe でミューオン・トリガー効率を測定し、ビンごとの不確かさを出してください。', 'hep-detector', ['tag-and-probe'], None, None, {"set": "T19"}),
 ('t19-ja-2', 'ja', 'direct', '観測事象 0、バックグラウンド 0.8 での Feldman-Cousins 区間を求めてください。', 'hep-statistics', ['Feldman-Cousins', 'low or zero counts'], None, None, {"set": "T19"}),
 ('t19-ja-3', 'ja', 'direct', 'コントロール領域（control regions）を使って、ダイレプトン測定のバックグラウンド推定（background estimation）を設計してください。', 'hep-measurement', ['control regions', 'background estimation'], None, None, {"set": "T19"}),
 ('t19-ja-4', 'ja', 'direct', 'PyTorch でジェット分類器を学習し、run ごとに分けた grouped train/validation/test splits でリークを防いでください。', 'hep-ml', ['grouped train/validation/test splits and leakage checks'], None, None, {"set": "T19"}),
 ('t19-ja-5', 'ja', 'direct', 'この NLO 計算の scale envelopes から理論誤差をどう出すか説明してください。', 'hep-theory', ['scale envelopes'], None, None, {"set": "T19"}),
 ('t19-de-1', 'de', 'direct', 'Miss die Myon-Triggereffizienz mit tag-and-probe und gib die Unsicherheit pro Bin an.', 'hep-detector', ['tag-and-probe'], None, None, {"set": "T19"}),
 ('t19-de-2', 'de', 'direct', 'Setze eine obere CLs-Grenze auf die Signalstärke aus diesen Ereigniszahlen: 12 beobachtet, 9,5 erwartet.', 'hep-statistics', ['CLs'], None, None, {"set": "T19"}),
 ('t19-de-3', 'de', 'direct', 'Mein ROOT-Makro stürzt beim Einlesen ab (crashes); bitte hilf mir beim Debuggen.', 'hep-computing', ['crashes'], None, None, {"set": "T19"}),
 ('t19-de-4', 'de', 'direct', 'Leite den Wirkungsquerschnitt (cross sections) für e+e- → μ+μ- auf Baumniveau her, mit expliziten Konventionen (conventions).', 'hep-theory', ['cross sections', 'conventions'], None, None, {"set": "T19"}),
 ('t19-de-5', 'de', 'direct', 'Prüfe, ob dieses INSPIRE-Zitat (citations) die 2,1 % in meinem Entwurf wirklich stützt.', 'hep-communication', ['citations', 'INSPIRE-HEP'], None, None, {"set": "T19"}),
 # T19: adversarial: a tool is named, the deliverable belongs to another skill
 ('t19-adv-1', 'en', 'negative', 'Using PyTorch, compute a Feldman-Cousins interval for 2 observed events over a background of 0.5.', 'hep-statistics', ['Feldman-Cousins', 'low or zero counts'], 'hep-ml', None, {"set": "T19", "variant": "adversarial"}),
 ('t19-adv-2', 'en', 'negative', 'In ROOT, decide which control regions and ABCD regions should estimate the multijet background in my search.', 'hep-measurement', ['control regions', 'ABCD', 'background estimation'], 'hep-computing', None, {"set": "T19", "variant": "adversarial"}),
 ('t19-adv-3', 'en', 'negative', "I have pyhf installed, but first derive the tree-level cross section of my Z' model with explicit conventions.", 'hep-theory', ['cross sections', 'conventions'], 'hep-statistics', None, {"set": "T19", "variant": "adversarial"}),
 ('t19-adv-4', 'en', 'negative', 'With uproot already reading my ntuples, measure the electron reconstruction efficiency with tag-and-probe and the data/MC agreement.', 'hep-detector', ['tag-and-probe', 'data/MC agreement'], 'hep-computing', None, {"set": "T19", "variant": "adversarial"}),
 ('t19-adv-5', 'en', 'negative', 'Using the MadGraph samples I already generated, set a 95% CL CLs limit on the coupling from 12 observed over 9.5 expected.', 'hep-statistics', ['CLs'], 'hep-theory', None, {"set": "T19", "variant": "adversarial"}),
 ('t19-adv-6', 'en', 'negative', 'In LaTeX, decide which systematic uncertainties my W cross-section measurement must evaluate and how.', 'hep-measurement', ['systematic uncertainties', 'evaluation plan'], 'hep-communication', None, {"set": "T19", "variant": "adversarial"}),
 # T19: quick questions (the known weak spot)
 ('t19-quick-1', 'en', 'direct', 'Quick: Feldman-Cousins or CLs for zero events?', 'hep-statistics', ['Feldman-Cousins', 'low or zero counts'], None, None, {"set": "T19", "variant": "quick"}),
 ('t19-quick-2', 'en', 'direct', 'Quick one: why does my PyROOT script crash on TFile.Open?', 'hep-computing', ['crashes', 'ROOT/PyROOT'], None, None, {"set": "T19", "variant": "quick"}),
 ('t19-quick-3', 'en', 'direct', "Quick: what's the denominator in tag-and-probe?", 'hep-detector', ['tag-and-probe'], None, None, {"set": "T19", "variant": "quick"}),
 ('t19-quick-4', 'en', 'direct', 'Quick question: should my signal region stay blinded? What blinding policy?', 'hep-measurement', ['blinding policy'], None, None, {"set": "T19", "variant": "quick"}),
 ('t19-quick-5', 'en', 'direct', 'Quick: does arXiv:2405.01234 really exist?', 'hep-communication', ['whether a paper exists'], None, None, {"set": "T19", "variant": "quick"}),
 ('t19-quick-6', 'en', 'direct', 'Quick: is e+e- -> mu+mu- through a photon allowed at tree level?', 'hep-theory', ['process or Feynman diagram is allowed'], None, None, {"set": "T19", "variant": "quick"}),
 ('t19-quick-7', 'en', 'direct', 'Quick: NaN loss after a few PyTorch steps, where do I look?', 'hep-ml', ['debugging NaNs and shapes'], None, None, {"set": "T19", "variant": "quick"}),
 # T19: multi-turn handoffs: the second turn must load the next owner
 ('t19-turns-1', 'en', 'multi-turn', 'I have truth and reconstructed energies from my calorimeter simulation; build the response matrix and state its orientation and normalization.', 'hep-detector', ['response matrices'], None, None,
  {"set": "T19", "turns": [{"prompt": "Now unfold the measured spectrum with that matrix and check the coverage.", "expected": "hep-statistics", "trigger_terms": ["unfolding", "coverage"]}]}),
 ('t19-turns-2', 'en', 'multi-turn', "Derive the tree-level production cross section of my Z' model with explicit conventions.", 'hep-theory', ['cross sections', 'conventions'], None, None,
  {"set": "T19", "turns": [{"prompt": "Now set a 95% CL CLs limit on its coupling from 12 observed over 9.5 expected.", "expected": "hep-statistics", "trigger_terms": ["CLs"]}]}),
 ('t19-turns-3', 'en', 'multi-turn', 'Fit the signal and background template yields in these histograms with Barlow-Beeston template fits.', 'hep-statistics', ['template fits'], None, None,
  {"set": "T19", "turns": [{"prompt": "Write the results paragraph for the paper from that fit, keeping its status labels.", "expected": "hep-communication", "trigger_terms": ["drafting or revising paper sections"]}]}),
 ('t19-turns-4', 'zh-Hant', 'multi-turn', '用 PyTorch 訓練我的訊號分類器，依 run 做 grouped train/validation/test splits。', 'hep-ml', ['grouped train/validation/test splits and leakage checks'], None, None,
  {"set": "T19", "turns": [{"prompt": "接著把分類器輸出加進事件選擇（event/candidate selection），並用 control regions 估計背景。", "expected": "hep-measurement", "trigger_terms": ["event/candidate selection", "control regions"]}]}),
 # ML ownership rows of docs/routing-contract.md: BDTs and event weights, quick classifier questions, ML calibration
 ('ml-own-bdt-1', 'en', 'neighboring', 'Train a BDT for my event selection and pick the working point.', 'hep-ml', ['BDTs in analyses', 'working points'], 'hep-measurement', None, {"set": "ML-OWN"}),
 ('ml-own-bdt-2', 'zh-Hant', 'neighboring', '請幫我為事件選擇訓練一個 BDT（BDTs in analyses），並決定 working points。', 'hep-ml', ['BDTs in analyses', 'working points'], 'hep-measurement', None, {"set": "ML-OWN"}),
 ('ml-own-negw-1', 'en', 'direct', 'My XGBoost BDT misbehaves with the negative event weights of my NLO samples; how should I train and evaluate it?', 'hep-ml', ['event weights including negative ones', 'BDTs in analyses'], None, None, {"set": "ML-OWN"}),
 ('ml-own-negw-2', 'zh-Hant', 'direct', '我的 XGBoost 遇到 NLO 樣本的負權重（event weights including negative ones）就出問題，BDT 該怎麼訓練與評估？', 'hep-ml', ['event weights including negative ones', 'BDTs in analyses'], None, None, {"set": "ML-OWN"}),
 ('ml-own-quick-1', 'en', 'direct', "Quick: is AUC enough to choose my jet classifier's working point?", 'hep-ml', ['working points'], None, None, {"set": "ML-OWN", "variant": "quick"}),
 ('ml-own-quick-2', 'zh-Hant', 'direct', '快速問一下：分類器的 working points 要怎麼選，只看 AUC 可以嗎？', 'hep-ml', ['working points'], None, None, {"set": "ML-OWN", "variant": "quick"}),
 ('ml-own-ecal-1', 'en', 'neighboring', 'Train a neural-network energy regression to calibrate ECAL clusters from their cell energies.', 'hep-ml', ['classifiers and regressors', 'detector signals'], 'hep-detector', None,
  {"set": "ML-OWN", "note": "the deliverable is a trained regression model, which hep-ml owns; the detector calibration chain and its validation in data stay with hep-detector"}),
 ('ml-own-ecal-2', 'zh-Hant', 'neighboring', '請用神經網路訓練 ECAL 能量回歸（classifiers and regressors），從 cell 能量校正 cluster 能量。', 'hep-ml', ['classifiers and regressors'], 'hep-detector', None,
  {"set": "ML-OWN", "note": "the deliverable is a trained regression model, which hep-ml owns; the detector calibration chain and its validation in data stay with hep-detector"}),
 # STH-T4.6: natural (non-English) prompts that quote no description wording, gap cases, and the fit half of J5
 ('st-t46-nat-1', 'zh-Hant', 'direct', '兩個實驗量測同一物理量，有共同的亮度誤差，要怎麼合併？', 'hep-statistics', [], None, None, {"set": "STH-T4.6", "natural": True}),
 ('st-t46-nat-2', 'zh-Hant', 'direct', '我觀測到 3 個事件，預期背景 1.2 個且有兩成不確定度，上限該怎麼算？', 'hep-statistics', [], None, None, {"set": "STH-T4.6", "natural": True}),
 ('st-t46-nat-3', 'zh-Hant', 'direct', '這組 MCMC 樣本的鏈混合得不好，後驗分布還能用嗎？', 'hep-statistics', [], None, None, {"set": "STH-T4.6", "natural": True}),
 ('st-t46-nat-4', 'zh-Hant', 'direct', '掃描所有質量之後，這個峰值是否仍然顯著？', 'hep-statistics', [], None, None, {"set": "STH-T4.6", "natural": True}),
 ('st-t46-nat-5', 'zh-Hant', 'direct', '用迭代貝氏方法反摺積這個能譜，迭代次數要怎麼選、誤差怎麼給？', 'hep-statistics', [], None, None, {"set": "STH-T4.6", "natural": True}),
 ('st-t46-nat-6', 'zh-Hant', 'direct', '分子和分母的計數都上百萬，各能量區間比值之間的相關誤差矩陣要怎麼算？', 'hep-statistics', [], None, None, {"set": "STH-T4.6", "natural": True}),
 ('st-t46-ratio-1', 'en', 'direct', 'Compute the per-bin ratio of these two spectra with its full covariance, including the efficiency systematic they share.', 'hep-statistics', ['covariance assembly and validation'], None, None, {"set": "STH-T4.6"}),
 ('st-t46-break-1', 'en', 'direct', 'Fit a broken power law to these published flux points with their covariance and give an interval for the break energy.', 'hep-statistics', ['fits of model parameters to published data points with their covariance'], None, None, {"set": "STH-T4.6"}),
 ('st-t46-bump-1', 'en', 'direct', 'Search for a bump on a smoothly falling background that I fit from the data, and quote the global significance.', 'hep-statistics', ['significance and look-elsewhere effects'], None, None, {"set": "STH-T4.6"}),
 ('st-t46-comb-1', 'en', 'direct', "Combine our cross-section measurement with the other experiment's; both depend on the same luminosity measurement.", 'hep-statistics', ['combinations across datasets or experiments'], None, None, {"set": "STH-T4.6"}),
 ('j05-turn-fit', 'en', 'multi-turn', 'Fold my prediction through the detector response.', 'hep-detector', ['folding a prediction through the response'], None, None,
  {"set": "STH-T4.6", "turns": [{"prompt": "Now fit the normalization of the folded prediction to the data.", "expected": "hep-statistics", "trigger_terms": ["fits that use a folded prediction"]}],
   "note": "Q9: the fold belongs to hep-detector, the fit that uses the folded prediction to hep-statistics (routing contract row 36); the inputs of j05, so the folded prediction can exist"}),
 # WP11 (ams02-skill-upgrade): cosmic-ray coverage. Self-contained prompts (no input files needed).
 # cosmic-ray interpretation
 ('wp11-interp-1', 'en', 'direct', 'Compute the B/C prediction of a simple leaky-box model, stating the spallation cross-section conventions, so I can compare it with the published AMS-02 B/C data.', 'hep-theory', ['predictions', 'conventions'], None, None, {"set": "WP11", "profiles": ["experiment:ams-02"], "note": "cosmic-ray interpretation: model prediction for a published comparison"}),
 ('wp11-interp-2', 'zh-Hant', 'direct', '高能宇宙線正電子比例上升：請比較純次級產生與 pulsar 來源的 model alternatives，並給出理論不確定度（theory uncertainties）。', 'hep-theory', ['model alternatives', 'theory uncertainties'], None, None, {"set": "WP11", "note": "cosmic-ray interpretation"}),
 ('wp11-interp-3', 'zh-Hant', 'direct', '有人宣稱 AMS-02 的反質子/質子比支持暗物質的解釋，這個結果真的支持這種說法嗎？', 'hep-communication', ['whether a result supports a claim or interpretation'], None, None, {"set": "WP11", "profiles": ["experiment:ams-02"], "note": "cosmic-ray interpretation: claim-support question"}),
 ('wp11-interp-4', 'en', 'neighboring', 'Is my diffusion-model prediction a good description of the published AMS-02 lithium flux? Compute the chi-square with the published covariance and its p-value.', 'hep-statistics', ['goodness of fit'], 'hep-theory', None, {"set": "WP11", "profiles": ["experiment:ams-02"], "note": "cosmic-ray interpretation: the prediction exists, the goodness of fit is inference"}),
 # propagation fits: hep-statistics, limited support until WP10 lands (then update this expectation)
 ('wp11-prop-1', 'en', 'direct', 'Fit the diffusion coefficient D0 and halo height L to the AMS-02 B/C ratio with its covariance, using precomputed propagation-code predictions on a parameter grid.', 'hep-statistics', ['fits of model parameters to published data points with their covariance'], None, None, {"set": "WP11", "profiles": ["experiment:ams-02"], "note": "propagation fit on tabulated predictions (WP10: in v1, synthetic-data status)"}),
 ('wp11-prop-2', 'zh-Hant', 'direct', '請用 B/C 與 Be/B 比值擬合宇宙線傳播參數（擴散係數與暈高度），並說明 D0/L 的簡併。', 'hep-statistics', [], None, None, {"set": "WP11", "note": "propagation fit on tabulated predictions (WP10: in v1, synthetic-data status)"}),
 ('wp11-prop-3', 'zh-Hant', 'direct', '我想對宇宙線傳播模型的參數（擴散指數與 Alfvén 速度）做 Bayesian posteriors 抽樣，先驗與收斂要怎麼處理？', 'hep-statistics', ['bayesian posteriors'], None, None, {"set": "WP11", "note": "propagation fit on tabulated predictions (WP10: in v1, synthetic-data status)"}),
 ('wp11-prop-4', 'en', 'direct', 'Run a profile likelihood scan of the diffusion slope in a cosmic-ray propagation fit to secondary-to-primary ratios, with the nuclear cross-section uncertainties as nuisance parameters.', 'hep-statistics', ['profile likelihood', 'nuisance parameters'], None, None, {"set": "WP11", "note": "propagation fit on tabulated predictions (WP10: in v1, synthetic-data status)"}),
 # time-series inference
 ('wp11-ts-1', 'en', 'direct', 'For the AMS-02 proton flux per Bartels rotation, build the covariance between rotations from the time-correlated systematics and test whether the variation over time is significant.', 'hep-statistics', ['covariance assembly and validation', 'significance'], None, None, {"set": "WP11", "profiles": ["experiment:ams-02"], "note": "time-series inference"}),
 ('wp11-ts-2', 'zh-Hant', 'direct', '每個太陽自轉週期的通量之間有時間相關的系統誤差，要怎麼建立相關矩陣，並檢驗通量的變化是否真實？', 'hep-statistics', [], None, None, {"set": "WP11", "natural": True, "note": "time-series inference"}),
 ('wp11-ts-3', 'zh-Hant', 'direct', '請把每日質子通量的時間序列對中子監測器計數做線性擬合，並給出 goodness of fit。', 'hep-statistics', ['goodness of fit'], None, None, {"set": "WP11", "note": "time-series inference"}),
 ('wp11-ts-4', 'en', 'direct', 'Fit a periodic modulation (amplitude and phase) to a daily cosmic-ray flux series with correlated errors, scanning the period, and quote the global significance of the best period.', 'hep-statistics', ['significance and look-elsewhere effects'], None, None, {"set": "WP11", "note": "time-series inference"}),
 ('wp11-ts-5', 'zh-Hant', 'neighboring', '請設計時間相關通量量測的時間分段，以及每個時段的 exposure 與 live time 修正。', 'hep-measurement', ['exposure', 'live time'], 'hep-statistics', None, {"set": "WP11", "note": "time-series boundary: binning and corrections are measurement design, not inference"}),
 # cross-experiment comparison
 ('wp11-xexp-1', 'en', 'direct', 'Combine the AMS-02 and PAMELA proton fluxes in their overlapping rigidity range, with a correlated normalization uncertainty, and test whether they are consistent.', 'hep-statistics', ['combinations across datasets or experiments'], None, None, {"set": "WP11", "profiles": ["experiment:ams-02"], "note": "cross-experiment comparison"}),
 ('wp11-xexp-2', 'zh-Hant', 'direct', 'AMS-02 與 DAMPE 的質子通量在 TeV 附近看起來不一致，考慮各自的能量標度誤差後，兩者的相容程度（p 值）是多少？', 'hep-statistics', [], None, None, {"set": "WP11", "natural": True, "profiles": ["experiment:ams-02"], "note": "cross-experiment comparison"}),
 ('wp11-xexp-3', 'zh-Hant', 'underspecified', '比較 AMS-02 和其他實驗的通量。', 'ask', [], None, None, {"set": "WP11", "note": "ask which species, observable, energy range and experiments; never pick them"}),
 ('wp11-xexp-4', 'en', 'direct', 'Build a literature matrix of the published proton spectral-hardening measurements from AMS-02, PAMELA, CREAM and DAMPE with the break rigidity and its uncertainty.', 'hep-communication', ['literature matrices and reviews'], None, None, {"set": "WP11", "profiles": ["experiment:ams-02"], "note": "cross-experiment comparison: literature work"}),
 # CRDB queries (owner of adapters/crdb is hep-theory per D2; the request routes by its deliverable)
 ('wp11-crdb-1', 'en', 'direct', 'Pull the published AMS-02 and PAMELA B/C points from CRDB, labelled as secondary, so I can compare my propagation-model prediction with them.', 'hep-theory', ["comparing a model with an experiment's published data"], None, None, {"set": "WP11", "profiles": ["experiment:ams-02"], "note": "CRDB query for a model comparison"}),
 ('wp11-crdb-2', 'zh-Hant', 'direct', '從 CRDB 取得 AMS-02 的 Li/C 資料點並標為次級來源，用來和我的模型預測（predictions）比較。', 'hep-theory', ['predictions'], None, None, {"set": "WP11", "profiles": ["experiment:ams-02"], "note": "CRDB query for a model comparison"}),
 ('wp11-crdb-3', 'en', 'direct', 'A CRDB entry for the AMS-02 positron flux looks different from what I remember. Which paper is it transcribed from, and what does that paper state?', 'hep-communication', ['what a paper states'], None, None, {"set": "WP11", "profiles": ["experiment:ams-02"], "note": "CRDB value checked against its primary paper"}),
 ('wp11-crdb-4', 'zh-Hant', 'ams-computing', '我的 CRDB 查詢腳本在解析 AMS-02 匯出 csv 的標頭時 crashes，請幫我除錯。', 'hep-computing', ['crashes'], 'hep-theory', None, {"set": "WP11", "note": "CRDB code problem: the code, not the database, routes"}),
 # custom ML in a measurement: hep-ml trains and picks the working point, then hands to hep-measurement
 ('wp11-ml-1', 'en', 'neighboring', 'Train an e/p classifier on TRD and ECAL variables and pick a working point for my positron flux measurement.', 'hep-ml', ['classifiers and regressors', 'working points'], 'hep-measurement', None, {"set": "WP11", "chain": ["hep-ml", "hep-measurement"], "note": "the trained model and working point are hep-ml; the selection and proton-background estimate hand to hep-measurement"}),
 ('wp11-ml-2', 'zh-Hant', 'neighboring', '請用 TRD 與 ECAL 的變數訓練電子/質子分類器並選定 working points，之後用在正電子通量量測的事件選擇。', 'hep-ml', ['working points'], 'hep-measurement', None, {"set": "WP11", "chain": ["hep-ml", "hep-measurement"], "note": "the trained model and working point are hep-ml; the selection hands to hep-measurement"}),
 # boundaries
 ('wp11-bound-dm-1', 'en', 'out-of-v1', 'Which dark-matter model explains the positron excess?', 'hep-theory', [], None, None, {"set": "WP11", "limited_support": True, "also_accept": ["hep-communication"], "note": "interpretation beyond the validated profiles: hep-theory gives the limited-support notice"}),
 ('wp11-bound-dm-2', 'zh-Hant', 'out-of-v1', '哪一種暗物質模型可以解釋正電子超出？', 'hep-theory', [], None, None, {"set": "WP11", "limited_support": True, "note": "interpretation beyond the validated profiles: hep-theory gives the limited-support notice"}),
 ('wp11-bound-bc-1', 'en', 'direct', "Which is AMS's latest B/C paper?", 'hep-communication', ['which result is the latest'], None, None, {"set": "WP11", "profiles": ["experiment:ams-02"], "note": "publication-record question"}),
 ('wp11-bound-bc-2', 'zh-Hant', 'direct', 'AMS 最新的 B/C 論文是哪一篇？', 'hep-communication', ['which result is the latest'], None, None, {"set": "WP11", "profiles": ["experiment:ams-02"], "note": "publication-record question"}),
 # v1.3 plan: BDT, RooFit/ROOT, detector design, theory domains, paper writing
 ("ml-bdt-1", "en", "direct", "Train an XGBoost BDT with 5-fold cross-training by event number; my NLO signal sample has negative weights.", "hep-ml", ["XGBoost", "event weights including negative ones"], None, None, {}),
 ("ml-bdt-2", "zh-Hant", "direct", "用 XGBoost 訓練 BDT 分辨訊號與背景，k-fold 依事件編號切，再選一個 90% 訊號效率的 working point。", "hep-ml", ["XGBoost", "working points"], None, None, {}),
 ("st-roofit-1", "en", "direct", "My RooFit fit returns covQual 1 and asymmetric MINOS errors; can I quote the result?", "hep-statistics", ["RooFit/RooStats"], None, None, {}),
 ("st-roofit-2", "zh-Hant", "direct", "加權事件的 unbinned RooFit 擬合，誤差要用 SumW2Error 還是 AsymptoticError？", "hep-statistics", ["RooFit/RooStats", "unbinned fits"], None, None, {}),
 ("co-roofit-neg-1", "en", "negative", "My RooWorkspace crashes when I import a second dataset with the same variable names.", "hep-computing", ["crashes"], "hep-statistics", None, {}),
 ("co-rntuple-1", "en", "direct", "Convert my TTree to RNTuple and run the same RDataFrame selection with systematic variations through Vary.", "hep-computing", ["RNTuple", "RDataFrame"], None, None, {}),
 ("co-teff-1", "zh-Hant", "neighboring", "TEfficiency 的通過數比總數多，程式一直報錯，怎麼修？", "hep-computing", ["histogram and TEfficiency objects"], "hep-detector", None, {}),
 ("st-teff-2", "en", "neighboring", "Which interval should I quote for a trigger efficiency with only three failing events, Clopper-Pearson or Wilson?", "hep-statistics", ["intervals and limits"], "hep-computing", None, {}),
 ("dr-design-1", "en", "direct", "Compare the magnetic field configuration and momentum resolution of the ATLAS and CMS trackers, with sources.", "hep-detector", ["sourced facts on large experiments' detectors", "tracking"], None, None, {}),
 ("dr-design-2", "zh-Hant", "direct", "設計一個在 1 TeV 時動量解析度 10% 的磁譜儀，磁場、槓桿臂與層數要怎麼取捨？", "hep-detector", ["design principles and trade-offs"], None, None, {}),
 ("ms-design-neg-1", "zh-Hant", "negative", "這個截面量測的 estimand 與 fiducial 區域要怎麼定義？", "hep-measurement", ["estimand and observable definition"], "hep-detector", None, {}),
 ("th-const-1", "en", "direct", "Which CODATA edition gives the proton mass in my kinematics, and convert 1 GeV^-2 to millibarn.", "hep-theory", ["constants"], None, None, {}),
 ("th-alphas-2", "zh-Hant", "direct", "把 αs(mZ) 用四迴圈跑到 mτ，味閾值要怎麼處理？", "hep-theory", ["schemes"], None, None, {}),
 ("th-pi0-1", "en", "direct", "Given this neutral-pion spectrum, compute the gamma-ray spectrum from pi0 decay in astroparticle physics terms.", "hep-theory", ["astroparticle physics"], None, None, {}),
 ("th-decay-2", "zh-Hant", "direct", "計算 238U 衰變鏈在 10 年後各子核的活度，有沒有達到長期平衡？", "hep-theory", ["nuclear decays"], None, None, {}),
 ("cm-numbers-1", "en", "direct", "Generate the LaTeX macros for my results table from this statistical result, with consistent numbers and units.", "hep-communication", ["numbers and units"], None, None, {}),
 ("cm-genre-2", "zh-Hant", "direct", "我要寫一篇 search 論文投 PRD，結果章節一定要有哪些內容？", "hep-communication", ["papers from results"], None, None, {}),
 ("cm-translate-1", "en", "direct", "Translate my Chinese draft abstract into English without changing the claim strength or any number.", "hep-communication", ["English or Chinese"], None, None, {}),
    # batch A, Th9: physical constants, particle and nuclide data (physical_data.py)
 ("th-a-qvalue-1", "en", "direct", "What is the Q value of the 238U alpha decay from AME2020 masses, and which edition and uncertainty should I quote?", "hep-theory", ["nuclear decays"], None, None, {}),
 ("th-a-const-2", "zh-Hant", "direct", "π⁺ 的質量要用哪一版 PDG 的數值？請附上來源、版本與不確定度。", "hep-theory", ["constants"], None, None, {}),
    # batch A, Th7: four-vector kinematics (kinematics.py)
 ("th-a-kin-1", "en", "direct", "What beam energy is the threshold for antiproton production on a proton at rest, and what is the Dalitz-plot boundary of D0 to K pi pi0?", "hep-theory", ["decay rates and widths"], None, None, {}),
 ("th-a-kin-2", "zh-Hant", "direct", "把這個四動量從質心系 boost 到實驗室系，順便算 s、t、u 與 rapidity。", "hep-theory", ["cross sections"], None, None, {}),
    # batch A (D7, D1): synthetic spectrometer test bed, propagating a calibration residual
    ("dr-a-toy-1", "en", "direct", "Simulate a toy magnetic spectrometer with a fixed seed so I can test how the efficiency and resolution of my rigidity selection change when a tracker layer is added.", "hep-detector", ["efficiency and resolution"], None, None, {}),
    ("dr-a-toy-2", "zh-Hant", "direct", "用固定亂數種子產生一組合成的磁譜儀事件，作為 detector simulation (Geant4) 之外的快速版本，檢查各時段的剛度解析度。", "hep-detector", ["detector simulation (Geant4)"], None, None, {}),
    ("dr-a-residual-1", "en", "direct", "Propagate my calibration and alignment residual, a curvature offset, into the antiproton-to-proton ratio bins and give me up and down variations.", "hep-detector", ["calibration and alignment"], None, None, {}),
    ("dr-a-residual-2", "zh-Hant", "direct", "動量尺度的 calibration and alignment 殘差要怎麼傳遞到每個能區的產額與共變異矩陣？", "hep-detector", ["calibration and alignment"], None, None, {}),
 # batch A docs track: M5 scaling class of systematics
 # batch A docs track: M5 scaling class of systematics, Th3 charge-sign-dependent modulation
 ("ms-a-scaling-1", "en", "direct", "Which of my systematic uncertainties will shrink with a four times larger control sample, and which are a floor? I need the evaluation plan for the projection.", "hep-measurement", ["the physical sources of systematic uncertainties and their evaluation plan"], None, None, {}),
 ("th-a-drift-1", "en", "direct", "Can I fit one force-field phi to positron and electron fluxes across the solar polarity reversal, or do drift effects break the approximation?", "hep-theory", ["approximations and validity domains"], None, None, {}),
 ("th-a-drift-2", "zh-Hant", "direct", "太陽磁場極性反轉前後的反質子比，用 force-field 近似還適用嗎？漂移效應要怎麼處理？", "hep-theory", ["approximations and validity domains"], None, None, {}),
 ("ms-a-scaling-2", "zh-Hant", "direct", "我的系統誤差哪些會隨控制樣本變大而縮小、哪些是下限？請幫我規劃評估方式。", "hep-measurement", ["the physical sources of systematic uncertainties and their evaluation plan"], None, None, {}),
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
TEXT = json.dumps({"note": "Routing cases. Static check: tools/check_routing_static.py. "
                           "A live check needs approval for paid model calls.", "cases": cases}, indent=1, ensure_ascii=False) + "\n"

if __name__ == "__main__":
    # --stdout prints the generated file instead of writing it (used by the tests)
    if "--stdout" in sys.argv[1:]:
        sys.stdout.write(TEXT)
    else:
        (Path(__file__).resolve().parent / "cases.json").write_text(TEXT, encoding="utf-8")
