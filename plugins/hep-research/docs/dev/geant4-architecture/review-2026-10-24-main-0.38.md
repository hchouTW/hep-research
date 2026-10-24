# 對照 main 0.38.0 的深度審查（2026-10-24）

> 對象：`geant4-program.md`（commit 3f8b9c1，基準 `9f08796`／0.23.0／contracts 3.5.0）
> 對照：`origin/main` `5584927`（0.38.0，contracts 3.12.0，比基準多 197 個 commit）
> 方法：四位獨立審查者（任務 A、任務 B／J15、任務 C、計畫與架構）各自對照 main 的程式碼；主要論點由主工作階段在 main 上複核（標 ✔）
> 狀態：審查紀錄；`geant4-program.md` 已於同日依本紀錄與使用者的決定（全面重寫；搜尋為 `evaluate_design.py search`；D0 採資格路徑）重新規劃

## 1. 結論

1. **main 已經有完整的探測器系統設計流程**（0.37.0–0.38.0，hep-detector，M0–M4）：design-spec／design-candidate／design-evaluation 三種產物；`contracts/design.py` 推導判定、成熟度、過時與篩選；保真度 F0–F5（F4 = 經 `check_geant4_study.py label --upgrade` 重新發出的 Geant4 研究）；`scan`／`expand`／Pareto；人工閘門 H1–H4；「絕不宣稱全域最佳」。本文件完全沒有提到這些（`evaluate_design.py`、`design.py`、design-spec、`design-geometry/1` 在全文出現 0 次）。
2. **任務 A 仍然成立，而且更急**：F4 只接受 `validated-in-scope` 的研究（`contracts/design.py:1004` ✔），A1 修正的正是這個標籤的判定。但 A1 的流程、契約與介面部分已過時（帳本與 advisory 格式、版本、重複的 core 函式、分層），並漏了一個 main 已記載的缺陷。
3. **任務 B 的 Geant4 基礎設施仍然合理，但定位要改**：main 的 F4 路徑缺一個能跑磁譜儀的 Geant4 應用，B 正好補上；然而目前的 B 不會寫出 F4 需要的欄位、J15 依規則永遠是 `unvalidated`、四種尾部來源都沒有模擬，所以 B 的結果進不了設計流程，就算進得去也只會是 `optimistic`。
4. **任務 C 照現在的寫法不能合併**：它在 main 旁邊再造一套設計系統（需求規格、設計格式、保真度名稱、需求判定、排序與「推薦設計」），而且違反 main 的規則（判定只由 `design.py` 推導、排序與 Pareto 需要成立的 `comparison_basis`、不宣稱最佳、閘門要人）。真正新的部分（自動產生候選、Geant4 多保真度搜尋、共同亂數配對比較、贏家詛咒保護、封閉測試）值得保留，應改寫成 D2 階段的「候選產生器」。
5. **main 本身有兩個問題**（應回報維護者，見 §5）：F4 的 `--label-spec` 路徑實際上無法完成；收斂閘門在缺少最細的掃描點時會用較粗的點通過。

## 2. 三個面向的評估

| 面向 | 評估 |
|---|---|
| 合理性 | A 的必要性提高（F4 依賴正確的標籤）。B 的價值提高：main 的適足表中 shower-containment、tracking-selection-efficiency、hadronic-energy-resolution、trigger-efficiency 等在 F4 以下都是 `capability.unavailable`，只有 Geant4 能提供。C 的「自動優化」與 main「不宣稱最佳、由人決定」的原則衝突，需改為產生候選、交給 `design.py` 判定 |
| 正確性 | 檔案與行號：adapter、`check_geant4_study.py`、`geant4_benchmarks.py`、`schema.py` 未變，大多數引用仍正確；`contracts/validate.py` 與帳本、版本、腳本數量、`geant4_benchmarks.py` 的函式行號需要更新（§4.2）。物理數字：附錄 A 與 `j15_design_estimates.py` 輸出一致 |
| 靈活性 | 輸出端（觀測量、summary、判定）夠一般。後端（盒狀幾何、一層巢狀、無光學）是 J15／AMS 形狀；main 的設計流程已涵蓋對撞機徑跡＋ECAL、TOF／RICH、量能器。應以「幾何種類 → realizer」作為擴充點（`element_sim`、使用者應用程式或 GDML、之後 DD4hep），並讓 C 的搜尋由 tool contract 驅動，自然與探測器種類無關 |

## 3. main 已提供、本計畫必須使用的介面

| main 的介面 | 位置 | 對本計畫的意義 |
|---|---|---|
| design-spec（REQ、分母、配分、`comparison_basis`、`pareto_axes`） | `contracts/schemas/ext_design_spec.json` | 取代任務 C 的 `detector-requirements/1` |
| design-candidate（以 `DES-*` 為鍵的子系統、`subsystem_roles`、`derived_from`＋`overrides`、每個參數的來源與每個子系統的校正） | `ext_design_candidate.json`；`contracts/vocab/core.json:203` | 取代 `detector-design/1`；基因組只當最佳化器的內部編碼，另寫解碼器 |
| 保真度 F0–F5 | `contracts/design.py:65` ✔；`system-design-workflow.md:100-105` ✔ | 任務 C 的 F0／F1／F2 名稱衝突：C 的 F0 = main 的 F1；C 的 Geant4 搜尋值在 main 沒有保真度，只是搜尋值；C 的 F2 與確認 = main 的 F4 |
| `evaluate_design.py geometry` → 研究 → `f4` | `evaluate_design.py:462-560` ✔；`design.py:988-1062` ✔ | B 必須消化 `design-geometry/1`，研究紀錄必須寫 `extension.study.results.<fom>.{value, statistical_uncertainty, model_envelope}`、`tail_sources_simulated`，並把幾何檔列在 `input_manifest` |
| 幾何對照表 `layered-spectrometer` 1.0.0 | `contracts/rules/design_geometry.json` ✔ | 只有徑跡與磁場五個欄位；沒有材料、橫向大小、磁場範圍、TOF、量能器，卻列了 shower-containment；需要 1.1.0 |
| 尾部來源 alignment、calibration-non-uniformity、noise-digitization、pattern-recognition | `design.py:64`、`1058-1059` ✔ | 四種都模擬，F4 的解析度或電荷誤判才是 `estimate`，否則是 `optimistic` |
| 參數層級的過時、`run_workflow.py --incremental` | `system-design-workflow.md:138-145` | 取代任務 C 的設計快取與部分版本規則 |
| `scan_summary`（不寫 evaluation、免孤兒規則） | `ext_computational_run.json`；`design.py:1663` | 任務 C 的搜尋族群應存成同樣形式的 `search_summary`，只把決選者 `expand` 成候選 |
| 判定、排序、Pareto（1σ 支配） | `design.py:1369-1508`、`1949-2051` | 刪除任務 C 的 `threshold` 需求判定、`order`、自訂 Pareto 與「推薦設計」 |
| 能力 `detector-design`（hep-detector） | `docs/capability-map.json:153` ✔ | 不需要新的 adapter 或能力；搜尋放在 hep-detector 的腳本（`evaluate_design.py search` 或同層腳本）；只有選用的 Ax／BoTorch 後端才算 adapter |
| schema 支援的關鍵字 | `contracts/schema.py:61-63` ✔ | 仍沒有 `maxItems`／`maximum`／`exclusiveMaximum`／`uniqueItems`；A2.7 的規劃仍需要，且 `layered_sim/spec.schema.json` 另用 `oneOf`、`not` |

## 4. 發現

嚴重度：阻擋（不改就不能開始或不能合併）、主要、次要。

### 4.1 跨部與計畫（§P、§R）

| # | 嚴重度 | 位置 | 問題 | 建議 |
|---|---|---|---|---|
| P1 | 阻擋 | §P.7（新增） | 偵測器層級的 Geant4 研究（解析度、電荷誤判、簇射包含）沒有參考 benchmark，依 `geant4-study-protocol.md` 永遠無法 `validated-in-scope`，因此永遠不算 F4 | 新增待決事項 D0（擋 B3、C2）：(a) 偵測器層級的資格路徑（材料範圍已驗證＋磁場與重建的驗證）；或 (b) `design.py` 允許未驗證的 F4 只用於篩選、不用於合規 |
| P2 | 阻擋 | §P.0、§P.3、§C.0、§C.1 | 保真度名稱與 main 衝突 | 全文採用 main 的 F0–F5；C 的 Geant4 搜尋值不稱保真度 |
| P3 | 主要 | §P.4、§R.3.1、§R.9.1 | `adapters/detector-design/` 與 adapter 的定義不符（「連接外部工具」，`adapter-authoring.md:3-4`），main 把設計流程放在 hep-detector 腳本＋`contracts/design.py` | 搜尋放在 hep-detector 腳本；刪除 detector-design adapter 的版本序列 |
| P4 | 主要 | §P.7 第 11、12、13 項 | 已由 main 決定：能力擁有者是 hep-detector；入口是 hub 連結、不改 SKILL.md 描述（CHANGELOG OQ-01）；`extension.design_search` 應改為類似 `scan_summary` 的 run 欄位 | 標為已由 main 決定 |
| P5 | 主要 | §P.0 階段圖 | C 不再需要依賴 A；B 必須提供 F4 介面 | 見 §6 新階段圖 |
| P6 | 次要 | 文件標頭、§P.5 | 基準 contracts 3.5.0 已過時 | 基準改為 3.12.0；CVn 在發布時才定（CV1 ≥ 3.13.0） |
| P7 | 次要 | §P.8 | main 兩天內從 3.5.0 到 3.12.0；`dependencies.py` 已改為參數綁定時只警告 | 新增風險：rebase 的頻繁變動、共用檔案 `validate.py`／`dependencies.py`；建議在 `contracts/rules/registry.json` 新增 `geant4` 影響群組 |
| P8 | 次要 | §P.10.3 第 8 條 | 獨立審查的隔離由 `independent-review-spec.md:670-678` 規定（主機設定），不是 worktree | 審查的隔離引用該規格；worktree 只用於實作 |
| P9 | 次要 | §R.2.2、§A.3 第 3 條、§C.3 第 1 條 | core 的必要依賴本來就含 numpy、scipy（`requirements-core.txt`） | 「只用標準函式庫」寫成刻意的選擇，不是限制 |
| R1 | 主要 | §R.4、§R.5、§R.6 | 設計理由與 main 的決定不同：保真度命名、判定擁有權、全域最佳、審查閘門、參數層級過時、增量重跑 | 第 5 部補一節「與 main 設計流程的關係」，並刪去被取代的理由 |

### 4.2 任務 A

| # | 嚴重度 | 位置 | 問題 | 建議 |
|---|---|---|---|---|
| A1 | 主要 | A1.8；§P.3 A1 列 | **漏掉的缺陷 D11**：收斂閘門用「已提供的 summary 中最細的兩個值」，缺少最細的掃描點時以較粗的點通過（`check_geant4_study.py:341-348` ✔；protocol 第 93–95 行 ✔ 已記載） | 新增 D11：每個宣告的掃描值都必須有 summary，否則 `incomplete`；「最細兩個」指宣告值中最細的兩個 |
| A2 | 主要 | A1.14 帳本 | 帳本格式已改：一筆只修一件事；需要 `independence`、`commits`、`parent_records`、`mutants`；S1 要有封閉形式時的 C4 與每筆的 review 簽核；S3 放在 `documentation_fixes`（`maintenance.md:126-237`） | 把 `variance-method` 拆成 batch-means SE、精確低計數區間、MPV 估計三筆；D1、D2 同樣拆開；D6／D7 進 `documentation_fixes`；D8 不改數字或判定，移出帳本；以 `tools/scifix_ledger.py report` 檢查 |
| A3 | 主要 | A1.14 advisory | 格式改為 `hep-research-scifix-advisory/2`，以 `applies_to.match` 群組比對，每組要有可區分的條件（`maintenance.md:252-283`）；最新編號 SFA-2026-038 | 改寫成 match 群組；編號改為 -039、-040；影響範圍 0.20.0 至合併前最後一版；advisory 範圍也要涵蓋 F4 design-evaluation（它們依賴錯誤的標籤） |
| A4 | 主要 | §A.3 第 3 條、§A.4.5、§P.4、附錄 C | `core/stats/poisson_diagnostics.py:162` 已有 Garwood 區間 ✔（基準時就有）；`core/stats/toy_ensemble.py:60` 已有 SHA-256 種子推導、`:160`／`:189` 已有 `coverage`、`coverage_gate` | 依 R3 重用：不新增第二個 Garwood；`seeds.py` 說明 H 與 `toy_seed` 的關係或合併；A1.15 的覆蓋率 toy 經 `coverage_gate` 執行 |
| A5 | 主要 | A1.5、A2.7 | `core/` 只能匯入 `core`（`check_layering.py:4`），無法使用 `contracts/schema.py` | 擇一：驗證放在呼叫 `contracts.schema` 的 adapter／skill 腳本；或把 summary schema 放到 `contracts/schemas`；不在 `core` 另寫驗證器 |
| A6 | 主要 | 缺：F4 的消費端 | `evaluate_design.py f4` 呼叫 `label --upgrade` 時沒有傳 `--run-record`，`label` 必然拒絕（見 §5）；`label` 寫出的紀錄沒有 `results`、`tail_sources_simulated`；`f4` 把任何非零結束碼都當 `failed` | A1 改變 `label` 結束碼前要讓 `f4` 把 3 對應為 `incomplete`；新增 `--label-run-record` 轉傳；與維護者決定由 A1 或後續小階段寫出 `results` 與尾部來源；把 `contracts/design.py`、`evaluate_design.py`、`system-design-workflow.md` 加入檔案清單 |
| A7 | 主要 | A1.1 | F4 的三個 figure of merit 中，shower-containment 在 A1 是 sanity，其他兩個沒有對應的 kind | 說明 CV1 下沒有 F4 figure of merit 能 `validated-in-scope`，直到 B2 加入類別；定義 `observable_kind` → figure of merit 的對應 |
| A8 | 主要 | A1.2；§A.0 第 3 條 | 版本門檻「3.5.0 或以下」已不對（main 3.12.0，J14 研究紀錄已以 3.12.0 寫出）；原型寫死 3.6.0 會把 CV1 追溯套用到 3.6–3.12 的紀錄 | 改為「低於 CV1（目前 ≤ 3.12.x）」；原型的門檻要換掉 |
| A9 | 次要 | A1.6、A1.10 | F4 把純量不確定度讀成覆蓋率 0.6827 的高斯（`design.py:1050-1052`）；A1 的 SE 有 K−1 = 15 自由度（68.27 % 半寬約 1.03·SE）；低計數分支沒有 SE | `statistical_uncertainty` 定義為 68.27 % 的 t 半寬；精確分支寫出不對稱的 `uncertainty`（需改 `f4`）；`model_envelope` 取變化表的 [min, max] |
| A10 | 次要 | A2.7 | `layered_sim/spec.schema.json` 另用 `oneOf`、`not`；`output.schema.json` 不是 JSON Schema | 實作或限定掃描範圍；豁免 `output.schema.json`；新 schema 不用 `uniqueItems` |
| A11 | 次要 | A1.12 | `ext_computational_run.json` 的 `study` 是開放物件；3.11.0 新增 `argv`、`script_sha256`、`parameter_digest`、`scan_summary` | `study` 若加結構要保持開放（`results`、`tail_sources_simulated` 選用）；`geant4_run.py run` 也寫 `argv`、`script_sha256`、`versions.plugin_release` |
| A12 | 次要 | A1.4 | `cmd_label` 已用 `evidence_records[].role = "Geant4 run"`（`check_geant4_study.py:623`） | 新欄位改名 `simulation.evidence_role` 或統一意義 |
| A13 | 次要 | §A.8、§A.1 | main 新增 `tools/check_wiring.py`、`ci_plan.py`、`scifix_ledger.py`、`test_scifix_schemas.py`、tool contract 對 `--help` 的檢查、`test_cli_robustness.py:212` 對 `adapters/*/assets/*.py` 的掃描 | 加入檢查清單；`summary_from_csv.py` 登錄 `MISSING_FILE_ARGS`；10⁴ 次 toy 的測試放慢速層 |
| A14 | 次要 | §A.7 | `core/__init__.py:2` `CORE_VERSION = "1.0.0"` 依 SemVer；`core/OWNERS.json` 要求超過一個頂層使用者 | 提升 `CORE_VERSION`（minor）；`OWNERS.json` 登錄 `stats` 新檔與 `simulation` 模組並指名第二個使用者 |
| A15 | 次要 | 引用 | `validate.py` 行號移動：`_scope_inside()` 349→351、`_study_upgrade` 395／419→397／421、`GEANT4_UPGRADE_FROM` 346→348；`DetectorScriptCount` 21→23；advisory 最新 -037→-038 | 更新；其他引用（`check_geant4_study.py`、`geant4_benchmarks.py` 多數、`geant4_run.py`、`layered_sim.cc`、`Actions.cc`、`engine.py:381`）在 main 上仍正確 |

### 4.3 任務 B 與 J15

| # | 嚴重度 | 位置 | 問題 | 建議 |
|---|---|---|---|---|
| B1 | 阻擋 | B2.2–B2.3 | main 上沒有任何程式寫出 `extension.study.results` 或 `tail_sources_simulated`；`label --write` 從頭重建紀錄，`study` 區塊沒有這些欄位，`input_manifest` 也沒有幾何檔（`check_geant4_study.py:584-617` ✔） | B2：`label` 新增 `--results`、`--geometry`，保留 `results`、尾部來源與幾何檔；新增 `geometry → 研究 → label --upgrade → f4` 的端到端測試 |
| B2 | 阻擋 | §B.0 決策 4、§B.3 第 6 條 | J15 依規則是 `unvalidated`，F4 不計；升級需要涵蓋研究範圍的 reference benchmark，B2.4 只加 verification 與 sanity | 把 J15 分成「驗證載體」（維持 `unvalidated`）與候選 F4 研究；新增一個徑跡用的 reference benchmark（例如孤立 Si 片中的多重散射角寬度，對照 PDG Highland／Lynch–Dahl，附負對照）；宣告剛度與粒子的範圍維度（並見 P1） |
| B3 | 主要 | §B.4.1、B1.3、B2.1 | 四種尾部來源都沒有模擬，且只記錄主粒子的穿越 | B2 把尾部來源做成可切換的重建階段：每個 run 抽樣的錯位與對準後殘差；strip pitch、門檻、效率、雜訊 hit 與分群；所有徑跡的 hit 指派；各區磁場尺度的誤校正。誠實寫出 `tail_sources_simulated`（沒有就寫空陣列） |
| B4 | 主要 | B1.1 | `design-geometry/1` 只有五個徑跡與磁場欄位；`mapping_version` 只允許 1.0.0 | 候選設計是唯一真實來源；`design-geometry/1` 由它產生；`element_sim.spec/1` 由幾何檔確定性推導（新增 `geant4_run.py from-geometry`），兩者都進 `input_manifest`；mapping 1.1.0（契約變更）加入徑跡材料與面積、磁場區範圍、`tof` 與 `calorimetry-em` 角色的欄位 |
| B5 | 主要 | B3.8；B1.7 剛度網格 | 每個候選只有一個 `geometry_ref`，每個幾何檔只對應一個 figure of merit，`results.<fom>` 不分分母；第二次 `geometry` 會覆蓋 `geometry_ref`（推論，未執行） | B3 每個（figure of merit, 分母）一份研究；或請 main 讓 `results` 以分母為鍵並允許多個幾何檔 |
| B6 | 主要 | B3.8 | F4 一律寫對稱高斯不確定度；電荷誤判是計數型（`counting: true`） | 電荷誤判用計數估計與精確區間；向 main 提出 F4 需支援不對稱或精確不確定度 |
| B7 | 主要 | B3.8 | 文件的解析度是中央 68 % 半寬；`momentum-resolution-core` 是高斯核心 | 宣告一個核心估計（例如迭代 ±2σ 擬合）為 `simulation-observables/1` 項目，並把定義寫進研究區塊 |
| B8 | 次要 | B3.4 | 模型包絡是 [lo, hi]，兩端分別判定（`design.py:1310-1316`） | 徑跡加入多重散射模型變化（EM opt0 對 opt4、Urban 對 WentzelVI）；變化表轉成包絡並保留兩端的標準誤 |
| B9 | 次要 | B3.4 | protocol §6：π 在 12 GeV 以下是同一模型，核子在 1.5–12 GeV（`geant4-study-protocol.md:166-168`） | 更正「π 在 3 GeV 以下」 |
| B10 | 次要 | §B.1、B1.6、B3.7 | `MISSING_FILE_ARGS` 中 `geant4_run.py` 在第 153 行；腳本數 23；`geant4_benchmarks.py` 函式行號是 232／278／311／347（基準時就是），不是 233／284／325／365；protocol §6 從第 161 行開始 | 更新 |
| B11 | 次要 | 附錄 A | B／N 表未由程式印出（審查者以比例縮放核對：MDR 1066、1269 GV；散射項 4.47 %） | 讓 `j15_design_estimates.py` 印出這張表 |
| B12 | 次要 | §B.4.2、B3.2 | main 已有 F1／F2：`tracker_resolution`、`toy_spectrometer`（F2）、`design_estimates.py infield-acceptance` | 手算比較改為對 J15 候選執行 `evaluate_design.py run` F1、F2 |

數字複核：程式印出的值與附錄 A、§B.4.2 一致（MDR 1172.3 GV；A₄／A₆／A₈ = 81.0／66.96／57.17；六個接受度門檻；場檢查網格；TOF 1.84／2.31／3.46 %；上游 11.32 % X₀；18.41 X₀；每點 392 與 5,000 個事件）。

### 4.4 任務 C

| # | 嚴重度 | 位置 | 問題 | 建議 |
|---|---|---|---|---|
| C1 | 阻擋 | §C.1、§C.4.5、§P.0 | 保真度名稱衝突（同 P2） | 同 P2 |
| C2 | 阻擋 | §C.4.7、§C.4.8、C2.4 | 自行寫 `requirements[].verdict`（met／not-met／unresolved）；main 規定判定只由 `design.py` 推導、絕不手寫（workflow 第 3–4、149–150、203 行） | 刪除需求判定；決選者的判定由 `evaluate_design.py report` 推導 |
| C3 | 阻擋 | §C.4.7、C2.4、§C.0 | 「推薦設計」、`order`、自訂 Pareto；main 的排序只依 expected-precision，Pareto 必須含 expected-precision，支配需超過合併的 1σ，且絕不宣稱最佳；OQ-04 首版不排序 | 刪除；搜尋的前緣只是「搜尋階段的、無約束力的」前緣；比較用 main 的 `pareto()` |
| C4 | 主要 | §C.4.3、C1.1 | design-spec 已有需求、分母、`comparison_basis`、`pareto_axes`；範圍由 H1／H2 人工確認 | 刪除 `detector-requirements/1`；讀目前的 design-spec；`confirmed_by_user` 改為 H1／H2 紀錄；需求變更是新 spec 版本＋`requirement-change` 紀錄 |
| C5 | 主要 | §C.4.4 | 候選是以 `DES-*` 為鍵的子系統圖；參數要有來源、子系統要有校正；`overrides` 能加不能刪子系統 | 基因組只作內部編碼＋解碼器；採 main 的粒度（一個 `tracking` 子系統，陣列參數）；目錄對應角色（magnet-region→bending、tof-layer→tof、calorimeter-*→calorimetry-em／had、passive→`passive_x_over_x0`）；拓撲去掉子系統時用獨立候選 |
| C6 | 主要 | §C.4.4「實現」、C1.3 | `evaluate_design.py geometry` 已從候選產生研究幾何 | `realize()` 改為 `element_sim` 的第二個對照表（B 擁有的契約變更） |
| C7 | 主要 | §C.4.6、C2.2 | 一個 artifacts_dir 是一個設計，其中每個候選都會被彙整；只有進入比較的點才 `expand`（RSK-04） | 10⁴ 的搜尋族群不放進 artifacts_dir，存成一個 `search_summary` run；只 `expand` 決選者 |
| C8 | 主要 | §P.4、§C.0、§C.3 | 同 P3 | 同 P3 |
| C9 | 主要 | C1.7、§P.7 第 12 項 | 設計流程已有路由（hub 頁連到 workflow；routing-contract 已有案例） | 刪除 `detector-design-search.md` 與 SKILL.md 的一行；在 `system-design-workflow.md` 新增「D2 自動產生候選」一節 |
| C10 | 主要 | §C.4.8、C2.6 | 沒有規則把確認的種子與搜尋的種子綁在一起 | 定義 `search_summary`（類似 `scan_summary`，免孤兒規則）；`design.py` 新增一條：run 或研究的種子出現在搜尋摘要中的 evaluation 是 `design.contract_mismatch`（取代 CV3 的角色規則） |
| C11 | 主要 | §C.0、§C.9 | main 已涵蓋對撞機徑跡＋ECAL、TOF／RICH、量能器 | 「不做」只限 C 的 Geant4 部分；在 F1／F2 由 tool contract 驅動時搜尋本身與探測器種類無關 |
| C12 | 次要 | §C.4.7 | main 每個 figure of merit 用 `coverage_cl`，沒有多重比較修正 | 選擇感知的覆蓋率作為 `design.py` 或適足表的提案，與 hep-statistics 一起審查，不另建判定引擎 |
| C13 | 次要 | §C.4.3、§C.3 第 7 條 | 預算量只有 mass、power、channel_count、data_rate；cost 沒有評估器 | cost 是 `capability.unavailable`，不能當目標 |

**仍然有價值、main 沒有的部分：** 基因組與 NSGA-II、Sobol、超體積；Geant4 多保真度的搜尋值；共同亂數與配對比較（含 G-C2a）；贏家詛咒與搜尋規模的保護；`values` 分位數；封閉測試（DTLZ2、平面配置、結構選擇）；`proposer: llm` 併入參數來源 `proposal`。

## 5. main 本身的問題（建議回報維護者）

1. **F4 的 `--label-spec` 路徑無法完成。** `evaluate_design.py:503-506` ✔ 呼叫 `check_geant4_study.py label --upgrade` 時沒有 `--run-record`，`label` 因此必然以「no run record to reference as evidence」拒絕（`check_geant4_study.py:544-569` ✔）；即使通過，重建的紀錄也沒有 `results` 與 `tail_sources_simulated`（`:584-617` ✔），接著在 `evaluate_design.py:530-532` 失敗。測試只用合成紀錄（`tests/skills/hep_detector/test_design_m2.py`），沒有涵蓋這條路徑。
2. **收斂閘門可用較粗的點通過**（即 A1 的新缺陷 D11）。protocol 已記載並要求使用者自行補齊，但程式沒有擋。

## 6. 建議的新階段圖

```
D0 維護者決定：偵測器層級研究如何成為 F4（擋 B3′、C2′）

A1′ sci-fix（CV1）：D1–D11；帳本與 advisory 新格式；重用 core 既有函式；
    label 結束碼與 f4 一致；advisory 涵蓋 F4 evaluation
 └▶ A2 g4sim、per-event 種子、邊界產物（基本不變）
     └▶ B1′ element_sim ＋ from-geometry（design-geometry/1 → element_sim.spec/1）；
           所有帶電徑跡的 hit；分區磁場
         └▶ B2′ simreco ＋ 尾部來源（錯位、數位化與雜訊、hit 指派、磁場誤校正）；
                label 寫出 results／tail_sources_simulated／幾何檔；
                徑跡 reference benchmark；mapping 1.1.0（CV2）
             ├▶ B3′ J15 作為設計專案：design-spec＋候選 → F1、F2 → 每個（fom, 分母）的 F4
             └▶ C2′ Geant4 搜尋值、配對比較；決選者以新種子做 F4 確認

C1′ 候選產生器（hep-detector 腳本）：讀 design-spec 與基礎候選，
    以 main 的 F1 tool contract 在行程內評估，寫 search_summary，expand 決選者
    —— 不依賴 A，可先開始
C3′ 範例：在 Example A（磁譜儀）與 Example B（對撞機徑跡＋ECAL）上執行搜尋；
    選用的 Ax／BoTorch 後端才是 adapter
```

## 7. 需要決定的事項

1. 是否依 §6 重寫 `geant4-program.md`（中英兩版），包括把任務 C 改為 D2 候選產生器、刪除與 main 重複的部分。
2. D0：偵測器層級 Geant4 研究成為 F4 的路徑（維護者決定；文件可先列出選項）。
3. §5 的兩個 main 問題是否另外回報（issue 或交給維護者）。
4. 任務 C 的搜尋放在 `evaluate_design.py search` 子命令，還是同層的新腳本 `design_search.py`。
