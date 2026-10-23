# Geant4 模擬研究、J15 最小磁譜儀與自動化設計搜尋：整合文件

> 文件類型：計畫、實作規格與設計理由的整合文件（給執行的 agent、審查者與維護者）。狀態：待使用者與維護者核准
> 基準：hep-research `main` 的 `9f08796`（0.23.0 加未發布的變更），contracts 3.5.0，adapter geant4 0.1.0，Geant4 11.4.3
> 日期：2026-10-23
> 語言：繁體中文原文；英文版 [`geant4-program.en.md`](geant4-program.en.md) 內容相同。兩者不一致時以中文為準，並同時修正英文
> 執行環境：**每個階段都在自己的 isolated git worktree 中執行**（§P.10），不修改主要 checkout 或其他 worktree

## 如何使用本文件

**給執行的 agent：**
1. 讀 §P.0（階段一覽）、§P.10（在 isolated worktree 中執行）、§P.6（閘門）、§P.4（介面擁有權）。
2. 依 §P.10.2 為你的階段建立並確認 isolated worktree（`.claude/worktrees/geant4-<階段>`，分支 `worktree-geant4-<階段>`，基底為含前置階段的最新 `origin/main`）；之後所有步驟都在其中進行。
3. 讀你的階段所屬那一部的任務卡（§A.0、§B.0 或 §C.0），再讀該部的 §1–§4 與你的階段的工作項及驗收清單。
4. 需要某條規則的理由時，才讀第 5 部。
5. 本文件約 2,800 行：依目錄的節號分段讀取（例如搜尋 `## §A.5`），不要一次讀完。

**各部的權威範圍：**

| 部 | 節號 | 內容 | 權威範圍 |
|---|---|---|---|
| 第 1 部 計畫總覽 | §P | 評估、原則、階段、介面擁有權、命名、閘門、待決事項、風險、執行環境 | 階段的順序與依賴、編號、版本代號、介面擁有權、閘門、待決事項、執行環境 |
| 第 2 部 任務 A | §A | A1、A2 的工作項與驗收；共用的硬性限制（§A.3）與檢查（§A.8） | 這兩個階段的內容與驗收 |
| 第 3 部 任務 B | §B | J15 的設計；B1、B2、B3 的工作項與驗收 | 這三個階段的內容與驗收；J15 的數值 |
| 第 4 部 任務 C | §C | 自動化設計的設計；C1、C2、C3 的工作項與驗收 | 這三個階段的內容與驗收 |
| 第 5 部 設計理由 | §R | 從實際實驗得到的設計依據、架構、被取代的設計 | 只說明理由；與第 2–4 部衝突時以第 2–4 部為準並回報 |

**編號：**
- 節：「§A.8」是第 2 部（任務 A）的第 8 節，「§P.10.2」是第 1 部的 10.2 節，「§B 附錄 A」是第 3 部的附錄 A。
- 工作項：「A1.6」「B2.1」「C2.4」（階段.序號），在全文中唯一。
- 契約版本：CV1（A1）、CV2（B2）、CV3（C2），號碼在合併時才定；全文（含第 5 部）都用 CV1–CV3，「C1」「C2」只指階段。
- 第 2–4 部的結構相同：§X.0 任務卡、§X.1 名詞與檔案、§X.2 前提與提供的介面、§X.3 硬性限制、§X.4 設計摘要、§X.5 起每個階段一節（工作項與驗收清單），之後是契約與版本、檢查、不做與延後、待決事項與風險、執行步驟、附錄。

**整合紀錄：** 2026-10-23 由原本分散的 `plan.md`、`task-a-core.md`、`task-b-j15.md`、`task-c-design-search.md`、`architecture.md`（與各自的英文版）合併而成，內容不變，只改寫節號與交叉引用；舊檔已移除。各部的版本歷程保留在該部的附錄。設計數值的計算程式（`gate_operating_characteristics.py`、`j15_design_estimates.py`、`design_search_closure.py`）仍是同一資料夾中的獨立檔案。

## 目錄

- **第 1 部　計畫總覽（§P）**
  - §P.0 一頁摘要
  - §P.1 評估：先前規劃的問題與處理
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
  - §A.5 階段 A1：正確性修正（contracts CV1，sci-fix）
  - §A.6 階段 A2：共用標頭與邊界產物（geant4 adapter 0.2.0）
  - §A.7 契約與版本
  - §A.8 每個階段結束時的檢查
  - §A.9 不做與延後
  - §A.10 待決事項與殘餘風險
  - §A.11 建議的執行步驟
  - §A 附錄 A：統計規格彙整
  - §A 附錄 B：數值
  - §A 附錄 C：基準核對值（`9f08796`）
  - §A 附錄 D：出處
  - §A 附錄 E：版本歷程
- **第 3 部　任務 B：`element_sim`、重建與 J15 最小磁譜儀（§B）**
  - §B.0 任務卡
  - §B.1 名詞與檔案
  - §B.2 前提與提供的介面
  - §B.3 硬性限制
  - §B.4 J15 的設計
  - §B.5 階段 B1：`element_sim` 與事件檔（geant4 adapter 0.3.0）
  - §B.6 階段 B2：重建與契約（geant4 adapter 0.4.0、contracts CV2）
  - §B.7 階段 B3：J15 研究
  - §B.8 契約與版本
  - §B.9 不做與延後
  - §B.10 待決事項與殘餘風險
  - §B.11 建議的執行步驟
  - §B 附錄 A：數值
  - §B 附錄 B：出處
  - §B 附錄 C：版本歷程
- **第 4 部　任務 C：自動化探測器設計搜尋（§C）**
  - §C.0 任務卡
  - §C.1 名詞與檔案
  - §C.2 前提與提供的介面
  - §C.3 硬性限制
  - §C.4 設計
  - §C.5 階段 C1：需求、文法與快速搜尋（detector-design 0.1.0）
  - §C.6 階段 C2：模擬評估與確認（detector-design 0.2.0、geant4 adapter 0.5.0、contracts CV3）
  - §C.7 階段 C3：範例（detector-design 0.3.0）
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

---

# 第 1 部　計畫總覽（§P）

> 日期：2026-10-23

---

## §P.0 一頁摘要

三個任務、八個階段，每個階段是一次可以單獨合併的變更，有自己的驗收清單：

| 階段 | 任務 | 一句話 | 前提 | 版本 | 規模 |
|---|---|---|---|---|---|
| **A1** | A 正確性 | 修正會錯誤發出 `validated-in-scope` 的缺陷 D1–D8、D10；統計與 summary 的共用模組放進 `core/` | — | contracts **CV1**（sci-fix） | 大 |
| **A2** | A 邊界產物 | `g4sim` 共用標頭、逐事件種子、`layered_sim` 寫出三個邊界產物；研究層只讀邊界產物（D9） | A1 | geant4 adapter **0.2.0** | 大 |
| **B1** | B 新後端 | `element_sim`（盒狀元件、場、平面穿越、量能器漏失）、逐事件 ROOT 檔、`simroot` | A2 | geant4 adapter **0.3.0** | 大 |
| **B2** | B 重建與契約 | `simreco`、結果表、遞移的處理鏈、verification／regression／surrogate 類別 | B1 | geant4 adapter **0.4.0**、contracts **CV2** | 中 |
| **B3** | B J15 研究 | J15 驗證梯、收斂、variation、TOF 敏感度、journey | B2 | 範例與文件 | 中（計算量大） |
| **C1** | C 快速搜尋 | 需求規格、元件目錄、設計文法、F0 解析評估、NSGA-II、封閉測試 | A1 | detector-design adapter **0.1.0** | 中 |
| **C2** | C 模擬搜尋 | F1/F2 評估、確認 run、需求判定、配對比較、穩健性與防護 | B2、C1 | detector-design **0.2.0**、geant4 adapter **0.5.0**、contracts **CV3** | 大 |
| **C3** | C 範例 | J16 自動設計範例（與 J15 比較）、選用的 MOBO 後端 | B3、C2 | detector-design **0.3.0** | 小到中 |

```
A1 ──▶ A2 ──▶ B1 ──▶ B2 ──▶ B3 ─────────┐
 │                    │                  ▼
 └──▶ C1 ─────────────┴──────▶ C2 ──▶ C3
```

到「以模擬自動設計探測器」（C2）的關鍵路徑是 A1 → A2 → B1 → B2 → C2；C1 可以在 A1 之後與 A2、B 平行進行；J15 的物理研究（B3）不在 C2 的關鍵路徑上，只是 C3 比較的對象。

---

## §P.1 評估：先前規劃的問題與處理

| # | 問題 | 影響 | 處理 |
|---|---|---|---|
| P1 | **A1 的範圍膨脹。** 上一輪把只有任務 C 需要的功能（單邊門檻與優劣判定、配對比較、搜尋角色、`values` 累加器）放進 A1 | A1 是 sci-fix，要盡快修正已經會錯誤發出 `validated-in-scope` 的缺陷；多出的功能加重證據與審查負擔，延後修正 | 原則 R1（「由第一個使用者引入」）：A1 只含它自己用到的東西；判定引擎的 `change` 在 B2、`threshold`／`order`／配對比較在 C2 加入；位置（`core/`）一開始就定好 |
| P2 | **命名衝突。** 「C1、C2」同時指契約版本與任務 C 的階段 | agent 與審查者讀錯 | 契約版本改記為 **CV1、CV2、CV3**；任務 C 的階段為 C1–C3（§P.5） |
| P3 | **關鍵路徑過長。** 任務 C 等待整個 B2，而 B2 混合了基礎設施（`simreco`、契約）與 J15 的物理研究 | 自動化設計被 J15 的研究工作拖住 | B 拆成 B2（重建與契約）與 B3（J15 研究）；C2 只等 B2；C1 只等 A1 |
| P4 | **介面放錯層。** 統計與 summary 讀取原本在 hep-detector 的腳本，adapter 依分層規則不能 import | 任務 C 需要第二份實作 | 共用程式一律在 `core/`；本部 §P.4 列出每個介面的位置、擁有者與使用者 |
| P5 | **文件重複而漂移。** §R.10 複製了各階段內容與驗收，每次修改都要同步，已出現不一致 | 讀者不知道以哪份為準 | 權威分工（§P.9）；§R.10 改為指向本部 |
| P6 | **待決事項分散**在三份規格 | 維護者看不到全貌，也不知道哪個決定擋住哪個階段 | 合併為一張表，標示阻擋的階段（§P.7） |
| P7 | **沒有階段之間的閘門** | 例如 ROOT 讀取能力或場的確定性檢查失敗時，後續階段仍會照計畫進行 | 明確的閘門（§P.6） |
| P8 | **工作量只有零星估計** | 無法排程 | 相對規模（小／中／大）與已知的估計（A1 契約部分約 8–12 個工作天）；其餘在各階段開始時估計（§P.0、§P.8） |
| P9 | **跨 adapter 的依賴未定義。** 任務 C 要產生 `element_sim` 的 spec 並驗證，但 adapter 不能 import 另一個 adapter | C1 無法驗證實現結果 | `geant4_run.py` 提供 `check-spec` 子命令（B1），`detector-design` 以子行程呼叫；C1 以自己的有效性規則為準，以 `check-spec` 驗證實現在 C2（C2.9）（§P.4） |

---

## §P.2 規劃原則

| # | 原則 | 說明 |
|---|---|---|
| R1 | **由第一個使用者引入，但位置一開始就定好** | 每個介面在第一個需要它的階段加入；共用的介面從第一天起就放在所有使用者都能 import 的地方（`core/`、`contracts/`） |
| R2 | **schema 只做附加的演進** | 新欄位都是選用的；版本號（`summary_version` 等）的 minor 增加；舊紀錄永遠能讀、能重播 |
| R3 | **同一個量只有一份正式實作** | 另一種語言或另一個位置的實作只能在測試中作為 oracle |
| R4 | **sci-fix 保持最小** | A1 只含修正缺陷所需的變更與它們的直接基礎 |
| R5 | **每個階段可單獨合併** | 有自己的版本、VALIDATION 條目、CHANGELOG、驗收清單；合併後 plugin 是一致的 |
| R6 | **判定可重現，數字可追溯** | 重現的定義是判定與 label 相同（§R.5.6）；結果附搜尋規模與證據相關性 |
| R7 | **AI 是設計者，不是裁判** | Claude 選結構、提出種子、解讀結果；「是否符合、哪個最好」只由有紀錄的評估與統計判定（任務 C） |

---

## §P.3 階段的內容與驗收（摘要）

各階段的完整工作項與驗收在任務規格中；這裡只列範圍的邊界，避免重疊。

| 階段 | 包含 | 明確不包含（在哪個階段） |
|---|---|---|
| A1 | benchmark 表與驗證類別（reference、setup-matched、sanity、interface）；範圍比對；configuration 與隔離（`spec-v1`）；區塊 batch means、精確區間、MPV、分位數（直方圖）；判定引擎的 `equivalence` 與 `detection_limit`；兩階段事件數；種子雜湊 H；evidence 角色；`simulation-summary/1` 與 `simulation-observables/1` 的 schema 與讀取；Python summary 產生器；D6、D7（停止規則、證據相關性、trace）與 D8、D10 的修正；`ext_computational_run.json` 宣告既有的 `simulation` 屬性；`tolerance_mode` 的 `absolute`（每個觀測量自己的 `tolerance`）；J14 重產；sci-fix 流程。`absolute` 模式是 P1 的例外：A1 自己的 J14 benchmark 就需要它 | `change`（B2）、`threshold`／`order`／配對比較（C2）、regression 角色（B2）、search 與 confirmation 角色和 seed_group（C2）、`values` 累加器（C2）、C++ summary（A2） |
| A2 | `g4sim`（`SimHash`、`SimSeed`、`SimSummary`、`MiniJson`、`SimProbe`）；`per-event` 種子；`layered_sim` 寫出 summary、column map、effective config；不含名稱的 `tree-v1`；effective config 依內容雜湊存放；`validate_spec`、`spec.schema.json` 與 `Spec.cc` 接受 `run.seeding`、`output.observables`、`output.blocks`、`output.debug_observable_dump`；研究層只讀邊界產物；schema 關鍵字（`maxItems`、`maximum`、`exclusiveMaximum`） | `element_sim`（B1） |
| B1 | `element_sim.spec/1`、`element_sim`、場、平面穿越、量能器母體與漏失欄、逐事件 ROOT 檔、`simroot`、`geant4_run.py check-spec`（登記於 `MISSING_FILE_ARGS`）、兩個後端的介面一致性、確定性場檢查 | `simreco`（B2）、J15 的統計研究（B3） |
| B2 | `simreco`（數位化與重建，可攜的亂數）、`geant4_run.py reco` 與 `table`、遞移的處理鏈、verification／regression／surrogate 類別與表條目、regression 角色、判定引擎的 `change`、CV2 | J15 的驗證梯與收斂（B3） |
| B3 | J15 研究：驗證梯（隔離的 PVT benchmark 是獨立的研究紀錄）、量能器 cut 收斂、variation、TOF σ_t 敏感度、recorded 資料、journey 與路由、文件 | — |
| C1 | 需求規格、元件目錄第一版、設計文法與實現、F0 解析評估、NSGA-II（標準函式庫）、搜尋紀錄（F0-only）、agent 協定、封閉測試。A2 合併前 schema 不用 `maxItems`、`maximum`、`exclusiveMaximum`（A2.7 才提供），這些上限在 Python 中檢查 | 任何 Geant4 評估、以 `check-spec` 驗證實現（C2） |
| C2 | F1/F2 評估、確認 run、判定引擎的 `threshold` 與 `order`、配對比較與 seed_group、search 角色、`values` 累加器（Python 與 `SimSummary.hh`）、以 `check-spec` 驗證實現（C2.9；B3 已合併時 J15 以 `--strict` 檢查）、利用模擬缺陷的防護、穩健性、CV3 | J16、MOBO（C3） |
| C3 | J16 自動設計範例（與 J15 比較）、選用的 MOBO（Ax/BoTorch）後端 | — |

---

## §P.4 介面擁有權

| 介面 | 引入 | 位置 | 擁有者（steward） | 使用者 |
|---|---|---|---|---|
| benchmark 表、驗證類別、範圍比對、隔離規則 | A1（B2、C2 附加） | `contracts/validate.py`、`dependencies.py` | contracts（內容由 hep-detector 提出） | A1、B2、B3、C2 |
| 種子雜湊 H（Python） | A1 | `core/simulation/seeds.py` | hep-detector | geant4 adapter、`check_geant4_study.py`、detector-design |
| 種子雜湊 H（C++） | A2 | `adapters/geant4/assets/g4sim/SimHash.hh` | hep-detector | `layered_sim`、`element_sim`、`simreco` |
| 角色：evidence 角色 | A1 | `contracts/`、study spec schema | contracts | 全部 |
| 角色：regression | B2 | 同上（CV2） | contracts | B2、B3 |
| 角色：search 與 confirmation 角色、seed_group | C2 | 同上（CV3） | contracts | C2、C3 |
| `simulation-summary/1`、`simulation-observables/1` 的 schema、讀取、合併 | A1（`values` 在 C2 附加） | `core/simulation/summary.py`、`core/simulation/schemas/` | hep-detector | 全部 |
| column map、effective config 的 schema | A2 | `core/simulation/schemas/` | hep-detector | A2、B1、C2 |
| `tree-v1` 目標雜湊與 `hash_scheme` | A2（A1 為 `spec-v1`） | `adapters/geant4/assets/g4sim/SimProbe.hh`；比對在 `check_geant4_study.py` | hep-detector | A2、B1、B3、C2 |
| `per-event` 種子（`run.seeding`） | A2 | `adapters/geant4/assets/g4sim/SimSeed.hh`、spec/1 | hep-detector | `layered_sim`、`element_sim` |
| 物理探針（effective config 的 physics 部分） | A2 | `adapters/geant4/assets/g4sim/SimProbe.hh` | hep-detector | A2、B1、B2（regression）、C2 |
| 區塊估計量、精確區間、MPV、分位數 | A1（`values` 分位數在 C2） | `core/stats/batch_means.py` | hep-statistics | hep-detector 腳本、detector-design |
| 分布函式（`t_ppf`、`f_ppf`、`garwood`） | A1 | `core/stats/distributions.py` | hep-statistics | 同上 |
| 判定引擎 | A1 `equivalence`、`detection_limit`；B2 `change`；C2 `threshold`、`order`、配對模式 | `core/stats/decisions.py` | hep-statistics | A1、B2、B3、C2 |
| `g4sim` 標頭 | A2（`SimSummary` 的 `values` 在 C2） | `adapters/geant4/assets/g4sim/` | hep-detector | `layered_sim`、`element_sim`、`simreco` |
| `element_sim.spec/1` 與 `check-spec` | B1 | geant4 adapter | hep-detector | B1、B3、C2（C2.9） |
| 逐事件 ROOT 檔、`simroot` | B1 | geant4 adapter | hep-detector | B2、B3 |
| `simreco` 與 reco spec | B2 | geant4 adapter（C++，不連結 Geant4） | hep-detector | B3、C2 |
| 需求規格、元件目錄、設計文法、搜尋 spec | C1 | `adapters/detector-design/` | hep-detector（待決，§P.7） | C1–C3 |
| `extension.design_search` 與其規則 | C2 | `contracts/`（CV3） | contracts | C2、C3 |

跨 adapter 的呼叫一律以子行程與 JSON 檔案進行（分層規則：adapter 只 import `core` 與 `contracts`），例如 detector-design 呼叫 `geant4_run.py check-spec`、`geant4_run.py run`、`geant4_run.py reco`。

---

## §P.5 命名與編號

| 對象 | 寫法 | 例 |
|---|---|---|
| 階段 | 任務字母加數字 | A1、A2、B1、B2、B3、C1、C2、C3 |
| 工作項 | 階段.序號 | A1.6、B2.1、C2.4 |
| 契約版本（合併時才定號碼） | **CV1、CV2、CV3** | CV1 = A1 的 contracts minor；CV2 = B2；CV3 = C2 |
| 閘控寫法 | `strict or _at_least(contract_version, CVn)` | — |
| geant4 adapter 版本 | 0.2.0（A2）、0.3.0（B1）、0.4.0（B2）、0.5.0（C2） | — |
| detector-design adapter 版本 | 0.1.0（C1）、0.2.0（C2）、0.3.0（C3） | — |
| journey | J14 薄矽層（既有）、J15 最小磁譜儀（B3）、J16 自動設計（C3）、J17 離子源與 Birks（延後） | — |
| VALIDATION 條目 | GEANT4-CORRECTNESS（A1）、GEANT4-SUMMARY（A2）、GEANT4-ELEMENT（B1）、GEANT4-RECO（B2）、GEANT4-J15（B3）、DESIGN-SEARCH-F0（C1）、DESIGN-SEARCH（C2）、DESIGN-SEARCH-J16（C3） | — |
| 節的引用 | 全部在本文件中：「§P.n」是第 1 部、「§A.n」「§B.n」「§C.n」是第 2–4 部、「§R.n」是第 5 部；「§B 附錄 A」是第 3 部的附錄 | — |

先前文件中的「contracts C1、C2」即 CV1、CV2；第 5 部（設計理由） 保留舊寫法，在檔頭註明對應。

---

## §P.6 階段閘門

| 閘門 | 時機 | 條件 | 不通過時 |
|---|---|---|---|
| G-A1 | A1 合併前 | J14 重產的紀錄通過 `--strict` 與 `dependencies.py`；閘門、覆蓋率、MPV、偵測極限的 toy 通過 | 不合併；若 J14 因未達標而失去 `validated-in-scope`，由維護者依 §P.7 第 4 項決定 |
| G-A2 | A2 合併前 | J14 的 CSV 與 A2 前逐位元相同；探針不改變亂數狀態 | 不合併 |
| G-B1a | B1 開始的第一天 | `G4RootAnalysisReader` 能讀 MT 合併、壓縮的檔案與字串欄 | `simroot` 改為只讀純量欄，字串移到 JSON 旁檔（B1.5）；兩種結果都可接受，備案也是有效的計畫 |
| G-B1b | B1 合併前 | 確定性場檢查在名義值下通過；兩個後端共同觀測量以 `equivalence`（宣告的容許值與 se 目標）判定一致；量能器比較總漏失（後、前、側面之和），因為兩個後端的面不同 | 不合併 |
| G-C1 | C1 合併前 | 全部封閉測試通過 | 不合併 |
| G-C2a | C2 的 trial | 量測配對比較的變異縮減 | 縮減小於宣告值時，S2 改用獨立比較（C2.3） |
| G-C2b | C2 合併前 | 贏家詛咒與需求判定的 toy、CV3 的契約測試通過 | 不合併 |
| G-C3 | C3 合併前 | J16 完成並附與 J15 的比較 | 不合併 |

---

## §P.7 待維護者決定的事項（合併清單）

| # | 事項 | 建議 | 阻擋 |
|---|---|---|---|
| 1 | CV1 的歸類 | minor 加 sci-fix | A1 |
| 2 | 新 `core/` 模組的 steward | 統計歸 hep-statistics；`core/simulation/` 歸 hep-detector | A1 |
| 3 | hep-computing 同意在 `ext_computational_run.json` 宣告既有的 `simulation` 屬性 | 同意 | A1 |
| 4 | 兩階段係數 F₀.₉₀（約 10 % 未達標）或 F₀.₉₅（約 5 %，事件數多約 22 %）；重產的 J14 偶然失去 `validated-in-scope` 時的處理 | J14 重錄用 F₀.₉₅；失去時記錄並保留舊紀錄於 advisory | A1 |
| 5 | J14 掃描與 variation run 的 live 重錄，以及 recorded 大小上限 | 重錄；上限 3 MB | A1 |
| 6 | 精確區間的切換門檻 | 任一區塊為 0 或總數 < 100 | A1 |
| 7 | G5「未複製範例程式碼」的確認方式 | 審查者在 VALIDATION 條目中確認 | A2、B1 |
| 8 | 遞移的處理鏈（hep-computing 同意）與 CV2 的歸類 | 同意；minor | B2 |
| 9 | `simreco` 的 C++17 CI 工作是否必要 | 必要 | B2 |
| 10 | ROOT 檔的存放位置與保留期限 | 不提交；由使用者的儲存決定，紀錄只留雜湊 | B1 |
| 11 | `element_sim` 與 detector-design 的維護歸屬 | hep-detector | B1、C1 |
| 12 | 在 hep-detector `SKILL.md` 加一行指向 `detector-design-search.md` 的路由（約 120 bytes；quick load 剩 931 bytes） | 加 | C1 |
| 13 | CV3 的歸類與 hep-computing 同意 `extension.design_search` | minor；同意 | C2 |
| 14 | MOBO 後端（Ax/BoTorch）是否列為測試過的工具 | 列為選用 | C3 |

---

## §P.8 跨任務的主要風險

1. **兩個 Geant4 程式的維護成本**（`layered_sim` 凍結、`element_sim` 新增）。以 `g4sim` 控制重複；長期可在 `element_sim` 加入主粒子出射紀錄後，把 J14 遷移過去並退役 `layered_sim`（延後，觸發條件：`element_sim` 能產生 J14 的全部觀測量）。
2. **統計的實際行為**：區塊 batch means 對偏斜分布的 O(1/B) 偏差、兩階段設計的未達標率（一對點約 19 %）、配對比較的變異縮減可能很小。都以 toy 與 trial 量測，不事先假設。
3. **未逐行核對的 Geant4 行為**：stepper 的建立、Birks 的 API、場交點誤差的方向、兩個 physics list 的核子截面、`G4RootAnalysisReader` 的能力。各在第一次使用的階段先核對。
4. **計算量**：J14 重錄（A1）、量能器簇射（B3）、F1/F2 搜尋（C2）。各階段在 trial 後寫入預算。
5. **入口預算**：hep-detector quick load 只剩 931 bytes、description 1,016 / 1,024 字元。只有 §P.7 第 12 項可能動 `SKILL.md`。
6. **工作量估計不完整**：只有 A1 契約部分有原型估計（約 8–12 個工作天）；其餘在各階段開始時估計並記錄。
7. **參考文獻**：任務 C 引用的 GRACE、VI-BRATO 是 2026 年的預印本；所有出處在正式引用前經 hep-citations 核對。

---

## §P.9 文件地圖與權威分工

| 文件 | 內容 | 權威範圍 |
|---|---|---|
| 第 1 部（本部） | 評估、原則、階段、介面擁有權、命名、閘門、待決事項、風險、執行環境 | 順序、編號、版本代號、擁有權、閘門、待決事項、執行環境（isolated worktree） |
| 第 2 部（任務 A） | A1、A2 的工作項與驗收 | 這兩個階段的內容與驗收 |
| 第 3 部（任務 B） | J15 的設計；B1、B2、B3 的工作項與驗收 | 這三個階段的內容與驗收；J15 的數值 |
| 第 4 部（任務 C） | 自動化設計的設計；C1、C2、C3 的工作項與驗收 | 這三個階段的內容與驗收 |
| 第 5 部（設計理由） | 設計理由、參考實驗、被取代的設計 | 理由；與規格衝突時以規格為準並回報 |
| `README.md` | 資料夾入口，指向本文件 | — |
| `gate_operating_characteristics.py`、`j15_design_estimates.py`、`design_search_closure.py` | 設計數值的計算程式 | 對應附錄的數值 |

第 2–4 部的結構相同：§X.0 任務卡、§X.1 名詞與檔案、§X.2 前提與提供的介面、§X.3 硬性限制、§X.4 設計摘要、§X.5 起各階段的工作項與驗收，之後是契約與版本、檢查、不做與延後、待決事項與風險、執行步驟、附錄（X 為 A、B 或 C）。

---

## §P.10 執行環境：isolated worktree

### §P.10.1 原則

- **每個階段在自己的 isolated git worktree 中執行**：一個階段、一個 worktree、一個分支。
- 主要 checkout（repo 根目錄的工作區）與其他 worktree 中的檔案一律不修改。
- 理由：
  - 可以平行的階段（例如 C1 與 A2、B1）與平行的 agent 不會互相覆寫；
  - 建置目錄、Geant4 輸出與暫存檔彼此隔離；
  - 一個階段失敗時可以整個丟棄，不影響其他工作；
  - 每個階段的變更就是一個分支的 diff，審查與合併的範圍清楚。

### §P.10.2 建立與確認

| 項目 | 規定 |
|---|---|
| 位置 | `.claude/worktrees/geant4-<階段>`，階段名小寫，例如 `.claude/worktrees/geant4-a1` |
| 分支 | `worktree-geant4-<階段>`，例如 `worktree-geant4-a1`（`EnterWorktree` 的命名規則） |
| 基底 | 已包含全部前提階段（§P.0 的「前提」欄）的最新 `main`；例如 B2 以 B1 合併後的 `main` 為基底 |
| 規格的來源 | 本資料夾核准後合併到 `main`，worktree 中就有規格。核准前，規格只在分支 `worktree-geant4-architecture` 上，以 `git show worktree-geant4-architecture:plugins/hep-research/docs/dev/geant4-architecture/<檔名>` 讀取，不把該分支合併進階段分支 |
| 在 Claude Code 中 | 工作階段本身以 `EnterWorktree`（name `geant4-<階段>`）建立並進入 worktree：位置 `.claude/worktrees/geant4-<階段>`、分支 `worktree-geant4-<階段>`、基底 `origin/main`；把工作委派給 subagent 時，Agent 工具使用 `isolation: "worktree"` |
| 在其他環境 | `git fetch origin && git worktree add .claude/worktrees/geant4-a1 -b worktree-geant4-a1 origin/main`；在 Claude Code 中可再以 `EnterWorktree` 的 `path` 進入這個既有的 worktree |
| 開始前確認 | `git rev-parse --show-toplevel` 是該 worktree 的路徑、`git branch --show-current` 是該階段的分支、`git status` 乾淨；每個前提階段的合併 commit 都滿足 `git merge-base --is-ancestor <合併 commit> HEAD`；這些結果寫入該階段的工作紀錄（VALIDATION 條目的環境欄） |

### §P.10.3 在 worktree 中的規則

1. 所有編輯、建置、測試、Geant4 執行與規格修正都在該階段的 worktree 中進行；不 `cd` 到主要 checkout 或其他 worktree。
2. 指令使用 worktree 內清楚的絕對路徑或相對路徑；避免以執行時才計算的變數組出 git 的參數，讓工具與審查者都能確認指令留在 worktree 內。
3. **`git stash` 是所有 worktree 共用的。** 不使用裸的 `git stash` 或 `git stash pop`；需要暫存時用暫時的 WIP commit。
4. 建置目錄、E2 的輸出、ROOT 檔與 trial 的結果放在該 worktree 內不提交的目錄（例如 `build/`、`work/`，由 `.gitignore` 排除），或該 worktree 專屬的暫存目錄；不同 worktree 不共用建置目錄。Geant4 本身的安裝（E2）可以由多個 worktree 唯讀共用。
5. 只在該階段的分支提交；commit 附規定的 trailer；推送到同名的遠端分支。未經維護者核准不推送 `main`、不開 pull request。
6. 合併前在 worktree 中執行 §A.8 的檢查，並確認閘門（§P.6）。
7. 規格需要修正時：維護者核准規格之前，在文件的 worktree（`.claude/worktrees/geant4-architecture`，分支 `worktree-geant4-architecture`）中修改；實作開始之後，在該階段的 worktree 中修改。兩種情況都同時修改中英兩版並記入版本歷程；影響其他階段時同時更新本部。
8. 獨立審查與其他 subagent 以 `isolation: "worktree"` 執行；審查只讀不寫，沒有變更的 worktree 結束後自動清除。

### §P.10.4 可以平行的階段

| 同時進行 | 條件 | 注意 |
|---|---|---|
| C1 與 A2、B1、B2、B3 | A1 已合併 | C1 主要動 `adapters/detector-design/` 與它的文件，但也動一份 reference 文件、hep-detector `SKILL.md` 的一行路由（§P.7 第 12 項）、`core/physics/tracking.py`（新增）、hep-detector 的 `tracker_resolution.py` 與 `multiple_scattering.py`（改為呼叫 `core/`）與 `docs/capability-map.json`／`.md`；這些檔案與其他階段可能衝突，後合併者 rebase 並重跑檢查 |
| B3 與 C2 | B2 與 C1 已合併 | 兩者都可能修改 `geant4-study-protocol.md` 與 journey 文件；後合併者在新的 `main` 上 rebase 並重跑檢查 |

每個平行的階段各用自己的 worktree 與分支；同一個階段不由兩個 agent 同時在不同 worktree 中實作。

### §P.10.5 結束

- **合併後：** `git worktree remove .claude/worktrees/geant4-<階段>`，刪除本地分支；下一個階段從新的 `main` 建立新的 worktree。
- **放棄：** 移除該 worktree 與分支；不在主要 checkout 中做任何清理。
- **本資料夾本身** 在分支 `worktree-geant4-architecture` 與 worktree `.claude/worktrees/geant4-architecture` 中撰寫；之後的文件修改也在那裡進行，直到它合併到 `main`。

---

## §P.11 版本歷程

| 版本 | 內容 |
|---|---|
| 2026-10-23 | 初版：整合評估（P1–P9）、規劃原則、八個階段（B 拆為 B1–B3、C 為 C1–C3）、介面擁有權、命名（契約版本改記 CV1–CV3）、閘門、合併的待決事項與風險 |
| **2026-10-23（本版）** | **加入 §P.10「執行環境：isolated worktree」（建立、確認、規則、平行階段、結束）與給 agent 的讀法** |

---

# 第 2 部　任務 A：正確性修正與邊界產物（§A）

> 順序：A1 → A2；之後是任務 B（第 3 部（任務 B））與任務 C（第 4 部（任務 C））
> 基準：hep-research `main` 的 `9f08796`（0.23.0 加未發布的變更），contracts 3.5.0，adapter geant4 0.1.0，Geant4 11.4.3
> 日期：2026-10-23

---

## §A.0 任務卡

**目標。** 修正會讓模擬研究被錯誤標成 `validated-in-scope` 的缺陷（D1–D8、D10），並讓研究層只透過三個邊界產物（run summary、column map、effective config）認識模擬後端（D9）。統計與 summary 讀取一開始就放在 `core/`，讓之後的 adapter（任務 C）可以直接使用。

**兩個階段（依序，各自合併）：**

| 階段 | 內容 | 版本 | 語言 |
|---|---|---|---|
| **A1** 正確性修正 | 契約（benchmark 表、範圍、configuration 與隔離、evidence 角色）；`core/stats/`（區塊 batch means、精確區間、MPV、分位數、判定引擎的 `equivalence` 與 `detection_limit`、分布函式）；`core/simulation/`（種子雜湊、summary 與觀測量的 schema 與讀取）；Python summary 產生器；J14 重產 | contracts **CV1**（minor，sci-fix） | Python |
| **A2** 共用標頭與邊界產物 | `g4sim`（`SimHash`、`SimSeed`、`SimSummary`、`MiniJson`、`SimProbe`）；`per-event` 種子；`layered_sim` 寫出三個邊界產物；不含名稱的 `tree-v1`；effective config 依內容雜湊存放；研究層只讀邊界產物 | geant4 adapter **0.2.0**；contracts 不升版 | C++ 與 Python |

**不在範圍內：**
- `element_sim`、場、平面穿越、ROOT 檔、`simroot`、`simreco`、J15（任務 B）；判定引擎的 `change`（B2）。
- 判定引擎的 `threshold`、`order`、配對比較、search 角色、seed_group、`values` 累加器（任務 C 的 C2；§P.2 R1）。
- `layered_sim` 的 spec 格式（spec/1）不重構，只加選用欄位。

**交付物：** 程式與測試；重產的 J14 紀錄；sci-fix 的 ledger 條目與 advisory；VALIDATION 條目 GEANT4-CORRECTNESS（A1）與 GEANT4-SUMMARY（A2）；CHANGELOG；release manifest。

**完成的定義：** A1.15 與 A2.10 的驗收清單全部打勾；§A.8 的檢查全部通過；閘門 G-A1、G-A2（§P.6）通過。

**主要決定：**
1. **A1 是最小的 sci-fix。** 只含修正 D1–D8、D10 所需的變更與它們的直接基礎；任務 B、C 才需要的判定與欄位由它們自己加入（§P.2 R1、R4）。
2. **共用程式在 `core/`。** adapter 只能 import `core` 與 `contracts`；統計、判定、種子雜湊與 summary 讀取從第一天起就在 `core/`，hep-detector 的腳本只是呼叫層。
3. **重現 = 判定相同。** 不追求逐位元相同的統計量（§A.4.3）。
4. **`layered_sim` 凍結。** A2 只加選用欄位與檔案；新的幾何功能在任務 B 的 `element_sim`。

**第一步：** 依 §P.10.2 為本階段建立 isolated worktree（`.claude/worktrees/geant4-<階段>`，分支 `geant4-<階段>`，基底為已含前提階段的最新 `main`），並確認 `git rev-parse --show-toplevel`、`git branch --show-current` 與 `git status`。以下所有步驟都在這個 worktree 中進行。

**開始前必做：**
1. 確認 `main` 是否已超過 `9f08796`。若是，讀新的 CHANGELOG，重做§A 附錄 C 的核對，並更新本部（中英兩版）。
2. 讀 §P.0–§P.6；讀 §R.0、§R.2；讀 `docs/maintenance.md` 的 sci-fix 流程、adapter 變更流程、release 步驟。
3. A1 從 `prototype/phase1-core.patch` 開始。它只改 `contracts/validate.py`、`check_geant4_study.py`、`geant4_benchmarks.py`、study spec schema 與兩個測試檔，不含 `core/`：benchmark 表（等級與 kind，沒有驗證類別）、含 kind 的範圍比對（`scope_outside()`；維度寫死為 particle、material、energy、thickness，`longitudinal-profile` 例外）、benchmark 輸出 configuration 與目標雜湊（由 run record 的 `extension.simulation.geometry` 推導，不是由 spec/1；`longitudinal-profile` 沒有目標），以及 A1.12 的 enum 修正。它早於本規格：缺 `target_slabs`、`setup-matched`、依 benchmark 宣告的範圍維度、`hash_scheme`、`dependencies.py` 的重新推導與 CV1 閘控；閘控寫死 3.6.0；把 `longitudinal-profile` 寫成 `("reference", ("shower-shape",))`。

---

## §A.1 名詞與檔案

| 名詞 | 意義 |
|---|---|
| J14 | 既有 journey `examples/geant4-thin-silicon/`：薄矽層研究，唯一有 `validated-in-scope` 紀錄的 Geant4 範例 |
| study record | 帶 `extension.study` 的 computational-run 紀錄；`label` 決定其 artifact label |
| `validated-in-scope` | 經可升級的 benchmark 驗證、且宣告範圍在 benchmark 範圍內時才可有的 label；由 `contracts/validate.py` 的 `_study_upgrade` 把關 |
| 驗證類別 | benchmark 參考的性質（§A.4.4）；A1 定義 reference、setup-matched、sanity、interface；B2 加入 verification、regression、surrogate |
| observable kind | study spec 中受控的觀測量種類（enum），如 `most-probable-value` |
| configuration | 目標的放置情形：`isolated` 或 `embedded`（A1.3） |
| 邏輯 run | 由 spec、後端與邏輯 run 種子 S 決定的 N 個事件，編號 0 … N−1；可切成多個工作（job） |
| 區塊 | 邏輯 run 中依事件編號劃分的 K 段，每段 B 個事件（N = K·B）；batch means 的單位 |
| 三個邊界產物 | run summary（`simulation-summary/1`）、column map（`simulation-columns/1`）、effective config（引擎無關外框加實際幾何樹） |
| `seeding` | `stream`（既有行為）或 `per-event`（每個事件以 H(S, 事件編號) 重設；A2 起） |
| `hash_scheme` | 目標雜湊的推導方式：`spec-v1`（A1，由 spec/1）或 `tree-v1`（A2 起，由幾何樹） |
| 角色 | run 在研究中的用途；A1 定義 evidence 角色 trial、nominal、scan、control、variation、calibration；B2 加入 regression；C2 加入 confirmation 與 search 角色 |
| 判定引擎 | `core/stats/decisions.py`；A1 提供 `equivalence` 與 `detection_limit`，B2、C2 附加其他判定 |
| CV1、CV2、CV3 | 合併時才定號碼的 contracts minor（§P.5）；CV1 屬 A1 |
| E2 | 有 Geant4 11.4.3 建置的執行環境 |
| IUT | intersection-union test：所有觀測量都等價才通過 |
| DL | negative control 的偵測極限 |
| sci-fix | `docs/maintenance.md` 中修正科學正確性缺陷的流程 |
| 記法 | 「A1.6」「B1.3」「C2.1」是工作項（全文唯一）；「§A.7」「§P.4」「§R.6」是本文件各部的節（§P 第 1 部、§A 本部、§B 第 3 部、§C 第 4 部、§R 第 5 部） |

**主要檔案（相對 `plugins/hep-research/`）：**

| 用途 | 路徑 |
|---|---|
| 契約 | `contracts/validate.py`、`contracts/dependencies.py`、`contracts/schema.py`、`contracts/schemas/ext_computational_run.json` |
| 共用模組（新增） | `core/stats/distributions.py`、`core/stats/batch_means.py`、`core/stats/decisions.py`（steward hep-statistics）；`core/simulation/seeds.py`、`core/simulation/summary.py`、`core/simulation/schemas/`（steward hep-detector） |
| 既有 core | `core/status.py`、`core/trace.py`、`core/OWNERS.json`、`core/stats/tail_estimation.py`（`beta_ppf`、`clopper_pearson`）、`core/partition/engine.py`（`NON_ADDITIVE_TOKENS` 行 381） |
| 研究層 | `skills/hep-detector/scripts/check_geant4_study.py`（`convergence()` 行 335、相對差行 357、判定行 359、`scope_within()` 行 482）、`geant4_benchmarks.py`（`GRADES` 行 92–94、`bootstrap()` 行 197、`mpv()` 行 204、偵測極限行 275、MPV 的 bootstrap SE 行 369、`at_limit` 行 678）、`tracker_resolution.py`、`multiple_scattering.py`；`skills/hep-detector/assets/geant4-study-spec.schema.json`；`skills/hep-detector/references/geant4-study-protocol.md` |
| adapter | `adapters/geant4/adapter.json`；`adapters/geant4/assets/geant4_run.py`（`SIM_SOURCES` 行 63、`validate_spec()` 行 103、`cmd_scan` 行 435、`cmd_chunk` 行 491、`cmd_summarize` 行 525）、`geant4_build.py`（`GEANT4_USE_GDML: OFF` 行 53）、`geant4_verify.py`、`g4common.py`（既有的 Python 模組）；`adapters/geant4/assets/layered_sim/`（`Actions.cc`：CSV 格式 `%.10g` 行 23、沉積乘 track 權重行 113；`layered_sim.cc`：種子與 run manager 行 149–154；`MiniJson.hh`、`spec.schema.json`、`output.schema.json`） |
| J14 | `examples/geant4-thin-silicon/run.py`、`recorded/`（`events/` 5 個縮減 CSV、`runs/`、`summaries/`、`specs/`）、`output/` |
| 測試 | `tests/contracts/test_geant4_upgrade.py`、`test_simulated_dataset.py`、`test_schema_keywords.py`；`tests/adapters/test_geant4.py`；`tests/examples/test_geant4_thin_silicon.py`；`tests/skills/test_cli_robustness.py` |
| 工具 | `tools/run_all_checks.py`、`check_layering.py`、`check_relocation.py`、`check_ownership.py`、`check_packaging.py`、`measure_entrypoints.py`、`reference_inventory.py`、`capability_map.py`、`check_routing_static.py`、`scifix_advisories.py` |

---

## §A.2 前提與提供的介面

**前提：** 無（任務 A 先做）。

**提供給任務 B、C 的介面**（擁有權見 §P.4）：

| 介面 | 工作項 | 使用者 |
|---|---|---|
| benchmark 表、驗證類別、範圍比對、隔離規則（可附加條目） | A1.1–A1.3 | B2、B3、C2 |
| evidence 角色（可附加角色） | A1.4 | B2、C2 |
| 種子雜湊 H（Python `core/simulation/seeds.py`；C++ `g4sim/SimHash.hh`） | A1.4、A2.1 | 所有模擬程式、detector-design |
| `simulation-summary/1`、`simulation-observables/1` 的 schema 與讀取（可附加欄位） | A1.5 | B1、B2、C2 |
| 區塊估計量、精確區間、MPV、分位數 | A1.6、A1.7 | B3、C2 |
| 判定引擎 `equivalence`、`detection_limit`（可附加判定） | A1.8、A1.10 | B2、B3、C2 |
| 兩階段事件數 | A1.9 | B3、C2 |
| `g4sim` 標頭、`per-event` 種子、探針、`tree-v1`、column map、effective config 存放 | A2.1–A2.5 | B1、B2、C2 |
| schema 關鍵字 `maxItems`、`maximum`、`exclusiveMaximum` | A2.7 | B1、C1 |

附加只能是選用欄位、新的 enum 值或新的函式，不能改變既有行為（§P.2 R2）。

---

## §A.3 硬性限制

違反任何一條都不能合併。

1. **分層。** skill 腳本與 adapter 只 import `core` 與 `contracts`。hep-detector 的腳本與任何 adapter 都需要的程式（統計、判定、種子雜湊、summary 讀取）放在 `core/`，並在 `core/OWNERS.json` 指定 steward；`core/` 不得引用 `skills/`、`adapters/`、`profiles/` 的路徑。
2. **實驗名稱。** `skills/`、`contracts/`、`core/` 中不得出現實驗名稱（含 ALICE；`check_layering.py`）；需要時用引用鍵。
3. **Python 只用標準函式庫**；不加 Python 綁定。t 與 F 分位數（非整數自由度）與 Garwood 區間以既有的 `beta_ppf` 實作在 `core/stats/distributions.py`（這是共用的數值函式，不是 §A.9 所說的「新的 core 驗證器」）。
4. **C++ 依賴。** `g4sim` 的 `SimHash.hh`、`SimSummary.hh`、`MiniJson.hh` 只用 C++17 標準函式庫；`SimSeed.hh`、`SimProbe.hh` 與 `layered_sim` 連結 Geant4。不引入第三方函式庫。
5. **G5 授權邊界。** Python 只和獨立執行檔交換 JSON 與 CSV；程式依 Geant4 API 撰寫，不複製或改寫 Geant4 範例程式碼。
6. **狀態與退出碼**（`core/status.py`）：0 ok、1 負向判定（`refused`/`failed`）、2 無法使用的輸入（`rejected`）、3 `incomplete`。未定案與未達標一律是 3。
7. **execution trace。** 新的紀錄寫入者呼叫 `trace.provenance()`；新的共用函式呼叫 `trace.tag()`；呼叫 C++ 執行檔時記錄執行檔與原始碼的 sha256、版本、子命令。
8. **大小與路徑。** 單檔 ≤ 2 MiB（`check_packaging.py` 掃描所有文字檔）；寫出的路徑經 `tilde()`；plugin README 的大小聲明需在實際值的 10 % 內。
9. **入口預算。** hep-detector quick load ≤ 25,600 bytes（目前 24,669），description ≤ 1,024 字元（`measure_entrypoints.py` 回報 1,016）。本任務不修改 `skills/hep-detector/SKILL.md` 與 description。
10. **流程。** A1 依 sci-fix 流程；A2 依 adapter 變更流程；兩者都依 release 步驟。每個階段在自己的 isolated worktree 與分支（`geant4-a1`、`geant4-a2`）中工作（§P.10）；未經維護者核准不推送 `main`、不開 pull request。
11. **契約版本。** 新規則以 `strict or _at_least(contract_version, CV1)` 閘控，不設 warning 分支。
12. **J14 的離線重播** 永遠可以執行，且不需要 Geant4 與編譯器。
13. **不改既有輸出。** A2 只新增檔案與選用欄位；J14 既有 spec 的 CSV 必須和 A2 前逐位元相同（同一主機）。
14. **不做：** 整數量化、128 位元整數、逐位元相同的統計量、spec 格式轉換、`simstat`、不連結 Geant4 的 `simcore`（理由見 §R.13）。

---

## §A.4 設計摘要

### §A.4.1 已確認的缺陷（`9f08796`）

| # | 缺陷 | 位置 | 後果 | 工作項 |
|---|---|---|---|---|
| D1 | 範圍檢查不比對觀測量；宣告缺少的維度不受限制 | `validate.py` `_scope_inside()`（行 349 起）；`check_geant4_study.py` `scope_within()`（行 482–493） | 用 MPV benchmark 通過的研究可以把其他觀測量標成 `validated-in-scope` | A1.2 |
| D2 | benchmark 的等級由紀錄自己宣告 | `_study_upgrade`（行 395；篩選行 419） | 寫 `"grade": "reference"` 就能升級 | A1.1 |
| D3 | negative control 在不同單位間比較、只測單向 | `geant4_benchmarks.py` 行 678 | 偵測極限在觀測量上未被證明 | A1.10 |
| D4 | 收斂閘門無等價檢定 | `check_geant4_study.py` 行 359 | 真實差值等於容許值時約 50 % 通過 | A1.8 |
| D5 | MPV 的 SE 用 bootstrap | `geant4_benchmarks.py` 行 369 | 變異數估計不一致；J14 的偵測極限建立其上 | A1.6、A1.7 |
| D6 | 停止規則未禁止依結果加跑 | protocol 第 4 節 | optional stopping 偏差 | A1.11 |
| D7 | 證據相關性未揭露 | J14 的 nominal run 被閘門、統計目標、benchmark、variation 共用 | 被當作獨立證據 | A1.11 |
| D8 | study spec 的 benchmark enum 缺 `shower-containment` 與 `longitudinal-profile` | `geant4-study-spec.schema.json`；`GRADES` 9 個、enum 7 個 | 一致性缺口 | A1.12 |
| D9 | 研究層綁死 `layered_sim` 的資料格式 | `derived()` 讀 `geometry.layers`；`summarize` 與 benchmark 讀固定欄名 | 其他後端無法進入 | A2.6 |
| D10 | 測試順序相依 | `test_geant4_upgrade` 的 `tearDownModule` 刪除共用的 J14 重播目錄，`test_simulated_dataset` 的 5 個測試出錯 | 錯誤依執行順序而定 | A1.12 |

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
| reference | Geant4 所近似的物理模型或薄靶量測，在 isolated 目標上 | 能（範圍內） | A1（CV1） |
| setup-matched | 已發表的量測，目標雜湊和量測配置相同，且 isolated | 能（範圍內） | A1（CV1） |
| sanity、interface | 合理範圍、介面檢查 | 不能 | 既有 |
| verification | 輸入的精確推論（解析螺旋、運動學） | 不能 | B2（CV2） |
| regression | 前一個版本的同一研究 | 不能 | B2（CV2） |
| surrogate | 以完整模擬為參考的快速模擬或代理模型 | 不能改變物理 label | B2（CV2） |

### §A.4.5 `core/` 中的共用模組

| 模組 | A1 的內容 | 之後附加 |
|---|---|---|
| `core/stats/distributions.py` | `t_ppf`、`f_ppf`（非整數自由度）、`garwood` | — |
| `core/stats/batch_means.py` | 區塊估計量、SE、共變異、精確區間、直方圖分位數、MPV | C2：`values` 的經驗分位數 |
| `core/stats/decisions.py` | `equivalence`（IUT 閘門）、`detection_limit`；回傳 `{verdict, margin, reason}`，`reason` 取自封閉清單 | B2：`change`；C2：`threshold`、`order`、配對模式 |
| `core/simulation/seeds.py` | 種子雜湊 H、邏輯 run 種子、工作種子 | — |
| `core/simulation/summary.py` 與 `schemas/` | `simulation-summary/1`、`simulation-observables/1` 的 schema、讀取、驗證、合併 | A2：column map 與 effective config 的 schema；C2：`values` 欄位 |

hep-detector 的 `check_geant4_study.py` 與 `geant4_benchmarks.py` 改為呼叫這些模組；之後的任務也呼叫同一份實作。

---

## §A.5 階段 A1：正確性修正（contracts CV1，sci-fix）

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
- 表可在之後的契約版本附加條目（B2、C2）。
- J14 的判定不變，但 study 與 benchmark 檔案的內容會改變（新欄位；`code_paths` 多出 `contracts/validate.py`）。

### A1.2 範圍檢查（D1）

**修改：** `contracts/validate.py`（唯一實作，匯出）；`check_geant4_study.py`（匯入，刪除 `scope_within()`；`label` 寫 `declared_scope.observable_kind`）；study spec schema（`validation_plan.scope` 是 `additionalProperties: false`，加入 `observable_kind`、`target_geometry_sha256`、`hash_scheme`）。

**規則：**
- 比對受控的 `observable.kind`，不比自由文字。
- 宣告的 kind 必須在被計入 benchmark 的支持 kind 之內。
- 維度清單依 benchmark（A1.1 第四欄）；類別維度比集合包含，區間維度比區間包含；純量視為 [v, v]。
- benchmark 有的維度，宣告範圍都必須有；缺少視為超出範圍。
- 以目標雜湊為維度時，宣告範圍必須帶相同的 `target_geometry_sha256` 與 `hash_scheme`。
- 閘控：`strict or _at_least(contract_version, CV1)`；3.5.0 以下的紀錄只在 `--strict` 下受約束，且只有帶 `validated-in-scope` 的紀錄會失敗。

### A1.3 configuration 與隔離

**修改：** `geant4_benchmarks.py`（輸出）；`contracts/validate.py`（規則）；`contracts/dependencies.py`（重新推導）。

- `geant4_benchmarks.py` 為每個 benchmark 結果輸出 `configuration`、`target_geometry_sha256`、`hash_scheme: spec-v1`、`configuration_basis`，從 benchmark 設定的 `run_record` 所指 run record 的 spec/1 推導，不接受使用者輸入。計入升級的 benchmark 必須有 `run_record`。
- **目標：** benchmark 設定宣告 `target_slabs`（目標包含的 slab 名稱，含吸收層）。單層 benchmark 預設為被量測的那一片；`longitudinal-profile` 必須明列整個取樣堆疊（它的 `layers` 只列讀出欄位）。
- **真空：** 世界材料為 `G4_Galactic`，或密度 < 1e-20 g/cm³。
- **isolated：** 世界是真空，世界以外的每個放置都屬於目標；spec/1 沒有場，視為無場（場的規則在任務 B 生效：只有附加在目標內的場屬於目標並計入雜湊）。否則為 embedded。
- **`spec-v1` 的正規形式：** 依序的 slab、厚度、橫向尺寸、材料名稱與宣告的組成；重複放置逐一列出；數值以 Python `float.hex()`；對這個清單的 JSON（鍵排序、無空白）取 sha256。
- **契約規則（CV1）：** 被計入的 reference benchmark 必須 isolated；被計入的 setup-matched benchmark 必須 isolated，且目標雜湊與 `hash_scheme` 和 benchmark 的量測配置相同。缺少或 embedded 都是 error。`dependencies.py` **必須**從 `evidence_records` 中的 run record 重新推導並比對。
- 殘餘限制（寫入 protocol）：J14 的 recorded CSV 是縮減版，雜湊對不上 run record 的 `output_hashes`；configuration 描述的是設定檔指名的 run record。negative control run 的幾何不另外檢查。

### A1.4 邏輯 run、種子與角色

**修改：** 新增 `core/simulation/seeds.py`；`check_geant4_study.py`、`geant4_run.py` 呼叫它。

- **H 的定義**（Python 與 C++ 必須相同；C++ 在 A2.1 的 `SimHash.hh`）：H(x₁, …, x_n) = int.from_bytes(sha256("\x1f".join(str(x) for x in (x₁, …, x_n)).encode("utf-8"))[:8], "big") % (2³¹ − 1) + 1，值在 [1, 2³¹ − 1]；整數以十進位、無前導零寫成字串。
- 每個證據點是一個邏輯 run，種子 S = H(study_id, role, point_id)；正負兩向的控制組用不同的 point_id。
- **存放：** run record 的 `extension.simulation` 加入 `role`、`point_id`、`logical_run_seed`（S）與 `seed_scheme`（`hash-v1` 或 `legacy`）；A2 起執行用 spec 也寫入 `run.logical_run_seed`（A2.2）。
- A1 的新錄製一律 `seeding: stream`（`layered_sim` 現有行為）；單一工作的種子對為 (H(S, 0, 0), H(S, 0, 1))。不使用 `make_manifest` 的 `seed × 100003 + k`、`cmd_scan` 的 `[s0, s1 + k]`、`cmd_chunk` 的 `start + 1`。
- 一個邏輯 run 可以切成多個工作（`geant4_run.py chunk` 以手動建立的 manifest，每個工作涵蓋一段事件編號）：起始事件為 e 的工作，種子對為 (H(S, e, 0), H(S, e, 1))；`cmd_chunk`（行 504 的 `seeds=[max(1, args.seed), args.start + 1]`）改為以這個種子對執行，並在 manifest 中寫入該工作的種子 H(S, e, 0)。同一 manifest 內的種子因此彼此不同，`validate_manifest` 的 `partition.duplicate_seed` 檢查不需修改。`stream` 模式下不同切法的事件不同，但統計上等價。
- **角色：** `extension.simulation.role` 取自 evidence 角色 enum（trial、nominal、scan、control、variation、calibration）；未知的角色是 error（CV1 閘控）。enum 可在之後附加（B2 的 regression、C2 的 confirmation 與 search 角色）。
- **唯一性：** 同一研究的所有 run record 中 S 不重複（`check_geant4_study.py` 檢查）。A1 不重錄的 5 個 J14 run（A1.13）沒有 S：它們的 run record 不改寫；study record 中以原本的種子對（第一個種子 1401 或 1402）登記為 `seed_scheme: legacy`，只檢查完整種子對不重複。

### A1.5 summary、觀測量宣告與 Python 產生器

**修改：** 新增 `core/simulation/summary.py`（`simulation-summary/1` 的讀取、schema 驗證、依區塊合併、累加器的存取）與 `core/simulation/schemas/`（`simulation-summary/1`、`simulation-observables/1`）；新增 `adapters/geant4/assets/summary_from_csv.py`（或 `geant4_run.py` 的子命令 `summarize-blocks`），以 `core/simulation/summary.py` 寫出與合併。

- **觀測量宣告 `simulation-observables/1`：** 陣列，每項 `{name, source_column, selection, bins: {lo, hi, width}, thresholds, tolerance_mode, tolerance}`。`selection` 是對 CSV 欄位的宣告式篩選（欄名、比較子 `==`、`!=`、`<`、`<=`、`>`、`>=`、值；多個條件為 AND）；`thresholds` 給 `count_if` 用（計數 x > threshold 的事件，嚴格大於，和 `check_geant4_study.py` 的 `tail_fraction` 相同）；`tolerance_mode` 與 `tolerance` 見 A1.8。study spec（A1.12）與模擬程式的 `output.observables`（A2.3、B1.1）都引用它。
- **輸入：** 一個或多個工作的逐事件 CSV、觀測量宣告、區塊大小 B 與區塊數 K。
- **選擇：** 每個觀測量只累加滿足其 `selection` 的事件（宣告必須重現現行程式的選擇：`check_geant4_study.py` 中只有 `mpv_loss_MeV` 要求 `primary_fate == 1`（行 284），`mpv_deposit_MeV` 與 `tail_fraction` 使用全部事件（行 277–282）；benchmark 的 `transmitted()` 另要求 `primary_fate == 1` 且 `primary_end_process == "Transportation"`（`geant4_benchmarks.py` 行 232–236））；`n` 是通過選擇的事件數，另記錄每個區塊的總事件數。
- **區塊：** 事件 i（`event` 欄減去邏輯 run 的第一個事件編號）屬於區塊 ⌊i/B⌋；i ≥ K·B 的事件忽略並註明數量。
- **每個區塊、每個觀測量的累加器：** 整數 `n`、直方圖每格計數（固定分格；溢位與下溢分開）、`count_if[]`（x > threshold）；浮點 Σx、Σx²、`min`、`max`（Neumaier 補償加總）。
- **輸出欄位：** `summary_version`、`run`（邏輯 run 的識別與種子、`role`、事件範圍、`seeding`、B、K、spec 雜湊、產生者 `python-csv` 與版本）、`observables[]`、每個累加器的 `merge` 規則（`sum`、`min`、`max`、`hist`）。多個工作依區塊編號合併。schema 允許附加選用欄位（C2 的 `values`）。
- **事件權重：** CSV 有 `weight` 欄時必須全為 1，否則 exit 2（沉積已乘 track 權重，見 `Actions.cc` 行 113）。沒有 `weight` 欄時（J14 的 5 個縮減 CSV 就沒有），summary 記錄 `weight_column: absent`，並以 run record 的 spec 中沒有 biasing 指令作為依據；spec 中有 biasing 指令時 exit 2。
- A2 起 `layered_sim` 以相同 schema 寫出 summary；這個 Python 產生器只留在測試中作為 oracle。

### A1.6 估計量與 SE（D5）

**修改：** 新增 `core/stats/distributions.py` 與 `core/stats/batch_means.py`；`check_geant4_study.py`、`geant4_benchmarks.py` 改為呼叫它們（只讀 summary；刪除 `bootstrap()` 的正式使用，保留在測試中作為對照）。

- 每個區塊 b 算 θ_b；回報 θ̄ = 平均，SE = sd(θ_b)/√K，自由度 K − 1。K ≥ 16，在第一個證據 run 前宣告。
- 多個觀測量：每個區塊的估計量向量一起保存，共變異由這些向量估計。
- 全樣本值：平均與比例另由合併累加器算出，和 θ̄ 的差寫入紀錄作為診斷。
- 分位數：直方圖內線性內插；分格寬度除以估計值須小於相對容許值的 1/10；落在溢位或下溢格時判為 incomplete。
- **計數很少時：** 計數型估計量在任一區塊為 0 或合併總數 < 100（門檻可宣告）時，改用合併累加器上的精確區間：比例用 Clopper–Pearson（既有的 `clopper_pearson`），計數用 Garwood；兩個 run 的比較用條件二項法求率之比的區間，相對差 = 比 − 1（對 Poisson 計數是精確的；用於比例時只是近似，因為分母固定，protocol 註明）。這時沒有 SE，閘門以區間端點判定（A1.8）。
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
- **差值：** 沿用行 357 的慣例：a 為最細的設定，b 為第二細的設定（`vals` 由小到大排序，a = `finest[0]`、b = `finest[1]`）。觀測量宣告 `tolerance_mode`：`relative`（預設）時 diff = (a − b)/b、se_diff = √(se_a² + se_b²)/|b|；`absolute` 時 diff = a − b、se_diff = √(se_a² + se_b²)，tol 取觀測量宣告的 `tolerance`（同觀測量的單位；`absolute` 時必填）；`relative` 時 tol 為 study spec 的 `tolerance_relative`。ν 以 Welch 公式逐對計算（等變異數、K = 16 時為 30）。（`absolute` 的第一個使用者是 B3；因為它只是同一個函式的選項，放在 A1 以免之後改變閘門的定義。）
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
- trace tag（小寫連字號）：`geant4-scope-kind`、`geant4-configuration`、`geant4-convergence-iut`、`geant4-batch-means`、`geant4-mpv-block`、`geant4-seed-hash`。`check_geant4_study.py` 改 import `contracts.validate` 後，`code_paths` 會多出 `contracts/validate.py`，這是預期的變化。

### A1.12 其他修正（D8、D10）

- study spec 的 benchmark enum 補上 `shower-containment` 與 `longitudinal-profile`；grade enum（目前為 reference、sanity、interface）加入 `setup-matched`；observable kind enum 加入 `shower-maximum`；`validation_plan.scope` 加入 `observable_kind`、`target_geometry_sha256` 與 `hash_scheme`（setup-matched 用，A1.2）。
- study spec（頂層 `additionalProperties: false`）新增頂層屬性：`observables`（引用 `simulation-observables/1`；`name` 必須和 `convergence_plan.observables` 中的名稱相同，例如 `mpv_deposit_MeV`）與 `blocks: {K, B}`。既有的單數 `observable` 不變，仍是研究的主觀測量。
- `ext_computational_run.json` 在 schema 中宣告既有的 `simulation` 屬性（J14 的 run record 已帶 `extension.simulation`，`_study_upgrade` 也已檢查它；需 hep-computing 同意）。
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
- recorded 的大小在 A1 中量測（以 bytes 計，不用 `du` 的區塊用量）；單檔受 `check_packaging.py` 的 2 MiB（2,097,152 bytes）限制；整個 `recorded/` 的上限由維護者決定（§P.7 第 5 項）。

### A1.14 版本與 sci-fix 流程

- **版本：** contracts CV1（minor）。新增閘控規則族的先例（2.4.0、2.6.0、2.8.0、3.1.0、3.2.0）都是 minor。
- **ledger：** 下表每列一筆（D10 是測試修正，不入 ledger，只記在 CHANGELOG），`changelog` 為結構化物件（`{"kind": "unreleased", ...}`）。

| 缺陷 | ledger 條目 | 等級 | 理由 |
|---|---|---|---|
| D1（含依 benchmark 宣告的範圍維度） | scope-kind | S2 | 改變判定 |
| D2（含驗證類別） | grade-table | S2 | 改變判定 |
| D3（含 t 分位數的偵測極限） | control-shift | S2 | 改變判定 |
| D4（含差值與 se 的定義） | gate-IUT | S2 | 改變判定 |
| D5（含區塊 batch means 取代 bootstrap、精確計數區間、MPV 內插） | variance-method | **S1** | 改變回報的數值 |
| 隔離定義（含真空） | isolation | S2 | 改變判定 |
| D6 | stopping-rule | S3 | 只是指引 |
| D7 | evidence-overlap | S3 | 只是揭露，不改變判定 |
| D8 | enum-gap | S3 | 一致性，不改變判定 |

- **證據：** S2 需 C2 與 D2 層級；S1 需 C3 與 D2 層級（`docs/maintenance.md` 的證據層級；這裡的 C2、D2 是證據層級，不是契約版本或缺陷編號）。證據測試經 `validate.py` 與 `check_geant4_study.py` 的命令列執行，才能在 parent commit 上執行；不能執行的寫入 `gaps`。
- **advisory：** S1 與 S2 各一份，S3 不需要 advisory（`scifix_advisories.py check` 要求 advisory 的等級和每個列出的 ledger 條目相同）；編號取合併時下一個未使用者（目前為 SFA-2026-038 與 -039）。
  - 鍵：`artifact_types: [computational-run]`、`extension_keys: ["study", "evidence_records"]`。
  - 範圍：introduced 0.20.0，附 `database_specific.introduced_basis`；受影響版本 0.20.0–0.23.x 與未發布版本。
  - simulated dataset-record 無法用鍵區分；remedy 要求持有者對每個 simulated 表格執行 `contracts/dependencies.py`。
- 0.20.0 以後產生、帶 `validated-in-scope` 的 study record 在 `--strict` 下會失敗；advisory 說明處理方式（以新版本重產）。

### A1.15 A1 驗收

- [ ] kind 不符、宣告缺少維度、類別或等級與表不符、configuration 缺少或 embedded、目標雜湊或 `hash_scheme` 不符的紀錄，在 `--strict` 與 CV1 下被拒；`dependencies.py` 重新推導不符時被拒；純量範圍正確比對。
- [ ] 未知的角色、同一研究中重複的 S 被拒；legacy 種子的 run 依規則檢查。
- [ ] 重產的 J14 study record 通過 `validate.py --strict` 與 `dependencies.py`；判定的任何改變都記錄並說明原因（閘門 G-A1）。
- [ ] 閘門 toy（每格 10⁴ 次，依 A1.8 表頭說明的模型）和 A1.8 的表一致到 ±3σ_MC：「se = 目標」各欄只核對 TOST 部分，「兩階段」各欄核對包含達標條件的完整閘門；`absolute` 模式與計數很少時的區間判定有測試。
- [ ] 區塊 batch means 的覆蓋率 toy：J14 各類估計量（平均、比例、分位數、眾數）名義 90 % 區間的實際覆蓋率滿足 |覆蓋率 − 0.90| ≤ 0.02 + 3σ_MC，逐類回報。
- [ ] MPV 偏差 toy 的 95 % 上界 ≤ tol/10；每次的實測核對生效。
- [ ] 偵測極限 toy（A1.10 的 caught 定義）：在 DL 注入時抓到的機率 ≥ 0.977 − 3σ_MC；J14 的實現控制組結果記錄於 VALIDATION。
- [ ] J14 的離線重播由已提交的 summary 執行，判定符合 §A.4.3，不需要 Geant4 與編譯器。
- [ ] Python 產生器的單元測試：區塊劃分、選擇、合併、`weight ≠ 1` 時 exit 2、溢位格。
- [ ] 新的 `core/` 模組各有單元測試（`t_ppf`、`f_ppf`、`garwood` 對已知值；H 的測試向量），在 `core/OWNERS.json` 有 steward；一個只 import `core` 的測試（模擬 adapter 的用法）能讀 summary、計算估計量並呼叫 `equivalence`；`check_layering.py` 通過。
- [ ] `python3 -m unittest discover -s tests/contracts -t .` 沒有錯誤。
- [ ] 九筆 ledger 條目、兩份 advisory 通過 `scifix_advisories.py check`、parent record 齊全；live Geant4 證據以 release-gate 執行記錄；VALIDATION GEANT4-CORRECTNESS；CHANGELOG；release manifest。

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
| 存放 | 內容依 `config_sha256` 存放一次（`effective_configs/<config_sha256>.json`），相同設定的多個 run 只引用雜湊；`extension.simulation.effective_config` 放引用；提交的 J14 紀錄另附完整內容以便離線重播。schema 在 `core/simulation/schemas/` |

- 規則與 variation 的模型指派優先讀探針，讀不到才退回宣告，並輸出 `source: probe | declared`；兩者都有而不一致時報錯。
- 測試觸發：一個只在測試建置中存在的 UI 指令，在 `/run/initialize` 之後、第一次 `BeamOn` 之前呼叫探針，必須寫出 `recorded: false`。

### A2.5 column map（`simulation-columns/1`）

- `layered_sim` 每個 run 寫出 `column_map.json`，雜湊寫入 run record；schema 在 `core/simulation/schemas/`。
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

- 擴充 `contracts/schema.py`：`maxItems`、`maximum`、`exclusiveMaximum`（`layered_sim` 的 schema 已用到；`element_sim` 與任務 C 的 schema 也需要）。更新 `SUPPORTED_KEYWORDS`，並讓 `tests/contracts/test_schema_keywords.py` 也掃描 adapter 與 `core/simulation/schemas/` 的 schema。
- contracts 不升版（沒有契約 schema 使用新關鍵字）。
- `geant4_run.py` 的 `validate_spec()` 不被取代；A2.2、A2.3 只在它的鍵清單加入新欄位。

### A2.8 adapter 變更流程

| 項目 | 內容 |
|---|---|
| 版本 | 0.1.0 → 0.2.0 |
| `adapter.json` | `assets` 加入 `g4sim/`、`summary_from_csv.py`；更新 `purpose`；`status` 維持 `demonstrated-on-synthetic-data` |
| `SIM_SOURCES` | 加入 `g4sim/` 的檔案，讓 `sources_sha256` 涵蓋全部（B1 再改為依程式分組） |
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
- [ ] J14 的離線重播仍符合 §A.4.3。
- [ ] VALIDATION GEANT4-SUMMARY；CHANGELOG；release manifest。

---

## §A.7 契約與版本

| 物件 | 位置 | 版本 |
|---|---|---|
| benchmark 表（類別、kind、範圍維度）、範圍比對、configuration 與隔離、`hash_scheme`、evidence 角色、S 的唯一性 | `contracts/validate.py`、`contracts/dependencies.py`、`check_geant4_study.py` | CV1（minor、閘控、sci-fix） |
| `simulation` 屬性的宣告 | `contracts/schemas/ext_computational_run.json` | CV1（需 hep-computing 同意） |
| schema 關鍵字擴充 | `contracts/schema.py` | 不升版 |
| `core/stats/`、`core/simulation/` 的模組與 schema | `core/` | 隨 plugin 版本；schema 以 `summary_version`、`column_map_version`、`probe_version` 與 `simulation-observables/1` 的版本號管理 |
| `g4sim`、`seeding`、summary、column map、effective config 的寫出 | geant4 adapter | 0.2.0 |
| `GRADES`、kind 與 configuration 的輸出 | hep-detector | 隨 plugin 版本 |

computational-run schema 的擁有者是 hep-computing。CV2 屬任務 B（B2），CV3 屬任務 C（C2）。

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
- `tools/scifix_advisories.py check`（A1）
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
| `change`、`threshold`、`order`、配對比較、search 角色、`values` | 移到 B2、C2 | §P.2 R1 |
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

**待決事項**（編號見 §P.7）：第 1 項（CV1 的歸類）、第 2 項（`core/` 模組的 steward）、第 3 項（`simulation` 屬性）、第 4 項（兩階段係數與 J14 偶然失去升級時的處理）、第 5 項（J14 重錄與 recorded 上限）、第 6 項（精確區間的切換門檻）、第 7 項（G5 的確認方式）。

**殘餘風險：**
1. J14 的偵測極限可能因區塊 batch means、t 分位數與觀測量單位的控制組而改變，需要重新設計控制組。
2. 區塊 batch means 對偏斜分布的比值、分位數與眾數有 O(1/B) 的偏差，不隨 K 減少；覆蓋率 toy 容許 ±0.02，必要時加大 B。
3. 區塊獨立的前提在事件之間有狀態時不成立；探針標記 biasing，有疑慮時改為多個獨立的邏輯 run。
4. 以容差比較時，接近門檻的判定在不同平台可能不同；以邊距標記與「CI 平台為準」處理。
5. 自訂 `G4VAccumulable` 的 MT 合併需以測試確認行為。
6. 探針假設 worker 與 master 設定相同；若發現 thread-local 差異，改為逐執行緒傾印。
7. setup-matched 的目標雜湊只能證明配置相同，不能證明它就是論文中的配置；仍需審查者核對。
8. quick load 只剩 931 bytes。
9. 工作量：原型估計 A1 的契約部分約 8–12 個工作天，另加 Geant4 執行時間；統計部分與 A2 在開始時估計。

---

## §A.11 建議的執行步驟

每個階段開始時依 §P.10.2 建立並確認該階段的 isolated worktree，所有步驟都在其中進行；合併後依 §P.10.5 移除。

**A1**
1. 開始前檢查（§A.0）；套用 `prototype/phase1-core.patch`，補齊 A1.1–A1.3 缺少的部分。
2. 先修 D10（A1.12），之後一律以 `python3 -m unittest discover -s tests/contracts -t .` 整體執行。
3. A1.1 → A1.2 → A1.3（契約與 `dependencies.py`），加契約測試。
4. `core/simulation/seeds.py` 與 `summary.py`、schema、A1.5 的 Python 產生器；以 J14 的 5 個逐事件 CSV 離線產生 summary。
5. `core/stats/` 的三個模組（A1.6–A1.10），hep-detector 的腳本改為呼叫它們並改讀 summary；加 toy 測試（閘門、覆蓋率、MPV 偏差、偵測極限）與只 import `core` 的使用測試。
6. A1.4 的角色規則與 A1.11、A1.12 其餘項目（protocol、enum、`simulation` 屬性）。
7. 在 E2 先錄 trial run，依 A1.9 定事件數，再 live 重錄 J14 的掃描、variation 與負方向控制組（A1.13）；重產 J14 紀錄，跑 `--strict`。
8. A1.14：ledger、advisory、parent record、VALIDATION、CHANGELOG、release manifest；跑 §A.8 的檢查。

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
| 收斂閘門 | IUT；`relative` 或 `absolute`；se_diff；Welch ν；每點 se 目標 tol/(4√2)；通過需兩點都達標 | A1.8 |
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

## §A 附錄 C：基準核對值（`9f08796`）

| 項目 | 值 |
|---|---|
| `CONTRACTS_VERSION` | 3.5.0 |
| `GEANT4_UPGRADE_FROM` | 3.1.0（行 346） |
| J14 study record | contract 3.5.0，帶 `code_paths`、`code_tags` |
| J14 世界材料 | `G4_Galactic` |
| J14 `recorded/` | 2,447,979 bytes（約 2.45 MB；`du -sh` 顯示 2.6M）；`events/` 5 個縮減 CSV（`event`、`primary_eloss_MeV`、`edep_Si_MeV`、`primary_fate`、`primary_end_process`）；`runs/` 18 個 run record；`summaries/` 有全部 18 個 run 的單值摘要（`geant4-run-summary/1`）；5 個 run 另有逐事件 CSV，13 個掃描、variation 與情境 run 只有單值摘要 |
| J14 種子 | 未重錄的 5 個 run 的第一個種子為 1401 或 1402 |
| advisory | 最新 SFA-2026-037 |
| hep-detector | quick load 24,669 / 25,600 bytes；description 1,016 / 1,024 字元（`measure_entrypoints.py`）；`DetectorScriptCount` 21 |
| `GRADES` | `longitudinal-profile: "reference"`（行 92–94）；study spec 的 grade enum 為 reference、sanity、interface |
| `ext_computational_run.json` | 未宣告 `simulation`；J14 的 run record 已帶 `extension.simulation` |
| `core/stats` | steward hep-statistics；已有 `beta_ppf`、`clopper_pearson`；沒有 t、F 分位數與 Garwood |
| 分層規則 | adapter 只 import `core` 與 `contracts`（`tools/check_layering.py`） |
| `SUPPORTED_KEYWORDS` | 無 maxItems、maximum、exclusiveMaximum |
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
| **2026-10-23（本版）** | **依計畫（第 1 部）重新整理：A1 回到最小的 sci-fix（`change`、`threshold`、`order`、配對比較、search 角色、`values` 移到 B2、C2）；契約版本改記 CV1；種子雜湊放在 `core/simulation/seeds.py`；節的編號與任務 B、C 一致（§A.2 前提與提供的介面、§A.8 檢查、§A.10 待決與風險）** |
| 2026-10-23 | 加入 isolated worktree 的執行規定：檔頭、§A.0 的第一步、§A.11 的開頭（§P.10） |
| 2026-10-23 | 詳細檢查後修正：spec 新欄位同時加入 `validate_spec()`、`spec.schema.json`、`Spec.cc`；A1.5 的選擇與現行程式一致；`tolerance`、`count_if` 的方向；種子欄位的名稱與 `cmd_chunk`；trial run 與 N 進位到 K 的倍數；DL 的 tol 與 se_rel；`tree-v1` 的目標；`float.hex()` 的特殊值、`setTheSeeds`、`IsBlocked()` 與 general process；Box–Muller 的跨平台容差；ledger 補 D7、D8；事實更正（行號、`recorded/` 大小、`summaries/`、原型的描述） |

---

# 第 3 部　任務 B：`element_sim`、重建與 J15 最小磁譜儀（§B）

> 順序：B1 在 A2 之後；B2 在 B1 之後；B3 在 B2 之後。任務 C 的 C2 只等 B2，C3 等 B3
> 基準：撰寫時同任務 A（hep-research `main` 的 `9f08796`，contracts 3.5.0，Geant4 11.4.3）；開始前必須重新核對（§B.0）
> 日期：2026-10-23
> 範例性質：J15 是**合成幾何**，是 verification 的載體，不是任何實驗的偵測器；最接近的實際儀器是 PAMELA 與 AMS-02（§B.4.3）

---

## §B.0 任務卡

**目標。** 新增一個通用的盒狀元件 Geant4 程式 `element_sim` 作為第二個後端（場、平面穿越、量能器漏失、逐事件 ROOT 檔），加入不連結 Geant4 的重建程式 `simreco` 與新的驗證類別，再以它們完成 J15 最小磁譜儀研究。

**三個階段（依序，各自合併）：**

| 階段 | 內容 | 版本 |
|---|---|---|
| **B1** `element_sim` 與事件檔 | `element_sim.spec/1` 與 `element_sim`（盒狀元件、一層巢狀、場、平面穿越、量能器漏失）；逐事件 ROOT 檔；`simroot`；`geant4_run.py check-spec`；兩個後端的介面一致性；確定性場檢查 | geant4 adapter **0.3.0** |
| **B2** 重建與契約 | `simreco`（數位化與重建、可攜的亂數）；`geant4_run.py reco` 與 `table`；遞移的處理鏈；verification、regression、surrogate 類別與表條目；判定引擎的 `change`；regression 角色 | geant4 adapter **0.4.0**、contracts **CV2**（minor） |
| **B3** J15 研究 | 驗證梯、量能器 cut 收斂、variation、TOF σ_t 敏感度、recorded 資料、J15 journey 與文件 | 範例與文件（adapter 不升版） |

**不在範圍內：** 任務 A 的介面變更（必要時先在任務 A 範圍內以 adapter 修補版處理）；`layered_sim` 的新幾何功能（它凍結）；任務 C 的設計搜尋；離子源與 Birks（J17）；非盒狀幾何與場圖（§B.9）。

**交付物：** `element_sim`、`simroot`、`simreco` 與其測試；`geant4_run.py check-spec`、`reco`、`table`；CV2 的契約變更；J15 範例（`examples/` 下的新資料夾、README、recorded 資料）；J15 journey 與路由案例；VALIDATION 條目 GEANT4-ELEMENT（B1）、GEANT4-RECO（B2）、GEANT4-J15（B3）；CHANGELOG；release manifest。

**完成的定義：** B1.9、B2.6、B3.8 的驗收清單全部打勾；§A.8 的檢查全部通過；閘門 G-B1a、G-B1b（§P.6）通過。

**主要決定：**
1. **新增後端，不改 `layered_sim`。** `element_sim` 讓 J14 的程式不動，並以真正的第二個後端驗證輸出層介面（§R.3.2）。
2. **場精度用確定性檢查。** charged geantino 對解析螺旋，不需要統計；在 B1 完成（B1.7）。
3. **基礎設施與物理研究分開。** B2 只做 `simreco` 與契約，讓任務 C 的 C2 不必等 J15 研究（§P.1 P3）。
4. **J15 是 verification 的載體。** J15 研究的所有結果都是 `unvalidated`；選用的孤立 PVT 平板 benchmark 另立一份 study record（不屬於 J15 研究），示範新材料的升級路徑（B3.2）。
5. **hep-detector 不新增腳本。** 重建在 C++ 的 `simreco`，介面在 adapter；quick load 與 description 不變。

**第一步：** 依 §P.10.2 為本階段建立 isolated worktree（`.claude/worktrees/geant4-<階段>`，分支 `geant4-<階段>`，基底為已含前提階段的最新 `main`），並確認 `git rev-parse --show-toplevel`、`git branch --show-current` 與 `git status`。以下所有步驟都在這個 worktree 中進行。

**開始前必做：**
1. 確認 A2 已合併，§B.2 列的介面都存在。
2. 依 §A 附錄 C 的方法，以當時的 `main` 重新核對本部引用的事實（quick load、description 長度、journey 清單、`DetectorScriptCount`、contracts 版本、`MISSING_FILE_ARGS` 的結構），並更新本部（中英兩版）。
3. 讀 §A.1、§A.3、§A.4 與 §P.4–§P.6；本部不重複。

---

## §B.1 名詞與檔案

| 名詞 | 意義 |
|---|---|
| J15 | 本任務的最小磁譜儀（合成幾何） |
| `element_sim` | B1 新增的 Geant4 程式；spec `element_sim.spec/1` |
| 偏轉平面 | x–y 平面（B 沿 z）；非偏轉方向為 z |
| 剛度 R | p/\|q\|，單位 GV；C = 0.2998 GV/(T·m) |
| MDR | 最大可偵測剛度：只算量測項時 σ_R/R = 1 的剛度 |
| TOF 站 | TOF1 或 TOF2；每站兩層（a、b） |
| charged geantino | Geant4 中只受場作用、無物質交互作用的帶電測試粒子（質量 0，β = 1） |
| 處理鏈 | 模擬 → 縮減 → 數位化與重建 → 表格，每一步一份 computational-run 紀錄 |
| 記法 | 「B1.3」是本部的工作項；「§B.4.2」是本部的節；「A1.6」「C2.1」是任務 A、C 的工作項；「§A.3」「§P.4」「§R.6」是本文件其他部的節 |

**主要檔案（相對 `plugins/hep-research/`）：** `adapters/geant4/assets/g4sim/`（A2 建立，本任務擴充）；`adapters/geant4/assets/element_sim/`（新增）；`adapters/geant4/assets/simroot/`（新增）；`adapters/geant4/assets/simreco/`（新增，不連結 Geant4）；`adapters/geant4/assets/geant4_run.py`（新增 `check-spec`、`reco`、`table`；`SIM_SOURCES` 行 63 定義，行 327、386 使用）；`core/stats/decisions.py`（B2 加入 `change`）；`contracts/validate.py`、`contracts/dependencies.py`（CV2）；`skills/hep-detector/scripts/geant4_benchmarks.py`（`GRADES`、新的 benchmark 函式）；`skills/hep-detector/assets/geant4-study-spec.schema.json`；`skills/hep-detector/references/geant4-study-protocol.md`；`tests/skills/test_cli_robustness.py`（`MISSING_FILE_ARGS`，`geant4_run.py` 的條目在行 130）；`docs/researcher-journeys.md`、`docs/maintenance.md`、`docs/capability-matrix.md`（行 47 的「twenty-one scripts」，由 `tests/skills/test_documented_output_claims.py` 行 145 的測試類別 `DetectorScriptCount` 檢查）、`docs/capability-map.json` 與 `docs/capability-map.md`；`tests/examples/test_geant4_minimal_spectrometer.py`（新增）。

---

## §B.2 前提與提供的介面

**前提（任務 A 提供）：**

| 介面 | 任務 B 的用法 |
|---|---|
| benchmark 表、驗證類別、範圍比對、隔離規則（A1.1–A1.3） | B2 附加 verification、regression、surrogate 與 J15 的條目；J15 研究的 benchmark 都是 embedded，不計入升級；選用的孤立 PVT benchmark 是另一份 study record，依隔離規則判定（B3.2） |
| evidence 角色與 S 的唯一性（A1.4） | B2 附加 regression 角色 |
| 區塊估計量、精確區間、MPV、判定引擎 `equivalence`、兩階段事件數（A1.6–A1.10） | B3 的判定；B2 依同一介面加入 `change` |
| `simulation-summary/1`、`simulation-observables/1`（A1.5） | `element_sim` 與 `simreco` 以同一 schema 寫出 summary |
| `g4sim`：`SimHash.hh`、`SimSeed.hh`、`SimSummary.hh`、`MiniJson.hh`、`SimProbe.hh`、材料與 physics list 輔助（A2.1） | `element_sim` 使用全部；`simreco` 只用不連結 Geant4 的 `SimHash.hh`、`SimSummary.hh`、`MiniJson.hh` |
| `per-event` 種子（在 `GeneratePrimaries` 開頭重設，A2.2） | `element_sim` 只支援 `per-event` |
| 三個邊界產物、不含名稱的 `tree-v1`、effective config 存放（A2.3–A2.6） | `element_sim` 與 `simreco` 交出同樣的邊界產物；研究層不需修改；附加在目標內的場計入 `tree-v1` 目標雜湊 |
| schema 關鍵字 `maxItems`、`maximum`、`exclusiveMaximum`（A2.7） | `element_sim.spec/1` 的 schema |

**提供給任務 C 的介面：**

| 介面 | 工作項 | 任務 C 的用法 |
|---|---|---|
| `element_sim.spec/1` 與 `geant4_run.py check-spec` | B1.1、B1.6 | C1 的實現結果以子行程驗證；C2 的 F1/F2 評估 |
| 量能器母體與 `leak_*_MeV` | B1.3 | 量能器元件的目標 |
| `simreco`（剛度、β、量能器能量） | B2.1 | F1/F2 的重建 |
| 判定引擎 `change`、surrogate 類別 | B2.4 | C2 把 F0、F1 定位為 surrogate；C2 附加 `threshold`、`order` |

---

## §B.3 硬性限制

§A.3 的全部限制都適用。另外：

1. 不修改 `skills/hep-detector/SKILL.md` 與 hep-detector 的 description（quick load 只剩 931 bytes；description 1,016 / 1,024 字元）。J15 的路由案例必須沿用 description 中已有的觸發詞。
2. `skills/`、`contracts/`、`core/` 中不得出現實驗名稱；契約表與 protocol 引用 `longitudinal-profile` 的參考時用引用鍵。實驗名稱（PAMELA、AMS-02）只可出現在 `docs/` 與 J15 的 `examples/` README。
3. 場的程式依 Geant4 API 撰寫，不複製或改寫 B5 範例的程式碼（G5）。
4. 共享 stanza 的文字不改（點 5 寫「3.1.0 upgrade rule」；修改會牽動全部 SKILL.md 與 live 路由重跑）。
5. J15 的 `recorded/` 每檔 ≤ 2 MiB、總和 ≤ 3 MB；ROOT 檔不提交（B3.6）。
6. J15 研究的所有結果都是 `unvalidated`；J15 study record 中的 benchmark 都不得計入升級。選用的孤立 PVT benchmark（B3.2）另立一份 study record，不屬於 J15 研究，依 A1.3 的隔離規則判定。
7. `layered_sim` 不加幾何功能；新的幾何功能只加在 `element_sim`。
8. Python 與 `simreco` 都不直接解析 ROOT；一律經 `simroot`。
9. 契約規則以 `strict or _at_least(contract_version, CV2)` 閘控。

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
- TOF2 後層的後表面（520）距量能器前表面（550）30 mm；TOF1 前層（−810）在粒子源（−1000）之後。
- 世界包含粒子源與量能器後端。

材料（11.4.3 的 NIST 定義對照 PDG）：`G4_PLASTIC_SC_VINYLTOLUENE` 1.032 g/cm³、I = 64.7 eV；`G4_Si` 2.33 g/cm³（PDG 2.329）。

**刻意的簡化**（J15 的 README 逐條列出）：均勻場與銳利邊界、無磁鐵材料、矽為整片平面（無條帶、無電荷分享、未模擬 δ 射線造成的重心偏移）、TOF 每層不分割、無光學光子、無觸發與讀出電子學、無反符合。

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

整體門檻 0.75 GV；只要求徑跡加 TOF 時 0.51 GV。低於 0.364 GV 的軌跡從場區側面離開，之後在無場的世界中走直線。

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

J15 的 README 以這張表說明 J15 的合理性，並強調 J15 是合成幾何、不代表任何實驗。

---

## §B.5 階段 B1：`element_sim` 與事件檔（geant4 adapter 0.3.0）

### B1.1 `element_sim` 與其 spec

**位置：** `adapters/geant4/assets/element_sim/`（CMake 專案，連結 Geant4 與 `g4sim`）。

**spec `element_sim.spec/1`**（schema 放在同一目錄，只用 `contracts/schema.py` 支援的關鍵字）：

| 區塊 | 內容 |
|---|---|
| 座標 | 世界中心為原點，mm；元件以中心座標與半長給出（盒狀）。**所有中心座標都是世界座標**（包括子體）；`element_sim` 自行換算為母體座標放置（例如場區母體中心 x = −100，Si1 的世界中心 x = −500 → 母體座標 −400） |
| `materials` | NIST 名稱或混合材料（成分順序保留；`g4sim` 的材料輔助） |
| `elements` | 盒狀元件：名稱、材料、中心、半長、母體（世界或一個元件；只允許一層巢狀）、角色（`passive`、`tracker-plane`、`tof-layer`、`calorimeter`（母體）、`calorimeter-active`、`calorimeter-passive`）、重複（用於量能器的取樣層） |
| `field` | 均勻磁場：附加的元件、B 向量、精度參數（B1.2） |
| `physics` | physics list 與 EM 選項、cut、region（同 `layered_sim` 的語意，經 `g4sim`） |
| `source` | `type: gun`：粒子、能量（`energy_MeV` 或 `ekin_per_nucleon_MeV`）、位置、方向；`gps` 與 `event-file` 只定義介面（§R.9.2），遇到時 exit 2 |
| `run` | 事件數、執行緒、邏輯 run 種子；`seeding` 只允許 `per-event` |
| `output.observables`、`output.blocks` | 同 A2.3（引用 `simulation-observables/1`） |
| `output.event_file` | `level`：`none`（預設）、`summary`、`crossings`、`hits`；`compression`（預設 1）；`max_events_hits`（預設 100） |

- 跨欄位規則（元件不重疊、子體在母體內、名稱唯一、角色與材料相容）在 Python 的 adapter 中檢查（B1.6 的 `check-spec`）；C++ 只檢查執行所需的最低限度。
- 每個 run 交出三個邊界產物（summary、column map、effective config），與 `layered_sim` 相同。

### B1.2 場

- 在 `ConstructSDandField` 中建立 `G4UniformMagField`、`G4FieldManager`、`G4ChordFinder`，以 `G4ThreadLocal` 儲存；master 與每個 worker 各有一份。在 `Construct()` 中建立會讓 worker 共用非執行緒安全的 chord finder。
- 以 `SetFieldManager(fm, true)` 附在場區母體上，傳遞到所有子體。
- 有場時加入 `G4StepLimiterPhysics`。
- stepper 與 driver **明確建立**：以 `G4Mag_UsualEqRhs` 建立 `G4DormandPrince745`，包成 driver（例如 `G4InterpolationDriver<G4DormandPrince745>`），再以 `G4ChordFinder(G4VIntegrationDriver*)` 建構（中等信心，類別與建構子以 11.4.3 原始碼核對）；不用 `G4ChordFinder` 預設建構子所選的 stepper（那不受 `G4FieldParameters` 控制）。stepper 類別寫入 spec，探針以 RTTI 記錄 stepper 與 driver 的實際類別名（helix stepper 會讓場傳輸檢查失去意義）。實作前以 11.4.3 原始碼核對建構子的簽名。
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

- **探針：** `SimProbe.hh` 走訪 `G4LogicalVolumeStore`，以 `GetFieldManager()` 讀回 B、chord finder 與各精度參數；依指標去重，記錄原始附加的體積；註明 master 只看到 master 的副本。附加在目標內體積的場計入 `tree-v1` 目標雜湊。
- **MT 測試：** 只在測試建置中存在的 UI 指令，回報每個執行緒的 field manager 指標，必須彼此不同。

### B1.3 平面穿越與量能器漏失

- **穿越：** 主粒子（track ID 1）在 `tracker-plane` 或 `tof-layer` 元件**第一次**進入時（前步點狀態為 `fGeomBoundary` 且所在體積為該平面），記錄前步點的位置、方向、動能、全域時間、PDG 碼；每個平面一個「已記錄」旗標。粒子源若位於平面內，不會出現 `fGeomBoundary`，該平面不寫列。
- **量能器漏失：** 角色為 `calorimeter` 的母體元件，記錄每個事件中從母體內部離開母體的粒子帶走的能量（`post` 步點離開該母體的步；正子加 2 mₑc²；乘 track 權重），依離開的面分為 `leak_rear_MeV`（+x 面）、`leak_front_MeV`（−x 面）、`leak_lateral_MeV`（y、z 面），語意和 `layered_sim` 的同名欄相同（`layered_sim` 以世界邊界為面，`element_sim` 以量能器母體為面）。這三欄寫入 CSV、`events` ntuple 與 column map，供 shower-containment（`geant4_benchmarks.py` 行 487）與 B3.3 的後漏比例使用。
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
| `crossings` | `crossings` 起（`hits` 也包含） | 每事件 × 每個被穿越的平面一列 | `event_id`、`plane_id`、`track_id`、PDG 碼、前步點位置、方向、動能、全域時間 |
| `hits` | 只在 `hits` | 每個有沉積的步一列 | `event_id`、`track_id`、`step_index`（該 track 的步序號；和 `event_id`、`track_id` 組成唯一鍵）、`parent_id`、PDG 碼、`volume_id`、`copy`、前後步點位置、時間、沉積、步長、`process_id` |

- `process_id` 在初始化時以確定的規則指定（例如依 process 名稱排序），與執行緒和工作切分無關；`run` 與 `processes` 只由 master 填寫，worker 不寫這兩個 ntuple。
- `hits` 層級要求的事件數超過 `max_events_hits` 時，spec 驗證以 `rejected`（exit 2）拒絕。
- 估計（J15，`crossings` 層級）：壓縮前每事件最多約 4 kB（`crossings` 10 列 × 80 B、`deposits` 最多 110 列 × 28 B、`events` 約 120 B）；10⁵ 事件壓縮前最多約 400 MB。

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

- **`geant4_run.py check-spec --spec <file>`：** 以 schema 與跨欄位規則驗證 `element_sim.spec/1`（不需要 Geant4）；輸出 JSON 的 `{ok, problems[]}`，退出碼 0 或 2。任務 C 的 `detector-design` 以子行程呼叫它（adapter 之間不 import）。B1 把 `tests/skills/test_cli_robustness.py` 的 `MISSING_FILE_ARGS` 擴充為「每個腳本可對應一組或多組 argv」（目前 `geant4_run.py` 只有 `run` 一組，行 130），並登記 `check-spec`。
- `element_sim` 交出的三個邊界產物通過和 `layered_sim` 相同的介面測試（schema、雜湊、column map 的語意名稱）。
- **統計一致性只比兩個後端都產生的觀測量。** J14 的 `stopping-power`、`range` 與 `thin-layer-mpv` 需要 `primary_eloss_MeV`、`primary_fate`、`primary_end_process`（`geant4_benchmarks.py` 的 `transmitted()` 行 233、`bench_stopping_power` 行 284、`bench_range` 行 325、`bench_mpv` 行 365），`element_sim` 不產生這些欄，所以不比較 J14 的 benchmark 判定。
- 做法：和 J14 nominal 相同的平板（`Si_study` 以混合材料宣告相同的組成與密度、相同的物理設定與 cut），兩個後端各跑一個邏輯 run（`layered_sim` 用 `stream`、`element_sim` 用 `per-event`，事件不同）；比較矽中沉積 `edep_Si_MeV` 的平均與眾數（A1.7），以及量能器型配置的**總漏失**比例（`leak_rear_MeV + leak_front_MeV + leak_lateral_MeV` 除以入射能量；兩個後端的「面」不同，`layered_sim` 是世界邊界、`element_sim` 是量能器母體，單一面的比例不可比）。每個觀測量以 `equivalence`（A1.8）判定，容許值與 se 目標（se_diff ≤ tol/4）事先宣告；未通過時不合併（閘門 G-B1b）。

### B1.7 確定性場檢查（`field-propagation`）

不需統計；只需要 `element_sim`。

- 軌跡：charged geantino（質量 0，β = 1），剛度 0.6、1、10、100、1000 GV。
- 方向：正入射；偏轉平面內 **50 mrad，方向和偏轉相反**（正電荷取 +y）；非偏轉平面 ±50 mrad。
- §B 附錄 A 核對：在這組方向下，每條軌跡都到達每片 Si 和 TOF2 的兩層，也不離開場區母體。若改成順偏轉方向，0.6 GV 和 1 GV 會錯過 Si6。
- 參考：解析螺旋；軌跡離開場區時改為分段直線，只比較解析軌跡實際到達的平面。

| 掃描 | 格點 | 判定 |
|---|---|---|
| delta intersection | 1e-3、1e-4、1e-5、1e-6 mm | 名義值（1e-5）下，所有平面的平面內距離 √(Δy² + Δz²) ≤ 0.5 µm（ε/20），解析軌跡在平面的 x 上取值；最細兩組相差 ≤ 0.2 µm；另記錄 Geant4 穿越點的 \|x − x_平面\|。各格點的結果都回報，不預設 1e-3 mm 一定不通過（Geant4 的交點誤差主要沿 x，換成平面內誤差只約為斜率 × δ ≤ 0.25 µm） |
| 最大步長 | 100、30、10、3 mm | 同上 |
| delta one step 與 epsilon | 名義值與 1/10 | 預期無變化，做一次確認 |
| TOF2 路徑時間（兩層） | — | \|Δt\| ≤ 1 ps（約 0.3 mm 路徑長），只檢驗路徑長 |

- negative control：Geant4 端 B × (1 ± δ)，δ 由 trial run 選定，使偏差超過判定標準。
- 結果以 `field-propagation` benchmark（verification，B2.4 加入表）記錄；B1 中先以測試與 VALIDATION 條目記錄。B2 的 `field_propagation()` 重用 B1 的解析螺旋 oracle（同一份程式），不另寫。

### B1.8 adapter 變更流程

| 項目 | 內容 |
|---|---|
| 版本 | 0.2.0 → 0.3.0 |
| `adapter.json` | `assets` 加入 `element_sim/`、`simroot/`、`element_sim.spec/1` 的 schema；更新 `purpose` |
| `SIM_SOURCES` | 目前是一個扁平的檔名 tuple，只在 `ASSETS/"layered_sim"` 下計算雜湊（`geant4_run.py` 行 63 定義，行 327、386 使用）。改為依程式分組的對照表 `{"layered_sim": [...], "element_sim": [...], "simroot": [...], "g4sim": [...]}`，每個 run record 記錄所用程式及 `g4sim` 的檔案雜湊；場的程式放在 `element_sim/Field.hh`、`Field.cc`；`layered_sim` 的雜湊鍵不變，舊紀錄仍可比對 |
| G5 | 聲明「依 Geant4 API 撰寫，未複製或改寫任何範例程式碼（含 B5）」，由審查者在 VALIDATION 條目中確認；同一條目註明 ROOT 檔類型與 `simroot` |
| 測試 | 離線測試（spec 驗證、跨欄位規則、`check-spec`）；live 測試（`HEP_GEANT4_LIVE_TEST=1`）：幾何、場、事件檔、`simroot` 往返 |
| 文件 | `docs/capability-matrix.md` 的 Geant4 列；adapter 文件 |

### B1.9 B1 驗收

- [ ] `element_sim` 的 J15 幾何通過 overlap、物質預算與逐事件能量平衡；§B.4.1 與 §B.4.2 的核對數值由測試重算。
- [ ] `check-spec` 對每種跨欄位錯誤回傳 exit 2 與原因；合法的 spec 回傳 exit 0；`check-spec` 在擴充後的 `MISSING_FILE_ARGS` 中登記並通過缺檔測試。
- [ ] B1.6 的介面一致性與兩個後端的統計一致性（閘門 G-B1b）。
- [ ] `per-event` 下，同一邏輯 run 以 1、2、4 個工作與 1、2、4 個執行緒執行，summary 整數相同、浮點相對差 ≤ 1e-12。
- [ ] MT 測試指令回報的各執行緒 field manager 指標彼此不同；探針記錄的場參數和 spec 一致；場計入目標雜湊。
- [ ] B1.7 的確定性場檢查在名義值下通過，各格點的結果都回報，negative control 被抓到（閘門 G-B1b）。
- [ ] 量能器漏失：一個簡單配置（電子打在薄量能器上）中，`leak_*_MeV` 加上沉積與離開世界的能量滿足逐事件能量平衡。
- [ ] `simroot` 往返：各層級、I、D、S 欄的值相同；serial、不同執行緒數、1 個與 4 個工作的 `content_sha256` 相同（`processes` 去重後一致）；`deposits` 依事件加總等於 CSV 的子系統總沉積；`hits` 超過上限時 exit 2；run 中斷時 incomplete。
- [ ] VALIDATION GEANT4-ELEMENT；CHANGELOG；release manifest。

---

## §B.6 階段 B2：重建與契約（geant4 adapter 0.4.0、contracts CV2）

### B2.1 `simreco`（數位化與重建）

**位置：** `adapters/geant4/assets/simreco/`（CMake 專案；只用 C++17 標準函式庫與 `g4sim` 中不連結 Geant4 的 `SimHash.hh`、`SimSummary.hh`、`MiniJson.hh`；不連結 Geant4）。參數（ε、σ_t、名義 B、標定樣本）寫在 hep-detector 擁有的 reco spec 中。

**輸入：** `simroot dump` 從 ROOT 檔取出的 `crossings` 與 `deposits`（依鍵排序，經管線傳遞、不另存）以及摘要 CSV。

| 步驟 | 內容 |
|---|---|
| 矽 | 穿越點加高斯誤差：偏轉方向（y）ε = 10 µm，非偏轉方向（z）30 µm；擬合使用的 x 和 scorer 相同（入射面） |
| TOF | 每層的時間加獨立的高斯誤差 σ_t（100 ps；敏感度另做 150 ps）；站時間 = 兩層時間的平均（先以擬合軌跡把兩層的時間換算到站中心）；另外輸出每層的 dE/dx 與同站兩層的時間差 |
| 徑跡 | x–y 平面圓擬合，含多重散射共變異（否則 1 GV 時 χ²/dof 上千），得到曲率 κ；x–z 平面直線擬合，得到傾角 λ；以名義 B 計算 R_reco = C·B/(κ cos λ)（總動量，C = 0.2998 GV/(T·m)）；輸出 R、χ²、自由度 |
| 剛度真值 | 1/R_true = 六片平面穿越紀錄的 \|q\|/p_i 的平均（**總動量** p_i；單位電荷時 1/R = 1/p）；R_true 與 R_reco 都用總動量，避免 p 與 p_T 之差（50 mrad 時約 0.125 %，大於 μ 場檢查的 0.05 % 容許） |
| β | 路徑長以兩站中心為端點，包含 TOF1→Si1、Si6→TOF2 的直線段與三維傾角；低 β 時回報 β 在兩站之間的變化 |
| 量能器 | 主動層總沉積除以**電子**取樣比例；取樣比例由 `calibration` 角色的 10 GeV 電子樣本求得；另外輸出 e/mip |
| 亂數 | 每個事件的數位化亂數流以 `SimHash.hh` 的 SplitMix64 產生，種子為 H(S, i, "digi")（A1.4 的 H；S 為邏輯 run 種子，i 為事件編號），常態亂數用 `SimHash.hh` 的 Box–Muller；不用 `std::normal_distribution`（libstdc++ 與 libc++ 的輸出不同）。和 Geant4 的亂數流分開。同一平台逐位元相同；跨平台時 `log`、`cos` 等 libm 函式的實作不同，不保證逐位元相同，只要求相對差 ≤ 1e-12；建置時加 `-ffp-contract=off` |

**輸出：** 逐事件結果 CSV（R、χ²、β、量能器能量等）與 run summary（`simulation-summary/1`，產生者 `simreco`；觀測量如 (1/R_reco − 1/R_true)·R_true、β − β_true 的區塊累加）。

- **擬合器的單元測試：** `tracker_resolution.py` 不做擬合，只由拋物線最小平方算出曲率解析度（`curvature_sigma`，行 89）。測試比較的是：在無多重散射的 toy（R ≥ 300 GV）上，C++ 擬合的 σ(1/R) 與 pull 寬度，和 `tracker_resolution.py momentum` 給的量測項解析度（`mdr_intrinsic_gev`）在 toy 的 MC 誤差內一致；pull 寬度在 1 ± 3σ_MC 內。

### B2.2 `geant4_run.py reco` 與 `table`

- `reco`：執行 `simroot dump` 與 `simreco`；每次執行寫一份 computational-run 紀錄（含 `**trace.provenance()`、`simreco` 的程式雜湊、輸入 run record 的雜湊與 ROOT 檔的 `content_sha256`、dump 的 ntuple 與欄位清單）。改變數位化參數不需要重跑模擬。
- `table`：把重建的結果（例如剛度解析度對剛度）寫成 simulated dataset-record（含 `trace.provenance()`）。
- 退出碼依 `core/status.py`：0 ok、1 負向判定、2 `rejected`（無法讀取的輸入，含缺檔）、3 incomplete。
- **CLI 登記：** 在 B1 擴充後的 `MISSING_FILE_ARGS`（B1.6）中加入 `reco`、`table`。

### B2.3 結果表與遞移的處理鏈

- **遞移的處理鏈：** 目前 `dependencies.py` 要求 simulated 表格的每個輸入都是帶 `extension.simulation` 或 `extension.study` 的 computational-run；重建紀錄兩者都沒有。CV2 改為：輸入鏈可以任意深，只要每一層都是有紀錄的 computational-run，而且鏈的每個根都是模擬 run（需 hep-computing 同意；§P.7 第 8 項）。
- 研究是 `unvalidated` 時，表格保持 `unvalidated`；使用它的 communication 會得到 `communication.simulated_source` 警告，圖表標示「Simulation」。

### B2.4 驗證類別、表條目與 `change`

**新增的 benchmark 表條目**（A1.1 的格式；等級即類別；`GRADES` 與 study spec 的 benchmark、grade enum 同步加入；計算函式放在 `geant4_benchmarks.py`，只讀 summary 或 `simroot dump`）：

| benchmark | 類別 | 支持的 kind | 範圍維度 | 計算位置 |
|---|---|---|---|---|
| `field-propagation` | verification | — | — | `field_propagation()`，讀 `simroot dump` 的 `crossings` 與解析螺旋（B1.7） |
| `field-propagation-muon` | sanity | — | — | `field_propagation_muon()`，讀 `simreco` 的 summary |
| `tof-beta` | verification | — | — | `tof_beta()`，讀 `simreco` 的 summary |
| `tof-layer-consistency` | verification | — | — | `tof_layer_consistency()`，讀 `simreco` 的 summary |
| `sampling-fraction` | sanity | — | — | `sampling_fraction()`，讀 `element_sim` 的 summary |
| `regression-comparison` | regression | — | — | `regression_comparison()`，讀兩個版本的 summary |
| `surrogate-comparison` | surrogate | — | — | `surrogate_comparison()`，讀代理模型（a）與參考模擬（b）的 summary |

- **verification：** 不計入升級。
- **regression：** 角色 enum 加入 `regression`。同一研究、同一設定，在新舊兩個版本（plugin、後端或 Geant4）各執行一次；兩次的 point_id 為版本標籤，所以 S 不同、樣本獨立（不違反 A1.4 的唯一性）。只比較純量觀測量（直方圖的比較屬於 §B.9 延後的分布層級 benchmark）。兩個版本都必須是 A1 以後的 run（都帶 S 與 summary）。判定由判定引擎新增的 `change(diff, se, ν, tol, m)` 執行：`changed` = |diff| − t_{1−α/m}·se_diff > tol；`unchanged` = `equivalence` 的通過；其他為 `unresolved`。計數型觀測量和 `equivalence` 一樣走精確區間的分支（A1.7）。容許值與 α 事先宣告。紀錄不影響 label；reference 觀測量 `changed` 時可觸發 sci-fix 檢查。
- **surrogate：** 代理模型**永遠不改變物理 label**。代理模型的研究宣告參考研究（一份 study record，不是 run record；run record 不帶升級）與範圍；以 `equivalence` 判定（χ² 只作診斷）。比較時 a = 代理模型、b = 參考模擬。通過時記錄 `extension.study.surrogate = {reference_study_ref, reference_sha256, scope}`，scope 為宣告範圍與參考研究範圍的交集；`dependencies.py` 由參考 study record 重新計算 `reference_sha256` 與範圍交集並核對。任務 C 的 F0、F1 評估在架構上屬於這個類別。
- 閘控：`strict or _at_least(contract_version, CV2)`，無 warning 分支。

### B2.5 adapter 變更流程與 CI

| 項目 | 內容 |
|---|---|
| 版本 | 0.3.0 → 0.4.0 |
| `adapter.json` | `assets` 加入 `simreco/` 與 reco spec 的 schema；更新 `purpose` |
| `SIM_SOURCES` | 加入 `simreco` 分組 |
| CI | C++17 CI 工作建置與測試 `simreco`（必要或選用由維護者決定，§P.7 第 9 項） |
| 文件 | adapter 文件、`geant4-study-protocol.md`（驗證類別、處理鏈、`reco` 與 `table`） |

### B2.6 B2 驗收

- [ ] `simreco` 的擬合器單元測試依 B2.1 通過；`simreco` 在 CI 工作中建置與測試（必要工作；或維護者決定為選用時，選用工作加一份本機建置與測試紀錄）。
- [ ] `simreco` 的數位化結果在同一平台上逐位元相同；Linux（libstdc++）與 macOS（libc++）之間相對差 ≤ 1e-12（以 `-ffp-contract=off` 建置）。
- [ ] `simreco` 的 summary 通過與 A2.9 相同的一致性測試（Python 由逐事件結果 CSV 重算）。
- [ ] `reco`、`table` 在 `MISSING_FILE_ARGS` 中登記並通過缺檔測試。
- [ ] 三層以上的處理鏈（模擬 → 重建 → 表格）被 `dependencies.py` 接受；根不是模擬 run 時被拒。
- [ ] 新的表條目與 `GRADES`、study spec 的 enum 一致（一致性測試）；verification 類別不計入升級。
- [ ] `change` 的 toy：真實差值 = tol 時判 changed 的機率 ≤ α/m + 3σ_MC；回報真實差值 = 2·tol 時判 changed 的機率（檢定力）與真實差值 = 0 時判 unchanged 的機率；一個回歸檢查（例如 J14 在兩個 plugin 版本上）產生 `changed`、`unchanged` 或 `unresolved` 的紀錄且不影響 label。
- [ ] surrogate 的契約測試：帶 `extension.study.surrogate` 的紀錄宣告 `validated-in-scope` 時被拒；參考不是 study record 時被拒。
- [ ] J14 在 `--strict` 下仍通過。
- [ ] VALIDATION GEANT4-RECO；CHANGELOG；release manifest。

---

## §B.7 階段 B3：J15 研究

### B3.1 J15 的 study spec

- 宣告：觀測量（剛度解析度、β 解析度、取樣比例、總沉積、後漏比例；引用 `simulation-observables/1`）、K 與 B、benchmark、收斂計畫、variation、停止規則。
- 所有結果 `unvalidated`；README 與 study record 寫明「verification 載體」的定位。

### B3.2 驗證梯

| 檢查 | 類別 | 參考 | 規格 | negative control |
|---|---|---|---|---|
| overlap | 實作 | — | — | 平移一片 Si 造成重疊 |
| 逐事件能量平衡（J15 幾何） | 實作 | 能量守恆 | — | 不加 2 mₑc²、重複計入 |
| 物質預算（geantino） | 實作 | PDG X₀ 加總 | 容許約 2 %（Geant4 的 X₀ 公式和 PDG 約差 1 %） | Pb 密度 ± δ |
| `field-propagation` | **verification** | charged geantino 對解析螺旋 | B1.7 | Geant4 端 B × (1 ± δ) |
| `field-propagation-muon` | **sanity** | 平面平均的 1/R 真值（B2.1） | μ⁻ 1、10、100 GV；觀測量 (1/R_reco − 1/R_true)·R_true 的平均；以 `equivalence`（A1.8）判定，`tolerance_mode: absolute`，容許 0.05 %（觀測量本身已是相對量）；SE 目標 0.1 %，N 依 A1.9 由 trial run 決定（估計：1 GV 約 400、100 GV 約 7400，對應 SE 約 0.07 % 與 0.10 %） | Geant4 端 B × (1 ± 1 %) |
| 擬合器單元測試 | 測試（不是 benchmark） | B2.1 | — | — |
| 多重散射一次性比較 | sanity | `multiple_scattering.py` 的解析項（不含 log）；可另用 `toy_spectrometer.py`（需 NumPy） | μ 與 p，1–10 GV，含 β | — |
| `tof-beta` | **verification**（bookkeeping） | 沿真實軌跡的運動學 | — | scorer 測試旗標注入時間偏移；沒有 Geant4 端的物理控制組，文件中註明 |
| `tof-layer-consistency` | **verification**（bookkeeping） | 同站兩層的時間差對「層間路徑長 / βc」（β = 1、正入射時 66.7 ps） | 殘差平均為 0；寬度 √2 σ_t（100 ps 時 141 ps） | 以測試旗標在一層的 scorer 時間注入偏移 |
| `sampling-fraction` | sanity | PDG 的 μ 能損表（Groom 等，經 hep-citations 取得）在 run 動量下的游離 dE/dx 比 | μ⁻ 1 GeV；統計量為 Σ PVT 沉積 / Σ（PVT + Pb）沉積；合理範圍 ±10 %（審查者的 Bethe 估計約 0.271）；和 `calibration` 樣本用不同種子 | PVT 密度 ± δ |
| 簇射包容 | sanity | PDG gamma 剖面，混合物有效臨界能約 10.2 MeV | 電子 1–100 GeV；`leak_*_MeV`（B1.3） | — |
| `longitudinal-profile`（0.21.0） | 不適用 | 它的參考是已發表的 ALICE FoCal-E 量測，只對該堆疊有效；J15 的量能器不同，而且是 embedded | — | — |
| 選用：孤立 PVT 平板的 stopping power | reference（`configuration: isolated`） | Bethe（RPP 2024 式 34.5） | p、T = 200–600 MeV（βγ ≈ 0.69–1.30，低於 PVT 的 10^x₀ ≈ 1.40，密度修正為 0）、1 cm 平板、排除核作用（約 1 %）；Sternheimer 參數取自 Sternheimer, Berger & Seltzer (1984) 並以 hep-citations 核對 | PVT 密度 ± δ |

選用的最後一項在孤立平板中執行（`element_sim` 的單一元件），另立一份 study record，不是 J15 研究的一部分，用來示範新材料的升級路徑；它的 label 依 A1.3 的隔離規則判定，不影響 J15 研究的 `unvalidated`。事件數與判定依 A1.6–A1.10。

### B3.3 量能器 production cut 收斂

- 格點：0.1、0.3、0.7、1.0 mm。
- 樣本：10 GeV e⁻；先跑 trial，再依 A1.9 決定 N。
- 觀測量：總沉積（相對容許 1 %，約 400 個簇射/點）、後漏比例（`leak_rear_MeV` 除以入射動能，只算量能器母體的後表面；**絕對**容許 0.002，`tolerance_mode: absolute`，約 5000 個簇射/點）。這兩個數不含兩階段因子 f ≈ 1.97（A1.9）；含 f 時約 770 與 9,900 個簇射/點。
- 每點事件數取兩者的較大值；判定依 A1.8（`equivalence`）。
- Si 的 production cut 不在 J15 收斂：它只影響 Si 的沉積，而 J15 的 Si 結果不作為證據。study spec 的 `convergence_plan.observables` 加入總沉積與後漏比例。各 benchmark 依賴的參數組事先宣告，並以探針的實際設定核對。

### B3.4 variation

| variation | 範圍 | 規則 |
|---|---|---|
| EM option4 對 option3 | 量能器剖面、取樣比例 | `G4R-PRECISION-EM` |
| FTFP_BERT_EMZ 對 **QGSP_BIC_EMZ** | 1.5 GeV 以下核子；觀測量為末態量：第一次作用後 5 層的沉積、作用後的帶電次級粒子能量。作用機率與第一次作用深度只在探針確認兩者的非彈性截面不同時才回報（兩個 physics list 可能共用核子截面，那時差值必為 0；這和 protocol §6 Variations（行 157–162）警告的「共用模型造成假零」是同類問題） | `G4R-BIC-RANGE`；3 GeV 以下 π、6–12 GeV 強子兩者模型相同，不得作為 variation |
| 真空對空氣 | 多重散射、剛度解析度 | — |

### B3.5 TOF 時間解析度的敏感度

- `simreco` 以 σ_t = 100 ps 與 150 ps 各重建一次（同一份模擬，不需重跑）。
- 回報兩者的 σβ/β（預期約 2.3 % 與 3.5 %）與 β 解析度對剛度的影響；README 說明 100 ps 比 AMS-02 的系統解析度（約 140 ps）樂觀。

### B3.6 recorded 資料預算

- `check_packaging.py` 的單檔上限 2 MiB（`MAX_BYTES = 2 * 1024 * 1024`，單位 bytes）；J14 的 `recorded/` 總和為 2,447,979 bytes（約 2.45 MB；`du -h` 顯示的 2.6 MB 含檔案系統區塊）。
- ROOT 檔不提交；run record 只記錄路徑、檔案 sha256、`content_sha256`、各 ntuple 列數與大小；測試需要的 ROOT 檔在 live 測試中產生。
- J15 只提交：run summary（模擬與重建）、effective config（依內容雜湊存放）、column map、縮減欄位的摘要 CSV（benchmark run）、以 `simroot dump --events` 取出的縮減穿越與沉積紀錄（供離線重播 `simreco` 的測試；事件子集依預算決定）、重建的結果表。
- 每檔 ≤ 2 MiB，J15 的 `recorded/` 總和 ≤ 3 MB。

### B3.7 註冊、journey 與文件

| 項目 | 內容 |
|---|---|
| 腳本計數 | hep-detector 不新增腳本；計數測試（`tests/skills/test_documented_output_claims.py` 行 145 的 `DetectorScriptCount`）維持 21，`docs/capability-matrix.md` 行 47 的「twenty-one scripts」不變 |
| 路由表 | 不修改 `skills/hep-detector/SKILL.md`；J15、`element_sim` 與 `simreco` 的說明放在 `geant4-study-protocol.md` 與 adapter 文件 |
| journey | J15；`docs/researcher-journeys.md`、`docs/maintenance.md` 範例表；`tests/examples/test_geant4_minimal_spectrometer.py`（重播並比對判定） |
| capability | `docs/capability-map.json` 與 `docs/capability-map.md`（在 `full-detector-simulation` 下新增項目，執行 `capability_map.py --write`）、`docs/capability-matrix.md` |
| 路由 | 新增 J15 的路由案例；`check_routing_static.py` 從 `docs/researcher-journeys.md` 讀取 journey 清單，所以 J15 一列入表就**必須**有路由案例。重跑 live 的 Geant4 案例，包括既有的繁中欠規格案例 `g4-underspec-2` |
| 描述長度 | description 1,016 / 1,024 字元；路由案例沿用已有的觸發詞，不改描述 |
| README | J15 的簡化清單（§B.4.1）、和 PAMELA 與 AMS-02 的對照（§B.4.3）、「合成幾何、verification 載體」的定位 |
| 獨立審查 | 本任務的 Markdown（protocol 變更、J15 README、本部）以 0.22.0 的 `review.py` 審查；紀錄只是 advisory，依 O04/O14 不取代人工的 G5 確認 |
| 其他 | `reference_inventory.py --check`、CHANGELOG、release manifest |

### B3.8 B3 驗收

- [ ] `field-propagation`（B1.7 的結果，以 B2.4 的表條目寫成 benchmark 紀錄）、`field-propagation-muon`、`tof-beta`、`tof-layer-consistency`、`sampling-fraction`、簇射包容執行完成並列入 J15 的 study record；執行選用的孤立 PVT benchmark 時，它的 study record 另外列出；各自的 negative control 依 B3.2 被抓到，或註明沒有控制組。
- [ ] 量能器 cut 收斂（B3.3）與 variation（B3.4）完成，判定與 incomplete 的比例記錄於 study record。
- [ ] TOF σ_t 的 100 與 150 ps 敏感度已回報。
- [ ] recorded 預算、註冊項目、文件全部完成；J15 的離線重播測試通過。
- [ ] 獨立 agent 只依文件與工具完成「1 GV 質子在 J15 的剛度解析度」：結果紀錄通過 `validate.py --strict`、label 為 `unvalidated`、解析度（(1/R_reco − 1/R_true)·R_true 分布的中央 68 % 半寬）落在 §B.4.2 多重散射表 1 GV 質子一列的範圍內（1.8–2.6 %，量測項在 1 GV 可忽略），過程不需要維護者協助。
- [ ] VALIDATION GEANT4-J15；CHANGELOG；release manifest。

---

## §B.8 契約與版本

| 物件 | 位置 | 版本 |
|---|---|---|
| `element_sim`、`element_sim.spec/1`、`element_sim.events/1`、`simroot`、`check-spec` | geant4 adapter | 0.3.0（B1） |
| `simreco`、reco spec、`reco`、`table` | geant4 adapter（C++，不連結 Geant4） | 0.4.0（B2） |
| verification、regression、surrogate 類別與表條目；regression 角色；遞移的處理鏈 | `contracts/validate.py`、`contracts/dependencies.py` | CV2（minor、閘控） |
| 判定引擎 `change` | `core/stats/decisions.py` | 隨 plugin 版本 |
| `GRADES` 與 study spec 的 enum；`convergence_plan.observables` 加入總沉積與後漏比例 | hep-detector | 隨 plugin 版本 |

---

## §B.9 不做與延後

| 項目 | 決定 | 理由 / 觸發條件 |
|---|---|---|
| 量測主導區 σ(1/R) 作為 benchmark | 不做 | 改為擬合器單元測試 |
| `skills/hep-detector/scripts/digitize_reconstruct.py` | 不做 | 改為 C++ 的 `simreco` |
| `layered_sim` 的新幾何功能 | 不做 | 新功能只加在 `element_sim` |
| 管線中以 Python 直接讀 ROOT（uproot） | 不做 | 經 `simroot` |
| 離子源與 Birks 可見能量（J17） | 延後 | 宇宙線核素研究，且 PVT 的 Birks 常數有文獻紀錄。實作時依 11.4.3：在 `GeneratePrimaries` 中以 `GetIon(Z, A)` 取得離子；在 `Construct` 設定 kB（`GetIonisation()->SetBirksConstant`）、PreInit 呼叫 `G4EmParameters::Instance()->SetBirks(true)`，再以 `G4LossTableManager::Instance()->EmSaturation()` 取得（API 名稱實作時以 11.4.3 原始碼核對） |
| `element_sim` 的非盒狀 solid、旋轉、GDML 讀入、field map、邊緣場 | 延後 | 第一個需要它們、又不能用使用者應用的研究（任務 C 的圓柱幾何也以此為觸發） |
| `element_sim` 的主粒子出射紀錄（J14 的觀測量） | 延後 | 把 J14 遷移到 `element_sim` 並退役 `layered_sim` 時（§P.8） |
| 分布層級的 benchmark（含 regression 的直方圖比較）、觀測量的組合、profile、`gps` 與 `event-file` 粒子源、`simreduce` | 延後（介面已定義於 §R.9.2） | 各自的第一個用例 |
| RNTuple、vector 欄 | 延後 | ROOT 檔大小或讀取速度成為瓶頸 |

其他不做與延後的項目見 §A.9。

---

## §B.10 待決事項與殘餘風險

**待決事項**（編號見 §P.7）：第 7 項（G5 的確認方式）、第 8 項（遞移的處理鏈與 CV2 的歸類）、第 9 項（`simreco` 的 CI 工作）、第 10 項（ROOT 檔的存放）、第 11 項（`element_sim` 的維護歸屬）。

**殘餘風險：**
1. 取樣比例的參考需要 PDG 的 μ 能損表；選用的 PVT benchmark 需要 Sternheimer 參數。兩者都要經 hep-citations 取得文獻紀錄後才能使用。
2. 量能器簇射主導 CPU 時間；後漏的收斂每點約需 5000 個簇射（含兩階段因子約 9,900），事件數由 trial run 決定並記錄。
3. `G4RootAnalysisReader` 的讀取能力未驗證（閘門 G-B1a）。
4. 大樣本的 ROOT 檔可達數百 MB；MT 合併時 worker 的資料可能在記憶體中累積到 run 結束（實際行為依 11.4.3 的 ntuple merging 與 basket 設定，未核對）；`hits` 有事件數上限，大小與記憶體在 trial run 中確認。
5. 兩個 Geant4 程式的維護成本；靠 `g4sim` 控制重複（§P.8）。
6. 強子 variation：若兩個 physics list 的核子非彈性截面相同，作用機率不會改變；只回報末態量（B3.4）。
7. 部分 Geant4 行為（stepper 的建立、Birks 的 API、交點誤差的方向）依審查者的經驗判斷，未逐行核對 11.4.3 原始碼；實作時先核對。
8. 工作量在 B1 開始時依實際的 `g4sim` 估計。
9. 任務 A 的殘餘風險（區塊獨立的前提、接近門檻的判定、探針假設 worker 與 master 設定相同）同樣適用，見 §A.10。

---

## §B.11 建議的執行步驟

每個階段開始時依 §P.10.2 建立並確認該階段的 isolated worktree，所有步驟都在其中進行；合併後依 §P.10.5 移除。

**B1**
1. 開始前檢查（§B.0）；`G4RootAnalysisReader` 的一天試作（閘門 G-B1a）。
2. `element_sim` 的 spec、schema、`check-spec` 與幾何（B1.1、B1.6）；以 J14 相同的平板配置做兩個後端的一致性。
3. 場（B1.2）與 MT 測試；確定性場檢查（B1.7）。
4. 建立 J15 幾何（§B.4.1）；通過 overlap、物質預算、能量平衡；以測試重算 §B.4.1、§B.4.2 的核對數值。
5. 平面穿越與量能器漏失（B1.3）、ROOT 檔（B1.4）、`simroot`（B1.5）。
6. B1.8 的 adapter 變更項目；B1.9 全部打勾；跑 §A.8 的檢查。

**B2**
1. `simreco` 的擬合器單元測試，再接 `simroot dump` 的輸入（B2.1）；CI 工作。
2. `reco` 與 `table`、`MISSING_FILE_ARGS` 的擴充（B2.2）；遞移的處理鏈（B2.3）。
3. 驗證類別、表條目、`change`、regression 角色與契約測試（B2.4）。
4. B2.5 的 adapter 變更項目；B2.6 全部打勾；跑 §A.8 的檢查。

**B3**
1. J15 的 study spec（B3.1）；在 E2 執行驗證梯（B3.2）。
2. 量能器 cut 收斂、variation、TOF 敏感度（B3.3–B3.5）。
3. recorded 資料、註冊、journey、文件、獨立 agent 的驗收題（B3.6–B3.7）；B3.8 全部打勾；跑 §A.8 的檢查。

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
- PAMELA 與 AMS-02 的出處見 §R.14
- 待取得：PDG 的 μ 能損表（Groom, Mokhov & Striganov）；Sternheimer, Berger & Seltzer (1984), *Atomic Data and Nuclear Data Tables* 30, 261

## §B 附錄 C：版本歷程

| 版本 | 內容 |
|---|---|
| 探測器文件與 v5 | 單軸疊層磁譜儀；Gluckstern 小 N 公式更正；磁場方向與場檢查網格 |
| 2026-10-22 | TOF1、TOF2 各兩層；數位化與重建改為 C++；逐事件 ROOT 檔；拆分為任務 B；依新架構改寫（`element_sim` 取代 spec/2；B1、B2；PAMELA、AMS-02 對照與 TOF 敏感度） |
| 2026-10-23 | 獨立審查後修正（B1.6 只比共同觀測量、量能器漏失、表條目、surrogate 與 regression 規則、總動量剛度、CLI 與 `SIM_SOURCES`、可攜的亂數、stepper 明確建立等） |
| **2026-10-23（本版）** | **依計畫（第 1 部）重新整理：B2 拆為 B2（重建與契約）與 B3（J15 研究），讓任務 C 的 C2 只等 B2；確定性場檢查移到 B1.7；新增 `geant4_run.py check-spec`（B1.6，供任務 C 以子行程使用）；判定引擎的 `change` 與 regression 角色在 B2 加入；契約版本改記 CV2；節的編號與任務 A、C 一致** |
| 2026-10-23 | 加入 isolated worktree 的執行規定：檔頭、§B.0 的第一步、§B.11 的開頭（§P.10） |

---

# 第 4 部　任務 C：自動化探測器設計搜尋（§C）

> 順序：C1 在 A1 之後（可與 A2、B 平行）；C2 在 B2 與 C1 之後；C3 在 B3 與 C2 之後
> 日期：2026-10-23
> 一句話：使用者寫下物理需求；Claude 從元件目錄自由選擇探測器結構種類並組合，最佳化器在多保真度的模擬上搜尋，最後以獨立的確認 run 回報符合需求的最佳設計與取捨

---

## §C.0 任務卡

**目標。** 讓 AI 從「物理需求」出發，自行選擇探測器結構種類（徑跡平面、磁場區、TOF、量能器、被動層……）並自由組合與調整參數，得到符合需求的最佳化設計（或一組取捨的 Pareto 前緣），而且結果經得起統計與來源的檢查。

**三個階段：**

| 階段 | 內容 | 前提 | 版本 |
|---|---|---|---|
| **C1** 需求、文法與快速搜尋 | 需求規格、元件目錄、設計文法與實現、F0 解析評估、標準函式庫的搜尋器（Sobol、NSGA-II）、搜尋紀錄（F0-only）、agent 協定、封閉測試 | A1 | 新 adapter `detector-design` **0.1.0** |
| **C2** 模擬評估與確認 | `core/` 的附加（`threshold`、`order`、配對比較、`values`、search 角色與 seed_group）；F1/F2 評估；確認 run 與需求判定；穩健性與防護；CV3 | B2、C1 | detector-design **0.2.0**、geant4 adapter **0.5.0**、contracts **CV3**（minor） |
| **C3** 範例 | J16 自動設計範例（與 J15 比較）；選用的 MOBO 後端；journey 與路由 | B3、C2 | detector-design **0.3.0** |

**不在範圍內：** 可微分模擬與可微分代理模型（MODE 路線，§C.9）；非盒狀幾何（圓柱形對撞機探測器）；光學物理（Cherenkov、RICH）；強化學習；讓 LLM 單獨決定最佳設計。

**交付物：** `adapters/detector-design/`（schema、目錄、實現、評估、搜尋、報告）；`core/` 的附加（C2.1）；hep-detector 的 reference `detector-design-search.md`（含 agent 協定）；CV3 的契約規則；封閉測試；J16 範例；VALIDATION 條目 DESIGN-SEARCH-F0（C1）、DESIGN-SEARCH（C2）、DESIGN-SEARCH-J16（C3）；CHANGELOG；release manifest。

**完成的定義：** C1.9、C2.9、C3.4 的驗收清單全部打勾；§A.8 的檢查全部通過；閘門 G-C1、G-C2a、G-C2b、G-C3（§P.6）通過。

**主要決定：**
1. **Claude 是設計者，不是裁判。** Claude 選結構種類、提出種子設計、劃定搜尋範圍、解讀結果；「哪個設計最好、是否符合需求」只由有紀錄的評估與統計判定。Claude 的提案和隨機產生的候選走同一條評估管線，沒有特權（§C.4.2）。
2. **自由組合，但在文法之內。** 結構的自由度來自「元件目錄 × 組合規則」：任何通過有效性規則的元件序列都是合法設計。新的元件種類只能經由審查過的目錄變更加入（§C.4.4）。
3. **多保真度。** F0 解析式篩選 10⁴–10⁶ 個設計；F1 少量事件的 Geant4 細化數百個；F2 完整統計只給少數決選者（§C.4.5）。
4. **搜尋與確認分開。** 搜尋階段的數值有「贏家詛咒」，只作排序，永遠不當結果回報；回報的性能只來自事先宣告、種子獨立的確認 run（§C.4.7）。
5. **結果是提案，不是驗證。** 搜尋出的設計 label 一律 `unvalidated`；紀錄寫明「以模擬最佳化的設計」，並附搜尋規模、確認 run 與穩健性。
6. **任務 C 需要的統計附加由任務 C 自己加入**（§P.2 的 R1），位置在 `core/`，讓 hep-detector 與 adapter 共用（C2.1）。

**第一步：** 依 §P.10.2 為本階段建立 isolated worktree（`.claude/worktrees/geant4-<階段>`，分支 `geant4-<階段>`，基底為已含前提階段的最新 `main`），並確認 `git rev-parse --show-toplevel`、`git branch --show-current` 與 `git status`。以下所有步驟都在這個 worktree 中進行。

**開始前必做：** 讀 §P.0–§P.6；讀 §A.1、§A.3、§A.4 與 A1.4–A1.9；C2 另讀 §B.4、B1.1、B1.6、B2.1、B2.4。依 §A 附錄 C 的方法核對本部引用的事實。

---

## §C.1 名詞與檔案

| 名詞 | 意義 |
|---|---|
| 需求規格 | `detector-requirements/1`：物理目標（objective）、硬性需求（constraint）、資源限制與包絡，事先宣告 |
| 設計文法 | `detector-design/1`：由元件目錄中的元件依組合規則排成的設計描述 |
| 元件目錄 | `catalogue/1`：可用的結構種類（block type），每種有參數、範圍、有效性規則、實現規則與質量／成本模型 |
| 實現（realize） | 把一個設計轉成 `element_sim.spec/1`（與 `simreco` 的 reco spec）的確定性函式 |
| 基因（genome） | 搜尋器看到的設計編碼：結構（哪些元件、順序、數量）＋類別參數（材料）＋整數＋連續參數 |
| 保真度 F0、F1、F2 | F0 解析式；F1 少量事件的 Geant4；F2 依任務 A 統計規格的完整評估 |
| 決選者 | 進入 F2 與確認的少數設計 |
| 確認 run | role 為 `confirmation` 的邏輯 run，種子不曾在搜尋中使用；回報的性能只來自它 |
| 贏家詛咒 | 從 n 個帶雜訊的評估中選最佳者時，其估計值的期望偏樂觀 |
| Pareto 前緣 | 沒有任何其他設計在所有目標上都不差且至少一項更好的設計集合 |
| 搜尋規模 | 各保真度實際評估的設計數；寫入紀錄，類似 look-elsewhere |
| seed_group、配對比較 | 一組共用 S 的 run；以逐區塊差值估計差值的 SE（common random numbers；C2.1） |
| 記法 | 「C1.3」是本部的工作項；「A1.8」「B2.1」是任務 A、B 的工作項（工作項編號全文唯一）；「§C.4」是本部的節；「§A.3」「§P.7」「§R.6」等是同一文件其他部的節 |

**主要檔案（相對 `plugins/hep-research/`）：** `adapters/detector-design/`（新增：`adapter.json`、`assets/design_search.py`、`assets/catalogue/`、`assets/schemas/`）；`core/stats/decisions.py`、`core/stats/batch_means.py`、`core/simulation/summary.py`、`core/simulation/seeds.py`（C2 附加）；`contracts/validate.py`、`contracts/dependencies.py`（CV3）；`adapters/geant4/assets/g4sim/SimSummary.hh`（C2 加入 `values`）；`skills/hep-detector/references/detector-design-search.md`（新增）；`core/physics/tracking.py`（C1 新增：由 `tracker_resolution.py` 抽出的 `curvature_sigma` 與散射式）；`skills/hep-detector/scripts/tracker_resolution.py`、`multiple_scattering.py`（C1 改為呼叫 `core/` 的函式，輸出不變）；`adapters/detector-design/assets/catalogue/materials.json`（C1 新增，隨附的材料表）。

---

## §C.2 前提與提供的介面

| 提供者 | 介面 | 任務 C 的用法 | 需要於 |
|---|---|---|---|
| 任務 A | `core/simulation/seeds.py`（H、S） | F1：S = H(search_id, role, seed_group)；F2 與確認：S = H(search_id, role, design_sha256)（C2.1） | C1（紀錄）、C2 |
| 任務 A | `core/simulation/summary.py`、`simulation-observables/1` | 搜尋 spec 引用同一份觀測量宣告；讀 F1/F2 的 summary | C2 |
| 任務 A | `core/stats/batch_means.py`、`decisions.py` 的 `equivalence`；兩階段事件數（A1.9） | F1/F2 的估計；確認 run 的事件數；F0 與確認的比較 | C2 |
| 任務 A | evidence 角色、S 的唯一性（A1.4） | C2 附加 search 角色、confirmation 與 seed_group | C2 |
| 任務 A | 不含名稱的 `tree-v1`；effective config 依內容雜湊存放（A2.4） | 設計快取；數百個 run 不重複儲存設定 | C2 |
| 任務 A | schema 關鍵字（A2.7） | detector-design 的 schema；A2 合併前，C1 的 schema 不使用 `maxItems`、`maximum`、`exclusiveMaximum`，這些上限在 Python 中檢查（C1.1） | C1（若 A2 已合併）、C2 |
| 任務 B | `element_sim.spec/1` 與 `geant4_run.py check-spec`（B1.1、B1.6） | 實現結果的驗證（子行程） | C1（B1 合併後加入測試）、C2 |
| 任務 B | 量能器母體與 `leak_*_MeV`（B1.3） | 量能器元件的目標 | C2 |
| 任務 B | `simreco`、`geant4_run.py reco`（B2.1、B2.2） | F1/F2 的重建 | C2 |
| 任務 B | surrogate 類別、判定引擎 `change`（B2.4） | F0、F1 在架構上屬 surrogate；C2 依同一介面附加判定 | C2 |
| 任務 B | J15 的設計與結果（B3） | J16 的比較對象 | C3 |
| 既有工具 | `tracker_resolution.py`、`multiple_scattering.py` | F0 的徑跡解析度：C1 把 `curvature_sigma` 與散射式移到 `core/physics/tracking.py`，腳本與 F0 共用同一份實作（每個設計以子行程呼叫的成本太高） | C1 |

**提供給其他任務的介面：** C2.1 加入 `core/` 的判定、配對比較、`values` 與角色，任何研究都可使用（例如收斂閘門可以宣告配對模式）。

---

## §C.3 硬性限制

§A.3 與 §B.3 的限制都適用。另外：

1. **搜尋器核心只用標準函式庫。** Sobol 序列、NSGA-II、（選用）CMA-ES 以標準函式庫實作。貝氏最佳化（Ax/BoTorch）只作為選用後端（C3），在 `adapter.json` 記錄測試過的版本；沒有安裝時搜尋仍可執行。MOBO 後端以延遲 import（在函式內 import，失敗時退回 NSGA-II）載入，是「只用標準函式庫」規定的唯一例外。
2. **adapter 之間不 import。** detector-design 以子行程呼叫 `geant4_run.py`（`check-spec`、`run`、`reco`），交換 JSON 檔案；共用的 Python 程式（包括 F0 的徑跡公式）只從 `core/` import。
3. **同一個量只有一份正式實作。** F0 的徑跡與多重散射公式由 C1 移到 `core/physics/tracking.py`，hep-detector 的腳本改為呼叫它；材料常數來自隨附的材料表（C1.4），不另寫一份。
4. **事先宣告。** 需求、目錄版本、文法、搜尋預算、最佳化器設定與種子在第一次評估前寫入搜尋 spec 並取雜湊。之後的任何變更產生新的搜尋版本；舊版本與其結果保留在紀錄中。
5. **搜尋數值不回報。** 搜尋階段的目標值只用於排序；任何對外的性能數字必須引用確認 run。
6. **LLM 提案沒有特權。** Claude 提出的設計以 `proposer: llm` 標記，經相同的有效性檢查與評估；Claude 不得修改評估輸出，不得在看到結果後改需求而不開新版本。
7. **成本與質量模型是宣告的輸入。** plugin 只附占位模型，標記 `assumed`；真實的單價與質量模型由使用者提供並附來源。沒有模型時，成本與質量不作為目標或約束。
8. **實驗名稱** 只出現在 `docs/` 與範例 README；元件目錄用通用名稱。reference `detector-design-search.md` 引用 §C.4.1 的研究時只用 citation key（例如 `Cisbani2020`），不寫 EIC、ePIC 等名稱（實驗名稱掃描會檢查）。
9. **不修改 `skills/hep-detector/SKILL.md`**，除非維護者核准一行指向 reference 的路由（§P.7 第 12 項）。
10. 契約規則以 `strict or _at_least(contract_version, CV3)` 閘控。

---

## §C.4 設計

### §C.4.1 實際做法的參考與教訓

| 研究 | 做法 | 本設計採用的教訓 |
|---|---|---|
| EIC dRICH（Cisbani 等，JINST 15 (2020) P05009） | 8 個參數；目標為 π/K 分離（兩個動量的調和平均）；Geant4 帶 2.5 % 雜訊；高斯過程貝氏最佳化，每次 20 個設計並行，約 55 次呼叫收斂；優於原設計（3.23 對 2.9）；以後驗推得容差區間（數字待依原文核對） | 雜訊要明確建模；平行批次；以後驗做容差與參數相關性分析；結果「只基於模擬」，需原型驗證 |
| AID(2)E（ePIC，arXiv:2405.16279） | 多目標貝氏最佳化（qNEHVI，Ax/BoTorch）與 NSGA-II；dRICH 7 個參數、200 次評估、150 次收斂；以已知 Pareto 前緣的 DTLZ2 做封閉測試；PanDA 分散執行 | 多目標與 Pareto；目標數 ≤ 4 時用 MOBO，更多或不連續時用遺傳演算法；先做封閉測試；幾何約束（重疊、包絡）在模擬前檢查 |
| MODE（arXiv:2203.13818、2310.05673） | 端到端可微分最佳化；以可微分代理模型取代不可微的模擬；效用函數包含物理目標與成本 | 以單一效用或 Pareto 對齊實驗目標，而非各子系統各自最佳化；代理模型可能把設計導向偏差，必須以完整模擬確認 |
| AIDO 擴散模型量能器（arXiv:2502.02152） | 6 層取樣量能器、12 個參數（厚度與材料；數字待依原文核對）；材料以 softmax 的類別變數處理；成本與長度上限；結果重現已知的量能器原則 | 類別選擇（材料）與成本約束可以進入搜尋；「重現已知原則」是合理的第一個驗收 |
| ECAL 縱向結構（Borysov 等，EPJ Web Conf. 315, 03006） | 半解析模型（以 Geant4 核對）＋遺傳演算法與非支配排序 | 解析模型先篩選、Geant4 核對：即 F0 → F2 的多保真度 |
| SWGO 陣列佈局（arXiv:2310.01857） | 10³–10⁴ 量級個單元位置的可微分最佳化；效用 = 通量精度 + 能量解析 + 指向解析 + 面積成本 | 效用的權重是宣告的選擇；某些導數項會主導並把設計推向極端，需要檢查 |
| GRACE（arXiv:2602.15039） | LLM agent 從自然語言或論文建立模擬並探索設計變體；有物理檢查器與 provenance | 幾何常需多次重產才符合規格，應在模擬前驗證；agent 注意到異常卻未追查；忽略成本與工程約束 |
| VI-BRATO（arXiv:2604.21804） | LLM agent 指揮 DD4hep/Geant4 的幾何與數位化雙層掃描，46 次 run 達到 2255 點網格的最佳 | agent 擅長分解問題與調整掃描；但結論需獨立核對，且仍需專家把關可實現性 |

綜合：沒有一個實際案例讓 LLM 自己宣告「最佳」；成功的做法都是「明確的目標與約束＋可重現的評估＋有紀錄的最佳化器＋完整模擬確認」。LLM 的價值在於把需求轉成搜尋問題、提出有物理根據的起點、分解問題、追查異常。

### §C.4.2 三個角色

```
 使用者 ──需求──▶ Claude（設計者）──設計摘要、種子設計、搜尋範圍──▶ 搜尋器（有紀錄、可重現）
                      ▲                                                  │ 候選設計
                      │ Pareto 前緣、異常、取捨                          ▼
                      └──────────────── 評估管線 F0 → F1 → F2 → 確認 ◀──┘
```

| 角色 | 可以做 | 不可以做 |
|---|---|---|
| Claude（設計者） | 把需求轉成 `detector-requirements/1`（與使用者確認）；從目錄選擇候選結構種類；以物理推理寫出 2–6 個種子拓撲與理由；設定搜尋範圍（在目錄限制內）；分解問題（例如先決定磁場與臂長，再決定量能器）；決定何時升到更高保真度；追查異常；解讀 Pareto 前緣並向使用者說明取捨 | 發明目錄外的元件；跳過有效性檢查；修改評估輸出；回報搜尋階段的數值；在看到結果後悄悄改需求 |
| 搜尋器 | 在基因空間中產生候選；依預算、種子與設定執行；記錄每次評估 | 判定是否符合需求（那是評估與統計的工作） |
| 評估管線 | 實現設計、檢查有效性、在指定保真度計算目標與約束、附 SE | 依提案者改變行為 |

### §C.4.3 需求規格 `detector-requirements/1`

示意（`//` 為說明，不是 JSON 的一部分）：

```
{ "requirements_version": 1,
  "particles": [{"species": "proton", "rigidity_GV": [0.6, 1000]}, {"species": "electron", "energy_GeV": [1, 100]}],
  "objectives": [  // 最小化或最大化；最多 4 個參與 Pareto，其餘以約束表達
    {"name": "rigidity_resolution", "at": {"species": "proton", "rigidity_GV": 100}, "sense": "min"},
    {"name": "mass_kg", "sense": "min"} ],
  "constraints": [  // 硬性需求：每項有門檻與方向
    {"name": "mdr_GV", "op": ">=", "value": 1000},
    {"name": "beta_resolution", "at": {"beta": 1}, "op": "<=", "value": 0.03},
    {"name": "acceptance_threshold_GV", "op": "<=", "value": 0.8},
    {"name": "calorimeter_depth_X0", "op": ">=", "value": 16},
    {"name": "upstream_material_X0", "op": "<=", "value": 0.15} ],
  "envelope": {"length_mm": 2000, "transverse_mm": [600, 600]},
  "environment": {"world_material": "G4_Galactic"},
  "cost_model": null, "mass_model": "catalogue-default",
  "tolerance": {"relative": 0.01},
  "provenance": {"elicited_by": "claude", "confirmed_by_user": true} }
```

- **目標目錄**（每個目標宣告它在各保真度的評估方式）：剛度解析度（指定剛度）、MDR、β 解析度、接受度門檻剛度、幾何因子（面積 × 立體角）、量能器深度（X₀、λ_I）、上游物質（X₀）、能量解析度（F1/F2）、e/p 拒斥（F2）、總質量、總長、通道數、成本（有模型時）。
- 目標與約束的名稱必須在目錄中；新增需要目錄變更與測試。
- 需求由 Claude 從使用者的描述整理，但必須經使用者確認（`confirmed_by_user`）後才能開始搜尋。

### §C.4.4 設計文法 `detector-design/1` 與元件目錄

**元件目錄第一版**（全部可實現為 `element_sim` 的盒狀元件，最多一層巢狀）：

| 元件種類 | 參數（型別） | 實現 | F0 的評估模型 |
|---|---|---|---|
| `magnet-region` | B（連續，T）、長度、孔徑（連續，mm） | 場區母體（`field`），可容納徑跡與 TOF 子體 | 偏轉；MDR；質量模型（宣告） |
| `tracker-plane` | 材料（類別）、厚度、位置解析度（偏轉／非偏轉）、尺寸 | `tracker-plane` 元件；解析度寫入 reco spec | `tracker_resolution.py`（量測項）、`multiple_scattering.py`（散射項） |
| `tof-layer` | 材料、厚度、σ_t、尺寸 | `tof-layer` 元件 | σβ/β = σ_t c / D（多層平均；§B.4.2） |
| `calorimeter-sampling` | 吸收層材料與厚度、主動層材料與厚度、層數（整數）、橫向尺寸 | `calorimeter` 母體 + 重複的取樣層 | X₀、λ_I、有效 Molière 半徑；能量解析度的參數化只作 F0 排序，參數化的來源經 hep-citations 記錄 |
| `calorimeter-homogeneous` | 材料、長度、橫向尺寸 | `calorimeter` 母體 + 單一主動體 | X₀、λ_I |
| `passive` | 材料、厚度、尺寸 | `passive` 元件 | 物質預算、多重散射 |

**組合規則（有效性，模擬前檢查）：**
- 元件沿 x 軸排成序列；序列長度與各種類的數量有上限（宣告於搜尋 spec）。
- 不重疊；全部在包絡內；平面之間的最小間距（宣告）。
- 子體只能放在 `magnet-region` 或 `calorimeter` 母體中，且只有一層巢狀（`element_sim` 的限制）。
- 參數在目錄範圍內；材料在目錄的材料清單中。
- 結構上「不合理」的組合（例如沒有磁場卻要求剛度解析度）**不**由規則禁止，而由目標與約束自然淘汰；規則只處理物理上或程式上不可能的情形。這保留了「自由組合」。

**基因編碼：** 固定數量的槽位（slot），每個槽位有「啟用」位元、元件種類（類別）、`parent_slot`（整數；−1 為頂層，否則指向一個啟用的 `magnet-region` 或 `calorimeter-*` 槽位，表示子體）與該種類的參數；停用的槽位不實現。順序由槽位的 x 位置決定。這讓遺傳演算法可以增刪元件與更換種類。

**修復與違反量：** 交配或突變之後依序修復：連續與整數參數截到目錄範圍；`parent_slot` 指向停用或不能當母體的槽位時改為 −1；子體超出母體時把子體的位置截到母體內。修復後仍無效的設計不再修復，以違反量 v = Σ（各規則的正規化違反：重疊長度／包絡長度、超出包絡的長度／包絡長度、間距不足／宣告的最小間距、巢狀超過一層的子體數）進入 constrained-domination（v 小者優先；v = 0 才比較目標）。

**實現：** `realize(design) → (element_sim.spec/1, reco spec)` 是確定性函式；設計雜湊 = 正規化設計 JSON 的 sha256；實現的 spec 以 `geant4_run.py check-spec`（B1.6）驗證；執行後以 `tree-v1`（A2.4）核對幾何。相同設計雜湊的評估可以重用（快取），快取鍵包含設計雜湊、保真度、目錄版本、程式雜湊，以及 S、N、K、B（同一設計在不同 seed_group 中是不同的評估）。同一搜尋中重複的設計（相同設計雜湊、相同保真度與 S）只評估一次，搜尋規模以不重複的設計計。

### §C.4.5 多保真度評估

| 保真度 | 方法 | 每個設計的成本 | 輸出 | 用途 |
|---|---|---|---|---|
| F0 | 解析式與既有工具（徑跡量測項與散射項、物質預算、接受度的螺旋幾何、TOF 公式、X₀ 與 λ_I） | 微秒到毫秒 | 目標值（無統計誤差，但有模型誤差） | 結構搜尋；篩選 10⁴–10⁶ 個設計 |
| F1 | `element_sim` + `simreco`，每個設計約 10³ 事件，K = 16 | 分鐘 | 目標值 ± SE（區塊 batch means） | 細化數百個設計的連續參數；校正 F0 |
| F2 | 同 F1，事件數依 A1.9 的兩階段設計；收斂閘門（A1.8）與 variation（B3.4 的規則） | 小時 | 目標值 ± SE，判定 | 決選者 |
| 確認 | 同 F2，role `confirmation`，種子獨立 | 小時 | 回報的性能與需求判定 | 唯一可回報的數字 |

- **F0 與 F2 的差異** 在每個決選者上記錄（`fidelity_gap`）。若差異超過宣告的門檻，該目標在決選時只依 F2 排序，並在報告中說明 F0 的模型限制。
- F0、F1 在架構上屬於 surrogate 類別（B2.4）：它們從不改變 label。

### §C.4.6 搜尋策略

| 步驟 | 內容 | 預設方法 | 預算（預設，可宣告） |
|---|---|---|---|
| S0 設計摘要 | Claude 讀需求，寫出候選結構種類、2–6 個種子拓撲與物理理由、問題的分解 | Claude | — |
| S1 結構搜尋 | 在 F0 上搜尋完整基因（結構＋參數）；初始族群 = 種子拓撲 + Sobol 隨機設計 | NSGA-II（標準函式庫） | 族群 200 × 100 代 = 2×10⁴ 次 F0 |
| S2 參數細化 | 取前 K 個**拓撲不同**的設計（以拓撲雜湊去重），在 F1 上細化連續參數；同一代的設計（包括存活的親代，在該代重新評估）共用 seed_group（配對比較，閘門 G-C2a） | NSGA-II 或 CMA-ES；C3 起可選 MOBO（qNEHVI），限目標 ≤ 4、參數 ≤ 20 | K = 5，每個約 100 次 F1 |
| S3 決選 | 每個拓撲的最佳設計進入 F2；收斂閘門、variation | — | ≤ 5 個設計 |
| S4 確認 | 決選者的確認 run；需求判定；穩健性 | — | ≤ 5 個設計 |

- 停止規則：預算用完，或超體積（hypervolume）在連續 G 代內改善小於宣告值。超體積在正規化的目標空間中以 WFG 演算法精確計算（目標 ≤ 4）；參考點在搜尋 spec 中宣告，預設為每個目標的宣告門檻往較差方向 × 1.1（最小化目標乘 1.1，最大化目標除以 1.1），沒有門檻的目標必須宣告參考點。不依結果加預算；加預算是新的搜尋版本。
- Claude 在 S0 之後可以加入新的種子拓撲（例如追查一個異常），但這些提案同樣標記為 `proposer: llm`、計入搜尋規模。

### §C.4.7 統計完整性

| 風險 | 處理 |
|---|---|
| 贏家詛咒 | 搜尋數值只作排序；回報只來自確認 run（role `confirmation`，S 不曾出現在搜尋中）；推薦設計在確認之前依 F2 固定，確認只回報它的性能，不在看到確認結果後於決選者之間重新挑選（否則必須回報全部決選者的確認結果並說明選擇偏差）；報告每個決選者的「搜尋估計 − 確認估計」作為診斷 |
| 帶雜訊的約束 | 需求判定由判定引擎的 `threshold`（C2.1）執行，為單邊：「≤ 門檻」的需求，符合 = 估計 + t₀.₉₅·SE ≤ 門檻；不符合 = 估計 − t_{1−α/m}·SE > 門檻；其他為 unresolved（m = 決選者數 × 需求數）。計數很少時用精確區間 |
| 在雜訊中宣稱支配 | 決選者之間的優劣由 `order`（C2.1）判定，只在差值的雙邊 t_{1−α/(2m)} 界限不含 0 時宣稱（m = 決選者配對數 × 目標數）；報告「統計上非支配的集合」 |
| 排序的雜訊 | S2 中同一代的設計共用一個 seed_group（配對比較），差值的變異較小；確認 run 不共用，維持獨立 |
| 搜尋規模 | 紀錄寫入各保真度評估的設計數、拓撲數、最佳化器設定與種子 |
| 利用模擬缺陷 | 決選者必須通過相關參數（production cut、最大步長、場精度）的收斂閘門；物理模型 variation（B3.4 的規則）；設計落在任何 reference benchmark 範圍外的材料或能量區時在報告中標記（label 本來就是 `unvalidated`，這是給讀者的資訊） |
| 穩健性 | 依需求的 `tolerance` 與目錄的製造容差擾動連續參數，以 F0 全因子或 F1 抽樣探索性能分布並找出容差內的最差點；「穩健符合」的判定只用確認保真度的 run（最差點以 role `confirmation`、F2 的事件數重跑），結果分為「穩健符合」與「名義符合」 |
| 改需求 | 需求或預算的任何改變是新的搜尋版本；報告列出所有版本 |

### §C.4.8 紀錄與契約（CV3）

搜尋紀錄是帶 `extension.design_search` 的 computational-run：

```
{ "requirements_sha256": "...", "catalogue_version": "1", "catalogue_sha256": "...",
  "search_spec_sha256": "...", "search_version": 1, "previous_versions": [],
  "optimizer": {"name": "nsga2", "implementation": "detector-design 0.2.0", "backend": null, "seed": 12345, "config": {...}},
  "budgets": {"F0": 20000, "F1": 500, "F2": 5, "confirmation": 5},
  "evaluated": {"F0": 20000, "F1": 487, "F2": 5, "topologies": 143},
  "evaluations_ref": {"path": "...", "sha256": "..."},
  "proposals": [{"design_sha256": "...", "proposer": "llm", "rationale": "..."}],
  "pareto_set": ["<design_sha256>", ...],
  "finalists": [{"design_sha256": "...", "spec_sha256": "...", "confirmation_runs": ["..."],
                 "requirements": [{"name": "mdr_GV", "verdict": "met|not-met|unresolved", "robust": true}],
                 "fidelity_gap": {...}, "search_minus_confirmation": {...}}],
  "label": "unvalidated" }
```

規則見 C2.6。C1 的紀錄只有 F0 的欄位，標記 `fidelity: F0-only`。C1 在 CV3 之前就寫出 `extension.design_search`：信封 schema 的 `extension` 只要求是 object（`contracts/schemas/envelope.json`），不限制其中的鍵，所以 C1 的紀錄在 CV3 之前可被接受；CV3 之後由 C2.6 的規則檢查。

---

## §C.5 階段 C1：需求、文法與快速搜尋（detector-design 0.1.0）

### C1.1 schema

`detector-requirements/1`、`detector-design/1`、`catalogue/1`、`design-search-spec/1`（需求雜湊、目錄版本、槽位數與上限、預算、最佳化器設定、種子、停止規則），放在 `adapters/detector-design/assets/schemas/`，只用 `contracts/schema.py` 支援的關鍵字；跨欄位規則在 Python 中檢查。A2（A2.7）合併前，schema 不使用 `maxItems`、`maximum`、`exclusiveMaximum`，序列長度、數量上限與參數上界在 Python 中檢查；A2 合併後可改由 schema 表達，Python 檢查保留為測試。

### C1.2 元件目錄第一版

§C.4.4 的六種元件；每種附參數範圍、材料清單（NIST 名稱）、製造容差、質量模型（密度 × 體積；磁鐵質量為宣告的占位模型，標記 `assumed`）、F0 模型、實現規則。目錄的每個條目有單元測試（實現後的幾何、物質預算）。

### C1.3 實現與有效性

`design_search.py realize`：設計 → `element_sim.spec/1` 與 reco spec；不需 Geant4。無效設計回傳原因（重疊、超出包絡、巢狀、範圍），exit 2。

- C1 以 detector-design 自己的有效性規則與 `element_sim.spec/1` 的草案（B1.1 的表）為準；C1 可能在 B1 之前合併。
- C2（B1 必定已合併）：加入一個測試，以子行程呼叫 `geant4_run.py check-spec` 驗證目錄中每種元件的實現結果（C2.9）。

### C1.4 F0 評估

`design_search.py evaluate --fidelity F0`，在同一行程中計算：
- **徑跡：** `core/physics/tracking.py` 的 `curvature_sigma`（量測項）與散射項。C1 把它們從 `tracker_resolution.py` 移到 `core/`（指定 steward），`tracker_resolution.py` 與 `multiple_scattering.py` 改為呼叫 `core/`，既有測試確認輸出不變。散射常數沿用 `tracker_resolution.py` 的慣例：曲率擬合的散射項用 PDG 的 0.016 GeV/c（`PDG_MS`，無對數修正），同時輸出 Highland（13.6 MeV，`HIGHLAND`）版本；所用的常數寫入 `model`。量測項的公式假設所有平面在均勻場中；有平面在 `magnet-region` 之外的設計，曲率只用場內的平面計算，並標記 `model: planes-outside-field`，該設計的 `fidelity_gap` 在報告中特別列出。
- **材料：** 物質預算與 X₀、λ_I 取自隨附的材料表 `catalogue/materials.json`（每種目錄材料的密度、X₀、λ_I；由 Geant4 NIST 材料的 dump 產生，檔頭記錄 Geant4 版本與產生指令；或取自 PDG 並經 hep-citations 記錄）。F0 不在執行時呼叫 Geant4；測試以同一 dump 核對此表（`geant4_verify.py` 行 132 用的是 dump 的 `radiation_length_cm`）。
- **接受度門檻剛度：** 在均勻場中從宣告的入射方向（預設正向入射）出發、仍穿過所有必要平面的最低剛度（螺旋與盒狀邊界；和 §B 附錄 A 同一公式）。
- **幾何因子：** 第一與最後一個必要平面（預設為最外側的兩個徑跡平面）構成的兩平行矩形平面望遠鏡的解析式（Sullivan 1971，經 hep-citations 記錄），不考慮磁場偏轉；這個近似寫入 `model`。
- **TOF：** 依 §B.4.2 的公式。

每個目標附 `model` 欄位說明近似。

### C1.5 搜尋器

`design_search.py search`：Sobol 初始化（Joe–Kuo 方向數，隨附所需維度的表）、NSGA-II（模擬二元交配 η_c = 15、多項式突變 η_m = 20，處理連續與整數基因，整數在突變後四捨五入；類別基因與 `parent_slot` 以均勻交配與隨機重設；槽位啟用位元以位元翻轉）；之後依 §C.4.4 修復，約束以違反量的 constrained-domination 處理。分布指數與突變機率寫入搜尋 spec。標準函式庫實作；同一種子結果逐位元相同。

### C1.6 搜尋紀錄與報告

`design_search.py report`：Pareto 前緣、每個拓撲的最佳設計、搜尋規模、F0 模型限制；輸出紀錄（§C.4.8，`fidelity: F0-only`）與一份給使用者的 Markdown 摘要。C1 的結果明確標示「只基於解析模型」。

### C1.7 agent 協定與文件

- `skills/hep-detector/references/detector-design-search.md`：§C.4.2 的角色與限制、需求確認流程、設計摘要的格式、何時升保真度、如何回報（必須說明搜尋規模、確認狀態與穩健性）。
- reference 引用研究時只用 citation key（§C.3 第 8 條）。
- adapter 文件；`docs/capability-matrix.md` 加入 detector-design 列。
- 路由：依 §P.7 第 12 項的決定，在 `SKILL.md` 加一行指向 reference，或只靠路由案例與 reference。

### C1.8 封閉測試

| 測試 | 已知答案 | 通過條件 |
|---|---|---|
| DTLZ2（3 目標，已知 Pareto 前緣） | 解析的前緣 | 2×10⁴ 次評估內超體積達到真值的 95 % 以上（AID(2)E 的封閉測試做法） |
| 平面配置（N = 6、臂長 L 固定、只有量測項、宣告最小間距 L/32） | 最佳 A = 47.66：1/32 格點上窮舉，不受格點限制的局部搜尋得到同一值（等距為 66.96；§C 附錄 A） | 搜尋器在最小間距 L/32 下找到 A ≤ 47.66 × 1.01 的配置 |
| 結構選擇（需求 MDR ≥ 1 TV，給定包絡與質量上限） | 必須選出含 `magnet-region` 與 ≥ 3 片 `tracker-plane` 的拓撲；無磁場的拓撲都不可行 | 所有可行的 Pareto 設計都含磁場區與徑跡平面；B·L² 與解析式一致 |
| 量能器深度（需求 ≥ 16 X₀、長度上限） | 在吸收層材料清單中，高 Z 吸收層使長度最短 | 選出的吸收層與解析排序一致 |
| 可重現 | — | 同一搜尋 spec 與種子，兩次執行的紀錄逐位元相同（時間戳除外） |

### C1.9 C1 驗收

- [ ] 四個 schema 與跨欄位規則的測試；無效設計的每種原因都有測試。
- [ ] 目錄六種元件的實現測試；A2 合併前 schema 不用 `maxItems`、`maximum`、`exclusiveMaximum`，對應上限的 Python 檢查有測試。
- [ ] F0 的每個目標和既有工具或附錄的解析值一致。
- [ ] C1.8 的封閉測試全部通過（閘門 G-C1；不通過不合併）。
- [ ] `core/physics/tracking.py` 的單元測試；`tracker_resolution.py`、`multiple_scattering.py` 的既有測試不變地通過；`materials.json` 與 Geant4 dump 一致。
- [ ] 一個獨立 agent 依 agent 協定，從一段自然語言需求完成：需求確認（由測試扮演使用者）、設計摘要、F0 搜尋、報告；報告標示「只基於解析模型」並列出搜尋規模。
- [ ] `check_layering.py`（detector-design 只 import `core` 與 `contracts`）與 `check_packaging.py` 通過。
- [ ] VALIDATION DESIGN-SEARCH-F0；CHANGELOG；release manifest。

---

## §C.6 階段 C2：模擬評估與確認（detector-design 0.2.0、geant4 adapter 0.5.0、contracts CV3）

### C2.1 `core/` 與契約的附加

依 §P.2 的 R1 與 R2（只附加、不改既有行為）：

| 附加 | 位置 | 內容 |
|---|---|---|
| `threshold(est, se, ν, op, value, m)` | `core/stats/decisions.py` | met／not-met／unresolved；符合 = 單邊 95 % 界限滿足門檻；不符合 = 單邊 1 − α/m 界限違反門檻；精確區間分支 |
| `order(diff, se, ν, m)` | 同上 | better／worse／indistinct；只有差值的雙邊 t_{1−α/(2m)}(ν) 界限不含 0 時才宣稱優劣；m = 決選者配對數 × 目標數 |
| 配對模式 | 同上（`equivalence`、`change`、`order` 都接受 `pairing: paired`） | 兩點屬於同一 seed_group，K、B 相同；`absolute`：逐區塊差值 d_b = θ_a,b − θ_b,b，diff = d̄，se_diff = sd(d_b)/√K。`relative`：對要檢查的每個界限 r（TOST 的 ±tol、`change` 的 tol、`order` 的 0）構成 z_b = (θ_a,b − (1+r)θ_b,b)/b̄（b̄ 為 b 點的區塊平均），以 z̄ 與 sd(z_b)/√K 對 0 做單邊檢定（Fieller 型，b̄ 的不確定度不需忽略）。ν = K − 1；se 目標為 r = 0 時的 se ≤ tol/4。預設仍為 `independent` |
| `values` 累加器 | `core/simulation/summary.py` 與 schema（`summary_version` 的 minor 增加）；`core/stats/batch_means.py` | 每個區塊通過選擇的原始值（依事件編號排序）；`values_max`（觀測量宣告，預設 10⁴）是每個區塊的上限，區塊的 `n` ≤ `values_max` 時寫出該區塊的值，任一區塊超過時該觀測量不使用經驗分位數並記錄；`merge` 規則 `concat`；有 `values` 時以經驗分位數（Hyndman–Fan 第 7 型，寫入 `quantile_method`）估計。理由：不同設計的解析度差很多，固定分格無法同時適合所有設計 |
| `values` 的 C++ 實作 | `g4sim/SimSummary.hh`；`element_sim` 與 `simreco` 寫出 | 和 Python 產生器一致（A2.9 的方法） |
| 角色 | `contracts/`、study spec 與搜尋 spec 的 schema | 加入 `confirmation`（evidence 角色）與 `search-F1`、`search-F2`（search 角色）；search 角色的 run 不能作為任何升級或回報的證據 |
| seed_group | `core/simulation/seeds.py`；`contracts/` | F1：同一 seed_group 的 run 共用 S = H(search_id, role, seed_group)；F2 與確認不共用：S = H(search_id, role, design_sha256)。同一 seed_group 的 run K、B、`seeding` 相同，spec 雜湊互不相同；唯一性改為「(S, spec 雜湊) 不重複；S 只在宣告的 seed_group 內重複」；evidence 角色的 S 不得等於任何 search 角色的 S |

### C2.2 F1、F2 評估

`design_search.py evaluate --fidelity F1|F2`：實現 → `geant4_run.py run`（`element_sim`）→ `geant4_run.py reco`（`simreco`）→ summary；每個設計評估是一個邏輯 run，point_id = 設計雜湊，role 為 `search-F1` 或 `search-F2`。事件數：F1 固定（宣告），F2 依 A1.9。批次執行經既有的 partition 與 batch 機制（hep-computing），以 §C.4.4 的快取鍵快取。存活的親代在每一代的 seed_group 中重新評估，所以同一代內的比較全部配對；重新評估是新的評估（S 不同，不命中快取），計入 F1 預算。

### C2.3 搜尋中的配對比較

- S2 的每一代宣告一個 seed_group；同一代的設計共用 S，排序以 `order` 的配對模式進行。
- **閘門 G-C2a：** 在第一次搜尋的 trial 中，量測差值的變異比 Var(獨立) / Var(配對)；比小於宣告值（預設 2）時，S2 改用獨立比較並在紀錄中註明。配對的估計在任何相關程度下都有效，只是增益可能很小（Geant4 中不同設計很快消耗不同的亂數）。

### C2.4 確認與需求判定

`design_search.py confirm`：決選者的確認 run（role `confirmation`，S 不在任何搜尋評估中）；§C.4.7 的單邊需求判定（`threshold`）；決選者之間的優劣（`order`，獨立模式）；`search_minus_confirmation` 與 `fidelity_gap`。推薦設計在確認之前依 F2 固定並寫入紀錄（§C.4.7）。

### C2.5 防護與穩健性

決選者的收斂閘門（production cut、最大步長、場精度；A1.8）；variation（B3.4 的規則）；容差擾動；benchmark 範圍外的標記（以 `contracts/validate.py` 匯出的範圍比對判斷）。

### C2.6 契約 CV3

- 搜尋紀錄的 label 必須是 `unvalidated`。
- 每個決選者的 `confirmation_runs` 必須存在，role 為 `confirmation`，其 spec 雜湊等於該設計的實現，其種子 S 不在 `evaluations_ref` 所列的任何搜尋評估中（`dependencies.py` 重新推導）。
- 由搜尋紀錄衍生的表格或 communication，其數值必須來自確認 run；引用搜尋階段數值時被拒。
- communication 使用搜尋結果時得到 `communication.simulation_optimized_design` 警告。
- C2.1 的角色與 seed_group 規則。
- 閘控 `strict or _at_least(contract_version, CV3)`；需 hep-computing 同意 `extension.design_search`（§P.7 第 13 項）。

### C2.7 adapter 變更

| 項目 | 內容 |
|---|---|
| detector-design | 0.1.0 → 0.2.0：`evaluate --fidelity F1|F2`、`confirm`；搜尋 spec 引用 `simulation-observables/1`；`adapter.json` 與文件 |
| geant4 adapter | 0.4.0 → 0.5.0：`SimSummary.hh` 的 `values`；`element_sim` 與 `simreco` 依觀測量宣告寫出 `values`；`SIM_SOURCES` 不變結構 |
| G5 | 新的 C++ 變更依 Geant4 API 撰寫；審查者在 VALIDATION 條目中確認 |

### C2.8 計算預算

F0 2×10⁴ 個設計：分鐘級；F1 約 500 × 10³ 事件；F2 與確認各 ≤ 5 個設計，事件數依 A1.9；量能器簇射主導 CPU。實際預算在 trial 後寫入搜尋 spec。

### C2.9 C2 驗收

- [ ] `threshold` 的 toy：真實值等於門檻時判 met 的機率 ≤ 0.05 + 3σ_MC；`order` 的 toy：真實差值為 0 時宣稱優劣的機率 ≤ α/m + 3σ_MC。
- [ ] 配對模式的 toy：se_diff 名義 90 % 區間的覆蓋率 |覆蓋率 − 0.90| ≤ 0.02 + 3σ_MC；trial 中量測的變異比已記錄（閘門 G-C2a）。
- [ ] `values` 累加器：Python 與 `SimSummary.hh` 一致；超過 `values_max` 時省略並記錄；經驗分位數有單元測試；舊的 summary（沒有 `values`）仍可讀。
- [ ] 目錄每種元件的實現結果以子行程通過 `geant4_run.py check-spec`（C1.3）。
- [ ] `order` 用雙邊 t_{1−α/(2m)}；配對 `relative` 模式的 toy 在真實相對差等於 r 時拒絕的機率 ≤ 0.05 + 3σ_MC。
- [ ] 角色與 seed_group 的契約測試：search 角色列為證據時被拒；seed_group 外重複的 S、同一 seed_group 內相同的 spec 雜湊被拒；確認 run 的 S 等於某個搜尋 run 的 S 時被拒。
- [ ] F1、F2 的 summary 通過任務 A 的一致性測試；評估快取以設計雜湊、保真度、目錄版本、程式雜湊與 S、N、K、B 為鍵；重複的設計只評估一次；存活的親代在每一代重新評估。
- [ ] CV3 的契約測試：引用搜尋數值的表格被拒；搜尋紀錄的 label 不是 `unvalidated` 時被拒。
- [ ] 贏家詛咒的 toy：在純雜訊的設計集合上，搜尋估計顯著偏樂觀，確認估計無偏（閘門 G-C2b）。
- [ ] 一次完整的小型搜尋（例如 C1.8 的結構選擇問題，以 F1/F2 評估）完成 S0–S4，報告含搜尋規模、確認判定與穩健性。
- [ ] J14 在 `--strict` 下仍通過；B3 已合併時 J15 也是。
- [ ] VALIDATION DESIGN-SEARCH；CHANGELOG；release manifest；§A.8 的檢查。

---

## §C.7 階段 C3：範例（detector-design 0.3.0）

### C3.1 J16：自動設計範例

- 需求：由 J15 的設計目標整理（MDR ≥ 1 TV、σβ/β ≤ 3 %、接受度門檻 ≤ 0.8 GV、量能器 ≥ 16 X₀、上游物質 ≤ 15 % X₀、長度 ≤ 2 m、宣告的質量模型）；**不**提供 J15 的幾何。
- 執行 S0–S4；報告比較搜尋結果與 J15（B3 的結果）：是否找到 J15 型的拓撲、在哪些目標上更好或更差、原因（例如平面向兩端與中央聚集提高 MDR，但多重散射主導區的解析度變差；§C 附錄 A）。
- 和 J15 一樣是合成研究；README 說明它展示的是流程，不是新的探測器設計（AIDO 與 SWGO 研究的同樣定位）。

### C3.2 選用的 MOBO 後端

Ax/BoTorch（qNEHVI），只在 S2 使用，限目標 ≤ 4、連續參數 ≤ 20；版本記錄在紀錄與 `adapter.json`（是否列為測試過的工具見 §P.7 第 14 項）；沒有安裝時退回 NSGA-II，並在紀錄中註明。以 DTLZ2 封閉測試比較兩者。

### C3.3 註冊與文件

`docs/researcher-journeys.md`（J16）、路由案例（沿用 hep-detector description 中已有的「design principles and trade-offs」觸發詞；`check_routing_static.py` 要求列入表的 journey 都有路由案例）、`tests/examples/test_detector_design_j16.py`（重播並比對判定）、capability map、capability matrix、adapter 文件、protocol；本任務的 Markdown 以 `review.py` 審查（advisory）。

### C3.4 C3 驗收

- [ ] J16 完成；報告含搜尋規模、確認判定、穩健性與和 J15 的比較（閘門 G-C3）。
- [ ] J16 的離線重播（由已提交的紀錄與 summary）判定相同。
- [ ] MOBO 後端（若安裝）通過 DTLZ2 封閉測試；未安裝時退回並註明。
- [ ] 註冊與文件完成；路由案例通過。
- [ ] VALIDATION DESIGN-SEARCH-J16；CHANGELOG；release manifest；§A.8 的檢查。

---

## §C.8 契約與版本

| 物件 | 位置 | 版本 |
|---|---|---|
| `detector-requirements/1`、`detector-design/1`、`catalogue/1`、`design-search-spec/1`、F0、搜尋器 | `adapters/detector-design/` | detector-design 0.1.0（C1） |
| F1、F2、確認 | `adapters/detector-design/` | detector-design 0.2.0（C2） |
| `threshold`、`order`、配對模式、`values`、seed_group | `core/` | 隨 plugin 版本（C2）；summary schema 的 `summary_version` minor 增加 |
| `values` 的 C++ 實作 | geant4 adapter | 0.5.0（C2） |
| 角色、seed_group 規則、`extension.design_search` 與其規則 | `contracts/validate.py`、`contracts/dependencies.py` | CV3（minor、閘控；C2） |
| MOBO 後端、J16 | `adapters/detector-design/`、`examples/` | detector-design 0.3.0（C3） |
| agent 協定 | `skills/hep-detector/references/detector-design-search.md` | 隨 plugin 版本 |

---

## §C.9 不做與延後

| 項目 | 決定 | 理由 / 觸發條件 |
|---|---|---|
| 讓 LLM 單獨決定最佳設計 | 不做 | 沒有實際案例這樣做；判定必須可重現 |
| 搜尋中臨時發明元件種類 | 不做 | 新元件需要實現規則、F0 模型與測試；經目錄變更加入 |
| 可微分模擬與可微分代理模型（MODE 路線） | 延後 | Geant4 不可微；可微分代理模型對點雲尺度仍不成熟（arXiv:2310.05673）。觸發：一個連續參數 > 20 的問題，且 F1 預算不足 |
| 圓柱與非盒狀幾何、對撞機探測器 | 延後 | `element_sim` 只有盒狀元件。觸發：`element_sim` 加入圓柱元件（§B.9） |
| Cherenkov、RICH、TRD | 延後 | 需要光學物理與專用重建 |
| 強化學習、大型神經網路代理模型 | 延後 | 資料量與可解釋性；NSGA-II 與 MOBO 對 ≤ 數十個參數已足夠 |
| 真實成本資料庫 | 不附 | 由使用者提供並附來源 |

---

## §C.10 待決事項與殘餘風險

**待決事項**（編號見 §P.7）：第 11 項（detector-design 的維護歸屬）、第 12 項（`SKILL.md` 的路由行）、第 13 項（CV3 與 `extension.design_search`）、第 14 項（MOBO 後端）。

**殘餘風險：**
1. F0 模型的偏差可能讓結構搜尋錯過好的拓撲；以 S2 的拓撲多樣性與 `fidelity_gap` 緩解，但不能排除。
2. 模擬最佳化的設計可能利用 Geant4 在未驗證區的行為；收斂閘門與 variation 只能部分防護，label 維持 `unvalidated`。
3. 質量與成本的占位模型很粗；沒有使用者模型時不應把它們當目標。
4. 目標超過 4 個時，Pareto 前緣難以解讀；需求應把其餘目標寫成約束。
5. Claude 的設計摘要可能帶入「已知儀器」的偏見；以 Sobol 隨機設計與拓撲多樣性抵銷，並在報告中區分 LLM 與隨機提案的貢獻。
6. 配對比較在 Geant4 中的變異縮減可能很小（閘門 G-C2a）。
7. 計算量：量能器的 F1、F2 評估成本高；預算在 trial 後調整。
8. 本部的參考資料中，GRACE、VI-BRATO 是 2026 年的預印本，結論尚未經同儕審查。

---

## §C.11 建議的執行步驟

每個階段開始時依 §P.10.2 建立並確認該階段的 isolated worktree，所有步驟都在其中進行；合併後依 §P.10.5 移除。

**C1（A1 合併後；可與 A2、B 平行）**
1. 開始前檢查；schema（C1.1）與目錄（C1.2）。
2. 實現與有效性（C1.3）；F0（C1.4），以既有工具核對。
3. 搜尋器（C1.5）與 DTLZ2、平面配置的封閉測試。
4. 紀錄與報告（C1.6）；agent 協定與文件（C1.7）；其餘封閉測試與獨立 agent 驗收；C1.9。

**C2（B2 與 C1 合併後）**
1. `core/` 與契約的附加（C2.1）及其 toy 與契約測試。
2. F1、F2（C2.2）；配對比較的 trial（C2.3）；確認與需求判定（C2.4）。
3. 防護與穩健性（C2.5）；CV3（C2.6）；adapter 變更（C2.7）；C2.9。

**C3（B3 與 C2 合併後）**
1. J16（C3.1）；選用的 MOBO（C3.2）。
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

重合的聚集配置不受最小間距限制，所以不是封閉測試的答案，只用來說明趨勢。J15 的 MDR 1172 GV 在 1/32 格點的最佳配置下約為 1389 GV；但聚集的配置在多重散射主導區較差，這正是 J16 要讓搜尋器處理的取捨。

## §C 附錄 B：出處

- E. Cisbani et al., "AI-optimized detector design for the future Electron-Ion Collider: the dual-radiator RICH case", JINST 15 (2020) P05009, [arXiv:1911.05797](https://arxiv.org/abs/1911.05797)
- AID(2)E collaboration, "AI-Assisted Detector Design for the EIC (AID(2)E)", [arXiv:2405.16279](https://arxiv.org/abs/2405.16279)
- MODE collaboration, "Toward the end-to-end optimization of particle physics instruments with differentiable programming", [arXiv:2203.13818](https://arxiv.org/abs/2203.13818)；"Progress in end-to-end optimization of detectors for fundamental physics with differentiable programming", [arXiv:2310.05673](https://arxiv.org/abs/2310.05673)
- Schmidt et al.（MODE），"End-to-end detector optimization with diffusion models: a case study in sampling calorimeters", [arXiv:2502.02152](https://arxiv.org/abs/2502.02152)
- O. Borysov et al., "Longitudinal structure optimization for a high density electromagnetic calorimeter", [EPJ Web Conf. 315, 03006 (2024)](https://www.epj-conferences.org/10.1051/epjconf/202431503006)
- T. Dorigo et al., "Toward the end-to-end optimization of the SWGO array layout", [arXiv:2310.01857](https://arxiv.org/abs/2310.01857)
- J. Hill, H. J. Ryoo, "GRACE: an agentic AI for particle physics experiment design and simulation", [arXiv:2602.15039](https://arxiv.org/abs/2602.15039)（預印本）
- W. Chung et al., "Agentic-AI detector co-design and optimization in vertically-integrated differentiable full simulations", [arXiv:2604.21804](https://arxiv.org/abs/2604.21804)（預印本）
- 以上於 2026-10-23 取得；作者與期刊資訊在引用前需經 hep-citations 核對

## §C 附錄 C：版本歷程

| 版本 | 內容 |
|---|---|
| 2026-10-23 | 初版提案：三個角色、需求規格、元件目錄與設計文法、F0/F1/F2 多保真度、搜尋與確認分開、契約、C1/C2、J16；之後依任務 A 的重新審視引用 `core/` 的共用模組 |
| **2026-10-23（本版）** | **依計畫（第 1 部）重新整理：三個階段（C1 在 A1 後、C2 在 B2 與 C1 後、C3 在 B3 與 C2 後）；任務 C 需要的 `threshold`、`order`、配對比較、`values`、search 角色與 seed_group 由 C2.1 自己加入 `core/` 與契約；實現以 `geant4_run.py check-spec` 驗證；契約版本改記 CV3；J16 與 MOBO 移到 C3；節的編號與任務 A、B 一致** |
| 2026-10-23 | 加入 isolated worktree 的執行規定：檔頭、§C.0 的第一步、§C.11 的開頭（§P.10） |
| 2026-10-23 | 詳細檢查後的修正：A2 前的 schema 關鍵字限制；check-spec 測試移到 C2；`order` 的雙邊界限與 m；配對 `relative` 模式改用 z_b；快取鍵含 S、N、K、B；親代每代重新評估；F1 與 F2／確認的 S；設計去重；推薦設計依 F2 固定；隨附材料表；徑跡公式移到 `core/`，散射常數與場外平面；基因的 `parent_slot`、修復、違反量、SBX／PM 指數、Joe–Kuo、超體積；接受度與幾何因子；封閉測試的最小間距與新增配置；穩健性以確認保真度判定；citation key；MOBO 的延遲 import；`values_max` 每區塊；文獻數字待核對 |

---

# 第 5 部　設計理由（§R）

> 基準：hep-research `main` 的 `9f08796`（0.23.0 加未發布的變更），contracts 3.5.0，adapter geant4 0.1.0，Geant4 11.4.3
> 日期：2026-10-22（2026-10-23 依詳細檢查修正）
> 注意：本部寫於 2026-10-23 重新規劃（任務 C、八個階段、`core/` 模組）之前，只補了必要的指向。階段、版本、介面與驗收以第 1–4 部為準；兩者衝突時以第 1–4 部為準並回報。

---

## §R.0 摘要

**目的。** 讓 hep-research 裡的模擬研究（目前是 Geant4）做到三件事：結果不會被錯誤地標成 `validated-in-scope`；數值與判定可重現、可追溯；研究層不綁死在某一個模擬程式、某一種幾何或某一類研究上。

**設計的出發點。** 大型實驗已經解決過同樣的問題，只是規模大得多。本架構只取它們經過時間考驗、而且在 plugin 的限制下（Python 只用標準函式庫、以獨立執行檔交換 JSON/CSV、最小變動）做得到的做法：

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

- Python 只用標準函式庫。
- G5 授權邊界：Python 只和獨立執行檔交換 JSON 與 CSV；不複製 Geant4 範例程式碼。
- 分層：skill 腳本與 adapter 只 import `core`、`contracts`；兩者都要用的程式（統計、判定、種子雜湊、summary 讀取）因此放在 `core/stats/` 與 `core/simulation/`（§A.3 第 1 條、§A.4.5）；`skills/`、`contracts/` 不出現實驗名稱（實驗名稱可以出現在 `docs/` 與 `examples/`）。
- 狀態與退出碼（`core/status.py`）：0 ok、1 負向判定、2 `rejected`、3 `incomplete`。
- 檔案 ≤ 2 MiB；hep-detector quick load ≤ 25,600 bytes（目前 24,669）、description ≤ 1,024 字元（`measure_entrypoints.py` 回報 1,016）。`SKILL.md` 與 description 不改；唯一的例外是 §P.7 第 12 項待決的一行路由（C1）。
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
  hep-detector      規則、參考公式、推論（batch means、精確區間、MPV、IUT、negative control、分布比較）、判定、label
  adapters/geant4   spec 驗證、建置、執行、工作切分、紀錄（trace.provenance()）、simulated 表格；
                    A1 由逐事件 CSV 產生 run summary（A2 起只在測試中作為 oracle）
  adapters/detector-design  （任務 C）需求、元件目錄、實現、搜尋與確認
  core              trace、status；stats/（區塊估計量、精確區間、判定引擎、分布函式）；
                    simulation/（種子雜湊、summary 與觀測量的 schema 與讀取）
  contracts         驗證類別與等級表、範圍、configuration 與隔離（CV1）；新類別、遞移的處理鏈（CV2）；
                    extension.design_search（CV3）
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
| 契約 | Python | A1（CV1）、B2（CV2）、C2（CV3） | — |
| 推論與判定（`core/stats/`、`core/simulation/`） | Python | A1；B2、C2 附加 | — |
| `detector-design` adapter | Python | C1–C3 | `core`、`contracts`；呼叫 geant4 adapter |
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
| 模型對模型（surrogate） | 以 Geant4 等完整模擬為參考的快速模擬或 ML 代理模型 | 參數化量能器對 Geant4 | IUT 或 χ² | 不能升級物理 label；代理模型自己可得到「在範圍內與參考模擬一致」的標記 |

另有 `sanity`（粗略的合理範圍檢查）與 `interface`（介面檢查），兩者都不能升級。

### §R.6.2 benchmark 表（CV1，CV2 擴充）

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
| CV2 加入：J15 的檢查（`field-propagation` 等） | verification 或 sanity | — | — |
| CV2 加入：`regression-comparison` | regression | — | — |
| CV2 加入：`surrogate-comparison` | surrogate | — | — |

`regression-comparison` 與 `surrogate-comparison` 的範圍取被比較的兩個研究範圍的交集，由 `dependencies.py` 重新推導（§B 的 CV2 表為準）。

紀錄中的類別或等級和表不一致、或名稱不在表中，判為 error。`geant4_benchmarks.py` 的 `GRADES` 保留給工具，以測試確保一致。

### §R.6.3 範圍（CV1）

- 比對受控的 `observable.kind`；`label` 把它寫入 `declared_scope.observable_kind`。
- 維度清單依 benchmark 宣告（6.2 的第四欄），每個維度有型別：類別或數值區間；純量視為 [v, v]。新用例加維度只改表格。
- 宣告範圍缺少 benchmark 有的維度，視為超出範圍。
- 以目標雜湊為維度時，宣告範圍必須帶相同的 `target_geometry_sha256` 與 `hash_scheme`。
- 閘控：`strict or _at_least(contract_version, CV1)`，無 warning 分支。

### §R.6.4 configuration 與隔離（CV1）

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

### §R.6.5 回歸與模型對模型（CV2）

- **回歸：** 對同一研究、同一設定，在新舊兩個版本（plugin、後端或 Geant4）上各執行一次（point_id 為版本標籤，樣本獨立），比較每個純量觀測量。三種判定：`changed`（|diff| − t_{1−α/m}·se_diff > tol）、`unchanged`（§R.6.6 的通過規則）、`unresolved`；「不顯著」不等於「沒有改變」。直方圖的比較延後到分布層級的 benchmark。不影響 label；reference 觀測量 `changed` 時可觸發 sci-fix 的檢查。
- **模型對模型：** 代理模型永遠不改變物理 label。代理模型的研究宣告它的參考研究（study record）與範圍；以 IUT 判定（χ² 只作診斷）。通過時記錄 `extension.study.surrogate`（參考研究的引用與雜湊、範圍取兩者的交集）。

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

### §R.7.1 CV1（A1）

§R.6.2–6.4 的表格、範圍與隔離規則；`dependencies.py` 的重新推導；`ext_computational_run.json` 加入選用的 `simulation` 屬性（需 hep-computing 同意）。

### §R.7.2 CV2（B2）

§R.6.2 的新條目（verification、`regression-comparison`、`surrogate-comparison`）；§R.6.5 的規則；§R.7.4 的遞移處理鏈。閘控方式同 CV1。CV3（C2）加入 `extension.design_search` 與確認 run 的規則，見 §C。

### §R.7.3 sci-fix 與 advisory（A1）

| 缺陷 | ledger 條目 | 等級 |
|---|---|---|
| D1（含依 benchmark 宣告的範圍維度） | scope-kind | S2 |
| D2 | grade-table | S2 |
| D3（含 t 分位數的偵測極限） | control-shift | S2 |
| D4（含差值與 se 的定義） | gate-IUT | S2 |
| D5（含區塊 batch means 取代 bootstrap、精確計數區間、MPV 內插） | variance-method | **S1** |
| 隔離定義（含場與真空） | isolation | S2 |
| D6 | stopping-rule | S3 |

S1 與 S2 各發一份 advisory（鍵 `artifact_types: [computational-run]`、`extension_keys: ["study", "evidence_records"]`；introduced 0.20.0）。simulated dataset-record 無法用鍵區分，remedy 要求持有者對每個 simulated 表格執行 `contracts/dependencies.py`。

### §R.7.4 處理鏈的追溯

- 每個處理步驟（模擬、縮減、數位化與重建、表格）寫一份 computational-run 紀錄，含 `**trace.provenance()`、設定雜湊、輸入紀錄與檔案的雜湊、程式雜湊。
- simulated 表格的輸入鏈可以任意深，只要每一層都是有紀錄的 computational-run，而且鏈的每個根都是模擬 run（CV2；以前只允許一層）。
- 呼叫 C++ 執行檔時，Python 記錄執行檔與原始碼的 sha256、版本與子命令，並以 `trace.tag()` 標記。

---

## §R.8 程式與 CI

| 位置 | 變更 |
|---|---|
| `contracts/validate.py`、`dependencies.py` | §R.6、§R.7 |
| `contracts/schema.py` | `maxItems`、`maximum`、`exclusiveMaximum`（A2.7 加入；`element_sim` 的 schema 需要；不升契約版本） |
| `core/stats/`、`core/simulation/` | 區塊估計量、判定引擎（A1 的 `equivalence`、`detection_limit`；B2 的 `change`；C2 的 `threshold`、`order` 與配對模式）、分布函式、種子雜湊、summary 的讀取與 schema。放在 `core/` 是因為 hep-detector 的腳本與 adapter（`geant4`、任務 C 的 `detector-design`）都要用，而分層規則只允許 adapter import `core` 與 `contracts`（§A.3 第 1 條、§A.4.5） |
| `skills/hep-detector/scripts/` | 推論與判定只讀邊界產物；幾何事實（最小厚度、configuration）從 effective config 讀取，A2 前的紀錄仍從 spec/1 讀取；不新增腳本；`SKILL.md` 與 description 不改，唯一例外是 §P.7 第 12 項待決的一行路由（C1） |
| `adapters/geant4/assets/` | `g4sim/`；`layered_sim/` 加入 `g4sim`；`geant4_run.py`（邏輯 run 與工作切分、A1 的 Python summary 產生器、B2 的 `reco` 與 `table`）；B1 `element_sim/` 與 `simroot`；B2 `simreco` |
| `adapters/detector-design/` | 任務 C（C1–C3） |
| `SIM_SOURCES` | 涵蓋 `g4sim` 與各程式的原始碼 |
| CI | 任務 A 不需要新的必要 CI 工作；`SimSummary.hh` 的 ctest 可作為選用工作。B2 的 `simreco` 的 C++17 CI 工作是否必要由維護者決定（§P.7 第 9 項，建議必要） |

---

## §R.9 通用性

### §R.9.1 涵蓋的用例

| 用例 | 由什麼支援 | 狀態 |
|---|---|---|
| 材料層級的參考（J14 類） | reference 類別、孤立平板 | A1 |
| 有場的磁譜儀（J15，對照 PAMELA、AMS-02） | `element_sim`、場計入目標、verification、重建鏈 | B1、B2、B3 |
| 自動化探測器設計（J16） | `detector-design` adapter、確認 run、需求判定 | C1–C3 |
| 試束或模組（和數據比較） | setup-matched 類別、幾何樹推導的目標雜湊、依 benchmark 宣告的範圍維度 | 契約在 A1、A2；幾何用使用者應用或 `element_sim` |
| 稀有事件 | 精確計數區間 | A1 |
| 軟體或 Geant4 改版 | regression 類別 | B2 |
| 快速模擬、ML 代理模型 | surrogate 類別、縮減工具 | B2（契約）；縮減工具在第一個需要時 |
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
| 離子源與 Birks（J17） | 宇宙線核素研究，且 PVT 的 Birks 常數有文獻紀錄 |
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

---

## §R.10 階段與驗收

本節在 2026-10-23 以前複製了各階段的內容與驗收，容易和任務規格不一致，因此改為指向。階段的順序、內容邊界、介面擁有權、閘門與待決事項以 第 1 部 為準；每個階段的工作項與驗收以任務規格為準。

| 階段 | 一句話 | 規格 |
|---|---|---|
| A1 | 修正錯誤發出 `validated-in-scope` 的缺陷；統計與 summary 的共用模組放進 `core/`（contracts CV1） | §A.5 |
| A2 | `g4sim`、`per-event` 種子、`layered_sim` 寫出三個邊界產物、研究層只讀邊界產物 | §A.6 |
| B1 | `element_sim`、場、平面穿越、量能器漏失、逐事件 ROOT 檔、`simroot`、`check-spec` | §B.5 |
| B2 | `simreco`、處理鏈、verification／regression／surrogate（contracts CV2） | §B.6 |
| B3 | J15 研究 | §B.7 |
| C1 | 需求、元件目錄、F0 搜尋、封閉測試 | §C.5 |
| C2 | F1/F2 評估、確認 run、需求判定、配對比較（contracts CV3） | §C.6 |
| C3 | J16 自動設計範例、選用的 MOBO | §C.7 |

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
10. quick load 只剩 931 bytes；本架構不改 `SKILL.md` 與 description，唯一例外是 §P.7 第 12 項待決的一行路由（約 120 bytes，C1）。
11. 工作量：原型估計 A1 的契約部分約 8–12 個工作天，另加 Geant4 執行時間；其餘未估計。

---

## §R.12 決策紀錄

### §R.12.1 使用者已決定

| 日期 | 決定 | 位置 |
|---|---|---|
| 2026-10-22 | 核心程式用 C++，Python 作為介面；計算核心用 C++、參考值留在 Python；以獨立執行檔交換 JSON/CSV，不用 Python 綁定 | 原則 2（依 12.2 第 1 項的詮釋） |
| 2026-10-22 | J15 的 TOF1、TOF2 各兩層，四層同材料 | §B |
| 2026-10-22 | 詳細的逐事件資訊存成 ROOT 檔 | §R.4.1 T1、B1 |
| 2026-10-22 | J15 與其他部分拆成兩個任務，J15 後做 | 任務 A（A1、A2）、任務 B（B1、B2、B3）；之後加入任務 C（§P.0） |

### §R.12.2 本部的提議（需要使用者確認）

1. **語言分工的詮釋：** 逐事件的計算（模擬、數位化、重建、累加）在 C++；合併後的推論在 Python。
2. **輸出層的後端介面**（三個邊界產物），不做引擎抽象層。
3. **事件決定性：** 新 spec 預設 `seeding: per-event`；工作切分與執行緒數不影響事件。
4. **重現的定義是「判定相同」**，數值以容差比較；不做整數量化與逐位元相同的統計量。
5. **區塊 batch means：** 一個 run 內依事件編號分 K ≥ 16 個區塊；J14 有逐事件資料的 run 離線重算，不重錄。
6. **新增 `element_sim`**，`layered_sim` 不改 spec 格式；兩者共用 `g4sim`。
7. **五種驗證類別**，其中 regression 與 surrogate 在 CV2（B2）加入。
8. **八個階段**（A1、A2、B1、B2、B3、C1、C2、C3；§P.0），ROOT 檔與 `simroot` 在 B1。
9. 兩階段係數用 F₀.₉₀ 或 F₀.₉₅；精確區間的切換門檻（任一區塊為 0 或總數 < 100）。

### §R.12.3 待維護者決定

合併後的清單與建議見 §P.7（共 14 項）；本部原有的七項都已併入該清單。

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
