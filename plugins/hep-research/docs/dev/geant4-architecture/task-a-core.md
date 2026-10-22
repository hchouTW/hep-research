# 任務 A：Geant4 研究流程的正確性修正與 C++ 計算核心

> 文件類型：實作規格（給執行的 agent 與審查者）。狀態：最終提案，待維護者核准
> 順序：**任務 A 先做**；任務 B（J15 最小磁譜儀，[`task-b-j15.md`](task-b-j15.md)）在任務 A 合併後才開始
> 基準：hep-research `main` 的 `9f08796`（0.23.0 加未發布的變更），contracts 3.5.0，adapter geant4 0.1.0，Geant4 11.4.3（commit `2ee379e6`）
> 日期：2026-10-22
> 語言：繁體中文原文；英文版 [`task-a-core.en.md`](task-a-core.en.md) 內容相同。兩者不一致時以中文為準，並同時修正英文
> 依據：三輪獨立審查（7 份報告）、依 0.21.0 的重新核對、依 `9f08796` 的第二次深度檢查與階段 1 原型（附錄 B）

---

## 0. 任務卡

**目標。** 修正 hep-research（0.20.0 起）Geant4 研究流程中會讓結果被錯誤標成 `validated-in-scope` 的缺陷，再把所有「把模擬輸出化為數字」的計算移到 C++，讓研究流程只透過資料（column map、探針輸出）認識模擬後端。

**兩個階段（依序，各自合併）：**

| 階段 | 內容 | 版本 | 對 J14 的影響 |
|---|---|---|---|
| 1 | sci-fix：修正 D1–D10（第 3 節），在現有 Python 中以最小變動完成 | contracts **C1**（minor） | 工作項 A1.1–A1.3 以離線重播重產；A1.4、A1.6 需在 E2 live 重錄一次 |
| 2 | C++ 計算核心：layered_sim 重構（spec/2、scorer 元件、探針、column map、逐事件 ROOT 檔）、新的 `simcore`（`simspec`、`simstat`）與 `simroot`；Python 改為介面與判斷層 | adapter **0.2.0**；contracts 不升版 | 同主機逐位元相同驗證後重錄一次 |

**不在範圍內：** J15 與其所需的場區、平面穿越 scorer、`simreco`、`verification` 等級、contracts C2（都在任務 B）。任務 A 只預留兩處介面給任務 B（A2.2 的 `field` 區塊、A2.9 的 `event_file_version`）。

**交付物：** 程式與測試變更、重產的 J14 紀錄、sci-fix ledger 條目與 advisory、VALIDATION 條目 GEANT4-CORRECTNESS（階段 1）與 GEANT4-CORE（階段 2）、CHANGELOG、release manifest。

**完成的定義：** A1.12 與 A2.12 的驗收清單全部打勾，第 10 節的檢查全部通過。

**開始前必做：**
1. 確認 `main` 是否已超過 `9f08796`。若是，讀新的 CHANGELOG，重做附錄 B.2 的核對（缺陷位置、`CONTRACTS_VERSION`、`GRADES`、advisory 編號、quick load、description 長度、journey 清單），並更新附錄 B（中英兩版）。
2. 讀 `docs/maintenance.md`：sci-fix 流程（階段 1）、adapter 變更流程（階段 2）、release 步驟。
3. 從 `prototype/phase1-core.patch` 開始階段 1；它實作了 A1.1、A1.2、A1.3 的前半與 A1.10 的 enum 修正，但早於本文件的規格（缺 `target_slabs`、`longitudinal-profile` 的目標雜湊比對、缺少維度的規則、`shower-maximum`、`dependencies.py` 的重新推導、隔離規則的 C1 閘控；閘控寫死 3.6.0）。

---

## 1. 名詞與記法

| 名詞 | 意義 |
|---|---|
| J14 | 既有的 journey：`examples/geant4-thin-silicon/`，薄矽層研究，唯一有 `validated-in-scope` 紀錄的 Geant4 範例 |
| J15 | 任務 B 的最小磁譜儀 |
| study record | 帶 `extension.study` 的 computational-run 紀錄；`label` 決定其 artifact label |
| `validated-in-scope` | 經 reference benchmark 驗證、且宣告範圍在 benchmark 範圍內時才可有的 label；由 `contracts/validate.py` 的 `_study_upgrade` 把關 |
| 等級（grade） | benchmark 的參考性質：`reference`、`sanity`、`interface`（任務 B 加 `verification`）；只有 reference 計入升級 |
| observable kind | study spec 中受控的觀測量種類（enum），如 `most-probable-value`、`stopping-power` |
| configuration | benchmark 目標的放置情形：`isolated` 或 `embedded`（A1.3） |
| C1、C2 | 合併時下一個未使用的 contracts minor（C1 屬任務 A；C2 屬任務 B）。不寫死版本號，3.3.0–3.5.0 已被其他變更使用 |
| E2 | 有 Geant4 11.4.3 建置的執行環境 |
| IUT | intersection-union test：全部觀測量都等價才通過 |
| DL | negative control 的偵測極限 |
| 子 run | 以 K = 16 個獨立 chunk 產生的樣本分割 |
| spec/1、spec/2 | `layered_sim` 的舊幾何格式（`layers`）與新格式（`elements`，A2.2） |
| sci-fix | `docs/maintenance.md` 中修正科學正確性缺陷的流程（ledger、advisory、parent record） |
| 章節記法 | 「A1.6」是本文件的工作項；「§8」是本文件的第 8 節；「B1.3」是任務 B 的工作項 |

**主要檔案（相對 `plugins/hep-research/`）：**

| 用途 | 路徑 |
|---|---|
| 契約 | `contracts/validate.py`、`contracts/dependencies.py`、`contracts/schema.py`、`contracts/schemas/ext_computational_run.json` |
| 研究層（hep-detector） | `skills/hep-detector/scripts/check_geant4_study.py`、`geant4_benchmarks.py`、`tracker_resolution.py`、`multiple_scattering.py`；`skills/hep-detector/assets/geant4-study-spec.schema.json`；`skills/hep-detector/references/geant4-study-protocol.md` |
| adapter | `adapters/geant4/adapter.json`；`adapters/geant4/assets/geant4_run.py`（`SIM_SOURCES` 行 63、`validate_spec()` 行 103、`cmd_scan` 行 435、`cmd_chunk` 行 491、`cmd_summarize` 行 525）、`geant4_build.py`、`geant4_verify.py`；`adapters/geant4/assets/layered_sim/`（`Detector.cc`、`Spec.cc`、`Actions.cc`、`Physics.cc`、`MiniJson.hh`、`spec.schema.json`、`output.schema.json`） |
| core | `core/status.py`、`core/trace.py`、`core/OWNERS.json`、`core/partition/engine.py`（`NON_ADDITIVE_TOKENS` 行 381） |
| 測試 | `tests/contracts/test_geant4_upgrade.py`、`test_simulated_dataset.py`、`test_schema_keywords.py`；`tests/adapters/test_geant4.py`；`tests/skills/test_cli_robustness.py` |
| 工具 | `tools/run_all_checks.py`、`check_layering.py`、`check_relocation.py`、`check_ownership.py`、`check_packaging.py`、`measure_entrypoints.py`、`reference_inventory.py`、`capability_map.py`、`check_routing_static.py`、`scifix_advisories.py` |

---

## 2. 硬性限制

違反任何一條都不能合併。

1. **分層。** skill 腳本與 adapter 只能 import `core` 與 `contracts`。新的共用模組放在 `core/`，並在 `core/OWNERS.json` 指定 steward。
2. **實驗名稱。** `skills/` 與 `contracts/` 中不得出現實驗名稱（含 ALICE；`check_layering.py`）。需要時用引用鍵。
3. **Python 只用標準函式庫**（Geant4 相關腳本的設計選擇）。不加 Python 綁定。
4. **C++ 依賴。** `simcore` 只用 C++17 標準函式庫與既有的 `MiniJson.hh`，不連結 Geant4。`layered_sim` 與 `simroot` 連結 Geant4；ROOT 檔由 Geant4 內附的 g4tools 讀寫，不需要安裝 ROOT。
5. **G5 授權邊界。** Python 只和獨立執行檔交換 JSON 與 CSV。程式依 Geant4 API 撰寫，不複製或改寫 Geant4 範例程式碼。
6. **狀態與退出碼**（`core/status.py`）：0 ok、1 負向判定（`refused`/`failed`）、2 無法使用的輸入（`rejected`）、3 `incomplete`。不得使用其他退出碼；「未定案」一律是 3，不是 1。
7. **execution trace。** 新的紀錄寫入者呼叫 `trace.provenance()`；新的共用函式呼叫 `trace.tag()`。
8. **大小與路徑。** `check_packaging.py`：單檔 ≤ 2 MiB，掃描所有文字檔；寫出的路徑經 `tilde()`。plugin README 的大小聲明需在實際值的 10 % 以內。
9. **入口預算。** hep-detector quick load ≤ 25,600 bytes（目前 24,669）；description ≤ 1,024 字元（目前 1,018）。本任務不修改 `skills/hep-detector/SKILL.md` 與 description。
10. **流程。** 階段 1 依 sci-fix 流程；階段 2 依 adapter 變更流程；每個階段都依 release 步驟。只在分支 `worktree-geant4-architecture` 工作；未經維護者核准，不推送到 `main`、不開 pull request。
11. **契約版本。** 新規則以 `strict or _at_least(contract_version, C1)` 閘控，不設 warning 分支；版本號在合併時才決定。

---

## 3. 背景：已確認的缺陷

都已對照 `9f08796` 的原始碼確認（行號為該版本）。

| # | 缺陷 | 位置 | 後果 | 工作項 |
|---|---|---|---|---|
| D1 | 範圍檢查不比對觀測量 | `validate.py` `_scope_inside()`（行 349 起）；`check_geant4_study.py` `scope_within()`（行 482–493，迴圈中跳過 observable，且忽略純量） | 用 MPV benchmark 通過的研究可以把其他觀測量標成 `validated-in-scope`；宣告範圍缺少某個維度時，該維度不受限制 | A1.2 |
| D2 | benchmark 的等級由紀錄自己宣告 | `_study_upgrade`（行 395；篩選在行 419）讀紀錄內的 `grade` | 任何產生端寫 `"grade": "reference"` 就能升級 | A1.1 |
| D3 | negative control 在不同單位間比較、只測單向 | `geant4_benchmarks.py` 行 678 的 `at_limit` | 「位於偵測極限」在觀測量上未被證明 | A1.4 |
| D4 | 收斂閘門無等價檢定 | `check_geant4_study.py` `convergence()`（判定在行 359） | 真實差值等於容許值時約 50 % 通過 | A1.5 |
| D5 | MPV 的 SE 用 bootstrap | `geant4_benchmarks.py` 行 369 對 argmax 型的 `mpv()` 做 bootstrap | 變異數估計不一致；J14 的偵測極限建立其上 | A1.6 |
| D6 | 停止規則未明文禁止依結果加跑 | protocol 第 4 節 | optional stopping 偏差 | A1.10 |
| D7 | 證據相關性未揭露 | J14 的 nominal run 同時供閘門、統計目標、benchmark、variation 使用 | 被當作獨立證據 | A1.9 |
| D8 | study spec 的 benchmark enum 缺 `shower-containment` 與 `longitudinal-profile` | `geant4-study-spec.schema.json`；`GRADES` 有 9 個、enum 有 7 個 | 一致性缺口（執行時沒有作用：目前沒有程式以 schema 驗證 study spec，spec 中的 `grade` 也不被讀取） | A1.10 |
| D9 | 研究層和 layered_sim 的資料格式綁死 | `derived()` 讀 `geometry.layers`；`summarize` 與 benchmark 讀固定欄名 | 其他後端無法進入閘門與 benchmark | A2.4、A2.7 |
| D10 | 測試順序相依 | `test_geant4_upgrade` 的 `tearDownModule` 刪除共用的 J14 重播目錄，`test_simulated_dataset` 的 5 個測試因此出錯；單獨執行時通過 | 錯誤依執行順序而定 | A1.10 |

---

## 4. 設計原則

1. **正確性先於擴充。** 階段 1 合併前，不合併任何新功能。
2. **研究核心只認資料。** 規則、閘門、benchmark 經 column map 與探針輸出讀取，不讀後端專屬的欄名或 UI 指令字串。
3. **相信實際狀態，宣告只作為退路。**
4. **證據的停止規則與格點事先宣告。** 加跑、加密、重做控制組都不得依閘門或 benchmark 的結果決定。
5. **先找現有實作。** plugin 已有的方法一律重用；oracle 不得 import 被測模組。
6. **最小變動。**
7. **遵守既有規則**（第 2 節）。
8. **後端自我描述。** layered_sim 在執行時輸出自己的 column map 與實際生效的設定。
9. **驗證等級依參考的性質決定。** 參考值若是輸入的精確推論（解析螺旋、運動學、最小平方代數），屬於 verification，不能用來升級；若是 Geant4 所近似的物理模型（Bethe、Landau–Vavilov、Highland、簇射剖面）或已發表的量測，才可能是 reference 或 sanity。
10. **可升級的事實由契約認定。** 等級、kind、configuration 都不得由紀錄自行宣告。
11. **語言分工。** 把模擬輸出化為數字的計算（逐事件與逐 run 的縮減、估計量與其 SE、擬合）在 C++；由物理輸入算出參考值的公式、門檻比較與判定、紀錄與 provenance、契約在 Python。同一個量只有一份正式實作；另一種語言的實作只能出現在測試中作為 oracle。

---

## 5. 目標架構

| 層 | 語言 | 內容 |
|---|---|---|
| 計算核心 | C++ | `layered_sim`（連結 Geant4）：模擬、scorer、探針、column map、逐事件 ROOT 檔。`simroot`（只連結 Geant4 的 analysis 函式庫）：讀 ROOT 檔、轉成 CSV、內容雜湊。`simcore`（C++17 標準函式庫，不連結 Geant4）：`simspec`（spec/1 → spec/2）、`simstat`（觀測量、MPV 與子 run、bootstrap、收斂差值與其 SE、能量平衡殘差）；任務 B 加 `simreco` |
| 介面 | Python | `adapters/geant4/assets/*.py`：命令列、建置、執行 C++ 執行檔、spec 的 schema 與跨欄位驗證、紀錄寫出（含 `trace.provenance()`）、simulated 表格 |
| 判斷與參考 | Python | hep-detector：規則、獨立的參考公式（Bethe、Δp、Highland、gamma 剖面、PSTAR）、閘門與 benchmark 的判定、label；和 C++ 的計算互為獨立實作 |
| 契約 | Python | `contracts/`（全 plugin 共用） |

C++ 與 Python 只以獨立執行檔交換 JSON/CSV，不用 Python 綁定。所以 Python 端只用標準函式庫、不需編譯，G5 的邊界文字不變。`simcore` 不連結 Geant4，可在沒有 Geant4 的 CI 中建置與測試。詳細的逐事件資訊寫成 ROOT 檔（A2.9）；Python 與 `simcore` 都不直接讀 ROOT，而是經 `simroot`。

```
hep-detector（判斷與參考，Python）
  check_geant4_study.py     spec / summarize / run / variations / label；規則與閘門判定；數值讀自 simstat 的輸出
                            ＋ 經 core 的雙格式幾何存取器（spec/1、spec/2）
  geant4_benchmarks.py      參考公式與比較；Geant4 端的統計量讀自 simstat；輸出 configuration 與 target_geometry_sha256
  tracker_resolution.py、multiple_scattering.py（既有；作為獨立參考）
        │  只讀檔；import 只限 core、contracts
        ▼
core
  geometry/layered.py       （階段 2）雙格式幾何存取器（steward：hep-detector）
  trace.py                  （既有）trace.provenance()、trace.tag()
contracts（Python，全 plugin 共用）
  validate.py               （階段 1，C1）範圍比對 observable kind；benchmark 對照表（名稱 → 等級、kind）；隔離規則
                            （既有）simulated dataset-record（3.2.0）、execution trace（3.5.0）
  schema.py                 （階段 2）加 maxItems、maximum、exclusiveMaximum（不升版）
  computational-run（既有；extension.study 為自由格式區塊；C1 把 extension.simulation 加為選用的自由格式屬性）
        ▲
        │  產生檔案（JSON、CSV；ROOT 檔只經 simroot 讀取）
adapters/geant4（紀錄一律 unvalidated）
  Python 介面
    geant4_build.py         build / check；建置 layered_sim、simroot 與 simcore
    geant4_run.py           run / scan / chunk / summarize / reduce / oracle
    geant4_verify.py        overlaps / budget / balance / mirror / datapaths（讀雙格式；數值來自 simstat）
  C++ 計算核心
    layered_sim             連結 Geant4；只認 spec/2；scorer 元件；探針；column map（layered_sim.output/2）；
                            逐事件 ROOT 檔（G4AnalysisManager、g4tools；layered_sim.events/1）；（0.21.0 既有）混合材料
    simroot                 只連結 Geant4 的 analysis 函式庫；ROOT 檔的 info / dump（→ CSV）/ hash
    simcore                 不連結 Geant4（C++17 標準函式庫）
      simspec               spec/1 → spec/2 轉換（沿用舊幾何的浮點運算）
      simstat               觀測量與統計量
        │
        ▼
hep-computing（run_workflow.py、local_partition.py）
```

---

## 6. 階段 1：修正缺陷（contracts C1，sci-fix）

在現有 Python 中以最小變動完成。A1.5–A1.9 的估計量在階段 2 移到 `simstat`，屆時這裡的 Python 實作只留在 `tests/` 作為 oracle（A2.8）。

### A1.1 契約側的 benchmark 對照表（D2）

**修改：** `contracts/validate.py`（新增常數表；`_study_upgrade` 改從表取得等級與 kind，不再讀紀錄內的宣告）；`geant4_benchmarks.py`（`GRADES` 保留給工具，加一致性測試）。

| benchmark | 等級 | 支持的 observable kind |
|---|---|---|
| `stopping-power` | reference | `stopping-power` |
| `range` | reference | `range` |
| `thin-layer-mpv` | reference | `most-probable-value` |
| `thin-layer-width` | sanity | `thin-layer-width` |
| `multiple-scattering` | sanity | — |
| `em-shower-shape` | sanity | — |
| `shower-containment` | sanity | — |
| `longitudinal-profile` | reference | `shower-maximum`（新增的 kind；它只量 t_max） |
| `published-data` | interface | — |

**規則：**
- 表中等級和目前的 `GRADES` 相同（9 個名稱；原型已加測試確認）。
- 紀錄的 `grade` 和表不一致，或 benchmark 名稱不在表中：判為 error。適用於所有帶 Geant4 study 區塊的紀錄，不只升級的紀錄。
- benchmark 支持的 kind 只以契約表為準；工具輸出的 kind 只供閱讀。
- J14 的判定不變，但所有 study 與 benchmark 檔案的內容會改變（新欄位；`code_paths` 多出 `contracts/validate.py` 等）。

### A1.2 範圍檢查（D1）

**修改：** `contracts/validate.py`（唯一實作，匯出）；`check_geant4_study.py`（匯入使用，刪除 `scope_within()`；`label` 寫 `declared_scope.observable_kind`）；study spec schema。

**規則：**
- 比對受控的 `observable.kind`，不比自由文字（自由文字保留供人閱讀）。
- `label` 把 study spec 的 `observable.kind` 複製到 `declared_scope.observable_kind`；它必須在被計入 benchmark 的支持 kind 之內。study spec 的 `validation_plan.scope` 是 `additionalProperties: false`，所以 schema 也要加入 `observable_kind`。
- 比對維度：observable kind、particle、material、energy、thickness；純量視為 `[v, v]`。
- benchmark 範圍中有的維度，宣告範圍都必須有；缺少的維度視為超出範圍。
- `longitudinal-profile` 的範圍只有 particle 與 energy（工具對它輸出 null 的 material 與 thickness）。比對時用這兩維、kind，以及**目標幾何雜湊**：宣告範圍必須帶有和 benchmark 相同的 `target_geometry_sha256`（A1.3）。只比 particle 與 energy 會讓任何材料堆疊都能借用已發表堆疊的結果升級（原型驗證過這個漏洞）。能量為純量，所以宣告的能量範圍必須等於該值。
- 閘控：`strict or _at_least(contract_version, C1)`，無 warning 分支。contract 3.5.0 以下的紀錄只在 `--strict` 下受新規則約束，且只有帶 `validated-in-scope` 的紀錄會失敗（`_study_upgrade` 對其他紀錄提早返回）。

### A1.3 configuration 與隔離規則

**修改：** `geant4_benchmarks.py`（輸出）；`contracts/validate.py`（規則）；`contracts/dependencies.py`（重新推導）。

**規則：**
- `geant4_benchmarks.py` 為每個 benchmark 結果輸出 `configuration`、`target_geometry_sha256` 與 `configuration_basis`，從 benchmark 設定的 `run_record` 所指 run record 的幾何推導，不接受使用者輸入。計入升級的 benchmark 必須有 `run_record`（目前是選用）。
- **目標：** benchmark 設定宣告 `target_slabs`（目標包含的 slab 名稱，含吸收層）。單層 benchmark 預設為被量測的那一片。`longitudinal-profile` 必須明列整個取樣堆疊：它的 `layers` 只列讀出欄位、不含吸收層，無法推導；照字面推導時真實的取樣堆疊一律是 `embedded`。
- **`isolated`** 的條件：沒有場、世界是真空（`G4_Galactic`；J14 符合）、世界以外的每個放置都屬於 `target_slabs`；否則為 `embedded`。spec/1 沒有場的欄位，視為無場；spec/2 以明確的 `field` 區塊判定，階段 2 起再以探針記錄的實際場核對。
- **`target_geometry_sha256`：** 目標的正規化清單（依序的 slab、厚度、橫向尺寸、材料組成與密度；數值以 `repr`；重複放置逐一列出）的 sha256；spec/1 與 spec/2 的結果相同。
- **契約規則（C1，閘控同 A1.2）：** 每個被計入的 benchmark 都必須是 `configuration == "isolated"`；缺少或為 `embedded` 都是 error。`dependencies.py` **必須**從 `evidence_records` 中的 run record 重新推導 configuration 與雜湊，並和紀錄比對（否則 configuration 和等級一樣是自行宣告）。
- 原型確認：configuration 可從既有的 recorded run record 推導，所以 J14 只需離線重播。
- **殘餘限制（寫入 protocol）：** J14 的 recorded CSV 是縮減版，其雜湊對不上 run record 的 `output_hashes`；configuration 描述的是設定檔**指名**的 run record，而不是被證明產生該 CSV 的 run record。negative control run 的幾何不另外檢查。

### A1.4 negative control（D3）

**修改：** `geant4_benchmarks.py`。

- 判定量為觀測量上的實際位移：`shift = (control − nominal) / reference`，SE 由兩個 run 合成。
- 位於偵測極限：`caught` 且 `|shift| ≤ 1.1 × DL`。
- 兩個方向都要注入；否則把宣稱限縮為單向，寫入 `scope.detection_limit_sign`。
- J14 現有控制組只注入 +密度。先把兩個 J14 宣稱限縮為單向（`detection_limit_sign: "+"`）；依原型兩者已滿足 `|shift| ≤ 1.1 × DL`（MPV 0.0856 對 DL 0.0827；stopping power 0.0381 對 0.0378）。live 重錄時補上負向控制組。

### A1.5 收斂閘門與回報（D4）

**修改：** `check_geant4_study.py` 的 `convergence()` 與 `cmd_run`。

「所有觀測量都等價才通過」是 intersection-union test：

```
通過：|diff| + q_pass · se ≤ tol
失敗：|diff| − q_fail · se > tol
其他：unresolved
```

| 項目 | 規格 |
|---|---|
| se | **差值**的 SE |
| q_pass | se 來自子 run：t₀.₉₅(ν)；來自大樣本 bootstrap：z₀.₉₅ = 1.645 |
| q_fail | 同上，但分位數為 1 − α/m，m 為（參數 × 觀測量）組數 |
| ν | 兩個各有 K = 16 子 run 的估計之差，以 Welch 近似，約 30（t₀.₉₅(30) = 1.697）；單一估計時 15 |
| 事件數 | 事先設定使差值的 se ≤ tol/4 |

操作特性（se = tol/4 視為已知、α = 0.05）：

| 真實差值 | 通過 | 失敗（m = 1） | 失敗（m = 6） | 失敗（m = 30） |
|---|---|---|---|---|
| 0 | 0.981 | 0.000 | 0.000 | 0.000 |
| tol/2 | 0.639 | 0.000 | 0.000 | 0.000 |
| tol | 0.050 | 0.050 | 0.008 | 0.002 |
| 2 tol | 0.000 | 0.991 | 0.946 | 0.857 |

真實差值為 tol/2 時通過的檢定力只有約 64 %；這是事先設定 se ≤ tol/4 的代價，在文件中寫明。

**回報：** unresolved 以執行狀態 `incomplete`（exit 3）回報，artifact label 保持 `unvalidated`；只有 fail 是 `failed`（exit 1）。目前 `convergence()` 與 `cmd_run` 把非 pass 一律當 `failed`，需要修改。

### A1.6 MPV 的估計量與 SE（D5）

- nominal 樣本改以 K = 16 個 chunk 產生（以手動建立的 partition manifest 呼叫 `geant4_run.py chunk`），總事件數仍為 N。這**不是**切開既有的單一 nominal run：每個 chunk 都是新事件，所以 J14 的 nominal 需要 live 重錄。全樣本以各 chunk 的 CSV 串接（`concat`）得到。
- 回報值改為 **16 個子 run MPV 的平均**；分格寬度固定並寫入 spec；SE = sd(子 run MPV) / √16；分位數用 t₁₅。
- 全樣本 MPV 只作診斷，和平均值的差寫入紀錄。理由：直方圖眾數估計量不依 1/√N 縮放，sd/√K 只對「子 run MPV 的平均」成立；審查者的 toy 顯示對全樣本 MPV 會低估 1.1 到 2.3 倍（視分格寬度）。
- bootstrap 不再用於 MPV。
- 子 run 的 MPV 從各 chunk 的 CSV 分別計算，不得經 partition 的合併規則（`mpv` 不在 `NON_ADDITIVE_TOKENS` 中，若作為 chunk 的數值鍵會被靜默加總）。

### A1.7 兩階段事件數

- `N = ceil(N_trial · (SE_trial / target)² · f)`。
- 「未達標」以證據 run 的**估計** SE 判定。試探 run 與證據 run 的 SE 都來自 K = 16 子 run 時，達標機率為 P(F₁₅,₁₅ ≤ f)：f = 1.2 只有 0.636，所以取 **f = F₀.₉₀(15,15) ≈ 1.97**（達標機率 90 %）。
- SE 來自大樣本 bootstrap 時，f = 1.2。
- 證據 run 未達標時判為 unresolved（`incomplete`，exit 3），**不得補跑**。

### A1.8 種子

- `H(study_id, role, point_id, k)` 映射為 [1, 2³¹) 內的**一個**整數（C++ 以 double 讀種子，超過 2⁵³ 會失去精度）。角色：trial、nominal、scan、control、variation、calibration；k 是 chunk 索引；正負兩個方向的控制組使用不同的 point_id。
- chunk：manifest 由研究手動建立，每個 chunk 的種子為 H；layered_sim 的第二個種子沿用 `cmd_chunk` 的 `start + 1`。不使用 `make_manifest` 的 `seed × 100003 + k`。
- scan：各點的種子改用 H，不再用 `cmd_scan` 的 `[s0, s1 + k]`。
- 檢查：`validate_manifest` 只拒絕同一 manifest 內的重複種子；`check_geant4_study.py` 另外檢查同一研究的所有 run record 中種子對不重複。

### A1.9 bootstrap、證據相關性（D7）與 execution trace

- **bootstrap**（用於平均、分位數、比例）：Poisson(1) 權重由 64 位元計數器雜湊（study_seed、run_id、chunk_id、event_id、replica_id）產生，以反 CDF 轉換；R ≥ 400；`summarize` 檢查事件鍵是否重複。
- **證據相關性：** `extension.study.evidence_overlap` 列出被多個判定共用的 run，附 `evidence_overlap_version`。
- **trace tag**（小寫連字號）：範圍比對 `geant4-scope-kind`、configuration 推導 `geant4-configuration`、IUT 閘門 `geant4-convergence-iut`、子 run MPV `geant4-mpv-subrun`、種子雜湊 `geant4-seed-hash`。advisory 掃描目前不讀 tag，但之後可用來判斷受影響的程式是否執行過。`check_geant4_study.py` 改 import `contracts.validate` 後，`code_paths` 會多出 `contracts/validate.py` 等，這是預期的變化。階段 2 起，子 run MPV 與 bootstrap 在 `simstat` 中執行，tag 由呼叫它的 Python 介面記錄。

### A1.10 其他修正

- study spec 的 benchmark enum 補上 `shower-containment` 與 `longitudinal-profile`（D8）；observable kind enum 加入 `shower-maximum`；`validation_plan.scope` 加入 `observable_kind`。
- `ext_computational_run.json` 加入選用的自由格式屬性 `simulation`（需 schema 擁有者 hep-computing 同意），讓 advisory 可以用它作為鍵。
- D10：`test_geant4_upgrade` 與 `test_simulated_dataset` 不再共用會被刪除的暫存目錄（各自建立重播，或改為 package 層級的 fixture）。
- protocol 第 4 節（D6）：停止規則、掃描格點、unresolved 的處理方式必須在第一個證據 run 之前寫入 study spec。

### A1.11 版本與 sci-fix 流程

- **版本：contracts C1（minor）。** 現有閘控都設在 x.y.0；新增閘控規則族的先例（2.4.0、2.6.0、2.8.0、3.1.0、3.2.0）都是 minor。
- **ledger：** 每個缺陷一筆，`changelog` 為結構化物件（`{"kind": "unreleased", ...}`）。

| 缺陷 | ledger 條目 | 等級 | 理由 |
|---|---|---|---|
| D1 | scope-kind | S2 | 改變判定 |
| D2 | grade-table | S2 | 改變判定 |
| D3 | control-shift | S2 | 改變判定 |
| D4 | gate-IUT | S2 | 改變判定 |
| D5 | MPV-subrun | **S1** | 改變回報的數值（MPV 與其 SE） |
| D6 | stopping-rule | S3 | 只是指引 |

- **證據：** S2 至少 C2 層級；S1 需 C3 與 D2 層級（`docs/maintenance.md` 的證據層級，不是本文的缺陷 D2）。證據測試經 `validate.py` 與 `check_geant4_study.py` 的命令列執行，才能在 parent commit 上執行；無法在 parent 上執行的寫入 `gaps`。
- **advisory：** `scifix_advisories.py check` 要求 advisory 的等級和它列出的每個 ledger 條目相同，所以 S1 與 S2 各發一份（編號取合併時下一個未使用者；目前為 SFA-2026-038 與 -039）。
  - 鍵：`artifact_types: [computational-run]`、`extension_keys: ["study", "evidence_records"]`（兩者都是選用欄位，可以區分）。
  - 範圍：introduced 0.20.0，附 `database_specific.introduced_basis`（0.19.0 已有 `contracts/validate.py`）；受影響版本 0.20.0–0.23.x 與未發布版本。
  - simulated dataset-record 無法用鍵區分（`status`、`observable` 是必填欄位，掃描只看鍵是否存在）。remedy 要求持有者對每個 simulated 表格執行 `contracts/dependencies.py`，從輸入鏈找出受影響的 study record。以值比對的掃描是另一項工具變更。
- 0.20.0 以後產生、帶 `validated-in-scope` 的 study record 缺少 kind 與 configuration，在 `--strict` 下會失敗；advisory 說明處理方式（以新版本重產）。

### A1.12 階段 1 驗收

- [ ] kind 不符、宣告缺少維度、等級和契約表不符、configuration 缺少或為 `embedded`、`target_geometry_sha256` 不符的紀錄，在 `--strict` 與 C1 下被拒；`dependencies.py` 重新推導的 configuration 與紀錄不符時被拒；純量範圍正確比對。
- [ ] 重產的 J14 study record（含 kind、configuration）通過 `validate.py --strict` 與 `dependencies.py`。
- [ ] negative control 以觀測量位移判定，正負兩個方向都有測試。
- [ ] 閘門 toy 測試（每格 10⁴ 次）：真實差值 = tol 時通過率 ≤ 0.05 + 3σ_MC；真實差值 = 0 時通過率 ≥ 0.97；失敗率（m = 1、6、30）和 A1.5 的表一致到 3σ_MC 內；unresolved 以 exit 3 回報。
- [ ] MPV：在 J14 的同一個 N 下，比較子 run 平均與全樣本 MPV 的差值，以及子 run SE 與 bootstrap SE；結果記錄在 VALIDATION。
- [ ] A1.1–A1.3 的 J14 重產以離線重播完成（原型已示範）；A1.4 的負向控制組與 A1.6 的子 run 以 live 重錄完成。
- [ ] D10 修正後，`python3 -m unittest discover -s tests/contracts -t .` 沒有錯誤。
- [ ] J14 在 E2 重錄後，每個 reference benchmark 的控制組仍在 `|shift| ≤ 1.1 × DL` 內被抓到；若不成立，以新的偵測極限重新設計控制組並記錄原因。
- [ ] 六筆 ledger 條目、兩份 advisory（S1、S2）通過 `scifix_advisories.py check`、parent record 齊全；live Geant4 證據以 release-gate 執行記錄；VALIDATION 條目 GEANT4-CORRECTNESS；CHANGELOG；release manifest。

---

## 7. 階段 2：C++ 計算核心（adapter 0.2.0）

### A2.1 範圍

所有會影響 J14 的 C++ 工作都在這一階段：spec/2 讀取、scorer 元件化、探針、column map、逐事件 ROOT 檔與 `simroot`，以及把觀測量與統計量的計算從 Python 移到 `simcore`。場區與平面穿越在任務 B 加入（混合材料 0.21.0 已有）。

### A2.2 spec/2 的座標與格式

- 座標以世界中心為原點，堆疊軸為 x，單位 mm。
- `at_mm` 是元件**前表面**的 x 座標（世界座標）。子體的 `at_mm` 也是世界座標，必須落在母體範圍內。
- 巢狀只允許一層。
- schema 只用 `contracts/schema.py` 支援的關鍵字（含本階段新增的三個，A2.5）。
- gun 欄位：`energy_MeV`（任務 B 加 `ekin_per_nucleon_MeV`）。
- **為任務 B 預留：** schema 定義選用的 `field` 區塊；本階段的 `layered_sim` 遇到非空的 `field` 時以 `rejected`（exit 2）拒絕。A1.3 已把有 `field` 的幾何判為 `embedded`。

### A2.3 spec/1 → spec/2 轉換與逐位元相同

spec/1 一律先經 C++ 的 `simspec convert` 轉成 spec/2；`layered_sim` 只讀 spec/2。轉換必須讓同主機上的模擬輸出逐位元相同：

| 因素 | 會改變事件？ | 轉換規則 |
|---|---|---|
| 材料建立 | **會**（混合材料以 `G4Material::AddMaterial` 依序加入成分；順序決定元素向量順序，模型依亂數抽選元素時依此順序） | 保留 `materials[]` 與 `components[]` 的順序，數值以 `%.17g` 輸出 |
| 放置位置 | **會**（差一個 ulp 就改變步長） | 在 C++ 中沿用舊 `Detector.cc` 的運算順序（`stack = Σ repeat × Σt`、`world = world_scale × stack` 或 `world.size_mm`、`x = −stack/2`、`center = x + t/2`、`x += t`），以 `%.17g` 輸出；新 `Detector.cc` 以 `at + t/2` 求中心 |
| `shift_mm ≠ 0` | **會** | `(x + t/2) + shift` 和 `(x + shift) + t/2` 不保證逐位元相同；只對 `shift = 0` 保證（J14 與 mirror 都是 0），其他情況做統計比對 |
| 粒子源位置 | **會** | `gun_world_fraction × world 長度`，以相同順序計算後寫入 |
| physics list 組成 | **會** | `G4StepLimiterPhysics` 只在 `step_limit_mm > 0`、`min_ekin_MeV > 0`（任務 B 起另加：有場時）加入 |
| 子體放置順序 | 低 | 保持原順序 |
| 材料與 region 建立順序 | 低（只影響 couple 編號） | 保持原順序 |
| 體積名稱、copy number | 不會（只影響輸出欄名） | 保持不變 |
| overlap 檢查 | 不會（使用獨立的 `G4QuickRand`） | — |
| 輸出欄位集合與順序 | 影響比對 | spec/1 轉換來的 spec 啟用舊 scorer 集合，順序和 `CsvColumns` 相同 |

**驗收：** 同一主機、同一 Geant4 build 上，階段 2 開始前的 layered_sim 與新版對 TestEm3、TestEm5 mirror 與 J14 spec 產生逐位元相同的 CSV（同種子、serial），且兩版每個放置的 hex-float 傾印（名稱、copy number、平移、母體）完全相同。跨主機只做統計比對；已提交的 J14 CSV 不作為逐位元參考。

### A2.4 hep-detector 的雙格式支援

J14 的已記錄紀錄必須永遠可以重播，所以 Python 永久能讀 spec/1 與 spec/2 的幾何事實（元件、厚度、材料；不計算位置）。

| 位置 | 變更 |
|---|---|
| run record | 記錄 `spec_sha256`（使用者給的 spec）與 `effective_spec_sha256`（C++ 執行的 spec/2） |
| `check_records` | 比對 study 中的 spec 和 run 的 `spec_sha256` |
| 幾何存取器（新模組 `core/geometry/layered.py`，steward hep-detector，登記於 `core/OWNERS.json`） | 從 `layers` 或 `elements` 取得元件清單、最小厚度、材料；`check_geant4_study.py`、`geant4_benchmarks.py`、`geant4_verify.py` 共用；以 J14 紀錄測試 |
| `derived()` | `min_thickness_mm` 經存取器計算；加測試確保 `G4R-THIN-FLUCT`、`G4R-THIN-CUT-SCAN` 在兩種格式下都觸發 |
| `cmd_summarize` | 讀 `simstat summarize` 的輸出，不在 Python 中計算統計量；粒子源能量從 run record 的 `extension.simulation.gun` 讀取 |
| `geant4_verify.py` | 體積計數（overlaps）與物質預算（budget）經存取器讀取；能量平衡的逐事件殘差由 `simstat balance` 計算，Python 只做判定 |
| study spec schema | `$comment` 改為接受 `layered_sim.spec/1` 或 `/2` |

### A2.5 schema 驗證

- 擴充 `contracts/schema.py`：`maxItems`、`maximum`、`exclusiveMaximum`（`SUPPORTED_KEYWORDS` 目前沒有；layered_sim 的 schema 已用到全部三個）。更新 `SUPPORTED_KEYWORDS`，並擴充 `tests/contracts/test_schema_keywords.py`，讓它也掃描 adapter 的 schema（現在只掃描 `contracts/schemas/*.json`）。contracts **不升版**：沒有契約 schema 使用新關鍵字。
- `geant4_run.py` 改用 `contracts.schema.validate()`。原 `validate_spec()`（行 103）中 schema 表達不了的跨欄位規則保留為 `cross_field_checks()`：混合材料的 components 與 z/a_g_mole 擇一、至少兩個成分、質量分率和為 1、成分只能引用 NIST 或先前定義的材料；slab 名稱重用時材料與厚度必須一致；world 的 scale 與 size 恰好擇一；`reference_list` 與 `em_constructor` 擇一；region 的 slab 名稱存在；禁用的 UI 指令；粒子源位置範圍。
- C++（`layered_sim`、`simspec`）只檢查執行所需的最低限度；schema 與跨欄位規則的判定在 Python。

### A2.6 探針（`Probe.hh`）

| 項目 | 規格 |
|---|---|
| 時機 | master 的 `BeginOfRunAction`；狀態為 `G4State_GeomClosed` 且 couple 數大於 0。否則寫入 `effective_config: {"recorded": false, "reason": ...}`，layered_sim 照常 exit 0（不用 `refused`：它在 `core/status.py` 中表示負向判定）。依 11.4.3 原始碼，這時物理表已建好；fake run（`/run/beamOn 0`）在 `BeginOfRunAction` 之前返回，探針不執行 |
| 頻率 | 每個 run 一次 |
| 執行緒 | 只在 master；輸出註明「workers assumed identical」 |
| EM 參數 | `G4EmParameters::StreamInfo(os)` 全文加上解析出的欄位；不用 `Dump()`（11.4.3 中每個行程只印一次） |
| cut | 逐 material-cuts couple：材料、region、range cut、各粒子的能量閾值 |
| 強子模型 | 逐 process、逐模型，以材料與元素查詢能量範圍；重疊區間標示為隨機選擇 |
| run manager | 型別、`seedOncePerCommunication`、`G4RUN_MANAGER_TYPE`；SubEvt 或非 0 的種子模式回報 gap |
| 其他 | `G4UserLimits`、biasing、資料集路徑與內容雜湊 |
| 路徑 | 經 `tilde()` 寫出 |
| 版本 | 11.4.x；附 `probe_version` |
| 輸出位置 | `extension.simulation.effective_config` |

- 規則與 variation 的模型指派優先讀探針，讀不到才退回宣告，並輸出 `source: probe | declared`；兩者都有而不一致時報錯。
- 測試觸發：加一個只在測試建置中存在的 UI 指令，在 `/run/initialize` 之後、第一次 `BeamOn` 之前呼叫探針，必須寫出 `recorded: false`。

### A2.7 column map

- 檔名 `column_map.json`，schema `layered_sim.output/2`，和 `output.schema.json` 一起放在 adapter。
- layered_sim 在每個 run 自動輸出，雜湊寫入 run record。
- 每個欄位包含語意名稱、實際欄名、單位、操作定義；附 `column_map_version`。
- 同時描述 CSV 的欄與 ROOT 檔各 ntuple 的欄（每個欄位標明 `file: csv | root` 與 `ntuple`）。
- 使用者自己的應用可以手寫同格式的對照檔；只允許宣告式運算（改名、單位換算、加總、篩選）。需要計算的轉換必須是另一個有紀錄的步驟。

### A2.8 `simcore`（C++ 計算核心）

| 項目 | 規格 |
|---|---|
| 位置 | `adapters/geant4/assets/simcore/`（CMake 專案；擁有者 hep-detector） |
| 依賴 | C++17 標準函式庫與既有的 `MiniJson.hh`；不連結 Geant4，不用第三方函式庫 |
| 執行檔 | `simspec`、`simstat`（任務 B 加 `simreco`） |
| 介面 | 輸入：spec、CSV、column map、參數 JSON（不讀 ROOT；需要時由 `simroot dump` 轉成 CSV）。輸出：一個 JSON 物件（stdout 或 `--out`），含 `status`、`program`（名稱、版本、編譯器）與結果 |
| 退出碼 | 0、1、2、3（第 2 節第 6 條） |
| 數值 | double；加總與順序無關（先排序或補償加總），結果不受執行緒與 chunk 順序影響；亂數只用計數器雜湊（SplitMix64），不用 `<random>` 的分布（各實作輸出不同） |
| 輸出精度 | 浮點以 `%.17g` 寫出 |

`simstat` 的子命令（取代原本在 Python 中的計算）：

| 子命令 | 內容 | 取代 |
|---|---|---|
| `summarize` | 逐 run 的觀測量：平均沉積、尾端比例、洩漏比例、MPV（固定分格寬度）、穿透主粒子的 E_in − E_exit；經 column map 讀欄位 | `check_geant4_study.py summarize` 的計算；`geant4_benchmarks.py` 中 Geant4 端的統計量 |
| `subrun` | 各 chunk CSV 的 MPV、其平均與 sd/√K | A1.6 的估計量 |
| `bootstrap` | Poisson(1) 計數器雜湊權重下的 SE（平均、分位數、比例）；同一事件的所有觀測量共用權重 | `bootstrap()` |
| `diff` | 兩個掃描點之間觀測量的差值與差值的 SE | `convergence()` 的數值部分；判定留在 Python |
| `balance` | 逐事件的能量平衡殘差 | `geant4_verify.py balance` 的數值部分 |

- **遷移與等價：** 階段 1 的 Python 估計量移到 `tests/`，只作為 oracle。等價測試以 J14 的 recorded CSV 比較 `simstat` 與 oracle：計數完全相同、MPV 選到相同分格、其他浮點相對差 ≤ 1e-12（加總順序不同所致）。
- **為什麼不用 Python 綁定：** 獨立執行檔讓 Python 端只用標準函式庫、不需編譯；輸出是有雜湊的檔案，直接進入 provenance；G5 的核准文字不必改。
- **trace：** `simcore` 在另一個行程執行，不會出現在 `code_paths`。呼叫它的 Python 介面在紀錄中寫入執行檔與原始碼的 sha256、版本與子命令，並以 `trace.tag()` 標記（例如 `geant4-simstat`）。

### A2.9 逐事件 ROOT 檔

模擬的詳細逐事件資訊寫成 ROOT 檔（使用者決定，2026-10-22）。逐事件 CSV 保留為摘要表：既有欄位、A2.3 的逐位元比對與 `simstat` 的輸入都不變。

| 項目 | 規格 |
|---|---|
| 寫出 | `layered_sim` 經 `G4AnalysisManager`（ROOT 輸出類型）寫出；底層是 Geant4 內附的 g4tools，不需安裝 ROOT，不新增建置依賴 |
| 設定 | spec/2 的 `output.event_file`：`level` 為 `none`（預設；J14 不變）、`summary`、`hits`（任務 B 加 `crossings`）；`compression`（預設 1）；`max_events_hits`（預設 100） |
| 檔案 | 每個 run（每個 chunk）一個檔；MT 下以 `SetNtupleMerging(true)` 由 master 合併成單一檔（11.4.3 中只有 ROOT 輸出支援 ntuple 合併）；路徑經 `tilde()` 寫入 run record |
| 結構 | 扁平 ntuple，只用純量欄（I、D、S），每列帶鍵（`event_id` 加 ntuple 自己的次鍵）；不用 vector 欄，ROOT 與 uproot 能直接讀成表格 |
| 列的順序 | MT 合併後的列順序取決於執行緒排程，不可依賴；讀取端一律先依鍵排序 |
| 寫出時機 | `EndOfEventAction` 填列；run 結束時寫檔並關閉。run 中斷時檔案不完整，run 判為 incomplete（exit 3），不寫入 `output_hashes` |
| 版本 | 結構記為 `layered_sim.events/1`，檔內帶 `event_file_version`；column map 允許增加 ntuple（任務 B 加 `crossings`，版本加一） |

ntuple（欄位的單位與操作定義寫在 column map）：

| ntuple | 層級 | 每列 | 欄位 |
|---|---|---|---|
| `run` | `summary` 起 | 每檔一列 | spec 與 column map 的 sha256、layered_sim 版本與原始碼雜湊、Geant4 版本、種子、chunk 索引、事件數、`event_file_version`、process 編號對照表 |
| `events` | `summary` 起 | 每事件一列 | `event_id`、主粒子 PDG 碼、動能、起點、方向；各子系統的總沉積；離開世界體積的能量；旗標 |
| `deposits` | `summary` 起 | 每事件 × 每個有沉積的體積一列 | `event_id`、`volume_id`、`copy`、總沉積、帶電粒子的沉積；沒有沉積的體積不寫 |
| `hits` | 只在 `hits` | 每個有沉積的步一列 | `event_id`、`track_id`、`parent_id`、PDG 碼、`volume_id`、`copy`、前後步點位置、時間、沉積、步長、process 編號 |

- `hits` 很大（量能器中一個 GeV 級簇射有上萬步），只用於小樣本：事件數超過 `max_events_hits` 時，spec 驗證以 `rejected`（exit 2）拒絕。
- **內容雜湊：** ROOT 檔的位元組含寫出時間等資訊，兩次相同的 run 也不會逐位元相同。run record 同時記錄檔案的 sha256（只用於完整性）與 `simroot hash` 的 `content_sha256`（用於比對與 provenance）；逐位元相同的要求只適用於 CSV 與 `content_sha256`。MT 下每個事件的種子由 master 預先產生，事件內容和執行緒無關，所以不同執行緒數的兩次 run 應有相同的 `content_sha256`。
- **一致性：** 每個量只由一個 scorer 計算一次，再分別寫入 CSV 與 ROOT 檔。
- **大小：** ROOT 檔不提交到 repo；run record 記錄路徑、檔案 sha256、`content_sha256`、各 ntuple 列數與檔案大小；測試需要的 ROOT 檔在 live 測試中產生。`summary` 層級壓縮前每事件約 120 B（`events`）加上每個有沉積的體積 28 B（`deposits`）。
- **G5：** Python 仍只和獨立執行檔交換 JSON 與 CSV，邊界文字不變；ROOT 檔只由連結 Geant4 的 `layered_sim` 與 `simroot` 經 Geant4 自身的 analysis 模組讀寫。VALIDATION 條目註明新的檔案類型與 `simroot`，由審查者確認。

### A2.10 `simroot`（ROOT 檔讀取）

Python 不解析 ROOT；`simcore` 不連結 Geant4。讀取由 `simroot` 負責：和 `layered_sim` 同一個 CMake 專案，只連結 Geant4 的 analysis 函式庫（`G4RootAnalysisReader`，同樣基於 g4tools），不建立 run manager。退出碼依第 2 節第 6 條。

| 子命令 | 內容 |
|---|---|
| `info` | 各 ntuple 的列數與欄位、`run` 列的內容；輸出 JSON |
| `dump` | 依鍵排序後，把指定 ntuple 與欄位寫成 CSV（stdout 或 `--out`），浮點以 `%.17g`；可一次讀多個 chunk 檔；`--events` 取子集 |
| `hash` | 內容雜湊：各 ntuple 依鍵排序，數值以 hex-float 正規化後計算 sha256；輸出 `content_sha256` |

- 下游：`simstat` 只讀 CSV；任務 B 的 `simreco` 讀 `simroot dump` 的輸出（經管線，不另存）。研究者可用 ROOT 或 uproot（hep-computing 的 root-uproot adapter）直接分析 ROOT 檔，但它們不是管線或必要測試的依賴。
- 尚未以實際檔案驗證 `G4RootAnalysisReader` 對字串欄、多檔與大檔的支援（§12 風險 9）；若往返測試顯示不足，`simroot` 只讀扁平純量欄，`run` 的字串改寫到 JSON 旁檔。

### A2.11 adapter 變更流程

| 項目 | 內容 |
|---|---|
| 版本 | 0.1.0 → 0.2.0 |
| `adapter.json` | `assets` 加入新檔；更新 `purpose`；`status` 維持 `demonstrated-on-synthetic-data` |
| `SIM_SOURCES`（`geant4_run.py` 行 63） | 加入 `Scorers.*`、`Probe.hh`、`EventFile.*` 與 `simroot` 的原始碼；另設 `SIMCORE_SOURCES` 記錄 `simcore` 的原始碼（否則 `sources_sha256` 會遺漏新原始碼） |
| G5 | 聲明「依 Geant4 API 撰寫，未複製或改寫任何範例程式碼」，由審查者在 VALIDATION 條目中確認；同一條目註明 ROOT 檔類型與 `simroot` |
| 測試 | `tests/adapters/test_geant4.py` 的 assets 檢查；離線測試；`HEP_GEANT4_LIVE_TEST=1` 的 live 測試；`simcore` 的 ctest 與等價測試（不需 Geant4）；`simroot` 的往返與內容雜湊測試（live） |
| CI | 新增必要的 `simcore` 工作：以 C++17 編譯器建置，執行 ctest 與等價測試 |
| 文件 | `docs/capability-matrix.md` 的 Geant4 列 |

### A2.12 階段 2 驗收

- [ ] 以 `simspec convert` 轉換後的新 `layered_sim` 與階段 2 前的 layered_sim：A2.3 的同主機逐位元相同，以及放置傾印完全相同。
- [ ] `simcore` 在 CI 的必要工作中建置，ctest 通過；等價測試在 J14 的 recorded CSV 上通過（計數相同、MPV 分格相同、其他相對差 ≤ 1e-12）。
- [ ] hep-detector 與 adapter 的 Python 正式程式中不再有觀測量與統計量的計算（測試確認 `mpv(`、`bootstrap(` 只出現在 `tests/`）。
- [ ] J14 經存取器讀取 spec/1 與 spec/2 結果一致；兩條薄層規則在兩種格式下都觸發。
- [ ] 探針在測試指令觸發的錯誤時機寫出 `recorded: false`；J14 每個 run 都有 `effective_config`；與宣告一致，故意製造的不一致被抓到。
- [ ] 一個只改欄名的假後端加上手寫 column map，通過 J14 的 summarize、閘門、benchmark。
- [ ] `contracts.schema.validate()` 加 `cross_field_checks()` 對一組合法與非法 spec 的結論，和原 `validate_spec()` 及 C++ 一致。
- [ ] 非空的 `field` 區塊被 `layered_sim` 以 exit 2 拒絕。
- [ ] `output.event_file.level` 為 `none` 時，輸出和階段 2 前逐位元相同；開啟 `summary` 不改變 CSV 的位元組（同種子、serial）。
- [ ] `simroot` 往返測試：`summary` 與 `hits` 層級、含 I、D、S 欄，`dump` 的值和寫入值逐位元相同；同種子、不同執行緒數的兩次 MT run，`content_sha256` 相同。
- [ ] 一致性測試：CSV 的子系統總沉積等於 `deposits` 依事件加總（相對差 ≤ 1e-12），`events` 列數等於 CSV 列數；`hits` 超過 `max_events_hits` 時被拒絕（exit 2）；run 中斷時判為 incomplete。
- [ ] 選用：E2 上若有 ROOT 或 uproot，開啟 ROOT 檔並和 `simroot dump` 比對（不是必要測試）。
- [ ] J14 在 E2 重錄一次；VALIDATION 條目 GEANT4-CORE；CHANGELOG；release manifest。

---

## 8. 統計規格彙整

| 項目 | 規格 | 工作項 |
|---|---|---|
| 停止 | 只依事先宣告的 N；未達標判 unresolved，不補跑 | A1.7、A1.10 |
| 兩階段係數 | SE 來自 K = 16 子 run：f = F₀.₉₀(15,15) ≈ 1.97；來自大樣本 bootstrap：1.2 | A1.7 |
| 收斂閘門 | IUT：通過用 q₀.₉₅，失敗用 q₁₋α/m；SE 為估計值時用 t（差值約 ν = 30），否則用 z；se 是差值的 SE；事先設 se ≤ tol/4 | A1.5 |
| MPV | 16 個子 run 的 MPV 平均；固定分格寬度；SE = sd/√16；t₁₅；全樣本 MPV 只作診斷 | A1.6 |
| bootstrap | 64 位元計數器雜湊、反 CDF、全域唯一事件鍵、R ≥ 400；不用於 MPV | A1.9 |
| 種子 | `H(study_id, role, point_id, k)` → [1, 2³¹) 內的整數；chunk 第二個種子為 start + 1 | A1.8 |
| negative control | 觀測量位移、正負兩個方向 | A1.4 |
| 證據相關性 | `evidence_overlap` | A1.9 |
| 新區塊版本 | `probe_version`、`column_map_version`、`evidence_overlap_version`、`event_file_version` | A1.9、A2.6、A2.7、A2.9 |
| 計算位置 | 階段 1 在 Python；階段 2 起由 `simstat` 計算，門檻與判定留在 Python | A2.8 |

---

## 9. 契約與版本

| 物件 | 位置 | 版本 |
|---|---|---|
| simulated dataset-record、execution trace | `contracts/validate.py`、`core/trace.py` | 3.2.0、3.5.0（既有） |
| 範圍比對 observable kind、benchmark 對照表、等級不得自行宣告、configuration 與隔離規則、`extension.simulation` 選用屬性 | `contracts/validate.py`、`contracts/dependencies.py`、`ext_computational_run.json` | C1（minor、閘控、sci-fix） |
| schema 關鍵字擴充 | `contracts/schema.py` | 不升版 |
| `effective_config`、`evidence_overlap` | computational-run 的自由格式區塊 | 不改契約 |
| `layered_sim.spec/2`、`layered_sim.output/2`、`column_map` | adapter | adapter 0.2.0 |
| `layered_sim.events/1`、`simroot` | adapter（C++） | adapter 0.2.0 |
| `simcore`（`simspec`、`simstat`） | adapter（C++） | adapter 0.2.0 |
| `GRADES`、kind 與 configuration 的輸出 | hep-detector | 隨 plugin 版本 |
| 幾何存取器 | `core/geometry/layered.py` | 隨 plugin 版本 |

computational-run schema 的擁有者是 hep-computing；本任務只加入選用的 `simulation` 屬性（需其同意）。C2 屬於任務 B。

---

## 10. 每個階段結束時的檢查

- `run_all_checks.py`（含 CI lock 環境）
- `check_layering.py`、`check_relocation.py`、`check_ownership.py`、`check_packaging.py`
- `measure_entrypoints.py`（hep-detector quick load ≤ 25,600 bytes）
- `reference_inventory.py --check`、`capability_map.py --check`、`check_routing_static.py`
- 每份 study record 都通過 `validate.py --strict` 與 `dependencies.py`
- `tests.adapters.test_geant4` 離線與 live（`HEP_GEANT4_LIVE_TEST=1`）
- `simcore` 的建置、ctest 與等價測試（CI 必要工作，不需 Geant4）
- `simroot` 的往返、內容雜湊與一致性測試（live，需要 Geant4；階段 2）
- `python3 -m unittest discover -s tests/contracts -t .`（整體執行，以抓測試順序相依）
- `tools/scifix_advisories.py check`（階段 1）
- 由沒參與撰寫的 agent 執行一個新問題，並附通過條件
- 各階段的 Markdown（protocol 變更、本文件）以 0.22.0 的 `review.py` 審查（`--lens-model design=<最強模型>`、`--filter-model`）；紀錄只是 advisory，依 O04/O14 不取代人工的 G5 確認
- VALIDATION 條目、CHANGELOG、release manifest

---

## 11. 不做與延後

| 項目 | 決定 | 理由 / 觸發條件 |
|---|---|---|
| `uses-validated-physics` label | 不做 | 雜湊太嚴也太鬆；會繞過範圍檢查 |
| `physics_config_comparison` 註記 | 延後 | 目前沒有使用者；J15 無法沿用 J14。觸發：需要比較物理設定的研究；屆時差異須經 `evidence_records` 取得 run record 的 `effective_config`，處理 `probe_version` 差異，缺少 `effective_config` 時一律失敗 |
| 依 SE 自適應停止、以加密掃描作為證據 | 不做 | optional stopping 偏差 |
| C++ 雙軌幾何格式 | 不做 | 改由 `simspec convert` 先轉成 spec/2 |
| 新的 core 驗證器、重寫徑跡與多重散射公式 | 不做 | 重用 `contracts/schema.py`、`tracker_resolution.py`、`multiple_scattering.py` |
| 欄位對照放進 contracts | 不做 | 留在 adapter（`layered_sim.output/2`） |
| contracts 4.0 | 不做 | 新增選用區塊與閘控規則屬 minor |
| 規則版本範圍、物理知識外移 | 延後 | 觸發：支援第二個 Geant4 版本 |
| benchmark registry | 延後 | 由契約對照表與 enum 一致性測試取代；觸發：benchmark 數量使測試不足 |
| `inspect` 與 Linux 環境 | 延後 | 觸發：需要在 CVMFS 或 LCG 上執行；需要新的環境編號 |
| 使用者應用後端、可嵌入探針 | 延後 | 觸發：第一個實驗組應用；需重新核准 G5 |
| ReferenceMaterial 契約 | 延後 | 觸發：第一個非平板幾何的 reference benchmark |
| RNTuple、vector 欄 | 延後 | 觸發：檔案大小或讀取速度成為瓶頸；需先確認 Geant4 的寫出與 `simroot` 的讀取支援 |
| 管線中以 Python 直接讀 ROOT（uproot） | 不做 | 管線經 `simroot`；研究者可自行分析 |
| 模擬內 bootstrap、內容定址快取、新執行器、replay 後端 | 不做或延後 | 目前規模不需要；快取鍵難以完整 |
| Python 綁定（pybind11 等） | 不做 | 使用者決定以獨立執行檔交換 JSON/CSV |
| 一般化 `scoped_upgrade` | 延後 | 觸發：第二種研究類型需要升級 |
| Geant4 10.x 探針 | 延後 | 觸發：第一個使用 10.x 的應用；`StreamInfo`（10.2 起）、`FluctuationType()`（11.x 起）需依版本條件編譯 |
| J15 相關項目 | 在任務 B | 見任務 B §11 |

---

## 12. 待維護者決定的事項與殘餘風險

**待決定：**
1. 階段 1 的版本歸類：本文件依「閘控設在 x.y.0」的慣例，定為 C1（minor）加 sci-fix。
2. 若同主機也無法逐位元相同，是否接受改為統計比對（在 VALIDATION 記錄原因）。
3. G5「未複製範例程式碼」的確認方式。
4. `ext_computational_run.json` 加入選用的 `simulation` 屬性：需要 hep-computing 同意。
5. 新增必要的 CI 工作建置 `simcore`（需要 C++17 編譯器）；目前 adapter 沒有必要的 CI 工作。
6. ROOT 檔的存放位置與保留期限（不提交 repo；建議放在 hep-computing 的執行目錄，以 run record 的雜湊對應）。

**殘餘風險：**
1. J14 的偵測極限可能因子 run 估計量、t 分位數與觀測量單位的控制組而改變，需要重新設計控制組。
2. 子 run MPV 平均和全樣本 MPV 有小偏差（審查者的 toy 約 0.25 %），在 sci-fix 紀錄中說明。
3. quick load 只剩 931 bytes。
4. 探針假設 worker 和 master 的設定相同；若發現 thread-local 差異，改為逐執行緒傾印。
5. `longitudinal-profile` 的 `target_slabs` 由人宣告；契約只能以 `target_geometry_sha256` 比對宣告與 benchmark，無法判定目標堆疊就是論文中的配置，仍需審查者核對。
6. 工作量：原型估計階段 1 約 8–12 個工作天，另加 Geant4 執行時間（A1.1、A1.2、A1.10 約 1 天；A1.3 1–2 天；A1.4 1–2 天；A1.5–A1.9 3–5 天；sci-fix 流程約 1 天）。階段 2 未估計。
7. 兩種語言的維護成本：以原則 11 與等價測試控制，同一個量只有一份正式實作。
8. 浮點等價：編譯器與最佳化（例如 FMA）可能讓 `simstat` 與 oracle 在最後幾位不同；等價測試用相對差 ≤ 1e-12，逐位元相同只要求模擬輸出與 `simspec` 的放置數值（同一建置）。
9. `G4RootAnalysisReader` 對字串欄、多檔與大檔的讀取能力尚未以實際檔案驗證；由 A2.12 的往返測試確認（退路見 A2.10）。
10. 磁碟與記憶體：大樣本的 ROOT 檔可達數百 MB；MT 合併時 worker 的 basket 在 run 結束前留在記憶體中。`hits` 有事件數上限；大小與記憶體在 trial run 中確認並記錄。

---

## 13. 建議的執行步驟

**階段 1**
1. 開始前檢查（§0）；套用 `prototype/phase1-core.patch`，補齊 A1.1–A1.3 中原型缺少的部分。
2. A1.10 的 D10 修正先做，之後每次都以 `python3 -m unittest discover -s tests/contracts -t .` 整體執行。
3. A1.1 → A1.2 → A1.3（契約與 `dependencies.py`），加契約測試；以離線重播重產 J14 並通過 `--strict`。
4. A1.10 其餘項目（schema enum、`simulation` 屬性、protocol 第 4 節）。
5. A1.4–A1.9（`geant4_benchmarks.py`、`check_geant4_study.py`），加 toy 測試。
6. 在 E2 live 重錄 J14（K = 16 chunk、負向控制組）；檢查 A1.12 的偵測極限項。
7. A1.11：ledger、advisory、parent record、VALIDATION、CHANGELOG、release manifest；跑 §10 的檢查。

**階段 2（階段 1 合併後）**
1. A2.5（schema 關鍵字）與 A2.4 的幾何存取器（純 Python，可先做）。
2. `simcore`：先 `simspec convert`（A2.3），再 `simstat`（A2.8）與等價測試；建立 CI 工作。
3. layered_sim：spec/2 讀取（A2.2，含 `field` 拒絕）、scorer 元件化、探針（A2.6）、column map（A2.7）；完成同主機逐位元比對。
4. 逐事件 ROOT 檔（A2.9）與 `simroot`（A2.10）及其測試。
5. Python 介面改為呼叫 `simstat`，移除正式程式中的統計計算；A2.11 的 adapter 變更項目。
6. J14 在 E2 重錄；A2.12 全部打勾；跑 §10 的檢查。

---

## 附錄 A：數值

計算程式：`j15_design_estimates.py`（本資料夾；只用標準函式庫，scipy 可選）。J15 的數值見任務 B 附錄 A。

- 達標機率：以真實 SE 判定時 P(χ²₁₅ ≥ 15/f)：f = 1.2 為 0.641，f = 1.755 為 0.90。以估計 SE 判定時 P(F₁₅,₁₅ ≤ f)：f = 1.2 為 0.636，f = 1.755 為 0.856，**f = 1.972 為 0.90**。
- t₀.₉₅(30) = 1.697，t₀.₉₅(15) = 1.753，t₀.₉₇₅(15) = 2.131。

---

## 附錄 B：基準核對紀錄

### B.1 依 0.21.0 的重新核對（2026-10-21；歷史紀錄）

本提案原以 0.20.0 撰寫；0.21.0（`c4f7954`）合併後逐項重新核對。

| 0.21.0 變更 | 影響 | 處理 |
|---|---|---|
| contracts 3.2.0：simulated dataset-record | 原定的 3.2.0 已被使用 | 改用 C1、C2 記法（B.2） |
| simulated dataset-record：輸入 study record 為 `validated-in-scope` 時，表格可不帶 `unvalidated` | 範圍漏洞（D1、D2）會經由這條路徑傳到表格 | advisory 一併說明（A1.11）；J15 的重建表格以此格式發布（任務 B） |
| 新的 reference benchmark `longitudinal-profile` | 契約對照表要加入；它的目標是整個取樣堆疊，「唯一一片平板」的 isolated 定義會誤判 | 對照表加入（A1.1）；configuration 以 benchmark 目標定義並輸出目標雜湊（A1.3） |
| study spec 的 benchmark enum 未列 `shower-containment`、`longitudinal-profile` | D8 擴大 | A1.10 兩者都補上 |
| layered_sim 支援混合材料（`components`） | 轉換與逐位元相同要處理材料順序 | A2.3、A2.5；任務 B 不需再做 |
| `multiple_scattering.py` 輸出 `intrinsic_coefficient` 並在 N < 10 時警告；回報值仍用 Gluckstern | J15 的參數說明需更新 | 任務 B §4.2 |
| `check_routing_static.py` 從 `docs/researcher-journeys.md` 讀取 journey | J15 列入表後就必須有路由案例 | 任務 B §9 |
| `geant4.def` 固定基底映像的 digest | 無 | — |

0.21.0 時仍存在的缺陷（0.21.0 行號）：

| # | 位置 | 狀態 |
|---|---|---|
| D1 | `validate.py` `_scope_inside()` 行 327；`check_geant4_study.py` `scope_within()` 行 481 | 未修正 |
| D2 | `validate.py` `_study_upgrade()` 行 373，篩選行 397 | 未修正 |
| D3 | `geant4_benchmarks.py` 行 678 | 未修正 |
| D4 | `check_geant4_study.py` 行 358 | 未修正 |
| D5 | `geant4_benchmarks.py` 行 369 | 未修正 |
| D8 | study spec enum 7 個、`GRADES` 9 個 | 擴大 |

0.21.0 的其他核對值：`CONTRACTS_VERSION` 3.2.0；`GEANT4_UPGRADE_FROM` 3.1.0（行 324）；`SUPPORTED_KEYWORDS` 仍無 maxItems、maximum、exclusiveMaximum；`SIM_SOURCES` 11 個檔案；`validate_spec()` 在 `geant4_run.py` 行 103（新增混合材料的檢查）；`DetectorScriptCount` 21；adapter geant4 0.1.0（`demonstrated-on-synthetic-data`）；共享 stanza 點 5 寫「3.1.0 upgrade rule」；J14 `recorded/` 2,447,979 bytes；quick load 24,669 / 25,600 bytes；`check_packaging.py` MAX_BYTES 2 MiB；最新 advisory SFA-2026-035；journey 表 J1–J14。

### B.2 依 `9f08796` 的第二次深度檢查（2026-10-22）

檢查分三部分：一位沒參與撰寫的 agent 以 0.22.0、0.23.0 與未發布的變更審查提案；另一位在獨立 worktree 中照階段 1 規格做原型；主要證據由撰寫者重新核對。

| 變更 | 影響 | 處理 |
|---|---|---|
| contracts 3.3.0（審查格式）、3.4.0（審查篩選）、3.5.0（execution trace）已被使用 | 原定版本號失效 | 改用 C1、C2 記法 |
| execution trace：`provenance.code_paths`、`code_tags`、`trace.tag()` | 新的寫入者需加 `trace.provenance()`；新的共用函式應加 tag；import `contracts.validate` 會改變 `code_paths` | A1.9；任務 B §5 |
| `scifix_advisories.py check`：鍵必須可區分、advisory 與 ledger 等級一致、範圍與 `introduced_basis` | 原 advisory 寫法無法通過；simulated 表格無法用鍵區分；D5 是 S1 | A1.11 |
| `core/status.py`：`refused` 是負向判定，`rejected` 是無法使用的輸入；exit 0/1/2/3 | unresolved、未達標、探針、新腳本的狀態 | A1.5、A2.6；任務 B §5 |
| partition：manifest 內重複種子被拒；`make_manifest` 的種子規則；`cmd_chunk` 的 `start + 1` | 原種子公式衝突；子 run 不是切分既有 run | A1.6、A1.8 |
| `check_layering.py` 更嚴、`core/OWNERS.json` 需 steward | 幾何存取器放在 `core/`；不得寫實驗名稱 | §2、A2.4；任務 B §9 |
| `measure_entrypoints.py` 完整量測折疊描述 | hep-detector 描述 1,018 / 1,024 字元 | 任務 B §9 |
| `check_packaging.py` 掃描所有文字檔 | 探針寫出的路徑經 `tilde()` | A2.6 |
| 獨立審查工具 `review.py`（0.22.0） | 可作為各階段文件的 advisory 審查 | §10 |

**階段 1 原型**（`prototype/phase1-core.patch`，可套用到 `9f08796`）：

| 項目 | 結果 |
|---|---|
| 實作範圍 | A1.1、A1.2、A1.3、A1.10；未做 A1.4–A1.9 |
| 測試 | 四個相關模組 55 個測試通過；`tests/skills/hep_detector` 346 個通過；`check_layering`、`reference_inventory --check`、`check_ownership`、`check_packaging` 通過 |
| J14 | 離線重播重產後，7 份 study record 都通過 `validate.py --strict` 與 `dependencies.py`；27 個準則全部通過。舊的已提交紀錄在 `--strict` 下以 `geant4.upgrade_scope_outside` 失敗，不加 `--strict` 時通過，證明閘控有效 |
| 被推翻或修正的宣稱 | 版本號已過時；「舊紀錄在 `--strict` 下失敗」只對帶 `validated-in-scope` 者成立；A1.1–A1.3 不需 live 重錄；「J14 不受影響」只對判定成立；`longitudinal-profile` 照字面推導一律 `embedded`，只比 particle 與 energy 會放寬範圍 |
| 規格不足處（已補） | kind 存放位置、benchmark kind 的來源、等級檢查的適用範圍、宣告缺少維度、雜湊的正規形式、`run_record` 為選用、重複放置、場的判定、CSV 與 run record 無法以雜湊連結、D8 在執行時沒有作用 |

原型的重跑結果已由撰寫者確認（55 個測試通過）。D10 已在乾淨的 main 上重現：`tests/contracts` 整體執行有 5 個錯誤，單獨執行 `test_simulated_dataset` 則通過。

**`9f08796` 的核對值：**

| 項目 | 值 |
|---|---|
| `CONTRACTS_VERSION` | 3.5.0 |
| `GEANT4_UPGRADE_FROM` | 3.1.0（行 346） |
| J14 study record | contract 3.5.0，帶 `code_paths`、`code_tags` |
| J14 世界材料 | `G4_Galactic` |
| J14 `recorded/` | 2,447,979 bytes |
| advisory | 最新 SFA-2026-037 |
| hep-detector | quick load 24,669 / 25,600 bytes；description 1,018 / 1,024 字元 |
| `SUPPORTED_KEYWORDS` | 無 maxItems、maximum、exclusiveMaximum |
| `DetectorScriptCount` | 21；`docs/capability-matrix.md` 行 47 寫「twenty-one scripts」 |
| 共享 stanza 點 5 | 寫「3.1.0 upgrade rule」 |
| `check_packaging.py` MAX_BYTES | 2 MiB |
| `longitudinal-profile` 設定 | 只有 `layers: [{t, column}]`，沒有放置清單 |
| benchmark 輸出的 scope | `material`、`thickness_mm` 取自設定（`longitudinal-profile` 通常為 null），`observable` 為自由文字 |
| journey 表 | J1–J14 |

**尚未做：** 本文件尚未經獨立審查。建議在維護者本機以 `review.py` 審查（依 `skills/hep-authoring/references/independent-review.md`：先關閉 fork 子代理並重啟 host，且文件在 host 上沒有其他副本）。

---

## 附錄 C：出處

- Geant4 v11.4.3 原始碼（`github.com/Geant4/geant4`，tag `v11.4.3`），審查中讀過：`G4RunManager.cc`、`G4RunManagerKernel.cc`、`G4MTRunManager.cc`、`G4TaskRunManager.cc`、`G4WorkerRunManager.cc`、`G4EmParameters.cc`、`G4EmParametersMessenger.cc`、`G4EmExtraParametersMessenger.cc`、`G4ProductionCutsTable`、`G4HadronicInteraction.hh`、`G4HadronicProcess.hh`、`source/analysis/`（含 `G4VAnalysisManager.hh`）、`G4FieldManager.hh`、`G4ChordFinder.hh`、`G4PropagatorInField.cc`、`G4FieldBuilder`、`G4FieldParameters`、`G4LogicalVolume`、`G4ChargedGeantino.cc`、`G4EmBuilder`、`G4EmSaturation`、`G4LossTableManager`、`G4IonisParamMat`、`G4IonTable`、`FTFP_BERT.cc`、`G4PhysListFactory`、`G4NistMaterialBuilder.cc`、`G4PVPlacement`、`G4QuickRand.hh`、`G4GeomTestVolume.cc`
- Geant4 Book for Application Developers：[Analysis](https://geant4.web.cern.ch/documentation/dev/bfad_html/ForApplicationDevelopers/Analysis/introduction.html)
- I. Hřivnáčová, Geant4 analysis tools（CHEP 2023）：ntuple 合併（MT、row-wise 與 column-wise）
- hep-research 0.21.0（`c4f7954`）與 `9f08796`：`contracts/validate.py`、`contracts/schema.py`、`contracts/stanzas/context-resolution.md`、`skills/hep-detector/`、`adapters/geant4/`、`examples/geant4-thin-silicon/`、`docs/maintenance.md`、`docs/capability-matrix.md`、`tools/measure_entrypoints.py`、`tools/check_packaging.py`、`tests/skills/test_documented_output_claims.py`、`CHANGELOG.md`、`VALIDATION.md`

---

## 附錄 D：版本歷程

| 版本 | 主要內容 | 審查與主要更正 |
|---|---|---|
| v2 | 四層架構、四份契約、三種後端 | 兩份審查：探針時機、EM 參數鎖定、SE 停止偏差、`uses-validated-physics`；發現現行範圍檢查缺陷 |
| v3 | 縮小為三批次 | — |
| v4 | 整合為五階段 | 三份審查：幾何不自洽、J14 會失效、收斂不可行、契約不強制升級限制、重複實作 |
| v5 | 三階段 | 兩份審查：MPV 估計量、F 分布係數（0.74 更正為 0.64）、等級自行宣告、隔離漏洞、種子索引、多處 plugin 事實（磁場相關見任務 B） |
| 最終版（0.21.0 基準） | 依 0.21.0 重新核對 | 附錄 B.1 |
| 最終版（`9f08796` 基準） | 第二次深度檢查：差異審查與階段 1 原型；C1、C2 記法；隔離規則移到階段 1；`longitudinal-profile` 的目標與 kind；sci-fix 拆分；種子與退出碼；D10 | 附錄 B.2 |
| 語言分工（2026-10-22） | 計算核心改用 C++（`simcore`）；Python 為介面與判斷層；獨立執行檔交換 JSON/CSV | 使用者決定 |
| 逐事件 ROOT 檔（2026-10-22） | 詳細逐事件資訊寫成 ROOT 檔（g4tools，不需安裝 ROOT）；`simroot`；CSV 保留為摘要 | 使用者決定 |
| 任務拆分（2026-10-22） | 拆成任務 A（本文件）與任務 B（J15，之後做）；spec/2 預留 `field`；`crossings` 層級移到任務 B | 使用者決定 |
| **整理為實作規格（2026-10-22）** | **加入任務卡、名詞表、硬性限制、工作項編號（A1.x、A2.x）、建議執行步驟；章節重新編號；內容不刪減** | 使用者要求 |
