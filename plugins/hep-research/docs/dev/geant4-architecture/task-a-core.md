# 任務 A：正確性修正與邊界產物

> 文件類型：實作規格（給執行的 agent 與審查者）。狀態：待使用者與維護者核准
> 計畫：[`plan.md`](plan.md)（階段順序、編號、介面擁有權、閘門、待決事項）。理由：[`architecture.md`](architecture.md)。本文件是 A1、A2 的可執行規格；與其他文件不一致時，內容與驗收以本文件為準並回報
> 順序：A1 → A2；之後是任務 B（[`task-b-j15.md`](task-b-j15.md)）與任務 C（[`task-c-design-search.md`](task-c-design-search.md)）
> 執行環境：**每個階段在自己的 isolated git worktree 中執行**（分支 `geant4-<階段>`，例如 `geant4-a1`；計畫 §10）；開始寫程式前先建立並確認 worktree，不修改主要 checkout
> 基準：hep-research `main` 的 `9f08796`（0.23.0 加未發布的變更），contracts 3.5.0，adapter geant4 0.1.0，Geant4 11.4.3
> 日期：2026-10-23
> 語言：繁體中文原文；英文版 [`task-a-core.en.md`](task-a-core.en.md) 內容相同。兩者不一致時以中文為準，並同時修正英文

---

## 0. 任務卡

**目標。** 修正會讓模擬研究被錯誤標成 `validated-in-scope` 的缺陷（D1–D8、D10），並讓研究層只透過三個邊界產物（run summary、column map、effective config）認識模擬後端（D9）。統計與 summary 讀取一開始就放在 `core/`，讓之後的 adapter（任務 C）可以直接使用。

**兩個階段（依序，各自合併）：**

| 階段 | 內容 | 版本 | 語言 |
|---|---|---|---|
| **A1** 正確性修正 | 契約（benchmark 表、範圍、configuration 與隔離、evidence 角色）；`core/stats/`（區塊 batch means、精確區間、MPV、分位數、判定引擎的 `equivalence` 與 `detection_limit`、分布函式）；`core/simulation/`（種子雜湊、summary 與觀測量的 schema 與讀取）；Python summary 產生器；J14 重產 | contracts **CV1**（minor，sci-fix） | Python |
| **A2** 共用標頭與邊界產物 | `g4sim`（`SimHash`、`SimSeed`、`SimSummary`、`MiniJson`、`SimProbe`）；`per-event` 種子；`layered_sim` 寫出三個邊界產物；不含名稱的 `tree-v1`；effective config 依內容雜湊存放；研究層只讀邊界產物 | geant4 adapter **0.2.0**；contracts 不升版 | C++ 與 Python |

**不在範圍內：**
- `element_sim`、場、平面穿越、ROOT 檔、`simroot`、`simreco`、J15（任務 B）；判定引擎的 `change`（B2）。
- 判定引擎的 `threshold`、`order`、配對比較、search 角色、seed_group、`values` 累加器（任務 C 的 C2；計畫原則 R1）。
- `layered_sim` 的 spec 格式（spec/1）不重構，只加選用欄位。

**交付物：** 程式與測試；重產的 J14 紀錄；sci-fix 的 ledger 條目與 advisory；VALIDATION 條目 GEANT4-CORRECTNESS（A1）與 GEANT4-SUMMARY（A2）；CHANGELOG；release manifest。

**完成的定義：** A1.15 與 A2.10 的驗收清單全部打勾；§8 的檢查全部通過；閘門 G-A1、G-A2（計畫 §6）通過。

**主要決定：**
1. **A1 是最小的 sci-fix。** 只含修正 D1–D8、D10 所需的變更與它們的直接基礎；任務 B、C 才需要的判定與欄位由它們自己加入（計畫原則 R1、R4）。
2. **共用程式在 `core/`。** adapter 只能 import `core` 與 `contracts`；統計、判定、種子雜湊與 summary 讀取從第一天起就在 `core/`，hep-detector 的腳本只是呼叫層。
3. **重現 = 判定相同。** 不追求逐位元相同的統計量（§4.3）。
4. **`layered_sim` 凍結。** A2 只加選用欄位與檔案；新的幾何功能在任務 B 的 `element_sim`。

**第一步：** 依計畫 §10.2 為本階段建立 isolated worktree（`.claude/worktrees/geant4-<階段>`，分支 `geant4-<階段>`，基底為已含前提階段的最新 `main`），並確認 `git rev-parse --show-toplevel`、`git branch --show-current` 與 `git status`。以下所有步驟都在這個 worktree 中進行。

**開始前必做：**
1. 確認 `main` 是否已超過 `9f08796`。若是，讀新的 CHANGELOG，重做附錄 C 的核對，並更新本文件（中英兩版）。
2. 讀計畫 §0–§6；讀架構 §0、§2；讀 `docs/maintenance.md` 的 sci-fix 流程、adapter 變更流程、release 步驟。
3. A1 從 `prototype/phase1-core.patch` 開始：它實作了 A1.1、A1.2、A1.3 的前半與 A1.12 的 enum 修正，但早於本規格（缺 `target_slabs`、驗證類別、依 benchmark 宣告的範圍維度、`hash_scheme`、`dependencies.py` 的重新推導與 CV1 閘控；閘控寫死 3.6.0；把 `longitudinal-profile` 寫成 `("reference", ("shower-shape",))`）。

---

## 1. 名詞與檔案

| 名詞 | 意義 |
|---|---|
| J14 | 既有 journey `examples/geant4-thin-silicon/`：薄矽層研究，唯一有 `validated-in-scope` 紀錄的 Geant4 範例 |
| study record | 帶 `extension.study` 的 computational-run 紀錄；`label` 決定其 artifact label |
| `validated-in-scope` | 經可升級的 benchmark 驗證、且宣告範圍在 benchmark 範圍內時才可有的 label；由 `contracts/validate.py` 的 `_study_upgrade` 把關 |
| 驗證類別 | benchmark 參考的性質（§4.4）；A1 定義 reference、setup-matched、sanity、interface；B2 加入 verification、regression、surrogate |
| observable kind | study spec 中受控的觀測量種類（enum），如 `most-probable-value` |
| configuration | 目標的放置情形：`isolated` 或 `embedded`（A1.3） |
| 邏輯 run | 由 spec、後端與邏輯 run 種子 S 決定的 N 個事件，編號 0 … N−1；可切成多個工作（job） |
| 區塊 | 邏輯 run 中依事件編號劃分的 K 段，每段 B 個事件（N = K·B）；batch means 的單位 |
| 三個邊界產物 | run summary（`simulation-summary/1`）、column map（`simulation-columns/1`）、effective config（引擎無關外框加實際幾何樹） |
| `seeding` | `stream`（既有行為）或 `per-event`（每個事件以 H(S, 事件編號) 重設；A2 起） |
| `hash_scheme` | 目標雜湊的推導方式：`spec-v1`（A1，由 spec/1）或 `tree-v1`（A2 起，由幾何樹） |
| 角色 | run 在研究中的用途；A1 定義 evidence 角色 trial、nominal、scan、control、variation、calibration；B2 加入 regression；C2 加入 confirmation 與 search 角色 |
| 判定引擎 | `core/stats/decisions.py`；A1 提供 `equivalence` 與 `detection_limit`，B2、C2 附加其他判定 |
| CV1、CV2、CV3 | 合併時才定號碼的 contracts minor（計畫 §5）；CV1 屬 A1 |
| E2 | 有 Geant4 11.4.3 建置的執行環境 |
| IUT | intersection-union test：所有觀測量都等價才通過 |
| DL | negative control 的偵測極限 |
| sci-fix | `docs/maintenance.md` 中修正科學正確性缺陷的流程 |
| 記法 | 「A1.6」是本文件的工作項；「§7」是本文件的節；「B1.3」「C2.1」是任務 B、C 的工作項；「計畫 §n」「架構 §n」是其他文件的節 |

**主要檔案（相對 `plugins/hep-research/`）：**

| 用途 | 路徑 |
|---|---|
| 契約 | `contracts/validate.py`、`contracts/dependencies.py`、`contracts/schema.py`、`contracts/schemas/ext_computational_run.json` |
| 共用模組（新增） | `core/stats/distributions.py`、`core/stats/batch_means.py`、`core/stats/decisions.py`（steward hep-statistics）；`core/simulation/seeds.py`、`core/simulation/summary.py`、`core/simulation/schemas/`（steward hep-detector） |
| 既有 core | `core/status.py`、`core/trace.py`、`core/OWNERS.json`、`core/stats/tail_estimation.py`（`beta_ppf`、`clopper_pearson`）、`core/partition/engine.py`（`NON_ADDITIVE_TOKENS` 行 381） |
| 研究層 | `skills/hep-detector/scripts/check_geant4_study.py`（`convergence()` 行 335、相對差行 357、判定行 359、`scope_within()` 行 482）、`geant4_benchmarks.py`（`GRADES` 行 92–94、`bootstrap()` 行 197、`mpv()` 行 204、偵測極限行 274、MPV 的 bootstrap SE 行 369、`at_limit` 行 678）、`tracker_resolution.py`、`multiple_scattering.py`；`skills/hep-detector/assets/geant4-study-spec.schema.json`；`skills/hep-detector/references/geant4-study-protocol.md` |
| adapter | `adapters/geant4/adapter.json`；`adapters/geant4/assets/geant4_run.py`（`SIM_SOURCES` 行 63、`validate_spec()` 行 103、`cmd_scan` 行 435、`cmd_chunk` 行 491、`cmd_summarize` 行 525）、`geant4_build.py`（`GEANT4_USE_GDML: OFF` 行 53）、`geant4_verify.py`、`g4common.py`（既有的 Python 模組）；`adapters/geant4/assets/layered_sim/`（`Actions.cc`：CSV 格式 `%.10g` 行 23、沉積乘 track 權重行 113；`layered_sim.cc`：種子與 run manager 行 150–154；`MiniJson.hh`、`spec.schema.json`、`output.schema.json`） |
| J14 | `examples/geant4-thin-silicon/run.py`、`recorded/`（`events/` 5 個縮減 CSV、`runs/`、`summaries/`、`specs/`）、`output/` |
| 測試 | `tests/contracts/test_geant4_upgrade.py`、`test_simulated_dataset.py`、`test_schema_keywords.py`；`tests/adapters/test_geant4.py`；`tests/examples/test_geant4_thin_silicon.py`；`tests/skills/test_cli_robustness.py` |
| 工具 | `tools/run_all_checks.py`、`check_layering.py`、`check_relocation.py`、`check_ownership.py`、`check_packaging.py`、`measure_entrypoints.py`、`reference_inventory.py`、`capability_map.py`、`check_routing_static.py`、`scifix_advisories.py` |

---

## 2. 前提與提供的介面

**前提：** 無（任務 A 先做）。

**提供給任務 B、C 的介面**（擁有權見計畫 §4）：

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

附加只能是選用欄位、新的 enum 值或新的函式，不能改變既有行為（計畫原則 R2）。

---

## 3. 硬性限制

違反任何一條都不能合併。

1. **分層。** skill 腳本與 adapter 只 import `core` 與 `contracts`。hep-detector 的腳本與任何 adapter 都需要的程式（統計、判定、種子雜湊、summary 讀取）放在 `core/`，並在 `core/OWNERS.json` 指定 steward；`core/` 不得引用 `skills/`、`adapters/`、`profiles/` 的路徑。
2. **實驗名稱。** `skills/`、`contracts/`、`core/` 中不得出現實驗名稱（含 ALICE；`check_layering.py`）；需要時用引用鍵。
3. **Python 只用標準函式庫**；不加 Python 綁定。t 與 F 分位數（非整數自由度）與 Garwood 區間以既有的 `beta_ppf` 實作在 `core/stats/distributions.py`（這是共用的數值函式，不是 §9 所說的「新的 core 驗證器」）。
4. **C++ 依賴。** `g4sim` 的 `SimHash.hh`、`SimSummary.hh`、`MiniJson.hh` 只用 C++17 標準函式庫；`SimSeed.hh`、`SimProbe.hh` 與 `layered_sim` 連結 Geant4。不引入第三方函式庫。
5. **G5 授權邊界。** Python 只和獨立執行檔交換 JSON 與 CSV；程式依 Geant4 API 撰寫，不複製或改寫 Geant4 範例程式碼。
6. **狀態與退出碼**（`core/status.py`）：0 ok、1 負向判定（`refused`/`failed`）、2 無法使用的輸入（`rejected`）、3 `incomplete`。未定案與未達標一律是 3。
7. **execution trace。** 新的紀錄寫入者呼叫 `trace.provenance()`；新的共用函式呼叫 `trace.tag()`；呼叫 C++ 執行檔時記錄執行檔與原始碼的 sha256、版本、子命令。
8. **大小與路徑。** 單檔 ≤ 2 MiB（`check_packaging.py` 掃描所有文字檔）；寫出的路徑經 `tilde()`；plugin README 的大小聲明需在實際值的 10 % 內。
9. **入口預算。** hep-detector quick load ≤ 25,600 bytes（目前 24,669），description ≤ 1,024 字元（`measure_entrypoints.py` 回報 1,016）。本任務不修改 `skills/hep-detector/SKILL.md` 與 description。
10. **流程。** A1 依 sci-fix 流程；A2 依 adapter 變更流程；兩者都依 release 步驟。每個階段在自己的 isolated worktree 與分支（`geant4-a1`、`geant4-a2`）中工作（計畫 §10）；未經維護者核准不推送 `main`、不開 pull request。
11. **契約版本。** 新規則以 `strict or _at_least(contract_version, CV1)` 閘控，不設 warning 分支。
12. **J14 的離線重播** 永遠可以執行，且不需要 Geant4 與編譯器。
13. **不改既有輸出。** A2 只新增檔案與選用欄位；J14 既有 spec 的 CSV 必須和 A2 前逐位元相同（同一主機）。
14. **不做：** 整數量化、128 位元整數、逐位元相同的統計量、spec 格式轉換、`simstat`、不連結 Geant4 的 `simcore`（理由見架構 §13）。

---

## 4. 設計摘要

### 4.1 已確認的缺陷（`9f08796`）

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

### 4.2 兩個平面

逐事件的處理在 C++（模擬程式；A2 起包括 summary 的累加）；合併後的推論、判定、紀錄、契約在 Python。同一個量只有一份正式實作；另一種語言的實作只能在測試中作為 oracle。A1 的 summary 由 Python 從逐事件 CSV 產生；A2 起由 `layered_sim` 產生，Python 產生器只留在測試中。

### 4.3 重現的定義

| 層次 | 要求 |
|---|---|
| 追溯 | 每份紀錄保存 spec、effective config、程式（`sources_sha256`）、種子、輸入與輸出檔案的雜湊 |
| 重新執行 | 同一建置與平台、同一邏輯 run：事件內容相同；summary 的整數累加量相同，浮點相對差 ≤ 1e-12 |
| 重播（由已提交的 summary 與紀錄） | 判定與 label 完全相同；數值相對差 ≤ 1e-9；判定邊距 < 1e-9（相對）時在紀錄中標記「接近門檻」 |
| 回歸檢查（A2） | J14 既有 spec（`seeding: stream`）在同一主機上產生和 A2 前逐位元相同的 CSV |

### 4.4 驗證類別

| 類別 | 參考 | 能否升級 | 引入 |
|---|---|---|---|
| reference | Geant4 所近似的物理模型或薄靶量測，在 isolated 目標上 | 能（範圍內） | A1（CV1） |
| setup-matched | 已發表的量測，目標雜湊和量測配置相同，且 isolated | 能（範圍內） | A1（CV1） |
| sanity、interface | 合理範圍、介面檢查 | 不能 | 既有 |
| verification | 輸入的精確推論（解析螺旋、運動學） | 不能 | B2（CV2） |
| regression | 前一個版本的同一研究 | 不能 | B2（CV2） |
| surrogate | 以完整模擬為參考的快速模擬或代理模型 | 不能改變物理 label | B2（CV2） |

### 4.5 `core/` 中的共用模組

| 模組 | A1 的內容 | 之後附加 |
|---|---|---|
| `core/stats/distributions.py` | `t_ppf`、`f_ppf`（非整數自由度）、`garwood` | — |
| `core/stats/batch_means.py` | 區塊估計量、SE、共變異、精確區間、直方圖分位數、MPV | C2：`values` 的經驗分位數 |
| `core/stats/decisions.py` | `equivalence`（IUT 閘門）、`detection_limit`；回傳 `{verdict, margin, reason}`，`reason` 取自封閉清單 | B2：`change`；C2：`threshold`、`order`、配對模式 |
| `core/simulation/seeds.py` | 種子雜湊 H、邏輯 run 種子、工作種子 | — |
| `core/simulation/summary.py` 與 `schemas/` | `simulation-summary/1`、`simulation-observables/1` 的 schema、讀取、驗證、合併 | A2：column map 與 effective config 的 schema；C2：`values` 欄位 |

hep-detector 的 `check_geant4_study.py` 與 `geant4_benchmarks.py` 改為呼叫這些模組；之後的任務也呼叫同一份實作。

---

## 5. 階段 A1：正確性修正（contracts CV1，sci-fix）

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

**修改：** `contracts/validate.py`（唯一實作，匯出）；`check_geant4_study.py`（匯入，刪除 `scope_within()`；`label` 寫 `declared_scope.observable_kind`）；study spec schema（`validation_plan.scope` 是 `additionalProperties: false`，加入 `observable_kind`）。

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
- A1 的新錄製一律 `seeding: stream`（`layered_sim` 現有行為）；單一工作的種子對為 (H(S, 0, 0), H(S, 0, 1))。不使用 `make_manifest` 的 `seed × 100003 + k`、`cmd_scan` 的 `[s0, s1 + k]`、`cmd_chunk` 的 `start + 1`。
- 一個邏輯 run 可以切成多個工作（`geant4_run.py chunk` 以手動建立的 manifest，每個工作涵蓋一段事件編號）：起始事件為 e 的工作，種子對為 (H(S, e, 0), H(S, e, 1))；S 另外記錄在 run record。同一 manifest 內的種子因此彼此不同，`validate_manifest` 的 `partition.duplicate_seed` 檢查不需修改。`stream` 模式下不同切法的事件不同，但統計上等價。
- **角色：** run record 的 `role` 取自 evidence 角色 enum（trial、nominal、scan、control、variation、calibration）；未知的角色是 error（CV1 閘控）。enum 可在之後附加（B2 的 regression、C2 的 confirmation 與 search 角色）。
- **唯一性：** 同一研究的所有 run record 中 S 不重複（`check_geant4_study.py` 檢查）。A1 不重錄的 5 個 J14 run（A1.13）沒有 S：它們以原本的種子對（第一個種子 1401 或 1402）登記為 `seed_scheme: legacy`，只檢查完整種子對不重複。

### A1.5 summary、觀測量宣告與 Python 產生器

**修改：** 新增 `core/simulation/summary.py`（`simulation-summary/1` 的讀取、schema 驗證、依區塊合併、累加器的存取）與 `core/simulation/schemas/`（`simulation-summary/1`、`simulation-observables/1`）；新增 `adapters/geant4/assets/summary_from_csv.py`（或 `geant4_run.py` 的子命令 `summarize-blocks`），以 `core/simulation/summary.py` 寫出與合併。

- **觀測量宣告 `simulation-observables/1`：** 陣列，每項 `{name, source_column, selection, bins: {lo, hi, width}, thresholds, tolerance_mode}`。`selection` 是對 CSV 欄位的宣告式篩選（欄名、比較子 `==`、`!=`、`<`、`<=`、`>`、`>=`、值；多個條件為 AND）；`thresholds` 給 `count_if` 用；`tolerance_mode` 見 A1.8。study spec（A1.12）與模擬程式的 `output.observables`（A2.3、B1.1）都引用它。
- **輸入：** 一個或多個工作的逐事件 CSV、觀測量宣告、區塊大小 B 與區塊數 K。
- **選擇：** 每個觀測量只累加滿足其 `selection` 的事件（例如 MPV 與 `tail_fraction` 需要 `primary_fate == 1` 且 `primary_end_process == "Transportation"`，見 `geant4_benchmarks.py` 行 232–236、`check_geant4_study.py` 行 284）；`n` 是通過選擇的事件數，另記錄每個區塊的總事件數。
- **區塊：** 事件 i（`event` 欄減去邏輯 run 的第一個事件編號）屬於區塊 ⌊i/B⌋；i ≥ K·B 的事件忽略並註明數量。
- **每個區塊、每個觀測量的累加器：** 整數 `n`、直方圖每格計數（固定分格；溢位與下溢分開）、`count_if[]`；浮點 Σx、Σx²、`min`、`max`（Neumaier 補償加總）。
- **輸出欄位：** `summary_version`、`run`（邏輯 run 的識別與種子、`role`、事件範圍、`seeding`、B、K、spec 雜湊、產生者 `python-csv` 與版本）、`observables[]`、每個累加器的 `merge` 規則（`sum`、`min`、`max`、`hist`）。多個工作依區塊編號合併。schema 允許附加選用欄位（C2 的 `values`）。
- **事件權重：** CSV 有 `weight` 欄時必須全為 1，否則 exit 2（沉積已乘 track 權重，見 `Actions.cc` 行 113）。沒有 `weight` 欄時（J14 的 5 個縮減 CSV 就沒有），summary 記錄 `weight_column: absent`，並以 run record 的 spec 中沒有 biasing 指令作為依據；spec 中有 biasing 指令時 exit 2。
- A2 起 `layered_sim` 以相同 schema 寫出 summary；這個 Python 產生器只留在測試中作為 oracle。

### A1.6 估計量與 SE（D5）

**修改：** 新增 `core/stats/distributions.py` 與 `core/stats/batch_means.py`；`check_geant4_study.py`、`geant4_benchmarks.py` 改為呼叫它們（只讀 summary；刪除 `bootstrap()` 的正式使用，保留在測試中作為對照）。

- 每個區塊 b 算 θ_b；回報 θ̄ = 平均，SE = sd(θ_b)/√K，自由度 K − 1。K ≥ 16，在第一個證據 run 前宣告。
- 多個觀測量：每個區塊的估計量向量一起保存，共變異由這些向量估計。
- 全樣本值：平均與比例另由合併累加器算出，和 θ̄ 的差寫入紀錄作為診斷。
- 分位數：直方圖內線性內插；分格寬度除以估計值須小於相對容許值的 1/10；落在溢位或下溢格時判為 incomplete。
- **計數很少時：** 計數型估計量在任一區塊為 0 或合併總數 < 100（門檻可宣告）時，改用合併累加器上的精確區間：比例用 Clopper–Pearson（既有的 `clopper_pearson`），計數用 Garwood；兩個 run 的比較用精確條件二項法求率之比的區間，相對差 = 比 − 1。這時沒有 SE，閘門以區間端點判定（A1.8）。
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
- **差值：** 沿用行 357 的慣例：a 為最細的設定，b 為第二細的設定（`vals` 由小到大排序，a = `finest[0]`、b = `finest[1]`）。觀測量宣告 `tolerance_mode`：`relative`（預設）時 diff = (a − b)/b、se_diff = √(se_a² + se_b²)/|b|；`absolute` 時 diff = a − b、se_diff = √(se_a² + se_b²)。ν 以 Welch 公式逐對計算（等變異數、K = 16 時為 30）。（`absolute` 的第一個使用者是 B3；因為它只是同一個函式的選項，放在 A1 以免之後改變閘門的定義。）
- **事件數目標：** 每個點的 se 目標為 tol/(4√2)（`relative` 時為相對 se）。
- **判定：** 通過 |diff| + t₀.₉₅(ν)·se_diff ≤ tol，**且兩個點都達到 se 目標**；失敗 |diff| − t_{1−α/m}(ν)·se_diff > tol（α = 0.05，m 為（參數 × 觀測量）組數；未達 se 目標也可以判失敗，因為較大的 se 只會讓失敗更難成立）；其他為 unresolved。計數很少時：通過 = 90 % 區間落在 [−tol, tol] 內；失敗 = 單邊 1 − α/m 區間完全落在外側。
- **回報：** unresolved 與未達標以 `incomplete`（exit 3）回報，label 保持 `unvalidated`；只有失敗是 `failed`（exit 1）。目前把非 pass 一律當 `failed`，需要修改。

**操作特性**（以 `gate_operating_characteristics.py` 重算，每格 2×10⁶ 次 toy。「se = 目標」：se_diff 等於目標、以 ν = 30 估計；「兩階段」：兩個點各依 A1.9 設計，K = K_trial = 16，ν 以 Welch 公式由估計的 se 計算）：

| 真實差值 | 通過（se = 目標） | 通過（兩階段） | 通過（兩階段，兩點都達標的條件下） | 失敗 m = 1（se = 目標） | 失敗 m = 30（se = 目標） | 失敗 m = 30（兩階段） |
|---|---|---|---|---|---|---|
| 0 | 0.976 | 0.809 | 0.999 | 0.000 | 0.000 | 0.000 |
| tol/2 | 0.621 | 0.696 | 0.860 | 0.000 | 0.000 | 0.000 |
| tol | 0.050 | 0.044 | 0.054 | 0.050 | 0.002 | 0.002 |
| 2 tol | 0.000 | 0.000 | 0.000 | 0.988 | 0.780 | 0.952 |

- 兩階段設計下約 19 % 的點對至少一點未達標，因此真實差值為 0 時通過率只有 0.809。
- 真實差值為 tol 時，無條件的通過率 0.044 ≤ 0.05；在兩點都達標的條件下是 0.054，略高於名義的 0.05（達標的點 se 偏小），在 protocol 中揭露。
- 真實差值為 tol 時約 90 % 是 unresolved；protocol 寫明預期的 incomplete 比例。

### A1.9 兩階段事件數

- N = ceil(N_trial·(SE_trial/target)²·f)，f = F₀.₉₀(K − 1, K_trial − 1)（兩者都是 16 時 ≈ 1.97）。
- 約 10 % 的證據 run 會未達標，判為 incomplete，**不得補跑**（若維護者選 F₀.₉₅ ≈ 2.40，約 5 %，事件數多約 22 %；計畫 §7 第 4 項）。
- 未達標是逐 run 獨立的：收斂閘門的一對點約 19 % 不完整；需要 n 個有 se 目標的 run 的研究，全部達標的機率約 0.9ⁿ（n = 6 時約 0.53）。protocol 寫明這一點。
- A1 不重錄的 5 個 J14 run 事件數固定，不是依本設計規劃的；它們的 se 仍和目標比較，未達標時同樣判為 incomplete。
- 計數很少時，以 trial run 的 Poisson 變異數規劃。

### A1.10 negative control 與偵測極限（D3）

**修改：** `geant4_benchmarks.py`；偵測極限的計算在 `core/stats/decisions.py` 的 `detection_limit()`。

- 判定量：shift = (control − nominal)/reference，SE 由兩個 run 合成。
- **抓到（caught）：** 控制組的 benchmark 判定為失敗，即 |rel_c| > tol（rel_c 為控制組相對參考值的偏差）；和現行程式以控制組 benchmark 判定的做法一致（`geant4_benchmarks.py` 約行 672）。
- 偵測極限：DL = tol + |rel| + t_{0.977}(ν)·se_rel（取代行 274 的 `2 * se_rel`）；rel 為 nominal 相對參考值的偏差，se_rel 為 shift 的合成 SE，ν 為其 Welch 自由度。
- 設計要求：toy 證明在 DL 注入時抓到的機率 ≥ 0.977。依上述定義，真實檢定力在 0.977 附近（審查者的計算約 0.9785），所以 toy 的驗收門檻是 0.977 − 3σ_MC（A1.15）。
- 正負兩個方向都注入；否則把宣稱限縮為單向，寫入 `scope.detection_limit_sign`。位於偵測極限 = caught 且 |shift| ≤ 1.1 × DL。
- 單次未抓到時記錄並說明，不自動失敗；不得換種子重跑。
- J14 現有控制組只注入 +密度；在負方向控制組錄製前，兩個 J14 宣稱限縮為 `detection_limit_sign: "+"`。

### A1.11 停止規則、證據相關性與 trace（D6、D7）

- protocol 第 4 節：停止規則、掃描格點、K 與 B、unresolved 的處理，在第一個證據 run 前寫入 study spec。
- `extension.study.evidence_overlap` 列出被多個判定共用的 run，附 `evidence_overlap_version`。
- trace tag（小寫連字號）：`geant4-scope-kind`、`geant4-configuration`、`geant4-convergence-iut`、`geant4-batch-means`、`geant4-mpv-block`、`geant4-seed-hash`。`check_geant4_study.py` 改 import `contracts.validate` 後，`code_paths` 會多出 `contracts/validate.py`，這是預期的變化。

### A1.12 其他修正（D8、D10）

- study spec 的 benchmark enum 補上 `shower-containment` 與 `longitudinal-profile`；grade enum（目前為 reference、sanity、interface）加入 `setup-matched`；observable kind enum 加入 `shower-maximum`；`validation_plan.scope` 加入 `observable_kind`。
- study spec（頂層 `additionalProperties: false`）新增頂層屬性：`observables`（引用 `simulation-observables/1`；`name` 必須和 `convergence_plan.observables` 中的名稱相同，例如 `mpv_deposit_MeV`）與 `blocks: {K, B}`。既有的單數 `observable` 不變，仍是研究的主觀測量。
- `ext_computational_run.json` 在 schema 中宣告既有的 `simulation` 屬性（J14 的 run record 已帶 `extension.simulation`，`_study_upgrade` 也已檢查它；需 hep-computing 同意）。
- D10：`test_geant4_upgrade` 與 `test_simulated_dataset` 不再共用會被刪除的暫存目錄（各自建立重播，或改為 package 層級的 fixture）。

### A1.13 J14 的重產與錄製

| run 類型 | 現況 | A1 的做法 |
|---|---|---|
| 有逐事件 CSV 的 5 個 run（`events/`，含 `event` 欄） | 單一縮減 CSV | 不重錄：以 A1.5 的產生器離線切區塊，產生並提交 `simulation-summary/1` |
| 13 個掃描、variation 與情境 run（例如 `mpv-cut-0.1`、`sp-em-option3`、`mpv-density-10`） | 只有 `geant4-run-summary/1`（一個值加 bootstrap SE） | 在 E2 以 `seeding: stream` live 重錄（事件數依 A1.9）；產生並提交 summary；CSV 不提交 |
| 負方向（−密度）控制組 | 不存在（既有的 `mpv-control`、`sp-control` 只注入 +密度） | 在 E2 新錄製，提交 summary |

- 重播：`examples/geant4-thin-silicon/run.py` 改由已提交的 summary 計算，符合 §4.3 的重播要求；不需要 Geant4 與編譯器。
- 舊的 `geant4-run-summary/1` 檔案保留，只供舊紀錄重播。
- recorded 的大小在 A1 中量測，受 `check_packaging.py` 限制；上限由維護者決定（計畫 §7 第 5 項）。

### A1.14 版本與 sci-fix 流程

- **版本：** contracts CV1（minor）。新增閘控規則族的先例（2.4.0、2.6.0、2.8.0、3.1.0、3.2.0）都是 minor。
- **ledger：** 每個缺陷一筆，`changelog` 為結構化物件（`{"kind": "unreleased", ...}`）。

| 缺陷 | ledger 條目 | 等級 | 理由 |
|---|---|---|---|
| D1（含依 benchmark 宣告的範圍維度） | scope-kind | S2 | 改變判定 |
| D2（含驗證類別） | grade-table | S2 | 改變判定 |
| D3（含 t 分位數的偵測極限） | control-shift | S2 | 改變判定 |
| D4（含差值與 se 的定義） | gate-IUT | S2 | 改變判定 |
| D5（含區塊 batch means 取代 bootstrap、精確計數區間、MPV 內插） | variance-method | **S1** | 改變回報的數值 |
| 隔離定義（含真空） | isolation | S2 | 改變判定 |
| D6 | stopping-rule | S3 | 只是指引 |

- **證據：** S2 需 C2 與 D2 層級；S1 需 C3 與 D2 層級（`docs/maintenance.md` 的證據層級；這裡的 C2、D2 是證據層級，不是契約版本或缺陷編號）。證據測試經 `validate.py` 與 `check_geant4_study.py` 的命令列執行，才能在 parent commit 上執行；不能執行的寫入 `gaps`。
- **advisory：** S1 與 S2 各一份（`scifix_advisories.py check` 要求 advisory 的等級和每個列出的 ledger 條目相同）；編號取合併時下一個未使用者（目前為 SFA-2026-038 與 -039）。
  - 鍵：`artifact_types: [computational-run]`、`extension_keys: ["study", "evidence_records"]`。
  - 範圍：introduced 0.20.0，附 `database_specific.introduced_basis`；受影響版本 0.20.0–0.23.x 與未發布版本。
  - simulated dataset-record 無法用鍵區分；remedy 要求持有者對每個 simulated 表格執行 `contracts/dependencies.py`。
- 0.20.0 以後產生、帶 `validated-in-scope` 的 study record 在 `--strict` 下會失敗；advisory 說明處理方式（以新版本重產）。

### A1.15 A1 驗收

- [ ] kind 不符、宣告缺少維度、類別或等級與表不符、configuration 缺少或 embedded、目標雜湊或 `hash_scheme` 不符的紀錄，在 `--strict` 與 CV1 下被拒；`dependencies.py` 重新推導不符時被拒；純量範圍正確比對。
- [ ] 未知的角色、同一研究中重複的 S 被拒；legacy 種子的 run 依規則檢查。
- [ ] 重產的 J14 study record 通過 `validate.py --strict` 與 `dependencies.py`；判定的任何改變都記錄並說明原因（閘門 G-A1）。
- [ ] 閘門 toy（每格 10⁴ 次，依 A1.8 表頭說明的模型）和 A1.8 的表一致到 ±3σ_MC；`absolute` 模式與計數很少時的區間判定有測試。
- [ ] 區塊 batch means 的覆蓋率 toy：J14 各類估計量（平均、比例、分位數、眾數）名義 90 % 區間的實際覆蓋率滿足 |覆蓋率 − 0.90| ≤ 0.02 + 3σ_MC，逐類回報。
- [ ] MPV 偏差 toy 的 95 % 上界 ≤ tol/10；每次的實測核對生效。
- [ ] 偵測極限 toy（A1.10 的 caught 定義）：在 DL 注入時抓到的機率 ≥ 0.977 − 3σ_MC；J14 的實現控制組結果記錄於 VALIDATION。
- [ ] J14 的離線重播由已提交的 summary 執行，判定符合 §4.3，不需要 Geant4 與編譯器。
- [ ] Python 產生器的單元測試：區塊劃分、選擇、合併、`weight ≠ 1` 時 exit 2、溢位格。
- [ ] 新的 `core/` 模組各有單元測試（`t_ppf`、`f_ppf`、`garwood` 對已知值；H 的測試向量），在 `core/OWNERS.json` 有 steward；一個只 import `core` 的測試（模擬 adapter 的用法）能讀 summary、計算估計量並呼叫 `equivalence`；`check_layering.py` 通過。
- [ ] `python3 -m unittest discover -s tests/contracts -t .` 沒有錯誤。
- [ ] 七筆 ledger 條目、兩份 advisory 通過 `scifix_advisories.py check`、parent record 齊全；live Geant4 證據以 release-gate 執行記錄；VALIDATION GEANT4-CORRECTNESS；CHANGELOG；release manifest。

---

## 6. 階段 A2：共用標頭與邊界產物（geant4 adapter 0.2.0）

A2 不改 `layered_sim` 的 spec 格式與既有輸出，只新增選用欄位與檔案。

### A2.1 `g4sim`

**位置：** `adapters/geant4/assets/g4sim/`（標頭檔；`layered_sim`、任務 B 的 `element_sim` 與 `simreco` 共用；擁有者 hep-detector）。目錄名不用 `g4common`，以免和既有的 Python 模組 `assets/g4common.py`（四個腳本 import、列在 `adapter.json`）混淆。

| 檔案 | 內容 | 依賴 |
|---|---|---|
| `SimHash.hh` | SHA-256（在 plugin 內撰寫）與 A1.4 的 H，以測試向量和 `core/simulation/seeds.py` 核對；SplitMix64 產生器與 Box–Muller 常態亂數（供不連結 Geant4 的程式使用，跨平台結果相同） | 只有 C++17 標準函式庫 |
| `SimSeed.hh` | 事件 i 的兩個種子 (H(S, i, 0), H(S, i, 1))；呼叫 `G4Random::setTheSeeds` | Geant4、`SimHash.hh` |
| `SimSummary.hh` | 區塊累加器（A1.5 的欄位）、Neumaier 加總、合併、`simulation-summary/1` 的 JSON 寫出 | 只有 C++17 標準函式庫 |
| `MiniJson.hh` | 由 `layered_sim/` 移入（內容不變；`layered_sim` 改為 include 這份） | 只有 C++17 標準函式庫 |
| `SimProbe.hh` | 探針（A2.4） | Geant4 |
| 輔助 | 材料建立（含混合材料的順序）、physics list 選擇、CSV 寫出 | Geant4 |

- 把 `layered_sim` 既有程式中相同功能的部分搬入 `g4sim` 時不得改變其行為（回歸檢查保證）。
- `SimHash.hh` 與 `SimSummary.hh` 以選用的 ctest 在沒有 Geant4 的環境測試（CI 選用工作）。

### A2.2 逐事件種子

- `layered_sim` 的 spec/1 加入選用的 `run.seeding`：`stream`（預設，既有行為）或 `per-event`。
- `per-event`：事件 i 在 `GeneratePrimaries` 的**開頭**（任何亂數抽取之前）以 `SimSeed.hh` 重設亂數，i 為全域事件編號。Geant4 在 `BeginOfEventAction` 之前就呼叫 `GeneratePrimaries`，所以不能在 `BeginOfEventAction` 重設；`BeginOfEventAction` 不得抽亂數。同一邏輯 run 以任何工作切法、任何執行緒數，事件內容相同。
- J14 的既有 spec 不改，維持 `stream`。新研究的 spec 由 adapter 預設寫入 `per-event`。

### A2.3 `layered_sim` 寫出 run summary

- spec/1 加入選用的 `output.observables`（引用 `simulation-observables/1`）與 `output.blocks`（K、B、邏輯 run 的第一個事件編號）；`geant4_run.py` 從 study spec 的觀測量宣告寫入執行用的 spec。
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
| 幾何樹 | 由 `G4PhysicalVolumeStore`（依建立順序的平面清單）與各體積的母邏輯體積重建樹；每個放置：名稱、copy number、solid 類型與參數、材料（Geant4 解析後的組成與密度）、轉換矩陣、母體、附加的 field manager 與參數；數值以 Python `float.hex()` 的格式（例如 `0x1.0000000000000p+0`）寫出；C 的 `%a` 輸出不同（`0x1p+0`），所以 `SimProbe.hh` 自帶格式器，並以測試向量和 Python 核對；replica 與 parameterised 體積記錄參數化描述 |
| `tree-v1` 雜湊 | 目標雜湊 = 目標放置的子樹的 JSON（鍵排序、無空白）的 sha256；`tree_sha256` 以同樣規則對整棵樹計算。內容只含物理：solid 類型與參數、材料組成與密度、相對母體的轉換、附加的場；**不含**體積名稱與 copy number。同一母體的子體依正規順序排列（依轉換的平移、再依 solid 參數、再依材料，全部以 hex 字串比較），不依建立順序；平移、solid 與材料完全相同時依 copy number 排序並註明。名稱與 copy number 另計 `naming_sha256`。這讓 setup-matched 能比對不同程式建立的同一配置，也讓任務 C 能快取相同的設計 |
| GDML | plugin 的建置關閉 GDML；使用者建置有 GDML 時可附 `gdml_sha256`，非必要 |
| EM 參數 | `G4EmParameters::StreamInfo(os)` 全文加上解析出的欄位；不用 `Dump()` |
| cut | 逐 material-cuts couple：材料、region、range cut、各粒子的能量閾值 |
| 強子模型 | 逐 process、逐模型，以 `GetHadronicInteractionList()` 與 `GetMinEnergy(mat, elm)`、`GetMaxEnergy(mat, elm)` 查詢能量範圍；重疊區間標示為隨機選擇。**不得**呼叫 `G4EnergyRangeManager::GetHadronicInteraction` 或 `ChooseHadronicInteraction`（區間重疊時它們會呼叫 `G4UniformRand`） |
| 亂數 | 探針不得抽取任何亂數（否則違反 §3 第 13 條）；測試以探針前後的亂數引擎狀態相同來確認 |
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
- `geant4_run.py` 的 `validate_spec()` 保持不變。

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

- [ ] 回歸檢查：J14 的既有 spec 在同一主機上產生和 A2 前逐位元相同的 CSV；探針前後的亂數引擎狀態相同（閘門 G-A2）。
- [ ] `SimHash.hh` 的 H 與 `core/simulation/seeds.py` 在測試向量上相同；`SimProbe.hh` 的 hex 格式和 Python `float.hex()` 相同。
- [ ] A2.9 的兩項測試通過；`per-event` 下 `GeneratePrimaries` 若抽亂數（測試用的隨機 gun），事件內容仍不受工作切法影響。
- [ ] `tree-v1` 不受命名影響：同一幾何以不同的體積名稱與建立順序建立兩次，`tree_sha256` 與目標雜湊相同，`naming_sha256` 不同；改變任一物理量（厚度、材料、位置）時雜湊改變。
- [ ] effective config 依內容雜湊只存一次；兩個相同設定的 run 引用同一個檔案。
- [ ] 為回歸檢查在 E2 重跑的 J14 spec（全部 18 個，仍為 `stream`）的新 run record 都有 effective config，且 `tree-v1` 與 `spec-v1` 的判定相同；故意製造的不一致被抓到；`recorded: false` 的 run 不能升級。已提交的 J14 紀錄維持 A1 的版本，不在 A2 重產。
- [ ] 薄層規則從 effective config 取得最小厚度，對 J14 的結論和 A1 相同。
- [ ] 研究層的正式程式不讀 CSV 欄名（測試確認）。
- [ ] 事件權重 ≠ 1 時 exit 2。
- [ ] J14 的離線重播仍符合 §4.3。
- [ ] VALIDATION GEANT4-SUMMARY；CHANGELOG；release manifest。

---

## 7. 契約與版本

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

## 8. 每個階段結束時的檢查

任務 B、C 的每個階段也執行這些檢查。

- `run_all_checks.py`（含 CI lock 環境）
- `check_layering.py`、`check_relocation.py`、`check_ownership.py`、`check_packaging.py`
- `measure_entrypoints.py`（quick load ≤ 25,600 bytes）
- `reference_inventory.py --check`、`capability_map.py --check`、`check_routing_static.py`
- 每份 study record 都通過 `validate.py --strict` 與 `dependencies.py`
- `tests.adapters.test_geant4` 離線與 live（`HEP_GEANT4_LIVE_TEST=1`）
- `tests/examples/test_geant4_thin_silicon.py`（重播的判定符合 §4.3）
- `python3 -m unittest discover -s tests/contracts -t .`（整體執行）
- `tools/scifix_advisories.py check`（A1）
- 由沒參與撰寫的 agent 執行一個新問題，並附通過條件
- 各階段的 Markdown 以 0.22.0 的 `review.py` 審查（`--lens-model design=<最強模型>`、`--filter-model`）；紀錄只是 advisory，依 O04/O14 不取代人工的 G5 確認
- VALIDATION 條目、CHANGELOG、release manifest

---

## 9. 不做與延後

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
| `change`、`threshold`、`order`、配對比較、search 角色、`values` | 移到 B2、C2 | 計畫原則 R1 |
| 加權累加與 biasing 規則 | 延後 | 第一個使用 biasing 的研究 |
| `physics_config_comparison` | 延後 | 需要比較物理設定的研究；屆時差異須經 `evidence_records` 取得 effective config，缺少時一律失敗 |
| 規則版本範圍、多個 Geant4 版本的探針 | 延後 | 支援第二個 Geant4 版本（B2 的 regression 類別會先用到） |
| benchmark registry | 延後 | 由契約表與 enum 一致性測試取代 |
| `inspect` 與 Linux 環境 | 延後 | 需要在 CVMFS 或 LCG 上執行 |
| ReferenceMaterial 契約 | 延後 | 第一個非平板幾何的 reference benchmark |
| 一般化 `scoped_upgrade` | 延後 | 第二種研究類型需要升級 |
| J14 遷移到 `element_sim`、退役 `layered_sim` | 延後 | `element_sim` 能產生 J14 的全部觀測量（計畫 §8） |

---

## 10. 待決事項與殘餘風險

**待決事項**（編號見計畫 §7）：第 1 項（CV1 的歸類）、第 2 項（`core/` 模組的 steward）、第 3 項（`simulation` 屬性）、第 4 項（兩階段係數與 J14 偶然失去升級時的處理）、第 5 項（J14 重錄與 recorded 上限）、第 6 項（精確區間的切換門檻）、第 7 項（G5 的確認方式）。

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

## 11. 建議的執行步驟

每個階段開始時依計畫 §10.2 建立並確認該階段的 isolated worktree，所有步驟都在其中進行；合併後依計畫 §10.5 移除。

**A1**
1. 開始前檢查（§0）；套用 `prototype/phase1-core.patch`，補齊 A1.1–A1.3 缺少的部分。
2. 先修 D10（A1.12），之後一律以 `python3 -m unittest discover -s tests/contracts -t .` 整體執行。
3. A1.1 → A1.2 → A1.3（契約與 `dependencies.py`），加契約測試。
4. `core/simulation/seeds.py` 與 `summary.py`、schema、A1.5 的 Python 產生器；以 J14 的 5 個逐事件 CSV 離線產生 summary。
5. `core/stats/` 的三個模組（A1.6–A1.10），hep-detector 的腳本改為呼叫它們並改讀 summary；加 toy 測試（閘門、覆蓋率、MPV 偏差、偵測極限）與只 import `core` 的使用測試。
6. A1.4 的角色規則與 A1.11、A1.12 其餘項目（protocol、enum、`simulation` 屬性）。
7. 在 E2 live 重錄 J14 的掃描、variation 與負方向控制組（A1.13）；重產 J14 紀錄，跑 `--strict`。
8. A1.14：ledger、advisory、parent record、VALIDATION、CHANGELOG、release manifest；跑 §8 的檢查。

**A2（A1 合併後）**
1. `g4sim/SimHash.hh`、`SimSummary.hh` 與 ctest（不需 Geant4），以 `core/simulation/` 與 A1.5 的 Python 產生器作為 oracle。
2. `SimSeed.hh` 與 `run.seeding`；`SimProbe.hh` 與幾何樹、`tree-v1`。
3. `layered_sim` 整合：summary、effective config（含依內容雜湊存放）、column map、測試用傾印；確認 J14 的 CSV 逐位元不變。
4. 研究層改讀邊界產物（A2.6）；schema 關鍵字（A2.7）。
5. A2.8 的 adapter 變更項目；在 E2 跑 live 測試；A2.10 全部打勾；跑 §8 的檢查。

---

## 附錄 A：統計規格彙整

| 項目 | 規格 | 工作項 |
|---|---|---|
| 區塊 | K ≥ 16 個依事件編號的區塊，每塊 B 個事件；事先宣告 | A1.5、A1.6 |
| SE | batch means，sd(θ_b)/√K，t_{K−1} | A1.6 |
| 計數很少 | 任一區塊為 0 或總數 < 100：Clopper–Pearson、Garwood、條件二項；閘門以區間端點判定 | A1.6、A1.8 |
| MPV | 區塊直方圖三點內插的平均；偏差 toy 95 % 上界 ≤ tol/10；每次核對 | A1.7 |
| 分位數 | 直方圖內線性內插；分格 < tol/10；溢位時 incomplete（C2 加入 `values` 的經驗分位數） | A1.6 |
| 收斂閘門 | IUT；`relative` 或 `absolute`；se_diff；Welch ν；每點 se 目標 tol/(4√2)；通過需兩點都達標 | A1.8 |
| 兩階段 | f = F₀.₉₀(K−1, K_trial−1)；未達標 incomplete，不補跑；一對點約 19 % 不完整，n 個 run 全部達標約 0.9ⁿ | A1.9 |
| negative control | 觀測量位移；DL = tol + \|rel\| + t_{0.977}(ν)·se_rel；正負兩向；toy 門檻 0.977 − 3σ_MC | A1.10 |
| 種子 | H 的位元組定義；S = H(study_id, role, point_id)；工作種子 H(S, e, 0/1)；事件種子 H(S, i, 0/1) | A1.4、A2.2 |
| 證據相關性 | `evidence_overlap` | A1.11 |
| 重現 | 判定相同、數值相對差 ≤ 1e-9、接近門檻標記 | §4.3 |
| 版本欄位 | `summary_version`、`column_map_version`、`probe_version`、`evidence_overlap_version` | A1.5、A1.11、A2.4、A2.5 |

## 附錄 B：數值

計算程式：`gate_operating_characteristics.py`（需要 numpy 與 scipy，只作設計輔助）。

- F₀.₉₀(15,15) = 1.972；F₀.₉₅(15,15) = 2.403；F₀.₉₀(31,31) = 1.594。
- t₀.₉₅(30) = 1.697，t₀.₉₅(15) = 1.753，t₀.₉₇₅(15) = 2.131；m = 30 的失敗分位數 t_{1−0.05/30}(30) = 3.189。
- Welch ν（K = 16）：變異數比 1 時 30，2 時 27，4 時 22.1，10 時 18.0。
- 兩階段設計下 se_diff 的平均 ≈ 0.189 tol（目標 0.25 tol）；一對點至少一點未達標的機率 0.190。
- 偵測極限的檢定力（A1.10 的 caught 定義）在 0.977 附近（審查者的計算約 0.9785）。

## 附錄 C：基準核對值（`9f08796`）

| 項目 | 值 |
|---|---|
| `CONTRACTS_VERSION` | 3.5.0 |
| `GEANT4_UPGRADE_FROM` | 3.1.0（行 346） |
| J14 study record | contract 3.5.0，帶 `code_paths`、`code_tags` |
| J14 世界材料 | `G4_Galactic` |
| J14 `recorded/` | 2.6 MB；`events/` 5 個縮減 CSV（`event`、`primary_eloss_MeV`、`edep_Si_MeV`、`primary_fate`、`primary_end_process`）；`runs/` 18 個 run record（5 個有逐事件 CSV；13 個掃描、variation 與情境 run 只有 `summaries/` 的單值摘要） |
| J14 種子 | 未重錄的 5 個 run 的第一個種子為 1401 或 1402 |
| advisory | 最新 SFA-2026-037 |
| hep-detector | quick load 24,669 / 25,600 bytes；description 1,016 / 1,024 字元（`measure_entrypoints.py`）；`DetectorScriptCount` 21 |
| `GRADES` | `longitudinal-profile: "reference"`（行 92–94）；study spec 的 grade enum 為 reference、sanity、interface |
| `ext_computational_run.json` | 未宣告 `simulation`；J14 的 run record 已帶 `extension.simulation` |
| `core/stats` | steward hep-statistics；已有 `beta_ppf`、`clopper_pearson`；沒有 t、F 分位數與 Garwood |
| 分層規則 | adapter 只 import `core` 與 `contracts`（`tools/check_layering.py`） |
| `SUPPORTED_KEYWORDS` | 無 maxItems、maximum、exclusiveMaximum |
| `check_packaging.py` MAX_BYTES | 2 MiB |
| Geant4 建置 | `GEANT4_USE_GDML: OFF`；`layered_sim` MT 用 `G4RunManagerType::MTOnly` |
| 共享 stanza 點 5 | 寫「3.1.0 upgrade rule」（不改） |
| journey 表 | J1–J14 |
| 階段 1 原型 | 55 個測試通過；J14 7 份 study record 通過 `--strict`；D10 在乾淨的 main 上重現（5 個錯誤） |

## 附錄 D：出處

設計所參考的實驗與框架（ATLAS、CMS、ALICE、Key4hep、Allpix²、geant-val、Belle II）見架構 §14。Geant4 11.4.3 原始碼的相關檔案：`G4RunManager.cc`、`G4MTRunManager.cc`、`G4WorkerRunManager.cc`、`G4EmParameters.cc`、`G4ProductionCutsTable`、`G4HadronicProcess.hh`、`G4EnergyRangeManager`、`G4AccumulableManager`、`G4VAccumulable`、`G4PhysicalVolumeStore`、`G4LogicalVolume`、`G4NistMaterialBuilder.cc`、`G4PVPlacement`。

## 附錄 E：版本歷程

| 版本 | 內容 |
|---|---|
| 2026-10-21 前 | 三輪獨立審查、依 0.21.0 與 `9f08796` 的兩次核對、階段 1 原型 |
| 2026-10-22 | 語言分工、逐事件 ROOT 檔、任務拆分、整理為實作規格；參考實際實驗重新設計（`architecture.md`）；依新架構改寫 |
| 2026-10-23 | 獨立審查後修正（兩階段操作特性重算、H 的定義、caught 定義、`GeneratePrimaries` 開頭重設種子等）；依自動化設計重新審視（統計移到 `core/`） |
| **2026-10-23（本版）** | **依計畫（`plan.md`）重新整理：A1 回到最小的 sci-fix（`change`、`threshold`、`order`、配對比較、search 角色、`values` 移到 B2、C2）；契約版本改記 CV1；種子雜湊放在 `core/simulation/seeds.py`；節的編號與任務 B、C 一致（§2 前提與提供的介面、§8 檢查、§10 待決與風險）** |
| 2026-10-23 | 加入 isolated worktree 的執行規定：檔頭、§0 的第一步、§11 的開頭（計畫 §10） |
