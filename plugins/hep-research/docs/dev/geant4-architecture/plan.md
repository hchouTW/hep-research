# 計畫總覽：Geant4 模擬、J15 最小磁譜儀與自動化設計搜尋

> 文件類型：計畫（給執行的 agent、審查者與維護者）。狀態：待使用者與維護者核准
> 日期：2026-10-23
> 語言：繁體中文原文；英文版 [`plan.en.md`](plan.en.md) 內容相同。兩者不一致時以中文為準，並同時修正英文
> 權威範圍：**階段的順序、編號、版本代號、介面擁有權、閘門、待決事項與執行環境以本文件為準**；工作項的內容與驗收以各任務規格為準；[`architecture.md`](architecture.md) 只說明設計理由
> 執行環境：**每個階段都在自己的 isolated git worktree 中執行**，不在主要 checkout 中修改任何檔案（§10）

**給執行的 agent：** 依序讀 §0（階段一覽）、§10（在 isolated worktree 中執行）、§6（閘門）、§4（介面擁有權），再讀負責階段所屬任務規格的 §0 任務卡。開始寫任何程式之前，先依 §10.2 建立並確認 worktree。

---

## 0. 一頁摘要

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

## 1. 評估：先前規劃的問題與處理

| # | 問題 | 影響 | 處理 |
|---|---|---|---|
| P1 | **A1 的範圍膨脹。** 上一輪把只有任務 C 需要的功能（單邊門檻與優劣判定、配對比較、搜尋角色、`values` 累加器）放進 A1 | A1 是 sci-fix，要盡快修正已經會錯誤發出 `validated-in-scope` 的缺陷；多出的功能加重證據與審查負擔，延後修正 | 原則 R1（「由第一個使用者引入」）：A1 只含它自己用到的東西；判定引擎的 `change` 在 B2、`threshold`／`order`／配對比較在 C2 加入；位置（`core/`）一開始就定好 |
| P2 | **命名衝突。** 「C1、C2」同時指契約版本與任務 C 的階段 | agent 與審查者讀錯 | 契約版本改記為 **CV1、CV2、CV3**；任務 C 的階段為 C1–C3（§5） |
| P3 | **關鍵路徑過長。** 任務 C 等待整個 B2，而 B2 混合了基礎設施（`simreco`、契約）與 J15 的物理研究 | 自動化設計被 J15 的研究工作拖住 | B 拆成 B2（重建與契約）與 B3（J15 研究）；C2 只等 B2；C1 只等 A1 |
| P4 | **介面放錯層。** 統計與 summary 讀取原本在 hep-detector 的腳本，adapter 依分層規則不能 import | 任務 C 需要第二份實作 | 共用程式一律在 `core/`；本文件 §4 列出每個介面的位置、擁有者與使用者 |
| P5 | **文件重複而漂移。** `architecture.md` §10 複製了各階段內容與驗收，每次修改都要同步，已出現不一致 | 讀者不知道以哪份為準 | 權威分工（§9）；`architecture.md` §10 改為指向本文件 |
| P6 | **待決事項分散**在三份規格 | 維護者看不到全貌，也不知道哪個決定擋住哪個階段 | 合併為一張表，標示阻擋的階段（§7） |
| P7 | **沒有階段之間的閘門** | 例如 ROOT 讀取能力或場的確定性檢查失敗時，後續階段仍會照計畫進行 | 明確的閘門（§6） |
| P8 | **工作量只有零星估計** | 無法排程 | 相對規模（小／中／大）與已知的估計（A1 契約部分約 8–12 個工作天）；其餘在各階段開始時估計（§0、§8） |
| P9 | **跨 adapter 的依賴未定義。** 任務 C 要產生 `element_sim` 的 spec 並驗證，但 adapter 不能 import 另一個 adapter | C1 無法驗證實現結果 | `geant4_run.py` 提供 `check-spec` 子命令（B1），`detector-design` 以子行程呼叫；B1 之前 C1 以自己的有效性規則為準（§4） |

---

## 2. 規劃原則

| # | 原則 | 說明 |
|---|---|---|
| R1 | **由第一個使用者引入，但位置一開始就定好** | 每個介面在第一個需要它的階段加入；共用的介面從第一天起就放在所有使用者都能 import 的地方（`core/`、`contracts/`） |
| R2 | **schema 只做附加的演進** | 新欄位都是選用的；版本號（`summary_version` 等）的 minor 增加；舊紀錄永遠能讀、能重播 |
| R3 | **同一個量只有一份正式實作** | 另一種語言或另一個位置的實作只能在測試中作為 oracle |
| R4 | **sci-fix 保持最小** | A1 只含修正缺陷所需的變更與它們的直接基礎 |
| R5 | **每個階段可單獨合併** | 有自己的版本、VALIDATION 條目、CHANGELOG、驗收清單；合併後 plugin 是一致的 |
| R6 | **判定可重現，數字可追溯** | 重現的定義是判定與 label 相同（架構 §5.6）；結果附搜尋規模與證據相關性 |
| R7 | **AI 是設計者，不是裁判** | Claude 選結構、提出種子、解讀結果；「是否符合、哪個最好」只由有紀錄的評估與統計判定（任務 C） |

---

## 3. 階段的內容與驗收（摘要）

各階段的完整工作項與驗收在任務規格中；這裡只列範圍的邊界，避免重疊。

| 階段 | 包含 | 明確不包含（在哪個階段） |
|---|---|---|
| A1 | benchmark 表與驗證類別（reference、setup-matched、sanity、interface）；範圍比對；configuration 與隔離（`spec-v1`）；區塊 batch means、精確區間、MPV、分位數（直方圖）；判定引擎的 `equivalence` 與 `detection_limit`；兩階段事件數；種子雜湊 H；evidence 角色；`simulation-summary/1` 與 `simulation-observables/1` 的 schema 與讀取；Python summary 產生器；J14 重產；sci-fix 流程 | `change`（B2）、`threshold`／`order`／配對比較（C2）、search 角色與 seed_group（C2）、`values` 累加器（C2）、C++ summary（A2） |
| A2 | `g4sim`（`SimHash`、`SimSeed`、`SimSummary`、`MiniJson`、`SimProbe`）；`per-event` 種子；`layered_sim` 寫出 summary、column map、effective config；不含名稱的 `tree-v1`；effective config 依內容雜湊存放；研究層只讀邊界產物；schema 關鍵字 | `element_sim`（B1） |
| B1 | `element_sim.spec/1`、`element_sim`、場、平面穿越、量能器母體與漏失欄、逐事件 ROOT 檔、`simroot`、`geant4_run.py check-spec`、兩個後端的介面一致性、確定性場檢查 | `simreco`（B2）、J15 的統計研究（B3） |
| B2 | `simreco`（數位化與重建，可攜的亂數）、`geant4_run.py reco` 與 `table`、遞移的處理鏈、verification／regression／surrogate 類別與表條目、判定引擎的 `change`、CV2 | J15 的驗證梯與收斂（B3） |
| B3 | J15 研究：驗證梯、量能器 cut 收斂、variation、TOF σ_t 敏感度、recorded 資料、journey 與路由、文件 | — |
| C1 | 需求規格、元件目錄第一版、設計文法與實現、F0 解析評估、NSGA-II（標準函式庫）、搜尋紀錄（F0-only）、agent 協定、封閉測試 | 任何 Geant4 評估（C2） |
| C2 | F1/F2 評估、確認 run、判定引擎的 `threshold` 與 `order`、配對比較與 seed_group、search 角色、`values` 累加器（Python 與 `SimSummary.hh`）、利用模擬缺陷的防護、穩健性、CV3 | J16、MOBO（C3） |
| C3 | J16 自動設計範例（與 J15 比較）、選用的 MOBO（Ax/BoTorch）後端 | — |

---

## 4. 介面擁有權

| 介面 | 引入 | 位置 | 擁有者（steward） | 使用者 |
|---|---|---|---|---|
| benchmark 表、驗證類別、範圍比對、隔離規則 | A1（B2、C2 附加） | `contracts/validate.py`、`dependencies.py` | contracts（內容由 hep-detector 提出） | A1、B2、B3、C2 |
| 種子雜湊 H（Python） | A1 | `core/simulation/seeds.py` | hep-detector | geant4 adapter、`check_geant4_study.py`、detector-design |
| 種子雜湊 H（C++） | A2 | `adapters/geant4/assets/g4sim/SimHash.hh` | hep-detector | `layered_sim`、`element_sim`、`simreco` |
| 角色：evidence 角色 | A1 | `contracts/`、study spec schema | contracts | 全部 |
| 角色：search 角色、seed_group | C2 | 同上（CV3） | contracts | C2、C3 |
| `simulation-summary/1`、`simulation-observables/1` 的 schema、讀取、合併 | A1（`values` 在 C2 附加） | `core/simulation/summary.py`、`core/simulation/schemas/` | hep-detector | 全部 |
| column map、effective config 的 schema | A2 | `core/simulation/schemas/` | hep-detector | A2、B1、C2 |
| 區塊估計量、精確區間、MPV、分位數 | A1（`values` 分位數在 C2） | `core/stats/batch_means.py` | hep-statistics | hep-detector 腳本、detector-design |
| 分布函式（`t_ppf`、`f_ppf`、`garwood`） | A1 | `core/stats/distributions.py` | hep-statistics | 同上 |
| 判定引擎 | A1 `equivalence`、`detection_limit`；B2 `change`；C2 `threshold`、`order`、配對模式 | `core/stats/decisions.py` | hep-statistics | A1、B2、B3、C2 |
| `g4sim` 標頭 | A2（`SimSummary` 的 `values` 在 C2） | `adapters/geant4/assets/g4sim/` | hep-detector | `layered_sim`、`element_sim`、`simreco` |
| `element_sim.spec/1` 與 `check-spec` | B1 | geant4 adapter | hep-detector | B1、B3、C1（B1 合併後）、C2 |
| 逐事件 ROOT 檔、`simroot` | B1 | geant4 adapter | hep-detector | B2、B3 |
| `simreco` 與 reco spec | B2 | geant4 adapter（C++，不連結 Geant4） | hep-detector | B3、C2 |
| 需求規格、元件目錄、設計文法、搜尋 spec | C1 | `adapters/detector-design/` | hep-detector（待決，§7） | C1–C3 |
| `extension.design_search` 與其規則 | C2 | `contracts/`（CV3） | contracts | C2、C3 |

跨 adapter 的呼叫一律以子行程與 JSON 檔案進行（分層規則：adapter 只 import `core` 與 `contracts`），例如 detector-design 呼叫 `geant4_run.py check-spec`、`geant4_run.py run`、`geant4_run.py reco`。

---

## 5. 命名與編號

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
| 節的引用 | 「§n」是同一文件；「任務 A §n」「架構 §n」「計畫 §n」是其他文件 | — |

先前文件中的「contracts C1、C2」即 CV1、CV2；`architecture.md` 保留舊寫法，在檔頭註明對應。

---

## 6. 階段閘門

| 閘門 | 時機 | 條件 | 不通過時 |
|---|---|---|---|
| G-A1 | A1 合併前 | J14 重產的紀錄通過 `--strict` 與 `dependencies.py`；閘門、覆蓋率、MPV、偵測極限的 toy 通過 | 不合併；若 J14 因未達標而失去 `validated-in-scope`，由維護者依 §7 第 4 項決定 |
| G-A2 | A2 合併前 | J14 的 CSV 與 A2 前逐位元相同；探針不改變亂數狀態 | 不合併 |
| G-B1a | B1 開始的第一天 | `G4RootAnalysisReader` 能讀 MT 合併、壓縮的檔案與字串欄 | `simroot` 改為只讀純量欄，字串移到 JSON 旁檔（任務 B B1.5） |
| G-B1b | B1 合併前 | 確定性場檢查在名義值下通過；兩個後端共同觀測量統計一致 | 不進入 B2 |
| G-C1 | C1 合併前 | 全部封閉測試通過 | 不進入 C2 的搜尋部分 |
| G-C2a | C2 的 trial | 量測配對比較的變異縮減 | 縮減小於宣告值時，S2 改用獨立比較（任務 C C2.3） |
| G-C2b | C2 合併前 | 贏家詛咒與需求判定的 toy、CV3 的契約測試通過 | 不合併 |
| G-C3 | C3 合併前 | J16 完成並附與 J15 的比較 | 不合併 |

---

## 7. 待維護者決定的事項（合併清單）

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

## 8. 跨任務的主要風險

1. **兩個 Geant4 程式的維護成本**（`layered_sim` 凍結、`element_sim` 新增）。以 `g4sim` 控制重複；長期可在 `element_sim` 加入主粒子出射紀錄後，把 J14 遷移過去並退役 `layered_sim`（延後，觸發條件：`element_sim` 能產生 J14 的全部觀測量）。
2. **統計的實際行為**：區塊 batch means 對偏斜分布的 O(1/B) 偏差、兩階段設計的未達標率（一對點約 19 %）、配對比較的變異縮減可能很小。都以 toy 與 trial 量測，不事先假設。
3. **未逐行核對的 Geant4 行為**：stepper 的建立、Birks 的 API、場交點誤差的方向、兩個 physics list 的核子截面、`G4RootAnalysisReader` 的能力。各在第一次使用的階段先核對。
4. **計算量**：J14 重錄（A1）、量能器簇射（B3）、F1/F2 搜尋（C2）。各階段在 trial 後寫入預算。
5. **入口預算**：hep-detector quick load 只剩 931 bytes、description 1,016 / 1,024 字元。只有 §7 第 12 項可能動 `SKILL.md`。
6. **工作量估計不完整**：只有 A1 契約部分有原型估計（約 8–12 個工作天）；其餘在各階段開始時估計並記錄。
7. **參考文獻**：任務 C 引用的 GRACE、VI-BRATO 是 2026 年的預印本；所有出處在正式引用前經 hep-citations 核對。

---

## 9. 文件地圖與權威分工

| 文件 | 內容 | 權威範圍 |
|---|---|---|
| `plan.md`（本文件） | 評估、原則、階段、介面擁有權、命名、閘門、待決事項、風險、執行環境 | 順序、編號、版本代號、擁有權、閘門、待決事項、執行環境（isolated worktree） |
| `task-a-core.md` | A1、A2 的工作項與驗收 | 這兩個階段的內容與驗收 |
| `task-b-j15.md` | J15 的設計；B1、B2、B3 的工作項與驗收 | 這三個階段的內容與驗收；J15 的數值 |
| `task-c-design-search.md` | 自動化設計的設計；C1、C2、C3 的工作項與驗收 | 這三個階段的內容與驗收 |
| `architecture.md` | 設計理由、參考實驗、被取代的設計 | 理由；與規格衝突時以規格為準並回報 |
| `README.md` | 資料夾入口與檔案清單 | — |
| `gate_operating_characteristics.py`、`j15_design_estimates.py`、`design_search_closure.py` | 設計數值的計算程式 | 對應附錄的數值 |

每份規格的結構相同：§0 任務卡、§1 名詞與檔案、§2 前提與提供的介面、§3 硬性限制、§4 設計摘要、§5 起各階段的工作項與驗收、之後是契約與版本、檢查、不做與延後、待決事項與風險、執行步驟、附錄。

---

## 10. 執行環境：isolated worktree

### 10.1 原則

- **每個階段在自己的 isolated git worktree 中執行**：一個階段、一個 worktree、一個分支。
- 主要 checkout（repo 根目錄的工作區）與其他 worktree 中的檔案一律不修改。
- 理由：
  - 可以平行的階段（例如 C1 與 A2、B1）與平行的 agent 不會互相覆寫；
  - 建置目錄、Geant4 輸出與暫存檔彼此隔離；
  - 一個階段失敗時可以整個丟棄，不影響其他工作；
  - 每個階段的變更就是一個分支的 diff，審查與合併的範圍清楚。

### 10.2 建立與確認

| 項目 | 規定 |
|---|---|
| 位置 | `.claude/worktrees/geant4-<階段>`，階段名小寫，例如 `.claude/worktrees/geant4-a1` |
| 分支 | `geant4-<階段>`，例如 `geant4-a1` |
| 基底 | 已包含全部前提階段（§0 的「前提」欄）的最新 `main`；例如 B2 以 B1 合併後的 `main` 為基底 |
| 規格的來源 | 本資料夾核准後合併到 `main`，worktree 中就有規格。核准前，規格只在分支 `worktree-geant4-architecture` 上，以 `git show worktree-geant4-architecture:plugins/hep-research/docs/dev/geant4-architecture/<檔名>` 讀取，不把該分支合併進階段分支 |
| 在 Claude Code 中 | 工作階段本身以 `EnterWorktree` 進入 worktree；把工作委派給 subagent 時，Agent 工具使用 `isolation: "worktree"` |
| 在其他環境 | `git fetch origin && git worktree add .claude/worktrees/geant4-a1 -b geant4-a1 origin/main` |
| 開始前確認 | `git rev-parse --show-toplevel` 是該 worktree 的路徑、`git branch --show-current` 是該階段的分支、`git status` 乾淨；三項結果寫入該階段的工作紀錄（VALIDATION 條目的環境欄） |

### 10.3 在 worktree 中的規則

1. 所有編輯、建置、測試、Geant4 執行與規格修正都在該階段的 worktree 中進行；不 `cd` 到主要 checkout 或其他 worktree。
2. 指令使用 worktree 內清楚的絕對路徑或相對路徑；避免以執行時才計算的變數組出 git 的參數，讓工具與審查者都能確認指令留在 worktree 內。
3. **`git stash` 是所有 worktree 共用的。** 不使用裸的 `git stash` 或 `git stash pop`；需要暫存時用暫時的 WIP commit。
4. 建置目錄、E2 的輸出、ROOT 檔與 trial 的結果放在該 worktree 內不提交的目錄（例如 `build/`、`work/`，由 `.gitignore` 排除），或該 worktree 專屬的暫存目錄；不同 worktree 不共用建置目錄。Geant4 本身的安裝（E2）可以由多個 worktree 唯讀共用。
5. 只在該階段的分支提交；commit 附規定的 trailer；推送到同名的遠端分支。未經維護者核准不推送 `main`、不開 pull request。
6. 合併前在 worktree 中執行任務 A §8 的檢查，並確認閘門（§6）。
7. 實作中發現規格需要修正時，在同一個 worktree 中同時修改中英兩版並記入版本歷程；影響其他階段時同時更新本文件。
8. 獨立審查與其他 subagent 以 `isolation: "worktree"` 執行；審查只讀不寫，沒有變更的 worktree 結束後自動清除。

### 10.4 可以平行的階段

| 同時進行 | 條件 | 注意 |
|---|---|---|
| C1 與 A2、B1、B2、B3 | A1 已合併 | C1 只動 `adapters/detector-design/` 與它的文件，衝突少 |
| B3 與 C2 | B2 與 C1 已合併 | 兩者都可能修改 `geant4-study-protocol.md` 與 journey 文件；後合併者在新的 `main` 上 rebase 並重跑檢查 |

每個平行的階段各用自己的 worktree 與分支；同一個階段不由兩個 agent 同時在不同 worktree 中實作。

### 10.5 結束

- **合併後：** `git worktree remove .claude/worktrees/geant4-<階段>`，刪除本地分支；下一個階段從新的 `main` 建立新的 worktree。
- **放棄：** 移除該 worktree 與分支；不在主要 checkout 中做任何清理。
- **本資料夾本身** 在分支 `worktree-geant4-architecture` 與 worktree `.claude/worktrees/geant4-architecture` 中撰寫；之後的文件修改也在那裡進行，直到它合併到 `main`。

---

## 11. 版本歷程

| 版本 | 內容 |
|---|---|
| 2026-10-23 | 初版：整合評估（P1–P9）、規劃原則、八個階段（B 拆為 B1–B3、C 為 C1–C3）、介面擁有權、命名（契約版本改記 CV1–CV3）、閘門、合併的待決事項與風險 |
| **2026-10-23（本版）** | **加入 §10「執行環境：isolated worktree」（建立、確認、規則、平行階段、結束）與給 agent 的讀法** |
