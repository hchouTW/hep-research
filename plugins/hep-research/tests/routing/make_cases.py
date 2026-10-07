"""Writes tests/routing/cases.json (routing cases). Edit the table here, then rerun (--stdout prints instead)."""
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
 ("rc-ams-paper-1", "en", "direct", "What data period and rigidity range does the AMS-02 nitrogen flux paper report?", "research-communication", ["what a paper states"], None, None, {"profiles": ["experiment:ams-02"], "note": "publication-record question"}),
 ("rc-ams-exists-1", "en", "direct", "A colleague cites an AMS-02 paper observing antihelium-4. Is that paper real?", "research-communication", ["whether a paper exists"], None, None, {"profiles": ["experiment:ams-02"], "note": "publication-record question"}),
 ("rc-ams-latest-1", "en", "direct", "What has AMS-02 published most recently on cosmic-ray nuclei?", "research-communication", ["what a named experiment published"], None, None, {"profiles": ["experiment:ams-02"], "note": "publication-record question"}),
 ("rc-ams-latest-2", "en", "direct", "Is the 2016 AMS-02 boron-to-carbon ratio paper still the latest result I should cite?", "research-communication", ["which result is the latest"], None, None, {"profiles": ["experiment:ams-02"], "note": "currency question (T33 shape)"}),
 ("rc-ams-support-1", "en", "direct", "Does the AMS-02 hardening of the proton and helium spectra prove a second source population?", "research-communication", ["whether a result supports a claim or interpretation"], None, None, {"profiles": ["experiment:ams-02"], "note": "claim-support question (T40 shape)"}),
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
 # batch schedulers
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
 ("j05", "en", "journey", "Fold my prediction through the detector response and fit a normalization scale.", "detector-response", ["folding a prediction through the response"], None, "J5", {"chain": ["detector-response", "hep-statistics", "research-communication"], "note": "T1: the prediction exists, so the chain starts at the fold (routing-contract ownership table)"}),
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
 ("out-of-v1-2", "zh-Hant", "out-of-v1", "幫我做 SMEFT 全域擬合。", "hep-theory", [], None, None, {"limited_support": True, "also_accept": ["hep-statistics"]}),  # hep-theory claims EFT global fits; both give the notice
 ("underspec-1", "en", "underspecified", "Compare the two experiments.", "ask", [], None, None, {"note": "ask which datasets and observables; never pick experiments"}),
 ("underspec-2", "zh-Hant", "underspecified", "比較這兩個實驗的結果。", "ask", [], None, None, {}),
 # EIC profile: facility, experiment, theory with no profile, underspecified
 ("eic-facility-1", "en", "direct", "Which beam species and polarizations does the EIC provide, and where are its design energies specified? I am planning a measurement there.", "hep-analysis", ["measurement"], None, None, {"profiles": ["experiment:eic"], "note": "facility module of the eic profile; design targets only, no number is shipped"}),
 ("epic-detector-1", "zh-Hant", "direct", "請說明 EIC 的 ePIC 偵測器概念：磁鐵、tracking、calorimetry、particle identification 與資料擷取。", "detector-response", ["tracking", "calorimetry", "particle identification"], None, None, {"profiles": ["experiment:eic"], "note": "ePIC-scoped detector module only"}),
 ("eic-dis-theory-1", "en", "theory-no-experiment", "Write down the DIS variables x, y and Q^2 from the lepton and hadron four-momenta and the identity that links them to sqrt(s).", "hep-theory", ["derivations", "conventions"], None, None, {"profiles": [], "note": "generic DIS kinematics; reading any experiment profile is a loading violation"}),
 ("eic-underspec-1", "en", "underspecified", "What is the tracking resolution at the EIC?", "ask", [], None, None, {"note": "must ask which detector concept, geometry release and configuration, and whether a projection or a measurement is meant"}),
 # at least 15 cases per skill, scored separately ("set": "T3")
 ('dr-t3-1', 'en', 'direct', 'How should I align the silicon tracker with cosmic-ray and collision tracks, and check that the alignment did not bias the momentum scale?', 'detector-response', ['calibration and alignment'], None, None, {"set": "T3"}),
 ('dr-t3-2', 'zh-Hant', 'direct', 'TOF 的時間解析度要怎麼從資料中量測？請分開核心和尾巴。', 'detector-response', ['TOF', 'timing'], None, None, {"set": "T3"}),
 ('dr-t3-3', 'en', 'direct', 'Set up a Geant4 detector simulation of a lead-glass calorimeter test beam and compare it with the beam data.', 'detector-response', ['detector simulation (Geant4)'], None, None, {"set": "T3"}),
 ('dr-t3-4', 'zh-Hant', 'direct', '如何用 truth matching 評估 tracking 的效率與假徑跡率？', 'detector-response', ['truth matching', 'tracking'], None, None, {"set": "T3"}),
 ('dr-t3-5', 'en', 'direct', 'Which conditions tag and calibration version produced my reconstructed sample, and how do I record that provenance?', 'detector-response', ['conditions and their provenance'], None, None, {"set": "T3"}),
 ('dr-t3-6', 'zh-Hant', 'direct', 'TRD 的電子與質子分離能力（particle identification）要怎麼評估？', 'detector-response', ['TRD', 'particle identification'], None, None, {"set": "T3"}),
 ('dr-t3-7', 'en', 'direct', 'Explain signal formation and readout in a silicon strip sensor, including charge sharing between strips.', 'detector-response', ['signal formation and readout'], None, None, {"set": "T3"}),
 ('dr-t3-8', 'zh-Hant', 'direct', '請說明 muon systems 的觸發與重建，以及 muon 動量解析度如何量測。', 'detector-response', ['muon systems'], None, None, {"set": "T3"}),
 ('dr-t3-9', 'en', 'direct', 'Give me a parametrized electron efficiency and smearing so a theorist can recast our search.', 'detector-response', ['parametrized response for recasting'], None, None, {"set": "T3"}),
 ('an-t3-1', 'en', 'direct', 'Set up an ABCD background estimate for the multijet background in my search and say which closure checks it needs.', 'hep-analysis', ['background estimation', 'ABCD'], None, None, {"set": "T3"}),
 ('an-t3-2', 'zh-Hant', 'direct', '我的宇宙線通量量測要怎麼計算 exposure 與 live time？', 'hep-analysis', ['exposure', 'live time'], None, None, {"set": "T3"}),
 ('an-t3-3', 'en', 'direct', 'Which systematic uncertainties should my W cross-section measurement evaluate, and how should each one be evaluated?', 'hep-analysis', ['systematic uncertainties', 'evaluation plan'], None, None, {"set": "T3"}),
 ('an-t3-4', 'zh-Hant', 'direct', '請幫我定義 Z→ee 量測的 estimand 與 observable definition。', 'hep-analysis', ['estimand', 'observable definition'], None, None, {"set": "T3"}),
 ('an-t3-5', 'en', 'direct', 'Use mass sidebands to estimate the combinatorial background under my peak.', 'hep-analysis', ['sidebands', 'background estimation'], None, None, {"set": "T3"}),
 ('an-t3-6', 'zh-Hant', 'direct', '我們要在解盲前先定 blinding policy，哪些區域要保持盲化？', 'hep-analysis', ['blinding policy'], None, None, {"set": "T3"}),
 ('an-t3-7', 'en', 'direct', 'Lay out the correction chain from raw counts to a fiducial cross section: efficiency, acceptance and luminosity.', 'hep-analysis', ['correction chains', 'acceptance'], None, None, {"set": "T3"}),
 ('an-t3-8', 'en', 'direct', 'Give me a verdict-first measurement review of a plan in which the analyst who tunes the selection also sees the blinded offset.', 'hep-analysis', ['measurement review'], None, None, {"set": "T3"}),
 ('co-t3-1', 'zh-Hant', 'direct', '用 uproot/awkward 讀取巢狀的 jagged arrays 很慢，怎麼改善 performance？', 'hep-computing', ['uproot/awkward', 'performance'], None, None, {"set": "T3"}),
 ('co-t3-2', 'en', 'direct', 'Write a run manifest that records the environment, inputs and seeds for this production.', 'hep-computing', ['environment and run manifests'], None, None, {"set": "T3"}),
 ('co-t3-3', 'en', 'direct', 'Port my event loop to RDataFrame and check that the outputs are identical.', 'hep-computing', ['RDataFrame'], None, None, {"set": "T3"}),
 ('th-t3-1', 'en', 'direct', 'Which PDF set and alpha_s value should my NLO Drell-Yan prediction use, and how do I quote the PDF uncertainty?', 'hep-theory', ['PDFs', 'theory uncertainties'], None, None, {"set": "T3"}),
 ('th-t3-2', 'zh-Hant', 'direct', '請說明 SMEFT 的運算子基底與正規化慣例（SMEFT conventions）。', 'hep-theory', ['SMEFT conventions'], None, None, {"set": "T3"}),
 ('ml-t3-1', 'en', 'direct', 'Build a generative model for fast simulation of calorimeter showers in PyTorch.', 'physics-ml', ['generative models and fast simulation'], None, None, {"set": "T3"}),
 ('ml-t3-2', 'zh-Hant', 'direct', '我的 PyTorch 訓練在第 3 個 epoch 出現 NaN，請幫我 debugging NaNs and shapes。', 'physics-ml', ['debugging NaNs and shapes'], None, None, {"set": "T3"}),
 ('ml-t3-3', 'en', 'direct', 'Set up distributed training across four GPUs for my particle-flow network in PyTorch.', 'physics-ml', ['distributed training'], None, None, {"set": "T3"}),
 ('ml-t3-4', 'zh-Hant', 'direct', '分類器輸出的機率沒有校準，該怎麼做 calibration of model outputs？', 'physics-ml', ['calibration of model outputs'], None, None, {"set": "T3"}),
 ('ml-t3-5', 'en', 'direct', 'Train a regressor in PyTorch that predicts the jet energy correction from the jet constituents.', 'physics-ml', ['classifiers and regressors'], None, None, {"set": "T3"}),
 ('ml-t3-6', 'en', 'direct', 'Export my trained PyTorch tagger to ONNX and make sure the checkpoint reloads identically.', 'physics-ml', ['checkpoints', 'export'], None, None, {"set": "T3"}),
 ('ml-t3-7', 'zh-Hant', 'direct', '我的 DataLoader 很慢，GPU 一直在等資料，PyTorch 的 data loading 該怎麼優化？', 'physics-ml', ['data loading'], None, None, {"set": "T3"}),
 ('ml-t3-8', 'en', 'direct', 'Turn on mixed precision for my transformer jet tagger without breaking the loss.', 'physics-ml', ['mixed precision'], None, None, {"set": "T3"}),
 ('ml-t3-9', 'zh-Hant', 'direct', '神經網路回歸的 uncertainty estimation 要用 ensemble 還是 MC dropout？', 'physics-ml', ['uncertainty estimation'], None, None, {"set": "T3"}),
 ('ml-t3-10', 'en', 'direct', 'Set up simulation-based inference with a neural posterior estimator for my model parameters in PyTorch.', 'physics-ml', ['ML-assisted or simulation-based inference'], None, None, {"set": "T3"}),
 ('ml-t3-11', 'zh-Hant', 'direct', 'PyTorch 的 training loops 要怎麼寫才能完全重現？', 'physics-ml', ['training loops'], None, None, {"set": "T3"}),
 ('ml-t3-12', 'en', 'direct', 'My classifier trained on simulation underperforms on data; measure the domain shift and suggest a fix.', 'physics-ml', ['domain shift'], None, None, {"set": "T3"}),
 ('rc-t3-1', 'en', 'direct', 'Build a literature matrix of recent W mass measurements with their methods and uncertainties.', 'research-communication', ['literature matrices and reviews'], None, None, {"set": "T3"}),
 ('rc-t3-2', 'zh-Hant', 'direct', '請幫我把分析流程畫成 diagrams，輸出可編輯的原始檔。', 'research-communication', ['diagrams'], None, None, {"set": "T3"}),
 ('rc-t3-3', 'en', 'direct', 'Turn my thesis results into a 15-minute conference talk and a poster version.', 'research-communication', ['talks and posters'], None, None, {"set": "T3"}),
 ('rc-t3-4', 'zh-Hant', 'direct', '幫我寫研究計畫書（proposals）的動機與方法章節。', 'research-communication', ['proposals'], None, None, {"set": "T3"}),
 ('rc-t3-5', 'en', 'direct', 'Write handover notes for the student who takes over my analysis next month.', 'research-communication', ['handover notes'], None, None, {"set": "T3"}),
 ('rc-t3-6', 'en', 'direct', 'Improve the captions and layout of the figures and tables in chapter 4 of my thesis.', 'research-communication', ['captions', 'figures and tables'], None, None, {"set": "T3"}),
 ('dr-t3-neg', 'zh-Hant', 'negative', '我已有驗證過的響應矩陣，請選擇 unfolding 的正則化強度並檢查 coverage。', 'hep-statistics', ['unfolding', 'coverage'], 'detector-response', None, {"set": "T3"}),
 ('st-t3-neg', 'zh-Hant', 'negative', "請推導這個 Z' 模型在 LHC 的截面 predictions，之後再拿去擬合。", 'hep-theory', ['predictions', 'cross sections'], 'hep-statistics', None, {"set": "T3"}),
 ('th-t3-neg', 'en', 'negative', "Set a 95% CL CLs limit on my model's coupling from published yields of 12 observed over 9.5 expected.", 'hep-statistics', ['CLs'], 'hep-theory', None, {"set": "T3"}),
 ('ml-t3-neg', 'zh-Hant', 'negative', '我的 CMake builds 在連結 ROOT 函式庫時失敗，與機器學習無關。', 'hep-computing', ['CMake builds'], 'physics-ml', None, {"set": "T3"}),
 ('rc-t3-neg', 'zh-Hant', 'negative', '這張 Feynman 圖在樹圖階是否物理上允許？', 'hep-theory', ['Feynman diagram is allowed'], 'research-communication', None, {"set": "T3"}),
 ('co-t3-neg', 'en', 'negative', 'My code runs fine; which event selection cuts should define the signal region of my dimuon search?', 'hep-analysis', ['event/candidate selection'], 'hep-computing', None, {"set": "T3"}),
 ('an-t3-neg', 'en', 'negative', 'Train a PyTorch classifier for my signal selection with grouped train/validation/test splits by run.', 'physics-ml', ['grouped train/validation/test splits and leakage checks'], 'hep-analysis', None, {"set": "T3"}),
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
