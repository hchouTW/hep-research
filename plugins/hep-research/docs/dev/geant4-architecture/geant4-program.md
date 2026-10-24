# Geant4 模擬研究、J15 最小磁譜儀與自動產生設計候選：整合文件

> 文件類型：計畫、實作規格與設計理由的整合文件（給執行的 agent、審查者與維護者）。狀態：待使用者與維護者核准
> 基準：hep-research `main` 的 `5584927`（0.38.0），contracts 3.12.0，adapter geant4 0.1.0（自 `9f08796` 起未變），Geant4 11.4.3
> 日期：2026-10-24
> 語言：繁體中文原文；英文版 [`geant4-program.en.md`](geant4-program.en.md) 內容相同。兩者不一致時以中文為準，並同時修正英文
> 與 main 的關係：本計畫接上 main 的探測器系統設計流程（hep-detector，`skills/hep-detector/references/system-design-workflow.md`、`contracts/design.py`、`evaluate_design.py`）；需求、候選、證據與判定都用 main 的產物與規則
> 執行環境：**每個階段都在自己的 isolated git worktree 中執行**（§P.10），不修改主要 checkout 或其他 worktree

## 如何使用本文件

**給執行的 agent：**
1. 讀 §P.0（階段一覽）、§P.10（在 isolated worktree 中執行）、§P.6（閘門）、§P.4（介面擁有權）。
2. 依 §P.10.2 為你的階段建立並確認 isolated worktree（`.claude/worktrees/geant4-<階段>`，分支 `worktree-geant4-<階段>`，基底為含前置階段的最新 `origin/main`）；之後所有步驟都在其中進行。
3. 讀 main 的 `skills/hep-detector/references/system-design-workflow.md`（設計流程、保真度、閘門），它是第 3、4 部的前提。
4. 讀你的階段所屬那一部的任務卡（§A.0、§B.0 或 §C.0），再讀該部的 §1–§4 與你的階段的工作項及驗收清單。
5. 需要某條規則的理由時，才讀第 5 部。
6. 本文件約 2,800 行：依目錄的節號分段讀取（例如搜尋 `## §A.5`），不要一次讀完。

**各部的權威範圍：**

| 部 | 節號 | 內容 | 權威範圍 |
|---|---|---|---|
| 第 1 部 計畫總覽 | §P | 評估、原則、階段、介面擁有權、命名、閘門、待決事項、風險、執行環境 | 階段的順序與依賴、編號、版本代號、介面擁有權、閘門、待決事項、執行環境 |
| 第 2 部 任務 A | §A | A1、A2 的工作項與驗收；共用的硬性限制（§A.3）與檢查（§A.8） | 這兩個階段的內容與驗收 |
| 第 3 部 任務 B | §B | Geant4 F4 評估器與 J15 設計專案；B1、B2、B3 的工作項與驗收 | 這三個階段的內容與驗收；J15 的數值 |
| 第 4 部 任務 C | §C | 自動產生設計候選；C1、C2、C3 的工作項與驗收 | 這三個階段的內容與驗收 |
| 第 5 部 設計理由 | §R | 從實際實驗得到的設計依據、架構、與 main 設計流程的關係、被取代的設計 | 只說明理由；與第 2–4 部衝突時以第 2–4 部為準並回報 |

**編號：**
- 節：「§A.8」是第 2 部（任務 A）的第 8 節，「§P.10.2」是第 1 部的 10.2 節，「§B 附錄 A」是第 3 部的附錄 A。
- 工作項：「A1.6」「B2.1」「C2.4」（階段.序號），在全文中唯一。
- 契約變更：以擁有的階段命名為 CV-A1、CV-B2、CV-C1、CV-C2，號碼在發布時依合併順序決定（都 ≥ 3.13.0）；「C1」「C2」單獨出現時只指階段。
- 保真度：一律是 main 的 F0–F5（F0 啟發式、F1 解析 tool contract、F2 toy MC、F3 response／expected precision、F4 重新發出為 `validated-in-scope` 的 Geant4 研究、F5 量測）；搜尋中的 Geant4 短 run 只產生「搜尋值」，沒有保真度。
- 第 2–4 部的結構相同：§X.0 任務卡、§X.1 名詞與檔案、§X.2 前提與提供的介面、§X.3 硬性限制、§X.4 設計摘要、§X.5 起每個階段一節（工作項與驗收清單），之後是契約與版本、檢查、不做與延後、待決事項與風險、執行步驟、附錄。

**整合紀錄：** 2026-10-23 由原本分散的 `plan.md`、`task-a-core.md`、`task-b-j15.md`、`task-c-design-search.md`、`architecture.md`（與各自的英文版）合併而成，內容不變，只改寫節號與交叉引用；舊檔已移除。各部的版本歷程保留在該部的附錄。設計數值的計算程式（`gate_operating_characteristics.py`、`j15_design_estimates.py`、`design_search_closure.py`）仍是同一資料夾中的獨立檔案。

**重新規劃紀錄：** 2026-10-24 對照 main 0.38.0 審查（[`review-2026-10-24-main-0.38.md`](review-2026-10-24-main-0.38.md)）後，依 main 的探測器系統設計流程重新規劃：任務 B 成為 F4 的 Geant4 評估器，J15 成為設計專案，任務 C 成為 `evaluate_design.py search` 候選產生器；詳見 §P.1 與 §P.11。

## 目錄

- **第 1 部　計畫總覽（§P）**
  - §P.0 一頁摘要
  - §P.1 評估：問題與處理
  - §P.2 規劃原則
  - §P.3 階段的內容與驗收（摘要）
  - §P.4 介面擁有權
  - §P.5 命名與編號
  - §P.6 階段閘門
  - §P.7 待維護者決定的事項（合併清單）
  - §P.8 跨任務的主要風險
  - §P.9 文件地圖與權威分工
  - §P.10 執行環境：isolated worktree
  - §P.11 版本歷程
- **第 2 部　任務 A：正確性修正與邊界產物（§A）**
  - §A.0 任務卡
  - §A.1 名詞與檔案
  - §A.2 前提與提供的介面
  - §A.3 硬性限制
  - §A.4 設計摘要
  - §A.5 階段 A1：正確性修正（contracts CV-A1，sci-fix）
  - §A.6 階段 A2：共用標頭與邊界產物（geant4 adapter 0.2.0）
  - §A.7 契約與版本
  - §A.8 每個階段結束時的檢查
  - §A.9 不做與延後
  - §A.10 待決事項與殘餘風險
  - §A.11 建議的執行步驟
  - §A 附錄 A：統計規格彙整
  - §A 附錄 B：數值
  - §A 附錄 C：基準核對值（`9f08796`；2026-10-24 依 `5584927` 重新核對）
  - §A 附錄 D：出處
  - §A 附錄 E：版本歷程
- **第 3 部　任務 B：`element_sim`、重建與 J15 最小磁譜儀（§B）**
  - §B.0 任務卡
  - §B.1 名詞與檔案
  - §B.2 前提與提供的介面
  - §B.3 硬性限制
  - §B.4 J15 的設計
  - §B.5 階段 B1：`element_sim`、事件檔與幾何推導（geant4 adapter 0.3.0）
  - §B.6 階段 B2：重建與 F4 介面（geant4 adapter 0.4.0、contracts CV-B2）
  - §B.7 階段 B3：J15 設計專案
  - §B.8 契約與版本
  - §B.9 不做與延後
  - §B.10 待決事項與殘餘風險
  - §B.11 建議的執行步驟
  - §B 附錄 A：數值
  - §B 附錄 B：出處
  - §B 附錄 C：版本歷程
- **第 4 部　任務 C：自動化候選設計產生（§C）**
  - §C.0 任務卡
  - §C.1 名詞與檔案
  - §C.2 前提與提供的介面
  - §C.3 硬性限制
  - §C.4 設計
  - §C.5 階段 C1：F1 搜尋（contracts CV-C1）
  - §C.6 階段 C2：Geant4 搜尋值與 F4 確認（geant4 adapter 0.5.0、contracts CV-C2）
  - §C.7 階段 C3：範例（J16）
  - §C.8 契約與版本
  - §C.9 不做與延後
  - §C.10 待決事項與殘餘風險
  - §C.11 建議的執行步驟
  - §C 附錄 A：數值
  - §C 附錄 B：出處
  - §C 附錄 C：版本歷程
- **第 5 部　設計理由（§R）**
  - §R.0 摘要
  - §R.1 設計依據：從實際實驗學到的事
  - §R.2 目標、限制與原則
  - §R.3 架構總覽
  - §R.4 資料分層與 run summary
  - §R.5 執行、種子、區塊與重現
  - §R.6 驗證類別與判定
  - §R.7 契約、追溯與 sci-fix
  - §R.8 程式與 CI
  - §R.9 通用性
  - §R.10 階段與驗收
  - §R.11 殘餘風險
  - §R.12 決策紀錄
  - §R.13 演進紀錄：被取代的設計
  - §R.14 出處
  - §R.15 與 main 探測器系統設計流程的關係（2026-10-24）

---

# 第 1 部　計畫總覽（§P）

> 日期：2026-10-24（依 main 0.38.0 的探測器系統設計流程重新規劃）

---

## §P.0 一頁摘要

本計畫接上 main 已有的探測器系統設計流程（hep-detector，0.37.0–0.38.0）：design-spec／design-candidate／design-evaluation 三種產物，`contracts/design.py` 推導判定，保真度 F0–F5，人工閘門 H1–H4。本計畫補上它缺的三件事：**正確的 Geant4 標籤**（任務 A）、**能成為 F4 的 Geant4 評估器**（任務 B）、**自動產生候選**（任務 C）。三個任務、八個階段，每個階段是一次可以單獨合併的變更，有自己的驗收清單：

| 階段 | 任務 | 一句話 | 前提 | 版本 | 規模 |
|---|---|---|---|---|---|
| **A1** | A 正確性 | 修正會錯誤發出 `validated-in-scope` 的缺陷 D1–D8、D10、D11；統計與 summary 的共用模組放進 `core/`（重用既有函式）；讓 `evaluate_design.py f4` 能走完 `label --upgrade` | — | contracts **CV-A1**（sci-fix） | 大 |
| **A2** | A 邊界產物 | `g4sim` 共用標頭、逐事件種子、`layered_sim` 寫出三個邊界產物；研究層只讀邊界產物（D9） | A1 | geant4 adapter **0.2.0** | 大 |
| **B1** | B 新後端 | `element_sim`（盒狀元件、分區磁場、所有帶電徑跡的平面 hit、量能器漏失）、逐事件 ROOT 檔、`simroot`；`geant4_run.py from-geometry` 把 `design-geometry/1` 轉成 `element_sim.spec/1` | A2 | geant4 adapter **0.3.0** | 大 |
| **B2** | B 重建與 F4 介面 | `simreco` 與可切換的尾部來源；`label` 寫出 `results`、`tail_sources_simulated` 與幾何檔；徑跡 reference benchmark（F4 資格路徑）；對照表 1.1.0 | B1 | geant4 adapter **0.4.0**、contracts **CV-B2** | 大 |
| **B3** | B J15 | J15 寫成設計專案（design-spec＋候選），F1、F2 經 `evaluate_design.py run`，F4 經 `geometry → 研究 → f4`；驗證梯是獨立的 `unvalidated` 紀錄 | B2、G-D0 | 範例與文件；journey J15 | 中（計算量大） |
| **C1** | C 候選產生器 | `evaluate_design.py search`：在 main 的 F1 上搜尋，寫出 `search_summary`，以 `expand --search` 把決選者變成候選；不寫判定、不排序 | — | contracts **CV-C1** | 中 |
| **C2** | C Geant4 搜尋與確認 | 以短 `element_sim` run 得到搜尋值、共同亂數配對比較、贏家詛咒保護；決選者以新種子做 F4 確認；`design.py` 拒絕用搜尋種子的證據 | B2、C1（確認另需 G-D0） | contracts **CV-C2** | 大 |
| **C3** | C 範例 | 在 Example A（太空磁譜儀）與 Example B（對撞機徑跡＋ECAL）上執行搜尋；選用的貝氏最佳化後端 | C2 | 範例與文件；journey J16；選用 `adapters/design-bo/` **0.1.0** | 小到中 |

```
D0 （維護者核准 F4 資格路徑）─────────────┐
                                           ▼
A1 ──▶ A2 ──▶ B1 ──▶ B2 ──┬──────────────▶ B3
                          │
C1 ───────────────────────┴──▶ C2 ──▶ C3
```

- 到「Geant4 研究成為設計流程的 F4 證據」的關鍵路徑是 A1 → A2 → B1 → B2，再加上 D0 的核准。
- C1 只依賴 main，可以從第一天起與 A、B 平行進行。
- C2 的搜尋部分只等 B2 與 C1；它的 F4 確認與 B3 都要等 D0。

---

## §P.1 評估：問題與處理

前一版（2026-10-23）以 main `9f08796`（0.23.0）為基準。2026-10-24 對照 main 0.38.0 的審查（`review-2026-10-24-main-0.38.md`）發現 main 已經有完整的設計流程，於是重新規劃。

| # | 問題 | 影響 | 處理 |
|---|---|---|---|
| P1 | **偵測器層級的 Geant4 研究無法成為 F4。** F4 只接受重新發出為 `validated-in-scope` 的研究（`contracts/design.py:1004`），升級需要涵蓋研究範圍的 reference benchmark，而解析度、電荷誤判、簇射包含都沒有 | 任務 B 與 C 的 Geant4 結果都進不了設計流程 | 建立 F4 資格路徑（D0，§P.7 第 1 項）：材料範圍、場傳播驗證、重建驗證、新的徑跡 reference benchmark 都通過時才可升級（B2） |
| P2 | **保真度名稱衝突。** 前一版任務 C 的 F0／F1／F2 與 main 的 F0–F5 意義不同 | 讀者與 `design.py` 對同一個名稱有不同解讀 | 全文採用 main 的名稱（§P.5）；搜尋中的 Geant4 短 run 只產生「搜尋值」，不是任何保真度 |
| P3 | **任務 C 再造一套設計系統**：自己的需求規格、設計格式、需求判定、排序與「推薦設計」，並違反 main 的規則（判定只由 `design.py` 推導、絕不宣稱全域最佳、閘門要人） | 不能合併 | C 改為 D2 階段的候選產生器 `evaluate_design.py search`：讀 design-spec 與基礎候選，只寫 `search_summary`，決選者經 `expand` 成為候選，由 `report` 推導判定 |
| P4 | **F4 的資料路徑不完整。** main 上沒有程式寫出 `extension.study.results` 與 `tail_sources_simulated`；`evaluate_design.py f4` 呼叫 `label --upgrade` 時沒有傳 `--run-record`，`label` 必然拒絕 | F4 實際上無法產生 | A1 修正 `f4` 的轉傳與結束碼；B2 讓 `label` 寫出 F4 需要的欄位，並加端到端測試 |
| P5 | **A1 漏掉一個缺陷並使用舊格式。** 收斂閘門缺少最細的掃描點時以較粗的點通過（D11）；帳本與 advisory 的格式已改；Garwood 區間與種子推導在 `core/stats` 已有 | A1 不能照舊開始 | A1 加 D11、改用新格式、重用既有函式（第 2 部） |
| P6 | **A1 的範圍膨脹**（沿用前一版的處理）。只有後續階段需要的功能不放進 A1 | sci-fix 被拖慢 | 原則 R1；判定引擎在 A1 只有 `equivalence` 與 `detection_limit`，B2 加 `change`；需求判定一律由 `design.py` 負責 |
| P7 | **契約變更的代號依合併順序而定。** C1 不再依賴 A，可能比 A1 先合併 | 「CV1–CV3」的順序不再成立 | 以擁有的階段命名：CV-A1、CV-B2、CV-C1、CV-C2；號碼在發布時依合併順序決定（§P.5） |
| P8 | **介面放錯層**（沿用）。`core/` 只能 import `core`（`check_layering.py:4`） | `core/` 無法使用 `contracts/schema.py` | summary 的 schema 放在 `contracts/schemas/`，由 adapter 或 skill 腳本驗證；`core/simulation/` 只做計算 |
| P9 | **待決事項與閘門分散**（沿用） | 看不到哪個決定擋住哪個階段 | 合併為 §P.6、§P.7 兩張表；main 已決定的事項標明出處 |

**main 已提供、本計畫直接使用的介面：** design-spec、design-candidate、design-evaluation（contracts 3.11.0）；`contracts/design.py`（判定、彙整、篩選、比較基準、排序與 Pareto、F4 與 F5 的檢查）；`contracts/rules/design_adequacy.json`（每個 figure of merit 的篩選與合規保真度）；`contracts/rules/design_geometry.json`（`layered-spectrometer` 對照表 1.0.0）；`evaluate_design.py` 的 `run`、`budget`、`geometry`、`f4`、`scan`、`expand`、`plan`、`report`；參數層級的過時與 `run_workflow.py --incremental`；`scan_summary`；能力 `detector-design`（hep-detector）。

**本計畫新增的：** 正確的標籤與統計（A1）；能產生 F4 的 Geant4 應用、重建與尾部來源（B1、B2）；把 J15 做成設計專案的完整示範（B3）；自動產生候選與 Geant4 多保真度搜尋（C1、C2）；兩個範例上的示範（C3）。

---

## §P.2 規劃原則

| # | 原則 | 說明 |
|---|---|---|
| R1 | **由第一個使用者引入，但位置一開始就定好** | 每個介面在第一個需要它的階段加入；共用的介面從第一天起就放在所有使用者都能 import 的地方（`core/`、`contracts/`） |
| R2 | **schema 只做附加的演進** | 新欄位都是選用的；版本號的 minor 增加；舊紀錄永遠能讀、能重播 |
| R3 | **同一個量只有一份正式實作** | 另一種語言或另一個位置的實作只能在測試中作為 oracle；`core/stats` 已有的函式直接重用 |
| R4 | **sci-fix 保持最小** | A1 只含修正缺陷所需的變更與它們的直接基礎（包括讓 F4 的消費端不誤報的小修正） |
| R5 | **每個階段可單獨合併** | 有自己的版本、VALIDATION 條目、CHANGELOG、驗收清單；合併後 plugin 是一致的 |
| R6 | **判定可重現，數字可追溯** | 重現的定義是判定與 label 相同（§R.5.6）；結果附搜尋規模與證據相關性 |
| R7 | **AI 是設計者，不是裁判** | Claude 選結構、提出候選、解讀結果；「是否符合」只由 `contracts/design.py` 從產物推導，閘門由人核准 |
| R8 | **接上 main 的設計流程，不另建一套** | 需求用 design-spec，候選用 design-candidate，證據用 design-evaluation；保真度用 main 的 F0–F5 |
| R9 | **判定只由 `design.py` 推導** | 本計畫的程式不寫判定、成熟度、過時標記、`screened_out` 或 `at-risk`；`core/stats/decisions.py` 只判定研究層的閘門（收斂、benchmark、regression） |
| R10 | **絕不宣稱全域最佳** | 搜尋的前緣是無約束力的搜尋階段前緣；排序與 Pareto 只由 `report` 在比較基準成立時給出 |

---

## §P.3 階段的內容與驗收（摘要）

各階段的完整工作項與驗收在第 2–4 部；這裡只列範圍的邊界，避免重疊。

| 階段 | 包含 | 明確不包含（在哪個階段） |
|---|---|---|
| A1 | D1–D8、D10、D11 的修正；benchmark 表與驗證類別（reference、setup-matched、sanity、interface）；範圍比對；configuration 與隔離（`spec-v1`）；區塊 batch means、精確區間（重用 `core/stats/poisson_diagnostics.py` 的 `central_interval`）、MPV、分位數；判定引擎的 `equivalence` 與 `detection_limit`；兩階段事件數；種子雜湊 H（與 `toy_ensemble.toy_seed` 的關係寫明）；`extension.simulation.evidence_role`；`simulation-summary/1` 與 `simulation-observables/1` 的 schema（`contracts/schemas/`）；Python summary 產生器；`tolerance_mode` 的 `absolute`（P6 的例外：A1 自己的 J14 benchmark 就需要它）；`evaluate_design.py f4` 轉傳 `--label-run-record`、把 `label` 結束碼 3 對應為 `incomplete`；帳本與 advisory `/2` 的新格式；J14 重產 | `change` 與 regression（B2）、`results` 與尾部來源欄位（B2）、搜尋與確認的種子規則（C2）、`values` 累加器（C2）、C++ summary（A2） |
| A2 | `g4sim`（`SimHash`、`SimSeed`、`SimSummary`、`MiniJson`、`SimProbe`）；`per-event` 種子；`layered_sim` 寫出 summary、column map、effective config；`tree-v1`；effective config 依內容雜湊存放；`validate_spec`、`spec.schema.json` 與 `Spec.cc` 接受 `run.seeding`、`output.observables`、`output.blocks`、`output.debug_observable_dump`；`geant4_run.py run` 寫出 `argv`、`script_sha256`、`versions.plugin_release`；研究層只讀邊界產物；schema 關鍵字（`maxItems`、`maximum`、`exclusiveMaximum`；不用 `uniqueItems`） | `element_sim`（B1） |
| B1 | `element_sim.spec/1`、`element_sim`、分區均勻磁場、所有帶電徑跡的平面 hit 表、量能器母體與漏失欄、逐事件 ROOT 檔、`simroot`、`geant4_run.py check-spec`（登記於 `MISSING_FILE_ARGS`）、`geant4_run.py from-geometry` 與實現設定檔（realization profile）、兩個後端的介面一致性、確定性場檢查 | `simreco` 與尾部來源（B2）、對照表 1.1.0（B2）、J15（B3） |
| B2 | `simreco`（數位化與重建，可攜的亂數）；可切換的尾部來源（錯位、數位化與雜訊、hit 指派、磁場尺度誤校正）與曲率偏移；`geant4_run.py reco` 與 `table`；遞移的處理鏈；verification 與 regression 類別、regression 角色、判定引擎的 `change`；高斯核心解析度與計數型電荷誤判的觀測量；`label` 的 `--results`、`--geometry`；`f4` 接受不對稱或精確的不確定度；對照表 1.1.0；徑跡 reference benchmark 與 F4 資格規則；`geometry → 研究 → label --upgrade → f4` 端到端測試；CV-B2 | J15 設計專案（B3）；任務 C 用的 surrogate 類別（刪除） |
| B3 | J15 的 design-spec 與候選（名義 0.5 T／N = 6，變體 N = 4、N = 8）；F1、F2 經 `evaluate_design.py run`；每個（figure of merit, 分母）一份 F4 研究；示範尾部來源開啟時界限由 `optimistic` 變成 `estimate`、模型包絡、電荷誤判在缺資料驗證時為 `chain.incomplete`；驗證梯（場傳播、TOF、取樣分率；隔離的 PVT benchmark 是獨立的研究紀錄）為 `unvalidated` 紀錄；量能器 cut 收斂、variation、TOF σ_t 敏感度；journey J15 | — |
| C1 | `evaluate_design.py search` 與 `expand --search`；搜尋 spec（參數範圍、各角色的子系統槽、評估預算、種子、目標 = 適足表的 figure of merit）；基因組與解碼器（寫成基礎候選的 `overrides`）；在行程內以與 tool contract 相同的函式做 F1 評估；NSGA-II、Sobol、WFG 超體積；`search_summary`（CV-C1，免孤兒規則）；封閉測試；`system-design-workflow.md` 的「D2 自動產生候選」一節 | 任何 Geant4 評估（C2）；判定、排序、推薦設計（不做，由 `design.py`）；新的 reference 檔或 `SKILL.md` 修改（不做） |
| C2 | 以 `from-geometry` 與短 `element_sim` run 產生的搜尋值；共同亂數與配對比較（G-C2a）；`values` 累加器（Python 與 `SimSummary.hh`，`values_max` 以區塊計）；贏家詛咒 toy；種子角色與快取鍵；決選者的 F4 確認；`design.py` 的搜尋種子規則（CV-C2） | 範例（C3）；選擇感知的覆蓋率（只提案給 hep-statistics 與 `design.py`） |
| C3 | Example A 與 Example B 上的搜尋（含 `capability.unavailable` 列）、決選者經 report 閘門（含缺 expected-precision 時拒絕排序）、C2 合併後 Example A 的一次 Geant4 確認；journey J16；選用的 `adapters/design-bo/`（Ax/BoTorch） | — |

---

## §P.4 介面擁有權

| 介面 | 引入 | 位置 | 擁有者（steward） | 使用者 |
|---|---|---|---|---|
| benchmark 表、驗證類別、範圍比對、隔離規則 | A1（B2 附加 verification、regression、徑跡 reference） | `contracts/validate.py`、`dependencies.py`、`geant4_benchmarks.py` | contracts（內容由 hep-detector 提出） | A1、B2、B3、C2 |
| 種子雜湊 H（Python） | A1 | `core/simulation/seeds.py`（說明與 `core/stats/toy_ensemble.py` 的 `toy_seed` 的關係） | hep-detector | geant4 adapter、`check_geant4_study.py`、`evaluate_design.py search` |
| 種子雜湊 H（C++） | A2 | `adapters/geant4/assets/g4sim/SimHash.hh` | hep-detector | `layered_sim`、`element_sim`、`simreco` |
| `extension.simulation.evidence_role` | A1 | `contracts/`、study spec schema | contracts | 全部 |
| regression 角色 | B2 | 同上（CV-B2） | contracts | B2、B3 |
| `simulation-summary/1`、`simulation-observables/1` 的 schema | A1（`values` 在 C2 附加） | `contracts/schemas/` | contracts（內容由 hep-detector 提出） | 全部 |
| summary 的讀取與合併（只計算） | A1 | `core/simulation/summary.py` | hep-detector | 全部 |
| column map、effective config 的 schema | A2 | `contracts/schemas/` | contracts | A2、B1、C2 |
| `tree-v1` 目標雜湊與 `hash_scheme` | A2（A1 為 `spec-v1`） | `g4sim/SimProbe.hh`；比對在 `check_geant4_study.py` | hep-detector | A2、B1、B3、C2 |
| `per-event` 種子（`run.seeding`） | A2 | `g4sim/SimSeed.hh`、spec/1 | hep-detector | `layered_sim`、`element_sim` |
| 物理探針（effective config 的 physics 部分） | A2 | `g4sim/SimProbe.hh` | hep-detector | A2、B1、B2（regression）、C2 |
| 區塊估計量、MPV、分位數 | A1（`values` 分位數在 C2） | `core/stats/batch_means.py` | hep-statistics | hep-detector 腳本、`evaluate_design.py search` |
| 分布函式（`t_ppf`、`f_ppf`）；Garwood 重用 `central_interval` | A1 | `core/stats/distributions.py`；`core/stats/poisson_diagnostics.py` | hep-statistics | 同上 |
| 研究層判定引擎 | A1 `equivalence`、`detection_limit`；B2 `change`；C2 配對模式 | `core/stats/decisions.py` | hep-statistics | A1、B2、B3、C2 |
| `evaluate_design.py f4` 的 `--label-run-record` 與結束碼對應 | A1 | `skills/hep-detector/scripts/evaluate_design.py` | hep-detector | B3、C2 |
| `g4sim` 標頭 | A2（`SimSummary` 的 `values` 在 C2） | `adapters/geant4/assets/g4sim/` | hep-detector | `layered_sim`、`element_sim`、`simreco` |
| `element_sim.spec/1` 與 `check-spec` | B1 | geant4 adapter | hep-detector | B1、B3、C2 |
| `geant4_run.py from-geometry` 與實現設定檔 | B1 | geant4 adapter | hep-detector | B3、C2 |
| 逐事件 ROOT 檔、`simroot` | B1 | geant4 adapter | hep-detector | B2、B3 |
| `simreco`、reco spec 與尾部來源 | B2 | geant4 adapter（C++，不連結 Geant4） | hep-detector | B3、C2 |
| 研究紀錄的 `results.<fom>`、`tail_sources_simulated`、幾何檔（`label --results`、`--geometry`） | B2 | `skills/hep-detector/scripts/check_geant4_study.py` | hep-detector | B3、C2（經 `f4`） |
| 幾何對照表 1.1.0 | B2 | `contracts/rules/design_geometry.json`、`contracts/schemas/design_geometry.json`（CV-B2） | contracts | B3、C2 |
| `f4` 的不對稱與精確不確定度 | B2 | `contracts/design.py`、`evaluate_design.py`（CV-B2） | contracts | B3、C2 |
| 徑跡 reference benchmark 與 F4 資格規則 | B2（D0 核准後生效） | `geant4_benchmarks.py`、`geant4-study-protocol.md` | hep-detector | B3、C2 |
| `evaluate_design.py search`、`expand --search`、搜尋 spec、基因組與解碼器 | C1 | `skills/hep-detector/scripts/evaluate_design.py` | hep-detector | C1–C3 |
| `search_summary`（computational-run 的欄位，免孤兒規則） | C1 | `contracts/schemas/ext_computational_run.json`、`contracts/design.py`（CV-C1） | contracts | C1–C3 |
| 行程內的 F1 搜尋值 | C1 | `evaluate_design.py search` 匯入 F1 工具腳本並以 tool contract 的引數呼叫其 `main(argv)`（C1.4）；不新增 `core/` 模組（`core/OWNERS.json` 的准入規則要求多個頂層元件使用，這些工具與 `evaluate_design.py` 同屬 hep-detector） | hep-detector | `evaluate_design.py search` |
| 搜尋種子規則（evaluation 的 run 或研究種子出現在搜尋摘要中 → `design.contract_mismatch`） | C2 | `contracts/design.py`（CV-C2） | contracts | C2、C3 |
| 選用的貝氏最佳化後端 | C3 | `adapters/design-bo/`（延遲 import） | hep-detector | C3 |

跨 adapter 與跨 skill 的呼叫一律以子行程與 JSON 檔案進行（分層規則：adapter 只 import `core` 與 `contracts`；`evaluate_design.py` 不 import `adapters/geant4`），例如 `evaluate_design.py search` 呼叫 `geant4_run.py from-geometry`、`run`、`reco`。

---

## §P.5 命名與編號

| 對象 | 寫法 | 例 |
|---|---|---|
| 階段 | 任務字母加數字 | A1、A2、B1、B2、B3、C1、C2、C3 |
| 工作項 | 階段.序號 | A1.6、B2.1、C2.4 |
| 契約變更（號碼在發布時依合併順序決定，都 ≥ 3.13.0） | **CV-A1、CV-B2、CV-C1、CV-C2** | CV-A1 = A1 的 contracts minor（sci-fix）；CV-C1 = `search_summary` |
| 閘控寫法 | `strict or _at_least(contract_version, CV-x)` | — |
| 保真度 | main 的 **F0–F5**：F0 啟發式（無 run）、F1 解析 tool contract、F2 toy MC、F3 response／expected precision、F4 重新發出為 `validated-in-scope` 的 Geant4 研究、F5 量測 | 搜尋中的 Geant4 短 run 只產生「搜尋值」 |
| geant4 adapter 版本 | 0.2.0（A2）、0.3.0（B1）、0.4.0（B2）；C2 只有在新增 run 選項時才是 0.5.0 | — |
| 其他 adapter | 只有選用的 `adapters/design-bo/` 0.1.0（C3）；沒有 `adapters/detector-design/` | — |
| journey | J14 薄矽層（既有）、J15 最小磁譜儀設計專案（B3）、J16 自動產生候選（C3） | main 的 journey 到 J14 為止 |
| VALIDATION 條目 | GEANT4-CORRECTNESS（A1）、GEANT4-SUMMARY（A2）、GEANT4-ELEMENT（B1）、GEANT4-F4（B2）、GEANT4-J15（B3）、DESIGN-SEARCH-F1（C1）、DESIGN-SEARCH-G4（C2）、DESIGN-SEARCH-EXAMPLES（C3） | — |
| 待決事項 | D0 與 §P.7 的編號 | D0 = F4 資格路徑 |
| 節的引用 | 全部在本文件中：「§P.n」是第 1 部、「§A.n」「§B.n」「§C.n」是第 2–4 部、「§R.n」是第 5 部；「§B 附錄 A」是第 3 部的附錄 | — |

前一版的 CV1、CV2、CV3 分別改為 CV-A1、CV-B2、CV-C2；CV-C1 是新的。前一版任務 C 的「F0」相當於 main 的 F1，「F1、F2」與「確認」相當於搜尋值與 F4。

---

## §P.6 階段閘門

| 閘門 | 時機 | 條件 | 不通過時 |
|---|---|---|---|
| G-D0 | B3 開始前、C2 的確認開始前 | 維護者核准 F4 資格路徑（§P.7 第 1 項） | B3 與 C2 的確認不開始；B2 的資格規則保留但不生效 |
| G-A1 | A1 合併前 | J14 重產的紀錄通過 `--strict` 與 `dependencies.py`；閘門、覆蓋率、MPV、偵測極限的 toy 通過；`tools/scifix_ledger.py report` 與 advisory 檢查通過；`f4 --label-spec` 的測試依第 2 部的說明通過 | 不合併；若 J14 因未達標而失去 `validated-in-scope`，由維護者依 §P.7 第 5 項決定 |
| G-A2 | A2 合併前 | J14 的 CSV 與 A2 前逐位元相同；探針不改變亂數狀態 | 不合併 |
| G-B1a | B1 開始的第一天 | `G4RootAnalysisReader` 能讀 MT 合併、壓縮的檔案與字串欄 | `simroot` 改為只讀純量欄，字串移到 JSON 旁檔（B1.5）；兩種結果都可接受 |
| G-B1b | B1 合併前 | 確定性場檢查在名義值下通過；兩個後端共同觀測量以 `equivalence`（宣告的容許值與 se 目標）判定一致；量能器比較總漏失（後、前、側面之和）；`from-geometry` 對同一幾何檔產生相同的 spec | 不合併 |
| G-B2 | B2 合併前 | `geometry → 研究 → label --upgrade → f4` 端到端測試通過；徑跡 reference benchmark 的負對照被抓到；尾部來源全部關閉時與 B1 的結果一致 | 不合併 |
| G-C1 | C1 合併前 | 全部封閉測試通過；`search` 不寫任何判定；`expand --search` 產生的候選通過 `design.py` | 不合併 |
| G-C2a | C2 的 trial | 量測配對比較的變異縮減 | 縮減小於宣告值時改用獨立比較（C2.3） |
| G-C2b | C2 合併前 | 贏家詛咒 toy、搜尋種子規則的契約測試通過 | 不合併 |
| G-C3 | C3 合併前 | 兩個範例的搜尋完成，決選者通過 report 閘門 | 不合併 |

---

## §P.7 待維護者決定的事項（合併清單）

| # | 事項 | 建議 | 阻擋 |
|---|---|---|---|
| 1 | **D0：偵測器層級 Geant4 研究成為 F4 的路徑** | 建立資格路徑（使用者已選定方向）：材料在已通過的 A1 材料 benchmark 範圍內、場傳播驗證通過、重建驗證通過、新的徑跡 reference benchmark（孤立 Si 片中的多重散射角寬度，對照 PDG Highland／Lynch–Dahl，附負對照，範圍維度為剛度與粒子）通過；另一個選項（`design.py` 允許未驗證的 F4 只用於篩選）不採用 | B3、C2 的確認 |
| 2 | CV-A1 的歸類 | minor 加 sci-fix | A1 |
| 3 | 新 `core/` 模組的 steward 與第二個使用者 | 統計歸 hep-statistics；`core/simulation/` 歸 hep-detector；`OWNERS.json` 登錄 | A1 |
| 4 | hep-computing 同意在 `ext_computational_run.json` 宣告 `simulation` 與 `search_summary` | 同意 | A1、C1 |
| 5 | 兩階段係數 F₀.₉₀ 或 F₀.₉₅；重產的 J14 偶然失去 `validated-in-scope` 時的處理 | J14 重錄用 F₀.₉₅；失去時記錄並保留舊紀錄於 advisory | A1 |
| 6 | J14 掃描與 variation run 的 live 重錄，以及 recorded 大小上限 | 重錄；上限 3 MB | A1 |
| 7 | 精確區間的切換門檻 | 任一區塊為 0 或總數 < 100 | A1 |
| 8 | G5「未複製範例程式碼」的確認方式 | 審查者在 VALIDATION 條目中確認 | A2、B1 |
| 9 | ROOT 檔的存放位置與保留期限 | 不提交；由使用者的儲存決定，紀錄只留雜湊 | B1 |
| 10 | 遞移的處理鏈（hep-computing 同意）與 CV-B2 的歸類 | 同意；minor | B2 |
| 11 | `simreco` 的 C++17 CI 工作是否必要 | 必要 | B2 |
| 12 | `results` 以分母為鍵、每個候選允許多個幾何檔 | 先採「每個（figure of merit, 分母）一份研究」；鍵化的結果作為 main 的後續改進 | B3 |
| 13 | CV-C1、CV-C2 的歸類 | minor | C1、C2 |
| 14 | 貝氏最佳化後端（Ax/BoTorch）是否列為測試過的工具 | 列為選用 | C3 |
| 15 | 新增 CI 影響群組（`adapters/geant4/**`、`core/stats/**`、`core/simulation/**`） | 新增，減少全量 CI | A1 |

**已由 main 決定（不再待決）：**
- `detector-design` 能力的擁有者是 hep-detector（`docs/capability-map.json`）。
- 設計流程的入口是 hub 連結，不改 `SKILL.md` 描述（CHANGELOG 0.37.0，OQ-01）；任務 C 只在 `system-design-workflow.md` 加一節。
- 搜尋的子命令形式沿用 `scan` 的先例（OQ-18）。
- 前一版的 `extension.design_search` 改為 computational-run 的 `search_summary` 欄位（同 `scan_summary`）。
- 前一版的 detector-design adapter、需求規格 schema 與元件目錄 schema 已刪除。

---

## §P.8 跨任務的主要風險

1. **main 變動快。** main 在兩天內從 contracts 3.5.0 到 3.12.0。共用檔案 `contracts/validate.py`、`dependencies.py`、`design.py`、`evaluate_design.py`、`ext_computational_run.json` 容易衝突；每個階段開始時在最新 `main` 上重新核對引用的行號，合併前 rebase 並重跑檢查。
2. **F4 資格路徑未核准。** D0 不核准時，B3 與 C2 的 Geant4 結果只能停在 `unvalidated`，不能成為 F4；B1、B2 仍有價值（基礎設施與端到端路徑）。
3. **尾部來源的模型化程度。** 只有四種尾部來源都模擬時，F4 的解析度與電荷誤判才是 `estimate`；B2 的錯位、數位化與雜訊、hit 指派、磁場誤校正都是簡化模型，結果的意義以研究紀錄的宣告為限。
4. **兩個 Geant4 程式的維護成本**（`layered_sim` 凍結、`element_sim` 新增）。以 `g4sim` 控制重複；長期可在 `element_sim` 能產生 J14 的全部觀測量後退役 `layered_sim`（延後）。
5. **統計的實際行為**：區塊 batch means 對偏斜分布的 O(1/B) 偏差、兩階段設計的未達標率（一對點約 19 %）、配對比較的變異縮減可能很小。都以 toy 與 trial 量測，不事先假設。
6. **未逐行核對的 Geant4 行為**：stepper 的建立、Birks 的 API、場交點誤差的方向、兩個 physics list 的核子截面、`G4RootAnalysisReader` 的能力、保存亂數狀態的函式名稱。各在第一次使用的階段先核對。
7. **計算量**：J14 重錄（A1）、量能器簇射與每個（figure of merit, 分母）一份的 F4 研究（B3）、Geant4 搜尋（C2）。各階段在 trial 後寫入預算。
8. **CI 成本**：main 的 `contracts/rules/registry.json` 沒有 `adapters/geant4/**`、`core/stats/**` 等的影響群組，這些變更會觸發全量 CI（§P.7 第 15 項）。
9. **入口預算**：hep-detector quick load 只剩 931 bytes、description 1,016 / 1,024 字元。本計畫不修改 `SKILL.md`。
10. **工作量估計不完整**：只有 A1 契約部分有原型估計（約 8–12 個工作天）；其餘在各階段開始時估計並記錄。
11. **參考文獻**：任務 C 引用的 GRACE、VI-BRATO 是 2026 年的預印本；AIDO 與 Cisbani 的數字待核對；所有出處在正式引用前經 hep-citations 核對。

---

## §P.9 文件地圖與權威分工

| 文件 | 內容 | 權威範圍 |
|---|---|---|
| 第 1 部（本部） | 評估、原則、階段、介面擁有權、命名、閘門、待決事項、風險、執行環境 | 順序、編號、版本代號、擁有權、閘門、待決事項、執行環境（isolated worktree） |
| 第 2 部（任務 A） | A1、A2 的工作項與驗收 | 這兩個階段的內容與驗收 |
| 第 3 部（任務 B） | J15 的設計；B1、B2、B3 的工作項與驗收 | 這三個階段的內容與驗收；J15 的數值 |
| 第 4 部（任務 C） | 自動產生候選的設計；C1、C2、C3 的工作項與驗收 | 這三個階段的內容與驗收 |
| 第 5 部（設計理由） | 設計理由、參考實驗、與 main 設計流程的關係、被取代的設計 | 理由；與規格衝突時以規格為準並回報 |
| `review-2026-10-24-main-0.38.md` | 對照 main 0.38.0 的審查紀錄（發現與建議） | 重新規劃的依據；本文件已依它修改 |
| `README.md` | 資料夾入口，指向本文件 | — |
| `gate_operating_characteristics.py`、`j15_design_estimates.py`、`design_search_closure.py` | 設計數值的計算程式 | 對應附錄的數值 |

第 2–4 部的結構相同：§X.0 任務卡、§X.1 名詞與檔案、§X.2 前提與提供的介面、§X.3 硬性限制、§X.4 設計摘要、§X.5 起各階段的工作項與驗收，之後是契約與版本、檢查、不做與延後、待決事項與風險、執行步驟、附錄（X 為 A、B 或 C）。

---

## §P.10 執行環境：isolated worktree

### §P.10.1 原則

- **每個階段在自己的 isolated git worktree 中執行**：一個階段、一個 worktree、一個分支。
- 主要 checkout（repo 根目錄的工作區）與其他 worktree 中的檔案一律不修改。
- 理由：
  - 可以平行的階段（例如 C1 與 A、B）與平行的 agent 不會互相覆寫；
  - 建置目錄、Geant4 輸出與暫存檔彼此隔離；
  - 一個階段失敗時可以整個丟棄，不影響其他工作；
  - 每個階段的變更就是一個分支的 diff，審查與合併的範圍清楚。

### §P.10.2 建立與確認

| 項目 | 規定 |
|---|---|
| 位置 | `.claude/worktrees/geant4-<階段>`，階段名小寫，例如 `.claude/worktrees/geant4-a1` |
| 分支 | `worktree-geant4-<階段>`，例如 `worktree-geant4-a1`（`EnterWorktree` 的命名規則） |
| 基底 | 已包含全部前提階段（§P.0 的「前提」欄）的最新 `main`；例如 B2 以 B1 合併後的 `main` 為基底；C1 以當時最新的 `main` 為基底 |
| 規格的來源 | 本資料夾核准後合併到 `main`，worktree 中就有規格。核准前，規格只在分支 `worktree-geant4-architecture` 上，以 `git show worktree-geant4-architecture:plugins/hep-research/docs/dev/geant4-architecture/<檔名>` 讀取，不把該分支合併進階段分支 |
| 在 Claude Code 中 | 工作階段本身以 `EnterWorktree`（name `geant4-<階段>`）建立並進入 worktree：位置 `.claude/worktrees/geant4-<階段>`、分支 `worktree-geant4-<階段>`、基底 `origin/main`；把實作工作委派給 subagent 時，Agent 工具使用 `isolation: "worktree"` |
| 在其他環境 | `git fetch origin && git worktree add .claude/worktrees/geant4-a1 -b worktree-geant4-a1 origin/main`；在 Claude Code 中可再以 `EnterWorktree` 的 `path` 進入這個既有的 worktree |
| 開始前確認 | `git rev-parse --show-toplevel` 是該 worktree 的路徑、`git branch --show-current` 是該階段的分支、`git status` 乾淨；每個前提階段的合併 commit 都滿足 `git merge-base --is-ancestor <合併 commit> HEAD`；本文件引用的 main 行號在新基底上重新核對；這些結果寫入該階段的工作紀錄（VALIDATION 條目的環境欄） |

### §P.10.3 在 worktree 中的規則

1. 所有編輯、建置、測試、Geant4 執行與規格修正都在該階段的 worktree 中進行；不 `cd` 到主要 checkout 或其他 worktree。
2. 指令使用 worktree 內清楚的絕對路徑或相對路徑；避免以執行時才計算的變數組出 git 的參數，讓工具與審查者都能確認指令留在 worktree 內。
3. **`git stash` 是所有 worktree 共用的。** 不使用裸的 `git stash` 或 `git stash pop`；需要暫存時用暫時的 WIP commit。
4. 建置目錄、E2 的輸出、ROOT 檔與 trial 的結果放在該 worktree 內不提交的目錄（例如 `build/`、`work/`，由 `.gitignore` 排除），或該 worktree 專屬的暫存目錄；不同 worktree 不共用建置目錄。Geant4 本身的安裝（E2）可以由多個 worktree 唯讀共用。
5. 只在該階段的分支提交；commit 附規定的 trailer；推送到同名的遠端分支。未經維護者核准不推送 `main`、不開 pull request。
6. 合併前在 worktree 中執行 §A.8 的檢查，並確認閘門（§P.6）。
7. 規格需要修正時：維護者核准規格之前，在文件的 worktree（`.claude/worktrees/geant4-architecture`，分支 `worktree-geant4-architecture`）中修改；實作開始之後，在該階段的 worktree 中修改。兩種情況都同時修改中英兩版並記入版本歷程；影響其他階段時同時更新本部。
8. 獨立審查的隔離依 `docs/dev/independent-review-spec.md` 附錄 A7（主機設定：`CLAUDE_CODE_FORK_SUBAGENT=0` 或 `permissions.deny` 中的 `Agent(fork)`，並指名非 fork 的 subagent 類型）；worktree 只用於實作。審查只讀不寫。

### §P.10.4 可以平行的階段

| 同時進行 | 條件 | 注意 |
|---|---|---|
| C1 與 A1、A2、B1、B2 | 無（C1 只依賴 main） | C1 動 `skills/hep-detector/scripts/evaluate_design.py`、`contracts/design.py`、`contracts/schemas/ext_computational_run.json`、`skills/hep-detector/references/system-design-workflow.md`；A1 也動 `evaluate_design.py`，B2 也動 `design.py` 與 `evaluate_design.py`；後合併者在新的 `main` 上 rebase 並重跑檢查 |
| B3 與 C2 | B2、C1 已合併，且 G-D0 通過（B3 與 C2 的確認） | 兩者都可能修改 `geant4-study-protocol.md`、`system-design-workflow.md` 與 journey 文件；後合併者 rebase 並重跑檢查 |

每個平行的階段各用自己的 worktree 與分支；同一個階段不由兩個 agent 同時在不同 worktree 中實作。

### §P.10.5 結束

- **合併後：** `git worktree remove .claude/worktrees/geant4-<階段>`，刪除本地分支；下一個階段從新的 `main` 建立新的 worktree。
- **放棄：** 移除該 worktree 與分支；不在主要 checkout 中做任何清理。
- **本資料夾本身** 在分支 `worktree-geant4-architecture` 與 worktree `.claude/worktrees/geant4-architecture` 中撰寫；之後的文件修改也在那裡進行，直到它合併到 `main`。

---

## §P.11 版本歷程

| 版本 | 內容 |
|---|---|
| 2026-10-23 | 初版：整合評估、規劃原則、八個階段（B 拆為 B1–B3、C 為 C1–C3）、介面擁有權、命名（契約版本改記 CV1–CV3）、閘門、合併的待決事項與風險 |
| 2026-10-23 | 加入 §P.10「執行環境：isolated worktree」（建立、確認、規則、平行階段、結束）與給 agent 的讀法 |
| **2026-10-24（本版）** | **依 main 0.38.0 的探測器系統設計流程重新規劃（審查紀錄 `review-2026-10-24-main-0.38.md`）：基準改為 `5584927`；採用 main 的保真度 F0–F5；B 改為 F4 評估器（`from-geometry`、尾部來源、`results` 欄位、資格路徑 D0）；J15 改為設計專案；C 改為 `evaluate_design.py search` 候選產生器、不依賴 A；契約代號改為 CV-A1、CV-B2、CV-C1、CV-C2；新增 G-D0、G-B2；待決事項重新編號並標出 main 已決定者** |

---

# 第 2 部　任務 A：正確性修正與邊界產物（§A）

> 順序：A1 → A2；之後是任務 B（第 3 部）。任務 C 的 C1 不依賴任務 A（§P.0）
> 基準：hep-research `main` 的 `5584927`（0.38.0），contracts 3.12.0，adapter geant4 0.1.0（自 `9f08796` 未變），Geant4 11.4.3；最初依 `9f08796`（0.23.0）撰寫
> 日期：2026-10-24

---

## §A.0 任務卡

**目標。** 修正會讓模擬研究被錯誤標成 `validated-in-scope` 的缺陷（D1–D8、D10、D11），並讓研究層只透過三個邊界產物（run summary、column map、effective config）認識模擬後端（D9）。main 0.37.0 起的探測器設計流程只把 `validated-in-scope` 的研究當作 F4（`contracts/design.py` 行 1004），所以這些缺陷也影響設計評估；A1 同時讓 `evaluate_design.py f4` 能把研究交給 `label --upgrade` 並如實回報（A1.17）。統計與 summary 讀取一開始就放在 `core/`，讓任務 B 與任務 C（`evaluate_design.py search`）直接使用。

**兩個階段（依序，各自合併）：**

| 階段 | 內容 | 版本 | 語言 |
|---|---|---|---|
| **A1** 正確性修正 | 契約（benchmark 表、範圍、configuration 與隔離、evidence 角色、收斂閘門的掃描點完整性）；`core/stats/`（區塊 batch means、精確區間、MPV、分位數、判定引擎的 `equivalence` 與 `detection_limit`、分布函式）；`core/simulation/`（種子雜湊、summary 的讀取與合併）；summary 與觀測量的 schema（`contracts/schemas/`）；Python summary 產生器；J14 重產；F4 消費端的相容（`evaluate_design.py f4`） | contracts **CV-A1**（minor，sci-fix）；`CORE_VERSION` minor | Python |
| **A2** 共用標頭與邊界產物 | `g4sim`（`SimHash`、`SimSeed`、`SimSummary`、`MiniJson`、`SimProbe`）；`per-event` 種子；`layered_sim` 寫出三個邊界產物；不含名稱的 `tree-v1`；effective config 依內容雜湊存放；研究層只讀邊界產物 | geant4 adapter **0.2.0**；contracts 不升版 | C++ 與 Python |

**不在範圍內：**
- `element_sim`、場、平面穿越、ROOT 檔、`simroot`、`simreco`、J15（任務 B）；判定引擎的 `change`（B2）。
- 配對比較、search 與 confirmation 角色、seed_group、`values` 累加器（任務 C 的 C2；§P.2 R1）。需求的判定、排序與 Pareto 由 main 的 `contracts/design.py` 推導，不在 `core/stats/decisions.py`。
- 研究紀錄的 `results.<figure of merit>`、`tail_sources_simulated` 與幾何檔（B2）。
- `layered_sim` 的 spec 格式（spec/1）不重構，只加選用欄位。

**交付物：** 程式與測試；重產的 J14 紀錄；sci-fix 的 ledger 條目（每個修正一筆）與兩份 advisory（格式 `/2`）；VALIDATION 條目 GEANT4-CORRECTNESS（A1）與 GEANT4-SUMMARY（A2）；CHANGELOG；release manifest。

**完成的定義：** A1.15 與 A2.10 的驗收清單全部打勾；§A.8 的檢查全部通過；閘門 G-A1、G-A2（§P.6）通過。

**主要決定：**
1. **A1 是最小的 sci-fix。** 只含修正 D1–D8、D10、D11 與讓 F4 消費端如實回報所需的變更，以及它們的直接基礎；任務 B、C 才需要的判定與欄位由它們自己加入（§P.2 R1、R4）。
2. **共用程式在 `core/`。** adapter 只能 import `core` 與 `contracts`；統計、判定、種子雜湊與 summary 讀取從第一天起就在 `core/`，hep-detector 的腳本只是呼叫層。`core/` 只能 import `core`，所以 schema 驗證由呼叫層經 `contracts.schema` 執行；既有的 Garwood 區間、toy 種子與覆蓋率閘門直接重用（§A.4.5）。
3. **重現 = 判定相同。** 不追求逐位元相同的統計量（§A.4.3）。
4. **`layered_sim` 凍結。** A2 只加選用欄位與檔案；新的幾何功能在任務 B 的 `element_sim`。
5. **接上 main 的設計流程。** A1 不寫 F4 的結果欄位（B2 的工作），但修正 F4 消費端，讓研究的升級結果如實回報（A1.17）。

**第一步：** 依 §P.10.2 為本階段建立 isolated worktree（`.claude/worktrees/geant4-<階段>`，分支 `worktree-geant4-<階段>`，基底為已含前提階段的最新 `origin/main`），並確認 `git rev-parse --show-toplevel`、`git branch --show-current` 與 `git status`。以下所有步驟都在這個 worktree 中進行。

**開始前必做：**
1. 確認 `main` 是否已超過 `5584927`（0.38.0；2026-10-24 已依它重做核對，見 §A 附錄 C 與審查紀錄 `review-2026-10-24-main-0.38.md`）。若是，讀新的 CHANGELOG，重做 §A 附錄 C 的核對，並更新本部（中英兩版）。
2. 讀 §P.0–§P.6；讀 §R.0、§R.2；讀 `docs/maintenance.md` 的 sci-fix 流程（證據層級與帳本約第 126–251 行、advisory 約第 252–294 行）、adapter 變更流程、release 步驟；讀 `skills/hep-detector/references/system-design-workflow.md` 的 D3（F4 的列）。
3. A1 從 `prototype/phase1-core.patch` 開始。它只改 `contracts/validate.py`、`check_geant4_study.py`、`geant4_benchmarks.py`、study spec schema 與兩個測試檔，不含 `core/`：benchmark 表（等級與 kind，沒有驗證類別）、含 kind 的範圍比對（`scope_outside()`；維度寫死為 particle、material、energy、thickness，`longitudinal-profile` 例外）、benchmark 輸出 configuration 與目標雜湊（由 run record 的 `extension.simulation.geometry` 推導，不是由 spec/1；`longitudinal-profile` 沒有目標），以及 A1.12 的 enum 修正。它早於本規格：缺 `target_slabs`、`setup-matched`、依 benchmark 宣告的範圍維度、`hash_scheme`、`dependencies.py` 的重新推導與 CV-A1 閘控；閘控寫死 3.6.0（會把新規則追溯套用到 3.6.0–3.12.x 的紀錄，必須改為 CV-A1 的常數）；把 `longitudinal-profile` 寫成 `("reference", ("shower-shape",))`。它在 `5584927` 上仍可套用（dry run；`contracts/validate.py` 偏移 2 行）。

---

## §A.1 名詞與檔案

| 名詞 | 意義 |
|---|---|
| J14 | 既有 journey `examples/geant4-thin-silicon/`：薄矽層研究，唯一有 `validated-in-scope` 紀錄的 Geant4 範例 |
| study record | 帶 `extension.study` 的 computational-run 紀錄；`label` 決定其 artifact label |
| `validated-in-scope` | 經可升級的 benchmark 驗證、且宣告範圍在 benchmark 範圍內時才可有的 label；由 `contracts/validate.py` 的 `_study_upgrade` 把關 |
| 驗證類別 | benchmark 參考的性質（§A.4.4）；A1 定義 reference、setup-matched、sanity、interface；B2 加入 verification、regression，並在 reference 類別附加一個徑跡 benchmark（§B） |
| observable kind | study spec 中受控的觀測量種類（enum），如 `most-probable-value` |
| configuration | 目標的放置情形：`isolated` 或 `embedded`（A1.3） |
| 邏輯 run | 由 spec、後端與邏輯 run 種子 S 決定的 N 個事件，編號 0 … N−1；可切成多個工作（job） |
| 區塊 | 邏輯 run 中依事件編號劃分的 K 段，每段 B 個事件（N = K·B）；batch means 的單位 |
| 三個邊界產物 | run summary（`simulation-summary/1`）、column map（`simulation-columns/1`）、effective config（引擎無關外框加實際幾何樹） |
| `seeding` | `stream`（既有行為）或 `per-event`（每個事件以 H(S, 事件編號) 重設；A2 起） |
| `hash_scheme` | 目標雜湊的推導方式：`spec-v1`（A1，由 spec/1）或 `tree-v1`（A2 起，由幾何樹） |
| evidence 角色 | run 在研究中的用途，存於 `extension.simulation.evidence_role`（不用 `role`：`label` 已寫 `evidence_records[].role = "Geant4 run"`）；A1 定義 trial、nominal、scan、control、variation、calibration；B2 加入 regression；C2 加入 search 與 confirmation |
| 判定引擎 | `core/stats/decisions.py`；A1 提供 `equivalence` 與 `detection_limit`，B2 附加 `change`，C2 附加配對模式；只判定研究層的閘門，需求的判定由 `contracts/design.py` 推導 |
| CV-A1、CV-B2、CV-C1、CV-C2 | 依擁有的階段命名的 contracts minor，號碼在發布時依合併順序決定，都 ≥ 3.13.0（§P.5）；CV-A1 屬 A1 |
| F4 | main 設計流程的保真度：經 `check_geant4_study.py label --upgrade` 重新發出為 `validated-in-scope` 的 Geant4 研究（`system-design-workflow.md` 的 D3） |
| E2 | 有 Geant4 11.4.3 建置的執行環境 |
| IUT | intersection-union test：所有觀測量都等價才通過 |
| DL | negative control 的偵測極限 |
| sci-fix | `docs/maintenance.md` 中修正科學正確性缺陷的流程 |
| 記法 | 「A1.6」「B1.3」「C2.1」是工作項（全文唯一）；「§A.7」「§P.4」「§R.6」是本文件各部的節（§P 第 1 部、§A 本部、§B 第 3 部、§C 第 4 部、§R 第 5 部） |

**主要檔案（相對 `plugins/hep-research/`）：**

| 用途 | 路徑 |
|---|---|
| 契約 | `contracts/validate.py`、`contracts/dependencies.py`、`contracts/schema.py`、`contracts/schemas/ext_computational_run.json`、`contracts/schemas/`（新增 summary 與觀測量的 schema）、`contracts/design.py`（`check_f4` 行 988–1062，只讀） |
| 共用模組（新增） | `core/stats/distributions.py`、`core/stats/batch_means.py`、`core/stats/decisions.py`（steward hep-statistics）；`core/simulation/seeds.py`、`core/simulation/summary.py`（steward hep-detector） |
| 既有 core | `core/status.py`、`core/trace.py`、`core/OWNERS.json`、`core/stats/tail_estimation.py`（`beta_ppf`、`clopper_pearson`）、`core/partition/engine.py`（`NON_ADDITIVE_TOKENS` 行 381）、`core/stats/poisson_diagnostics.py`（`central_interval`，Garwood，行 162）、`core/stats/toy_ensemble.py`（`toy_seed` 行 60、`coverage` 行 160、`coverage_gate` 行 189）、`core/__init__.py`（`CORE_VERSION`） |
| 研究層 | `skills/hep-detector/scripts/check_geant4_study.py`（`convergence()` 行 335、相對差行 357、判定行 359、`scope_within()` 行 482）、`geant4_benchmarks.py`（`GRADES` 行 92–94、`bootstrap()` 行 197、`mpv()` 行 204、偵測極限行 275、MPV 的 bootstrap SE 行 369、`at_limit` 行 678）、`tracker_resolution.py`、`multiple_scattering.py`；`skills/hep-detector/assets/geant4-study-spec.schema.json`；`skills/hep-detector/references/geant4-study-protocol.md`；`skills/hep-detector/scripts/evaluate_design.py`（`f4` 行 498–560）、`skills/hep-detector/references/system-design-workflow.md` |
| adapter | `adapters/geant4/adapter.json`；`adapters/geant4/assets/geant4_run.py`（`SIM_SOURCES` 行 63、`validate_spec()` 行 103、`cmd_scan` 行 435、`cmd_chunk` 行 491、`cmd_summarize` 行 525）、`geant4_build.py`（`GEANT4_USE_GDML: OFF` 行 53）、`geant4_verify.py`、`g4common.py`（既有的 Python 模組）；`adapters/geant4/assets/layered_sim/`（`Actions.cc`：CSV 格式 `%.10g` 行 23、沉積乘 track 權重行 113；`layered_sim.cc`：種子與 run manager 行 149–154；`MiniJson.hh`、`spec.schema.json`、`output.schema.json`） |
| J14 | `examples/geant4-thin-silicon/run.py`、`recorded/`（`events/` 5 個縮減 CSV、`runs/`、`summaries/`、`specs/`）、`output/` |
| 測試 | `tests/contracts/test_geant4_upgrade.py`、`test_simulated_dataset.py`、`test_schema_keywords.py`；`tests/adapters/test_geant4.py`；`tests/examples/test_geant4_thin_silicon.py`；`tests/skills/test_cli_robustness.py`；`tests/skills/hep_detector/test_design_m2.py`（`F4Path` 行 336）；`tests/tools/test_scifix_ledger.py`、`test_scifix_advisories.py`、`test_scifix_schemas.py` |
| 工具 | `tools/run_all_checks.py`、`check_layering.py`、`check_relocation.py`、`check_ownership.py`、`check_packaging.py`、`measure_entrypoints.py`、`reference_inventory.py`、`capability_map.py`、`check_routing_static.py`、`scifix_advisories.py`、`scifix_ledger.py`、`check_wiring.py`、`ci_plan.py`、`run_required_backends.py` |
| sci-fix 紀錄 | `docs/evidence/sci-fixes.json`（`fixes`、`documentation_fixes`、`superseded`）、`docs/evidence/advisories/`、`docs/evidence/schemas/`、`scifix-sources.json`、`scifix-claims.json` |

---

## §A.2 前提與提供的介面

**前提：** 無（任務 A 先做）。

**提供給任務 B、C 的介面**（擁有權見 §P.4）：

| 介面 | 工作項 | 使用者 |
|---|---|---|
| benchmark 表、驗證類別、範圍比對、隔離規則（可附加條目） | A1.1–A1.3 | B2、B3、C2 |
| evidence 角色（可附加角色） | A1.4 | B2、C2 |
| 種子雜湊 H（Python `core/simulation/seeds.py`；C++ `g4sim/SimHash.hh`） | A1.4、A2.1 | 所有模擬程式、`evaluate_design.py search`（C2） |
| `simulation-summary/1`、`simulation-observables/1` 的 schema（`contracts/schemas/`）與讀取（可附加欄位） | A1.5 | B1、B2、C2 |
| `statistical_uncertainty` 的定義（68.27 % 的 t 半寬） | A1.6 | B2 |
| 區塊估計量、精確區間、MPV、分位數 | A1.6、A1.7 | B3、C2 |
| 判定引擎 `equivalence`、`detection_limit`（可附加判定） | A1.8、A1.10 | B2、B3、C2 |
| 兩階段事件數 | A1.9 | B3、C2 |
| `evaluate_design.py f4` 轉傳 `label` 的 run record 並如實回報 | A1.17 | B2、B3、C2 |
| `g4sim` 標頭、`per-event` 種子、探針、`tree-v1`、column map、effective config 存放 | A2.1–A2.5 | B1、B2、C2 |
| schema 關鍵字 `maxItems`、`maximum`、`exclusiveMaximum` | A2.7 | B1、C1 |

附加只能是選用欄位、新的 enum 值或新的函式，不能改變既有行為（§P.2 R2）。

---

## §A.3 硬性限制

違反任何一條都不能合併。

1. **分層。** skill 腳本與 adapter 只 import `core` 與 `contracts`。hep-detector 的腳本與任何 adapter 都需要的程式（統計、判定、種子雜湊、summary 讀取）放在 `core/`，並在 `core/OWNERS.json` 指定 steward；`core/` 不得引用 `skills/`、`adapters/`、`profiles/` 的路徑。`core/` 本身只能 import `core`（`check_layering.py` 第 4–5 行），因此不能使用 `contracts/schema.py`：schema 驗證由呼叫層執行（A1.5）。新的 core 檔案與模組依 `core/OWNERS.json` 的 admission rule 登錄（超過一個頂層使用者）。
2. **實驗名稱。** `skills/`、`contracts/`、`core/` 中不得出現實驗名稱（含 ALICE；`check_layering.py`）；需要時用引用鍵。
3. **Python 只用標準函式庫**，這是刻意的選擇，不是限制（core 的必要環境本來就含 numpy 與 scipy，見 `requirements-core.txt`）：讓 adapter 的腳本與 J14 的重播不依賴科學套件；scipy 只在測試中作為第三方 oracle。不加 Python 綁定。t 與 F 分位數（非整數自由度）以既有的 `beta_ppf` 實作在 `core/stats/distributions.py`（共用的數值函式，不是 §A.9 所說的「新的 core 驗證器」）；Garwood 區間重用既有的 `core/stats/poisson_diagnostics.py` 的 `central_interval`（行 162），不另寫一份。
4. **C++ 依賴。** `g4sim` 的 `SimHash.hh`、`SimSummary.hh`、`MiniJson.hh` 只用 C++17 標準函式庫；`SimSeed.hh`、`SimProbe.hh` 與 `layered_sim` 連結 Geant4。不引入第三方函式庫。
5. **G5 授權邊界。** Python 只和獨立執行檔交換 JSON 與 CSV；程式依 Geant4 API 撰寫，不複製或改寫 Geant4 範例程式碼。
6. **狀態與退出碼**（`core/status.py`）：0 ok、1 負向判定（`refused`/`failed`）、2 無法使用的輸入（`rejected`）、3 `incomplete`。未定案與未達標一律是 3。
7. **execution trace。** 新的紀錄寫入者呼叫 `trace.provenance()`；新的共用函式呼叫 `trace.tag()`；呼叫 C++ 執行檔時記錄執行檔與原始碼的 sha256、版本、子命令。
8. **大小與路徑。** 單檔 ≤ 2 MiB（`check_packaging.py` 掃描所有文字檔）；寫出的路徑經 `tilde()`；plugin README 的大小聲明需在實際值的 10 % 內。
9. **入口預算。** hep-detector quick load ≤ 25,600 bytes（目前 24,669），description ≤ 1,024 字元（`measure_entrypoints.py` 回報 1,016）。本任務不修改 `skills/hep-detector/SKILL.md` 與 description。
10. **流程。** A1 依 sci-fix 流程；A2 依 adapter 變更流程；兩者都依 release 步驟。每個階段在自己的 isolated worktree 與分支（`worktree-geant4-a1`、`worktree-geant4-a2`）中工作（§P.10）；A1 的每個修正以單獨的 `sci-fix:` commit（S4 用 `robust-fix:`）提交，讓 ledger 的 `commits` 與 parent record 指向它（A1.14）；未經維護者核准不推送 `main`、不開 pull request。
11. **契約版本。** 新規則以 `strict or _at_least(contract_version, CV-A1)` 閘控，不設 warning 分支。
12. **J14 的離線重播** 永遠可以執行，且不需要 Geant4 與編譯器。
13. **不改既有輸出。** A2 只新增檔案與選用欄位；J14 既有 spec 的 CSV 必須和 A2 前逐位元相同（同一主機）。
14. **不做：** 整數量化、128 位元整數、逐位元相同的統計量、spec 格式轉換、`simstat`、不連結 Geant4 的 `simcore`（理由見 §R.13）。

---

## §A.4 設計摘要

### §A.4.1 已確認的缺陷（`9f08796` 發現，`5584927` 上仍存在）

| # | 缺陷 | 位置 | 後果 | 工作項 |
|---|---|---|---|---|
| D1 | 範圍檢查不比對觀測量；宣告缺少的維度不受限制 | `validate.py` `_scope_inside()`（行 351 起）；`check_geant4_study.py` `scope_within()`（行 482–493） | 用 MPV benchmark 通過的研究可以把其他觀測量標成 `validated-in-scope` | A1.2 |
| D2 | benchmark 的等級由紀錄自己宣告 | `_study_upgrade`（行 397；篩選行 421） | 寫 `"grade": "reference"` 就能升級 | A1.1 |
| D3 | negative control 在不同單位間比較、只測單向 | `geant4_benchmarks.py` 行 678 | 偵測極限在觀測量上未被證明 | A1.10 |
| D4 | 收斂閘門無等價檢定 | `check_geant4_study.py` 行 359 | 真實差值等於容許值時約 50 % 通過 | A1.8 |
| D5 | MPV 的 SE 用 bootstrap | `geant4_benchmarks.py` 行 369 | 變異數估計不一致；J14 的偵測極限建立其上 | A1.6、A1.7 |
| D6 | 停止規則未禁止依結果加跑 | protocol 第 4 節 | optional stopping 偏差 | A1.11 |
| D7 | 證據相關性未揭露 | J14 的 nominal run 被閘門、統計目標、benchmark、variation 共用 | 被當作獨立證據 | A1.11 |
| D8 | study spec 的 benchmark enum 缺 `shower-containment` 與 `longitudinal-profile` | `geant4-study-spec.schema.json`；`GRADES` 9 個、enum 7 個 | 一致性缺口 | A1.12 |
| D9 | 研究層綁死 `layered_sim` 的資料格式 | `derived()` 讀 `geometry.layers`；`summarize` 與 benchmark 讀固定欄名 | 其他後端無法進入 | A2.6 |
| D10 | 測試順序相依 | `test_geant4_upgrade` 的 `tearDownModule` 刪除共用的 J14 重播目錄，`test_simulated_dataset` 的 5 個測試出錯 | 錯誤依執行順序而定 | A1.12 |
| D11 | 收斂閘門只在「已提供的 summary」中取最細的兩個值；缺少最細的掃描點時以較粗的點通過 | `check_geant4_study.py` `convergence()` 行 341–348；protocol 第 93–95 行已記載，要求使用者自行補齊 | 太粗的 cut 可以通過唯一能抓到它的檢查 | A1.16 |

### §A.4.2 兩個平面

逐事件的處理在 C++（模擬程式；A2 起包括 summary 的累加）；合併後的推論、判定、紀錄、契約在 Python。同一個量只有一份正式實作；另一種語言的實作只能在測試中作為 oracle。A1 的 summary 由 Python 從逐事件 CSV 產生；A2 起由 `layered_sim` 產生，Python 產生器只留在測試中。

### §A.4.3 重現的定義

| 層次 | 要求 |
|---|---|
| 追溯 | 每份紀錄保存 spec、effective config、程式（`sources_sha256`）、種子、輸入與輸出檔案的雜湊 |
| 重新執行 | 同一建置與平台、同一邏輯 run：事件內容相同；summary 的整數累加量相同，浮點相對差 ≤ 1e-12 |
| 重播（由已提交的 summary 與紀錄） | 判定與 label 完全相同；數值相對差 ≤ 1e-9；判定邊距 < 1e-9（相對）時在紀錄中標記「接近門檻」 |
| 回歸檢查（A2） | J14 既有 spec（`seeding: stream`）在同一主機上產生和 A2 前逐位元相同的 CSV |

### §A.4.4 驗證類別

| 類別 | 參考 | 能否升級 | 引入 |
|---|---|---|---|
| reference | Geant4 所近似的物理模型或薄靶量測，在 isolated 目標上 | 能（範圍內） | A1（CV-A1） |
| setup-matched | 已發表的量測，目標雜湊和量測配置相同，且 isolated | 能（範圍內） | A1（CV-A1） |
| sanity、interface | 合理範圍、介面檢查 | 不能 | 既有 |
| verification | 輸入的精確推論（解析螺旋、運動學） | 不能 | B2（CV-B2） |
| regression | 前一個版本的同一研究 | 不能 | B2（CV-B2） |

B2 另在 reference 類別附加一個徑跡 benchmark（孤立 Si 片中的多重散射角寬度），作為偵測器層級研究成為 F4 的資格路徑的一部分（§P.7 的 D0、§B）。原計畫的 surrogate 類別已刪除：main 的保真度與 bound 模型已涵蓋快速模擬。

### §A.4.5 `core/` 中的共用模組

| 模組 | A1 的內容 | 之後附加 |
|---|---|---|
| `core/stats/distributions.py` | `t_ppf`、`f_ppf`（非整數自由度）；Garwood 不在這裡，重用 `poisson_diagnostics.central_interval` | — |
| `core/stats/batch_means.py` | 區塊估計量、SE、共變異、精確區間、直方圖分位數、MPV | C2：`values` 的經驗分位數 |
| `core/stats/decisions.py` | `equivalence`（IUT 閘門）、`detection_limit`；回傳 `{verdict, margin, reason}`，`reason` 取自封閉清單 | B2：`change`；C2：配對模式（只判定研究層的閘門與搜尋值；需求的判定在 `contracts/design.py`） |
| `core/simulation/seeds.py` | 種子雜湊 H、邏輯 run 種子、工作種子；文件說明 H 與既有 `toy_ensemble.toy_seed` 的差別（H 的值域 [1, 2³¹ − 1] 是 Geant4 引擎可接受的種子，`toy_seed` 是 63 位元；兩者都由 SHA-256 推導、都與切分無關） | — |
| `core/simulation/summary.py` | `simulation-summary/1` 的讀取、依區塊合併、累加器存取；不做 schema 驗證（schema 在 `contracts/schemas/`，由呼叫層以 `contracts.schema.validate` 驗證） | C2：`values` 欄位 |

hep-detector 的 `check_geant4_study.py` 與 `geant4_benchmarks.py` 改為呼叫這些模組；之後的任務也呼叫同一份實作。

`core/OWNERS.json`：`stats` 模組的 `files` 加入 `distributions`、`batch_means`、`decisions`（模組已有多個使用者）；新增 `simulation` 模組（steward hep-detector；使用者 `skills/hep-detector/scripts/check_geant4_study.py` 與 `adapters/geant4/assets/geant4_run.py`、`summary_from_csv.py`，滿足 admission rule）。`CORE_VERSION` 在 A1 升 minor（1.0.0 → 1.1.0；`docs/maintenance.md` 的 Versioning）。A1.15 的覆蓋率 toy 以 `toy_ensemble` 的 `run`、`coverage`、`coverage_gate` 執行。

---

## §A.5 階段 A1：正確性修正（contracts CV-A1，sci-fix）

A1 只改 Python。統計量由 Python 從逐事件 CSV 產生的 summary 計算；A2 起改讀 `layered_sim` 寫出的 summary。

### A1.1 benchmark 表（D2）

**修改：** `contracts/validate.py`（新增常數表；`_study_upgrade` 只從表取得類別、kind 與範圍維度）；`geant4_benchmarks.py`（`GRADES` 保留給工具，值改為表的類別，加一致性測試）。

**等級即類別。** 表的第二欄同時是紀錄中 `grade` 欄位應有的值。

| benchmark | 類別 | 支持的 kind | 範圍維度（型別） |
|---|---|---|---|
| `stopping-power` | reference | `stopping-power` | particle（類別）、material（類別）、energy（區間）、thickness（區間） |
| `range` | reference | `range` | 同上 |
| `thin-layer-mpv` | reference | `most-probable-value` | 同上 |
| `thin-layer-width` | sanity | `thin-layer-width` | 同上 |
| `multiple-scattering` | sanity | — | — |
| `em-shower-shape` | sanity | — | — |
| `shower-containment` | sanity | — | — |
| `longitudinal-profile` | setup-matched | `shower-maximum`（新增的 kind，只量 t_max） | particle（類別）、energy（區間）、目標雜湊 |
| `published-data` | interface | — | — |

**規則：**
- 紀錄中的類別或等級和表不一致、或 benchmark 名稱不在表中：error。適用所有帶 Geant4 study 區塊的紀錄。
- 只有 reference 與 setup-matched 會被 `_study_upgrade` 計入。
- 支持的 kind 與範圍維度只以表為準；工具輸出的值只供閱讀。
- 表的 9 個名稱和目前的 `GRADES` 相同；`GRADES` 的值改為表的類別，唯一的改變是 `longitudinal-profile`：reference → setup-matched（行 92–94）。study spec 的 grade enum 加入 `setup-matched`（A1.12）。
- 表可在之後的契約版本附加條目（B2：verification、regression 與徑跡 reference benchmark）。
- J14 的判定不變，但 study 與 benchmark 檔案的內容會改變（新欄位；`code_paths` 多出 `contracts/validate.py`）。

### A1.2 範圍檢查（D1）

**修改：** `contracts/validate.py`（唯一實作，匯出）；`check_geant4_study.py`（匯入，刪除 `scope_within()`；`label` 寫 `declared_scope.observable_kind`）；study spec schema（`validation_plan.scope` 是 `additionalProperties: false`，加入 `observable_kind`、`target_geometry_sha256`、`hash_scheme`）。

**規則：**
- 比對受控的 `observable.kind`，不比自由文字。
- 宣告的 kind 必須在被計入 benchmark 的支持 kind 之內。
- 維度清單依 benchmark（A1.1 第四欄）；類別維度比集合包含，區間維度比區間包含；純量視為 [v, v]。
- benchmark 有的維度，宣告範圍都必須有；缺少視為超出範圍。
- 以目標雜湊為維度時，宣告範圍必須帶相同的 `target_geometry_sha256` 與 `hash_scheme`。
- 閘控：`strict or _at_least(contract_version, CV-A1)`；低於 CV-A1（目前 ≤ 3.12.x；J14 的研究紀錄已以 3.12.0 寫出）的紀錄只在 `--strict` 下受約束，且只有帶 `validated-in-scope` 的紀錄會失敗。

### A1.3 configuration 與隔離

**修改：** `geant4_benchmarks.py`（輸出）；`contracts/validate.py`（規則）；`contracts/dependencies.py`（重新推導）。

- `geant4_benchmarks.py` 為每個 benchmark 結果輸出 `configuration`、`target_geometry_sha256`、`hash_scheme: spec-v1`、`configuration_basis`，從 benchmark 設定的 `run_record` 所指 run record 的 spec/1 推導，不接受使用者輸入。計入升級的 benchmark 必須有 `run_record`。
- **目標：** benchmark 設定宣告 `target_slabs`（目標包含的 slab 名稱，含吸收層）。單層 benchmark 預設為被量測的那一片；`longitudinal-profile` 必須明列整個取樣堆疊（它的 `layers` 只列讀出欄位）。
- **真空：** 世界材料為 `G4_Galactic`，或密度 < 1e-20 g/cm³。
- **isolated：** 世界是真空，世界以外的每個放置都屬於目標；spec/1 沒有場，視為無場（場的規則在任務 B 生效：只有附加在目標內的場屬於目標並計入雜湊）。否則為 embedded。
- **`spec-v1` 的正規形式：** 依序的 slab、厚度、橫向尺寸、材料名稱與宣告的組成；重複放置逐一列出；數值以 Python `float.hex()`；對這個清單的 JSON（鍵排序、無空白）取 sha256。
- **契約規則（CV-A1）：** 被計入的 reference benchmark 必須 isolated；被計入的 setup-matched benchmark 必須 isolated，且目標雜湊與 `hash_scheme` 和 benchmark 的量測配置相同。缺少或 embedded 都是 error。`dependencies.py` **必須**從 `evidence_records` 中的 run record 重新推導並比對。
- 殘餘限制（寫入 protocol）：J14 的 recorded CSV 是縮減版，雜湊對不上 run record 的 `output_hashes`；configuration 描述的是設定檔指名的 run record。negative control run 的幾何不另外檢查。

### A1.4 邏輯 run、種子與角色

**修改：** 新增 `core/simulation/seeds.py`；`check_geant4_study.py`、`geant4_run.py` 呼叫它。

- **H 的定義**（Python 與 C++ 必須相同；C++ 在 A2.1 的 `SimHash.hh`）：H(x₁, …, x_n) = int.from_bytes(sha256("\x1f".join(str(x) for x in (x₁, …, x_n)).encode("utf-8"))[:8], "big") % (2³¹ − 1) + 1，值在 [1, 2³¹ − 1]；整數以十進位、無前導零寫成字串。
- 每個證據點是一個邏輯 run，種子 S = H(study_id, role, point_id)；正負兩向的控制組用不同的 point_id。
- **存放：** run record 的 `extension.simulation` 加入 `evidence_role`、`point_id`、`logical_run_seed`（S）與 `seed_scheme`（`hash-v1` 或 `legacy`）；A2 起執行用 spec 也寫入 `run.logical_run_seed`（A2.2）。
- A1 的新錄製一律 `seeding: stream`（`layered_sim` 現有行為）；單一工作的種子對為 (H(S, 0, 0), H(S, 0, 1))。不使用 `make_manifest` 的 `seed × 100003 + k`、`cmd_scan` 的 `[s0, s1 + k]`、`cmd_chunk` 的 `start + 1`。
- 一個邏輯 run 可以切成多個工作（`geant4_run.py chunk` 以手動建立的 manifest，每個工作涵蓋一段事件編號）：起始事件為 e 的工作，種子對為 (H(S, e, 0), H(S, e, 1))；`cmd_chunk`（行 504 的 `seeds=[max(1, args.seed), args.start + 1]`）改為以這個種子對執行，並在 manifest 中寫入該工作的種子 H(S, e, 0)。同一 manifest 內的種子因此彼此不同，`validate_manifest` 的 `partition.duplicate_seed` 檢查不需修改。`stream` 模式下不同切法的事件不同，但統計上等價。
- **角色：** `extension.simulation.evidence_role` 取自 evidence 角色 enum（trial、nominal、scan、control、variation、calibration）；未知的角色是 error（CV-A1 閘控）。欄名不用 `role`：`label` 寫的 `evidence_records[].role = "Geant4 run"`（`check_geant4_study.py` 行 623）是另一個意思。enum 可在之後附加（B2 的 regression、C2 的 confirmation 與 search 角色）。
- **唯一性：** 同一研究的所有 run record 中 S 不重複（`check_geant4_study.py` 檢查）。A1 不重錄的 5 個 J14 run（A1.13）沒有 S：它們的 run record 不改寫；study record 中以原本的種子對（第一個種子 1401 或 1402）登記為 `seed_scheme: legacy`，只檢查完整種子對不重複。

### A1.5 summary、觀測量宣告與 Python 產生器

**修改：** 新增 `core/simulation/summary.py`（`simulation-summary/1` 的讀取、依區塊合併、累加器的存取；不做 schema 驗證，因為 `core/` 不能 import `contracts`）；在 `contracts/schemas/` 新增 `simulation-summary/1` 與 `simulation-observables/1` 的 schema（CV-A1；檔名在實作時定；只用 `contracts/schema.py` 支援的關鍵字，由 `tests/contracts/test_schema_keywords.py` 涵蓋）；新增 `adapters/geant4/assets/summary_from_csv.py`（或 `geant4_run.py` 的子命令 `summarize-blocks`），以 `core/simulation/summary.py` 寫出與合併，並以 `contracts.schema.validate` 驗證寫出的 summary（`check_geant4_study.py` 讀入時同樣驗證）；`summary_from_csv.py` 登錄在 `tests/skills/test_cli_robustness.py` 的 `MISSING_FILE_ARGS`。

- **觀測量宣告 `simulation-observables/1`：** 陣列，每項 `{name, source_column, selection, bins: {lo, hi, width}, thresholds, tolerance_mode, tolerance}`。`selection` 是對 CSV 欄位的宣告式篩選（欄名、比較子 `==`、`!=`、`<`、`<=`、`>`、`>=`、值；多個條件為 AND）；`thresholds` 給 `count_if` 用（計數 x > threshold 的事件，嚴格大於，和 `check_geant4_study.py` 的 `tail_fraction` 相同）；`tolerance_mode` 與 `tolerance` 見 A1.8。study spec（A1.12）與模擬程式的 `output.observables`（A2.3、B1.1）都引用它。
- **輸入：** 一個或多個工作的逐事件 CSV、觀測量宣告、區塊大小 B 與區塊數 K。
- **選擇：** 每個觀測量只累加滿足其 `selection` 的事件（宣告必須重現現行程式的選擇：`check_geant4_study.py` 中只有 `mpv_loss_MeV` 要求 `primary_fate == 1`（行 284），`mpv_deposit_MeV` 與 `tail_fraction` 使用全部事件（行 277–282）；benchmark 的 `transmitted()` 另要求 `primary_fate == 1` 且 `primary_end_process == "Transportation"`（`geant4_benchmarks.py` 行 232–236））；`n` 是通過選擇的事件數，另記錄每個區塊的總事件數。
- **區塊：** 事件 i（`event` 欄減去邏輯 run 的第一個事件編號）屬於區塊 ⌊i/B⌋；i ≥ K·B 的事件忽略並註明數量。
- **每個區塊、每個觀測量的累加器：** 整數 `n`、直方圖每格計數（固定分格；溢位與下溢分開）、`count_if[]`（x > threshold）；浮點 Σx、Σx²、`min`、`max`（Neumaier 補償加總）。
- **輸出欄位：** `summary_version`、`run`（邏輯 run 的識別與種子、`evidence_role`、事件範圍、`seeding`、B、K、spec 雜湊、產生者 `python-csv` 與版本）、`observables[]`、每個累加器的 `merge` 規則（`sum`、`min`、`max`、`hist`）。多個工作依區塊編號合併。schema 允許附加選用欄位（C2 的 `values`）。
- **事件權重：** CSV 有 `weight` 欄時必須全為 1，否則 exit 2（沉積已乘 track 權重，見 `Actions.cc` 行 113）。沒有 `weight` 欄時（J14 的 5 個縮減 CSV 就沒有），summary 記錄 `weight_column: absent`，並以 run record 的 spec 中沒有 biasing 指令作為依據；spec 中有 biasing 指令時 exit 2。
- A2 起 `layered_sim` 以相同 schema 寫出 summary；這個 Python 產生器只留在測試中作為 oracle。

### A1.6 估計量與 SE（D5）

**修改：** 新增 `core/stats/distributions.py` 與 `core/stats/batch_means.py`；`check_geant4_study.py`、`geant4_benchmarks.py` 改為呼叫它們（只讀 summary；刪除 `bootstrap()` 的正式使用，保留在測試中作為對照）。

- 每個區塊 b 算 θ_b；回報 θ̄ = 平均，SE = sd(θ_b)/√K，自由度 K − 1。K ≥ 16，在第一個證據 run 前宣告。
- 多個觀測量：每個區塊的估計量向量一起保存，共變異由這些向量估計。
- 全樣本值：平均與比例另由合併累加器算出，和 θ̄ 的差寫入紀錄作為診斷。
- 分位數：直方圖內線性內插；分格寬度除以估計值須小於相對容許值的 1/10；落在溢位或下溢格時判為 incomplete。
- **計數很少時：** 計數型估計量在任一區塊為 0 或合併總數 < 100（門檻可宣告）時，改用合併累加器上的精確區間：比例用 Clopper–Pearson（既有的 `clopper_pearson`），計數用 Garwood（既有的 `poisson_diagnostics.central_interval`）；兩個 run 的比較用條件二項法求率之比的區間，相對差 = 比 − 1（對 Poisson 計數是精確的；用於比例時只是近似，因為分母固定，protocol 註明）。這時沒有 SE，閘門以區間端點判定（A1.8）。
- **F4 用的不確定度：** 研究紀錄寫出的 `statistical_uncertainty`（B2 起寫在 `results.<figure of merit>`）定義為 68.27 % 的 t 半寬 t_{0.84135}(K − 1)·SE（K = 16 時約 1.03·SE），讓 `contracts/design.py` 把純量讀成覆蓋率 0.6827 的高斯（行 1050–1052）時涵蓋率正確。計數很少的精確分支沒有 SE，寫出不對稱的區間；`f4` 接受不對稱或精確不確定度是 B2 的變更（CV-B2）。
- 前提：事件之間沒有狀態。探針（A2）記錄 biasing 等設定；A1 中 J14 符合此前提。

### A1.7 MPV（D5）

**修改：** `core/stats/batch_means.py`。

- 每個區塊的直方圖取最大格，以它和相鄰兩格做三點拋物線內插求眾數；回報 K 個眾數的平均與 SE（A1.6）。這取代現行 `mpv()` 的五點最小平方擬合，在 S1 的 ledger 條目中註明。
- **邊界情形：** 分格的原點與寬度取自觀測量宣告的 `bins`；最大格有並列時取編號最小者；最大格是第一或最後一個有效格、或分母 y₋ − 2y₀ + y₊ = 0 時，該區塊的眾數取最大格的中心並計數記錄；這類區塊超過 K/4 時該 benchmark 判為 incomplete。
- **設計時：** 在宣告的 B 與分格寬度下以 toy 估計偏差；toy 的 95 % 上界須 ≤ tol/10。toy 用 Landau–Vavilov 分布，並以一次高統計 Geant4 run 的直方圖形狀核對。
- **每次執行：** 以合併直方圖的三點內插眾數 m 為基準，|θ̄ − m|/|m| ≤ tol/5 + 2·SE/|m|（tol 為相對容許值）；否則該 benchmark 判為 incomplete。
- 區塊的 MPV 不得經 partition 的合併規則（`mpv` 不在 `NON_ADDITIVE_TOKENS` 中）；只從 summary 的直方圖計算。

### A1.8 收斂閘門與判定引擎（D4）

**修改：** 新增 `core/stats/decisions.py`（`equivalence`）；`check_geant4_study.py` 的 `convergence()` 與 `cmd_run` 改為呼叫它。

- **判定引擎的介面：** 每個判定都有 SE 分支與計數很少時的精確區間分支，都接受多重性 m，都回傳 `{verdict, margin, reason}`，`reason` 取自封閉清單。A1 實作 `equivalence(diff, se, ν, tol, m) → pass／fail／unresolved` 與 `detection_limit`（A1.10）；B2、C2 依同一介面附加其他判定。
- **差值：** 沿用行 357 的慣例：a 為最細的設定，b 為第二細的設定（宣告值由小到大排序，a、b 為前兩個；A1.16）。觀測量宣告 `tolerance_mode`：`relative`（預設）時 diff = (a − b)/b、se_diff = √(se_a² + se_b²)/|b|；`absolute` 時 diff = a − b、se_diff = √(se_a² + se_b²)，tol 取觀測量宣告的 `tolerance`（同觀測量的單位；`absolute` 時必填）；`relative` 時 tol 為 study spec 的 `tolerance_relative`。ν 以 Welch 公式逐對計算（等變異數、K = 16 時為 30）。（`absolute` 的第一個使用者是 B3；因為它只是同一個函式的選項，放在 A1 以免之後改變閘門的定義。）
- **事件數目標：** 每個點的 se 目標為 tol/(4√2)（`relative` 時為相對 se）。
- **判定：** 通過 |diff| + t₀.₉₅(ν)·se_diff ≤ tol，**且兩個點都達到 se 目標**；失敗 |diff| − t_{1−α/m}(ν)·se_diff > tol（α = 0.05，m 為（參數 × 觀測量）組數；未達 se 目標也可以判失敗，因為較大的 se 只會讓失敗更難成立）；其他為 unresolved。計數很少時：通過 = 90 % 區間落在 [−tol, tol] 內；失敗 = 單邊 1 − α/m 區間完全落在外側。
- **回報：** unresolved 與未達標以 `incomplete`（exit 3）回報，label 保持 `unvalidated`；只有失敗是 `failed`（exit 1）。目前把非 pass 一律當 `failed`，需要修改。

**操作特性**（以 `gate_operating_characteristics.py` 重算，每格 2×10⁶ 次 toy。「se = 目標」：se_diff 等於目標、以 ν = 30 估計，只含 TOST 部分（不含「兩點都達標」的條件）；「兩階段」：兩個點各依 A1.9 設計，K = K_trial = 16，ν 以 Welch 公式由估計的 se 計算）：

| 真實差值 | 通過（se = 目標，只含 TOST 部分） | 通過（兩階段） | 通過（兩階段，兩點都達標的條件下） | 失敗 m = 1（se = 目標） | 失敗 m = 30（se = 目標） | 失敗 m = 30（兩階段） |
|---|---|---|---|---|---|---|
| 0 | 0.976 | 0.809 | 0.999 | 0.000 | 0.000 | 0.000 |
| tol/2 | 0.621 | 0.696 | 0.860 | 0.000 | 0.000 | 0.000 |
| tol | 0.050 | 0.044 | 0.054 | 0.050 | 0.002 | 0.002 |
| 2 tol | 0.000 | 0.000 | 0.000 | 0.988 | 0.780 | 0.952 |

- 兩階段設計下約 19 % 的點對至少一點未達標，因此真實差值為 0 時通過率只有 0.809。
- 真實差值為 tol 時，無條件的通過率 0.044 ≤ 0.05；在兩點都達標的條件下是 0.054，略高於名義的 0.05（達標的點 se 偏小），在 protocol 中揭露。
- 真實差值為 tol 時約 90 % 是 unresolved；protocol 寫明預期的 incomplete 比例。

### A1.9 兩階段事件數

- 每個證據點先錄一個 trial run（角色 trial，K_trial = 16，事件數 N_trial 事先宣告），再定 N = ceil(N_trial·(SE_trial/target)²·f)，進位到 K 的倍數（B = N/K 為整數）；f = F₀.₉₀(K − 1, K_trial − 1)（兩者都是 16 時 ≈ 1.97）。
- 約 10 % 的證據 run 會未達標，判為 incomplete，**不得補跑**（若維護者選 F₀.₉₅ ≈ 2.40，約 5 %，事件數多約 22 %；§P.7 第 4 項）。
- 未達標是逐 run 獨立的：收斂閘門的一對點約 19 % 不完整；需要 n 個有 se 目標的 run 的研究，全部達標的機率約 0.9ⁿ（n = 6 時約 0.53）。protocol 寫明這一點。
- A1 不重錄的 5 個 J14 run 事件數固定，不是依本設計規劃的；它們的 se 仍和目標比較，未達標時同樣判為 incomplete。
- 計數很少時，以 trial run 的 Poisson 變異數規劃。

### A1.10 negative control 與偵測極限（D3）

**修改：** `geant4_benchmarks.py`；偵測極限的計算在 `core/stats/decisions.py` 的 `detection_limit()`。

- 判定量：shift = (control − nominal)/reference，SE 由兩個 run 合成。
- **抓到（caught）：** 控制組的 benchmark 判定為失敗，即 |rel_c| > tol（rel_c 為控制組相對參考值的偏差）；和現行程式以控制組 benchmark 判定的做法一致（`geant4_benchmarks.py` 約行 672）。
- 偵測極限：DL = tol + |rel| + t_{0.977}(ν)·se_rel（取代行 275 的 `2 * se_rel`）。tol 為該 benchmark 的總容許值（`_tol()` 回傳的 total，行 261–269）；rel 為 nominal 相對參考值的偏差；se_rel = √(se_control² + se_nominal²)/|reference|，即 shift 的合成 SE；ν 為其 Welch 自由度。toy 使用同樣的定義。
- 設計要求：toy 證明在 DL 注入時抓到的機率 ≥ 0.977。依上述定義，真實檢定力在 0.977 附近（審查者的計算約 0.9785），所以 toy 的驗收門檻是 0.977 − 3σ_MC（A1.15）。
- 正負兩個方向都注入；否則把宣稱限縮為單向，寫入 `scope.detection_limit_sign`。位於偵測極限 = caught 且 |shift| ≤ 1.1 × DL。
- 單次未抓到時記錄並說明，不自動失敗；不得換種子重跑。
- J14 現有控制組只注入 +密度；在負方向控制組錄製前，兩個 J14 宣稱限縮為 `detection_limit_sign: "+"`。

### A1.11 停止規則、證據相關性與 trace（D6、D7）

- protocol 第 4 節：停止規則、掃描格點、K 與 B、unresolved 的處理，在第一個證據 run 前寫入 study spec。
- `extension.study.evidence_overlap` 列出被多個判定共用的 run，附 `evidence_overlap_version`。
- trace tag（小寫連字號）：`geant4-scope-kind`、`geant4-configuration`、`geant4-convergence-iut`、`geant4-batch-means`、`geant4-mpv-block`、`geant4-seed-hash`、`geant4-convergence-complete`。`check_geant4_study.py` 改 import `contracts.validate` 後，`code_paths` 會多出 `contracts/validate.py`，這是預期的變化。

### A1.12 其他修正（D8、D10）

- study spec 的 benchmark enum 補上 `shower-containment` 與 `longitudinal-profile`；grade enum（目前為 reference、sanity、interface）加入 `setup-matched`；observable kind enum 加入 `shower-maximum`；`validation_plan.scope` 加入 `observable_kind`、`target_geometry_sha256` 與 `hash_scheme`（setup-matched 用，A1.2）。
- study spec（頂層 `additionalProperties: false`）新增頂層屬性：`observables`（引用 `simulation-observables/1`；`name` 必須和 `convergence_plan.observables` 中的名稱相同，例如 `mpv_deposit_MeV`）與 `blocks: {K, B}`。既有的單數 `observable` 不變，仍是研究的主觀測量。
- `ext_computational_run.json` 在 schema 中宣告既有的 `simulation` 屬性（J14 的 run record 已帶 `extension.simulation`，`_study_upgrade` 也已檢查它；需 hep-computing 同意）。`study` 目前是開放物件（行 90–92）；若 CV-A1 宣告它的結構，必須保持開放：`results`、`tail_sources_simulated`（B2 寫出，`contracts/design.py` 的 `check_f4` 讀取）與 `evidence_overlap` 都是選用欄位。
- D10：`test_geant4_upgrade` 與 `test_simulated_dataset` 不再共用會被刪除的暫存目錄（各自建立重播，或改為 package 層級的 fixture）。

### A1.13 J14 的重產與錄製

| run 類型 | 現況 | A1 的做法 |
|---|---|---|
| 有逐事件 CSV 的 5 個 run（`events/`，含 `event` 欄） | 單一縮減 CSV | 不重錄：以 A1.5 的產生器離線切區塊，產生並提交 `simulation-summary/1` |
| 13 個掃描、variation 與情境 run（例如 `mpv-cut-0.1`、`sp-em-option3`、`mpv-density-10`） | 只有 `geant4-run-summary/1`（一個值加 bootstrap SE） | 在 E2 以 `seeding: stream` live 重錄（事件數依 A1.9）；產生並提交 summary；CSV 不提交 |
| 負方向（−密度）控制組 | 不存在（既有的 `mpv-control`、`sp-control` 只注入 +密度） | 在 E2 新錄製，提交 summary |
| trial run | 不存在 | live 錄製的每個點先在 E2 錄 trial run（A1.9），提交其 summary，作為事件數的依據 |

- 重播：`examples/geant4-thin-silicon/run.py` 改由已提交的 summary 計算，符合 §A.4.3 的重播要求；不需要 Geant4 與編譯器。
- 舊的 `geant4-run-summary/1` 檔案保留，只供舊紀錄重播。
- J14 的兩個研究都提供全部三個宣告的 cut 值（0.01、0.03、0.1 mm），A1.16 不改變它們的閘門判定。
- recorded 的大小在 A1 中量測（以 bytes 計，不用 `du` 的區塊用量）；單檔受 `check_packaging.py` 的 2 MiB（2,097,152 bytes）限制；整個 `recorded/` 的上限由維護者決定（§P.7 第 5 項）。

### A1.16 收斂閘門的掃描點完整性（D11）

編號在 2026-10-24 加入；為了不改動既有引用，不重新編號。

**修改：** `check_geant4_study.py` 的 `convergence()`（行 335 起；`vals` 在行 341–348）；protocol 第 93–95 行。

- 每個參數的宣告值（`convergence_plan.parameters[].values`）都必須有角色 scan 或 nominal 的 summary；缺少任何一個時，該參數的閘門為 `incomplete`（exit 3），`reason: missing-scan-value`，並列出缺少的值。
- 「最細的兩個」取宣告值中最細的兩個（宣告值由小到大排序取前兩個；A1.8 的 a、b 依此定義），不再取已提供的 summary 中最細的兩個。
- protocol 第 93–95 行目前要求使用者自行補齊並核對 `two_finest`；改為說明程式會檢查。
- trace tag `geant4-convergence-complete`。
- J14 的判定不變（A1.13）。
- ledger：S2（改變判定），條目 `geant4-gate-scan-completeness`（A1.14）。

### A1.17 F4 消費端的相容

main 0.37.0 起，`evaluate_design.py f4 --label-spec …` 先以 `check_geant4_study.py label --upgrade` 重新發出研究紀錄，再讀 `extension.study.results.<figure of merit>`（`evaluate_design.py` 行 498–560）；`contracts/design.py` 的 `check_f4`（行 988–1062）只計 `validated-in-scope` 的紀錄（行 1004）。這條路徑目前無法完成：`f4` 不傳 `--run-record`，`label` 因此以「no run record to reference as evidence」拒絕升級（`check_geant4_study.py` 行 564–569），但仍 exit 0 並寫出 `unvalidated` 紀錄；接著 `f4` 因紀錄沒有 `results` 以 exit 2 失敗（`evaluate_design.py` 行 530–532）。A1 改變 `label` 的升級規則，所以由 A1 修正消費端，讓結果如實回報；`results` 與尾部來源的寫出是 B2 的工作。

**修改：** `skills/hep-detector/scripts/evaluate_design.py`（只改 `f4` 子命令）、`system-design-workflow.md` 的 F4 列；測試。

- `f4` 新增 `--label-run-record REL`、`--label-reference-record REL`（都可重複）與 `--label-variations REL`，原樣轉傳為 `label` 的 `--run-record`、`--reference-record`、`--variations`。
- `label` 的結束碼依 §A.3 第 6 條；`f4` 把 `label` 的 exit 3 對應為 `incomplete`（exit 3），exit 1 為 `failed`，exit 2 為 `rejected`；目前任何非零都當 `failed`（行 508）。
- 重新發出的紀錄不是 `validated-in-scope`（升級被拒）時，`f4` 回報 `incomplete`（exit 3）並附 `label` 的 `upgrade.refused` 理由，不再落到之後「紀錄沒有 `results`」的使用錯誤；紀錄是 `validated-in-scope` 但沒有 `results.<figure of merit>` 時同樣回報 `incomplete`，理由 `results-missing`（B2 之前的正常情形）。
- `label` 本身在升級被拒時維持現行行為：exit 0，寫出 `unvalidated` 紀錄，回報 refusal。
- 測試（`tests/skills/hep_detector/`，依 `test_design_m2.py` 的 `F4Path` 作法，用合成的設計專案與 J14 形式的研究紀錄）：(a) run record 經 `f4` 轉傳到 `label`；(b) 升級被拒時 `f4` 是 `incomplete` 並列出理由；(c) 升級成功但沒有 `results` 時是 `incomplete`、`results-missing`；(d) 既有的 `F4Path` 測試不變地通過。完整的正向路徑（`geometry → 研究 → label --upgrade → f4` 得到 F4 evaluation）在 B2 測試。
- 依 `docs/maintenance.md`，把錯誤變成結論屬 S4（`robust-fix:`）：需要回歸測試與 parent record，不需要 advisory（ledger 條目 `design-f4-label-passthrough`，A1.14）。`evaluate_design.py` 沒有 tool contract，不需更新 `contracts/tool_contracts/`。

### A1.14 版本與 sci-fix 流程

- **版本：** contracts CV-A1（minor）。新增閘控規則族的先例（2.4.0、2.6.0、2.8.0、3.1.0、3.2.0）都是 minor。
- **commit：** 每個修正一個 `sci-fix:` commit（S4 用 `robust-fix:`），附它的回歸測試；ledger 的 `commits`（`parent`、`fix`、`follow_up`，40 字元雜湊）指向它（`docs/maintenance.md` 第 219–227 行）。
- **ledger（`docs/evidence/sci-fixes.json`）：** 一筆只記一個修正（第 226 行；合併多個修正的條目要拆開，舊 id 留在 `superseded`）。`fixes` 的每筆含 `id`、`title`、`changelog`（合併前 `{"kind": "unreleased"}`）、`severity`、`evidence_tests`、`oracle_kinds`、`correctness`、`discrimination`、`negative_control_emulates_pre_fix`、`gaps`、`note`、`independence`（每筆：kind、test、basis、detail、`expected_from`、`requires`）、`commits`、`parent_records`、`mutants`。D8 不改數字或判定，D10 是測試修正，兩者只記在 CHANGELOG。

| 缺陷 | `fixes` 條目 | 等級 | 最低證據 |
|---|---|---|---|
| D1 觀測量的 kind | `geant4-scope-kind` | S2 | C2、D2 |
| D1 缺少的範圍維度（依 benchmark 宣告的維度） | `geant4-scope-missing-dimension` | S2 | C2、D2 |
| D2 等級由紀錄自己宣告 | `geant4-grade-table` | S2 | C2、D2 |
| D2 驗證類別（`longitudinal-profile` 改為 setup-matched） | `geant4-setup-matched-class` | S2 | C2、D2 |
| D3 控制組在觀測量上判定、正負兩向 | `geant4-control-shift` | S2 | C2、D2 |
| D3 偵測極限的 t 分位數 | `geant4-detection-limit` | S2 | C2、D2 |
| D4 收斂閘門的 IUT（差值與 se 的定義） | `geant4-gate-iut` | S2 | C2、D2 |
| D11 掃描點完整性 | `geant4-gate-scan-completeness` | S2 | C2、D2 |
| 隔離的定義（含真空） | `geant4-isolation` | S2 | C2、D2 |
| D5 區塊 batch means 取代 bootstrap 的 SE | `geant4-batch-means-se` | **S1** | C3、D2；`review` 簽核 |
| D5 計數很少時的精確區間 | `geant4-low-count-exact` | **S1** | C4（有限的計數範圍可窮舉）、D2；`review` 簽核 |
| D5 MPV 的三點內插 | `geant4-mpv-estimator` | **S1** | C3、D2；`review` 簽核 |
| `f4` 的轉傳與結束碼（A1.17） | `design-f4-label-passthrough` | S4（`robust-fix:`） | C1、D2 |

| 缺陷 | `documentation_fixes` 條目 | 等級 | 來源 |
|---|---|---|---|
| D6 停止規則 | `geant4-stopping-rule` | S3 | 一個外部來源（optional stopping 的文獻，經 hep-citations 查證並定位）與一個內部來源（protocol 第 4 節） |
| D7 證據相關性 | `geant4-evidence-overlap` | S3 | 同上；只有內部來源時在 `gaps` 註明 |

- **證據：** C 與 D 兩軸分開回報（第 133–153 行）。S1 至少 C3＋D2（有封閉形式或有限定義域時 C4），S2 至少 C2＋D2，S3 要有已定位的來源與第二個來源，S4 為 C1＋D2（這裡的 C、D 是證據層級，不是契約版本或缺陷編號）。C3 需要至少一個 `expected_from` 不是 `transcribed-formula` 的 independence 紀錄（例如 t、F 分位數以 scipy 為 `third-party-definition`，batch means 的覆蓋率以 `general-result`）；`requires` 只列 `requirements-core.txt` 的套件。D2 需要每個 independence 所指的 oracle 都有 parent record（在 parent commit 上失敗、在修正上通過）；D3 另需一個被殺死的 `revert` mutant。在 parent 上，新的函式、參數或輸出鍵屬 `error`，不算數（第 147–149 行），所以證據測試經 `validate.py` 與 `check_geant4_study.py` 的命令列與既有輸入撰寫。只能在 E2 執行的 Geant4 證據在 release gate 記錄；不能執行的寫入 `gaps`。
- **檢查：** `tools/scifix_ledger.py report`（列出缺 `review` 的 S1 條目與只有轉錄公式的條目）、`tests/tools/test_scifix_ledger.py`、`test_scifix_schemas.py`、`tools/run_required_backends.py --from-ledger --no-skips`。
- **advisory（格式 `hep-research-scifix-advisory/2`，第 252–283 行）：** S1 一份、S2 一份（`scifix_advisories.py check` 要求 advisory 的等級和每個列出的條目相同）；S3、S4 不需要 advisory。編號取合併時下一個未使用者（目前為 SFA-2026-039（S1）與 SFA-2026-040（S2））。
  - `applies_to.match`（群組之間 OR、群組之內 AND；每組都要有可區分的條件）：
    - 研究紀錄：`artifact_types` 含 `computational-run`；條件 `extension.study` exists、`status[*]` eq `validated-in-scope`、`provenance.code_paths[*]` regex `check_geant4_study\.py$`（`unknown_before: 3.5.0`：較舊的紀錄沒有 trace，判為「可能受影響（no trace）」）。
    - F4 設計評估（依賴被錯誤升級的研究紀錄）：`artifact_types` 含 `design-evaluation`；條件 `extension.fidelity` eq `F4`。
    - simulated dataset-record：依 `contracts/validate.py` 的 `dataset.simulated_upgrade_*` 規則所讀的欄位寫條件；沒有欄位能區分時以 `match_basis` 說明並列在 `no_trace`。
    - `status[*]` 路徑能否被 `scifix_advisories.py check` 接受，在實作時以該工具確認（未驗證）。
  - 範圍：`introduced` 0.20.0，附 `database_specific.introduced_basis`；合併前沒有 `fixed` 事件，附 `database_specific.fixed_commit`；`affected` 由工具從 `release-manifests/` 算出（目前為 0.20.0–0.38.x）；發布時加入 `fixed`。
  - `impact`：`observables`（受影響的研究觀測量、偵測極限、F4 evaluation 的值與判定）、`bias`、`trigger`。
  - `remedy`：以新版本重產研究紀錄；研究重新發出後以 `evaluate_design.py f4 --replace` 重做 F4 evaluation（研究的雜湊改變後，舊的 evaluation 在 `contracts/design.py` 中成為過時）；simulated 表格執行 `contracts/dependencies.py`。
- 0.20.0 以後產生、帶 `validated-in-scope` 的 study record 在 `--strict` 下會失敗；advisory 說明處理方式（以新版本重產）。

### A1.15 A1 驗收

- [ ] kind 不符、宣告缺少維度、類別或等級與表不符、configuration 缺少或 embedded、目標雜湊或 `hash_scheme` 不符的紀錄，在 `--strict` 與 CV-A1 下被拒；`dependencies.py` 重新推導不符時被拒；純量範圍正確比對。
- [ ] 未知的角色、同一研究中重複的 S 被拒；legacy 種子的 run 依規則檢查。
- [ ] 重產的 J14 study record 通過 `validate.py --strict` 與 `dependencies.py`；判定的任何改變都記錄並說明原因（閘門 G-A1）。
- [ ] 閘門 toy（每格 10⁴ 次，依 A1.8 表頭說明的模型）和 A1.8 的表一致到 ±3σ_MC：「se = 目標」各欄只核對 TOST 部分，「兩階段」各欄核對包含達標條件的完整閘門；`absolute` 模式與計數很少時的區間判定有測試。
- [ ] 區塊 batch means 的覆蓋率 toy：J14 各類估計量（平均、比例、分位數、眾數）名義 90 % 區間的實際覆蓋率滿足 |覆蓋率 − 0.90| ≤ 0.02 + 3σ_MC，逐類回報（以 `toy_ensemble` 的 `coverage`、`coverage_gate` 執行）。
- [ ] MPV 偏差 toy 的 95 % 上界 ≤ tol/10；每次的實測核對生效。
- [ ] 偵測極限 toy（A1.10 的 caught 定義）：在 DL 注入時抓到的機率 ≥ 0.977 − 3σ_MC；J14 的實現控制組結果記錄於 VALIDATION。
- [ ] J14 的離線重播由已提交的 summary 執行，判定符合 §A.4.3，不需要 Geant4 與編譯器。
- [ ] Python 產生器的單元測試：區塊劃分、選擇、合併、`weight ≠ 1` 時 exit 2、溢位格。
- [ ] 新的 `core/` 檔案各有單元測試（`t_ppf`、`f_ppf` 對已知值與 scipy 的第三方值；H 的測試向量），在 `core/OWNERS.json` 登錄（`stats` 的 `files` 與新的 `simulation` 模組），`CORE_VERSION` 升 minor；Garwood 只有 `poisson_diagnostics.central_interval` 一份；一個只 import `core` 的測試（模擬 adapter 的用法）能讀 summary、計算估計量並呼叫 `equivalence`；`check_layering.py` 通過。
- [ ] `python3 -m unittest discover -s tests/contracts -t .` 沒有錯誤。
- [ ] D11（A1.16）：缺少任一宣告掃描值時閘門為 `incomplete`；「最細兩個」取宣告值；J14 的判定不變。
- [ ] F4 消費端（A1.17）的四項測試通過；`tests/skills/hep_detector/test_design_*.py` 與 `tests/contracts/test_design_*.py` 不變地通過。
- [ ] summary 與觀測量的 schema 在 `contracts/schemas/`，由呼叫層驗證；`core/` 不 import `contracts`（`check_layering.py`）。
- [ ] A1.14 的十三筆 `fixes` 與兩筆 `documentation_fixes` 通過 `tests/tools/test_scifix_ledger.py`、`test_scifix_schemas.py` 與 `tools/scifix_ledger.py report`（S1 條目在下一個 minor 前有 `review` 簽核）；兩份 advisory（格式 `/2`）通過 `scifix_advisories.py check`；parent record 與 mutant 齊全，`tools/run_required_backends.py --from-ledger --no-skips` 沒有未通過的 oracle；live Geant4 證據以 release-gate 執行記錄；VALIDATION GEANT4-CORRECTNESS；CHANGELOG；release manifest。

---

## §A.6 階段 A2：共用標頭與邊界產物（geant4 adapter 0.2.0）

A2 不改 `layered_sim` 的 spec 格式與既有輸出，只新增選用欄位與檔案。

### A2.1 `g4sim`

**位置：** `adapters/geant4/assets/g4sim/`（標頭檔；`layered_sim`、任務 B 的 `element_sim` 與 `simreco` 共用；擁有者 hep-detector）。目錄名不用 `g4common`，以免和既有的 Python 模組 `assets/g4common.py`（四個腳本 import、列在 `adapter.json`）混淆。

| 檔案 | 內容 | 依賴 |
|---|---|---|
| `SimHash.hh` | SHA-256（在 plugin 內撰寫）與 A1.4 的 H，以測試向量和 `core/simulation/seeds.py` 核對；SplitMix64 產生器與 Box–Muller 常態亂數（供不連結 Geant4 的程式使用）。SplitMix64 只用整數運算，跨平台逐位元相同；Box–Muller 用 libm 的 `log`、`cos`，只保證同一平台逐位元相同，跨平台相對差 ≤ 1e-12；以 `-ffp-contract=off` 建置 | 只有 C++17 標準函式庫 |
| `SimSeed.hh` | 事件 i 的兩個種子 (H(S, i, 0), H(S, i, 1))；以 0 結尾的陣列 `long seeds[3] = {s0, s1, 0}` 呼叫 `G4Random::setTheSeeds`（和 `layered_sim.cc` 行 150–151 相同） | Geant4、`SimHash.hh` |
| `SimSummary.hh` | 區塊累加器（A1.5 的欄位）、Neumaier 加總、合併、`simulation-summary/1` 的 JSON 寫出 | 只有 C++17 標準函式庫 |
| `MiniJson.hh` | 由 `layered_sim/` 移入（內容不變；`layered_sim` 改為 include 這份） | 只有 C++17 標準函式庫 |
| `SimProbe.hh` | 探針（A2.4） | Geant4 |
| 輔助 | 材料建立（含混合材料的順序）、physics list 選擇、CSV 寫出 | Geant4 |

- 把 `layered_sim` 既有程式中相同功能的部分搬入 `g4sim` 時不得改變其行為（回歸檢查保證）。
- `SimHash.hh` 與 `SimSummary.hh` 以選用的 ctest 在沒有 Geant4 的環境測試（CI 選用工作）。

### A2.2 逐事件種子

- `layered_sim` 的 spec/1 加入選用的 `run.seeding`：`stream`（預設，既有行為）或 `per-event`；以及 `run.logical_run_seed`（S）。三處同時加入：`geant4_run.py` `validate_spec()` 的 `run` 鍵清單（行 204）、`layered_sim/spec.schema.json`、`layered_sim/Spec.cc`。
- `per-event`：事件 i 在 `GeneratePrimaries` 的**開頭**（任何亂數抽取之前）以 `SimSeed.hh` 重設亂數，i 為全域事件編號。Geant4 在 `BeginOfEventAction` 之前就呼叫 `GeneratePrimaries`，所以不能在 `BeginOfEventAction` 重設；`BeginOfEventAction` 不得抽亂數。同一邏輯 run 以任何工作切法、任何執行緒數，事件內容相同。
- Geant4 在呼叫 `GeneratePrimaries` 之前儲存亂數狀態（`/random/setSavingFlag`、`StoreRandomNumberStatusToG4Event`），存下的是重設前的狀態，不能用來重現 `per-event` 的事件；重現改用 (S, i)。探針記錄這些旗標。
- J14 的既有 spec 不改，維持 `stream`。新研究的 spec 由 adapter 預設寫入 `per-event`。

### A2.3 `layered_sim` 寫出 run summary

- spec/1 加入選用的 `output.observables`（引用 `simulation-observables/1`）、`output.blocks`（K、B、邏輯 run 的第一個事件編號）與 `output.debug_observable_dump`；三處同時加入：`validate_spec()` 的 `output` 鍵清單（行 215）、`spec.schema.json`、`Spec.cc`；`geant4_run.py` 從 study spec 的觀測量宣告寫入執行用的 spec。
- 事件結束時，把宣告的觀測量累加到所屬區塊；MT 下以自訂的 `G4VAccumulable` 合併：每個 run 開始時（`BeginOfRunAction`）呼叫 `G4AccumulableManager::Reset()`；worker 在自己的 `EndOfRunAction` 呼叫 `G4AccumulableManager::Merge()`，master 在自己的 `EndOfRunAction` 寫出；master 與 worker 的註冊順序相同。
- 輸出 `summary.json`（`simulation-summary/1`，產生者 `layered_sim`），雜湊寫入 run record。
- 事件權重 ≠ 1 時 exit 2。
- **測試用傾印：** spec 的 `output.debug_observable_dump: true` 時，另寫一個旁檔，逐事件列出宣告觀測量的 `%.17g` 值；只在測試中使用，CSV 本身不變。

### A2.4 effective config 與探針（`SimProbe.hh`）

```
{ "engine": "geant4", "engine_version": "11.4.3", "probe_version": "...",
  "backend": {"name": "layered_sim", "version": "...", "sources_sha256": "..."},
  "source": "probe" | "declared", "recorded": true, "config_sha256": "...",
  "seeding": {"mode": "per-event" | "stream", "logical_run_seed": ...},
  "geometry": { "tree": [...], "tree_sha256": "...", "naming_sha256": "...", "hash_scheme": "tree-v1", "gdml_sha256": null },
  "environment_ref": "<build 紀錄的雜湊>",
  "sections": { "geant4": { ... } } }
```

| 項目 | 規格 |
|---|---|
| 時機 | master 的 `BeginOfRunAction`（在 `G4RunManager::RunInitialization` 之內、kernel 關閉幾何之後呼叫）；狀態為 `G4State_GeomClosed` 且 couple 數大於 0；否則 `recorded: false`（`layered_sim` 仍 exit 0），該 run 不能升級。fake run（`/run/beamOn 0`）在 `BeginOfRunAction` 之前返回，探針不執行 |
| 頻率與執行緒 | 每個 run 一次；只在 master；註明「workers assumed identical」 |
| 幾何樹 | 由 `G4PhysicalVolumeStore`（依建立順序的平面清單）與各體積的母邏輯體積重建樹；每個放置：名稱、copy number、solid 類型與參數、材料（Geant4 解析後的組成與密度）、轉換矩陣、母體、附加的 field manager 與參數；數值以 Python `float.hex()` 的格式（例如 `0x1.0000000000000p+0`）寫出；C 的 `%a` 輸出不同（`0x1p+0`），所以 `SimProbe.hh` 自帶格式器，並以測試向量和 Python 核對，含特殊值：0.0 → `0x0.0p+0`、−0.0 → `-0x0.0p+0`、subnormal（例如 `0x0.0000000000001p-1022`）、`inf`、`-inf`、`nan`（幾何中出現 inf 或 nan 時 exit 2）；replica 與 parameterised 體積記錄參數化描述 |
| `tree-v1` 雜湊 | 目標 = `target_slabs`（A1.3）所列 slab 的放置集合（含各自的子樹），依下述正規順序排列；目標雜湊 = 這個集合的 JSON（鍵排序、無空白）的 sha256，轉換改為相對第一個目標放置（目標整體平移不改變雜湊）；`tree_sha256` 以同樣規則對整棵樹計算。內容只含物理：solid 類型與參數、材料組成與密度、相對母體的轉換、附加的場；**不含**體積名稱與 copy number。同一母體的子體依正規順序排列（依轉換的平移、再依 solid 參數、再依材料，全部以 hex 字串比較），不依建立順序；平移、solid 與材料完全相同時依 copy number 排序並註明。名稱與 copy number 另計 `naming_sha256`。這讓 setup-matched 能比對不同程式建立的同一配置，也讓任務 C 能快取相同的設計 |
| GDML | plugin 的建置關閉 GDML；使用者建置有 GDML 時可附 `gdml_sha256`，非必要 |
| EM 參數 | `G4EmParameters::StreamInfo(os)` 全文加上解析出的欄位；不用 `Dump()` |
| cut | 逐 material-cuts couple：材料、region、range cut、各粒子的能量閾值 |
| 強子模型 | 逐 process、逐模型，以 `GetHadronicInteractionList()` 與 `GetMinEnergy(mat, elm)`、`GetMaxEnergy(mat, elm)` 查詢能量範圍；重疊區間標示為隨機選擇；記錄每個模型依材料與元素的 `IsBlocked()`；啟用 `G4NeutronGeneralProcess` 或 `G4GammaGeneralProcess` 時，逐一記錄其包含的子 process 與模型。**不得**呼叫 `G4EnergyRangeManager::GetHadronicInteraction` 或 `ChooseHadronicInteraction`（區間重疊時它們會呼叫 `G4UniformRand`） |
| 亂數 | 探針不得抽取任何亂數（否則違反 §A.3 第 13 條）；測試以探針前後的亂數引擎狀態相同來確認 |
| run manager | 實際的 run manager 型別（`MTOnly`/`SerialOnly` 時環境變數 `G4RUN_MANAGER_TYPE` 被忽略）、`seedOncePerCommunication`；SubEvt 或非 0 的種子模式回報 gap |
| 其他 | `G4UserLimits`、biasing（有 biasing 時標記「事件間可能有狀態」） |
| 資料集 | 路徑與內容雜湊只在 build 紀錄中計算一次；探針以 `environment_ref` 引用 |
| 場 | field manager 逐執行緒；宣告了場而 master 看不到時標記 `source: declared`（`layered_sim` 沒有場） |
| 路徑 | 經 `tilde()` 寫出 |
| 存放 | 內容依 `config_sha256` 存放一次（`effective_configs/<config_sha256>.json`），相同設定的多個 run 只引用雜湊；`extension.simulation.effective_config` 放引用；提交的 J14 紀錄另附完整內容以便離線重播。schema 在 `adapters/geant4/assets/schemas/`（adapter 擁有，由 adapter 的腳本以 `contracts.schema.validate` 驗證） |

- 規則與 variation 的模型指派優先讀探針，讀不到才退回宣告，並輸出 `source: probe | declared`；兩者都有而不一致時報錯。
- 測試觸發：一個只在測試建置中存在的 UI 指令，在 `/run/initialize` 之後、第一次 `BeamOn` 之前呼叫探針，必須寫出 `recorded: false`。

### A2.5 column map（`simulation-columns/1`）

- `layered_sim` 每個 run 寫出 `column_map.json`，雜湊寫入 run record；schema 在 `adapters/geant4/assets/schemas/`。
- 每個欄位：語意名稱、實際欄名、單位、操作定義、所在檔案（`csv` 或 `summary`）；附 `column_map_version`。
- 只允許宣告式運算（改名、單位換算、加總、篩選）；需要計算的轉換是另一個有紀錄的步驟。

### A2.6 研究層只讀邊界產物（D9）

| 位置 | 變更 |
|---|---|
| `cmd_summarize`、benchmark | 只讀 summary（與 column map 的語意名稱）；不讀 CSV 欄名 |
| `derived()` 與薄層規則 | 最小厚度由 effective config 的幾何樹取得；A2 前的紀錄（沒有 effective config）仍從 spec/1 的 `geometry.layers` 取得 |
| configuration 與目標雜湊 | A2 起的紀錄用 `tree-v1`；A1 的紀錄保持 `spec-v1`；比對只在相同 `hash_scheme` 之間進行；`dependencies.py` 依紀錄的 `hash_scheme` 重新推導 |
| 一致性核對 | `geant4_run.py`（不是 `layered_sim`，以免在 C++ 重複實作 `spec-v1`）在每個 `layered_sim` run 之後核對「`spec-v1` 推導的 configuration」與「`tree-v1` 推導的」判定相同；不同時 exit 2 |
| `geant4_verify.py` | 體積計數與物質預算改由幾何樹取得 |

### A2.7 schema 關鍵字

- 擴充 `contracts/schema.py`：`maxItems`、`maximum`、`exclusiveMaximum`（main 0.38.0 的 `SUPPORTED_KEYWORDS` 仍沒有，行 61–63；`layered_sim` 的 schema 已用到；`element_sim` 的 schema 也需要）。`layered_sim/spec.schema.json` 另用 `oneOf` 與 `not`：實作這兩個關鍵字，或改寫為已支援的形式，二擇一並在 VALIDATION 註明。更新 `SUPPORTED_KEYWORDS`，並讓 `tests/contracts/test_schema_keywords.py` 也掃描 adapter 的 schema（含 `adapters/geant4/assets/schemas/`）；`layered_sim/output.schema.json` 不是 JSON Schema（頂層鍵是欄名），列為豁免。新的 schema 一律不用 `uniqueItems`（validator 不支援，見該測試的 docstring）；需要唯一性時在 Python 檢查。
- contracts 不升版（沒有契約 schema 使用新關鍵字）。
- `geant4_run.py` 的 `validate_spec()` 不被取代；A2.2、A2.3 只在它的鍵清單加入新欄位。

### A2.8 adapter 變更流程

| 項目 | 內容 |
|---|---|
| 版本 | 0.1.0 → 0.2.0 |
| `adapter.json` | `assets` 加入 `g4sim/`、`summary_from_csv.py`；更新 `purpose`；`status` 維持 `demonstrated-on-synthetic-data` |
| `SIM_SOURCES` | 加入 `g4sim/` 的檔案，讓 `sources_sha256` 涵蓋全部（B1 再改為依程式分組） |
| run record | `geant4_run.py run` 寫出的 run record 另帶 `argv`、`script_sha256`、`versions.plugin_release`（和 `run_workflow.py` 相同；`ext_computational_run.json` 3.11.0 起的選用欄位） |
| schema | `adapters/geant4/assets/schemas/`（column map、effective config） |
| G5 | 聲明「依 Geant4 API 撰寫，未複製或改寫任何範例程式碼」，由審查者在 VALIDATION 條目中確認 |
| 測試 | `tests/adapters/test_geant4.py` 的 assets 檢查；離線測試；`HEP_GEANT4_LIVE_TEST=1` 的 live 測試；`SimHash.hh` 與 `SimSummary.hh` 的 ctest（選用） |
| 文件 | `docs/capability-matrix.md` 的 Geant4 列；`geant4-study-protocol.md`（邊界產物、區塊、驗證類別） |

### A2.9 測試與 oracle

- 由 A2.3 的測試用傾印，以 A1.5 的 Python 產生器重算 summary，和 `layered_sim` 寫出的比對：整數相同、浮點相對差 ≤ 1e-12。
- `per-event` 下，同一邏輯 run 以 1、2、4 個工作與 1、2、4 個執行緒執行：事件內容相同（傾印逐位元相同），summary 整數相同、浮點相對差 ≤ 1e-12。

### A2.10 A2 驗收

- [ ] 回歸檢查：在同一主機上以 A2 前的 commit（A1 合併後的 `main`）重建 `layered_sim` 作為參考，J14 的 18 個既有 spec 以 A2 的建置產生逐位元相同的 CSV；探針前後的亂數引擎狀態相同（閘門 G-A2）。
- [ ] `SimHash.hh` 的 H 與 `core/simulation/seeds.py` 在測試向量上相同；`SimProbe.hh` 的 hex 格式和 Python `float.hex()` 相同。
- [ ] A2.9 的兩項測試通過；`per-event` 下 `GeneratePrimaries` 若抽亂數（測試用的隨機 gun），事件內容仍不受工作切法影響。
- [ ] `tree-v1` 不受命名影響：同一幾何以不同的體積名稱與建立順序建立兩次，`tree_sha256` 與目標雜湊相同，`naming_sha256` 不同；改變任一物理量（厚度、材料、位置）時雜湊改變。
- [ ] effective config 依內容雜湊只存一次；兩個相同設定的 run 引用同一個檔案。
- [ ] spec 的新欄位（`run.seeding`、`run.logical_run_seed`、`output.observables`、`output.blocks`、`output.debug_observable_dump`）被 `validate_spec()`、`spec.schema.json` 與 `Spec.cc` 接受；未知欄位仍被拒。
- [ ] 為回歸檢查在 E2 重跑的 J14 spec（`recorded/specs/` 的全部 18 個：`mpv-nominal`、`mpv-control`、`mpv-cut-0.03`、`mpv-cut-0.1`、`mpv-cut-0.3`、`mpv-cut-1.0`、`mpv-density-10`、`mpv-em-option0`、`mpv-em-option3`、`mpv-ftfp-bert-emz`、`mpv-pai`、`sp-nominal`、`sp-control`、`sp-cut-0.03`、`sp-cut-0.1`、`sp-density-10`、`sp-em-option0`、`sp-em-option3`；仍為 `stream`）的新 run record 都有 effective config，且 `tree-v1` 與 `spec-v1` 的判定相同；故意製造的不一致被抓到；`recorded: false` 的 run 不能升級。已提交的 J14 紀錄維持 A1 的版本，不在 A2 重產。
- [ ] 薄層規則從 effective config 取得最小厚度，對 J14 的結論和 A1 相同。
- [ ] 研究層的正式程式不讀 CSV 欄名（測試確認）。
- [ ] 事件權重 ≠ 1 時 exit 2。
- [ ] run record 帶 `argv`、`script_sha256`、`versions.plugin_release`。
- [ ] schema 關鍵字測試掃描 adapter 的 schema（`output.schema.json` 豁免）；`oneOf`、`not` 依 A2.7 處理；沒有 `uniqueItems`。
- [ ] J14 的離線重播仍符合 §A.4.3。
- [ ] VALIDATION GEANT4-SUMMARY；CHANGELOG；release manifest。

---

## §A.7 契約與版本

| 物件 | 位置 | 版本 |
|---|---|---|
| benchmark 表（類別、kind、範圍維度）、範圍比對、configuration 與隔離、`hash_scheme`、evidence 角色、S 的唯一性、掃描點完整性 | `contracts/validate.py`、`contracts/dependencies.py`、`check_geant4_study.py` | CV-A1（minor、閘控、sci-fix） |
| `simulation` 屬性的宣告 | `contracts/schemas/ext_computational_run.json` | CV-A1（需 hep-computing 同意） |
| summary 與觀測量的 schema | `contracts/schemas/` | CV-A1 |
| schema 關鍵字擴充 | `contracts/schema.py` | 不升版 |
| `core/stats/`、`core/simulation/` 的模組 | `core/` | `CORE_VERSION`（SemVer；A1 升 minor）；summary 的格式以 `summary_version` 與 `simulation-observables/1` 的版本號管理 |
| column map 與 effective config 的 schema | `adapters/geant4/assets/schemas/` | geant4 adapter 0.2.0；以 `column_map_version`、`probe_version` 管理 |
| F4 消費端的相容（`--label-run-record` 等、結束碼對應） | `skills/hep-detector/scripts/evaluate_design.py` | 隨 plugin 版本（不改契約） |
| `g4sim`、`seeding`、summary、column map、effective config 的寫出 | geant4 adapter | 0.2.0 |
| `GRADES`、kind 與 configuration 的輸出 | hep-detector | 隨 plugin 版本 |

computational-run schema 的擁有者是 hep-computing。CV-B2 屬任務 B（B2）；CV-C1、CV-C2 屬任務 C。號碼在發布時依合併順序決定。

---

## §A.8 每個階段結束時的檢查

任務 B、C 的每個階段也執行這些檢查。

- `run_all_checks.py`（含 CI lock 環境）
- `check_layering.py`、`check_relocation.py`、`check_ownership.py`、`check_packaging.py`
- `measure_entrypoints.py`（quick load ≤ 25,600 bytes）
- `reference_inventory.py --check`、`capability_map.py --check`、`check_routing_static.py`
- 每份 study record 都通過 `validate.py --strict` 與 `dependencies.py`
- `tests.adapters.test_geant4` 離線與 live（`HEP_GEANT4_LIVE_TEST=1`）
- `tests/examples/test_geant4_thin_silicon.py`（重播的判定符合 §A.4.3）
- `python3 -m unittest discover -s tests/contracts -t .`（整體執行）
- `tools/check_wiring.py`（`run_all_checks.py` 也會執行）：新的腳本與 reference 必須接線
- `tools/ci_plan.py`：確認 pull request 會選到 Geant4 與 core 的測試（`contracts/rules/registry.json` 目前沒有 `adapters/geant4/**`、`core/stats/**`、`core/simulation/**` 的影響群組，會退回完整執行；新增群組是選用的，§P.8）
- `tests/skills/test_cli_robustness.py`（掃描 `adapters/*/assets/*.py`；新的腳本登錄 `MISSING_FILE_ARGS`）
- 有 tool contract 的腳本（`contracts/tool_contracts/`）與 `--help` 一致；任務 A 不新增 tool contract（`check_geant4_study.py`、`geant4_run.py`、`evaluate_design.py` 沒有 tool contract）
- 設計流程的測試：`tests/skills/hep_detector/test_design_*.py`、`tests/contracts/test_design_*.py`
- `tools/scifix_advisories.py check`、`tools/scifix_ledger.py report`、`tests/tools/test_scifix_ledger.py`、`test_scifix_schemas.py`、`tools/run_required_backends.py --from-ledger --no-skips`（A1）
- 10⁴ 次 toy 的測試放在慢速層（`HEP_SLOW_TESTS=1`），在 release gate 執行並記錄
- 由沒參與撰寫的 agent 執行一個新問題，並附通過條件
- 各階段的 Markdown 以 0.22.0 的 `review.py` 審查（`--lens-model design=<最強模型>`、`--filter-model`）；紀錄只是 advisory，依 O04/O14 不取代人工的 G5 確認
- VALIDATION 條目、CHANGELOG、release manifest

---

## §A.9 不做與延後

| 項目 | 決定 | 理由 / 觸發條件 |
|---|---|---|
| spec/2、spec 轉換、雙格式存取器、逐位元比對閘門 | 不做 | `layered_sim` 不改格式；新功能在 `element_sim` |
| 整數量化、128 位元整數、逐位元相同的統計量 | 不做 | 重現的定義是判定相同 |
| `simstat`、不連結 Geant4 的 `simcore` | 不做 | 推論留在 Python |
| 每個證據 run 多個獨立行程 | 不做 | 區塊在 run 內 |
| `uses-validated-physics` label | 不做 | 雜湊太嚴也太鬆；會繞過範圍檢查 |
| 依 SE 自適應停止、以加密掃描作為證據、換種子重跑控制組 | 不做 | optional stopping |
| 新的 core 驗證器、重寫徑跡與多重散射公式 | 不做 | 重用既有工具 |
| contracts 4.0 | 不做 | 新增選用區塊與閘控規則屬 minor |
| Python 綁定 | 不做 | 使用者決定以獨立執行檔交換 JSON/CSV |
| 取代 `validate_spec()` | 不做 | 不在範圍內 |
| `change`、配對比較、search 角色、`values` | 移到 B2、C2 | §P.2 R1 |
| `threshold`、`order` 作為需求的判定 | 不做 | 需求的判定、排序與 Pareto 由 main 的 `contracts/design.py` 推導（§P.0） |
| 第二份 Garwood、第二個 toy 種子推導、另一個覆蓋率閘門 | 不做 | 重用 `poisson_diagnostics.central_interval` 與 `toy_ensemble`；同一個量只有一份正式實作 |
| 加權累加與 biasing 規則 | 延後 | 第一個使用 biasing 的研究 |
| `physics_config_comparison` | 延後 | 需要比較物理設定的研究；屆時差異須經 `evidence_records` 取得 effective config，缺少時一律失敗 |
| 規則版本範圍、多個 Geant4 版本的探針 | 延後 | 支援第二個 Geant4 版本（B2 的 regression 類別會先用到） |
| benchmark registry | 延後 | 由契約表與 enum 一致性測試取代 |
| `inspect` 與 Linux 環境 | 延後 | 需要在 CVMFS 或 LCG 上執行 |
| ReferenceMaterial 契約 | 延後 | 第一個非平板幾何的 reference benchmark |
| 一般化 `scoped_upgrade` | 延後 | 第二種研究類型需要升級 |
| J14 遷移到 `element_sim`、退役 `layered_sim` | 延後 | `element_sim` 能產生 J14 的全部觀測量（§P.8） |

---

## §A.10 待決事項與殘餘風險

**待決事項**（編號見 §P.7）：第 1 項（CV-A1 的歸類）、第 2 項（`core/` 模組的 steward）、第 3 項（`simulation` 屬性）、第 4 項（兩階段係數與 J14 偶然失去升級時的處理）、第 5 項（J14 重錄與 recorded 上限）、第 6 項（精確區間的切換門檻）、第 7 項（G5 的確認方式）。

**殘餘風險：**
1. J14 的偵測極限可能因區塊 batch means、t 分位數與觀測量單位的控制組而改變，需要重新設計控制組。
2. 區塊 batch means 對偏斜分布的比值、分位數與眾數有 O(1/B) 的偏差，不隨 K 減少；覆蓋率 toy 容許 ±0.02，必要時加大 B。
3. 區塊獨立的前提在事件之間有狀態時不成立；探針標記 biasing，有疑慮時改為多個獨立的邏輯 run。
4. 以容差比較時，接近門檻的判定在不同平台可能不同；以邊距標記與「CI 平台為準」處理。
5. 自訂 `G4VAccumulable` 的 MT 合併需以測試確認行為。
6. 探針假設 worker 與 master 設定相同；若發現 thread-local 差異，改為逐執行緒傾印。
7. setup-matched 的目標雜湊只能證明配置相同，不能證明它就是論文中的配置；仍需審查者核對。
8. quick load 只剩 931 bytes。
9. 工作量：原型估計 A1 的契約部分約 8–12 個工作天，另加 Geant4 執行時間；統計部分與 A2 在開始時估計。新的帳本規則（每個修正一筆、parent record、mutant、S1 簽核）會增加 A1 的工作量。
10. main 變動快（兩天內從 3.5.0 到 3.12.0）；`validate.py`、`dependencies.py`、`evaluate_design.py` 與設計流程的 PR 共用；每次 rebase 後重跑 §A.8。
11. D2 需要每個 oracle 在 parent commit 上的紀錄；只能在 E2 執行的 Geant4 證據可能達不到，屆時在 `gaps` 註明並由維護者決定等級。

---

## §A.11 建議的執行步驟

每個階段開始時依 §P.10.2 建立並確認該階段的 isolated worktree，所有步驟都在其中進行；合併後依 §P.10.5 移除。

**A1**
1. 開始前檢查（§A.0）；套用 `prototype/phase1-core.patch`，把寫死的 3.6.0 改為 CV-A1，補齊 A1.1–A1.3 缺少的部分。
2. 先修 D10（A1.12），之後一律以 `python3 -m unittest discover -s tests/contracts -t .` 整體執行。
3. 每個修正先寫在 parent commit 上會失敗的證據測試（經命令列），再以單獨的 `sci-fix:` commit 修正（A1.14）。
4. A1.1 → A1.2 → A1.3（契約與 `dependencies.py`）→ A1.16（D11），加契約測試。
5. `core/simulation/seeds.py` 與 `summary.py`、`contracts/schemas/` 的 schema、A1.5 的 Python 產生器；以 J14 的 5 個逐事件 CSV 離線產生 summary。
6. `core/stats/` 的三個檔案（A1.6–A1.10），hep-detector 的腳本改為呼叫它們並改讀 summary；加 toy 測試（閘門、覆蓋率、MPV 偏差、偵測極限）與只 import `core` 的使用測試；`OWNERS.json` 與 `CORE_VERSION`。
7. A1.4 的角色規則與 A1.11、A1.12 其餘項目（protocol、enum、`simulation` 屬性）。
8. A1.17：`evaluate_design.py f4` 的轉傳與結束碼、測試（`robust-fix:`）。
9. 在 E2 先錄 trial run，依 A1.9 定事件數，再 live 重錄 J14 的掃描、variation 與負方向控制組（A1.13）；重產 J14 紀錄，跑 `--strict`。
10. A1.14：ledger 的 `commits`、`parent_records`、`mutants`、`independence`，兩份 advisory（格式 `/2`），VALIDATION、CHANGELOG、release manifest；跑 `tools/scifix_ledger.py report` 與 §A.8 的檢查。

**A2（A1 合併後）**
1. `g4sim/SimHash.hh`、`SimSummary.hh` 與 ctest（不需 Geant4），以 `core/simulation/` 與 A1.5 的 Python 產生器作為 oracle。
2. `SimSeed.hh` 與 `run.seeding`；`SimProbe.hh` 與幾何樹、`tree-v1`。
3. `layered_sim` 整合：spec 新欄位（`validate_spec()`、`spec.schema.json`、`Spec.cc`）、summary、effective config（含依內容雜湊存放）、column map、測試用傾印；以 A2 前的 commit 重建 `layered_sim` 作為參考，確認 J14 的 18 個 spec 的 CSV 逐位元不變。
4. 研究層改讀邊界產物（A2.6）；schema 關鍵字（A2.7）。
5. A2.8 的 adapter 變更項目；在 E2 跑 live 測試；A2.10 全部打勾；跑 §A.8 的檢查。

---

## §A 附錄 A：統計規格彙整

| 項目 | 規格 | 工作項 |
|---|---|---|
| 區塊 | K ≥ 16 個依事件編號的區塊，每塊 B 個事件；事先宣告 | A1.5、A1.6 |
| SE | batch means，sd(θ_b)/√K，t_{K−1} | A1.6 |
| 計數很少 | 任一區塊為 0 或總數 < 100：Clopper–Pearson、Garwood、條件二項；閘門以區間端點判定 | A1.6、A1.8 |
| MPV | 區塊直方圖三點內插的平均；偏差 toy 95 % 上界 ≤ tol/10；每次核對 | A1.7 |
| 分位數 | 直方圖內線性內插；分格 < tol/10；溢位時 incomplete（C2 加入 `values` 的經驗分位數） | A1.6 |
| 收斂閘門 | IUT；`relative` 或 `absolute`；se_diff；Welch ν；每點 se 目標 tol/(4√2)；通過需兩點都達標；掃描值須齊全，最細兩個取宣告值 | A1.8、A1.16 |
| F4 的不確定度 | `statistical_uncertainty` = t_{0.84135}(K−1)·SE；精確分支寫不對稱區間 | A1.6 |
| 兩階段 | trial run；N 進位到 K 的倍數；f = F₀.₉₀(K−1, K_trial−1)；未達標 incomplete，不補跑；一對點約 19 % 不完整，n 個 run 全部達標約 0.9ⁿ | A1.9 |
| negative control | 觀測量位移；DL = tol + \|rel\| + t_{0.977}(ν)·se_rel；正負兩向；toy 門檻 0.977 − 3σ_MC | A1.10 |
| 種子 | H 的位元組定義；S = H(study_id, role, point_id)；工作種子 H(S, e, 0/1)；事件種子 H(S, i, 0/1) | A1.4、A2.2 |
| 證據相關性 | `evidence_overlap` | A1.11 |
| 重現 | 判定相同、數值相對差 ≤ 1e-9、接近門檻標記 | §A.4.3 |
| 版本欄位 | `summary_version`、`column_map_version`、`probe_version`、`evidence_overlap_version` | A1.5、A1.11、A2.4、A2.5 |

## §A 附錄 B：數值

計算程式：`gate_operating_characteristics.py`（需要 numpy 與 scipy，只作設計輔助）。

- F₀.₉₀(15,15) = 1.972；F₀.₉₅(15,15) = 2.403；F₀.₉₀(31,31) = 1.594。
- t₀.₉₅(30) = 1.697，t₀.₉₅(15) = 1.753，t₀.₉₇₅(15) = 2.131；m = 30 的失敗分位數 t_{1−0.05/30}(30) = 3.189。
- Welch ν（K = 16）：變異數比 1 時 30，2 時 27，4 時 22.1，10 時 18.0。
- 兩階段設計下 se_diff 的平均 ≈ 0.189 tol（目標 0.25 tol）；一對點至少一點未達標的機率 0.190。
- 偵測極限的檢定力（A1.10 的 caught 定義）在 0.977 附近（審查者的計算約 0.9785）。

## §A 附錄 C：基準核對值（`9f08796`；2026-10-24 依 `5584927` 重新核對）

| 項目 | 值 |
|---|---|
| `CONTRACTS_VERSION` | 3.12.0（`9f08796` 時為 3.5.0） |
| `GEANT4_UPGRADE_FROM` | 3.1.0（行 348） |
| J14 study record | contract 3.12.0，帶 `code_paths`、`code_tags` |
| J14 世界材料 | `G4_Galactic` |
| J14 `recorded/` | 2,447,979 bytes（約 2.45 MB；`du -sh` 顯示 2.6M）；`events/` 5 個縮減 CSV（`event`、`primary_eloss_MeV`、`edep_Si_MeV`、`primary_fate`、`primary_end_process`）；`runs/` 18 個 run record；`summaries/` 有全部 18 個 run 的單值摘要（`geant4-run-summary/1`）；5 個 run 另有逐事件 CSV，13 個掃描、variation 與情境 run 只有單值摘要 |
| J14 種子 | 未重錄的 5 個 run 的第一個種子為 1401 或 1402 |
| advisory | 最新 SFA-2026-038；格式 `hep-research-scifix-advisory/2` |
| hep-detector | quick load 24,669 / 25,600 bytes；description 1,016 / 1,024 字元（`measure_entrypoints.py`）；`DetectorScriptCount` 23（`tests/skills/test_documented_output_claims.py` 行 145–147） |
| `GRADES` | `longitudinal-profile: "reference"`（行 92–94）；study spec 的 grade enum 為 reference、sanity、interface |
| `ext_computational_run.json` | 未宣告 `simulation`；J14 的 run record 已帶 `extension.simulation` |
| `core/stats` | steward hep-statistics；已有 `beta_ppf`、`clopper_pearson`、Garwood（`poisson_diagnostics.central_interval`，行 162，基準時就有）、`toy_ensemble`（`toy_seed`、`coverage`、`coverage_gate`）；沒有 t、F 分位數 |
| `core` | `CORE_VERSION = "1.0.0"`（`core/__init__.py` 行 2）；`OWNERS.json` 的 admission rule：超過一個頂層使用者 |
| 分層規則 | adapter 只 import `core` 與 `contracts`；`core/` 只 import `core`（`tools/check_layering.py`） |
| `SUPPORTED_KEYWORDS` | 無 maxItems、maximum、exclusiveMaximum、uniqueItems、oneOf、not（`contracts/schema.py` 行 61–63） |
| sci-fix 帳本 | `docs/evidence/sci-fixes.json`：`fixes`（46 筆）、`documentation_fixes`、`superseded`；每筆含 `independence`、`commits`、`parent_records`、`mutants` |
| 設計流程的 F4 | `evaluate_design.py f4`（行 498–560）呼叫 `label --upgrade` 時不傳 `--run-record`；`label` 因此拒絕升級，但仍 exit 0 並寫出 `unvalidated` 紀錄（`check_geant4_study.py` 行 544–628）；紀錄沒有 `results`，`f4` 接著以 exit 2 失敗（行 530–532） |
| 收斂閘門 | `convergence()` 由已提供的 summary 取最細兩值（行 341–348）；J14 兩個研究都提供 0.01、0.03、0.1 mm |
| 原型 | `prototype/phase1-core.patch` 在 `5584927` 上仍可套用（dry run；`validate.py` 偏移 2 行） |
| `check_packaging.py` MAX_BYTES | 2 MiB（2,097,152 bytes，單檔） |
| Geant4 建置 | `GEANT4_USE_GDML: OFF`；`layered_sim` MT 用 `G4RunManagerType::MTOnly` |
| 共享 stanza 點 5 | 寫「3.1.0 upgrade rule」（不改） |
| journey 表 | J1–J14 |
| 階段 1 原型 | 55 個測試通過；J14 7 份 study record 通過 `--strict`；D10 在乾淨的 main 上重現（5 個錯誤） |

## §A 附錄 D：出處

設計所參考的實驗與框架（ATLAS、CMS、ALICE、Key4hep、Allpix²、geant-val、Belle II）見 §R.14。Geant4 11.4.3 原始碼的相關檔案：`G4RunManager.cc`、`G4MTRunManager.cc`、`G4WorkerRunManager.cc`、`G4EmParameters.cc`、`G4ProductionCutsTable`、`G4HadronicProcess.hh`、`G4EnergyRangeManager`、`G4AccumulableManager`、`G4VAccumulable`、`G4PhysicalVolumeStore`、`G4LogicalVolume`、`G4NistMaterialBuilder.cc`、`G4PVPlacement`。

## §A 附錄 E：版本歷程

| 版本 | 內容 |
|---|---|
| 2026-10-21 前 | 三輪獨立審查、依 0.21.0 與 `9f08796` 的兩次核對、階段 1 原型 |
| 2026-10-22 | 語言分工、逐事件 ROOT 檔、任務拆分、整理為實作規格；參考實際實驗重新設計（第 5 部（設計理由））；依新架構改寫 |
| 2026-10-23 | 獨立審查後修正（兩階段操作特性重算、H 的定義、caught 定義、`GeneratePrimaries` 開頭重設種子等）；依自動化設計重新審視（統計移到 `core/`） |
| 2026-10-23 | 依計畫（第 1 部）重新整理：A1 回到最小的 sci-fix（`change`、`threshold`、`order`、配對比較、search 角色、`values` 移到 B2、C2）；契約版本改記 CV1；種子雜湊放在 `core/simulation/seeds.py`；節的編號與任務 B、C 一致（§A.2 前提與提供的介面、§A.8 檢查、§A.10 待決與風險） |
| 2026-10-23 | 加入 isolated worktree 的執行規定：檔頭、§A.0 的第一步、§A.11 的開頭（§P.10） |
| 2026-10-23 | 詳細檢查後修正：spec 新欄位同時加入 `validate_spec()`、`spec.schema.json`、`Spec.cc`；A1.5 的選擇與現行程式一致；`tolerance`、`count_if` 的方向；種子欄位的名稱與 `cmd_chunk`；trial run 與 N 進位到 K 的倍數；DL 的 tol 與 se_rel；`tree-v1` 的目標；`float.hex()` 的特殊值、`setTheSeeds`、`IsBlocked()` 與 general process；Box–Muller 的跨平台容差；ledger 補 D7、D8；事實更正（行號、`recorded/` 大小、`summaries/`、原型的描述） |
| **2026-10-24（本版）** | **對照 main 0.38.0（探測器設計流程）重新規劃：基準改為 `5584927`／contracts 3.12.0；新增 D11（A1.16）與 F4 消費端的相容（A1.17）；ledger 與 advisory 改用 main 的現行格式（每個修正一筆、`documentation_fixes`、advisory `/2`、SFA-2026-039／-040，涵蓋 F4 設計評估）；重用 Garwood、`toy_seed`、`coverage_gate`；summary 的 schema 移到 `contracts/schemas/`，column map 與 effective config 的 schema 移到 adapter；`statistical_uncertainty` 的定義；`evidence_role`；CV1 改記 CV-A1；`CORE_VERSION` 與 `OWNERS.json`；A2 的 run record 加入 `argv`、`script_sha256`、`versions.plugin_release`，schema 關鍵字的 `oneOf`／`not` 與豁免；行號更新** |

---

# 第 3 部　任務 B：`element_sim`、重建與 J15 最小磁譜儀（§B）

> 順序：B1 在 A2 之後；B2 在 B1 之後；B3 在 B2 之後。任務 C 的 C2 等 B2 與 C1；B3 與 C2 的 F4 確認等 D0（§P.7）
> 基準：hep-research `main` 的 `5584927`（0.38.0），contracts 3.12.0，adapter geant4 0.1.0，Geant4 11.4.3；開始前必須重新核對（§B.0）
> 日期：2026-10-24
> 範例性質：J15 是**合成幾何**的設計專案，不是任何實驗的偵測器；最接近的實際儀器是 PAMELA 與 AMS-02（§B.4.3）

---

## §B.0 任務卡

**目標。** 新增一個通用的盒狀元件 Geant4 程式 `element_sim` 作為第二個後端，加入不連結 Geant4 的重建程式 `simreco`，並讓兩者成為 main 的探測器系統設計流程中**缺少的 F4 評估器**：由 design-candidate 經 `evaluate_design.py geometry` 產生的 `design-geometry/1` 推導模擬設定，模擬並重建，寫出 `evaluate_design.py f4` 接受的研究紀錄（`extension.study.results`、`tail_sources_simulated`、幾何檔在 `input_manifest` 中）。最後以 J15 最小磁譜儀作為設計專案，從 F1、F2 走到 F4。

**三個階段（依序，各自合併）：**

| 階段 | 內容 | 版本 |
|---|---|---|
| **B1** `element_sim`、事件檔與幾何推導 | `element_sim.spec/1` 與 `element_sim`（盒狀元件、一層巢狀、分區均勻場、所有帶電徑跡的平面穿越、量能器漏失）；逐事件 ROOT 檔；`simroot`；`geant4_run.py check-spec` 與 `from-geometry`（`design-geometry/1` 加實現設定檔 → `element_sim.spec/1`）；兩個後端的介面一致性；確定性場檢查 | geant4 adapter **0.3.0**，無契約變更 |
| **B2** 重建與 F4 介面 | `simreco`（數位化與重建、可攜的亂數、可切換的尾部來源）；F4 用的觀測量；`geant4_run.py reco`、`table` 與 F4 結果檔；`check_geant4_study.py label` 寫出 `results`、尾部來源與幾何檔；幾何對照表 1.1.0；`f4` 的不對稱不確定度與每個 evaluation 的幾何檔；遞移的處理鏈；verification 與 regression 類別；判定引擎的 `change`；**F4 資格路徑**（D0）與徑跡 reference benchmark；`geometry → 研究 → f4` 的端到端測試 | geant4 adapter **0.4.0**、contracts **CV-B2**（minor） |
| **B3** J15 設計專案 | J15 的 design-spec 與候選（N = 6、4、8）；經 `evaluate_design.py` 的 F1、F2；每個（figure of merit、分母）一份 F4 研究；尾部來源開關對 bound 的影響；驗證梯（另一份 `unvalidated` 紀錄）；量能器 cut 收斂、variation 與模型包絡、TOF σ_t 敏感度；recorded 資料；journey J15 與文件 | 範例與文件（adapter 不升版） |

**不在範圍內：** 任務 A 的介面變更（必要時先在任務 A 範圍內以 adapter 修補版處理）；`layered_sim` 的新幾何功能（它凍結）；任務 C 的候選搜尋；離子源與 Birks（延後，§B.9）；非盒狀幾何與場圖（§B.9）；量能器 figure of merit 的 F4 資格（需要已發表資料的 reference，§B.9）。

**交付物：** `element_sim`、`simroot`、`simreco` 與其測試；`geant4_run.py check-spec`、`from-geometry`、`reco`、`table`；`check_geant4_study.py label`、`evaluate_design.py f4`、`contracts/design.py` 的 CV-B2 變更；幾何對照表 1.1.0；J15 範例 `examples/design-minimal-spectrometer/`（design-spec、候選、evaluation、研究紀錄、README、recorded 資料）；J15 journey 與路由案例；VALIDATION 條目 GEANT4-ELEMENT（B1）、GEANT4-F4（B2）、GEANT4-J15（B3）；CHANGELOG；release manifest。

**完成的定義：** B1.10、B2.10、B3.9 的驗收清單全部打勾；§A.8 的檢查全部通過；閘門 G-B1a、G-B1b、G-B2（§P.6）通過；B2.8 的資格規則與 B3 的 F4 確認在 D0 核准後才合併。

**主要決定：**
1. **新增後端，不改 `layered_sim`。** `element_sim` 讓 J14 的程式不動，並以真正的第二個後端驗證輸出層介面（§R.3.2）。
2. **候選設計是唯一的真實來源。** F4 研究的幾何一律由 `evaluate_design.py geometry` 從候選產生，`element_sim.spec/1` 由它確定性推導（B1.8）；手寫的 spec 只用於不作為 F4 的研究。
3. **場精度用確定性檢查。** charged geantino 對解析螺旋，不需要統計；在 B1 完成（B1.7）。
4. **F4 經資格路徑。** 偵測器層級的研究只有在材料、場、重建都通過驗證，而且徑跡 reference benchmark 通過時，才能經 `label --upgrade` 成為 `validated-in-scope`（B2.8，D0）。J15 的驗證梯另立一份永遠 `unvalidated` 的紀錄（B3.2）。
5. **尾部來源誠實申報。** 四種尾部來源（alignment、calibration-non-uniformity、noise-digitization、pattern-recognition）是 `simreco` 的可切換階段；研究紀錄只列實際模擬的來源，沒有就寫空陣列；只有四種都模擬時，解析度與電荷誤判的 F4 才是 `estimate`（`contracts/design.py:64`、`1058-1059`）。
6. **基礎設施與物理研究分開。** B2 交出 F4 介面與 `simreco`，讓任務 C 的 C2 不必等 J15 研究（§P.1 P3）。
7. **hep-detector 不新增腳本。** 重建在 C++ 的 `simreco`，介面在 adapter；只修改既有的 `check_geant4_study.py`、`geant4_benchmarks.py`、`evaluate_design.py`（腳本數維持 23）；quick load 與 description 不變。

**第一步：** 依 §P.10.2 為本階段建立 isolated worktree（`.claude/worktrees/geant4-<階段>`，分支 `worktree-geant4-<階段>`，基底為已含前提階段的最新 `origin/main`），並確認 `git rev-parse --show-toplevel`、`git branch --show-current`、`git status` 與前提階段的合併 commit 是 `HEAD` 的祖先。以下所有步驟都在這個 worktree 中進行。

**開始前必做：**
1. 確認 A2 已合併，§B.2 列的介面都存在；B2 開始前確認 D0 的狀態（§P.7）。
2. 依 §A 附錄 C 的方法，以當時的 `main` 重新核對本部引用的事實（quick load、description 長度、journey 清單、`DetectorScriptCount`、contracts 版本、`MISSING_FILE_ARGS` 的結構、`design_geometry.json` 的版本、`check_f4` 讀取的欄位），並更新本部（中英兩版）。
3. 讀 §A.1、§A.3、§A.4、§P.4–§P.6 與 main 的 `skills/hep-detector/references/system-design-workflow.md`；本部不重複。

---

## §B.1 名詞與檔案

| 名詞 | 意義 |
|---|---|
| J15 | 本任務的最小磁譜儀（合成幾何），以設計專案的形式存在（B3.1） |
| `element_sim` | B1 新增的 Geant4 程式；spec `element_sim.spec/1` |
| `design-geometry/1` | main 的 `evaluate_design.py geometry` 從候選產生的幾何檔（欄位依 `contracts/rules/design_geometry.json`），帶參數摘要 |
| 實現設定檔 | `element_sim.realization/1`：對照表沒有的幾何事實（材料、橫向大小、場區範圍、座標原點、尚未進對照表的子系統），由 `from-geometry` 讀取；雜湊進 `input_manifest`（B1.8） |
| F1–F5 | main 的保真度（`contracts/design.py:65`）：F1 解析工具、F2 toy MC、F3 response 與預期精度、F4 經 `label --upgrade` 重新發出的 Geant4 研究、F5 量測 |
| figure of merit、分母 | main 適足表（`contracts/rules/design_adequacy.json`）的量，例如 `momentum-resolution-core`（分母 `rigidity_GV`、`species`） |
| 尾部來源 | `contracts/design.py:64` 的四種：alignment、calibration-non-uniformity、noise-digitization、pattern-recognition |
| 偏轉平面 | x–y 平面（B 沿 z）；非偏轉方向為 z |
| 剛度 R | p/\|q\|，單位 GV；C = 0.2998 GV/(T·m) |
| MDR | 最大可偵測剛度：只算量測項時 σ_R/R = 1 的剛度 |
| TOF 站 | TOF1 或 TOF2；每站兩層（a、b） |
| charged geantino | Geant4 中只受場作用、無物質交互作用的帶電測試粒子（質量 0，β = 1） |
| 處理鏈 | 模擬 → 縮減 → 數位化與重建 → 表格，每一步一份 computational-run 紀錄 |
| 記法 | 「B1.3」是本部的工作項；「§B.4.2」是本部的節；「A1.6」「C2.1」是任務 A、C 的工作項；「§A.3」「§P.4」「§R.6」是本文件其他部的節 |

**主要檔案（相對 `plugins/hep-research/`）：** `adapters/geant4/assets/g4sim/`（A2 建立，本任務擴充）；`adapters/geant4/assets/element_sim/`（新增）；`adapters/geant4/assets/simroot/`（新增）；`adapters/geant4/assets/simreco/`（新增，不連結 Geant4）；`adapters/geant4/assets/geant4_run.py`（新增 `check-spec`、`from-geometry`、`reco`、`table`；`SIM_SOURCES` 行 63 定義，行 327、386 使用）；`core/stats/decisions.py`（B2 加入 `change`）；`contracts/validate.py`、`contracts/dependencies.py`、`contracts/design.py`、`contracts/rules/design_geometry.json`、`contracts/schemas/design_geometry.json`（CV-B2）；`skills/hep-detector/scripts/check_geant4_study.py`（`label`，行 540–630）、`skills/hep-detector/scripts/geant4_benchmarks.py`（`GRADES` 行 92、新的 benchmark 函式）、`skills/hep-detector/scripts/evaluate_design.py`（`geometry` 行 462、`f4` 行 498）；`skills/hep-detector/assets/geant4-study-spec.schema.json`；`skills/hep-detector/references/geant4-study-protocol.md`、`system-design-workflow.md`；`tests/skills/test_cli_robustness.py`（`MISSING_FILE_ARGS`，`geant4_run.py` 的條目在行 153）；`docs/researcher-journeys.md`、`docs/maintenance.md`、`docs/capability-matrix.md`（行 49 的「twenty-three scripts」，由 `tests/skills/test_documented_output_claims.py` 行 145 的測試類別 `DetectorScriptCount` 檢查）、`docs/capability-map.json` 與 `docs/capability-map.md`；`examples/design-minimal-spectrometer/` 與 `tests/examples/test_design_minimal_spectrometer.py`（新增）。

---

## §B.2 前提與提供的介面

**前提（任務 A 提供）：**

| 介面 | 任務 B 的用法 |
|---|---|
| benchmark 表、驗證類別、範圍比對、隔離規則（A1.1–A1.3） | B2 附加 verification、regression、徑跡 reference 的條目與資格規則；J15 驗證梯的 benchmark 都是 embedded，不計入升級 |
| evidence 角色與 S 的唯一性（A1.4） | B2 附加 regression 角色 |
| 區塊估計量、精確區間、MPV、判定引擎 `equivalence`、兩階段事件數（A1.6–A1.10） | B3 的判定；B2 依同一介面加入 `change`；F4 的 `statistical_uncertainty` 取 68.27 % 的 t 半寬（A1） |
| `simulation-summary/1`、`simulation-observables/1`（A1.5，schema 在 `contracts/schemas/`） | `element_sim` 與 `simreco` 以同一 schema 寫出 summary |
| `label` 與 `f4` 的相容修正：`f4` 轉傳 `--label-run-record`、`label` 結束碼 3 對應 `incomplete`（A1） | B2 的端到端測試沿用 |
| `g4sim`：`SimHash.hh`、`SimSeed.hh`、`SimSummary.hh`、`MiniJson.hh`、`SimProbe.hh`、材料與 physics list 輔助（A2.1） | `element_sim` 使用全部；`simreco` 只用不連結 Geant4 的 `SimHash.hh`、`SimSummary.hh`、`MiniJson.hh` |
| `per-event` 種子（在 `GeneratePrimaries` 開頭重設，A2.2） | `element_sim` 只支援 `per-event` |
| 三個邊界產物、不含名稱的 `tree-v1`、effective config 存放、run record 的 `argv` 與 `script_sha256`（A2.3–A2.6） | `element_sim` 與 `simreco` 交出同樣的邊界產物；附加在目標內的場計入 `tree-v1` 目標雜湊 |
| schema 關鍵字 `maxItems`、`maximum`、`exclusiveMaximum`（A2.7） | `element_sim.spec/1` 與 `element_sim.realization/1` 的 schema |

**前提（main 已提供）：**

| 介面 | 位置 | 任務 B 的用法 |
|---|---|---|
| `evaluate_design.py geometry`：從候選產生 `design-geometry/1`，設定候選的 `geometry_ref` | `evaluate_design.py:462-495` | `from-geometry` 的輸入（B1.8） |
| `evaluate_design.py f4` 與 `contracts/design.py` 的 F4 檢查 | `evaluate_design.py:498-560`；`design.py:988-1062` | B2.6 的輸出必須通過；B2 修改兩處（CV-B2） |
| 幾何對照表 `layered-spectrometer` 1.0.0 | `contracts/rules/design_geometry.json` | 徑跡與磁場五個欄位；B2 擴充為 1.1.0 |
| 適足表 | `contracts/rules/design_adequacy.json` | figure of merit、分母、合規保真度（解析度 F3、電荷誤判 F4 並需資料驗證與剛度尺度偏移、簇射包含 F4、tracking-selection-efficiency F4） |
| F1、F2 工具 | `tracker_resolution`、`multiple_scattering`、`toy_spectrometer`（F2）、`design_estimates.py infield-acceptance`（F2） | B3 的 F1、F2 evaluation |
| 範例專案的格式 | `examples/design-space-spectrometer/` | J15 設計專案的格式 |

**提供給任務 C 的介面：**

| 介面 | 工作項 | 任務 C 的用法 |
|---|---|---|
| `element_sim.spec/1`、`check-spec` | B1.1、B1.6 | C2 的 Geant4 搜尋值所用的 spec 由 `from-geometry` 產生並驗證 |
| `geant4_run.py from-geometry` 與實現設定檔 `element_sim.realization/1` | B1.8 | C2 由解碼後的候選經 `geometry` 與 `from-geometry` 得到 spec；同一個實現設定檔用於整個搜尋 |
| 量能器母體與 `leak_*_MeV` | B1.3 | 量能器子系統的搜尋值 |
| `simreco`（剛度、β、量能器能量）與尾部來源開關 | B2.1、B2.2 | 搜尋值的重建；確認研究的尾部來源 |
| F4 結果檔與 `label --results`、`--geometry` | B2.6 | C2 對決選者的 F4 確認 |
| 判定引擎 `change` | B2.7 | C2 的版本回歸檢查 |

---

## §B.3 硬性限制

§A.3 的全部限制都適用。另外：

1. 不修改 `skills/hep-detector/SKILL.md` 與 hep-detector 的 description（quick load 只剩 931 bytes；description 1,016 / 1,024 字元）。J15 的路由案例必須沿用 description 中已有的觸發詞。
2. `skills/`、`contracts/`、`core/` 中不得出現實驗名稱；契約表與 protocol 引用參考文獻時用引用鍵。實驗名稱（PAMELA、AMS-02）只可出現在 `docs/` 與 J15 的 `examples/` README。
3. 場的程式依 Geant4 API 撰寫，不複製或改寫 B5 範例的程式碼（G5）。
4. 共享 stanza 的文字不改（點 5 寫「3.1.0 upgrade rule」；修改會牽動全部 SKILL.md 與 live 路由重跑）。
5. J15 的 `recorded/` 每檔 ≤ 2 MiB、總和 ≤ 3 MB；ROOT 檔不提交（B3.7）。
6. J15 驗證梯的紀錄（B3.2）永遠 `unvalidated`，其中的 benchmark 不計入升級。J15 的 F4 研究（B3.6）只有經 B2.8 的資格路徑與 `label --upgrade` 才能 `validated-in-scope`；不得宣稱未升級的研究是 F4。
7. `layered_sim` 不加幾何功能；新的幾何功能只加在 `element_sim`。
8. Python 與 `simreco` 都不直接解析 ROOT；一律經 `simroot`。
9. 契約規則以 `strict or _at_least(contract_version, CV-B2)` 閘控。
10. 遵守 main 設計流程的「Never」（`system-design-workflow.md:201-208`）：不手寫判定、成熟度、過時標記；evaluation 只由 `evaluate_design.py` 寫出，寫出後不修改；F4 evaluation 只由 `evaluate_design.py f4` 產生。
11. F4 研究所用的 `design-geometry/1` 與由它推導的 `element_sim.spec/1` 不得手改；改變幾何就是改候選，再重新產生。

---

## §B.4 J15 的設計

### §B.4.1 幾何

座標：世界中心為原點，堆疊軸 x，單位 mm。

**磁場：B = (0, 0, +0.5 T)。** 偏轉平面為 x–y，非偏轉方向為 z。正電荷沿 +x 運動時偏向 −y；μ⁻ 偏向 +y。

```
x:  −1000   −810 … −780   −520 −500        …         300  320    490 … 520   550          900   ±1200
     gun    TOF1（兩層）   │ Si1  Si2  Si3  Si4  Si5  Si6  │     TOF2（兩層）  量能器 50 層    世界邊界
            10 + 10 mm    │◄────── 均勻場 0.5 T ẑ（−520 … 320）─────►│     10 + 10 mm   Pb 2 / PVT 5 mm
```

| 元件 | 材料 | 前表面 x | 厚度 | 範圍 | 橫向（y × z） |
|---|---|---|---|---|---|
| 世界 | `G4_Galactic` | — | 2400 | −1200 … 1200 | 1200 × 1200 |
| 粒子源 | — | x = −1000，y = z = 0 | — | — | — |
| TOF1a、TOF1b | `G4_PLASTIC_SC_VINYLTOLUENE` | −810、−790 | 各 10 | −810 … −800、−790 … −780 | 300 × 300 |
| 場區母體 | `G4_Galactic` | −520 | 840 | −520 … 320 | 300 × 300 |
| Si1–Si6（子體） | `G4_Si` | −500.15 + 160k | 0.3 | 中心 −500、−340、−180、−20、140、300 | 200 × 200 |
| TOF2a、TOF2b | `G4_PLASTIC_SC_VINYLTOLUENE`（和 TOF1 相同） | 490、510 | 各 10 | 490 … 500、510 … 520 | 400 × 400 |
| 量能器母體 | `G4_Galactic` | 550 | 350 | 550 … 900 | 500 × 500 |
| 量能器取樣層（子體） | 50 × (`G4_Pb` 2 + PVT 5) | 550 | 350 | 550 … 900 | 500 × 500 |

**TOF 站。** TOF1 與 TOF2 各兩層；四層同材料、同厚度（10 mm），每站兩層之間有 10 mm 真空間隙。每層是整片平板，不分割、不設 paddle 方向（刻意的簡化）；兩層提供兩次獨立的時間量測與 dE/dx 取樣，並讓同站兩層的一致性成為一項檢查（B3.2）。

**核對**（§B 附錄 A 的程式，測試中重算）：
- 量測臂長 L = 0.800 m；Si1 前緣和 Si6 後緣距母體邊界各 19.85 mm。
- 場在量測區兩端各多延伸 20 mm。
- TOF 站中心（兩層的中點：−795、505 mm）之間的距離 D = 1.300 m。
- TOF2 後層的後表面（520）距量能器前表面（550）30 mm；TOF1 前層（−810）在粒子源（−1000）的下游。
- 世界包含粒子源與量能器後端。

材料（11.4.3 的 NIST 定義對照 PDG）：`G4_PLASTIC_SC_VINYLTOLUENE` 1.032 g/cm³、I = 64.7 eV；`G4_Si` 2.33 g/cm³（PDG 2.329）。

**刻意的簡化**（J15 的 README 逐條列出）：名義上是均勻場與銳利邊界（分區均勻場只用於誤校正，B1.2）、無磁鐵材料、TOF 每層不分割、無光學光子、無觸發與讀出電子學、無反符合。矽的條帶、門檻、效率、雜訊與分群在 `simreco` 中以可切換的數位化階段處理（B2.2），名義設定關閉。

### §B.4.2 參數與接受度

| 參數 | 值 | 依據 |
|---|---|---|
| B | 0.5 T | 多重散射項等於量測項的剛度約 16–22 GV（μ），與 B 無關；0.5 T 讓 1–10 GV 與 100–1000 GV 各有一個十倍區間 |
| Si 層數 | 6 | N = 4 時偏轉平面只有 1 個自由度；N = 8 的 MDR 只改善約 8 % |
| MDR | 約 1172 GV | 只算量測項。參考值取自 `tracker_resolution.py` 的精確最小平方（C = 0.2998）。`multiple_scattering.py` 的 `mdr_intrinsic_only_gv` 同定義但用 Gluckstern 近似（N = 6 時約 1131 GV）；0.21.0 起另輸出 `intrinsic_coefficient` 並在 N < 10 時警告 |
| TOF | 每站兩層；σβ/β ≈ 2.3 %（每層 100 ps、兩層獨立、β = 1；每站一層時 3.3 %）；150 ps 時 3.5 % | D = 1.3 m；站時間取兩層平均，σ_站 = σ_層/√2 |
| 量能器 | 18.4 X₀、0.886 λ_I、寬 50 cm | 足以用簇射形狀分離 e/p，不足以量強子能量 |

**多重散射項。** Highland 公式，對總厚度取 log 項，乘 1.0–1.4 的係數。審查以離散散射平面做精確最小平方，係數為 1.02（加權）到 1.06（不加權）。`multiple_scattering.py` 依其約定**不含** log 項；比較時寫明差異。

| 粒子 | 剛度 | β | 多重散射項 | 兩項相等的剛度 |
|---|---|---|---|---|
| μ | 1 GV | 0.994 | 1.3–1.9 % | 16–22 GV |
| p | 0.6 GV | 0.539 | 2.5–3.5 % | 29–41 GV |
| p | 1 GV | 0.729 | 1.8–2.6 % | 21–30 GV |
| p | 2 GV | 0.905 | 1.5–2.1 % | 17–24 GV |

**接受度**（單位電荷、軸上正入射、均勻場、銳利邊界）：

| 條件 | 最低剛度 |
|---|---|
| 在 x = 320 前不從場區母體側面離開（\|y\| ≤ 150 mm） | 0.364 GV |
| 到達 Si6（\|y\| ≤ 100 mm） | 0.511 GV |
| 到達 TOF2 前層（x = 490，\|y\| ≤ 200 mm） | 0.385 GV |
| 穿過 TOF2 兩層（x = 520，\|y\| ≤ 200 mm） | 0.404 GV |
| 量能器前表面，簇射軸在 250 − 2 R_M,eff 內 | 0.490 GV |
| 量能器後表面，同上 | 0.745 GV |

整體門檻 0.75 GV；只要求徑跡加 TOF 時 0.51 GV。低於 0.364 GV 的軌跡從場區側面離開，之後在無場的世界中走直線。接受度的 F2 evaluation 由 main 的 `design_estimates.py infield-acceptance` 給出（B3.1）。

電子：簇射軸在 1 GeV 時於量能器前、後表面偏離 82 mm 與 127 mm，5 GeV 時 16 mm 與 25 mm。上游 11.3 % X₀（四層 TOF 佔 83 %）的軔致輻射光子不受偏轉，所以簇射軸不是直線外推；79 mm 邊距是幾何估計，簇射檢查要以實際的橫向能量分布核對。電子的簇射檢查限 1 GeV 以上。

**上游能損**（Bethe 積分，TOF1 兩層共 2 cm PVT）：

| 質子剛度 | 動能 | TOF1 能損 | Δp/p | β 在兩站中心之間的變化 |
|---|---|---|---|---|
| 0.6 GV | 175 MeV | 10.23 MeV | 3.20 % | 2.87 % |
| 1 GV | 433 MeV | 6.00 MeV | 0.82 % | 0.46 % |
| 2 GV | 1271 MeV | 4.34 MeV | 0.24 % | 0.05 % |

0.6 GV 時 β 在兩站之間變化 2.87 %，大於 TOF 解析度（2.3 %）：低剛度的 β 比較要用含能損的 β 模型，或限於 2 GV 以上。TOF1 在第一片 Si 之前，不影響曲率解析度；剛度真值取自 Si 平面的穿越紀錄。

**不能沿用 J14。** J15 的 Si 和 J14 的材料（`G4_Si` 對 `Si_study`）、物理設定、cut 都不同，而且 J15 只記錄入射，組不出 J14 的 E_in − E_exit 觀測量。

### §B.4.3 和實際儀器的對照

| 儀器 | 配置（出處見 §R.14） | 和 J15 比較 |
|---|---|---|
| PAMELA | 0.43 T 永久磁鐵；6 片雙面矽微條平面，解析度優於 4 µm；MDR 超過 1 TV；三個 TOF 平面（S1–S3，分割成 paddle）；鎢／矽成像量能器 16.3 X₀、0.6 λ；另有反符合、S4、中子偵測器 | 幾乎同型；J15 的 Si 解析度假設 10 µm（較保守）、TOF 不分割、沒有反符合 |
| AMS-02 | TOF 四個平面（8、8、10、8 個計數器）；系統對質子約 140 ps | J15 每層 100 ps 較樂觀，所以做 100 與 150 ps 的敏感度（B3.5） |

J15 的 README 以這張表說明 J15 的合理性，並強調 J15 是合成幾何、不代表任何實驗。main 的 `examples/design-space-spectrometer`（類 AMS 的三個候選，只到 F1）是另一個範例；J15 補上它缺少的 F2 到 F4。

### §B.4.4 J15 在設計流程中的表示

| 產物 | 內容 |
|---|---|
| design-spec `j15-v1` | 目標與需求（數值是示意，README 註明合成）：`REQ-TRK-001` `momentum-resolution-core`（質子 1 GV）；`REQ-TRK-002` 同上（質子 100 GV）；`REQ-CC-001` `charge-confusion-rate`（質子、宣告的 `curvature_offset_per_GV` 及其容許）；`REQ-CAL-001` `shower-containment`（電子 10 GeV）；約束（質量、通道數）列出 `subsystems`；衍生需求以 `covered_by` 指向驅動需求；`comparison_basis` 等質量；`pareto_axes` 含 `expected-precision` |
| 候選 `cand-N6`（名義） | `DES-TRK-001`（role `tracking`）：`layer_positions_m` = [0, 0.16, 0.32, 0.48, 0.64, 0.80]、`point_resolution_um` = 10、`layer_x_over_x0` = 0.0032（0.3 mm Si）、`passive_x_over_x0` = 0；`DES-MAG-001`（role `bending`）：`field_T` = 0.5；`DES-TOF-001`（role `tof`）與 `DES-CAL-001`（role `calorimetry-em`）的參數依對照表 1.1.0（B2.6）；每個子系統都有校正（方法與控制樣本）與合成的預算 |
| 變體 `cand-N4`、`cand-N8` | `derived_from: cand-N6`，`overrides` 只改 `layer_positions_m` 與 `layer_x_over_x0`（等距、同臂長） |
| 實現設定檔 `j15.realization.json` | 座標原點（Si1 中心 x = −500 mm）、堆疊軸 x、場沿 z、層材料 `G4_Si`、各元件橫向大小、場區範圍（量測區兩端各 20 mm）、TOF 與量能器的元件（在對照表 1.1.0 之前）、世界大小；所有數值和 §B.4.1 一致 |

`from-geometry`（B1.8）由候選的幾何檔與這個設定檔重建 §B.4.1 的幾何；測試比對兩者逐元件相同。

---

## §B.5 階段 B1：`element_sim`、事件檔與幾何推導（geant4 adapter 0.3.0）

### B1.1 `element_sim` 與其 spec

**位置：** `adapters/geant4/assets/element_sim/`（CMake 專案，連結 Geant4 與 `g4sim`）。

**spec `element_sim.spec/1`**（schema 放在同一目錄，只用 `contracts/schema.py` 支援的關鍵字）：

| 區塊 | 內容 |
|---|---|
| 座標 | 世界中心為原點，mm；元件以中心座標與半長給出（盒狀）。**所有中心座標都是世界座標**（包括子體）；`element_sim` 自行換算為母體座標放置（例如場區母體中心 x = −100，Si1 的世界中心 x = −500 → 母體座標 −400） |
| `materials` | NIST 名稱或混合材料（成分順序保留；`g4sim` 的材料輔助） |
| `elements` | 盒狀元件：名稱、材料、中心、半長、母體（世界或一個元件；只允許一層巢狀）、角色（`passive`、`tracker-plane`、`tof-layer`、`calorimeter`（母體）、`calorimeter-active`、`calorimeter-passive`）、重複（用於量能器的取樣層） |
| `field` | `regions[]`：每區附加的元件、B 向量（區內均勻）；精度參數（B1.2）。J15 名義上只有一區 |
| `physics` | physics list 與 EM 選項、cut、region（同 `layered_sim` 的語意，經 `g4sim`） |
| `source` | `type: gun`：粒子、能量（`energy_MeV` 或 `ekin_per_nucleon_MeV`）、位置、方向；`gps` 與 `event-file` 只定義介面（§R.9.2），遇到時 exit 2 |
| `run` | 事件數、執行緒、邏輯 run 種子；`seeding` 只允許 `per-event` |
| `output.observables`、`output.blocks` | 同 A2.3（引用 `simulation-observables/1`） |
| `output.event_file` | `level`：`none`（預設）、`summary`、`crossings`、`hits`；`compression`（預設 1）；`max_events_hits`（`hits` 層級允許的最大事件數，預設 100） |
| `provenance` | 由 `from-geometry` 產生時：幾何檔、實現設定檔的路徑與 sha256、候選 id 與參數摘要；手寫時省略 |

- 跨欄位規則（元件不重疊、子體在母體內、名稱唯一、角色與材料相容、場區不重疊）在 Python 的 adapter 中檢查（B1.6 的 `check-spec`）；C++ 只檢查執行所需的最低限度。
- 每個 run 交出三個邊界產物（summary、column map、effective config），與 `layered_sim` 相同。

### B1.2 場

- 在 `ConstructSDandField` 中為每個場區建立 `G4UniformMagField`、`G4FieldManager`、`G4ChordFinder`，以 `G4ThreadLocal` 儲存；master 與每個 worker 各有一份。在 `Construct()` 中建立會讓 worker 共用非執行緒安全的 chord finder。
- 以 `SetFieldManager(fm, true)` 附在該區的元件上，傳遞到所有子體；場區不得巢狀。
- 有場時加入 `G4StepLimiterPhysics`。
- stepper 與 driver **明確建立**：以 `G4Mag_UsualEqRhs` 建立 `G4DormandPrince745`，包成 driver（例如 `G4InterpolationDriver<G4DormandPrince745>`），再以 `G4ChordFinder(G4VIntegrationDriver*)` 建構（中等信心，類別與建構子以 11.4.3 原始碼核對）；不用 `G4ChordFinder` 預設建構子所選的 stepper（那不受 `G4FieldParameters` 控制）。stepper 類別寫入 spec，探針以 RTTI 記錄 stepper 與 driver 的實際類別名（helix stepper 會讓場傳輸檢查失去意義）。
- **分區均勻場**是場圖之前的最小形式：讓磁場尺度的誤校正（`simreco` 以每區的名義值重建，B2.2）成為可模擬的尾部來源。真正的場圖與邊緣場延後（§B.9）。
- 依 API 撰寫，不複製或改寫 B5 範例的程式碼（G5）。

| 參數 | 名義值 | 備註 |
|---|---|---|
| `delta_chord_mm` | 0.25 | 最大步長小於約 80 mm 時不起作用，只記錄不掃描 |
| `delta_one_step_mm` | 0.01 | 均勻場中 Runge–Kutta 的截斷誤差遠小於交點誤差，預期掃描無影響；做一次確認 |
| `delta_intersection_mm` | **1e-5**（0.01 µm） | 決定穿越點的精度 |
| `min_epsilon_step` | 5e-5 | |
| `max_epsilon_step` | 1e-3 | epsilon = delta one step / 步長，會被夾在這個上限 |
| `max_step_mm` | 10 | 需要 `G4StepLimiterPhysics`；`G4UserLimits` 必須逐體積設定，不會傳遞到子體 |
| `stepper` | DormandPrince745 | 明確建立（見上） |

- **探針：** `SimProbe.hh` 走訪 `G4LogicalVolumeStore`，以 `GetFieldManager()` 讀回各區的 B、chord finder 與各精度參數；依指標去重，記錄原始附加的體積；註明 master 只看到 master 的副本。附加在目標內體積的場計入 `tree-v1` 目標雜湊。
- **MT 測試：** 只在測試建置中存在的 UI 指令，回報每個執行緒的 field manager 指標，必須彼此不同。

### B1.3 平面穿越與量能器漏失

- **穿越：** **每一條帶電徑跡**（不只主粒子）在 `tracker-plane` 或 `tof-layer` 元件第一次進入時（前步點狀態為 `fGeomBoundary` 且所在體積為該平面），記錄 `track_id`、`parent_id`、PDG 碼、前步點的位置、方向、動能、全域時間；每條徑跡、每個平面一個「已記錄」旗標。粒子源若位於平面內，不會出現 `fGeomBoundary`，該平面不寫列。主粒子的列以 `track_id = 1` 辨識；B2 的 hit 指派以全部列為輸入，所以 δ 射線與次級粒子造成的假 hit 能被模擬（pattern-recognition）。
- **量能器漏失：** 角色為 `calorimeter` 的母體元件，記錄每個事件中從母體內部離開母體的粒子帶走的能量（`post` 步點離開該母體的步；正子加 2 mₑc²；乘 track 權重），依離開的面分為 `leak_rear_MeV`（+x 面）、`leak_front_MeV`（−x 面）、`leak_lateral_MeV`（y、z 面），語意和 `layered_sim` 的同名欄相同（`layered_sim` 以世界邊界為面，`element_sim` 以量能器母體為面）。這三欄寫入 CSV、`events` ntuple 與 column map，供 shower-containment（`geant4_benchmarks.py` 的 `bench_containment()`，行 482）與 B3.3 的後漏比例使用。
- 逐事件 CSV 只保留摘要欄（主粒子真值、各子系統總沉積、量能器漏失）；穿越與逐層沉積寫入 ROOT 檔（B1.4）。

### B1.4 逐事件 ROOT 檔

| 項目 | 規格 |
|---|---|
| 寫出 | 經 `G4AnalysisManager`（ROOT 輸出類型）；底層是 Geant4 內附的 g4tools，不需要安裝 ROOT，不新增建置依賴 |
| 檔案 | 每個工作一個檔；MT 下以 `SetNtupleMerging(true)` 由 master 合併成單一檔（11.4.3 中只有 ROOT 輸出支援 ntuple 合併）；路徑經 `tilde()` 寫入 run record |
| 結構 | 扁平 ntuple，只用純量欄（I、D、S），每列帶鍵（`event_id` 加 ntuple 自己的次鍵）；不用 vector 欄 |
| 列的順序 | MT 合併後不固定；讀取端一律依鍵排序 |
| 寫出時機 | `EndOfEventAction` 填列；run 結束時寫檔並關閉。run 中斷時檔案不完整，run 判為 incomplete（exit 3） |
| 版本 | 結構 `element_sim.events/1`，檔內帶 `event_file_version` |
| 雜湊 | 檔案位元組含寫出時間，不逐位元相同；run record 同時記錄檔案 sha256（完整性）與 `simroot hash` 的 `content_sha256`（比對與 provenance）。一個邏輯 run 有多個工作檔時，`content_sha256` 對所有檔案的聯集依鍵排序後計算（`run` ntuple 除外，它逐檔不同），`processes` 依 `process_id` 去重，所以和切法無關 |
| 大小 | 不提交；run record 記錄路徑、雜湊、各 ntuple 列數與大小 |

| ntuple | 層級 | 每列 | 欄位 |
|---|---|---|---|
| `run` | `summary` 起 | 每檔一列 | spec 與 column map 的 sha256、程式版本與原始碼雜湊、Geant4 版本、邏輯 run 種子、事件範圍、`event_file_version` |
| `processes` | `summary` 起 | 每個 process 一列 | `process_id`、`name`（`hits` 的 process 編號對照表） |
| `events` | `summary` 起 | 每事件一列 | `event_id`、主粒子 PDG 碼、動能、起點、方向；各子系統總沉積；`leak_rear_MeV`、`leak_front_MeV`、`leak_lateral_MeV`；離開世界體積的能量；旗標 |
| `deposits` | `summary` 起 | 每事件 × 每個有沉積的體積一列 | `event_id`、`volume_id`、`copy`、總沉積、帶電粒子的沉積 |
| `crossings` | `crossings` 起（`hits` 也包含） | 每事件 × 每條帶電徑跡 × 每個被穿越的平面一列 | `event_id`、`plane_id`、`track_id`、`parent_id`、PDG 碼、前步點位置、方向、動能、全域時間、該徑跡在該平面的沉積 |
| `hits` | 只在 `hits` | 每個有沉積的步一列 | `event_id`、`track_id`、`step_index`（該 track 的步序號；和 `event_id`、`track_id` 組成唯一鍵）、`parent_id`、PDG 碼、`volume_id`、`copy`、前後步點位置、時間、沉積、步長、`process_id` |

- `process_id` 在初始化時以確定的規則指定（例如依 process 名稱排序），與執行緒和工作切分無關；`run` 與 `processes` 只由 master 填寫，worker 不寫這兩個 ntuple。
- `hits` 層級要求的事件數超過 `max_events_hits` 時，spec 驗證以 `rejected`（exit 2）拒絕。
- 估計（J15，`crossings` 層級）：主粒子之外的帶電徑跡（δ 射線、量能器反散射）使列數增加；壓縮前每事件約 4–8 kB（`crossings` 10–30 列 × 100 B、`deposits` 最多 110 列 × 28 B、`events` 約 120 B）；10⁵ 事件壓縮前最多約 800 MB。實際大小在 trial run 中確認。

### B1.5 `simroot`

**位置：** `adapters/geant4/assets/simroot/`（和 `element_sim` 同一個 CMake 專案；只連結 Geant4 的 analysis 函式庫，不建立 run manager）。

- **閘門 G-B1a（開始的第一天）：** 確認 `G4RootAnalysisReader` 能讀 MT 合併、壓縮過的檔案與字串欄。兩種結果都可接受：能讀時照原設計；不足時 `simroot` 只讀扁平純量欄，`run` 的字串改寫到 JSON 旁檔。結果記入 VALIDATION 條目。

| 子命令 | 內容 |
|---|---|
| `info` | 各 ntuple 的列數與欄位、`run` 列的內容；輸出 JSON |
| `dump` | 依鍵排序後，把指定 ntuple 與欄位寫成 CSV（stdout 或 `--out`），浮點以 `%.17g`；可一次讀多個檔；`--events` 取子集 |
| `hash` | 內容雜湊：各 ntuple 依鍵排序，數值以 hex-float 正規化後計算 sha256；輸出 `content_sha256` |

- 退出碼依 `core/status.py`。研究者可以用 ROOT 或 uproot 直接分析 ROOT 檔，但它們不是管線或必要測試的依賴。

### B1.6 `check-spec` 與兩個後端的介面一致性

- **`geant4_run.py check-spec --spec <file>`：** 以 schema 與跨欄位規則驗證 `element_sim.spec/1`（不需要 Geant4）；輸出 JSON 的 `{ok, problems[]}`，退出碼 0 或 2。B1 把 `tests/skills/test_cli_robustness.py` 的 `MISSING_FILE_ARGS` 擴充為「每個腳本可對應一組或多組 argv」（目前 `geant4_run.py` 只有 `run` 一組，行 153），並登記 `check-spec` 與 `from-geometry`。
- `element_sim` 交出的三個邊界產物通過和 `layered_sim` 相同的介面測試（schema、雜湊、column map 的語意名稱）。
- **統計一致性只比兩個後端都產生的觀測量。** J14 的 `stopping-power`、`range` 與 `thin-layer-mpv` 需要 `primary_eloss_MeV`、`primary_fate`、`primary_end_process`（`geant4_benchmarks.py` 的 `transmitted()` 行 232、`bench_stopping_power` 行 278、`bench_range` 行 311、`bench_mpv` 行 347），`element_sim` 不產生這些欄，所以不比較 J14 的 benchmark 判定。
- 做法：和 J14 nominal 相同的平板（`Si_study` 以混合材料宣告相同的組成與密度、相同的物理設定與 cut），兩個後端各跑一個邏輯 run（`layered_sim` 用 `stream`、`element_sim` 用 `per-event`，事件不同）；比較矽中沉積 `edep_Si_MeV` 的平均與眾數（A1.7），以及量能器型配置的**總漏失**比例（`leak_rear_MeV + leak_front_MeV + leak_lateral_MeV` 除以入射能量；兩個後端的「面」不同，`layered_sim` 是世界邊界、`element_sim` 是量能器母體，單一面的比例不可比）。每個觀測量以 `equivalence`（A1.8）判定，容許值與 se 目標（se_diff ≤ tol/4）事先宣告；未通過時不合併（閘門 G-B1b）。

### B1.7 確定性場檢查（`field-propagation`）

不需統計；只需要 `element_sim`。

- 軌跡：charged geantino（質量 0，β = 1），剛度 0.6、1、10、100、1000 GV。
- 方向：正入射；偏轉平面內 **50 mrad，方向和偏轉相反**（正電荷取 +y）；非偏轉平面 ±50 mrad。
- §B 附錄 A 核對：在這組方向下，每條軌跡都到達每片 Si 和 TOF2 的兩層，也不離開場區母體。若改成順偏轉方向，0.6 GV 和 1 GV 會錯過 Si6。
- 參考：解析螺旋；軌跡離開場區時改為分段直線，只比較解析軌跡實際到達的平面。分區場的配置另以兩區（B 不同）各自的解析螺旋分段核對。

| 掃描 | 格點 | 判定 |
|---|---|---|
| delta intersection | 1e-3、1e-4、1e-5、1e-6 mm | 名義值（1e-5）下，所有平面的平面內距離 √(Δy² + Δz²) ≤ 0.5 µm（ε/20），解析軌跡在平面的 x 上取值；最細兩組相差 ≤ 0.2 µm；另記錄 Geant4 穿越點的 \|x − x_平面\|。各格點的結果都回報，不預設 1e-3 mm 一定不通過（Geant4 的交點誤差主要沿 x，換成平面內誤差只約為斜率 × δ ≤ 0.25 µm） |
| 最大步長 | 100、30、10、3 mm | 同上 |
| delta one step 與 epsilon | 名義值與 1/10 | 預期無變化，做一次確認 |
| TOF2 路徑時間（兩層） | — | \|Δt\| ≤ 1 ps（約 0.3 mm 路徑長），只檢驗路徑長 |

- negative control：Geant4 端 B × (1 ± δ)，δ 由 trial run 選定，使偏差超過判定標準。
- 結果以 `field-propagation` benchmark（verification，B2.7 加入表）記錄；B1 中先以測試與 VALIDATION 條目記錄。B2 的 `field_propagation()` 重用 B1 的解析螺旋 oracle（同一份程式），不另寫。這項檢查也是 F4 資格路徑的條件 (ii)（B2.8）。

### B1.8 `geant4_run.py from-geometry` 與實現設定檔

**用途：** 讓 F4 研究的幾何來自候選設計。輸入是 main 的 `evaluate_design.py geometry` 寫出的 `design-geometry/1`（`studies/<id>.geometry.json`）與一份實現設定檔；輸出是 `element_sim.spec/1`。

```
python3 <plugin root>/adapters/geant4/assets/geant4_run.py from-geometry \
    --geometry studies/G.geometry.json --profile j15.realization.json --out studies/G.element_sim.json
```

- **確定性：** 同樣的兩個輸入產生逐位元相同的 spec（鍵排序、數值以 `float.hex` 往返檢查）；spec 的 `provenance` 記錄兩個輸入的 sha256、候選 id 與幾何檔的 `parameter_digest`。
- **實現設定檔 `element_sim.realization/1`**（schema 在 adapter，只用支援的關鍵字）：幾何種類（`layered-spectrometer`）、對照表版本、堆疊軸與場的方向、座標原點、每個角色的元件模板（材料、橫向大小、厚度由 x/X₀ 與材料的 X₀ 換算時用的材料）、場區範圍規則（第一與最後一個量測平面外延的距離）、對照表尚未涵蓋的子系統元件（TOF、量能器、被動材料的位置）、世界大小、physics 與 run 的預設。設定檔是一般設定，不帶候選的參數；同一份設定檔可用於整個設計專案或搜尋。
- **對照規則（對照表 1.0.0）：** `layer_positions_m` → `tracker-plane` 元件的中心（加原點）；`layer_x_over_x0` × X₀(材料) → 厚度；`passive_x_over_x0` → 依設定檔的位置放置一片被動材料（厚度同樣換算）；`point_resolution_um` 不進入模擬，寫入 reco spec（B2.1）；`field_T` → 場區的 B（方向依設定檔）。對照表 1.1.0（B2.6）的新欄位依同樣方式對應。
- **拒絕：** 幾何種類或對照表版本未知、設定檔缺少某個角色的模板、推導出的 spec 未通過 `check-spec`，都以 exit 2 拒絕並說明原因。
- F4 研究的 study spec 必須在 `input_manifest` 中列出幾何檔、實現設定檔與推導出的 spec（B2.6）。
- 測試：J15 的候選 `cand-N6` 經 `geometry` 與 `from-geometry` 得到的 spec，和 §B.4.1 手寫的 spec 逐元件相同（位置、厚度、材料、場）；改變候選的一個參數，只有對應的元件改變。

### B1.9 adapter 變更流程

| 項目 | 內容 |
|---|---|
| 版本 | 0.2.0 → 0.3.0 |
| `adapter.json` | `assets` 加入 `element_sim/`、`simroot/`、`element_sim.spec/1` 與 `element_sim.realization/1` 的 schema；更新 `purpose` |
| `SIM_SOURCES` | 目前是一個扁平的檔名 tuple，只在 `ASSETS/"layered_sim"` 下計算雜湊（`geant4_run.py` 行 63 定義，行 327、386 使用）。改為依程式分組的對照表 `{"layered_sim": [...], "element_sim": [...], "simroot": [...], "g4sim": [...]}`，每個 run record 記錄所用程式及 `g4sim` 的檔案雜湊；場的程式放在 `element_sim/Field.hh`、`Field.cc`；`layered_sim` 的雜湊鍵不變，舊紀錄仍可比對 |
| G5 | 聲明「依 Geant4 API 撰寫，未複製或改寫任何範例程式碼（含 B5）」，由審查者在 VALIDATION 條目中確認；同一條目註明 ROOT 檔類型與 `simroot` |
| 測試 | 離線測試（spec 驗證、跨欄位規則、`check-spec`、`from-geometry`）；live 測試（`HEP_GEANT4_LIVE_TEST=1`）：幾何、場、事件檔、`simroot` 往返；`tests/skills/test_cli_robustness.py` 對 `adapters/*/assets/*.py` 的掃描；`tools/check_wiring.py` |
| 文件 | `docs/capability-matrix.md` 的 Geant4 列；adapter 文件 |

### B1.10 B1 驗收

- [ ] `element_sim` 的 J15 幾何通過 overlap、物質預算與逐事件能量平衡；§B.4.1 與 §B.4.2 的核對數值由測試重算。
- [ ] `check-spec` 對每種跨欄位錯誤回傳 exit 2 與原因；合法的 spec 回傳 exit 0；`check-spec` 與 `from-geometry` 在擴充後的 `MISSING_FILE_ARGS` 中登記並通過缺檔測試。
- [ ] `from-geometry`：J15 候選推導出的 spec 和 §B.4.1 逐元件相同；同樣輸入逐位元相同；缺模板、版本未知時 exit 2（B1.8）。
- [ ] B1.6 的介面一致性與兩個後端的統計一致性（閘門 G-B1b）。
- [ ] `per-event` 下，同一邏輯 run 以 1、2、4 個工作與 1、2、4 個執行緒執行，summary 整數相同、浮點相對差 ≤ 1e-12。
- [ ] MT 測試指令回報的各執行緒 field manager 指標彼此不同；探針記錄的各區場參數和 spec 一致；場計入目標雜湊。
- [ ] B1.7 的確定性場檢查在名義值下通過（單區與兩區），各格點的結果都回報，negative control 被抓到（閘門 G-B1b）。
- [ ] 穿越：次級帶電徑跡的列存在且 `parent_id` 正確；主粒子的列和只記錄主粒子時相同。
- [ ] 量能器漏失：一個簡單配置（電子打在薄量能器上）中，`leak_*_MeV` 加上沉積與離開世界的能量滿足逐事件能量平衡。
- [ ] `simroot` 往返：各層級、I、D、S 欄的值相同；serial、不同執行緒數、1 個與 4 個工作的 `content_sha256` 相同（`processes` 去重後一致）；`deposits` 依事件加總等於 CSV 的子系統總沉積；`hits` 超過上限時 exit 2；run 中斷時 incomplete。
- [ ] VALIDATION GEANT4-ELEMENT；CHANGELOG；release manifest。

---

## §B.6 階段 B2：重建與 F4 介面（geant4 adapter 0.4.0、contracts CV-B2）

### B2.1 `simreco`（數位化與重建）

**位置：** `adapters/geant4/assets/simreco/`（CMake 專案；只用 C++17 標準函式庫與 `g4sim` 中不連結 Geant4 的 `SimHash.hh`、`SimSummary.hh`、`MiniJson.hh`；不連結 Geant4）。參數（ε、σ_t、每區名義 B、標定樣本、尾部來源的開關與參數）寫在 hep-detector 擁有的 reco spec 中；由 `from-geometry` 產生的研究，`point_resolution_um` 取自幾何檔。

**輸入：** `simroot dump` 從 ROOT 檔取出的 `crossings` 與 `deposits`（依鍵排序，經管線傳遞、不另存）以及摘要 CSV。

| 步驟 | 內容 |
|---|---|
| 矽 | 名義設定：主粒子的穿越點加高斯誤差，偏轉方向（y）ε = 10 µm，非偏轉方向（z）30 µm；擬合使用的 x 和 scorer 相同（入射面）。尾部來源開啟時改走 B2.2 的數位化與 hit 指派 |
| TOF | 每層的時間加獨立的高斯誤差 σ_t（100 ps；敏感度另做 150 ps）；站時間 = 兩層時間的平均（先以擬合軌跡把兩層的時間換算到站中心）；另外輸出每層的 dE/dx 與同站兩層的時間差 |
| 徑跡 | x–y 平面圓擬合，含多重散射共變異（否則 1 GV 時 χ²/dof 上千），得到曲率 κ；x–z 平面直線擬合，得到傾角 λ；以重建用的 B（每區名義值，B2.2 的誤校正開啟時乘上該 run 的尺度）計算 R_reco = C·B/(κ cos λ)（總動量，C = 0.2998 GV/(T·m)）；`curvature_offset_per_GV` 不為 0 時以 1/R_reco + offset 套用；輸出 R、χ²、自由度、電荷符號 |
| 剛度真值 | 1/R_true = 六片平面穿越紀錄的 \|q\|/p_i 的平均（**總動量** p_i；單位電荷時 1/R = 1/p）；R_true 與 R_reco 都用總動量，避免 p 與 p_T 之差（50 mrad 時約 0.125 %，大於 μ 場檢查的 0.05 % 容許） |
| β | 路徑長以兩站中心為端點，包含 TOF1→Si1、Si6→TOF2 的直線段與三維傾角；低 β 時回報 β 在兩站之間的變化 |
| 量能器 | 主動層總沉積除以**電子**取樣比例；取樣比例由 `calibration` 角色的 10 GeV 電子樣本求得；另外輸出 e/mip |
| 亂數 | 每個事件的數位化亂數流以 `SimHash.hh` 的 SplitMix64 產生，種子為 H(S, i, "digi")（A1.4 的 H；S 為邏輯 run 種子，i 為事件編號）；每個 run 的錯位與磁場尺度以 H(S, "align") 與 H(S, "fieldscale") 抽樣；常態亂數用 `SimHash.hh` 的 Box–Muller；不用 `std::normal_distribution`（libstdc++ 與 libc++ 的輸出不同）。和 Geant4 的亂數流分開。同一平台逐位元相同；跨平台時 `log`、`cos` 等 libm 函式的實作不同，不保證逐位元相同，只要求相對差 ≤ 1e-12；建置時加 `-ffp-contract=off` |

**輸出：** 逐事件結果 CSV（R、χ²、電荷符號、β、量能器能量等）與 run summary（`simulation-summary/1`，產生者 `simreco`；觀測量見 B2.3）。

- **擬合器的單元測試：** `tracker_resolution.py` 不做擬合，只由拋物線最小平方算出曲率解析度（`curvature_sigma`，行 89）。測試比較的是：在無多重散射的 toy（R ≥ 300 GV）上，C++ 擬合的 σ(1/R) 與 pull 寬度，和 `tracker_resolution.py momentum` 給的量測項解析度（`mdr_intrinsic_gev`）在 toy 的 MC 誤差內一致；pull 寬度在 1 ± 3σ_MC 內。

### B2.2 尾部來源（可切換的重建階段）

每個階段在 reco spec 中有開關與參數；`simreco` 把實際開啟的階段寫入 summary 的 `tail_sources_simulated`，名稱和 `contracts/design.py:64` 的 `TAIL_SOURCES` 一致。全部關閉時寫空陣列。

| 尾部來源 | 階段 | 參數（reco spec） | 說明 |
|---|---|---|---|
| `alignment` | 每個 run 為每個平面抽樣錯位（平移 y、z 與繞 x 的旋轉），再減去對準後的殘差模型 | 錯位的分布寬度；對準後殘差寬度；對準方法的描述 | 重建以「已對準」的位置擬合，真實位置含殘差；弱模式（例如整體的曲率偏移）另由 `curvature_offset_per_GV` 表示 |
| `calibration-non-uniformity` | 每個 run 為每個場區抽樣磁場尺度 (1 + δ_區)；重建用名義 B | δ 的分布寬度 | 分區均勻場（B1.2）是這個來源的最小模型 |
| `noise-digitization` | 條帶化（pitch）、電荷分享的簡化模型、門檻、效率、雜訊 hit、分群與重心 | pitch、門檻、效率、雜訊率、分群規則 | 取代名義設定的高斯點誤差；點解析度由此產生，而不是假設 |
| `pattern-recognition` | 以所有帶電徑跡的穿越（B1.3）與雜訊 hit 為輸入，逐平面做 hit 指派（最近鄰加 χ² 截斷），再擬合 | 搜尋窗、χ² 截斷、最少 hit 數 | 指派錯誤產生解析度與電荷誤判的尾部；指派失敗計入 tracking-selection-efficiency |

- 四種都開啟時，F4 的 `momentum-resolution-core` 與 `charge-confusion-rate` 是 `estimate`，否則是 `optimistic`（`contracts/design.py:1058-1059`）。B3.6 示範這個轉變。
- 這些模型是**合成的**最小模型，參數由使用者宣告並寫入 README；它們讓 bound 的申報誠實，不代表任何實驗的實際尾部。電荷誤判的合規仍需資料驗證與剛度尺度偏移（適足表），F4 本身永遠不足以合規。

### B2.3 F4 用的觀測量

在 `simulation-observables/1` 中宣告（A1.5），由 `simreco` 的 summary 累加：

| figure of merit | 估計量 | 分母 | 不確定度 |
|---|---|---|---|
| `momentum-resolution-core` | 高斯核心寬度：(1/R_reco − 1/R_true)·R_true 的迭代 ±2σ 截斷擬合（定義與截斷參數寫入研究區塊，`estimator` 欄） | `rigidity_GV`、`species` | 區塊批次平均的 68.27 % t 半寬（A1） |
| `charge-confusion-rate` | 計數：重建電荷符號和真值相反的事件比例（`count_if` 與總數） | `rigidity_GV`、`species`、`charge_sign`、`curvature_offset_per_GV` | 精確（Clopper–Pearson）區間，不對稱（B2.6） |
| `shower-containment` | 1 −（漏失總能量 / 入射能量）的平均；也報後漏比例 | `energy_GeV`、`species` | 區塊批次平均的 t 半寬 |
| `tracking-selection-efficiency`（選用） | 計數：通過 hit 指派與擬合品質的主粒子比例 | `rigidity_GV`、`species` | 精確區間 |

- 核心估計和舊文件的「中央 68 % 半寬」不同；兩者都輸出，只有核心估計作為 `results.momentum-resolution-core.value`。

### B2.4 `geant4_run.py reco` 與 `table`

- `reco`：執行 `simroot dump` 與 `simreco`；每次執行寫一份 computational-run 紀錄（含 `**trace.provenance()`、`argv`、`script_sha256`、`simreco` 的程式雜湊、輸入 run record 的雜湊與 ROOT 檔的 `content_sha256`、dump 的 ntuple 與欄位清單、reco spec 的雜湊）。改變數位化參數或尾部來源開關不需要重跑模擬。
- `table`：把重建的結果（例如剛度解析度對剛度）寫成 simulated dataset-record（含 `trace.provenance()`）；`table --f4-results` 另寫一份 F4 結果檔（B2.6）。
- 退出碼依 `core/status.py`：0 ok、1 負向判定、2 `rejected`（無法讀取的輸入，含缺檔）、3 incomplete。
- **CLI 登記：** 在 B1 擴充後的 `MISSING_FILE_ARGS`（B1.6）中加入 `reco`、`table`。

### B2.5 遞移的處理鏈

- 目前 `dependencies.py` 要求 simulated 表格的每個輸入都是帶 `extension.simulation` 或 `extension.study` 的 computational-run；重建紀錄兩者都沒有。CV-B2 改為：輸入鏈可以任意深，只要每一層都是有紀錄的 computational-run，而且鏈的每個根都是模擬 run（需 hep-computing 同意；§P.7）。`dependencies.py` 對參數綁定（`binding: parameters`）只警告的既有行為不變。
- 研究是 `unvalidated` 時，表格保持 `unvalidated`；使用它的 communication 會得到 `communication.simulated_source` 警告，圖表標示「Simulation」。

### B2.6 F4 介面（CV-B2）

**F4 結果檔 `f4-results/1`**（`geant4_run.py table --f4-results` 寫出）：每個 figure of merit 一項 `{value, statistical_uncertainty | uncertainty, model_envelope, estimator, denominator}`，另有 `tail_sources_simulated`、幾何檔的路徑與 sha256。`model_envelope` = 變化表（`check_geant4_study.py variations`）中各 physics list 結果的 [lo, hi]，兩端各自的標準誤保留在註記中（`design.py` 逐端比較，行 1310–1316）。

**`check_geant4_study.py label` 的擴充：** 新旗標 `--results <f4-results>` 與 `--geometry <design-geometry>`。`label --write`（含 `--upgrade`）把結果寫入 `extension.study.results.<fom>` 與 `extension.study.tail_sources_simulated`，並把結果檔、幾何檔、實現設定檔與推導出的 spec 加入 `input_manifest`（目前 `label` 從頭重建紀錄，這些欄位都會遺失：`check_geant4_study.py:584-617`）。結果檔的幾何 sha256 和 `--geometry` 不一致時 exit 2。

**`contracts/design.py` 與 `evaluate_design.py` 的變更（需維護者同意，§P.7）：**

| 變更 | 理由 |
|---|---|
| 計數型 figure of merit 的 F4 接受不對稱或精確區間（`uncertainty` 物件，不只純量 `statistical_uncertainty`） | 電荷誤判是計數型（適足表 `counting: true`）；目前 F4 一律寫對稱高斯（`evaluate_design.py:546-548`；`design.py:1050-1054`） |
| F4 evaluation 自己記錄 `geometry_ref`，`check_f4` 讀 evaluation 的幾何檔；候選的 `geometry_ref` 保留為最近一次 | 每個候選只有一個 `geometry_ref`，而每個幾何檔只對應一個 figure of merit 與分母；第二次 `geometry` 會讓先前的 F4 evaluation 因 `input_manifest` 不符而失效（`design.py:1013-1028`） |
| `check_f4` 比對幾何檔的分母和 evaluation 的分母 | 目前只比對 figure of merit（`design.py:1041-1042`） |

維護者不同意第二項時，B3 每個候選同時只保留一個有效的 F4 evaluation，並在 README 說明。

**幾何對照表 1.1.0（CV-B2）：** `contracts/rules/design_geometry.json` 的 `mapping_version` 升為 1.1.0，`contracts/schemas/design_geometry.json` 的 enum 加入 1.1.0；新增欄位：徑跡層的材料與橫向面積、場區沿堆疊軸的範圍、`tof` 角色（層的位置、厚度、時間解析度）、`calorimetry-em` 角色（前表面位置、深度 X₀、取樣結構）。對照表 1.0.0 的候選照常可用（缺的欄位由實現設定檔補）。

**`f4` 接受一份研究所需的條件（檢查清單）：**

- [ ] 幾何來自 `evaluate_design.py geometry --figure-of-merit F --denominator … --id G`，`element_sim.spec/1` 由 `studies/G.geometry.json` 經 `from-geometry` 推導。
- [ ] 研究紀錄的 `extension.input_manifest` 列出幾何檔（sha256 相符）、實現設定檔與推導出的 spec（`design.py:1025-1028`）。
- [ ] 幾何檔的 `parameter_digest` 等於候選目前的摘要（`design.py:1029-1039`）。
- [ ] 幾何檔的 figure of merit 等於被評估的 figure of merit（`design.py:1041-1042`）；每個分母點一份研究。
- [ ] `extension.study.results.<fom>` 有 `value`、`statistical_uncertainty`（68.27 % t 半寬）或不對稱 `uncertainty`（計數型）、`model_envelope` [lo, hi]（`design.py:1044-1057`）。
- [ ] `extension.study.tail_sources_simulated` 是四種來源的子集；四種都有才是 `estimate`。
- [ ] 紀錄經 `label --upgrade` 重新發出為 `validated-in-scope`（B2.8 的資格路徑），而且重新發出的紀錄保留上述欄位與 manifest。
- [ ] 分母：解析度 {`rigidity_GV`, `species`}；電荷誤判 {`rigidity_GV`, `species`, `charge_sign`, `curvature_offset_per_GV`}；簇射 {`energy_GeV`, `species`}。
- [ ] 電荷誤判的合規另需上游 `charge-confusion-data-validation` 與 `rigidity-scale-offset` 的 evaluation（適足表）；F4 本身不會使它合規。

### B2.7 驗證類別、表條目與 `change`

**新增的 benchmark 表條目**（A1.1 的格式；等級即類別；`GRADES`（`geant4_benchmarks.py` 行 92）與 study spec 的 benchmark、grade enum 同步加入；計算函式放在 `geant4_benchmarks.py`，只讀 summary 或 `simroot dump`）：

| benchmark | 類別 | 支持的 kind | 範圍維度 | 計算位置 |
|---|---|---|---|---|
| `field-propagation` | verification | — | 場的配置（區數、B 範圍） | `field_propagation()`，讀 `simroot dump` 的 `crossings` 與解析螺旋（B1.7） |
| `field-propagation-muon` | sanity | — | — | `field_propagation_muon()`，讀 `simreco` 的 summary |
| `reco-closure` | verification | — | 剛度、粒子 | `reco_closure()`：尾部來源全部關閉、無多重散射的 toy 輸入下，`simreco` 的 pull 寬度與偏差對真值（擬合器的整合測試，B2.1） |
| `tof-beta` | verification | — | — | `tof_beta()`，讀 `simreco` 的 summary |
| `tof-layer-consistency` | verification | — | — | `tof_layer_consistency()`，讀 `simreco` 的 summary |
| `sampling-fraction` | sanity | — | — | `sampling_fraction()`，讀 `element_sim` 的 summary |
| `multiple-scattering-reference` | **reference** | `tracking-resolution`、`charge-confusion` | 材料、厚度（X₀）、剛度、粒子 | `ms_reference()`：孤立 Si 平板中投影出射角的核心寬度（沿用既有 `multiple-scattering` sanity benchmark 的中央 98 % 估計量，`geant4_benchmarks.py` 檔頭說明）對照 Lynch–Dahl（F = 98 %）公式；容許值依該公式的文獻精度（經 hep-citations 取得並核對）；精度不足以作為 reference 時，改以已發表的多重散射量測（例如 MuScat）作為 `published-data` |
| `regression-comparison` | regression | — | — | `regression_comparison()`，讀兩個版本的 summary |

- **verification：** 不單獨計入升級；`field-propagation` 與 `reco-closure` 是 B2.8 資格路徑的條件。
- **`multiple-scattering-reference`：** negative control 為平板密度或厚度 × (1 ± δ)，δ 由 trial run 選定；關閉多重散射屬「粗控制」，依 protocol 不算。既有的 `multiple-scattering`（sanity，對 Highland）維持不變。
- **regression：** 角色 enum 加入 `regression`。同一研究、同一設定，在新舊兩個版本（plugin、後端或 Geant4）各執行一次；兩次的 point_id 為版本標籤，所以 S 不同、樣本獨立（不違反 A1.4 的唯一性）。只比較純量觀測量（直方圖的比較屬於 §B.9 延後的分布層級 benchmark）。兩個版本都必須是 A1 以後的 run（都帶 S 與 summary）。判定由判定引擎新增的 `change(diff, se, ν, tol, m)` 執行：`changed` = |diff| − t_{1−α/m}·se_diff > tol；`unchanged` = `equivalence` 的通過；其他為 `unresolved`。計數型觀測量和 `equivalence` 一樣走精確區間的分支（A1.7）。容許值與 α 事先宣告。紀錄不影響 label；reference 觀測量 `changed` 時可觸發 sci-fix 檢查。
- 閘控：`strict or _at_least(contract_version, CV-B2)`，無 warning 分支。

### B2.8 F4 資格路徑（D0）

**問題：** 依 protocol，升級需要一個通過的 reference benchmark，其範圍涵蓋研究的範圍；偵測器層級的觀測量（解析度、電荷誤判）在 A1 的表中沒有任何 reference，所以這類研究永遠不能 `validated-in-scope`，也就永遠不算 F4。

**資格規則**（`contracts/validate.py` 的 `geant4.upgrade_*` 規則與 `check_geant4_study.py` 的資格判定，CV-B2；kind 為 `tracking-resolution` 或 `charge-confusion` 的研究）：可升級若且唯若下列都成立。

1. **材料：** 研究中所有有物質的元件的材料，都在已通過的 A1 材料 benchmark（stopping-power、thin-layer-mpv 等）的範圍內，或在 `multiple-scattering-reference` 的材料範圍內。
2. **場：** 同一場配置（區數與 B 範圍）的 `field-propagation` verification 已通過。
3. **重建：** 同一 reco spec（尾部來源關閉時）的 `reco-closure` verification 已通過。
4. **徑跡 reference：** `multiple-scattering-reference` 已通過且 negative control 被抓到，其範圍（材料、厚度、剛度、粒子）涵蓋研究宣告的範圍。
5. A1 的其他條件（收斂閘門、無殘留缺口、`reference_origin: independent`、變化表）照常適用。

- `shower-containment` 與其他量能器 figure of merit 不在這條路徑內：唯一的參考是 PDG gamma 剖面擬合（sanity，`geant4_benchmarks.py` 檔頭明言不能作為驗證），需要已發表的漏失資料作為 `published-data` reference（§B.9）。J15 的簇射包含 F4 研究因此停在未升級（`f4_unqualified`），README 說明。
- 規則、條件與範圍維度寫入 `geant4-study-protocol.md` 與 `system-design-workflow.md` 的 F4 列。
- **D0 未核准時：** B2 的其餘部分可合併；本節的規則（`validate.py` 與 `check_geant4_study.py` 的資格判定）留在分支，不合併（§P.6、§P.7）。

### B2.9 adapter 變更流程與 CI

| 項目 | 內容 |
|---|---|
| 版本 | 0.3.0 → 0.4.0 |
| `adapter.json` | `assets` 加入 `simreco/`、reco spec 與 `f4-results/1` 的 schema；更新 `purpose` |
| `SIM_SOURCES` | 加入 `simreco` 分組 |
| CI | C++17 CI 工作建置與測試 `simreco`（必要或選用由維護者決定，§P.7）；建議在 `contracts/rules/registry.json` 新增 `adapters/geant4/**` 的影響群組 |
| 文件 | adapter 文件、`geant4-study-protocol.md`（驗證類別、資格路徑、處理鏈、`reco`、`table`、F4 結果檔）、`system-design-workflow.md` 的 F4 列（`from-geometry`、尾部來源、資格） |

### B2.10 B2 驗收

- [ ] `simreco` 的擬合器單元測試依 B2.1 通過；`simreco` 在 CI 工作中建置與測試（必要工作；或維護者決定為選用時，選用工作加一份本機建置與測試紀錄）。
- [ ] `simreco` 的數位化結果在同一平台上逐位元相同；Linux（libstdc++）與 macOS（libc++）之間相對差 ≤ 1e-12（以 `-ffp-contract=off` 建置）。
- [ ] 尾部來源：每個階段單獨開啟時，解析度或電荷誤判朝預期方向改變；`tail_sources_simulated` 只列開啟的階段，全關時為空陣列；`curvature_offset_per_GV` 對電荷誤判的影響和解析式一致（高斯核心時）。
- [ ] `simreco` 的 summary 通過與 A2.9 相同的一致性測試（Python 由逐事件結果 CSV 重算）；B2.3 的估計量有單元測試（核心擬合、精確區間）。
- [ ] `reco`、`table` 在 `MISSING_FILE_ARGS` 中登記並通過缺檔測試。
- [ ] 三層以上的處理鏈（模擬 → 重建 → 表格）被 `dependencies.py` 接受；根不是模擬 run 時被拒。
- [ ] 新的表條目與 `GRADES`、study spec 的 enum 一致（一致性測試）；verification 類別不單獨計入升級。
- [ ] `change` 的 toy：真實差值 = tol 時判 changed 的機率 ≤ α/m + 3σ_MC；回報真實差值 = 2·tol 時判 changed 的機率（檢定力）與真實差值 = 0 時判 unchanged 的機率；一個回歸檢查（例如 J14 在兩個 plugin 版本上）產生 `changed`、`unchanged` 或 `unresolved` 的紀錄且不影響 label。
- [ ] `label --results --geometry`：重新發出的紀錄保留 `results`、尾部來源與 manifest；幾何 sha256 不符時 exit 2。
- [ ] 對照表 1.1.0：schema、`design.py` 的欄位讀取與 `from-geometry` 一致；1.0.0 的候選仍可用（main 的兩個範例不變）。
- [ ] **端到端測試**（閘門 G-B2）：小型磁譜儀候選 → `evaluate_design.py geometry` → `from-geometry` → `element_sim` → `reco` → `table --f4-results` → `label --upgrade --results --geometry`（經 A1 的 `--label-run-record`）→ `evaluate_design.py f4` → `report`；資格條件未滿足時被拒絕並列出原因；滿足時（D0 核准後）得到 F4 evaluation，bound 依尾部來源為 `optimistic` 或 `estimate`。
- [ ] 計數型 F4 的不對稱不確定度與 evaluation 自帶的 `geometry_ref`（若維護者同意）有 `contracts/design.py` 的測試；main 的 `tests/contracts/test_design_*.py` 與 `tests/skills/hep_detector/test_design_m2.py` 仍通過。
- [ ] J14 在 `--strict` 下仍通過；`tools/check_wiring.py`、`tools/scifix_ledger.py report` 通過。
- [ ] VALIDATION GEANT4-F4；CHANGELOG；release manifest。

---

## §B.7 階段 B3：J15 設計專案

### B3.1 J15 的 design-spec、候選與 F1、F2

- 依 §B.4.4 在 `examples/design-minimal-spectrometer/` 寫出 design-spec `j15-v1`、候選 `cand-N6`、`cand-N4`、`cand-N8` 與實現設定檔；格式同 main 的 `examples/design-space-spectrometer/`。
- 人工閘門 H1、H2 由 agent 準備決策紀錄、標明需人簽署（README 註明範例中為示範）。
- F1：`evaluate_design.py run` 對每個候選與需求（`tracker_resolution`、`multiple_scattering`、`charge_confusion_rate`）；`budget` 對質量與通道數。
- F2：`toy_spectrometer` 的解析度與 `design_estimates.py infield-acceptance` 的接受度。這取代舊文件的「多重散射一次性比較」：F1 與 F2 的數值與 §B.4.2 的手算表互相核對（測試）。
- `evaluate_design.py plan` 列出缺少的證據；`report` 推導合規矩陣、篩選與比較基準。

### B3.2 驗證梯（另一份 `unvalidated` 紀錄）

驗證梯是 J15 的 verification 載體，寫在一份**獨立的** study record 中（不是 F4 研究），永遠 `unvalidated`；其中的 verification 結果同時是 B2.8 資格條件的證據來源。

| 檢查 | 類別 | 參考 | 規格 | negative control |
|---|---|---|---|---|
| overlap | 實作 | — | — | 平移一片 Si 造成重疊 |
| 逐事件能量平衡（J15 幾何） | 實作 | 能量守恆 | — | 不加 2 mₑc²、重複計入 |
| 物質預算（geantino） | 實作 | PDG X₀ 加總 | 容許約 2 %（Geant4 的 X₀ 公式和 PDG 約差 1 %） | Pb 密度 ± δ |
| `field-propagation` | **verification** | charged geantino 對解析螺旋 | B1.7 | Geant4 端 B × (1 ± δ) |
| `field-propagation-muon` | **sanity** | 平面平均的 1/R 真值（B2.1） | μ⁻ 1、10、100 GV；觀測量 (1/R_reco − 1/R_true)·R_true 的平均；以 `equivalence`（A1.8）判定，`tolerance_mode: absolute`，容許 0.05 %（觀測量本身已是相對量）；SE 目標 0.1 %，N 依 A1.9 由 trial run 決定（估計：1 GV 約 400、100 GV 約 7400，對應 SE 約 0.07 % 與 0.10 %） | Geant4 端 B × (1 ± 1 %) |
| `reco-closure` | **verification** | 真值 | B2.7 | 重建用的 B × (1 ± δ) |
| `tof-beta` | **verification**（bookkeeping） | 沿真實軌跡的運動學 | — | scorer 測試旗標注入時間偏移；沒有 Geant4 端的物理控制組，文件中註明 |
| `tof-layer-consistency` | **verification**（bookkeeping） | 同站兩層的時間差對「層間路徑長 / βc」（β = 1、正入射時 66.7 ps） | 殘差平均為 0；寬度 √2 σ_t（100 ps 時 141 ps） | 以測試旗標在一層的 scorer 時間注入偏移 |
| `sampling-fraction` | sanity | PDG 的 μ 能損表（Groom 等，經 hep-citations 取得）在 run 動量下的游離 dE/dx 比 | μ⁻ 1 GeV；統計量為 Σ PVT 沉積 / Σ（PVT + Pb）沉積；合理範圍 ±10 %（審查者的 Bethe 估計約 0.271）；和 `calibration` 樣本用不同種子 | PVT 密度 ± δ |
| 簇射包容 | sanity | PDG gamma 剖面，混合物有效臨界能約 10.2 MeV | 電子 1–100 GeV；`leak_*_MeV`（B1.3） | — |
| `longitudinal-profile`（0.21.0） | 不適用 | 它的參考是已發表的 ALICE FoCal-E 量測，只對該堆疊有效；J15 的量能器不同，而且是 embedded | — | — |

`multiple-scattering-reference`（B2.7）在孤立的 Si 平板中執行（`element_sim` 的單一元件），另立一份 study record，依 A1.3 的隔離規則判定；它是 B2.8 資格條件 4 的證據。舊文件選用的孤立 PVT stopping-power benchmark 仍可選用執行，同樣另立紀錄。事件數與判定依 A1.6–A1.10。

### B3.3 量能器 production cut 收斂

- 格點：0.1、0.3、0.7、1.0 mm。
- 樣本：10 GeV e⁻；先跑 trial，再依 A1.9 決定 N。
- 觀測量：總沉積（相對容許 1 %，約 400 個簇射/點）、後漏比例（`leak_rear_MeV` 除以入射動能，只算量能器母體的後表面；**絕對**容許 0.002，`tolerance_mode: absolute`，約 5000 個簇射/點）。這兩個數不含兩階段因子 f ≈ 1.97（A1.9）；含 f 時約 770 與 9,900 個簇射/點。
- 每點事件數取兩者的較大值；判定依 A1.8（`equivalence`）；每個宣告的格點都必須有 summary（A1 的 D11）。
- Si 的 production cut 收斂只對 F4 徑跡研究做（B3.6），觀測量為核心解析度；驗證梯中的 Si 結果不作為證據。study spec 的 `convergence_plan.observables` 加入總沉積與後漏比例。各 benchmark 依賴的參數組事先宣告，並以探針的實際設定核對。

### B3.4 variation 與模型包絡

| variation | 範圍 | 規則 |
|---|---|---|
| EM option4 對 option3 | 量能器剖面、取樣比例 | `G4R-PRECISION-EM` |
| EM 多重散射模型：option0 對 option4（Urban 對 WentzelVI） | F4 徑跡研究的核心解析度與電荷誤判 | 結果轉為 `model_envelope`（B2.6） |
| FTFP_BERT_EMZ 對 **QGSP_BIC_EMZ** | 1.5 GeV 以下核子；觀測量為末態量：第一次作用後 5 層的沉積、作用後的帶電次級粒子能量。作用機率與第一次作用深度只在探針確認兩者的非彈性截面不同時才回報（兩個 physics list 可能共用核子截面，那時差值必為 0；這和 protocol §6 Variations（行 161 起，假零的警告在行 166–168）是同類問題） | `G4R-BIC-RANGE`；12 GeV 以下 π 與 1.5–12 GeV 核子兩者模型相同（protocol 行 166–168），不得作為 variation |
| 真空對空氣 | 多重散射、剛度解析度 | — |

- 每個 variation 的差值附標準誤；小於約 2 SE 的差值視為未解析（protocol §6）。包絡交給 hep-statistics 作為包絡，不當作 σ。

### B3.5 TOF 時間解析度的敏感度

- `simreco` 以 σ_t = 100 ps 與 150 ps 各重建一次（同一份模擬，不需重跑）。
- 回報兩者的 σβ/β（預期約 2.3 % 與 3.5 %）與 β 解析度對剛度的影響；README 說明 100 ps 比 AMS-02 的系統解析度（約 140 ps）樂觀。

### B3.6 F4 研究與尾部來源的示範

- **研究的切分：** 每個（候選、figure of merit、分母）一份研究：`cand-N6` 的 `momentum-resolution-core`（質子 1 GV、100 GV）、`charge-confusion-rate`（質子，需求宣告的偏移）、`shower-containment`（電子 10 GeV）；`cand-N4`、`cand-N8` 只做 1 GV 與 100 GV 的解析度。每份研究：`geometry` → `from-geometry` → `element_sim` → `reco` → `table --f4-results` → `label --upgrade`（資格路徑）→ `f4`。
- **尾部來源的示範：** 同一份模擬以尾部來源全關與全開各重建一次，兩份研究紀錄；`f4` 的 bound 分別為 `optimistic` 與 `estimate`；README 以表格說明解析度與電荷誤判的改變。
- **合規鏈：** 解析度的合規保真度是 F3：以 F4 核心 evaluation 為上游執行 `evaluate_design.py response`；電荷誤判停在 `chain.incomplete`，缺 `charge-confusion-data-validation` 與 `rigidity-scale-offset`（範例中誠實列出，不偽造資料）；簇射包含停在未升級的 F4（B2.8）。
- **比較：** `report` 推導篩選、比較基準與排序；沒有 expected-precision 的 evaluation 時，排序與 Pareto 被拒絕並列出原因。
- 收斂（Si 的 production cut，B3.3）與 variation（B3.4）依 A1 的規則；事件數依 A1.9 由 trial run 決定。

### B3.7 recorded 資料預算

- `check_packaging.py` 的單檔上限 2 MiB（`MAX_BYTES = 2 * 1024 * 1024`，單位 bytes）；J14 的 `recorded/` 總和為 2,447,979 bytes（約 2.45 MB；`du -h` 顯示的 2.6 MB 含檔案系統區塊）。
- ROOT 檔不提交；run record 只記錄路徑、檔案 sha256、`content_sha256`、各 ntuple 列數與大小；測試需要的 ROOT 檔在 live 測試中產生。
- J15 只提交：design-spec、候選、實現設定檔、幾何檔、evaluation、研究紀錄、報告；run summary（模擬與重建）、effective config（依內容雜湊存放）、column map、縮減欄位的摘要 CSV、以 `simroot dump --events` 取出的縮減穿越與沉積紀錄（供離線重播 `simreco` 的測試；事件子集依預算決定）、重建的結果表與 F4 結果檔。
- 每檔 ≤ 2 MiB，J15 的 `recorded/` 總和 ≤ 3 MB。

### B3.8 註冊、journey 與文件

| 項目 | 內容 |
|---|---|
| 腳本計數 | hep-detector 不新增腳本；計數測試（`tests/skills/test_documented_output_claims.py` 行 145 的 `DetectorScriptCount`）維持 23，`docs/capability-matrix.md` 行 49 的「twenty-three scripts」不變 |
| 路由表 | 不修改 `skills/hep-detector/SKILL.md`；`element_sim`、`simreco`、F4 路徑的說明放在 `geant4-study-protocol.md`、`system-design-workflow.md` 與 adapter 文件（設計流程的入口已由 hub 連結，main 的 OQ-01） |
| journey | J15（「把一個磁譜儀設計從 F1 走到 F4」）；`docs/researcher-journeys.md`、`docs/maintenance.md` 範例表；`tests/examples/test_design_minimal_spectrometer.py`（重播並比對 `report` 的推導結果） |
| capability | `docs/capability-map.json` 與 `docs/capability-map.md`（在 `full-detector-simulation` 與 `detector-design` 下新增項目，執行 `capability_map.py --write`）、`docs/capability-matrix.md` |
| 路由 | 新增 J15 的路由案例；`check_routing_static.py` 從 `docs/researcher-journeys.md` 讀取 journey 清單，所以 J15 一列入表就**必須**有路由案例。重跑 live 的 Geant4 案例，包括既有的繁中欠規格案例 `g4-underspec-2` |
| 描述長度 | description 1,016 / 1,024 字元；路由案例沿用已有的觸發詞，不改描述 |
| README | J15 的簡化清單（§B.4.1）、尾部來源模型的合成性質（B2.2）、和 PAMELA 與 AMS-02 的對照（§B.4.3）、「合成幾何」的定位、哪些證據仍缺（B3.6） |
| 獨立審查 | 本任務的 Markdown（protocol 變更、J15 README、設計報告、本部）依 main 的 `docs/dev/independent-review-spec.md` 以 `review.py` 審查；紀錄只是 advisory，依 O04/O14 不取代人工的 G5 確認 |
| 其他 | `reference_inventory.py --check`、`tools/check_wiring.py`、CHANGELOG、release manifest |

### B3.9 B3 驗收

- [ ] J15 的 design-spec 與候選通過 `contracts/design.py`（無 `design.*` 錯誤）；F1、F2 的 evaluation 由 `evaluate_design.py` 寫出，數值和 §B.4.2 的手算表一致（測試）。
- [ ] 驗證梯（B3.2）執行完成並寫成獨立的 `unvalidated` 紀錄；各自的 negative control 被抓到，或註明沒有控制組。`multiple-scattering-reference` 的紀錄另外列出。
- [ ] 量能器 cut 收斂（B3.3）與 variation（B3.4）完成，判定與 incomplete 的比例記錄於 study record；徑跡研究的模型包絡寫入結果檔。
- [ ] TOF σ_t 的 100 與 150 ps 敏感度已回報。
- [ ] F4 研究（B3.6）：D0 核准後，解析度研究經資格路徑升級並由 `f4` 接受；尾部來源全關與全開分別得到 `optimistic` 與 `estimate`；電荷誤判停在 `chain.incomplete` 並列出缺少的上游；簇射包含停在未升級並說明原因；`report` 的推導結果與 README 一致。D0 未核准時，`f4` 的拒絕原因記錄在 README，這一項以「拒絕正確」驗收。
- [ ] recorded 預算、註冊項目、文件全部完成；J15 的離線重播測試通過。
- [ ] 獨立 agent 只依文件與工具完成「1 GV 質子在 J15 的剛度解析度」：經 `evaluate_design.py` 產生 F1 evaluation 與 F4 研究，研究紀錄通過 `validate.py --strict`；核心解析度落在 §B.4.2 多重散射表 1 GV 質子一列的範圍內（1.8–2.6 %，量測項在 1 GV 可忽略；核心估計可略低於中央 68 % 半寬，兩者都回報）；過程不需要維護者協助。
- [ ] VALIDATION GEANT4-J15；CHANGELOG；release manifest。

---

## §B.8 契約與版本

| 物件 | 位置 | 版本 |
|---|---|---|
| `element_sim`、`element_sim.spec/1`、`element_sim.realization/1`、`element_sim.events/1`、`simroot`、`check-spec`、`from-geometry` | geant4 adapter | 0.3.0（B1） |
| `simreco`、reco spec、尾部來源、`reco`、`table`、`f4-results/1` | geant4 adapter（C++，不連結 Geant4） | 0.4.0（B2） |
| verification、regression、徑跡 reference 類別與表條目；regression 角色；遞移的處理鏈；F4 資格規則 | `contracts/validate.py`、`contracts/dependencies.py` | CV-B2（minor、閘控；資格規則待 D0） |
| 計數型 F4 的不確定度、evaluation 自帶的幾何檔、分母比對；幾何對照表 1.1.0 | `contracts/design.py`、`contracts/rules/design_geometry.json`、`contracts/schemas/design_geometry.json` | CV-B2（minor；需維護者同意） |
| `label --results --geometry` | `skills/hep-detector/scripts/check_geant4_study.py` | 隨 plugin 版本 |
| 判定引擎 `change` | `core/stats/decisions.py` | `CORE_VERSION` minor |
| `GRADES` 與 study spec 的 enum；`convergence_plan.observables` 加入總沉積與後漏比例 | hep-detector | 隨 plugin 版本 |

---

## §B.9 不做與延後

| 項目 | 決定 | 理由 / 觸發條件 |
|---|---|---|
| 量測主導區 σ(1/R) 作為 benchmark | 不做 | 改為擬合器單元測試與 `reco-closure` |
| `skills/hep-detector/scripts/digitize_reconstruct.py` | 不做 | 改為 C++ 的 `simreco` |
| surrogate 類別與 `surrogate-comparison` | 不做 | main 的保真度與 bound 模型已涵蓋近似評估；任務 C 的搜尋值不是 evaluation（§C） |
| `layered_sim` 的新幾何功能 | 不做 | 新功能只加在 `element_sim` |
| 管線中以 Python 直接讀 ROOT（uproot） | 不做 | 經 `simroot` |
| 量能器 figure of merit 的 F4 資格 | 延後 | 需要已發表的漏失或剖面資料作為 `published-data` reference；觸發：第一個需要量能器 F4 合規的設計 |
| 離子源與 Birks 可見能量 | 延後 | 宇宙線核素研究，且 PVT 的 Birks 常數有文獻紀錄。實作時依 11.4.3：在 `GeneratePrimaries` 中以 `GetIon(Z, A)` 取得離子；在 `Construct` 設定 kB（`GetIonisation()->SetBirksConstant`）、PreInit 呼叫 `G4EmParameters::Instance()->SetBirks(true)`，再以 `G4LossTableManager::Instance()->EmSaturation()` 取得（API 名稱實作時以 11.4.3 原始碼核對） |
| `element_sim` 的非盒狀 solid、旋轉、GDML 讀入、field map、邊緣場 | 延後 | 第一個需要它們、又不能用使用者應用的研究；擴充點是「幾何種類 → 實現程式」（第 5 部），新的幾何種類加一個對照表與一個 realizer |
| `element_sim` 的主粒子出射紀錄（J14 的觀測量） | 延後 | 把 J14 遷移到 `element_sim` 並退役 `layered_sim` 時（§P.8） |
| 分布層級的 benchmark（含 regression 的直方圖比較）、觀測量的組合、profile、`gps` 與 `event-file` 粒子源、`simreduce` | 延後（介面已定義於 §R.9.2） | 各自的第一個用例 |
| RNTuple、vector 欄 | 延後 | ROOT 檔大小或讀取速度成為瓶頸 |
| 真實的對準演算法、Kalman 濾波、完整的 pattern recognition | 延後 | B2.2 的最小模型足以讓 bound 誠實；第一個需要真實尾部形狀的研究 |

其他不做與延後的項目見 §A.9。

---

## §B.10 待決事項與殘餘風險

**待決事項**（編號見 §P.7）：D0（F4 資格路徑）；G5 的確認方式；遞移的處理鏈與 CV-B2 的歸類；`simreco` 的 CI 工作；ROOT 檔的存放；`element_sim` 的維護歸屬；`contracts/design.py` 的三項 F4 變更（B2.6）。

**殘餘風險：**
1. 取樣比例的參考需要 PDG 的 μ 能損表；`multiple-scattering-reference` 需要 Lynch–Dahl 公式的文獻精度；選用的 PVT benchmark 需要 Sternheimer 參數。都要經 hep-citations 取得文獻紀錄後才能使用；Lynch–Dahl 的精度不足時改用已發表的量測（B2.7）。
2. 量能器簇射主導 CPU 時間；後漏的收斂每點約需 5000 個簇射（含兩階段因子約 9,900），事件數由 trial run 決定並記錄。
3. `G4RootAnalysisReader` 的讀取能力未驗證（閘門 G-B1a）。
4. 大樣本的 ROOT 檔可達數百 MB；記錄所有帶電徑跡的穿越使大小約加倍；MT 合併時 worker 的資料可能在記憶體中累積到 run 結束（實際行為依 11.4.3 的 ntuple merging 與 basket 設定，未核對）；`hits` 有事件數上限，大小與記憶體在 trial run 中確認。
5. 兩個 Geant4 程式的維護成本；靠 `g4sim` 控制重複（§P.8）。
6. 強子 variation：若兩個 physics list 的核子非彈性截面相同，作用機率不會改變；只回報末態量（B3.4）。
7. 部分 Geant4 行為（stepper 的建立、Birks 的 API、交點誤差的方向）依審查者的經驗判斷，未逐行核對 11.4.3 原始碼；實作時先核對。
8. 工作量在 B1 開始時依實際的 `g4sim` 估計。
9. 任務 A 的殘餘風險（區塊獨立的前提、接近門檻的判定、探針假設 worker 與 master 設定相同）同樣適用，見 §A.10。
10. **D0 不核准**：偵測器層級的研究不能成為 F4，B3 只能示範被拒絕的路徑；`element_sim` 與 `simreco` 仍可作為 F4 以下的模擬工具，但 main 的適足表中 F4 才能篩選或合規的 figure of merit 仍是 `capability.unavailable`。
11. **main 的設計流程變動快**（3.5.0 到 3.12.0 約兩天）：`contracts/design.py`、`evaluate_design.py`、`design_geometry.json` 是共用檔，B2 開始與合併前都要 rebase 並重跑 main 的設計測試。
12. 尾部來源的最小模型可能被誤讀為實驗的實際尾部；README 與報告都標明合成。

---

## §B.11 建議的執行步驟

每個階段開始時依 §P.10.2 建立並確認該階段的 isolated worktree，所有步驟都在其中進行；合併後依 §P.10.5 移除。

**B1**
1. 開始前檢查（§B.0）；`G4RootAnalysisReader` 的一天試作（閘門 G-B1a）。
2. `element_sim` 的 spec、schema、`check-spec` 與幾何（B1.1、B1.6）；以 J14 相同的平板配置做兩個後端的一致性。
3. 場（B1.2，含分區）與 MT 測試；確定性場檢查（B1.7）。
4. 建立 J15 幾何（§B.4.1）；通過 overlap、物質預算、能量平衡；以測試重算 §B.4.1、§B.4.2 的核對數值。
5. 所有帶電徑跡的平面穿越與量能器漏失（B1.3）、ROOT 檔（B1.4）、`simroot`（B1.5）。
6. `from-geometry` 與實現設定檔（B1.8）；以 J15 候選核對。
7. B1.9 的 adapter 變更項目；B1.10 全部打勾；跑 §A.8 的檢查。

**B2**
1. `simreco` 的擬合器單元測試，再接 `simroot dump` 的輸入（B2.1）；CI 工作。
2. 尾部來源（B2.2）與 F4 觀測量（B2.3）。
3. `reco` 與 `table`、`MISSING_FILE_ARGS` 的擴充（B2.4）；遞移的處理鏈（B2.5）。
4. F4 介面：`f4-results/1`、`label --results --geometry`、對照表 1.1.0、`design.py` 的變更（B2.6）。
5. 驗證類別、表條目、`change`、regression 角色、`multiple-scattering-reference` 與契約測試（B2.7）。
6. 資格路徑（B2.8）：D0 核准前留在分支。
7. 端到端測試（閘門 G-B2）；B2.9 的 adapter 變更項目；B2.10 全部打勾；跑 §A.8 的檢查。

**B3**
1. J15 的 design-spec、候選、實現設定檔；F1、F2 與 `report`（B3.1）。
2. 在 E2 執行驗證梯與 `multiple-scattering-reference`（B3.2）。
3. 量能器 cut 收斂、variation 與包絡、TOF 敏感度（B3.3–B3.5）。
4. F4 研究與尾部來源的示範（B3.6）。
5. recorded 資料、註冊、journey、文件、獨立 agent 的驗收題（B3.7–B3.8）；B3.9 全部打勾；跑 §A.8 的檢查。

---

## §B 附錄 A：數值

計算程式：`j15_design_estimates.py`（本資料夾；只用標準函式庫，scipy 可選；A_N 以精確有理數最小平方核對閉式）。

**幾何**
- Si 中心：−500、−340、−180、−20、140、300 mm；L = 0.800 m。
- 場區：−520 … 320 mm；兩端邊距各 19.85 mm。
- TOF1 兩層 −810 … −800、−790 … −780；TOF2 兩層 490 … 500、510 … 520；站中心距 D = 1.300 m；世界 ±1200 mm。

**徑跡**
- A_N = 720 (N−1)³ / [(N−2) N (N+1)(N+2)]：A₄ = 81.0、A₆ = 66.96、A₈ = 57.17（N 點等距含兩端、等權重）。
- MDR（只算量測項）= C B L² / (ε √A_N)：C = 0.2998 時 1172 GV（C = 0.3 時 1173 GV）。
- 多重散射項（β = 1，含 log）：1.34 %，以 1.0–1.4 係數框定。

下表由 `j15_design_estimates.py` 印出（臂長 L 固定、平面等距；MDR ∝ B/√A_N；多重散射項 ∝ 1/B，並隨總厚度 N × 0.3 mm 依 Highland（含 log）改變；兩項相等的剛度 = 多重散射項 × MDR）：

| B (T) | N | MDR (GV) | 多重散射項（β = 1） | 兩項相等的剛度 |
|---|---|---|---|---|
| 0.15 | 6 | 352 | 4.5–6.2 % | 16–22 GV |
| **0.5** | **6** | **1172** | **1.3–1.9 %** | **16–22 GV** |
| 1.0 | 6 | 2345 | 0.7–0.9 % | 16–22 GV |
| 0.5 | 4 | 1066 | 1.1–1.5 % | 11–16 GV |
| 0.5 | 8 | 1269 | 1.6–2.2 % | 20–28 GV |

**場檢查網格**（50 mrad，方向和偏轉相反，正電荷）：

| 剛度 | 場內最大 \|y\| | Si1 … Si6 的 y（mm） | TOF2 兩層的 y |
|---|---|---|---|
| 0.6 GV | 29.0 | 25.0、29.0、26.6、17.8、2.5、−19.3 | −50.0、−53.2 |
| 1 GV | 32.4 | 25.0、30.6、32.4、30.3、24.4、14.6 | 0.2、−1.4 |
| 10 GV | 60.7 | 25.0 … 60.0 | 67.1、67.9 |
| 100 GV | 65.5 | 25.0 … 64.5 | 73.8、74.8 |
| 1000 GV | 66.0 | 25.0 … 65.0 | 74.5、75.5 |

若方向和偏轉相同（−50 mrad）：0.6 GV 在 Si6 的 y = −151 mm、1 GV 為 −116 mm，都錯過 Si6。正入射（0 mrad）時 0.6 GV 在 Si6 的 y ≈ −85 mm、TOF2 兩層 ≈ −126、−130 mm，仍在接受度內（`j15_design_estimates.py` 印出）。

**TOF**：σ_站 = σ_層/√2，σβ/β = σ_層 c / D；每層 80、100、150 ps 對應 1.8 %、2.3 %、3.5 %（每站一層時 2.6 %、3.3 %、4.9 %）。同站兩層之間 β = 1 的飛行時間 66.7 ps，兩層時間差的解析度 √2 σ_層（100 ps 時 141 ps）。

**量能器**：18.41 X₀、0.886 λ_I、35 cm；有效 Molière 半徑 3.95 cm；mip 能損比 0.284 只是 dE/dx_min 之比，**不是**參考值。

**量能器前的物質**：11.32 % X₀（四層 TOF 9.40 %，佔 83 %；Si 1.92 %）、5.46 % λ_I；其中 TOF1 在徑跡之前，佔 4.70 % X₀。

**事件數**（差值 se ≤ tol/4，不含兩階段因子）：10 GeV 電子總沉積（容許 1 %）約 392；後漏（絕對容許 0.002）約 5000。乘兩階段因子 f = F_0.90(15,15) ≈ 1.97 後約 770 與 9,900。

## §B 附錄 B：出處

- PDG Atomic and Nuclear Properties（2026-10-21 取得）：[Silicon](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/silicon_Si.html)、[Lead](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/lead_Pb.html)、[Polyvinyltoluene](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/polyvinyltoluene.html)
- PDG Review of Particle Physics 2024，第 34 章：式 34.5、34.12、34.16、34.34–34.36（式號依 plugin 的 VALIDATION GEANT4-STUDY）
- Geant4 v11.4.3 原始碼，與場和事件檔相關：`G4FieldManager.hh`、`G4ChordFinder.hh`、`G4PropagatorInField.cc`、`G4FieldParameters`、`G4LogicalVolume`、`G4ChargedGeantino.cc`、`G4VAnalysisManager.hh`、`G4EmSaturation`、`G4LossTableManager`、`G4IonTable`、`G4NistMaterialBuilder.cc`
- Geant4 Book for Application Developers，[Basic Examples](https://geant4.web.cern.ch/documentation/dev/bfad_html/ForApplicationDevelopers/Examples/BasicCodes.html)（B4、B5）
- hep-research `main` `5584927`：`skills/hep-detector/references/system-design-workflow.md`、`contracts/design.py`（`check_f4` 行 988–1062、`TAIL_SOURCES` 行 64）、`skills/hep-detector/scripts/evaluate_design.py`（`geometry` 行 462、`f4` 行 498）、`contracts/rules/design_geometry.json`、`contracts/rules/design_adequacy.json`、`examples/design-space-spectrometer/`、`skills/hep-detector/references/geant4-study-protocol.md`（§6 行 161–168）
- PAMELA 與 AMS-02 的出處見 §R.14
- 待取得：PDG 的 μ 能損表（Groom, Mokhov & Striganov）；Sternheimer, Berger & Seltzer (1984), *Atomic Data and Nuclear Data Tables* 30, 261；Lynch & Dahl (1991), *Nucl. Instrum. Methods B* 58, 6（多重散射寬度公式與其精度）；已發表的多重散射量測（例如 MuScat）

## §B 附錄 C：版本歷程

| 版本 | 內容 |
|---|---|
| 探測器文件與 v5 | 單軸疊層磁譜儀；Gluckstern 小 N 公式更正；磁場方向與場檢查網格 |
| 2026-10-22 | TOF1、TOF2 各兩層；數位化與重建改為 C++；逐事件 ROOT 檔；拆分為任務 B；依新架構改寫（`element_sim` 取代 spec/2；B1、B2；PAMELA、AMS-02 對照與 TOF 敏感度） |
| 2026-10-23 | 獨立審查後修正（B1.6 只比共同觀測量、量能器漏失、表條目、surrogate 與 regression 規則、總動量剛度、CLI 與 `SIM_SOURCES`、可攜的亂數、stepper 明確建立等） |
| 2026-10-23 | 依計畫（第 1 部）重新整理：B2 拆為 B2（重建與契約）與 B3（J15 研究）；確定性場檢查移到 B1.7；新增 `geant4_run.py check-spec`；判定引擎的 `change` 與 regression 角色在 B2 加入 |
| 2026-10-23 | 加入 isolated worktree 的執行規定：檔頭、§B.0 的第一步、§B.11 的開頭（§P.10） |
| **2026-10-24（本版）** | **對照 main 0.38.0 的設計流程重新規劃（審查紀錄 `review-2026-10-24-main-0.38.md` 的 B1–B12）：任務 B 成為 main 缺少的 F4 評估器；B1 加入 `from-geometry` 與實現設定檔、所有帶電徑跡的穿越、分區均勻場；B2 加入可切換的尾部來源、F4 觀測量、`label --results --geometry`、`f4-results/1`、對照表 1.1.0、`design.py` 的 F4 變更、F4 資格路徑（D0）與 `multiple-scattering-reference`、端到端測試，刪除 surrogate 類別；B3 改為 J15 設計專案（F1、F2、F4），驗證梯另立紀錄；保真度採 main 的 F0–F5；契約版本記為 CV-B2；VALIDATION 條目 GEANT4-F4；更正事實（`MISSING_FILE_ARGS` 行 153、腳本數 23、benchmark 函式行號、protocol §6 的模型範圍）** |

---

# 第 4 部　任務 C：自動化候選設計產生（§C）

> 順序：C1 以 main 為基底（不依賴任務 A、B）；C2 在 B2 與 C1 之後（F4 確認另需 §P.7 的 D0 核准）；C3 在 C2 之後
> 日期：2026-10-24（依 main 0.38.0 的探測器系統設計流程重新規劃）
> 一句話：在 main 的設計流程 D2 階段加入自動產生候選設計的 `evaluate_design.py search`；搜尋只提出候選，判定、篩選、比較與 Pareto 一律由 `contracts/design.py` 推導，回報的性能只來自 F4 確認研究

---

## §C.0 任務卡

**目標。** 讓 AI 在使用者的 design-spec 之下，自行選擇子系統的種類與數量並調整參數，自動產生值得評估的候選設計，再把少數決選者交給 main 的設計流程評估、判定與比較；以 Geant4 的搜尋值細化，並以種子獨立的 F4 研究確認。結果經得起統計與來源的檢查，而且不宣稱全域最佳。

**三個階段：**

| 階段 | 內容 | 前提 | 版本 |
|---|---|---|---|
| **C1** F1 搜尋 | 搜尋 spec、角色的實現規則與材料表、基因與解碼器（輸出 design-candidate 的 overrides）、以 tool contract 在行程內計算的 F1 搜尋值、標準函式庫的搜尋器（Sobol、NSGA-II、超體積）、`evaluate_design.py search` 與 `search_summary`、`expand --search`、封閉測試、workflow 文件 | main（0.38.0） | contracts **CV-C1**（minor） |
| **C2** Geant4 搜尋值與 F4 確認 | `core/` 的配對模式與 `values` 累加器；以 `element_sim` 短 run 計算的 Geant4 搜尋值；搜尋中的配對比較；決選者的 F4 確認研究；種子規則 | B2、C1；F4 確認需 D0 | geant4 adapter **0.5.0**、contracts **CV-C2**（minor） |
| **C3** 範例 | J16：在 Example A（太空磁譜儀）與 Example B（對撞機徑跡＋ECAL）上執行搜尋；選用的貝氏最佳化後端 | C2 | 選用 `adapters/design-bo/` **0.1.0** |

**不在範圍內：** 寫入或推導判定、排序、Pareto 或「推薦設計」（由 `contracts/design.py` 推導）；宣稱全域最佳；可微分模擬與可微分代理模型（§C.9）；Geant4 搜尋值的非盒狀幾何；光學物理；強化學習；以成本為目標。

**交付物：** `evaluate_design.py` 的 `search` 子命令與 `expand --search`；`contracts/schemas/design_search_spec.json` 與 `ext_computational_run.json` 的 `search_summary`（CV-C1）；`skills/hep-detector/assets/design-search/`（角色的實現規則、材料表、Sobol 方向數）；`core/` 的配對模式與 `values`（C2.1）；`contracts/design.py` 的種子規則（CV-C2）；`system-design-workflow.md` 的「D2 自動產生候選」一節；封閉測試；J16；VALIDATION 條目 DESIGN-SEARCH-F1（C1）、DESIGN-SEARCH-G4（C2）、DESIGN-SEARCH-EXAMPLES（C3）；CHANGELOG；release manifest。

**完成的定義：** C1.10、C2.9、C3.4 的驗收清單全部打勾；§A.8 的檢查全部通過；閘門 G-C1、G-C2a、G-C2b、G-C3（§P.6）通過。

**主要決定：**
1. **搜尋只提出候選，不下判定。** 判定、篩選、comparison basis、排序與 Pareto 只由 `contracts/design.py` 推導（`system-design-workflow.md` 第 3–4、149–150、203–207 行）；搜尋不寫 `verdict`、不排序、沒有「推薦設計」，也不宣稱全域最佳。
2. **搜尋是 D2 的候選產生器。** 輸入是目前的 design-spec 與一個基礎候選；族群（10⁴ 量級）只存在 `search_summary` 中，只有 `expand` 出來的決選者才成為 design-candidate，之後像任何候選一樣以 `evaluate_design.py run`、`budget`、`report` 處理（RSK-04：只有進入比較的點才展開）。
3. **保真度沿用 main 的名稱。** 行程內的 F1 是 main 的 F1 tool contract；Geant4 短 run 的數值是**搜尋值**，沒有保真度，永遠不是 evaluation；確認是種子獨立的 F4 研究。
4. **搜尋與確認分開。** 搜尋值有「贏家詛咒」，只用於選擇；對外的數字只來自 `evaluate_design.py` 寫出的 evaluation，Geant4 的性能只來自 F4 確認研究（§C.4.8）。
5. **自由組合，但在角色之內。** 結構的自由度來自「`subsystem_roles` × 角色的實現規則」：通過有效性規則的任何組合都是合法候選；新的角色或實現規則經審查過的變更加入（§C.4.5）。
6. **Claude 是設計者，不是裁判。** Claude 寫設計摘要、種子設計與搜尋範圍；它的提案和隨機產生的候選走同一條評估管線，參數的 `source` 為 `proposal`，並在 `search_summary` 中標記。
7. **只用標準函式庫是刻意的選擇。** core 的依賴本來允許 numpy、scipy（`requirements-core.txt`）；搜尋器以標準函式庫實作，是為了逐位元可重現與無依賴執行，不是限制。

**第一步：** 依 §P.10.2 為本階段建立 isolated worktree（`.claude/worktrees/geant4-<階段>`，分支 `worktree-geant4-<階段>`，基底為已含前提階段的最新 `origin/main`），並確認 `git rev-parse --show-toplevel`、`git branch --show-current`、`git status` 與前提階段的合併 commit 是 `HEAD` 的祖先。以下所有步驟都在這個 worktree 中進行。

**開始前必做：** 讀 §P.0–§P.6；讀 `skills/hep-detector/references/system-design-workflow.md` 全文與 `contracts/design.py` 的 `orphan_runs`、`effective`、`effective_digest`、`check_f4`、`ranking`、`pareto`；讀 `evaluate_design.py` 的 `run_evaluation`、`scan`、`expand`。C2 另讀 §A.3、§A.4、A1.4–A1.9、§B.4、B1.1、B1.6、B2.1、B2.4 與 F4 資格路徑（§P.7 的 D0）。依 §A 附錄 C 的方法核對本部引用的事實。

---

## §C.1 名詞與檔案

| 名詞 | 意義 |
|---|---|
| design-spec、design-candidate、design-evaluation | main 的三種設計產物（contracts 3.11.0 起）；需求、候選與評估都用它們，本任務不另定格式 |
| 基礎候選 | 搜尋的起點；解碼出的候選以 `derived_from` 指向它並只列 `overrides`（去掉子系統的拓撲例外，§C.4.5） |
| 搜尋 spec | `design-search-spec/1`：引用的 design-spec 與基礎候選、目標與約束（figure of merit id 與分母）、自由參數與範圍、角色槽位、預算、最佳化器設定、種子、停止規則；第一次評估前取雜湊 |
| 角色的實現規則 | 每個 `subsystem_roles` 角色可由搜尋改變的參數、範圍、單位、校正範本與預算模型；隨附於 `skills/hep-detector/assets/design-search/` |
| 基因（genome） | 搜尋器內部的編碼：槽位的啟用、角色、`parent_slot`、類別、整數與連續參數；只存在搜尋器內 |
| 解碼器 | 基因 → design-candidate（基礎候選上的 `overrides`）的確定性函式 |
| 搜尋值 | 搜尋中計算的目標值：行程內的 F1，或 C2 的 Geant4 短 run；只用於選擇，從不寫成 evaluation |
| 保真度 F0–F5 | main 的定義（`contracts/design.py:65`）：F0 啟發式、F1 解析 tool contract、F2 toy MC、F3 response 與預期精度、F4 重新發出為 `validated-in-scope` 的 Geant4 研究、F5 量測 |
| `search_summary` | 搜尋 run（`runs/SEARCH-*.computational-run.json`）的區塊（CV-C1）：設計摘要、搜尋值、搜尋前緣、超體積、搜尋規模、提案標記、決選者 |
| 搜尋前緣 | 搜尋值上的非支配集合；沒有約束力，不是 main 的 Pareto 前緣 |
| 決選者 | 搜尋結束時固定並 `expand` 成 design-candidate 的少數設計 |
| 確認研究 | 決選者的 F4 研究，種子 S = H(search_id, "confirmation", design_sha256)，不曾在搜尋中使用 |
| 贏家詛咒 | 從 n 個帶雜訊的評估中選最佳者時，其估計值的期望偏樂觀 |
| 搜尋規模 | 實際評估的不重複設計數與拓撲數；寫入 `search_summary`，類似 look-elsewhere |
| seed_group、配對比較 | 一組共用 S 的 Geant4 搜尋 run；以逐區塊差值估計差值的 SE（common random numbers；C2.1） |
| 記法 | 「C1.3」是本部的工作項；「A1.8」「B2.1」是任務 A、B 的工作項（工作項編號全文唯一）；「§C.4」是本部的節；「§A.3」「§P.7」「§R.6」等是同一文件其他部的節 |

**主要檔案（相對 `plugins/hep-research/`）：**
- `skills/hep-detector/scripts/evaluate_design.py`（新增子命令 `search`；`expand` 接受 `--search`）。
- `skills/hep-detector/assets/design-search/`（新增：`roles.json` 角色的實現規則、`materials.json` 材料表、`sobol_joe_kuo.txt` 方向數）。
- `contracts/schemas/design_search_spec.json`（新增）、`contracts/schemas/ext_computational_run.json`（`search_summary`）、`contracts/design.py`（`orphan_runs` 的豁免；CV-C2 的種子規則）。
- `skills/hep-detector/references/system-design-workflow.md`（新增一節）。
- C2：`core/stats/decisions.py`、`core/stats/batch_means.py`、`core/simulation/summary.py`、`core/simulation/seeds.py`（配對模式、`values`、seed_group）；`adapters/geant4/assets/g4sim/SimSummary.hh`（`values`）。

---

## §C.2 前提與提供的介面

| 提供者 | 介面 | 任務 C 的用法 | 需要於 |
|---|---|---|---|
| main | design-spec（REQ、分母、配分、`comparison_basis`、`pareto_axes`）與 H1、H2 | 目標與約束只引用 design-spec 的需求與 `design_adequacy.json` 的 figure of merit id；需求變更是新 spec 版本＋`requirement-change` 紀錄 | C1 |
| main | design-candidate（`DES-*` 子系統、`subsystem_roles`、`derived_from`＋`overrides`、參數的 `source`／`status`、子系統的 `calibration`、`budgets`） | 解碼器的輸出格式；`effective_digest` 去重 | C1 |
| main | F1 tool contract（`tracker_resolution`、`multiple_scattering`、`charge_confusion_rate`、`pid_separation_power`、`cherenkov_angle`、`calorimeter_resolution`、`design_estimates`）與 `run_evaluation` 的引數重算 | 行程內 F1 搜尋值：以同一個工具、同一組引數計算（C1.4） | C1 |
| main | `scan`／`expand` 與 `scan_summary`（`evaluate_design.py:754-875`；`orphan_runs` 對 `scan_summary` 豁免，`contracts/design.py:1655-1683`） | `search_summary` 依同一模式；`expand --search` 推廣 `expand` | C1 |
| main | `run`、`budget`、`report`、`plan`；判定、篩選、排序、Pareto（`contracts/design.py:1369-1508`、`1949-2051`） | 決選者的正式評估與比較 | C1 |
| main | `geometry` → 研究 → `f4`（`evaluate_design.py:462-560`；`contracts/design.py:988-1062`） | 決選者的 F4 確認 | C2 |
| main | `run_workflow.py --incremental`、`parameter_digest` | 決選者評估鏈的重跑 | C2 |
| 任務 A | `core/simulation/seeds.py`（H、S）、`summary.py`、`simulation-observables/1`、`core/stats/batch_means.py`、`decisions.py` 的 `equivalence`、兩階段事件數（A1.9）、`extension.simulation.evidence_role`（A1.4） | Geant4 搜尋值的種子、估計與角色 | C2 |
| 任務 B | `geant4_run.py from-geometry`（B1）、`element_sim`、`simreco`、`reco`、`label` 寫出的 `results` 與 `tail_sources_simulated`、mapping 1.1.0、B2 的變更判定 `change`（B2.4） | Geant4 搜尋值；F4 確認研究 | C2 |
| §P.7 | D0：偵測器層級研究成為 F4 的資格路徑（B2 實作） | 確認研究能否升級為 `validated-in-scope` | C2 |

**提供給其他任務的介面：** `search_summary` 與 `expand --search`（任何自動或人工的候選產生器都可沿用）；C2.1 的配對模式與 `values` 累加器，任何研究都可使用（例如收斂閘門可以宣告配對模式）。

---

## §C.3 硬性限制

§A.3 與 §B.3 中適用於本部的限制都適用。另外：

1. **不寫判定。** 搜尋與它的輸出不寫、不改任何 verdict、成熟度、過時標記、`screened_out`、`at-risk`、排序或 Pareto；不宣稱全域最佳（`system-design-workflow.md` 的「Never」一節）。
2. **搜尋值不是 evaluation。** 搜尋值只存在 `search_summary`；族群不以 design-candidate 寫入 artifacts_dir；只有 `expand` 的決選者成為候選。任何對外的性能數字必須引用 design-evaluation。
3. **同一個量只有一份正式實作。** 行程內的 F1 搜尋值以 tool contract 的同一個工具與同一組引數計算（匯入工具腳本並呼叫其 `main(argv)`，C1.4），不另寫公式；一致性測試比對行程內的值與 `evaluate_design.py run` 的值（C1.10）。
4. **事先宣告。** 搜尋 spec、design-spec 與基礎候選的雜湊、角色規則與材料表的版本、預算、最佳化器設定與種子在第一次評估前寫入 `search_summary`；之後的變更是新的搜尋（新的 SEARCH id）。需求的變更依 main 的規則（新 design-spec 版本＋`requirement-change` 紀錄）。
5. **LLM 提案沒有特權。** Claude 提出的設計和隨機設計走同一條解碼、有效性與評估管線；參數 `source` 為 `proposal`，在 `search_summary` 中標記 `proposer: llm`；Claude 不得修改任何輸出。
6. **成本不是目標。** cost 在 main 沒有評估器（`capability.unavailable`）；質量、功率、通道數與資料率只經由候選的 `budgets` 與 main 的 budget figure of merit 進入，搜尋由角色規則產生的預算列標記 `basis: estimate`、來源寫明是假設的模型。
7. **只用標準函式庫**（刻意的選擇，§C.0 決定 7）。貝氏最佳化只在選用的 `adapters/design-bo/` 中，以延遲 import 載入；沒有安裝時搜尋仍可執行。
8. **實驗名稱** 只出現在 `docs/` 與範例 README；角色規則用通用名稱；文件引用 §C.4.1 的研究時只用 citation key（例如 `Cisbani2020`），不寫 EIC、ePIC 等名稱（實驗名稱掃描會檢查）。
9. **不新增 reference、不修改 `skills/hep-detector/SKILL.md`。** 設計流程的入口已由 hub 連結決定（CHANGELOG 0.37.0 的 OQ-01）；本任務只在 `system-design-workflow.md` 新增一節。
10. **人工閘門不由搜尋取代。** 搜尋不需等待 H1、H2，但 `report` 照常顯示閘門旗標；決選者進入收斂（H3）與基準（H4）仍需人工紀錄。
11. 契約規則以 `strict or _at_least(contract_version, CV-C1)`（`search_summary`）與 `CV-C2`（種子規則）閘控。

---

## §C.4 設計

### §C.4.1 實際做法的參考與教訓

| 研究 | 做法 | 本設計採用的教訓 |
|---|---|---|
| `Cisbani2020`（JINST 15 (2020) P05009） | 8 個參數；目標為 π/K 分離（兩個動量的調和平均）；Geant4 帶 2.5 % 雜訊；高斯過程貝氏最佳化，每次 20 個設計並行，約 55 次呼叫收斂；優於原設計（3.23 對 2.9）；以後驗推得容差區間（數字待依原文核對） | 雜訊要明確建模；平行批次；結果「只基於模擬」，需要更高保真度與原型確認 |
| `AID2E2024`（arXiv:2405.16279） | 多目標貝氏最佳化（qNEHVI，Ax/BoTorch）與 NSGA-II；7 個參數、200 次評估、150 次收斂；以已知 Pareto 前緣的 DTLZ2 做封閉測試；分散執行 | 多目標；目標數 ≤ 4 時用 MOBO，更多或不連續時用遺傳演算法；先做封閉測試；幾何約束在模擬前檢查 |
| `MODE2022`、`MODE2023`（arXiv:2203.13818、2310.05673） | 端到端可微分最佳化；可微分代理模型；效用函數包含物理目標與成本 | 以實驗目標而非子系統各自最佳化；代理模型可能把設計導向偏差，必須以完整模擬確認 |
| `AIDO2025`（arXiv:2502.02152） | 取樣量能器的厚度與材料（數字待依原文核對）；材料為類別變數；成本與長度上限；重現已知的量能器原則 | 類別選擇可以進入搜尋；「重現已知原則」是合理的第一個驗收 |
| `Borysov2024`（EPJ Web Conf. 315, 03006） | 半解析模型（以 Geant4 核對）＋遺傳演算法與非支配排序 | 解析模型先篩選、Geant4 核對：即 main 的 F1 → F4 |
| `SWGO2023`（arXiv:2310.01857） | 10³–10⁴ 量級個單元位置的可微分最佳化；效用 = 通量精度 + 能量解析 + 指向解析 + 面積成本 | 效用的權重是宣告的選擇；某些項會把設計推向極端，需要檢查 |
| `GRACE2026`（arXiv:2602.15039） | LLM agent 從自然語言或論文建立模擬並探索設計變體；有物理檢查器與 provenance | 幾何應在模擬前驗證；agent 注意到異常卻未追查；忽略工程約束 |
| `VIBRATO2026`（arXiv:2604.21804） | LLM agent 指揮 DD4hep/Geant4 的雙層掃描，46 次 run 達到 2255 點網格的最佳 | agent 擅長分解問題與調整掃描；結論需獨立核對，可實現性仍需專家把關 |

綜合：沒有一個實際案例讓 LLM 自己宣告「最佳」；成功的做法都是「明確的目標與約束＋可重現的評估＋有紀錄的最佳化器＋完整模擬確認」。main 的設計流程已提供前兩者與確認的位置（F4、H1–H4）；本任務補上「有紀錄的最佳化器」與「從搜尋到確認的統計保護」。

### §C.4.2 在 main 設計流程中的位置

```
D0 範疇（H1） → D1 配分（H2） → D2 探索 ─────────────────────────────▶ D3 收斂（H3） → D4 審查（H4）
                                  │  人工候選、scan/expand（main）
                                  │  search（本任務）：
                                  │    設計摘要 → F1 搜尋值 →（C2）Geant4 搜尋值 → 決選者
                                  │    → expand → run/budget（F1–F3）→（C2）geometry → F4 確認 → f4
                                  └▶ report：判定、篩選、comparison basis、排序與 Pareto 或其拒絕（design.py）
```

| 角色 | 可以做 | 不可以做 |
|---|---|---|
| Claude（設計者） | 從 design-spec 整理搜尋 spec；選擇候選角色與槽位；寫 2–6 個種子拓撲與物理理由；設定搜尋範圍（在角色規則內）；分解問題；決定何時做 Geant4 搜尋與確認；追查異常；向使用者說明 `report` 的結果與取捨 | 發明角色規則外的參數；跳過有效性檢查；修改任何輸出；回報搜尋值；寫判定或排序；在看到結果後悄悄改需求 |
| 搜尋器 | 在基因空間中產生候選；依預算、種子與設定執行；記錄每次評估 | 判定是否符合需求；排序決選者 |
| `evaluate_design.py`／`contracts/design.py` | 正式評估、判定、篩選、比較、Pareto | 依提案者改變行為 |
| 使用者與審查者 | H1–H4 的人工紀錄；處置（accept-risk、next-study） | — |

### §C.4.3 舊任務 C 的概念與 main 的對應

| 舊任務 C 的概念 | main 的對應 | 處理 |
|---|---|---|
| 需求規格 `detector-requirements/1`、`confirmed_by_user` | design-spec（REQ、分母、配分、`comparison_basis`、`pareto_axes`）；H1、H2 | 刪除，改讀 design-spec |
| 目標與約束目錄 | `design_adequacy.json` 的 figure of merit id | 刪除，改用 id |
| 元件目錄 `catalogue/1` | `subsystem_roles` ＋ tool contract 的 design 區塊 | 改為角色的實現規則與參數範圍（新） |
| 設計文法 `detector-design/1` | design-candidate（子系統圖） | 刪除；基因只作內部編碼＋解碼器（新） |
| `realize()` → `element_sim.spec/1` | `evaluate_design.py geometry` ＋ B1 的 `from-geometry` | 刪除，由任務 B 提供 |
| 保真度 F0／F1／F2 | main 的 F1；Geant4 搜尋值（無保真度）；F4 | 改名（§C.4.6） |
| 設計雜湊與評估快取 | `effective_digest`、`parameter_digest`、`--replace`、`run_workflow.py --incremental` | 搜尋內的快取保留，正式評估用 main 的機制 |
| `threshold` 需求判定、`order`、自訂 Pareto、「推薦設計」 | 判定表與彙整、`ranking()`、`pareto()` | 刪除 |
| 搜尋紀錄 `extension.design_search` | `scan_summary` 的模式 | 改為 `search_summary`（CV-C1） |
| CV3 的角色規則 | 孤兒 run 規則 | 改為 CV-C2 的種子規則 |
| adapter `detector-design`、reference、`SKILL.md` 一行 | 能力 `detector-design`（hep-detector）、workflow 文件 | 刪除；新增 workflow 一節 |
| `proposer: llm` | 參數 `source`／`status: proposal` | 合併，另在 `search_summary` 標記 |
| NSGA-II、Sobol、超體積、修復與違反量 | 無 | 保留（新） |
| Geant4 多保真度搜尋、配對比較、G-C2a、`values` | 無 | 保留（C2） |
| 贏家詛咒與搜尋規模的保護 | 部分：RSK-04 只展開進入比較的點 | 保留並延伸 |
| 封閉測試 | 無 | 保留 |
| J16 | Example A、B（無 journey） | 改為在 Example A、B 上執行 |

### §C.4.4 搜尋 spec `design-search-spec/1`

示意（`//` 為說明，不是 JSON 的一部分）：

```
{ "search_spec_version": 1,
  "design_spec": {"path": "design-spec.v1.json", "sha256": "..."},
  "base_candidate": "<design_id>:cand-S",
  "objectives": [  // figure of merit id 與分母取自 design-spec 的需求；方向取自適足表的 better
    {"requirement": "REQ-TRK-001"},                       // momentum-resolution-core，rigidity_GV 100、proton
    {"figure_of_merit": "mass-budget"} ],
  "constraints": [ {"requirement": "REQ-MDR-001"} ],      // 搜尋中以搜尋值檢查的可行性，沒有約束力
  "free_parameters": [  // 角色規則內的範圍；整數與類別另標
    {"ref": "DES-TRK-001.parameters.layer_positions_m", "kind": "positions", "n": [4, 8], "min_spacing_m": 0.05},
    {"ref": "DES-MAG-001.parameters.field_T", "range": [0.1, 1.0]} ],
  "slots": {"tof": [0, 1]},                               // 選用：可增刪的角色與數量
  "rules_version": "1.0.0", "materials_version": "1.0.0",
  "budget": {"evaluations": 20000, "geant4": 0},           // C2 起 geant4 > 0
  "optimizer": {"name": "nsga2", "population": 200, "generations": 100, "eta_c": 15, "eta_m": 20, "seed": 12345},
  "stopping": {"hypervolume_window": 10, "min_improvement": 0.001, "reference_point": "auto"},
  "finalists": {"max": 5, "distinct_topologies": true} }
```

- 目標最多 4 個（超體積以 WFG 精確計算），其餘以約束表達。
- 目標只能是有 F1 tool contract 的 figure of merit（C1），或 C2 有 Geant4 實作的 figure of merit；需要上游的 figure of merit（例如電荷誤判需要解析度）在行程內依鏈的順序計算。
- 只有 `capability.unavailable` 的 figure of merit 不能當目標；搜尋照實記錄它們，`report` 照常列出。

### §C.4.5 基因、解碼與有效性

**角色的實現規則第一版**（`roles.json`；每條規則有參數、單位、範圍、校正範本與預算模型）：

| 角色 | 搜尋可改變的參數 | 預算模型（`basis: estimate`，假設的模型） | 對應的 F1 工具 |
|---|---|---|---|
| `tracking` | `layer_positions_m`（陣列；層數 N）、`point_resolution_um`、`layer_x_over_x0`（由材料與厚度經材料表換算）、`passive_x_over_x0` | 密度 × 體積；通道數 = 面積／pitch | `tracker_resolution`、`multiple_scattering`、`charge_confusion_rate` |
| `bending` | `field_T`（磁鐵長度另見 Example A 的說明） | 宣告的占位質量模型 | 同上（bending power） |
| `tof` | 層數、σ_t、厚度、路徑長 | 密度 × 體積；通道數 | `pid_separation_power` |
| `calorimetry-em` | 取樣係數、深度（X₀） | 密度 × 體積 | `calorimeter_resolution`（evaluate，optimistic） |
| `rich` | 輻射體折射率與長度、光子數參數 | 宣告的模型 | `cherenkov_angle` |

**基因編碼：** 固定數量的槽位，每個槽位有「啟用」位元、角色（類別）、`parent_slot`（整數；−1 為頂層，否則指向一個啟用的 `bending` 或 `calorimetry-*` 槽位）、該角色的類別參數（材料）、整數與連續參數。這讓遺傳演算法可以增刪子系統與更換種類。

**解碼（基因 → design-candidate）：**
- 採 main 的粒度：一個角色一個子系統，平面以陣列參數表達（例如一個 `tracking` 子系統的 `layer_positions_m`），不是每片平面一個子系統。
- 只改參數或新增子系統的設計：寫成基礎候選上的 `overrides`（新增的子系統以新的 `DES-*` id）；`deep_merge` 只能加不能刪（`contracts/design.py:252-260`、`384-394`），所以去掉子系統的拓撲寫成不含 `derived_from` 的獨立候選，由基礎候選複製並在說明中註明。
- 每個參數寫 `source: "search SEARCH-<id> point <k>"`、`status: proposal`；新增的子系統依角色規則帶 `calibration`（方法與至少一個控制樣本；否則 `design.calibration_incomplete`）與每個預算量的預算列。
- 解碼結果以 `contracts.validate.validate_artifact` 與 `contracts/design.py` 的候選檢查驗證。

**有效性（評估前檢查）：** 參數在角色規則範圍內；平面之間的最小間距；不超出包絡；子體只在一層巢狀內；材料在材料表中。結構上「不合理」的組合（例如沒有磁鐵卻要求剛度解析度）**不**由規則禁止，而由目標與約束自然淘汰。

**修復與違反量：** 交配或突變之後依序修復：連續與整數參數截到範圍；`parent_slot` 指向停用或不能當母體的槽位時改為 −1；平面位置排序後依最小間距推開，超出範圍的截回。修復後仍無效的設計以違反量 v = Σ（各規則的正規化違反：重疊長度／包絡長度、超出包絡的長度／包絡長度、間距不足／宣告的最小間距、巢狀超過一層的子體數）進入 constrained-domination（v 小者優先；v = 0 才比較目標）。

**去重與快取：** 搜尋內以解碼後候選的 `effective_digest`（同樣的參數得到同樣的摘要）去重，搜尋規模以不重複的設計計。快取鍵 = `effective_digest`、評估層級、工具與角色規則的版本、程式雜湊，以及 Geant4 搜尋值的 S、N、K、B（同一設計在不同 seed_group 中是不同的評估）。

### §C.4.6 評估的層級

| 層級 | 方法 | 每個設計的成本 | 寫在哪裡 | 用途 |
|---|---|---|---|---|
| F1 搜尋值 | 行程內呼叫 F1 tool contract 的工具（C1.4） | 毫秒 | `search_summary` | 結構與參數搜尋，10⁴–10⁵ 個設計 |
| Geant4 搜尋值（C2） | `element_sim` ＋ `simreco` 短 run，約 10³ 事件，K = 16 | 分鐘 | `search_summary` | 細化數百個設計；校正 F1 的偏差 |
| 正式評估（F1–F3） | 決選者 `expand` 後以 `evaluate_design.py run`、`budget`、`response` | 秒到分鐘 | `evaluations/`、`runs/` | design.py 的判定與比較 |
| 確認（F4，C2） | `geometry` → 研究（新種子，A1.9 的事件數、收斂閘門、variation）→ `label --upgrade` → `f4` | 小時 | `evaluations/`、研究紀錄 | 唯一的 Geant4 性能數字 |

- F1 搜尋值繼承 tool contract 的 bound（多半是 `optimistic`）：搜尋值達標不表示合規，只表示值得評估。
- 每個決選者記錄「搜尋值 − 正式評估或確認值」（`search_minus_official`），供贏家詛咒與模型差異的診斷；差異超過宣告門檻時，Claude 在報告中說明。

### §C.4.7 搜尋策略

| 步驟 | 內容 | 預設方法 | 預算（預設，可宣告） |
|---|---|---|---|
| S0 設計摘要 | Claude 讀 design-spec，寫出候選角色、2–6 個種子拓撲與物理理由、問題的分解 | Claude | — |
| S1 結構與參數搜尋 | 在 F1 搜尋值上搜尋完整基因；初始族群 = 種子拓撲 + Sobol 隨機設計 | NSGA-II（標準函式庫） | 族群 200 × 100 代 = 2×10⁴ 次 |
| S2 Geant4 細化（C2） | 取前 K 個**拓撲不同**的設計，以 Geant4 搜尋值細化連續參數；同一代的設計（包括存活的親代，在該代重新評估）共用 seed_group（配對比較，閘門 G-C2a） | NSGA-II 或 CMA-ES；C3 起可選 MOBO（qNEHVI），限目標 ≤ 4、參數 ≤ 20 | K = 5，每個約 100 次 |
| S3 決選與展開 | 依 `finalists` 規則固定決選者並寫入 `search_summary`，再 `expand --search`；以 `run`、`budget` 做正式評估，`report` 推導判定與比較 | — | ≤ 5 個設計 |
| S4 確認（C2） | 每個決選者、每個（figure of merit, 分母）一份 F4 研究；`f4`；`report` | — | ≤ 5 個設計 |

- 停止規則：預算用完，或超體積在連續 G 代內改善小於宣告值。超體積在正規化的目標空間中以 WFG 演算法精確計算（目標 ≤ 4）；參考點預設為每個目標的需求門檻往較差方向 × 1.1（最小化目標乘 1.1，最大化目標除以 1.1），沒有門檻的目標必須宣告參考點。不依結果加預算；加預算是新的搜尋。
- Claude 在 S0 之後可以加入新的種子拓撲（例如追查一個異常），這些提案同樣標記並計入搜尋規模。

### §C.4.8 統計完整性

| 風險 | 處理 |
|---|---|
| 贏家詛咒 | 搜尋值只用於選擇；決選者在任何正式評估或確認之前固定並寫入 `search_summary`；之後不在決選者之間重新挑選，`report` 一律列出全部決選者；確認研究的種子不曾在搜尋中出現（CV-C2 的規則）；`search_minus_official` 作為診斷 |
| 帶雜訊的約束與優劣 | 不另建判定引擎：合規由 design.py 以適足表的 `coverage_cl` 判定；決選者的優劣只由 design.py 的排序與 Pareto（超過合併 1σ 才支配）處理；選擇感知或多重比較的覆蓋率是給 hep-statistics 與 design.py 的提案（§C.9） |
| 排序的雜訊 | S2 中同一代的設計共用一個 seed_group（配對比較），差值的變異較小；確認研究不共用，維持獨立 |
| 搜尋規模 | `search_summary` 寫入評估的不重複設計數、拓撲數、最佳化器設定與種子 |
| 利用模擬缺陷 | 確認研究必須通過收斂閘門（A1.8、D11）與物理模型 variation（B2）；F4 的範圍與尾部來源由 `check_geant4_study.py label --upgrade` 與 `check_f4` 檢查（範圍外為 `domain.mismatch` 或無法升級） |
| 穩健性 | 對決選者在宣告的容差內以 `scan`（F1）探索，最差點以 `expand` 成候選並像任何候選一樣評估（必要時做 F4）；「穩健」只表示最差點候選在 `report` 中的判定，不另寫判定 |
| 改需求 | 需求的任何改變是新的 design-spec 版本與 `requirement-change` 紀錄；搜尋要重新執行（新的 SEARCH id），舊的搜尋 run 保留 |

### §C.4.9 搜尋紀錄與契約

搜尋 run 是 `runs/SEARCH-<id>.computational-run.json`，`argv`、`script_sha256`、`input_manifest`（design-spec、基礎候選鏈、搜尋 spec、角色規則、材料表）照 `scan` 的寫法，另有 `search_summary`（CV-C1）：

```
{ "search_spec_sha256": "...", "design_spec": "design-spec.v1.json", "base_candidate": "<design_id>:cand-S",
  "optimizer": {"name": "nsga2", "implementation": "evaluate_design.py search", "backend": null, "seed": 12345, "config": {...}},
  "levels": ["F1"],                                   // C2 起加入 "geant4"
  "evaluated": {"F1": 20000, "geant4": 0, "distinct_designs": 18734, "topologies": 143},
  "points": [{"index": 0, "effective_digest": "...", "genome": {...}, "proposer": "random|llm",
              "values": {"momentum-resolution-core": {"value": 0.081, "bound": "optimistic"}}, "violation": 0.0}],
  "front": [0, 17, 233],                              // 搜尋前緣：沒有約束力
  "hypervolume": [{"generation": 1, "value": 0.41}, ...],
  "finalists": [{"index": 233, "fixed_before": "expand"}],
  "seeds": {"geant4_search": []},                     // C2：每個 Geant4 搜尋 run 的 S
  "note": "search values are not evaluations: they take part in no aggregation and support no verdict; expand a point to evaluate it" }
```

- **CV-C1：** `ext_computational_run.json` 加入 `search_summary`（必填 `search_spec_sha256`、`points`、`front`、`finalists`；其餘選用）；`contracts/design.py` 的 `orphan_runs` 對 `search_summary` 豁免（同 `scan_summary`）；一個 evaluation 以搜尋 run 為 `run_ref` 時是 `design.scan_point_not_expanded`（沿用同一代碼，或新增 `design.search_point_not_expanded`，§C.10）。
- **CV-C2：** 一個 evaluation 的 run 或研究的種子（`extension.seeds` 或 `extension.simulation.logical_run_seed`）出現在同一 artifacts_dir 任一 `search_summary.seeds` 中時是 `design.contract_mismatch`；Geant4 搜尋 run 的 `extension.simulation.evidence_role` 為 `search`，不能作為 `label --upgrade` 的證據。
- 大型的 `points` 可以存成同目錄的 JSON Lines 檔，以 sha256 列在 `output_hashes`；`search_summary` 只放摘要與前緣。

---

## §C.5 階段 C1：F1 搜尋（contracts CV-C1）

### C1.1 搜尋 spec 的 schema

`contracts/schemas/design_search_spec.json`（`design-search-spec/1`，§C.4.4），只用 `contracts/schema.py` 支援的關鍵字（目前沒有 `maxItems`、`maximum`、`exclusiveMaximum`、`uniqueItems`；`contracts/schema.py:61-63`）；目標數上限、範圍上界、槽位數與跨欄位規則（目標的需求存在於 design-spec、figure of merit id 在適足表中、參數 ref 存在於基礎候選、角色在 `subsystem_roles` 中）在 Python 中檢查。A2.7 若加入上述關鍵字，可改由 schema 表達，Python 檢查保留為測試。

### C1.2 角色的實現規則與材料表

- `skills/hep-detector/assets/design-search/roles.json`：§C.4.5 的五個角色，每個附參數、單位、範圍、製造容差、校正範本、預算模型與對應的 F1 工具。
- `materials.json`：每種材料的密度、X₀、λ_I；由 Geant4 NIST 材料的 dump 產生（檔頭記錄 Geant4 版本與產生指令），或取自 PDG 並經 hep-citations 記錄；有 Geant4 時以同一 dump 核對（`geant4_verify.py` 行 132 用的是 dump 的 `radiation_length_cm`）。
- 每條規則有單元測試（解碼後的參數、預算列、校正欄位）。

### C1.3 基因、解碼與有效性

§C.4.5 的基因、解碼器、有效性、修復與違反量。無效設計回傳原因（重疊、超出包絡、巢狀、範圍），不評估。解碼結果通過 `validate_artifact` 與 design.py 的候選檢查；去掉子系統的拓撲寫成獨立候選。

### C1.4 行程內的 F1 搜尋值

- 對每個目標，以 `run_evaluation` 相同的方式選出 F1 operation（`choose_operation`），以 `contracts/design.py` 從解碼後候選與分母重算引數（T-58），然後在同一行程中匯入工具腳本一次並呼叫其 `main(argv)`、擷取輸出 JSON；config 檔寫在暫存目錄。不另寫公式，所以常數與近似（例如 `tracker_resolution.py` 的 `PDG_MS = 0.016` 與 Highland 版本）就是 tool contract 的；工具的有效範圍外的點記錄 `in_domain: false`。
- 需要上游的 figure of merit（電荷誤判需要解析度）在行程內依鏈的順序計算。
- 不把公式移到 `core/`：`core/OWNERS.json` 的准入規則要求超過一個頂層使用者，而 `tracker_resolution.py` 與 `evaluate_design.py` 同屬 hep-detector。
- 一致性：抽樣的點（宣告數量，預設 20）與全部決選者在暫存副本中以 `run` 重算，數值相對差 ≤ 1e-12（C1.10）。

### C1.5 搜尋器

Sobol 初始化（Joe–Kuo 方向數，隨附所需維度的表）；NSGA-II（模擬二元交配 η_c = 15、多項式突變 η_m = 20，處理連續與整數基因，整數在突變後四捨五入；類別基因與 `parent_slot` 以均勻交配與隨機重設；槽位啟用位元以位元翻轉）；之後依 §C.4.5 修復，約束以違反量的 constrained-domination 處理；超體積以 WFG 精確計算。分布指數與突變機率寫入搜尋 spec。標準函式庫實作；同一種子結果逐位元相同。

### C1.6 `evaluate_design.py search` 與 `search_summary`

```
evaluate_design.py search --artifacts DIR --spec REL --id SEARCH-ID [--max-evaluations N] [--status LABEL]
```

讀目前的 design-spec 與搜尋 spec，執行 S0 之後的 S1 與 S3 的決選，寫出 `runs/SEARCH-*.computational-run.json`（§C.4.9）。不寫任何 design-candidate 或 evaluation；`--max-evaluations` 是安全上限（預設等於搜尋 spec 的預算）。CV-C1：`search_summary` 的 schema 與 `orphan_runs` 的豁免；閘控 `strict or _at_least(contract_version, CV-C1)`。

### C1.7 `expand --search`

```
evaluate_design.py expand --artifacts DIR --search REL --point K --candidate-id NAME
```

推廣既有的 `expand`（目前只讀 `scan_summary`，`evaluate_design.py:837-875`）：讀 `search_summary` 的點，以 §C.4.5 的解碼器寫出候選；只改參數或新增子系統時以 `derived_from` 指向基礎候選，去掉子系統時寫成獨立候選；輸入列出基礎候選（`binding: parameters`）與搜尋 run。`--point` 只接受決選者，其他點被拒（RSK-04）。回傳下一步的 `run`、`budget` 建議（`plan` 同樣列出）。

### C1.8 封閉測試

| 測試 | 已知答案 | 通過條件 |
|---|---|---|
| DTLZ2（3 目標，已知 Pareto 前緣；直接呼叫搜尋器） | 解析的前緣 | 2×10⁴ 次評估內超體積達到真值的 95 % 以上（`AID2E2024` 的封閉測試做法） |
| 平面配置（N = 6、臂長 L 固定、只有量測項、宣告最小間距 L/32） | 最佳 A = 47.66：1/32 格點上窮舉，不受格點限制的局部搜尋得到同一值（等距為 66.96；§C 附錄 A） | 搜尋器在最小間距 L/32 下找到 A ≤ 47.66 × 1.01 的配置 |
| 結構選擇（Example A 的 design-spec，基礎候選去掉磁鐵，槽位允許 `bending` 0–1 個） | 所有可行的搜尋前緣設計都含 `bending` 與 ≥ 3 層 `tracking`；無磁場的設計都不可行 | 前緣中無磁場的設計違反量 > 0；決選者 `expand` 後 `report` 對它們的判定與搜尋值的可行性一致 |
| 可重現 | — | 同一搜尋 spec 與種子，兩次執行的 `search_summary` 逐位元相同（時間戳除外） |
| 一致性 | 行程內 F1 = `run` 的 F1 | 抽樣點與決選者的相對差 ≤ 1e-12 |

### C1.9 文件與註冊

- `system-design-workflow.md` 新增「D2 automated candidate generation」一節：何時用 `search`（L2 的完整設計、參數或拓撲多於人工能比較的數量）、搜尋 spec 的寫法、搜尋值與 evaluation 的區別、`expand --search`、贏家詛咒與「不宣稱最佳」、Claude 的角色限制（§C.4.2）、報告時必須說明搜尋規模與確認狀態。
- `evaluate_design.py` 的 docstring 與 `--help`；`tools/check_wiring.py`；`tests/skills/test_cli_robustness.py` 的 `MISSING_FILE_ARGS`（`--spec` 讀檔）。
- 能力 `detector-design` 新增項目（例如 DSD-SEARCH）；capability matrix；路由案例集 DSD 加一個「自動產生候選」案例（沿用既有觸發詞，不改 description）。
- 不新增 reference，不修改 `SKILL.md`（§C.3 第 9 條）。

### C1.10 C1 驗收

- [ ] 搜尋 spec 的 schema 與跨欄位規則的測試；上限在 Python 中檢查且有測試；無效設計的每種原因都有測試。
- [ ] 角色規則的單元測試；解碼後的候選通過 `validate_artifact` 與 design.py 的候選檢查（含 `calibration` 與預算列）；去掉子系統的拓撲寫成獨立候選。
- [ ] 行程內 F1 與 `run` 的一致性測試（相對差 ≤ 1e-12）。
- [ ] C1.8 的封閉測試全部通過（閘門 G-C1；不通過不合併）。
- [ ] `search` 不寫任何 design-candidate 或 evaluation；`search_summary` 的 schema 測試；`orphan_runs` 對它豁免；以搜尋 run 為 `run_ref` 的 evaluation 被拒。
- [ ] `expand --search` 只接受決選者；展開的候選經 `run`、`budget`、`report` 處理，`report` 的判定與排序拒絕（缺預期精度時）照常出現。
- [ ] 一個獨立 agent 依 workflow 的新一節，從 Example A 的 design-spec 完成設計摘要、`search`、`expand`、正式評估與 `report`；回覆說明搜尋規模，不宣稱最佳。
- [ ] `check_layering.py --strict`、`check_packaging.py`、`check_wiring.py` 通過；既有的 design 測試（`tests/contracts/test_design_*.py`、`tests/skills/hep_detector/test_design_*.py`）不變地通過。
- [ ] VALIDATION DESIGN-SEARCH-F1；CHANGELOG；release manifest。

---

## §C.6 階段 C2：Geant4 搜尋值與 F4 確認（geant4 adapter 0.5.0、contracts CV-C2）

### C2.1 `core/` 的附加

依 §P.2 的 R1 與 R2（只附加、不改既有行為）：

| 附加 | 位置 | 內容 |
|---|---|---|
| 配對模式 | `core/stats/decisions.py`（`equivalence`、`change` 都接受 `pairing: paired`） | 兩點屬於同一 seed_group，K、B 相同；`absolute`：逐區塊差值 d_b = θ_a,b − θ_b,b，diff = d̄，se_diff = sd(d_b)/√K。`relative`：對要檢查的每個界限 r（TOST 的 ±tol、`change` 的 tol）構成 z_b = (θ_a,b − (1+r)θ_b,b)/b̄（b̄ 為 b 點的區塊平均），以 z̄ 與 sd(z_b)/√K 對 0 做單邊檢定（Fieller 型，b̄ 的不確定度不需忽略）。ν = K − 1；se 目標為 r = 0 時的 se ≤ tol/4。預設仍為 `independent` |
| `values` 累加器 | `core/simulation/summary.py` 與 `contracts/schemas` 中的 summary schema（`summary_version` 的 minor 增加）；`core/stats/batch_means.py` | 每個區塊通過選擇的原始值（依事件編號排序）；`values_max`（觀測量宣告，預設 10⁴）是每個區塊的上限，區塊的 `n` ≤ `values_max` 時寫出該區塊的值，任一區塊超過時該觀測量不使用經驗分位數並記錄；`merge` 規則 `concat`；有 `values` 時以經驗分位數（Hyndman–Fan 第 7 型，寫入 `quantile_method`）估計。理由：不同設計的解析度差很多，固定分格無法同時適合所有設計 |
| `values` 的 C++ 實作 | `g4sim/SimSummary.hh`；`element_sim` 與 `simreco` 寫出 | 和 Python 產生器一致（A2.9 的方法） |
| seed_group | `core/simulation/seeds.py` | Geant4 搜尋值：同一 seed_group 的 run 共用 S = H(search_id, "search", seed_group)；確認研究：S = H(search_id, "confirmation", design_sha256)。同一 seed_group 的 run K、B、`seeding` 相同，spec 雜湊互不相同；唯一性改為「(S, spec 雜湊) 不重複；S 只在宣告的 seed_group 內重複」 |

`core/stats/decisions.py` 只判定研究的閘門（收斂、variation、變更），不判定需求。

### C2.2 Geant4 搜尋值

`evaluate_design.py search` 的 `budget.geant4 > 0` 時，S2 的每個設計：在暫存目錄中解碼成候選 → 以 `design.geometry_fields` 產生 `design-geometry/1` → `geant4_run.py from-geometry`（B1）→ `geant4_run.py run`（`element_sim`）→ `reco`（`simreco`）→ summary；數值與 SE 寫入 `search_summary.points[].values`，S 寫入 `search_summary.seeds`。事件數固定（宣告），K = 16。批次執行經既有的 partition 與 batch 機制（hep-computing），以 §C.4.5 的快取鍵快取；重複的設計只評估一次。存活的親代在每一代的 seed_group 中重新評估，所以同一代內的比較全部配對；重新評估是新的評估（S 不同，不命中快取），計入預算。Geant4 搜尋 run 的 `extension.simulation.evidence_role` 為 `search`。

### C2.3 搜尋中的配對比較

- S2 的每一代宣告一個 seed_group；同一代的設計共用 S，選擇以配對模式的差值進行。
- **閘門 G-C2a：** 在第一次搜尋的 trial 中，量測差值的變異比 Var(獨立) / Var(配對)；比小於宣告值（預設 2）時，S2 改用獨立比較並在 `search_summary` 中註明。配對的估計在任何相關程度下都有效，只是增益可能很小（Geant4 中不同設計很快消耗不同的亂數）。

### C2.4 決選者的 F4 確認

- 決選者在任何確認之前依 S2 的搜尋值固定並寫入 `search_summary`（§C.4.8）；以 `expand --search` 成為候選。
- 每個決選者、每個（figure of merit, 分母）：`evaluate_design.py geometry` → F4 研究（S = H(search_id, "confirmation", design_sha256)，A1.9 的兩階段事件數，收斂閘門，B2 的 variation 與尾部來源）→ `check_geant4_study.py label --upgrade`（D0 的資格路徑）→ `evaluate_design.py f4`。每個候選只有一個 `geometry_ref`、`results.<fom>` 不分分母，所以每對各一份研究（B2）。
- D0 尚未核准時，確認研究照樣執行，但停在「升級被拒」；`report` 把它當作不合格的 F4（`f4_unqualified`），不得改寫成其他判定。
- `evaluate_design.py search --diagnose SEARCH-ID` 寫出一個診斷 run（`search_minus_official`：每個決選者的搜尋值減正式評估或 F4 值），不寫 evaluation、不影響判定。

### C2.5 防護與穩健性

確認研究的收斂閘門（production cut、最大步長、場精度；A1.8 與 D11）；variation（B2）；尾部來源誠實寫出（B2）；範圍外由 `label --upgrade` 與 `check_f4` 處理。穩健性依 §C.4.8：決選者容差內的 `scan` 與最差點的展開。

### C2.6 契約 CV-C2

- §C.4.9 的種子規則：evaluation 的 run 或研究的種子出現在任一 `search_summary.seeds` 中時是 `design.contract_mismatch`。
- `extension.simulation.evidence_role: search` 的 run 不能列為 `label --upgrade` 的證據（`check_geant4_study.py`）。
- seed_group 的唯一性規則（C2.1）。
- 閘控 `strict or _at_least(contract_version, CV-C2)`。

### C2.7 adapter 變更

| 項目 | 內容 |
|---|---|
| geant4 adapter | 0.4.0 → 0.5.0：`SimSummary.hh` 的 `values`；`element_sim` 與 `simreco` 依觀測量宣告寫出 `values`；`run` 接受 `--seed-group`；`SIM_SOURCES` 不變結構 |
| G5 | 新的 C++ 變更依 Geant4 API 撰寫；審查者在 VALIDATION 條目中確認 |

### C2.8 計算預算

F1 搜尋 2×10⁴ 個設計：分鐘級；Geant4 搜尋約 500 × 10³ 事件；確認 ≤ 5 個設計 × figure of merit 與分母的對數，事件數依 A1.9；量能器簇射主導 CPU。實際預算在 trial 後寫入搜尋 spec。

### C2.9 C2 驗收

- [ ] 配對模式的 toy：se_diff 名義 90 % 區間的覆蓋率 |覆蓋率 − 0.90| ≤ 0.02 + 3σ_MC；配對 `relative` 模式的 toy 在真實相對差等於 r 時拒絕的機率 ≤ 0.05 + 3σ_MC；trial 中量測的變異比已記錄（閘門 G-C2a）。
- [ ] `values` 累加器：Python 與 `SimSummary.hh` 一致；超過 `values_max` 時省略並記錄；經驗分位數有單元測試；舊的 summary（沒有 `values`）仍可讀。
- [ ] 解碼後候選經 `geometry` 與 `from-geometry` 產生的 `element_sim.spec/1` 以子行程通過 `geant4_run.py check-spec`（每個角色至少一例）。
- [ ] seed_group 與種子規則的契約測試：seed_group 外重複的 S、同一 seed_group 內相同的 spec 雜湊被拒；確認研究的 S 等於某個搜尋 run 的 S 時 `design.contract_mismatch`；`evidence_role: search` 的 run 不能作為升級證據。
- [ ] 快取以 `effective_digest`、層級、版本、程式雜湊與 S、N、K、B 為鍵；重複的設計只評估一次；存活的親代在每一代重新評估。
- [ ] 贏家詛咒的 toy：在純雜訊的設計集合上，搜尋值顯著偏樂觀，確認值無偏（閘門 G-C2b）。
- [ ] 一次完整的小型搜尋（C1.8 的結構選擇問題，含 Geant4 搜尋值）完成 S0–S4：決選者固定、展開、正式評估、F4 確認（D0 未核准時停在升級被拒並如實呈現）、`report` 與診斷 run。
- [ ] J14 在 `--strict` 下仍通過；B3 已合併時 J15 也是。
- [ ] VALIDATION DESIGN-SEARCH-G4；CHANGELOG；release manifest；§A.8 的檢查。

---

## §C.7 階段 C3：範例（J16）

### C3.1 J16：在 Example A 與 Example B 上自動產生候選

- **Example A**（`examples/design-space-spectrometer`，太空磁譜儀）：以它的 design-spec 與一個候選為基礎，搜尋層數、層位置與磁場；決選者展開後經 `report`，顯示 comparison basis 是否成立，以及缺少預期精度時排序與 Pareto 被拒；C2 已合併時對一個決選者做 F4 確認。
- **Example B**（`examples/design-collider-tracker`，對撞機徑跡＋ECAL）：搜尋徑跡與 ECAL 的參數；`capability.unavailable` 的需求（hadronic energy resolution、trigger efficiency、pileup robustness 等）照實帶到 `report`，證明搜尋與探測器種類無關。
- 兩者都是合成範例；README 說明展示的是流程，不是新的探測器設計（同 `AIDO2025`、`SWGO2023` 的定位）；和 J15（B3）的設計比較作為說明，例如平面向兩端與中央聚集提高 MDR，但多重散射主導區的解析度變差（§C 附錄 A）。

### C3.2 選用的貝氏最佳化後端

`adapters/design-bo/`（0.1.0）：Ax/BoTorch（qNEHVI），只在 S2 使用，限目標 ≤ 4、連續參數 ≤ 20；以延遲 import 載入，版本記錄在 `search_summary` 與 `adapter.json`（是否列為測試過的工具見 §P.7 的 MOBO 一項）；沒有安裝時退回 NSGA-II 並註明。以 DTLZ2 封閉測試比較兩者。

### C3.3 註冊與文件

`docs/researcher-journeys.md`（J16）、路由案例（`check_routing_static.py` 要求列入表的 journey 都有路由案例）、`tests/examples/test_design_search_j16.py`（由已提交的 `search_summary` 與 evaluation 重播並比對 `report`）、capability map、capability matrix、adapter 文件（若有 design-bo）；本任務的 Markdown 以 hep-authoring 的獨立審查流程審查（advisory）。

### C3.4 C3 驗收

- [ ] J16 在 Example A 與 B 上完成；`report` 含篩選、comparison basis、排序或其拒絕；回覆說明搜尋規模與確認狀態（閘門 G-C3）。
- [ ] J16 的離線重播（由已提交的紀錄）得到相同的 `report`。
- [ ] 貝氏最佳化後端（若安裝）通過 DTLZ2 封閉測試；未安裝時退回並註明。
- [ ] 註冊與文件完成；路由案例通過。
- [ ] VALIDATION DESIGN-SEARCH-EXAMPLES；CHANGELOG；release manifest；§A.8 的檢查。

---

## §C.8 契約與版本

| 物件 | 位置 | 版本 |
|---|---|---|
| `design-search-spec/1`、`search_summary`、`orphan_runs` 的豁免 | `contracts/schemas/`、`contracts/design.py` | CV-C1（minor、閘控；C1） |
| `search`、`expand --search`、角色規則、材料表、搜尋器 | `skills/hep-detector/` | 隨 plugin 版本（C1） |
| 配對模式、`values`、seed_group | `core/` | 隨 plugin 版本，`CORE_VERSION` minor 增加（C2）；summary schema 的 `summary_version` minor 增加 |
| `values` 的 C++ 實作、`--seed-group` | geant4 adapter | 0.5.0（C2） |
| 種子規則、`evidence_role: search` 的限制 | `contracts/design.py`、`check_geant4_study.py` | CV-C2（minor、閘控；C2） |
| 貝氏最佳化後端 | `adapters/design-bo/` | 0.1.0（C3，選用） |
| J16 | `examples/`、`docs/researcher-journeys.md` | 隨 plugin 版本（C3） |

所有 CV-* 的號碼在發布時依合併順序決定，都 ≥ 3.13.0。

---

## §C.9 不做與延後

| 項目 | 決定 | 理由 / 觸發條件 |
|---|---|---|
| 搜尋寫判定、排序、推薦設計或宣稱最佳 | 不做 | 由 design.py 推導（審查 C2、C3） |
| 讓 LLM 單獨決定設計 | 不做 | 沒有實際案例這樣做；判定必須可重現 |
| 選擇感知或多重比較的覆蓋率 | 延後，作為提案 | main 每個 figure of merit 用 `coverage_cl`，沒有多重比較修正；交給 hep-statistics 與 design.py 審查（審查 C12） |
| 以成本為目標 | 不做 | cost 沒有評估器（審查 C13）；觸發：main 加入 cost 的評估器 |
| 量能器深度的封閉測試 | 延後 | 舊的「深度 ≥ 16 X₀」不是適足表的 figure of merit；shower-containment 在 F4 以下是 `capability.unavailable`；觸發：B2 的 shower-containment F4 可用 |
| 可微分模擬與可微分代理模型（MODE 路線） | 延後 | Geant4 不可微；可微分代理模型對點雲尺度仍不成熟（`MODE2023`）。觸發：一個連續參數 > 20 的問題，且 Geant4 搜尋預算不足 |
| Geant4 搜尋值的圓柱與非盒狀幾何 | 延後 | `element_sim` 只有盒狀元件。觸發：新的幾何種類與 realizer（§R 的擴充點） |
| Cherenkov、RICH、TRD 的 Geant4 搜尋值 | 延後 | 需要光學物理與專用重建；F1（`cherenkov_angle`）的搜尋可以做 |
| 強化學習、大型神經網路代理模型 | 延後 | 資料量與可解釋性；NSGA-II 與 MOBO 對 ≤ 數十個參數已足夠 |
| 真實成本與質量資料庫 | 不附 | 由使用者以候選的預算列提供並附來源 |

---

## §C.10 待決事項與殘餘風險

**待決事項**（編號見 §P.7）：D0（F4 資格路徑，擋 C2 的確認升級）；MOBO 後端是否列為測試過的工具；以搜尋 run 為 `run_ref` 的代碼沿用 `design.scan_point_not_expanded` 或新增 `design.search_point_not_expanded`（CV-C1 時決定）；`results` 是否以分母為鍵、是否允許多個 `geometry_ref`（B2 向維護者提出；影響 C2.4 的研究數）。

**殘餘風險：**
1. F1 工具的偏差（多半 optimistic）可能讓結構搜尋錯過好的拓撲；以 S2 的拓撲多樣性與 `search_minus_official` 緩解，但不能排除。
2. 模擬最佳化的設計可能利用 Geant4 在未驗證區的行為；收斂閘門、variation 與 F4 資格只能部分防護。
3. 角色規則的預算模型很粗；沒有使用者的預算列時，預算目標只是示意。
4. 目標超過 4 個時搜尋前緣難以解讀；design-spec 應把其餘目標寫成約束。
5. Claude 的設計摘要可能帶入「已知儀器」的偏見；以 Sobol 隨機設計與拓撲多樣性抵銷，並在 `search_summary` 中區分 LLM 與隨機提案。
6. 配對比較在 Geant4 中的變異縮減可能很小（閘門 G-C2a）。
7. 計算量：量能器的 Geant4 搜尋值與確認成本高；預算在 trial 後調整。
8. main 的設計流程變動快（0.37.0 到 0.38.0 只隔一天）；`evaluate_design.py`、`contracts/design.py` 的 rebase 衝突要預留時間（§P.8）。
9. 本部的參考資料中，GRACE、VI-BRATO 是 2026 年的預印本，結論尚未經同儕審查。

---

## §C.11 建議的執行步驟

每個階段開始時依 §P.10.2 建立並確認該階段的 isolated worktree，所有步驟都在其中進行；合併後依 §P.10.5 移除。

**C1（以 main 為基底；可與任務 A、B 平行）**
1. 開始前檢查；搜尋 spec 的 schema（C1.1）；角色規則與材料表（C1.2）。
2. 基因、解碼與有效性（C1.3）；行程內 F1 與一致性測試（C1.4）。
3. 搜尋器（C1.5）與 DTLZ2、平面配置的封閉測試。
4. `search` 與 `search_summary`（C1.6）；`expand --search`（C1.7）；其餘封閉測試；文件與註冊（C1.9）；獨立 agent 驗收；C1.10。

**C2（B2 與 C1 合併後）**
1. `core/` 的附加（C2.1）及其 toy。
2. Geant4 搜尋值（C2.2）；配對比較的 trial（C2.3）。
3. F4 確認（C2.4，依 D0 的狀態）；防護與穩健性（C2.5）；CV-C2（C2.6）；adapter 變更（C2.7）；C2.9。

**C3（C2 合併後）**
1. J16 在 Example A、B（C3.1）；選用的貝氏最佳化後端（C3.2）。
2. 註冊與文件（C3.3）；C3.4。

---

## §C 附錄 A：數值

**平面配置的封閉測試**（曲率變異 σ_k² = A σ² / L⁴，N = 6，等權重，只有量測項；精確有理數最小平方；計算程式見本資料夾的 `design_search_closure.py`）：

| 配置 | A | 相對等距的 MDR |
|---|---|---|
| 等距（J15） | 66.96 | 1 |
| 兩端與中央各 2 片（重合） | 48.00 | 1.181 |
| 2/3/1 片聚集於 0、1/2、1（重合） | 45.33 | 1.215 |
| 2/3/1 片聚集，中央聚集移到 0.465（1/1000 掃描的最佳） | 44.77 | 1.223 |
| 1/16 臂長格點上窮舉的最佳（平面不重合，最小間距 L/16） | 50.34（0, 3/8, 7/16, 1/2, 9/16, 1） | 1.153 |
| 1/32 臂長格點上窮舉的最佳（最小間距 L/32；封閉測試的答案） | 47.66（0, 1/32, 7/16, 15/32, 1/2, 1） | 1.185 |
| 大 N 的漸近極限（N/4、N/2、N/4 聚集於 0、1/2、1；N = 6 時無法以整數片數達到） | 256/N = 42.67 | 1.253 |

重合的聚集配置不受最小間距限制，所以不是封閉測試的答案，只用來說明趨勢。J15 的 MDR 1172 GV 在 1/32 格點的最佳配置下約為 1389 GV；但聚集的配置在多重散射主導區較差，這正是 J16 要讓搜尋處理的取捨。封閉測試以 `tracker_resolution` 的 F1 解析度為目標、物質設為 0（只有量測項）時，解析度 ∝ √A，所以最佳配置與上表相同。

## §C 附錄 B：出處

- `Cisbani2020`：E. Cisbani et al., "AI-optimized detector design for the future Electron-Ion Collider: the dual-radiator RICH case", JINST 15 (2020) P05009, [arXiv:1911.05797](https://arxiv.org/abs/1911.05797)
- `AID2E2024`：AID(2)E collaboration, "AI-Assisted Detector Design for the EIC (AID(2)E)", [arXiv:2405.16279](https://arxiv.org/abs/2405.16279)
- `MODE2022`、`MODE2023`：MODE collaboration, "Toward the end-to-end optimization of particle physics instruments with differentiable programming", [arXiv:2203.13818](https://arxiv.org/abs/2203.13818)；"Progress in end-to-end optimization of detectors for fundamental physics with differentiable programming", [arXiv:2310.05673](https://arxiv.org/abs/2310.05673)
- `AIDO2025`：Schmidt et al.（MODE），"End-to-end detector optimization with diffusion models: a case study in sampling calorimeters", [arXiv:2502.02152](https://arxiv.org/abs/2502.02152)
- `Borysov2024`：O. Borysov et al., "Longitudinal structure optimization for a high density electromagnetic calorimeter", [EPJ Web Conf. 315, 03006 (2024)](https://www.epj-conferences.org/10.1051/epjconf/202431503006)
- `SWGO2023`：T. Dorigo et al., "Toward the end-to-end optimization of the SWGO array layout", [arXiv:2310.01857](https://arxiv.org/abs/2310.01857)
- `GRACE2026`：J. Hill, H. J. Ryoo, "GRACE: an agentic AI for particle physics experiment design and simulation", [arXiv:2602.15039](https://arxiv.org/abs/2602.15039)（預印本）
- `VIBRATO2026`：W. Chung et al., "Agentic-AI detector co-design and optimization in vertically-integrated differentiable full simulations", [arXiv:2604.21804](https://arxiv.org/abs/2604.21804)（預印本）
- 以上於 2026-10-23 取得；citation key 是本文件的暫定名稱，作者與期刊資訊在引用前需經 hep-citations 核對

## §C 附錄 C：版本歷程

| 版本 | 內容 |
|---|---|
| 2026-10-23 | 初版提案：三個角色、需求規格、元件目錄與設計文法、F0/F1/F2 多保真度、搜尋與確認分開、契約、C1/C2、J16；之後依任務 A 的重新審視引用 `core/` 的共用模組 |
| 2026-10-23 | 依計畫（第 1 部）重新整理：三個階段；`threshold`、`order`、配對比較、`values`、search 角色與 seed_group 由 C2.1 加入；實現以 `check-spec` 驗證；契約版本記為 CV3；J16 與 MOBO 移到 C3 |
| 2026-10-23 | 加入 isolated worktree 的執行規定（§P.10） |
| 2026-10-23 | 詳細檢查後的修正：schema 關鍵字限制；`order` 的雙邊界限；配對 `relative` 模式；快取鍵；親代重新評估；設計去重；材料表；基因的修復與違反量；封閉測試的最小間距；citation key；`values_max` 每區塊 |
| **2026-10-24（本版）** | **依 main 0.38.0 的探測器系統設計流程重新規劃（審查紀錄 `review-2026-10-24-main-0.38.md` 的 C1–C13、P2–P4）：任務 C 改為 D2 的候選產生器 `evaluate_design.py search`；刪除需求規格、元件目錄與設計文法的格式、`realize()`、`threshold`／`order`、推薦設計與自訂 Pareto、adapter `detector-design`、reference 與 `SKILL.md` 一行；保真度改用 main 的 F0–F5（舊 F0 = F1，Geant4 搜尋值沒有保真度，確認 = F4）；搜尋族群存在 `search_summary`（CV-C1），只展開決選者；行程內 F1 呼叫 tool contract 的同一工具；C2 的種子規則（CV-C2）取代角色規則；C1 不再依賴任務 A；J16 改在 Example A、B 上執行；貝氏最佳化後端改為選用的 `adapters/design-bo/`；新增概念對應表（§C.4.3）** |

---

# 第 5 部　設計理由（§R）

> 基準：hep-research `main` 的 `5584927`（0.38.0），contracts 3.12.0，adapter geant4 0.1.0，Geant4 11.4.3；§R.1–§R.14 的程式事實多半查自 `9f08796`，相關檔案（Geant4 adapter、`check_geant4_study.py`、`geant4_benchmarks.py`）到 0.38.0 未變
> 日期：2026-10-22（2026-10-23 依詳細檢查修正；2026-10-24 對齊重新規劃）
> 注意：本部原寫於 2026-10-23 與 2026-10-24 兩次重新規劃之前；2026-10-24 只修改與 main 設計流程衝突的部分，並新增 §R.15。其餘段落若和第 1–4 部衝突，以第 1–4 部為準並回報。

---

## §R.0 摘要

**目的。** 讓 hep-research 裡的模擬研究（目前是 Geant4）做到三件事：結果不會被錯誤地標成 `validated-in-scope`；數值與判定可重現、可追溯；研究層不綁死在某一個模擬程式、某一種幾何或某一類研究上。

**設計的出發點。** 大型實驗已經解決過同樣的問題，只是規模大得多。本架構只取它們經過時間考驗、而且在 plugin 的限制與本計畫的選擇下（新模組刻意只用標準函式庫、以獨立執行檔交換 JSON/CSV、最小變動）做得到的做法：

| 問題 | 實際實驗的做法 | 本架構 |
|---|---|---|
| 平行執行下的可重現性 | ATLAS 每個事件依事件與 run 編號重設亂數；Allpix² 依事件編號給種子，「worker 數不同仍可重現」 | 每個事件以 H(邏輯 run 種子, 事件編號) 重設亂數；工作切分與執行緒數不影響事件內容（§R.5） |
| 大量平行工作的結果合併 | CMS DQM：工作各自填直方圖，harvesting 步驟合併後才做品質判定 | 模擬程式寫出可合併的 run summary；Python 只在合併後推論與判定（§R.4） |
| 設定與處理鏈的追溯 | CMS 以參數集的雜湊與 process history 記錄每個處理步驟 | 每個步驟的設定雜湊、輸入雜湊與程式雜湊寫入紀錄；多層鏈可遞移追溯（§R.7） |
| 支援多個模擬引擎 | ALICE 的 Virtual MC 在使用者程式與引擎之間加隔離層，但幾何分離多年仍在進行 | 不在 API 層抽象化；在**輸出**層抽象化：任何後端交出三個邊界產物即可（§R.3） |
| 不同元件共用資料 | Key4hep 以 EDM4hep 作為元件間的共同資料模型，舊工具以轉換接入 | 邊界產物就是共同資料模型；其他框架以縮減工具轉換接入（§R.3.4） |
| 模擬是否可信 | Geant4 以 geant-val 對實驗數據做跨版本比較；CMS 先用試束數據選 physics list，再用碰撞數據檢查；ATLAS 快速模擬以 Geant4 為參考 | 五種驗證類別，各有自己的參考、統計方法與可否升級的規則（§R.6） |
| 軟體改版是否改變結果 | Belle II 每晚執行驗證腳本、跨版本比較並可二分搜尋造成退化的提交；geant-val 每月執行 | 回歸類別：和前一版比較，只偵測改變，不升級（§R.6.5） |
| 資料量分層 | ATLAS：HITS → RDO → AOD；只保留下游需要的層級 | 四層資料：事件細節（不提交）→ 逐事件摘要 → run summary → 判定紀錄（§R.4.1） |

**架構的核心（六句話）：**
1. **兩個平面。** 逐事件的處理在 C++（資料平面：模擬、數位化、重建）；合併後的推論、判定、紀錄與契約在 Python（控制平面）。
2. **輸出層的後端介面。** 任何後端交出 run summary、column map、effective config（含實際幾何樹）三個邊界產物，就能進入閘門、benchmark 與 label。
3. **事件決定性。** 事件內容只由邏輯 run 種子與事件編號決定；工作切分、執行緒數、執行順序都不影響。
4. **可重現的定義是「判定相同」。** 重播時判定與 label 必須完全相同，數值在相對差 1e-9 內；接近門檻的判定會被標記。來源檔案以雜湊追溯。同一平台重新執行時事件逐位元相同；跨平台（libm 不同）只要求浮點累加量相對差 ≤ 1e-12。
5. **一種變異數方法。** run summary 依事件編號分成 K 個區塊；SE 一律以區塊的 batch means 估計，計數很少時用精確區間。
6. **驗證分成五類。** verification、物理參考、配置對應的量測、回歸、模型對模型；只有物理參考與配置對應的量測能升級，而且條件由契約從證據重新推導。

**階段：** 八個階段（A1、A2、B1、B2、B3、C1、C2、C3）的順序、內容與版本見 §P.0 與 §P.3；§R.10 只列一句話的指向。

**與 main 的設計流程。** main 0.37.0 起有探測器系統設計流程（design-spec、design-candidate、design-evaluation；判定由 `contracts/design.py` 推導；保真度 F0–F5，Geant4 研究是 F4）。本計畫的分工是：任務 A 讓 F4 依賴的標籤正確；任務 B 提供能跑磁譜儀的 Geant4 應用與 F4 研究紀錄介面；任務 C 是 D2 階段的候選產生器，不寫判定、不排序。理由見 §R.15。

---

## §R.1 設計依據：從實際實驗學到的事

本節每一點都附出處（§R.14）。「取用」是本架構採用的部分；「不取用」是刻意不做的部分與理由。

### §R.1.1 亂數與可重現性

- **ATLAS（AthenaMT）：** 不同用途的亂數流以使用它的演算法名稱區分；每個事件依事件與 run 編號重設亂數狀態；目標是「亂數序列必須和事件的處理順序無關」。
- **Allpix²：** 主執行緒依事件建立順序從中央種子產生器給每個事件種子；worker 執行前才設定；設計目標是「即使 worker 數不同，相同輸入仍得到相同結果」。需要依序輸出的模組以緩衝佇列等待，並保存亂數狀態。
- **CMS：** 另一種做法：每個模組、每個 stream 一個亂數引擎，並可把引擎狀態存進事件，之後還原以精確重播。
- **取用：** ATLAS 與 Allpix² 的逐事件重設種子。它最簡單，而且讓「把一個邏輯 run 切成多個工作」與「單一工作」產生完全相同的事件。**不取用：** CMS 的狀態保存（需要在每個事件保存引擎狀態，對我們的規模不必要）。

### §R.1.2 結果合併與判定的位置

- **CMS DQM：** 資料被切成任意多個工作、亂序且大量平行地處理；每個工作填 MonitorElement（主要是直方圖）；harvesting 步驟合併各檔案中相同的直方圖，之後才在單執行緒中依序做品質測試與衍生量。
- **取用：** 模擬程式只填「可合併的累加量」（計數、和、直方圖）；所有判定在合併之後、在 Python 中進行。這就是 run summary 與控制平面的分工。

### §R.1.3 追溯

- **CMS：** 以參數集的雜湊識別設定，並以 process history 記錄資料經過的每個處理步驟。
- **取用：** 每個步驟（模擬、數位化、重建、表格）都寫一份紀錄，含設定、輸入、程式的雜湊；simulated 表格的輸入鏈可以任意深，契約遞移地檢查（§R.7.4）。

### §R.1.4 多引擎

- **ALICE Virtual MC：** 在使用者程式與傳輸引擎之間加一層隔離，讓幾何與 hit 產生的程式只寫一次；當時 Geant3 用於生產，Geant4 只用於物理驗證，FLUKA 尚未完成，幾何與傳輸的分離仍在進行。
- **ATLAS AtlFast3：** 依粒子種類與能量把工作分給 Geant4、FastCaloSim V2、FastCaloGAN；快速模擬以「重建後和 Geant4 無可分辨的差異」來驗證。
- **取用：** 在**輸出**層抽象化，而不是在 stepping API 層：後端怎麼模擬都可以，只要交出相同的邊界產物。混合多個模擬器的後端，在 effective config 中描述其分派方式。快速模擬與 ML 代理模型以 Geant4 為參考時，屬於「模型對模型」驗證（§R.6.5）。**不取用：** 寫一個 VMC 式的引擎抽象層（ALICE 的經驗顯示成本高、週期長）。

### §R.1.5 共同資料模型與幾何

- **Key4hep：** Gaudi 處理框架、DD4hep 幾何、EDM4hep（以 podio 建立）資料模型；EDM4hep 是元件之間在記憶體與檔案中的交換格式；舊的 iLCSoft 處理器在進出時和 EDM4hep 互相轉換，不必改寫。
- **取用：** 邊界產物就是我們的共同資料模型；外部框架以「縮減工具」轉換接入（例如把 EDM4hep 檔縮減成 run summary）。幾何以後端的實際幾何（as-built）為準。**不取用：** Gaudi、DD4hep 作為依賴（plugin 的限制）。
- **GDML：** Geant4 能把實際幾何寫成 GDML，但需要建置時開啟 GDML；本 plugin 的建置是 `GEANT4_USE_GDML: OFF`（`geant4_build.py` 行 53）。所以實際幾何由探針自行走訪（§R.3.3）；使用者的建置有 GDML 時可另外附上。

### §R.1.6 驗證

- **geant-val（Geant4 合作組）：** 社群的驗證測試每月以開發版執行，結果存入資料庫，跨版本比較，並對分布做 χ² 與 KS 檢定。
- **CMS：** 先以試束數據調校並選定 physics list，再以碰撞數據中的孤立帶電粒子檢查量能器的響應與解析度；在多個 Geant4 版本之間比較後才採用，並在速度與準確度之間取捨。
- **Belle II：** 每個軟體套件都有驗證腳本產生直方圖；每晚集中執行、跨版本比較，並有工具二分搜尋造成退化的提交。
- **取用：** 把「驗證」分成性質不同的五類（§R.6）：精確推論的 verification；孤立目標對物理模型的參考（geant-val 的薄靶測試屬此類）；和同一配置量測的比較（CMS 的試束）；跨版本回歸（Belle II、geant-val 的每月比較）；模型對模型（ATLAS 快速模擬）。

### §R.1.7 資料分層

- **ATLAS：** 模擬輸出 HITS 檔；數位化輸出 RDO（概念上類似探測器的原始數據）；重建輸出 AOD。
- **取用：** 四層資料，各有保存規則（§R.4.1）。

### §R.1.8 實際儀器（J15 的對照）

- **PAMELA：** 0.43 T 永久磁鐵；6 片雙面矽微條平面，解析度優於 4 µm；MDR 超過 1 TV；三個 TOF 平面（S1–S3，分割成 paddle）；鎢／矽成像量能器 16.3 X₀、0.6 λ；另有反符合、S4 與中子偵測器。
- **AMS-02：** TOF 四個平面（8、8、10、8 個計數器）；系統對質子約 140 ps。
- **取用：** J15（0.5 T、6 片 Si、MDR 約 1.17 TV、每站兩層 TOF、18.4 X₀ 量能器）和 PAMELA 幾乎同型，可作為合理性的對照；TOF 每層 100 ps 比 AMS-02 樂觀，所以 J15 對 σ_t 做 100 與 150 ps 的敏感度掃描（B3，§B.7）。J15 仍是合成幾何，不代表任何實驗。

---

## §R.2 目標、限制與原則

### §R.2.1 目標

| 目標 | 由什麼保證 |
|---|---|
| `validated-in-scope` 不能被錯誤取得 | 契約從證據重新推導的事實（§R.7） |
| 判定可重現、數值可追溯 | 事件決定性（§R.5.1）、合併後推論（§R.4）、判定相同的重現定義（§R.5.6）、每個步驟的雜湊（§R.7.4） |
| 研究層不綁死後端、幾何或研究類型 | 輸出層的後端介面（§R.3） |
| 示範磁場、多子系統與重建 | J15（B1、B2、B3） |

### §R.2.2 限制

- 本計畫新增的 Python 模組只用標準函式庫。這是刻意的選擇，不是 plugin 的限制：main 的 `core/` 允許 numpy、scipy（`docs/architecture.md` §3）；本計畫的計算不需要它們，而且讓 J14 的離線重播不多一層依賴。唯一例外是 C3 的選用後端 `adapters/design-bo/`（延遲匯入）。
- G5 授權邊界：Python 只和獨立執行檔交換 JSON 與 CSV；不複製 Geant4 範例程式碼。
- 分層：skill 腳本與 adapter 只 import `core`、`contracts`；兩者都要用的程式（統計、判定、種子雜湊、summary 讀取）因此放在 `core/stats/` 與 `core/simulation/`（§A.3 第 1 條、§A.4.5）；`skills/`、`contracts/` 不出現實驗名稱（實驗名稱可以出現在 `docs/` 與 `examples/`）。
- 狀態與退出碼（`core/status.py`）：0 ok、1 負向判定、2 `rejected`、3 `incomplete`。
- 檔案 ≤ 2 MiB；hep-detector quick load ≤ 25,600 bytes（目前 24,669）、description ≤ 1,024 字元（`measure_entrypoints.py` 回報 1,016）。`SKILL.md` 與 description 不改；設計流程的入口已由 main 以 hub 連結提供（OQ-01），任務 C 只在 `system-design-workflow.md` 加一節。
- J14 的離線重播必須永遠可以執行，不需要 Geant4 與編譯器。

### §R.2.3 原則

1. **正確性先於擴充。** A1 合併前，不合併任何新功能。
2. **逐事件在 C++，合併後在 Python。** 處理逐事件資料的程式在資料平面；處理合併後累加量的程式在控制平面。同一個量只有一份正式實作；另一種語言的實作只能在測試中作為 oracle。
3. **在輸出層抽象化。** 研究層只認邊界產物，不認後端的欄名、spec 格式或 UI 指令。
4. **相信實際狀態，宣告只是退路。** 幾何、場與物理設定以探針讀到的為準；只有宣告時標記 `source: declared`，不能升級。
5. **可升級的事實由契約認定。** 等級、kind、範圍維度、configuration、目標雜湊都不得由紀錄自行宣告。
6. **驗證類別依參考的性質決定**（§R.6）。
7. **事件決定性。** 事件內容只由邏輯 run 種子與事件編號決定。
8. **重現的是判定。** 數值以容差比較，判定必須相同；來源以雜湊追溯。
9. **證據的停止規則、格點與區塊數事先宣告。** 加跑、加密、重做控制組都不得依結果決定。
10. **介面可擴充，實作只做眼前需要。** 不做通用運算式語言，不做外掛系統，不做引擎抽象層。
11. **先找現有實作；最小變動。**

---

## §R.3 架構總覽

### §R.3.1 兩個平面與元件

```
控制平面（Python，標準函式庫）
  hep-detector      規則、參考公式、推論（batch means、精確區間、MPV、IUT、negative control、分布比較）、研究層的判定、label；
                    evaluate_design.py search（C1、C2：D2 的候選產生器；需求判定與比較由 contracts/design.py 推導）
  adapters/geant4   spec 驗證、建置、執行、工作切分、紀錄（trace.provenance()）、simulated 表格；
                    A1 由逐事件 CSV 產生 run summary（A2 起只在測試中作為 oracle）；
                    from-geometry（B1：design-geometry/1 → element_sim.spec/1）
  adapters/design-bo  （C3，選用）Ax／BoTorch 的貝氏最佳化後端，延遲匯入
  core              trace、status；stats/（區塊估計量、精確區間、判定引擎、分布函式）；
                    simulation/（種子雜湊、summary 的計算與讀取；schema 在 contracts/schemas/）
  contracts         驗證類別與等級表、範圍、configuration 與隔離（CV-A1）；新類別、遞移的處理鏈、F4 研究紀錄欄位、
                    幾何對照表 1.1.0（CV-B2）；search_summary（CV-C1）；搜尋種子不得作為確認（CV-C2）；
                    design.py 推導需求判定（main 既有）
        ▲
        │  三個邊界產物（JSON；小、可提交、可雜湊）
        │    run summary        simulation-summary/1    （§R.4）
        │    column map         simulation-columns/1    （§R.3.5）
        │    effective config   引擎無關外框 + 實際幾何樹 （§R.3.3）
        │
資料平面（C++）
  g4sim/         共用 Geant4 輔助程式庫（標頭檔）：
                      SimHash.hh     sha256 與種子雜湊 H（和 core/simulation/seeds.py 一致）
                      SimSeed.hh     逐事件種子 H(邏輯 run 種子, 事件編號)
                      SimSummary.hh  區塊累加器、合併、JSON 寫出（只依賴標準函式庫）
                      MiniJson.hh    最小 JSON 讀寫（simreco 也使用）
                      SimProbe.hh    探針：設定與實際幾何樹（依賴 Geant4）
                      材料、physics list 選擇、CSV 寫出
  layered_sim       既有的平板程式；spec/1 不變；加上 g4sim
  element_sim       （B1）通用的盒狀元件程式：巢狀、場、平面穿越、逐事件 ROOT 檔
  simroot           （B1）只連結 Geant4 的 analysis 函式庫：ROOT 檔的 info / dump / hash
  simreco           （B2）不連結 Geant4：數位化與重建，輸出 run summary 與逐事件結果
  其他後端           使用者的 Geant4 應用（引入 g4sim）、其他引擎或框架（以縮減工具轉換）
```

| 元件 | 語言 | 階段 | 依賴 |
|---|---|---|---|
| 契約 | Python | A1（CV-A1）、B2（CV-B2）、C1（CV-C1）、C2（CV-C2） | — |
| 推論與研究層判定（`core/stats/`、`core/simulation/`） | Python | A1；B2、C2 附加 | — |
| `evaluate_design.py search`（hep-detector） | Python | C1、C2 | `core`、`contracts`；F1 的 tool contract；C2 以子行程呼叫 `geant4_run.py` |
| `adapters/design-bo/`（選用） | Python | C3 | Ax／BoTorch（延遲匯入） |
| run summary 的 Python 產生器（由逐事件 CSV） | Python | A1；A2 起只作為 oracle | — |
| `g4sim`（`SimHash.hh`、`SimSeed.hh`、`SimSummary.hh`、`MiniJson.hh`、`SimProbe.hh`、輔助） | C++ | A2 | Geant4（`SimHash.hh`、`SimSummary.hh`、`MiniJson.hh` 只依賴標準函式庫） |
| `layered_sim` | C++ | 既有；A2 加 `g4sim` | Geant4 |
| `element_sim` | C++ | B1 | Geant4、`g4sim` |
| `simroot` | C++ | B1 | Geant4 analysis（g4tools） |
| `simreco` | C++ | B2 | 標準函式庫、`SimSummary.hh`、`MiniJson.hh` |

### §R.3.2 後端

| 後端 | 用途 | 幾何 | 狀態 |
|---|---|---|---|
| `layered_sim` | 材料層級的平板研究（J14） | spec/1：沿 x 的平板堆疊 | 既有；A2 後只做維護與 `g4sim` 整合，不再加幾何功能 |
| `element_sim` | 探測器層級的研究（J15 起） | 盒狀元件、一層巢狀、場區 | B1 新增；之後的幾何功能都加在這裡 |
| 使用者的 Geant4 應用 | 實驗組自己的幾何 | 任意（含 GDML） | 引入 `g4sim` 即可交出邊界產物 |
| 其他引擎或框架 | FLUKA、快速模擬、ML 代理模型、Key4hep 等 | 任意 | 以縮減工具把其輸出轉成邊界產物；探針只有宣告（`source: declared`）時不能升級 |

**為什麼新增 `element_sim` 而不是改造 `layered_sim`。** 把 `layered_sim` 改成新的幾何格式，需要 spec 轉換與同主機逐位元相同的驗證，還要永久維護雙格式存取器；這是上一版成本最高、價值最低的一步（§R.13）。新增一個程式則讓 J14 的程式完全不動，並從第一天就有兩個真正的後端驗證輸出層介面。兩者共用 `g4sim`，避免重複。

### §R.3.3 effective config

```
{ "engine": "geant4", "engine_version": "11.4.3", "probe_version": "...",
  "backend": {"name": "element_sim", "version": "...", "sources_sha256": "..."},
  "source": "probe" | "declared", "recorded": true, "config_sha256": "...",
  "seeding": {"mode": "per-event" | "stream", "logical_run_seed": ...},
  "geometry": { "tree": [...], "tree_sha256": "...", "hash_scheme": "tree-v1", "gdml_sha256": null },
  "environment_ref": "<build 紀錄的雜湊>",
  "sections": { "geant4": { ... } } }
```

| 部分 | 內容 |
|---|---|
| 外框 | 與引擎無關；規則依 `engine` 選擇規則包（目前只有 Geant4 的 `G4R-*`） |
| `geometry.tree` | 由 `G4PhysicalVolumeStore`（依建立順序的平面清單）與各體積的母邏輯體積重建樹；每個放置記錄名稱、copy number、solid 類型與參數、材料（Geant4 解析後的組成與密度）、轉換矩陣、母體、附加的 field manager 與參數；數值以 Python `float.hex()` 格式。replica 與 parameterised 體積記錄其參數化描述 |
| GDML | 使用者的建置開啟 GDML 時，可另附 `G4GDMLParser` 寫出的檔案與其雜湊；不作為必要條件 |
| `sections.geant4` | `G4EmParameters::StreamInfo` 全文與解析欄位；逐 couple 的 cut 與能量閾值；逐 process、逐模型的能量範圍；run manager 型別；`G4UserLimits`、biasing |
| 資料集 | 路徑與內容雜湊只在 build 紀錄中計算一次；探針以 `environment_ref` 引用 |
| 時機 | master 的 `BeginOfRunAction`（`RunInitialization` 之後）、`G4State_GeomClosed` 且 couple 數大於 0；否則 `recorded: false`，該 run 不能升級 |
| 場 | field manager 逐執行緒；master 也呼叫 `ConstructSDandField`，所以 `g4sim` 的後端在 master 看得到場；宣告了場而 master 看不到時，標記 `source: declared` |
| 混合模擬器 | 後端若依粒子或區域分派給不同模擬器，在 `sections` 中描述分派規則 |

### §R.3.4 縮減工具（外部後端的接入點）

不能引入 `g4sim` 的後端（其他引擎、Key4hep 的 EDM4hep 檔、ML 代理模型）以一個有紀錄的縮減步驟接入：讀它的逐事件輸出，依 `output.observables` 的宣告寫出 run summary 與 column map；effective config 只有宣告。這個步驟本身是一份 computational-run 紀錄，列在處理鏈中（§R.7.4）。第一個縮減工具 `simreduce` 讀 `simroot dump` 的輸出（B1 之後、第一個需要時實作）。

### §R.3.5 column map（`simulation-columns/1`）

每個觀測量與輸出欄的語意名稱、實際欄名、單位、操作定義、所在檔案（`csv`、`root` 的哪個 ntuple、`summary`）；附 `column_map_version`。只允許宣告式運算（改名、單位換算、加總、篩選）；需要計算的轉換是另一個有紀錄的步驟。

---

## §R.4 資料分層與 run summary

### §R.4.1 四層資料

| 層 | 內容 | 對應 | 保存 |
|---|---|---|---|
| T1 事件細節 | ROOT 檔：逐體積沉積、平面穿越、逐步 hit | ATLAS 的 HITS | 不提交；紀錄保存路徑、檔案雜湊、內容雜湊、各 ntuple 列數 |
| T2 逐事件摘要 | CSV：主粒子真值、各子系統總沉積、宣告的觀測量 | 縮減的事件表 | benchmark run 提交縮減欄位版本；其餘不提交 |
| T3 run summary | `simulation-summary/1`：依事件區塊的可合併累加量 | CMS DQM 的 MonitorElement | 全部提交（每個 run 數 kB） |
| T4 判定紀錄 | study record、benchmark 結果、label | — | 全部提交 |

J14 的離線重播只需要 T3 與 T4；T2 只用於可選的 oracle 測試與 MPV 的高統計核對。

### §R.4.2 run summary（`simulation-summary/1`）

每個工作（job）一份 JSON。

| 欄位 | 內容 |
|---|---|
| `run` | 邏輯 run 的識別與種子、這個工作涵蓋的事件編號範圍、`seeding`、區塊大小 B 與區塊數 K、spec 與 effective config 的雜湊、產生者（`layered_sim`、`element_sim`、`simreco`、`python-csv`、縮減工具）與版本 |
| `observables[]` | 每個宣告的觀測量：語意名稱（對應 column map）、單位、累加器 |
| 區塊 | 事件依編號分入區塊：區塊 b 涵蓋事件 [b·B, (b+1)·B)；每個區塊有自己的一組累加器 |
| 累加器 | 整數：`n`、直方圖每格的計數（宣告的固定分格；溢位與下溢分開）、`count_if[]`（x > 宣告門檻的事件數）；浮點：Σx、Σx²、`min`、`max`，以 Neumaier 補償加總；C2 起可有 `values`（每個區塊保存原始值，供經驗分位數，超過 `values_max` 時省略並記錄）；`profile` 與二維直方圖只定義介面（§R.9.2） |
| `merge` | 每個累加器的合併規則（`sum`、`min`、`max`、`hist`）；同一個邏輯 run 的多個工作依區塊編號合併 |

**事件權重。** `layered_sim` 的沉積已經乘上 track 權重，CSV 的 `weight` 欄只是主粒子頂點的權重。為避免重複加權，目前要求事件權重為 1（否則 exit 2）；加權累加的語意與 biasing 的規則延後（§R.9.3）。

**數值精度。** 整數累加量（計數、直方圖、`count_if`）精確。浮點和以補償加總計算；不同工作切分或執行緒數下，合併順序不同，只造成約 1e-15 的相對差異，遠小於重現的容差（§R.5.6）。

---

## §R.5 執行、種子、區塊與重現

### §R.5.1 邏輯 run 與事件決定性

- 一個**邏輯 run** 由 spec、後端與邏輯 run 種子 S 決定，含 N 個事件，編號 0 … N−1。
- `seeding: per-event`（新 spec 的預設）：事件 i 在開始時以 H(S, i) 重設亂數。所以：
  - 把邏輯 run 切成任意多個工作（各自涵蓋一段事件編號），得到的事件和單一工作完全相同；
  - serial 與任何執行緒數的 MT，事件內容相同。
- `seeding: stream`：舊行為（serial 為連續亂數流；MT 由 master 分批產生每事件種子）。只用於 J14 既有的 spec，讓 A2 的回歸檢查可以要求 CSV 逐位元相同。
- 種子：S = H(study_id, role, point_id)，映射到 [1, 2³¹)；evidence 角色在 A1 為 trial、nominal、scan、control、variation、calibration，B2 加入 regression，C2 加入 confirmation 與 search 角色；正負兩個方向的控制組用不同的 point_id。同一研究中 S 不得重複，唯一的例外是 C2 的 seed_group：同一組的 run 刻意共用 S，以配對比較降低差值的變異（§C.6 C2.1、C2.3）。設計評估的 S 定義見 §C。

### §R.5.2 區塊與 batch means

- 區塊大小 B 與區塊數 K（K ≥ 16）在第一個證據 run 前宣告；N = K·B。
- 每個區塊 b 由 summary 算出估計量 θ_b（平均、比例、比值、分位數、眾數）；回報 θ̄ = 平均；SE = sd(θ_b)/√K，自由度 K − 1。
- 區塊是同一個 run 中不重疊的事件範圍。事件彼此獨立（`per-event` 時由種子保證；`stream` 時是 Monte Carlo 的標準假設），所以區塊估計量彼此獨立。
- 一個 run 就足以估計 SE，不需要為統計開多個行程；工作切分只為了平行化。
- 前提：事件之間沒有狀態（例如會自我調整的 biasing、跨事件的快取）。探針記錄 biasing 與相關設定，有疑慮時改為多個獨立的邏輯 run。

### §R.5.3 估計量

- **多個觀測量：** 每個區塊的估計量向量一起保存，觀測量之間的共變異由這些向量估計。
- **全樣本值：** 平均與比例另由合併累加器算出，和 θ̄ 的差寫入紀錄作為診斷。
- **分位數：** 直方圖內線性內插；分格寬度須小於容許值的 1/10；落在溢位或下溢格時判為 incomplete。C2 起有 `values` 累加器時，改用區塊內的經驗分位數。
- **MPV：** 每個區塊的直方圖取最大格，以它和相鄰兩格做三點拋物線內插；回報 K 個眾數的平均。設計時以 toy 證明偏差的 95 % 上界 ≤ tol/10（toy 用 Landau–Vavilov，並以一次高統計 Geant4 run 的形狀核對）；每次執行時，θ̄ 與合併直方圖的眾數之差須 ≤ tol/5 + 2·SE，否則該 benchmark 判為 incomplete。

### §R.5.4 計數很少時

- 計數型估計量在任一區塊為 0、或合併總數 < 100（門檻可宣告）時，改用合併累加器上的精確區間：比例用 Clopper–Pearson，計數用 Garwood；兩個 run 的比較用精確條件二項法求率之比的區間，相對差 = 比 − 1。
- 這些情況沒有 SE；閘門以區間端點判定（§R.6.6），事件數規劃用試探 run 的 Poisson 變異數。

### §R.5.5 兩階段事件數

N = ceil(N_trial·(SE_trial/target)²·f)，f = F₀.₉₀(K − 1, K_trial − 1)（兩者都是 16 時 ≈ 1.97）。約 10 % 的證據 run 會未達標而判為 incomplete，不得補跑；改用 F₀.₉₅（≈ 2.40）可降到約 5 %，事件數多約 22 %。

### §R.5.6 重現的定義

| 層次 | 要求 |
|---|---|
| 追溯 | 每份紀錄保存 spec、effective config、程式（`sources_sha256`）、種子、輸入與輸出檔案的雜湊 |
| 重新執行 | 同一建置與平台、同一邏輯 run，事件內容逐位元相同，summary 的整數累加量相同；跨平台（libm 的 log、cos 等不保證逐位元相同）浮點累加量相對差 ≤ 1e-12，建置使用 `-ffp-contract=off` |
| 重播（由已提交的 T3、T4） | 判定與 label 完全相同；數值相對差 ≤ 1e-9；任何判定的邊距 < 1e-9（相對）時，在紀錄中標記「接近門檻」 |
| 回歸檢查（A2） | J14 的既有 spec（`seeding: stream`）在同一主機上產生和 A2 前逐位元相同的 CSV；只新增檔案，不改原有輸出 |

---

## §R.6 驗證類別與判定

### §R.6.1 五種類別

| 類別 | 參考 | 例子 | 統計 | 能否升級 |
|---|---|---|---|---|
| verification | 輸入的精確推論 | charged geantino 對解析螺旋、運動學、最小平方代數 | 確定性比較或 IUT | 不能 |
| 物理參考（reference） | Geant4 所近似的物理模型或已發表的薄靶量測，在孤立目標上 | Bethe stopping power、Landau–Vavilov MPV、geant-val 式的薄靶測試 | IUT（純量）；χ²（分布，§R.9.2） | 能（範圍內） |
| 配置對應的量測（setup-matched） | 已發表的量測，且目標雜湊和量測配置相同 | 試束的縱向剖面、模組的響應與解析度 | 同上，加量測不確定度 | 能（範圍內） |
| 回歸（regression） | 同一研究在前一個軟體或 Geant4 版本的結果 | 改版前後的 MPV、直方圖形狀 | 純量的差值與 SE；直方圖的 χ² p 值 | 不能；只標記「改變」並可觸發 advisory |
| 模型對模型（surrogate） | 以 Geant4 等完整模擬為參考的快速模擬或 ML 代理模型 | 參數化量能器對 Geant4 | IUT 或 χ² | 不能升級物理 label；代理模型自己可得到「在範圍內與參考模擬一致」的標記。2026-10-24 起延後，不在 CV-B2（設計情境中的快速模擬由 main 的保真度與 bound 表示） |

另有 `sanity`（粗略的合理範圍檢查）與 `interface`（介面檢查），兩者都不能升級。

### §R.6.2 benchmark 表（CV-A1，CV-B2 擴充）

`contracts/validate.py` 自帶表格；`_study_upgrade` 只從表取得類別、等級、kind 與範圍維度。

| benchmark | 類別 | 支持的 kind | 範圍維度 |
|---|---|---|---|
| `stopping-power` | reference | `stopping-power` | particle、material、energy、thickness |
| `range` | reference | `range` | particle、material、energy、thickness |
| `thin-layer-mpv` | reference | `most-probable-value` | particle、material、energy、thickness |
| `thin-layer-width` | sanity | `thin-layer-width` | particle、material、energy、thickness |
| `multiple-scattering` | sanity | — | — |
| `em-shower-shape` | sanity | — | — |
| `shower-containment` | sanity | — | — |
| `longitudinal-profile` | setup-matched | `shower-maximum` | particle、energy、目標雜湊 |
| `published-data` | interface | — | — |
| CV-B2 加入：J15 的檢查（`field-propagation` 等） | verification 或 sanity | — | — |
| CV-B2 加入：`regression-comparison` | regression | — | — |
| CV-B2 加入：徑跡的 reference benchmark（孤立 Si 片的多重散射角寬度，對照 PDG Highland／Lynch–Dahl，附負對照；F4 資格路徑的第 iv 項，§R.15.5） | reference | 見 §B | 剛度、粒子（另見 §B） |
| 延後：`surrogate-comparison` | surrogate | — | — |

`regression-comparison` 的範圍取被比較的兩個研究範圍的交集，由 `dependencies.py` 重新推導（§B 的 CV-B2 表為準）。

紀錄中的類別或等級和表不一致、或名稱不在表中，判為 error。`geant4_benchmarks.py` 的 `GRADES` 保留給工具，以測試確保一致。

### §R.6.3 範圍（CV-A1）

- 比對受控的 `observable.kind`；`label` 把它寫入 `declared_scope.observable_kind`。
- 維度清單依 benchmark 宣告（6.2 的第四欄），每個維度有型別：類別或數值區間；純量視為 [v, v]。新用例加維度只改表格。
- 宣告範圍缺少 benchmark 有的維度，視為超出範圍。
- 以目標雜湊為維度時，宣告範圍必須帶相同的 `target_geometry_sha256` 與 `hash_scheme`。
- 閘控：`strict or _at_least(contract_version, CV-A1)`，無 warning 分支。

### §R.6.4 configuration 與隔離（CV-A1）

- **目標：** benchmark 設定宣告 `target_slabs`（A1，`layered_sim`）或目標體積清單（A2 起，對應幾何樹的放置）。
- **真空：** 世界材料為 `G4_Galactic`，或密度 < 1e-20 g/cm³。
- **isolated：** 世界是真空，世界以外的每個放置都屬於目標；只附加在目標內的場屬於目標並計入雜湊；延伸到目標以外的場使其成為 embedded。
- **推導與雜湊版本：**

| 階段 | 推導自 | `hash_scheme` |
|---|---|---|
| A1 | `layered_sim` 的 spec/1（對 `layered_sim` 而言 spec 就是實際幾何；A2 以幾何樹核對） | `spec-v1` |
| A2 起 | effective config 的幾何樹（任何後端） | `tree-v1` |

- 比對只在相同的 `hash_scheme` 之間進行；`dependencies.py` 依紀錄中的 `hash_scheme` 重新推導。J14 不使用目標雜湊維度，不受版本切換影響。
- 只有宣告的後端可以執行與發布，但不能升級。
- **契約規則：** 每個被計入的 benchmark 必須是 isolated（reference），或既是 isolated 又和量測配置的目標雜湊相符（setup-matched）；`dependencies.py` 必須從 `evidence_records` 中的 run record 重新推導並比對。

### §R.6.5 回歸與模型對模型（CV-B2）

- **回歸：** 對同一研究、同一設定，在新舊兩個版本（plugin、後端或 Geant4）上各執行一次（point_id 為版本標籤，樣本獨立），比較每個純量觀測量。三種判定：`changed`（|diff| − t_{1−α/m}·se_diff > tol）、`unchanged`（§R.6.6 的通過規則）、`unresolved`；「不顯著」不等於「沒有改變」。直方圖的比較延後到分布層級的 benchmark。不影響 label；reference 觀測量 `changed` 時可觸發 sci-fix 的檢查。
- **模型對模型（2026-10-24 起延後）：** 代理模型永遠不改變物理 label。代理模型的研究宣告它的參考研究（study record）與範圍；以 IUT 判定（χ² 只作診斷）。通過時記錄 `extension.study.surrogate`（參考研究的引用與雜湊、範圍取兩者的交集）。

### §R.6.6 收斂閘門（IUT）

- **差值：** a 為最細的設定，b 為第二細的設定；`relative` 模式 diff = (a − b)/b、se_diff = √(se_a² + se_b²)/|b|，`absolute` 模式 diff = a − b、se_diff = √(se_a² + se_b²)（兩個點是獨立的邏輯 run）；ν 以 Welch 公式逐對計算。C2 起可宣告配對模式（`pairing: paired`）：兩點屬於同一 seed_group、K 與 B 相同，以逐區塊差值估計 se_diff，ν = K − 1（定義見 §C.6 C2.1）；預設仍為獨立。
- **事件數目標：** 每個點的 se 目標為 tol/(4√2)，使 se_diff ≤ tol/4。
- **判定：** 通過：|diff| + t₀.₉₅(ν)·se_diff ≤ tol，且兩點都達到 se 目標；失敗（未達標也可判）：|diff| − t_{1−α/m}(ν)·se_diff > tol，m 為（參數 × 觀測量）組數；其他為 unresolved。計數很少時改用區間端點：通過 = 90 % 區間落在 [−tol, tol] 內；失敗 = 單邊 1 − α/m 區間完全落在外側。
- **回報：** unresolved 與未達標以 `incomplete`（exit 3）回報，label 保持 `unvalidated`；只有失敗是 `failed`（exit 1）。

**操作特性**（α = 0.05，2×10⁶ 次模擬；以本資料夾的 `gate_operating_characteristics.py` 重算；模型見任務 A 的 A1.8）：

| 真實差值 | 通過（se = 目標） | 通過（兩階段） | 通過（兩階段，兩點都達標的條件下） | 失敗 m = 1（se = 目標） | 失敗 m = 30（se = 目標） | 失敗 m = 30（兩階段） |
|---|---|---|---|---|---|---|
| 0 | 0.976 | 0.809 | 0.999 | 0.000 | 0.000 | 0.000 |
| tol/2 | 0.621 | 0.696 | 0.860 | 0.000 | 0.000 | 0.000 |
| tol | 0.050 | 0.044 | 0.054 | 0.050 | 0.002 | 0.002 |
| 2 tol | 0.000 | 0.000 | 0.000 | 0.988 | 0.780 | 0.952 |

真實差值為 tol 時約 90 % 是 unresolved，這是等價檢定的本質。兩階段設計下約 19 % 的點對有一點未達標而不完整。2026-10-23 的獨立審查發現舊版的兩階段欄重複計入試探的 χ²，已重算。

### §R.6.7 negative control 與偵測極限

- 判定量：shift = (control − nominal)/reference，SE 由兩個 run 合成。
- 偵測極限：DL = tol + |rel| + t_{0.977}(ν)·se_rel。
- caught：控制組的 benchmark 判定為失敗（|rel_c| > tol）。
- 設計要求：toy 證明在 DL 注入時抓到的機率 ≥ 0.977；真實檢定力在 0.977 附近，所以驗收門檻為 0.977 − 3σ_MC（A1 的驗收條件）。
- 實現：正負兩個方向都注入（否則宣稱限縮為單向）；位於偵測極限 = caught 且 |shift| ≤ 1.1 × DL。單次未抓到時記錄並說明，不自動失敗，不得換種子重跑。

### §R.6.8 停止規則與證據相關性

- 停止規則、掃描格點、K 與 B、unresolved 的處理在第一個證據 run 前寫入 study spec。
- `extension.study.evidence_overlap` 列出被多個判定共用的 run。

---

## §R.7 契約、追溯與 sci-fix

### §R.7.1 CV-A1（A1）

§R.6.2–6.4 的表格、範圍與隔離規則；`dependencies.py` 的重新推導；`ext_computational_run.json` 加入選用的 `simulation` 屬性（需 hep-computing 同意；欄位見 §A）。`study` 仍是開放物件，讓 B2 加入 F4 需要的欄位。

### §R.7.2 CV-B2（B2）

§R.6.2 的新條目（verification、`regression-comparison`、徑跡的 reference benchmark）；§R.6.5 的回歸規則；§R.7.4 的遞移處理鏈；F4 研究紀錄的 `results`、`tail_sources_simulated` 與計數型 figure of merit 的不對稱不確定度；`design_geometry.json` 1.1.0。閘控方式同 CV-A1。CV-C1（C1）加入 `search_summary`；CV-C2（C2）加入一條 `design.py` 規則：run 或研究的種子出現在搜尋摘要中的 evaluation 判為 `design.contract_mismatch`；見 §C。

### §R.7.3 sci-fix 與 advisory（A1）

缺陷 D1–D11 的修正依 main 目前的帳本格式記錄（`docs/maintenance.md`）：一筆只修一件事（例如變異數方法拆成 batch-means SE、精確低計數區間、MPV 估計三筆）；S1 有封閉形式時附 C4 與逐筆審查簽核；S3 放在 `documentation_fixes`。advisory 採 `/2` 格式，以 `applies_to.match` 群組比對；範圍包含錯誤升級的研究紀錄，以及建立在它們之上的 F4 design-evaluation（§R.15.5）。條目、等級與 advisory 編號以 §A 的 A1.14 為準。

### §R.7.4 處理鏈的追溯

- 每個處理步驟（模擬、縮減、數位化與重建、表格）寫一份 computational-run 紀錄，含 `**trace.provenance()`、設定雜湊、輸入紀錄與檔案的雜湊、程式雜湊。
- simulated 表格的輸入鏈可以任意深，只要每一層都是有紀錄的 computational-run，而且鏈的每個根都是模擬 run（CV-B2；以前只允許一層）。
- 呼叫 C++ 執行檔時，Python 記錄執行檔與原始碼的 sha256、版本與子命令，並以 `trace.tag()` 標記。

---

## §R.8 程式與 CI

| 位置 | 變更 |
|---|---|
| `contracts/validate.py`、`dependencies.py` | §R.6、§R.7 |
| `contracts/schema.py` | `maxItems`、`maximum`、`exclusiveMaximum`（A2.7 加入；`element_sim` 的 schema 需要；不升契約版本） |
| `core/stats/`、`core/simulation/` | 區塊估計量、研究層的判定引擎（A1 的 `equivalence`、`detection_limit`；B2 的 `change`；C2 的配對模式）、分布函式、種子雜湊、summary 的讀取。放在 `core/` 是因為 hep-detector 的腳本與 geant4 adapter 都要用，而分層規則只允許 adapter import `core` 與 `contracts`（§A.3 第 1 條、§A.4.5）；`core/` 只能 import `core`，所以 summary 的 schema 放在 `contracts/schemas/`，由腳本以 `contracts.schema` 驗證。重用 main 既有的函式（Garwood 區間、`toy_ensemble`），不重寫 |
| `skills/hep-detector/scripts/` | 推論與判定只讀邊界產物；幾何事實（最小厚度、configuration）從 effective config 讀取，A2 前的紀錄仍從 spec/1 讀取；`check_geant4_study.py label` 寫出 F4 欄位（B2）；`evaluate_design.py` 加 `search` 子命令（C1）並修正 `f4` 的 `--label-run-record` 轉傳與結束碼（A1）；不新增腳本；`SKILL.md` 與 description 不改 |
| `contracts/design.py`、`contracts/rules/design_geometry.json` | F4 的計數型不確定度與對照表 1.1.0（B2）；`search_summary` 的孤兒規則豁免（C1）；搜尋種子規則（C2） |
| `adapters/geant4/assets/` | `g4sim/`；`layered_sim/` 加入 `g4sim`；`geant4_run.py`（邏輯 run 與工作切分、A1 的 Python summary 產生器、B1 的 `from-geometry`、B2 的 `reco` 與 `table`）；B1 `element_sim/` 與 `simroot`；B2 `simreco` |
| `adapters/design-bo/` | C3 的選用後端（Ax／BoTorch）；本計畫唯一可能新增的 adapter |
| `SIM_SOURCES` | 涵蓋 `g4sim` 與各程式的原始碼 |
| CI | 任務 A 不需要新的必要 CI 工作；`SimSummary.hh` 的 ctest 可作為選用工作。B2 的 `simreco` 的 C++17 CI 工作是否必要由維護者決定（§P.7 第 9 項，建議必要） |

---

## §R.9 通用性

### §R.9.1 涵蓋的用例

| 用例 | 由什麼支援 | 狀態 |
|---|---|---|
| 材料層級的參考（J14 類） | reference 類別、孤立平板 | A1 |
| 有場的磁譜儀（J15，對照 PAMELA、AMS-02） | `element_sim`、場計入目標、verification、重建鏈、F4 研究紀錄介面 | B1、B2、B3 |
| 自動化探測器設計（J16） | `evaluate_design.py search`（D2 候選產生器）、以新種子做 F4 確認；需求判定與比較由 `contracts/design.py` | C1–C3 |
| 試束或模組（和數據比較） | setup-matched 類別、幾何樹推導的目標雜湊、依 benchmark 宣告的範圍維度 | 契約在 A1、A2；幾何用使用者應用或 `element_sim` |
| 稀有事件 | 精確計數區間 | A1 |
| 軟體或 Geant4 改版 | regression 類別 | B2 |
| 快速模擬、ML 代理模型 | surrogate 類別、縮減工具 | 延後（2026-10-24 移出 B2）；縮減工具在第一個需要時 |
| 其他引擎或框架（FLUKA、Key4hep） | 輸出層介面、縮減工具 | 介面已備；轉換工具延後 |

### §R.9.2 現在只定義介面的項目

| 介面 | 內容 | 第一個用例 |
|---|---|---|
| 分布層級的比較 | 以 summary 的直方圖做 χ²（兩邊都有統計不確定度；參考是量測時加量測不確定度） | 第一個以形狀為觀測量的 benchmark，或第一個回歸檢查 |
| 觀測量的組合與選擇 | 欄位的線性組合、兩欄之比；欄位與常數比較的 AND 選擇 | 第一個需要事件選擇的研究 |
| profile 與二維直方圖 | 依 x 分格的 n、Σy、Σy²；二維計數 | 第一個能譜源研究；J15 以固定剛度執行，不需要 |
| 粒子源 | `gps`（只允許宣告式設定）、`event-file`；summary 記錄通量歸一化所需的源面積與立體角 | 第一個能譜或通量研究 |
| `simreduce` | 讀事件檔（經 `simroot`）或外部格式，依宣告輸出 summary | 第一個事後才決定的觀測量，或第一個外部後端 |

### §R.9.3 延後（附觸發條件）

| 項目 | 觸發條件 |
|---|---|
| 加權累加與 biasing 規則 | 第一個使用 biasing 的研究 |
| `element_sim` 的非盒狀 solid、旋轉、GDML 讀入 | 第一個需要它們、又不能用使用者應用的研究 |
| 其他引擎的規則包與探針 | 第一個非 Geant4 的後端 |
| EDM4hep 的縮減工具 | 第一個 Key4hep 後端 |
| 光學光子、長時間窗、衰變鏈 | 第一個閃爍體或稀有事件研究 |
| 離子源與 Birks | 宇宙線核素研究，且 PVT 的 Birks 常數有文獻紀錄 |
| 多個 Geant4 版本的探針 | 第一個使用 11.4 以外版本的應用（regression 類別會先用到） |
| `physics_config_comparison` | 需要比較物理設定的研究 |
| RNTuple、vector 欄 | ROOT 檔大小或讀取速度成為瓶頸 |

### §R.9.4 刻意不做

- 引擎抽象層（VMC 式）：在輸出層抽象化已足夠，ALICE 的經驗顯示 API 層抽象的成本高。
- 處理框架（Gaudi 式）、驗證資料庫與網站（geant-val 式）：它們解決大型合作組的規模問題，違反 plugin 的限制。
- 通用運算式語言、估計量的外掛系統、跨引擎的統一探針內容。
- 整數量化與逐位元相同的統計量（§R.13）。
- 依結果加跑、加密、換種子重跑控制組。
- `uses-validated-physics` label、contracts 4.0、Python 綁定、內容定址快取、`simstat`、不連結 Geant4 的 `simcore`。
- 自己的需求規格、需求判定、候選排序或「推薦設計」，以及任何全域最佳的宣稱：這些屬於 main 的 `contracts/design.py` 與人工閘門（§R.15.2、§R.15.3）。

---

## §R.10 階段與驗收

本節在 2026-10-23 以前複製了各階段的內容與驗收，容易和任務規格不一致，因此改為指向。階段的順序、內容邊界、介面擁有權、閘門與待決事項以 第 1 部 為準；每個階段的工作項與驗收以任務規格為準。

| 階段 | 一句話 | 規格 |
|---|---|---|
| A1 | 修正錯誤發出 `validated-in-scope` 的缺陷；統計與 summary 的共用模組放進 `core/`（contracts CV-A1） | §A.5 |
| A2 | `g4sim`、`per-event` 種子、`layered_sim` 寫出三個邊界產物、研究層只讀邊界產物 | §A.6 |
| B1 | `element_sim`、場、平面穿越、量能器漏失、逐事件 ROOT 檔、`simroot`、`check-spec` | §B.5 |
| B2 | `simreco`、尾部來源、處理鏈、verification／regression、F4 研究紀錄介面與資格路徑（contracts CV-B2） | §B.6 |
| B3 | J15 作為設計專案：F1、F2 與每個（figure of merit, 分母）的 F4 | §B.7 |
| C1 | `evaluate_design.py search`：以 main 的 F1 在行程內搜尋，寫 `search_summary`，`expand` 決選者；封閉測試（contracts CV-C1） | §C.5 |
| C2 | Geant4 搜尋值、配對比較、以新種子做 F4 確認（contracts CV-C2） | §C.6 |
| C3 | J16：Example A 與 B 上的搜尋範例、選用的 `adapters/design-bo/` | §C.7 |

---

## §R.11 殘餘風險

1. J14 的偵測極限可能因區塊 batch means、t 分位數與觀測量單位的控制組而改變，需要重新設計控制組。
2. 區塊 batch means 對偏斜分布的比值、分位數與眾數有 O(1/B) 的偏差，不隨 K 減少；覆蓋率 toy 容許 ±0.02，必要時加大 B。
3. 區塊獨立的前提在事件之間有狀態時不成立；探針記錄相關設定，有疑慮時改為多個獨立的邏輯 run。
4. 兩階段設計下約 10 % 的證據 run 未達標（§R.5.5）。
5. 以容差比較時，接近門檻的判定在不同平台可能不同；以邊距標記與「CI 平台為準」處理。
6. 兩個 Geant4 程式：`layered_sim` 凍結於維護模式，靠 `g4sim` 控制重複。
7. 探針假設 worker 與 master 設定相同；若發現 thread-local 差異，改為逐執行緒傾印。
8. 以目標雜湊對應已發表量測時，契約只能比對雜湊，無法判定目標就是論文中的配置；仍需審查者核對。
9. `G4RootAnalysisReader` 的讀取能力未驗證（B1 的試作）。
10. quick load 只剩 931 bytes；本架構不改 `SKILL.md` 與 description（設計流程的入口由 main 的 hub 連結提供）。
11. 工作量：原型估計 A1 的契約部分約 8–12 個工作天，另加 Geant4 執行時間；其餘未估計。
12. 偵測器層級的 F4 資格路徑（§R.15.5）未經維護者核准前，J15 與任務 C 的確認研究只能是 `unvalidated`，design.py 不會把它們算作 F4。

---

## §R.12 決策紀錄

### §R.12.1 使用者已決定

| 日期 | 決定 | 位置 |
|---|---|---|
| 2026-10-22 | 核心程式用 C++，Python 作為介面；計算核心用 C++、參考值留在 Python；以獨立執行檔交換 JSON/CSV，不用 Python 綁定 | 原則 2（依 12.2 第 1 項的詮釋） |
| 2026-10-22 | J15 的 TOF1、TOF2 各兩層，四層同材料 | §B |
| 2026-10-22 | 詳細的逐事件資訊存成 ROOT 檔 | §R.4.1 T1、B1 |
| 2026-10-22 | J15 與其他部分拆成兩個任務，J15 後做 | 任務 A（A1、A2）、任務 B（B1、B2、B3）；之後加入任務 C（§P.0） |
| 2026-10-24 | 全面重寫以接上 main 的設計流程；任務 C 的搜尋做成 `evaluate_design.py search`；偵測器層級的 Geant4 研究經資格路徑成為 F4 | §R.15、§P.0 |

### §R.12.2 本部的提議（需要使用者確認）

1. **語言分工的詮釋：** 逐事件的計算（模擬、數位化、重建、累加）在 C++；合併後的推論在 Python。
2. **輸出層的後端介面**（三個邊界產物），不做引擎抽象層。
3. **事件決定性：** 新 spec 預設 `seeding: per-event`；工作切分與執行緒數不影響事件。
4. **重現的定義是「判定相同」**，數值以容差比較；不做整數量化與逐位元相同的統計量。
5. **區塊 batch means：** 一個 run 內依事件編號分 K ≥ 16 個區塊；J14 有逐事件資料的 run 離線重算，不重錄。
6. **新增 `element_sim`**，`layered_sim` 不改 spec 格式；兩者共用 `g4sim`。
7. **五種驗證類別**，其中 regression 在 CV-B2（B2）加入；surrogate 延後。
8. **八個階段**（A1、A2、B1、B2、B3、C1、C2、C3；§P.0），ROOT 檔與 `simroot` 在 B1。
9. 兩階段係數用 F₀.₉₀ 或 F₀.₉₅；精確區間的切換門檻（任一區塊為 0 或總數 < 100）。

### §R.12.3 待維護者決定

合併後的清單與建議見 §P.7；本部原有的七項都已併入該清單。

---

## §R.13 演進紀錄：被取代的設計

| 前一版的設計 | 取代為 | 依據 |
|---|---|---|
| `simstat` 與不連結 Geant4 的 `simcore`：把逐 run 的統計搬到 C++ | 推論留在 Python，讀合併後的 summary | 程式與資料量小，C++ 無收益，且使重播需要編譯器（合理性評估 P1）；CMS DQM 也在合併後才判定 |
| spec/2、`layered_sim convert`、雙格式存取器、同主機逐位元相同的閘門 | `layered_sim` 不改格式；新增 `element_sim` | 成本最高、價值最低；新增程式讓 J14 不動，並得到真正的第二後端 |
| 整數量化、雙字組 128 位元整數、五成雙捨入、`%.17g` 才能重算 | 浮點補償加總；整數只用於計數與直方圖；重現定義為判定相同 | 逐位元相同不是科學需求；實際實驗追求可重現的事件與可追溯的來源 |
| 每個證據 run 16 個獨立行程 | 一個 run 內依事件編號分區塊 | batch means 本來就是 run 內分批；逐事件種子讓工作切分與統計無關 |
| 強制逐事件種子只為了逐位元相同 | 逐事件種子作為新 spec 的預設，目的是事件決定性 | ATLAS、Allpix² 的做法 |
| 只檢查介面的合成後端 | `element_sim` 是真正的第二後端 | 第三次檢查 R19 |
| 驗證只有等級（reference、sanity、verification、interface） | 五種驗證類別，加入 regression 與 surrogate | geant-val、Belle II、ATLAS AtlFast3 |
| 任務 C 自己的需求規格 `detector-requirements/1`、元件目錄與設計格式 `detector-design/1` | main 的 design-spec 與 design-candidate；基因組只是最佳化器的內部編碼，解碼成基礎候選的 `overrides` | main 0.37.0 已有這些產物（2026-10-24 審查 C4、C5） |
| 任務 C 的保真度 F0、F1、F2 | main 的 F0–F5：舊 F0 是 main 的 F1；搜尋中的短 Geant4 run 只是搜尋值；確認是 F4 | 名稱衝突（審查 P2） |
| 任務 C 的需求判定（`threshold`）、`order`、自訂 Pareto 與「推薦設計」 | `contracts/design.py` 推導判定、篩選、排序與 Pareto；不宣稱最佳 | main 的規則（審查 C2、C3） |
| `realize()`：設計 → spec | `evaluate_design.py geometry` 產生 `design-geometry/1`，B1 的 `from-geometry` 推導 `element_sim.spec/1` | main 已有幾何產生步驟（審查 C6、B4） |
| `adapters/detector-design/` 與其版本序列 | `evaluate_design.py search`；只有選用的貝氏最佳化後端是 adapter | adapter 是連接外部工具的選用元件（審查 P3） |
| B2 為任務 C 加入的 surrogate 類別 | 延後 | 設計情境中的快速模擬由 main 的保真度與 bound 表示（審查 B 的重新規劃） |

仍然有效的前一版內容（已併入本部）：缺陷 D1–D10 的修正、契約的等級表與依 benchmark 宣告的範圍維度、隔離與場的定義、目標雜湊的版本、IUT 閘門與 t 分位數的操作特性、精確計數區間、MPV 的內插與兩道偏差檢查、t 分位數的偵測極限、兩階段事件數、事件權重的限制、探針的內容與時機、ROOT 檔的設計、J15 的設計。第三次深度檢查的 25 項發現中，R11、R12、R16、R18 因設計改變而不再適用，R19 由 `element_sim` 解決，其餘都已併入。

---

## §R.14 出處

- ATLAS Collaboration, *Software and computing for Run 3 of the ATLAS experiment at the LHC*, [arXiv:2404.06335](https://arxiv.org/pdf/2404.06335)（亂數：§R.3.1；資料格式：§R.2.3）
- ATLAS Collaboration, *AtlFast3: the next generation of fast simulation in ATLAS*, [arXiv:2109.02551](https://ar5iv.labs.arxiv.org/html/2109.02551)
- CMSSW `RandomNumberGenerator.h`（[LXR](https://cmssdt.cern.ch/lxr/source/FWCore/Utilities/interface/RandomNumberGenerator.h)）；DQM `README.md`（[LXR](https://cmssdt.cern.ch/lxr/source/DQMServices/Core/README.md)）；`ProcessHistory`（[doxygen](https://cmsdoxygen.web.cern.ch/cmsdoxygen/CMSSW_12_3_2/doc/html/d8/d42/ProcessHistory_8cc_source.html)）
- S. Banerjee, V. Ivanchenko (CMS), *Validation of physics models of Geant4 using data from the CMS experiment*, [EPJ Web Conf. CHEP 2021](https://www.epj-conferences.org/articles/epjconf/abs/2021/05/epjconf_chep2021_03010/epjconf_chep2021_03010.html)
- *Simulation in ALICE*（Virtual MC），[physics/0306092](https://ar5iv.labs.arxiv.org/html/physics/0306092)
- Key4hep, *Progress Report on Integrations*, [arXiv:2312.08152](https://arxiv.org/html/2312.08152v1)
- Allpix², [multithreading 文件](https://allpix-squared.docs.cern.ch/docs/04_framework/10_multithreading)；[arXiv:1806.05813](https://arxiv.org/pdf/1806.05813)
- *Geant-val: a web application for validation of detector simulations*, [EPJ Web Conf. CHEP 2018](https://www.epj-conferences.org/articles/epjconf/abs/2019/19/epjconf_chep2018_05002/epjconf_chep2018_05002.html)
- Belle II, *Tools for Physics Validation of the Software*（[basf2 文件](https://software.belle2.org/release-09-00-15/sphinx/_sources/validation/doc/index.rst)）
- *The PAMELA Space Experiment*, [arXiv:0905.2551](https://ar5iv.arxiv.org/html/0905.2551)
- *The AMS-02 Time of Flight System*, [astro-ph/0206021](https://ar5iv.labs.arxiv.org/html/astro-ph/0206021)
- hep-research `9f08796`：`adapters/geant4/assets/geant4_build.py`（行 53，`GEANT4_USE_GDML: OFF`）、`layered_sim/Actions.cc`（行 23、113）、`examples/geant4-thin-silicon/recorded/`、`check_geant4_study.py`（行 357）、`geant4_benchmarks.py`（行 274）

---

## §R.15 與 main 探測器系統設計流程的關係（2026-10-24）

main 0.37.0–0.38.0 在 hep-detector 加入探測器系統設計流程（`references/system-design-workflow.md`、`contracts/design.py`、`scripts/evaluate_design.py`）。本計畫在 2026-10-24 改為接上這個流程，不另建一套；本節說明分工的理由。

### §R.15.1 保真度與 Geant4 的位置

| 保真度（main） | 意義 | 本計畫提供的部分 |
|---|---|---|
| F0 | 啟發式論證，沒有 run | — |
| F1 | 解析式，由 tool contract 執行（`tracker_resolution`、`multiple_scattering`、`design_estimates` 等） | C1 的搜尋內圈在行程內使用同樣的函式 |
| F2 | toy Monte Carlo（`toy_spectrometer`、`design_estimates.py infield-acceptance`） | B3 對 J15 候選直接執行，取代手算比較 |
| F3 | 響應組裝與預期精度（hep-statistics 的 Asimov 擬合） | — |
| F4 | 經 `check_geant4_study.py label --upgrade` 重新發出 `validated-in-scope` 的 Geant4 研究 | A1 讓標籤正確；B1、B2 讓磁譜儀研究可行並寫出 F4 欄位；B3（J15）與 C2 的確認產生 F4 |
| F5 | 原型或試束量測 | — |

搜尋過程中的短 Geant4 run 沒有保真度，也不是 evaluation，只是存在 `search_summary` 中的搜尋值。理由：F4 要求研究經過資格判定；搜尋中的 run 為了速度犧牲統計，而且和選擇過程相關（贏家詛咒），不應該被當成證據。

### §R.15.2 判定的擁有權

需求是否滿足、成熟度、過時、篩選、比較基礎、排序與 Pareto 都由 `contracts/design.py` 從產物推導，絕不手寫（workflow 的「Never」一節）。本計畫的統計判定（`core/stats/decisions.py` 的 `equivalence`、`detection_limit`、`change`、收斂閘門與配對比較）只回答研究層的問題：benchmark 是否通過、run 是否收斂、版本之間是否改變、兩個設計在搜尋中的差值是否已分辨。理由：它們是研究標籤的輸入；需求的合規還需要適足表、bound 的組合與上游鏈，這些只有 `design.py` 有。所以任務 C 原本的需求判定（`threshold`）、`order` 與「推薦設計」都刪除（§R.13）。

### §R.15.3 不宣稱最佳；人工閘門

main 只在比較基礎成立、所有存活的候選都有相同保真度向量與分母的非樂觀 expected-precision 評估時才排序；Pareto 只在超過合併 1σ 時才判定支配；永遠不宣稱全域最佳；閘門 H1–H4 需要人。所以任務 C 是 D2 的候選產生器：10⁴ 級的搜尋族群留在 `search_summary`，只有決選者以 `expand` 成為候選，再由一般的 `evaluate_design.py run` 與 `report` 處理。贏家詛咒以「確認必須用新種子的 F4 研究」處理，並由 CV-C2 的規則強制：種子出現在搜尋摘要中的 evaluation 判為 `design.contract_mismatch`。

### §R.15.4 參數層級的過時與增量重跑

main 的 evaluation 以 `parameter_digest` 綁定候選：只有它讀到的參數改變才過時；`run_workflow.py --incremental` 以 argv、程式、plugin release 摘要、環境與輸入作為略過的鍵。所以任務 C 不再有自己的設計快取規則，只保留搜尋內部的快取鍵（含 S、N、K、B）；`geant4_run.py run` 也像 `run_workflow.py` 一樣寫出 `argv`、`script_sha256` 與 `versions.plugin_release`（A2）。

### §R.15.5 F4 的研究紀錄介面與資格路徑

`design.py` 對 F4 的要求：研究紀錄是 `validated-in-scope`；`evaluate_design.py geometry` 產生的幾何檔（`design-geometry/1`）列在 `input_manifest`，且參數摘要和候選一致；`extension.study.results.<figure of merit>` 有 `value`、`statistical_uncertainty`、`model_envelope`；`tail_sources_simulated` 列出模擬了哪些尾部來源（alignment、calibration-non-uniformity、noise-digitization、pattern-recognition 四種都有時 bound 才是 `estimate`，否則是 `optimistic`）。

本計畫的對應：B1 的 `from-geometry` 由幾何檔與宣告的實現設定檔推導 `element_sim.spec/1`；B2 的 `simreco` 把四種尾部來源做成可切換的階段，`label` 寫出 `results`、尾部來源與幾何檔；`statistical_uncertainty` 定義為 68.27 % 的 t 半寬（A1），和 `design.py` 讀成覆蓋率 0.6827 高斯的方式一致；每個（figure of merit, 分母）一份研究，因為每個候選只有一個 `geometry_ref`，而 `results` 不以分母為鍵。

**資格路徑（D0，待維護者核准）。** 偵測器層級的研究（解析度、電荷誤判、簇射包含）沒有對應的物理參考，依現有規則永遠無法升級。選擇建立資格路徑，而不是讓 `design.py` 接受未驗證的 F4：(i) 研究的材料都落在已通過的 A1 材料 benchmark 範圍內；(ii) 磁場傳播的 verification（B1 的解析螺旋）在該磁場設定下通過；(iii) 重建的 verification（`simreco` 對已知真值）通過；(iv) 新的徑跡 reference benchmark 通過（孤立 Si 片中的多重散射角寬度，對照 PDG Highland／Lynch–Dahl，附負對照，範圍維度為剛度與粒子）。理由：`validated-in-scope` 在全 plugin 只保留一個意義；第 iv 項給偵測器層級的研究一個物理上的錨點，而前三項保證研究的其他部分是正確推論。

### §R.15.6 擴充點：幾何種類 → realizer

`contracts/rules/design_geometry.json` 把候選的參數對應到一種幾何（目前只有 `layered-spectrometer`）。每一種幾何需要一個 realizer，把幾何檔變成某個後端的 spec：`element_sim`（B1 的 `from-geometry`）、使用者的 Geant4 應用（引入 `g4sim`）或使用者建置開啟 GDML 時的 GDML 檔，之後可以是 DD4hep。加入一種探測器 = 一個對照表條目（契約）加一個 realizer；研究層只讀邊界產物，不需要改。C1 的搜尋由 tool contract 驅動，所以在 F1、F2 與探測器種類無關；Geant4 部分只能用已有 realizer 的幾何種類（目前是磁譜儀；B2 的對照表 1.1.0 加入 TOF 與電磁量能器的欄位）。

### §R.15.7 為什麼搜尋不是 adapter

adapter 是連接外部工具的選用元件，沒有任何 skill 或 core 模組可以依賴它（`docs/adapter-authoring.md` 開頭）。搜尋是 plugin 對 main 產物的邏輯，所以放在 `evaluate_design.py search`，沿用 main 把 `scan` 做成子命令的先例（OQ-18）。只有選用的貝氏最佳化後端（Ax／BoTorch）是外部工具，因此是 `adapters/design-bo/`。