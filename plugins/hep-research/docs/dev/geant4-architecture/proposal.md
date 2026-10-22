# hep-research Geant4 研究架構：最終版

> 狀態：最終提案，待維護者核准
> 依據：三輪獨立審查（v2、v4、v5，共 7 份審查報告）、依 0.21.0 的重新核對（第 12 節），以及 2026-10-22 依目前 main 的第二次深度檢查（一份差異審查、一個階段 1 原型；第 13 節）；審查指出的事實與數值都已逐項核對
> 基準：hep-research `main` 的 `9f08796`（**0.23.0** 加未發布的變更），contracts **3.5.0**，adapter geant4 0.1.0，Geant4 11.4.3（commit `2ee379e6`）
> 日期：2026-10-22（依目前 main 重新核對；見第 13 節）
> 契約版本記法：**C1** = 合併時下一個未使用的 minor（3.5.0 先發布時為 3.6.0），**C2** = 其後一個。本文不寫死版本號：3.3.0–3.5.0 在本提案撰寫期間已被其他變更使用
> 語言：本文件為繁體中文原文；英文版見 [`proposal.en.md`](proposal.en.md)，兩者內容一致
> 範例性質：J15 最小磁譜儀是**合成幾何**，是 verification 的載體，不是任何實驗的偵測器

---

## 0. 摘要

本提案分三個階段，修正 hep-research（0.20.0 起至目前 main）Geant4 部分的正確性缺陷，讓研究流程不再綁死在單一後端，並以一個最小磁譜儀（J15）示範磁場、多子系統與重建鏈。

| 階段 | 內容 | 版本 | J14 |
|---|---|---|---|
| 1 | 修正 label 與統計缺陷（sci-fix）：範圍比對 observable kind、benchmark 等級改由契約對照表決定、configuration 由幾何推導並強制隔離規則、negative control 依觀測量位移、收斂閘門（IUT）、MPV 的 SE 改用子 run 分割 | **contracts C1**（minor） | 4.1–4.3 以離線重播重產；4.4、4.5 需 live 重錄一次 |
| 2 | C++ 計算核心：layered_sim 重構（spec/2、scorer 元件、探針、column map）與新的 `simcore`（spec 轉換、觀測量與統計量）；Python 改為介面；hep-detector 同時讀兩種格式 | **adapter 0.2.0**；contracts 不升版 | 同主機逐位元相同後重錄一次 |
| 3 | J15 最小磁譜儀：場區、平面穿越 scorer、以 `simcore` 做數位化與重建（混合材料 0.21.0 已支援）；`verification` 等級；重建紀錄可作為 simulated 表格的輸入 | **adapter 0.3.0**、**contracts C2**（minor） | 不重錄 |

**九個最重要的決定：**

1. **現行的 `validated-in-scope` 有漏洞，必須先修。** 範圍檢查跳過觀測量，而且 benchmark 的等級由紀錄自己宣告。
2. **驗證等級依參考的性質決定。** 參考值是輸入的精確推論的，屬於 verification；參考值是 Geant4 所近似的物理模型的，才可能是 validation。
3. **升級資格由契約強制。** 契約自帶「benchmark → 等級、kind」對照表；`configuration` 由工具從幾何推導、由 `dependencies.py` 重新推導核對，不接受使用者宣告。
4. **C++ 只保留一條幾何路徑。** spec/1 由 C++ 的 `simspec` 轉成 spec/2（沿用舊幾何的浮點運算），以同主機逐位元相同證明轉換正確。
5. **重用既有工具。** 包括 `contracts/schema.py`、`tracker_resolution.py`、`multiple_scattering.py`，不另寫第二份。
6. **場精度用確定性檢查。** 以 charged geantino 對解析螺旋比較，不需要統計。
7. **統計規格必須能被執行。** 收斂閘門用 intersection-union test；SE 是估計值時一律用 t 分位數；兩階段事件數的係數為 F₀.₉₀(15,15) ≈ 1.97；未定案與未達標以 `incomplete`（exit 3）回報，不標 `failed`。
8. **刪除或延後不必要的項目。** 包括 `uses-validated-physics`、`physics_config_comparison`、離子與 Birks、內容定址快取、契約 4.0 等（第 7 節）。
9. **計算核心用 C++，Python 是介面與判斷層。** 模擬、scorer、spec 轉換、觀測量與統計量、數位化與重建都在 C++（`layered_sim` 與不連結 Geant4 的 `simcore`），以獨立執行檔交換 JSON/CSV。Python 只負責命令列與流程、獨立的參考公式、規則與閘門判定、label、紀錄寫出與契約；C++ 與 Python 因此互為獨立實作（第 3 節）。

---

## 1. 背景：已確認的現行缺陷

以下各項都已對照目前 main（`9f08796`）的原始碼確認（行號為該版本）。

| # | 缺陷 | 位置 | 後果 |
|---|---|---|---|
| D1 | 範圍檢查不比對觀測量 | `validate.py` `_scope_inside()`（行 349 起）；`check_geant4_study.py` `scope_within()`（行 482–493，迴圈中明確跳過 observable，且忽略純量） | 用 MPV benchmark 通過的研究可以把其他觀測量標成 `validated-in-scope`；宣告範圍缺少某個維度（例如 material）時，該維度不受限制 |
| D2 | benchmark 的等級由紀錄自己宣告 | `_study_upgrade`（行 395；篩選在行 419）讀紀錄內的 `grade` | 任何產生端只要寫 `"grade": "reference"` 就能升級 |
| D3 | negative control 在不同單位間比較、只測單向 | `geant4_benchmarks.py` 行 678 的 `at_limit` | 「位於偵測極限」在觀測量上未被證明 |
| D4 | 收斂閘門無等價檢定 | `check_geant4_study.py` `convergence()`（判定在行 359） | 真實差值等於容許值時約 50 % 通過 |
| D5 | MPV 的 SE 用 bootstrap | `geant4_benchmarks.py` 行 369 對 argmax 型的 `mpv()` 做 bootstrap | 變異數估計不一致；J14 的偵測極限建立其上 |
| D6 | 停止規則未明文禁止依結果加跑 | protocol 第 4 節 | optional stopping 偏差 |
| D7 | 證據相關性未揭露 | J14 的 nominal run 同時供閘門、統計目標、benchmark、variation 使用 | 被當作獨立證據 |
| D8 | study spec 的 benchmark enum 缺 `shower-containment` 與 0.21.0 新增的 `longitudinal-profile` | `geant4-study-spec.schema.json`；`GRADES` 有 9 個、enum 有 7 個 | 一致性缺口；`longitudinal-profile` 是 reference 等級，卻無法在 study spec 中宣告 |
| D9 | 研究層和 layered_sim 的資料格式綁死 | `derived()` 讀 `geometry.layers`；`summarize` 與 benchmark 讀固定欄名 | 其他後端無法進入閘門與 benchmark |
| D10 | 測試順序相依：`tests/contracts` 整體執行時，`test_geant4_upgrade` 的 `tearDownModule` 刪除共用的 J14 重播目錄，`test_simulated_dataset` 的 5 個測試因此出錯；單獨執行時通過 | `tests/contracts/test_geant4_upgrade.py`、`tests/contracts/test_simulated_dataset.py` | 錯誤依執行順序而定，分片執行時可能被掩蓋 |

---

## 2. 設計原則

1. **正確性先於擴充。** 階段 1 完成前，不合併任何新功能。
2. **研究核心只認資料。** 規則、閘門、benchmark 經由 column map 與探針輸出讀取，不讀後端專屬的欄名或 UI 指令字串。
3. **相信實際狀態，宣告只作為退路。**
4. **證據的停止規則和格點事先宣告。** 加跑、加密、重做控制組都不得依閘門或 benchmark 的結果決定。
5. **先找現有實作。** plugin 已有的方法一律重用；oracle 不得 import 被測的模組。
6. **最小變動。**
7. **遵守既有規則。** 包括分層（skill 腳本和 adapter 只 import `core`、`contracts`）、quick load 上限（hep-detector 目前 24,669 / 25,600 bytes）、G5 授權邊界、adapter 變更流程、sci-fix 流程、執行狀態與退出碼（`core/status.py`）、execution trace（`trace.provenance()`）。新的共用模組放在 `core/` 時需在 `core/OWNERS.json` 指定 steward；`skills/` 與 `contracts/` 中不得出現實驗名稱（`check_layering.py`）。Geant4 相關腳本只用 Python 標準函式庫，這是設計選擇，不是 plugin 的全域規則。C++ 端只用 C++17 標準函式庫與既有的 `MiniJson.hh`；`simcore` 不連結 Geant4。
8. **後端自我描述。** layered_sim 在執行時輸出自己的 column map 與實際生效的設定。
9. **驗證等級依參考的性質決定。** 參考值若是輸入的**精確推論**（解析螺旋、運動學、最小平方代數），檢查屬於 verification，不能用來升級；參考值若是 Geant4 所**近似的物理模型**（Bethe、Landau–Vavilov、Highland、簇射剖面）或**已發表的量測**，才可能是 reference 或 sanity。
10. **可升級的事實由契約認定。** 等級、kind、配置都不得由紀錄自行宣告。
11. **語言分工。** 把模擬輸出化為數字的計算（逐事件與逐 run 的縮減、估計量與其 SE、擬合）一律在 C++；由物理輸入算出參考值的公式、門檻比較與判定、紀錄與 provenance、契約一律在 Python。同一個量不得在兩種語言各有一份正式實作；另一種語言的實作只能出現在測試中，作為 oracle。

---

## 3. 架構總覽

**語言分工**（使用者決定，2026-10-22）：

| 層 | 語言 | 內容 |
|---|---|---|
| 計算核心 | C++ | `layered_sim`（連結 Geant4）：模擬、scorer、探針、column map。`simcore`（C++17 標準函式庫，不連結 Geant4）：`simspec`（spec/1 → spec/2 轉換）、`simstat`（觀測量、MPV 與子 run、bootstrap、收斂差值與其 SE、能量平衡殘差）、`simreco`（階段 3：數位化、擬合、β、量能器） |
| 介面 | Python | `adapters/geant4/assets/*.py`：命令列、建置、執行 C++ 執行檔、spec 的 schema 與跨欄位驗證、紀錄寫出（含 `trace.provenance()`）、simulated 表格 |
| 判斷與參考 | Python | hep-detector：規則、獨立的參考公式（Bethe、Δp、Highland、gamma 剖面、PSTAR）、閘門與 benchmark 的判定、label；和 C++ 的計算互為獨立實作 |
| 契約 | Python | `contracts/`（全 plugin 共用，不變） |

C++ 與 Python 之間只以獨立執行檔交換 JSON/CSV，和現在的 `layered_sim` 相同；不用 Python 綁定。所以 Python 端維持只用標準函式庫、不需編譯，G5 核准的「獨立執行檔交換 JSON 與 CSV」邊界也不變。`simcore` 不連結 Geant4，不受 Geant4 授權影響，而且可以在沒有 Geant4 的 CI 中建置與測試。

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
                            （階段 3，C2）對照表加入 verification；重建紀錄作為 simulated 表格的輸入
                            （既有）simulated dataset-record（3.2.0）、execution trace（3.5.0）
  schema.py                 （階段 2）加 maxItems、maximum、exclusiveMaximum（不升版）
  computational-run（既有；extension.study 為自由格式區塊；C1 把 extension.simulation 加為選用的自由格式屬性）
        ▲
        │  產生檔案（JSON、CSV）
adapters/geant4（紀錄一律 unvalidated）
  Python 介面
    geant4_build.py         build / check；建置 layered_sim 與 simcore
    geant4_run.py           run / scan / chunk / summarize / reduce / oracle；（階段 3）reco / table
    geant4_verify.py        overlaps / budget / balance / mirror / datapaths（讀雙格式；數值來自 simstat）
  C++ 計算核心
    layered_sim             連結 Geant4；只認 spec/2；scorer 元件；探針；column map（layered_sim.output/2）
                            （0.21.0 既有）混合材料；（階段 3）場區、平面穿越
    simcore                 不連結 Geant4（C++17 標準函式庫）
      simspec               spec/1 → spec/2 轉換（沿用舊幾何的浮點運算）
      simstat               觀測量與統計量（階段 2）
      simreco               數位化與重建（階段 3）
        │
        ▼
hep-computing（run_workflow.py、local_partition.py）
```

---

## 4. 階段 1：修正現行缺陷（contracts C1，sci-fix）

階段 1 是 sci-fix：以最小變動，直接在現有的 Python 中修正。4.5 的估計量（子 run MPV、bootstrap、收斂差值）在階段 2 移到 C++ 的 `simstat`，屆時階段 1 的 Python 實作只保留在測試中作為 oracle（5.8）。

### 4.1 契約側的 benchmark 對照表（D2）

在 `contracts/validate.py` 新增常數表。`_study_upgrade` 改從這張表取得等級與 kind，不再讀紀錄內的宣告：

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

- 表中等級和目前的 `GRADES` 相同（9 個名稱；原型已加測試確認）。J14 的判定不變，但所有 study 與 benchmark 檔案的內容會改變（新增欄位；`code_paths` 多出 `contracts/validate.py` 等）。
- 紀錄裡的 `grade` 和表不一致、或 benchmark 名稱不在表中時，判為 error；適用於所有帶 Geant4 study 區塊的紀錄，不只升級的紀錄。
- `geant4_benchmarks.py` 的 `GRADES` 保留給工具使用，並加測試確保和契約表一致。benchmark 支持的 kind 只以契約表為準；工具輸出的 kind 僅供閱讀。

### 4.2 範圍檢查（D1）

- 比對受控的 `observable.kind`（study spec 既有 enum），不比自由文字；自由文字保留供人閱讀。
- 宣告的 kind 由 `label` 從 study spec 的 `observable.kind` 複製到 `declared_scope.observable_kind`（study spec 的 `validation_plan.scope` 是 `additionalProperties: false`，所以 schema 也要加入這個欄位）；它必須在被計入 benchmark 的「支持 kind」之內。
- benchmark 範圍中有的維度，宣告範圍都必須有；缺少的維度視為超出範圍（目前缺少即不受限制）。
- 比對維度：observable kind、particle、material、energy、thickness；純量視為 `[v, v]`。
- 單一實作放在 `validate.py` 並匯出；`check_geant4_study.py` 匯入使用，`scope_within()` 刪除。
- 閘控方式和其他規則族一致：`strict or _at_least(contract_version, C1)`，沒有 warning 分支。contract 3.5.0 以下的紀錄只在 `--strict` 下受新規則約束，而且只有帶 `validated-in-scope` 的紀錄會失敗（`_study_upgrade` 對其他紀錄提早返回）。
- `longitudinal-profile` 的範圍只含 particle 與 energy（工具對它輸出 null 的 material 與 thickness），比對時用這兩維、kind，以及**目標幾何雜湊**：宣告範圍必須帶有和 benchmark 相同的 `target_geometry_sha256`（4.3）。只比 particle 與 energy 會讓任何材料堆疊都能借用已發表堆疊的結果升級（原型驗證過這個放寬）。能量為純量，所以宣告的能量範圍必須等於該值。

### 4.3 configuration 與隔離規則（階段 1）

- `geant4_benchmarks.py` 為每個 benchmark 結果輸出 `configuration`、`target_geometry_sha256` 與 `configuration_basis`，從 benchmark 設定的 `run_record` 所指 run record 的幾何推導，不接受使用者輸入。計入升級的 benchmark 必須有 `run_record`（目前是選用）。
- **目標**：benchmark 設定宣告 `target_slabs`（目標包含的 slab 名稱，含吸收層）。單層 benchmark 預設為被量測的那一片；`longitudinal-profile` 必須明列整個取樣堆疊。它的 `layers` 只列讀出欄位、不含吸收層，無法推導；原型顯示照字面推導時，真實的取樣堆疊一律是 `embedded`。
- `isolated` 的條件：沒有場、世界是真空（`G4_Galactic`；J14 符合）、世界以外的每個放置都屬於 `target_slabs`；否則為 `embedded`。spec/1 沒有場的欄位，視為無場；spec/2 以明確的 `field` 區塊判定，階段 2 起再以探針記錄的實際場核對。
- `target_geometry_sha256`：目標的正規化清單（依序的 slab、厚度、橫向尺寸、材料組成與密度；數值以 `repr`；重複放置逐一列出）的雜湊，spec/1 與 spec/2 結果相同。
- **契約規則（C1，閘控同 4.2）**：每個被計入的 benchmark 都必須是 `configuration == "isolated"`；缺少或為 `embedded` 都是 error。`dependencies.py` **必須**從 `evidence_records` 中的 run record 重新推導 configuration 與雜湊，並和紀錄比對；否則 configuration 和等級一樣是自行宣告。
- 原型確認：configuration 可以從既有的 recorded run record 推導，所以 J14 只需離線重播就能帶上 `configuration: isolated`，不必為此 live 重錄。
- 殘餘限制：J14 的 recorded CSV 是縮減版，其雜湊無法和 run record 的 `output_hashes` 對上。configuration 描述的是設定檔**指名**的 run record，而不是被證明產生該 CSV 的 run record；protocol 中寫明。negative control run 的幾何不另外檢查。

### 4.4 negative control（D3）

- 判定量為觀測量上的實際位移：`shift = (control − nominal) / reference`，SE 由兩個 run 合成。
- 位於偵測極限：`caught` 且 `|shift| ≤ 1.1 × DL`。
- 兩個方向都要注入，否則把宣稱限縮為單向，寫入 `scope.detection_limit_sign`。
- J14 現有的控制組只注入 +密度。階段 1 先把兩個 J14 宣稱限縮為單向（`detection_limit_sign: "+"`）；依原型，兩者已滿足 `|shift| ≤ 1.1 × DL`（MPV 0.0856 對 DL 0.0827；stopping power 0.0381 對 0.0378）。live 重錄時補上負向控制組。

### 4.5 統計規格

**收斂閘門（D4）。** 「所有觀測量都等價才通過」是 intersection-union test：

```
通過：|diff| + q_pass · se ≤ tol
失敗：|diff| − q_fail · se > tol
其他：unresolved
```

| 項目 | 規格 |
|---|---|
| se | 指**差值**的 SE |
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

在真實差值為 tol/2 時，通過的檢定力只有約 64 %；這是事先設定 se ≤ tol/4 的代價，在文件中寫明。

**回報方式。** unresolved 以執行狀態 `incomplete`（exit 3）回報，artifact label 保持 `unvalidated`；只有 fail 是 `failed`（exit 1）。目前 `convergence()` 與 `cmd_run` 把非 pass 一律當 `failed`，需要修改。

**MPV 的估計量與 SE（D5）。**
- nominal 樣本改為以 K = 16 個 chunk 產生（以手動建立的 partition manifest 呼叫 `geant4_run.py chunk`），總事件數仍為 N。這**不是**把既有的單一 nominal run 切開：每個 chunk 都是新的事件，所以 J14 的 nominal 需要 live 重錄。全樣本以各 chunk 的 CSV 串接（`concat`）得到。
- 回報值改為 **16 個子 run MPV 的平均**，分格寬度固定並寫入 spec；SE = sd(子 run MPV) / √16；分位數用 t₁₅。
- 全樣本的 MPV 只作為診斷，和平均值的差寫入紀錄。理由是直方圖眾數估計量不依 1/√N 縮放，sd/√K 只對「子 run MPV 的平均」這個估計量成立。審查者的 toy 顯示，對全樣本 MPV 會低估 1.1 到 2.3 倍，視分格寬度而定。
- bootstrap 不再用於 MPV。
- 子 run 的 MPV 從各 chunk 的 CSV 分別計算，不得經 partition 的合併規則（`mpv` 不在 `NON_ADDITIVE_TOKENS` 中，若作為 chunk 的數值鍵會被靜默加總）。

**兩階段事件數。**
- `N = ceil(N_trial · (SE_trial / target)² · f)`。
- 「未達標」以證據 run 的**估計** SE 判定。當試探 run 和證據 run 的 SE 都來自 K = 16 子 run，達標機率為 P(F₁₅,₁₅ ≤ f)：f = 1.2 時只有 0.636，所以取 **f = F₀.₉₀(15,15) ≈ 1.97**，達標機率為 90 %。
- SE 來自大樣本 bootstrap 時，f = 1.2。
- 證據 run 未達標時判為 unresolved（`incomplete`，exit 3），**不得補跑**。

**種子。** `H(study_id, role, point_id, k)` 映射為 [1, 2³¹) 內的**一個**整數（C++ 以 double 讀取種子，超過 2⁵³ 會失去精度）。角色有 trial、nominal、scan、control、variation、calibration；k 是 chunk 索引；正負兩個方向的控制組使用不同的 point_id。
- chunk：manifest 由研究手動建立，每個 chunk 的種子為 H；layered_sim 的第二個種子沿用 `cmd_chunk` 的 `start + 1`。不使用 `make_manifest` 的 `seed × 100003 + k`。
- scan：各點的種子改用 H，不再用 `cmd_scan` 的 `[s0, s1 + k]`。
- 檢查：`validate_manifest` 只拒絕同一 manifest 內的重複種子；`check_geant4_study.py` 另外檢查一個研究的所有 run record 中，種子對不得重複。

**bootstrap**（用於平均、分位數、比例）。
- Poisson(1) 權重由 64 位元計數器雜湊（study_seed、run_id、chunk_id、event_id、replica_id）產生，以反 CDF 轉換。
- R ≥ 400。
- `summarize` 檢查事件鍵是否重複。

**證據相關性（D7）。** `extension.study.evidence_overlap` 列出被多個判定共用的 run，附 `evidence_overlap_version`。

**execution trace。** 新的共用函式呼叫 `trace.tag()`（小寫連字號名稱）：範圍比對 `geant4-scope-kind`、configuration 推導 `geant4-configuration`、IUT 閘門 `geant4-convergence-iut`、子 run MPV `geant4-mpv-subrun`、種子雜湊 `geant4-seed-hash`。advisory 掃描目前還不讀 tag，但之後的 advisory 可以用它判斷受影響的程式是否執行過。`check_geant4_study.py` 改 import `contracts.validate` 後，study record 的 `code_paths` 會多出 `contracts/validate.py` 等，這是預期的變化。階段 2 起，子 run MPV 與 bootstrap 改在 `simstat`（另一個行程）中執行，對應的 tag 由呼叫它的 Python 介面記錄（5.8）。

### 4.6 其他修正

- study spec 的 benchmark enum 補上 `shower-containment` 與 `longitudinal-profile`（D8）。D8 本身在執行時沒有作用：目前沒有程式以 schema 驗證 study spec，spec 中的 `grade` 也不會被讀取；這是一致性修正。
- study spec 的 observable kind enum 加入 `shower-maximum`；`validation_plan.scope` 加入 `observable_kind`。
- `ext_computational_run.json` 加入選用的自由格式屬性 `simulation`（schema 擁有者 hep-computing 需同意），讓 advisory 可以用它作為鍵。
- D10：`test_geant4_upgrade` 與 `test_simulated_dataset` 不再共用會被刪除的暫存目錄（各自建立重播，或改為 package 層級的 fixture）。
- protocol 第 4 節加入（D6）：停止規則、掃描格點、unresolved 的處理方式必須在第一個證據 run 之前寫入 study spec。

### 4.7 版本與 sci-fix 流程

- **版本：contracts C1（minor）。** 現有所有閘控都設在 x.y.0；新增閘控規則族的先例（2.4.0、2.6.0、2.8.0、3.1.0、3.2.0）都是 minor。
- **ledger**：每個缺陷一筆，`changelog` 為結構化物件（`{"kind": "unreleased", ...}`）：

| 缺陷 | ledger 條目 | 等級 | 理由 |
|---|---|---|---|
| D1 | scope-kind | S2 | 改變判定 |
| D2 | grade-table | S2 | 改變判定 |
| D3 | control-shift | S2 | 改變判定 |
| D4 | gate-IUT | S2 | 改變判定 |
| D5 | MPV-subrun | **S1** | 改變回報的數值（MPV 與其 SE） |
| D6 | stopping-rule | S3 | 只是指引 |

- **證據**：S2 至少 C2；S1 需 C3 與 D2。證據測試透過 `validate.py` 與 `check_geant4_study.py` 的命令列執行，才能在 parent commit 上執行（`docs/maintenance.md` 的 D2 層級，不是本文的缺陷 D2）；無法在 parent 上執行的寫入 `gaps`。
- **advisory**：`scifix_advisories.py check` 要求 advisory 的等級和它列出的每個 ledger 條目相同，所以 S1 與 S2 各發一份（編號取合併時下一個未使用者；目前為 SFA-2026-038 與 -039）。
  - 鍵：`artifact_types: [computational-run]`、`extension_keys: ["study", "evidence_records"]`（兩者都是選用欄位，可以區分）。
  - 範圍：introduced 0.20.0，附 `database_specific.introduced_basis`（0.19.0 已有 `contracts/validate.py`）；受影響的版本為 0.20.0–0.23.x 與未發布的版本。
  - simulated dataset-record 無法用鍵區分：`status`、`observable` 是必填欄位，而掃描只看鍵是否存在、不看值。remedy 要求持有者對每個 simulated 表格執行 `contracts/dependencies.py`，從輸入鏈找到受影響的 study record。以值比對的掃描是另一項工具變更。
- 0.20.0 以後產生、帶 `validated-in-scope` 的 study record 缺少 kind 與 configuration，在 `--strict` 下會失敗；advisory 說明處理方式（以新版本重產）。

### 4.8 階段 1 驗收

- [ ] kind 不符、宣告缺少維度、等級和契約表不符、configuration 缺少或為 `embedded`、`target_geometry_sha256` 不符的紀錄，在 `--strict` 與 C1 下被拒；`dependencies.py` 重新推導的 configuration 與紀錄不符時被拒；純量範圍正確比對。
- [ ] 重產的 J14 study record（含 kind、configuration）通過 `validate.py --strict` 與 `dependencies.py`。
- [ ] negative control 以觀測量位移判定，正負兩個方向都有測試。
- [ ] 閘門 toy 測試（每格 10⁴ 次）：真實差值 = tol 時通過率 ≤ 0.05 + 3σ_MC；真實差值 = 0 時通過率 ≥ 0.97；失敗率（m = 1、6、30）和 4.5 的表一致到 3σ_MC 內；unresolved 以 exit 3 回報。
- [ ] MPV：在 J14 的同一個 N 下，比較子 run 平均與全樣本 MPV 的差值，以及子 run SE 與 bootstrap SE；結果記錄在 VALIDATION。
- [ ] 4.1–4.3 的 J14 重產以離線重播完成（原型已示範）；4.4 負向控制組與 4.5 子 run 以 live 重錄完成。
- [ ] D10 修正後，`python3 -m unittest discover -s tests/contracts -t .` 沒有錯誤。
- [ ] J14 在 E2 重錄後，每個 reference benchmark 的控制組仍在 `|shift| ≤ 1.1 × DL` 內被抓到；若不成立，以新的偵測極限重新設計控制組，並記錄原因。
- [ ] 六筆 ledger 條目、兩份 advisory（S1、S2）通過 `scifix_advisories.py check`、parent record 齊全；live Geant4 證據以 release-gate 執行記錄；VALIDATION 條目 GEANT4-CORRECTNESS；CHANGELOG；release manifest。

---

## 5. 階段 2：C++ 計算核心（adapter 0.2.0）

### 5.1 範圍

所有會影響 J14 的 C++ 工作都在這一階段完成：spec/2 讀取、scorer 元件化、探針、column map，以及把觀測量與統計量的計算從 Python 移到新的 `simcore`（5.8）。場區與平面穿越在階段 3 加入（混合材料 0.21.0 已有）；它們會改變之後 live 重跑的 J14 `sources_sha256`，這是預期的變化，已提交的 J14 紀錄不重錄。

### 5.2 spec/2 的座標與格式

- 座標以世界中心為原點，堆疊軸為 x。
- `at_mm` 是元件**前表面**的 x 座標（世界座標）。子體的 `at_mm` 也是世界座標，必須落在母體範圍內。
- 巢狀只允許一層。
- schema 只用 `contracts/schema.py` 支援的關鍵字（含本階段新增的三個）。

### 5.3 spec/1 → spec/2 轉換與逐位元相同

| 因素 | 影響 | 轉換規則 |
|---|---|---|
| 材料建立 | **有**（混合材料以 `G4Material::AddMaterial` 依序加入成分；順序決定材料內元素向量的順序，模型依亂數抽選元素時依這個順序，所以會改變事件，不只是質量分率的浮點累加） | 轉換保留 `materials[]` 與 `components[]` 的順序，數值以 `%.17g` 輸出 |
| 放置位置 | **有**：差一個 ulp 就會改變步長 | 轉換在 C++ 的 `simspec convert` 中進行，沿用舊 `Detector.cc` 的運算順序（`stack = Σ repeat × Σt`、`world = world_scale × stack` 或 `world.size_mm`、`x = −stack/2`、`center = x + t/2`、`x += t`），以 `%.17g` 輸出；新 `Detector.cc` 以 `at + t/2` 求中心。同一種語言、同一套 double 運算，比在 Python 中重現浮點順序可靠 |
| `shift_mm ≠ 0` | **有** | `(x + t/2) + shift` 和 `(x + shift) + t/2` 不保證逐位元相同；只對 `shift = 0` 保證（J14 與 mirror 都是 0），其他情況做統計比對 |
| 粒子源位置 | **有** | `gun_world_fraction × world 長度`，以相同順序計算後寫入 |
| physics list 組成 | **有** | `G4StepLimiterPhysics` 只在 `step_limit_mm > 0`、`min_ekin_MeV > 0` 或（階段 3）有場時加入 |
| 子體放置順序 | 低 | 保持原順序 |
| 材料與 region 建立順序 | 低（只影響 couple 編號） | 保持原順序 |
| 體積名稱、copy number | **無**（只影響輸出欄名） | 保持不變 |
| overlap 檢查 | **無**（使用獨立的 `G4QuickRand`） | — |
| 輸出欄位集合與順序 | 影響比對 | spec/1 轉換來的 spec 啟用舊 scorer 集合，順序和 `CsvColumns` 相同 |

**驗收：** 在同一主機、同一 Geant4 build 上，階段 2 開始前的 layered_sim 與新版對 TestEm3、TestEm5 mirror 與 J14 spec 產生逐位元相同的 CSV（同種子、serial），而且兩版每個放置的 hex-float 傾印（名稱、copy number、平移、母體）完全相同。跨主機只做統計比對；已提交的 J14 CSV 不作為逐位元參考。

### 5.4 hep-detector 的雙格式支援

J14 的已記錄紀錄必須永遠可以重播，所以 Python 的介面與判斷層永久能讀 spec/1 與 spec/2 的幾何事實（元件、厚度、材料；不計算位置）；`layered_sim` 只讀 spec/2，spec/1 一律先經 `simspec convert`。

| 位置 | 變更 |
|---|---|
| run record | 記錄 `spec_sha256`（使用者給的 spec）與 `effective_spec_sha256`（C++ 執行的 spec/2） |
| `check_records` | 比對 study 中的 spec 和 run 的 `spec_sha256` |
| 幾何存取器（新模組 `core/geometry/layered.py`，steward hep-detector，登記於 `core/OWNERS.json`） | 從 `layers` 或 `elements` 取得元件清單、最小厚度、材料；`check_geant4_study.py`、`geant4_benchmarks.py`、`geant4_verify.py` 共用（skill 腳本與 adapter 只能 import `core`、`contracts`）；以 J14 紀錄測試 |
| `derived()` | `min_thickness_mm` 經存取器計算；加測試確保 `G4R-THIN-FLUCT`、`G4R-THIN-CUT-SCAN` 在兩種格式下都觸發 |
| `cmd_summarize` | 改為讀取 `simstat summarize` 的輸出，不再在 Python 中計算統計量；粒子源能量從 run record 的 `extension.simulation.gun` 讀取；定義 spec/2 的 gun 欄位（`energy_MeV`，階段 3 起另有 `ekin_per_nucleon_MeV`） |
| `geant4_verify.py` | 體積計數（overlaps）與物質預算（budget）經存取器讀取；能量平衡的逐事件殘差由 `simstat balance` 計算，Python 只做判定 |
| study spec schema | `$comment` 改為接受 `layered_sim.spec/1` 或 `/2` |

### 5.5 schema 驗證

- 擴充 `contracts/schema.py`：`maxItems`、`maximum`、`exclusiveMaximum`（目前的 `SUPPORTED_KEYWORDS` 仍沒有這三個；layered_sim 的 schema 已用到全部三個）。更新 `SUPPORTED_KEYWORDS`，並擴充 `tests/contracts/test_schema_keywords.py`，讓它也掃描 adapter 的 schema（現在只掃描 `contracts/schemas/*.json`）。
- `geant4_run.py` 改用 `contracts.schema.validate()`。原 `validate_spec()`（行 103）中 schema 表達不了的跨欄位規則保留為 `cross_field_checks()`，包括：混合材料的 components 與 z/a_g_mole 擇一、至少兩個成分、質量分率和為 1、成分只能引用 NIST 或先前定義的材料；slab 名稱重用時材料與厚度必須一致、world 的 scale 與 size 恰好擇一、`reference_list` 與 `em_constructor` 擇一、region 的 slab 名稱存在、禁用的 UI 指令、粒子源位置範圍。
- C++（`layered_sim`、`simspec`）只檢查執行所需的最低限度；schema 與跨欄位規則的判定在 Python 介面。
- contracts **不升版**：沒有任何契約 schema 使用新增的關鍵字。

### 5.6 探針與 column map

**探針（`Probe.hh`）：**

| 項目 | 規格 |
|---|---|
| 時機 | master 的 `BeginOfRunAction`；狀態為 `G4State_GeomClosed` 且 couple 數大於 0；否則寫入 `effective_config: {"recorded": false, "reason": ...}`，layered_sim 照常以 exit 0 結束（不用「refused」：在 `core/status.py` 中它表示負向判定）。依 11.4.3 原始碼，這時物理表已建好；fake run（`/run/beamOn 0`）會在 `BeginOfRunAction` 之前返回，所以探針不會執行 |
| 頻率 | 每個 run 一次 |
| 執行緒 | 只在 master；輸出註明「workers assumed identical」 |
| EM 參數 | `G4EmParameters::StreamInfo(os)` 全文加上解析出的欄位；不用 `Dump()`（11.4.3 中每個行程只印一次） |
| cut | 逐 material-cuts couple：材料、region、range cut、各粒子的能量閾值 |
| 強子模型 | 逐 process、逐模型，以材料與元素查詢能量範圍；重疊區間標示為隨機選擇 |
| run manager | 型別、`seedOncePerCommunication`、`G4RUN_MANAGER_TYPE`；SubEvt 或非 0 的種子模式回報 gap |
| 其他 | `G4UserLimits`、biasing、資料集路徑與內容雜湊 |
| 路徑 | 經 `tilde()` 寫出（`check_packaging.py` 會掃描所有文字檔） |
| 版本 | 11.4.x；附 `probe_version` |
| 輸出位置 | `extension.simulation.effective_config` |

規則與 variation 的模型指派優先讀探針，讀不到才退回宣告，並輸出 `source: probe | declared`；兩者都有而不一致時報錯。

**測試觸發**：加一個只在測試建置中存在的 UI 指令，在 `/run/initialize` 之後、第一次 `BeamOn` 之前呼叫探針，必須寫出 `recorded: false`。

**column map：**
- 檔名 `column_map.json`，schema `layered_sim.output/2`，和 `output.schema.json` 一起放在 adapter。
- layered_sim 在每個 run 自動輸出，雜湊寫入 run record。
- 每個欄位包含：語意名稱、實際欄名、單位、操作定義；附 `column_map_version`。
- 使用者自己的應用可以手寫同格式的對照檔；只允許宣告式運算（改名、單位換算、加總、篩選）。需要計算的轉換必須是另一個有紀錄的步驟。

### 5.7 adapter 變更流程

| 項目 | 內容 |
|---|---|
| 版本 | 0.1.0 → 0.2.0 |
| `adapter.json` | `assets` 加入新檔；更新 `purpose`；`status` 維持 `demonstrated-on-synthetic-data` |
| `SIM_SOURCES` | 加入 `Scorers.*`、`Probe.hh`；另設 `SIMCORE_SOURCES` 記錄 `simcore` 的原始碼（否則 `sources_sha256` 會遺漏新原始碼） |
| G5 | 聲明「依 Geant4 API 撰寫，未複製或改寫任何範例程式碼」，由審查者在 VALIDATION 條目中確認 |
| 測試 | `tests/adapters/test_geant4.py` 的 assets 檢查；離線測試；`HEP_GEANT4_LIVE_TEST=1` 的 live 測試；`simcore` 的 ctest 與等價測試（不需 Geant4） |
| CI | 新增必要的 `simcore` 工作：以 C++17 編譯器建置，執行 ctest 與等價測試 |
| 文件 | `docs/capability-matrix.md` 的 Geant4 列 |

### 5.8 C++ 計算核心 `simcore`

| 項目 | 規格 |
|---|---|
| 位置 | `adapters/geant4/assets/simcore/`（CMake 專案；adapter 的擁有者 hep-detector） |
| 依賴 | C++17 標準函式庫與既有的 `MiniJson.hh`；不連結 Geant4，不用第三方函式庫 |
| 執行檔 | `simspec`、`simstat`（本階段）；`simreco`（階段 3） |
| 介面 | 輸入：spec、CSV、column map、參數 JSON；輸出：一個 JSON 物件（stdout 或 `--out`），含 `status`、`program`（名稱、版本、編譯器）與結果 |
| 退出碼 | 依 `core/status.py`：0 ok、1 負向判定、2 無法使用的輸入（`rejected`）、3 incomplete；不用其他退出碼 |
| 數值 | double；加總採用與順序無關的方式（先排序或補償加總），結果不受執行緒與 chunk 順序影響；亂數只用計數器雜湊（SplitMix64），不用標準函式庫的 `<random>` 分布（各實作的輸出不同） |
| 輸出精度 | 浮點以 `%.17g` 寫出，可無損還原 |

`simstat` 的子命令（取代原本在 Python 中的計算）：

| 子命令 | 內容 | 取代 |
|---|---|---|
| `summarize` | 逐 run 的觀測量：平均沉積、尾端比例、洩漏比例、MPV（固定分格寬度）、穿透主粒子的 E_in − E_exit；經 column map 讀欄位 | `check_geant4_study.py summarize` 的計算；`geant4_benchmarks.py` 中 Geant4 端的統計量 |
| `subrun` | 各 chunk CSV 的 MPV、其平均與 sd/√K | 4.5 的子 run 估計量 |
| `bootstrap` | Poisson(1) 計數器雜湊權重下的 SE（平均、分位數、比例）；同一事件的所有觀測量共用權重 | `bootstrap()` |
| `diff` | 兩個掃描點之間觀測量的差值與差值的 SE | `convergence()` 的數值部分；判定留在 Python |
| `balance` | 逐事件的能量平衡殘差 | `geant4_verify.py balance` 的數值部分 |

**遷移與等價。** 階段 1 的 Python 估計量移到 `tests/`，只作為 oracle，不再出現在正式程式中。等價測試以 J14 的 recorded CSV 比較 `simstat` 與 Python oracle：計數完全相同、MPV 選到相同的分格、其他浮點的相對差 ≤ 1e-12（加總順序不同所致）。日後任一邊改了演算法，另一邊仍是獨立實作。

**為什麼不用 Python 綁定。** 獨立執行檔讓 Python 端維持只用標準函式庫、不需編譯；輸出是有雜湊的檔案，可以直接進入 provenance；G5 的核准文字不必改。

**trace。** `simcore` 在另一個行程執行，不會出現在 `code_paths`。呼叫它的 Python 介面在紀錄中寫入執行檔與原始碼的 sha256、版本與子命令，並以 `trace.tag()` 標記（例如 `geant4-simstat`）。

### 5.9 階段 2 驗收

- [ ] 以 `simspec convert` 轉換後的新 `layered_sim` 與階段 2 開始前的 layered_sim：5.3 的同主機逐位元相同，以及放置傾印完全相同。
- [ ] `simcore` 在 CI 的必要工作中建置，ctest 通過；等價測試在 J14 的 recorded CSV 上通過（計數相同、MPV 分格相同、其他相對差 ≤ 1e-12）。
- [ ] hep-detector 與 adapter 的 Python 正式程式中不再有觀測量與統計量的計算（測試確認 `mpv(`、`bootstrap(` 只出現在 `tests/`）。
- [ ] J14 經存取器讀取 spec/1 與 spec/2 結果一致；兩條薄層規則在兩種格式下都觸發。
- [ ] 探針在測試指令觸發的錯誤時機寫出 `recorded: false`；J14 每個 run 都有 `effective_config`；與宣告一致，故意製造的不一致被抓到。
- [ ] 一個只改欄名的假後端加上手寫 column map，通過 J14 的 summarize、閘門、benchmark。
- [ ] `contracts.schema.validate()` 加 `cross_field_checks()` 對一組合法與非法 spec 的結論，和原 `validate_spec()` 及 C++ 一致。
- [ ] J14 在 E2 重錄一次；VALIDATION 條目 GEANT4-CORE；CHANGELOG；release manifest。

---

## 6. 階段 3：J15 最小磁譜儀（adapter 0.3.0，contracts C2）

### 6.1 幾何

座標：世界中心為原點，堆疊軸 x，單位 mm。

**磁場：B = (0, 0, +0.5 T)。** 偏轉平面為 x–y，非偏轉方向為 z。正電荷沿 +x 運動時偏向 −y；μ⁻ 偏向 +y。

```
x:  −1000   −810 … −780   −520 −500        …         300  320    490 … 520   550          900   ±1200
     gun    TOF1（兩層）   │ Si1  Si2  Si3  Si4  Si5  Si6  │     TOF2（兩層）  量能器 50 層    世界邊界
            10 + 10 mm    │◄────── 均勻場 0.5 T ẑ（−520 … 320）─────►│     10 + 10 mm   Pb 2 / PVT 5 mm
```

| 元件 | 材料 | 前表面 `at_mm` | 厚度 | 範圍 | 橫向（y × z） |
|---|---|---|---|---|---|
| 世界 | `G4_Galactic` | — | 2400 | −1200 … 1200 | 1200 × 1200 |
| 粒子源 | — | x = −1000，y = z = 0 | — | — | — |
| TOF1a、TOF1b | `G4_PLASTIC_SC_VINYLTOLUENE` | −810、−790 | 各 10 | −810 … −800、−790 … −780 | 300 × 300 |
| 場區母體 | `G4_Galactic` | −520 | 840 | −520 … 320 | 300 × 300 |
| Si1–Si6（子體） | `G4_Si` | −500.15 + 160k | 0.3 | 中心 −500、−340、−180、−20、140、300 | 200 × 200 |
| TOF2a、TOF2b | `G4_PLASTIC_SC_VINYLTOLUENE`（和 TOF1 相同） | 490、510 | 各 10 | 490 … 500、510 … 520 | 400 × 400 |
| 量能器 | 50 × (`G4_Pb` 2 + PVT 5) | 550 | 350 | 550 … 900 | 500 × 500 |

**TOF 站。** TOF1 與 TOF2 各由兩層組成；四層都是同一種材料（`G4_PLASTIC_SC_VINYLTOLUENE`）、同一厚度（10 mm），每站兩層之間有 10 mm 的真空間隙。每層是一整片平板，不分割、不設 paddle 方向（刻意的簡化）；兩層的作用是提供兩次獨立的時間量測與 dE/dx 取樣，並讓同站兩層之間的一致性成為一項檢查（6.6）。

核對（附錄 A 的程式）：
- 量測臂長 L = 0.800 m；Si1 前緣和 Si6 後緣距母體邊界各 19.85 mm。
- 場在量測區兩端各多延伸 20 mm。
- TOF 站中心（兩層的中點：−795、505 mm）之間的距離 D = 1.300 m，和單層設計相同。
- TOF2 後層的後表面（520）距量能器前表面（550）30 mm；TOF1 前層（−810）在粒子源（−1000）之後。
- 世界包含粒子源與量能器後端。

材料（11.4.3 的 NIST 定義對照 PDG）：`G4_PLASTIC_SC_VINYLTOLUENE` 為 1.032 g/cm³、I = 64.7 eV，和 PDG 一致；`G4_Si` 為 2.33 g/cm³（PDG 2.329）。

### 6.2 參數與接受度

| 參數 | 值 | 依據 |
|---|---|---|
| B | 0.5 T | 多重散射項等於量測項的剛度約 16–22 GV（μ），與 B 無關。0.5 T 讓 1–10 GV 與 100–1000 GV 各有一個十倍區間 |
| Si 層數 | 6 | N = 4 時偏轉平面只有 1 個自由度；N = 8 的 MDR 只改善約 8 % |
| MDR | 約 1172 GV | 只算量測項時 σ_R/R = 1。參考值取自 `tracker_resolution.py` 的精確最小平方（常數 0.2998）。`multiple_scattering.py` 的 `mdr_intrinsic_only_gv` 是同一定義，但仍以 Gluckstern 近似計算（N = 6 時約 1131 GV）；0.21.0 起它另外輸出 `intrinsic_coefficient`（含本提案使用的精確係數）並在 N < 10 時警告 |
| TOF | 每站兩層；σβ/β ≈ 2.3 %（每層 100 ps、兩層獨立、β = 1；每站一層時為 3.3 %） | D = 1.3 m；站時間取兩層平均，σ_站 = σ_層 / √2 |
| 量能器 | 18.4 X₀、0.886 λ_I、寬 50 cm | 0.89 λ_I 足以用簇射形狀分離 e/p，不足以量強子能量 |

**多重散射項。** 這裡的設計估計用 Highland 公式，對總厚度取 log 項，再乘 1.0–1.4 的係數。審查以離散散射平面做精確最小平方，得到的係數為 1.02（加權擬合）到 1.06（不加權）。plugin 的 `multiple_scattering.py` 依其約定**不含** log 項；兩種約定的差異在比較時要寫明。

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

整體門檻為 0.75 GV；只要求徑跡加 TOF 時為 0.51 GV。低於 0.364 GV 的軌跡會從場區側面離開，之後在無場的世界中走直線。

電子：簇射軸在 1 GeV 時於量能器前、後表面分別偏離 82 mm 與 127 mm，5 GeV 時為 16 mm 與 25 mm。上游 11.3 % X₀（四層 TOF 佔 83 %）產生的軔致輻射光子不受偏轉，所以簇射軸不是直線外推；79 mm 的邊距是以幾何估計的，上游物質比單層設計多一倍，簇射檢查要以實際的橫向能量分布核對。電子的簇射檢查限 1 GeV 以上。

**上游能損**（Bethe 積分，TOF1 兩層共 2 cm PVT）：

| 質子剛度 | 動能 | TOF1 能損（兩層） | Δp/p | β 在兩個 TOF 站中心之間的變化 |
|---|---|---|---|---|
| 0.6 GV | 175 MeV | 10.23 MeV | 3.20 % | 2.87 % |
| 1 GV | 433 MeV | 6.00 MeV | 0.82 % | 0.46 % |
| 2 GV | 1271 MeV | 4.34 MeV | 0.24 % | 0.05 % |

0.6 GV 時 β 在兩站之間變化 2.87 %，已大於 TOF 的解析度（2.3 %）：TOF 量到的是路徑上的平均 β，所以低剛度的 β 比較要用含能損的 β 模型，或限於 2 GV 以上。TOF1 在第一片 Si 之前，只改變入射方向與動量，不影響曲率解析度；剛度真值取自 Si 平面的穿越紀錄，不受 TOF1 加厚影響。

**不能沿用 J14。** J15 的 Si 平面和 J14 的材料（`G4_Si` 對 `Si_study`）、物理設定、cut 都不同，而且 J15 只記錄入射，組不出 J14 的 E_in − E_exit 觀測量。

### 6.3 場的實作

- 在 `ConstructSDandField` 中建立 `G4UniformMagField`、`G4FieldManager`、`G4ChordFinder`，以 `G4ThreadLocal` 儲存；master 與每個 worker 各有一份。在 `Construct()` 中建立會讓 worker 共用非執行緒安全的 chord finder。
- 以 `SetFieldManager(fm, true)` 附在場區母體上，傳遞到所有子體。
- 依 API 撰寫，不複製或改寫 B5 範例的程式碼（G5）。
- stepper 類別寫入 spec，並由探針記錄（使用 helix stepper 會讓場傳輸檢查變得沒有意義）。

| 參數 | 名義值 | 備註 |
|---|---|---|
| `delta_chord_mm` | 0.25 | 最大步長小於約 80 mm 時不起作用，只記錄不掃描 |
| `delta_one_step_mm` | 0.01 | 均勻場中 Runge–Kutta 的截斷誤差遠小於交點誤差，預期掃描無影響；做一次確認 |
| `delta_intersection_mm` | **1e-5**（0.01 µm） | 決定穿越點的精度 |
| `min_epsilon_step` | 5e-5 | |
| `max_epsilon_step` | 1e-3 | epsilon = delta one step / 步長，會被夾在這個上限 |
| `max_step_mm` | 10 | 需要 `G4StepLimiterPhysics`；`G4UserLimits` 必須逐體積設定，不會傳遞到子體 |
| `stepper` | DormandPrince745 | 11.4.3 `G4FieldParameters` 的預設 |

探針：走訪 `G4LogicalVolumeStore`，以 `GetFieldManager()` 讀回 B、chord finder 與各精度參數；依指標去重，記錄原始附加的體積；註明 master 只看到 master 的副本。

**MT 測試**：只在測試建置中存在的 UI 指令，回報每個執行緒的 field manager 指標，必須彼此不同。

### 6.4 其他新功能

| 功能 | 規格 |
|---|---|
| 混合材料 | 0.21.0 已支援（`materials[].components`），J15 不需新增；PVT 與 Pb 都直接用 NIST 材料 |
| 平面穿越 scorer | 主粒子（track ID 1）在 tracker 或 tof 平面**第一次**進入時（前步點狀態為 `fGeomBoundary` 且所在體積為該平面），記錄前步點的位置、方向、動能、全域時間、PDG 碼；每個平面一個「已記錄」旗標。粒子源若位於平面內，不會出現 `fGeomBoundary`，填缺值 |
| 輸出 | 逐事件 CSV；平面穿越紀錄共 10 片（6 片 Si、4 層 TOF）；量能器的逐層欄位可關閉；column map 自動產生 |

**刻意的簡化**：均勻場與銳利邊界、無磁鐵材料、矽為整片平面（無條帶、無電荷分享、未模擬 δ 射線造成的重心偏移）、TOF 每層不分割（無 paddle、無方向）、無光學光子、無觸發與讀出電子學。J15 的 README 逐條列出。

### 6.5 數位化與重建

數位化與重建在 C++ 的 `simreco` 中進行，由 Python 介面 `geant4_run.py reco` 呼叫；參數（ε、σ_t、名義 B、標定樣本）寫在 hep-detector 擁有的 reco spec 中。hep-detector 不新增腳本。

| 步驟 | 內容 |
|---|---|
| 矽 | 穿越點加高斯誤差：偏轉方向（y）ε = 10 µm，非偏轉方向（z）30 µm；擬合使用的 x 和 scorer 相同（入射面） |
| TOF | 每層的時間加獨立的高斯誤差 σ_t = 100 ps；站時間 = 兩層時間的平均（先以擬合軌跡把兩層的時間換算到站中心）；另外輸出每層的 dE/dx 與同站兩層的時間差 |
| 徑跡 | x–y 平面圓擬合，含多重散射共變異（否則 1 GV 時 χ²/dof 上千）；x–z 平面直線擬合；輸出 R、χ²、自由度；使用名義 B |
| 剛度真值 | 六片平面穿越紀錄的 C·B / p_T,i 取平均（C = 0.2998），使用橫向動量 |
| β | 路徑長以兩站中心為端點，包含 TOF1→Si1、Si6→TOF2 的直線段與三維傾角；低 β 時回報 β 在兩站之間的變化 |
| 量能器 | 主動層總沉積除以**電子**取樣比例；取樣比例由 `calibration` 角色的 10 GeV 電子樣本求得；另外輸出 e/mip |
| 亂數 | 計數器雜湊，和 Geant4 的亂數流分開 |

`geant4_run.py reco` 每次執行寫一份 computational-run 紀錄（含 `**trace.provenance()` 與 `simreco` 的程式雜湊），輸入為 adapter 的 run record（含雜湊）。改變數位化參數不需要重跑模擬。`simreco` 與 `geant4_run.py reco` 的退出碼都依 `core/status.py`：0 ok、1 負向判定、2 `rejected`（無法讀取的輸入，含缺檔）、3 incomplete；`reco` 在 `tests/skills/test_cli_robustness.py` 的 `MISSING_FILE_ARGS` 登記。

重建後的結果表（例如剛度解析度對剛度）以 **simulated dataset-record** 發布，由 `geant4_run.py table` 寫出（含 `trace.provenance()`）。目前 `dependencies.py` 要求 simulated 表格的每個輸入都是帶 `extension.simulation` 或 `extension.study` 的 computational-run，而重建紀錄兩者都沒有；只列原始 run record 又會讓改變數值的步驟不在輸入鏈中。所以 C2 新增一個標記（例如 `extension.derived_from_simulation`），接受「輸入全是模擬 run 的 computational-run」作為 simulated 表格的輸入。J15 的 study record 是 `unvalidated`，表格保持 `unvalidated`；使用它的 communication 會得到 `communication.simulated_source` 警告，圖表標示「Simulation」。

### 6.6 驗證梯

| 檢查 | 等級 | 參考 | 規格 | negative control |
|---|---|---|---|---|
| overlap | 實作 | — | — | 平移一片 Si 造成重疊 |
| 逐事件能量平衡（J15 幾何） | 實作 | 能量守恆 | — | 不加 2 mₑc²、重複計入 |
| 物質預算（geantino） | 實作 | PDG X₀ 加總 | 容許約 2 %（Geant4 的 X₀ 公式和 PDG 約差 1 %）；用來抓幾何與材料指定錯誤 | Pb 密度 ± δ |
| `field-propagation` | **verification** | charged geantino 對解析螺旋（檢驗數值積分精度） | 見 6.7 | Geant4 端 B × (1 ± δ) |
| `field-propagation-muon` | **sanity** | 平面平均的 1/R 真值（6.5） | μ⁻ 1、10、100 GV；容許 = t·SE + 0.05 %；N ≈ 400（1 GV）、≈ 7400（100 GV） | Geant4 端 B × (1 ± 1 %) |
| 擬合器單元測試 | 測試（不是 benchmark） | 玩具真值（R ≥ 300 GV）：`simreco` 的 C++ 擬合對 Python 的 `tracker_resolution.py`（獨立實作） | — | — |
| 多重散射一次性比較 | sanity | `multiple_scattering.py` 的解析項（不含 log，依其約定）；可另用 `toy_spectrometer.py`（需 NumPy） | μ 與 p，1–10 GV，含 β | — |
| `tof-beta` | **verification**（bookkeeping） | 沿真實軌跡的運動學 | — | scorer 測試旗標注入時間偏移；沒有 Geant4 端的物理控制組，文件中註明 |
| `tof-layer-consistency` | **verification**（bookkeeping） | 同站兩層的時間差對「層間路徑長 / βc」（β = 1、正入射時 66.7 ps） | 殘差平均為 0；寬度為 √2 σ_t（100 ps 時 141 ps） | 以測試旗標在一層的 scorer 時間注入偏移 |
| `sampling-fraction` | sanity | PDG 的 μ 能損表（Groom 等，透過 hep-citations 取得）在 run 動量下的游離 dE/dx 比 | μ⁻ 1 GeV；統計量為 Σ PVT 沉積 / Σ（PVT + Pb）沉積；合理範圍 ±10 %（審查者的 Bethe 估計約 0.271）；和 `calibration` 樣本用不同種子 | PVT 密度 ± δ |
| 簇射包容 | sanity | PDG gamma 剖面，混合物有效臨界能約 10.2 MeV | 電子 1–100 GeV | — |
| `longitudinal-profile`（0.21.0） | 不適用 | 它的參考是已發表的 ALICE FoCal-E 量測，只對該堆疊有效；J15 的量能器不同，而且是 embedded | — | — |
| 選用：孤立 PVT 平板的 stopping power | reference（`configuration: isolated`） | Bethe（RPP 2024 式 34.5） | p、T = 200–600 MeV（βγ ≈ 0.67–1.37，低於 PVT 的 10^x₀ ≈ 1.40，所以密度修正為 0）、1 cm 平板、排除核作用（約 1 %）；Sternheimer 參數須取自 Sternheimer, Berger & Seltzer (1984) 並以 hep-citations 核對 | PVT 密度 ± δ |

選用的最後一項在孤立平板中執行，不是 J15 探測器的一部分，用來示範新材料的升級路徑。

### 6.7 收斂掃描

**場精度與最大步長（確定性，不需統計）：**
- 軌跡：charged geantino（質量 0，β = 1），剛度 0.6、1、10、100、1000 GV。
- 方向：正入射；偏轉平面內 **50 mrad，方向和偏轉相反**（正電荷取 +y）；非偏轉平面 ±50 mrad。
- 附錄 A 核對：在這組方向下，每條軌跡都到達每片 Si 和 TOF2 的兩層，也不離開場區母體。若改成順偏轉方向，0.6 GV 和 1 GV 會錯過 Si6。
- 參考：解析螺旋；若軌跡離開場區，參考改為分段直線，只比較解析軌跡實際到達的平面。

| 掃描 | 格點 | 判定 |
|---|---|---|
| delta intersection | 1e-3、1e-4、1e-5、1e-6 mm | 名義值（1e-5）下，所有平面的平面內距離 √(Δy² + Δz²) ≤ 0.5 µm（ε/20）；最細兩組相差 ≤ 0.2 µm；1e-3 mm 預期不通過 |
| 最大步長 | 100、30、10、3 mm | 同上 |
| delta one step 與 epsilon | 名義值與 1/10 | 預期無變化，做一次確認 |
| TOF2 路徑時間（兩層） | — | \|Δt\| ≤ 1 ps（約 0.3 mm 路徑長），只檢驗路徑長 |

**量能器 production cut：**
- 格點：0.1、0.3、0.7、1.0 mm。
- 樣本：10 GeV e⁻；先跑 trial，再依 4.5 決定 N。
- 觀測量：總沉積（相對容許 1 %，約 400 個簇射/點）、後漏比例（以既有的 `leak_rear_MeV` 計算，只算後表面；**絕對**容許 0.002，約 5000 個簇射/點）。
- 每點事件數取兩者的較大值。
- 判定依 4.5。

Si 的 production cut 不在 J15 收斂：它只影響 Si 的沉積，而 J15 的 Si 結果不作為證據。study spec 的 `convergence_plan.observables` enum 目前只有四個薄層觀測量，階段 3 加入總沉積與後漏比例。各 benchmark 依賴的參數組在 study spec 中事先宣告，並以探針的實際設定核對。

### 6.8 variation

| variation | 範圍 | 規則 |
|---|---|---|
| EM option4 對 option3 | 量能器剖面、取樣比例 | `G4R-PRECISION-EM` |
| FTFP_BERT_EMZ 對 **QGSP_BIC_EMZ** | 只看量能器中的作用機率與第一次作用深度；1.5 GeV 以下核子 | `G4R-BIC-RANGE`；3 GeV 以下 π、6–12 GeV 強子兩者模型相同，不得作為 variation |
| 真空對空氣 | 多重散射、剛度解析度 | — |

### 6.9 label 與 contracts C2

- 契約的 benchmark 對照表加入 J15 的檢查，等級為 `verification` 或 `sanity`；只有 reference 會被 `_study_upgrade` 計入。
- 隔離規則已在階段 1（C1）生效（4.3）；J15 的所有 benchmark 都是 `embedded`，不會被計入。
- C2 另外包含：重建紀錄作為 simulated 表格輸入的標記（6.5）。
- **J15 的定位**：verification 載體。完整探測器中的所有結果都是 `unvalidated`，README 與 study record 都寫明。
- `geant4_benchmarks.py` 的 `GRADES` 與 study spec 的 grade enum 都加入 `verification`。

### 6.10 recorded 資料預算

- `check_packaging.py` 的單檔上限是 2 MiB；J14 的 `recorded/` 目前為 2,447,979 bytes（2.45 MB）。
- J15 約 200 欄的 CSV 每事件約 2 kB，10⁴ 事件約 20 MB，不能直接提交。
- J15 只提交：縮減欄位的重播檔（比照 J14 的 `REDUCED`）、數位化與重建的輸出、探針與 column map。
- 驗收：每檔 ≤ 2 MiB，J15 的 `recorded/` 總和 ≤ 3 MB。

### 6.11 註冊與文件

| 項目 | 內容 |
|---|---|
| 腳本計數 | hep-detector 不新增腳本（重建在 `simreco`，介面在 adapter），`DetectorScriptCount` 維持 21，`docs/capability-matrix.md` 行 47 不變 |
| CLI 登記 | `geant4_run.py reco`、`table` 在 `tests/skills/test_cli_robustness.py` 與 adapter 測試中登記；`simcore` 的原始碼列入 `adapter.json` 的 `assets` |
| 路由表 | 不需修改 `skills/hep-detector/SKILL.md`（沒有新腳本），quick load 不變；J15 與 `simcore` 的說明放在 `geant4-study-protocol.md` 與 adapter 文件 |
| journey | J15；`docs/researcher-journeys.md`、`docs/maintenance.md` 範例表；`tests/examples/test_geant4_minimal_spectrometer.py`（重播並和已提交輸出比對） |
| capability | `docs/capability-map`（在 `full-detector-simulation` 下新增項目，執行 `capability_map.py --write`）、`docs/capability-matrix.md` |
| 路由 | 新增 J15 的路由案例；0.21.0 起 `check_routing_static.py` 從 `docs/researcher-journeys.md` 讀取 journey 清單，所以 J15 一列入表就**必須**有路由案例。重跑 live 的 Geant4 案例，包括既有的繁中欠規格案例 `g4-underspec-2` |
| 描述長度 | hep-detector 的 description 目前 1,018 / 1,024 字元（`measure_entrypoints.py` 會完整量測折疊描述）；J15 的路由案例必須沿用描述中已有的觸發詞，不改描述 |
| 實驗名稱 | `check_layering.py` 不允許 `skills/`、`contracts/` 中出現實驗名稱（含 ALICE）；契約表與 protocol 引用 `longitudinal-profile` 的參考時用引用鍵 |
| 獨立審查 | 各階段的 Markdown（protocol 變更、J15 README、本提案）以 0.22.0 的 `review.py` 審查（`--lens-model design=<最強模型>`、`--filter-model`）；其紀錄只是 advisory，依 O04/O14 不取代人工的 G5 確認 |
| 共享 stanza | 文字**不改**（點 5 寫的是「3.1.0 upgrade rule」；修改會牽動全部 SKILL.md 與 live 路由重跑） |
| 其他 | `reference_inventory.py --check`、CHANGELOG、release manifest、adapter 0.3.0、`SIM_SOURCES` 加入 `FieldSetup.*`、`SIMCORE_SOURCES` 加入 `simreco` 的原始碼 |

### 6.12 階段 3 驗收

- [ ] J15 幾何通過 overlap、物質預算、逐事件能量平衡；6.1 與 6.2 的核對數值由測試重算。
- [ ] MT 測試指令回報的各執行緒 field manager 指標彼此不同；探針記錄的場參數和 spec 一致。
- [ ] 6.7 的確定性場檢查在名義值下通過；delta intersection 1e-3 mm 如預期不通過。
- [ ] `field-propagation`、`field-propagation-muon`、`tof-beta`、`tof-layer-consistency`、`sampling-fraction` 執行完成；各自的 negative control 依 6.6 被抓到，或註明沒有控制組。
- [ ] `simreco` 的擬合器單元測試以 Python 的 `tracker_resolution.py` 為參考通過；`simreco` 在 CI 的 `simcore` 工作中建置與測試。
- [ ] 隔離規則的契約測試：缺少 configuration、`embedded`、等級和契約表不符時，都被拒絕；J14 在 `--strict` 下仍通過。
- [ ] recorded 預算、註冊項目、文件全部完成；VALIDATION 條目 GEANT4-J15。
- [ ] 獨立 agent 只依文件與工具完成「1 GV 質子在 J15 的剛度解析度」：結果紀錄通過 `validate.py --strict`、label 為 `unvalidated`、解析度落在 6.2 表的範圍內，過程不需要維護者協助。

---

## 7. 刪除與延後

| 項目 | 決定 | 理由 / 觸發條件 |
|---|---|---|
| `uses-validated-physics` label | 刪除 | 雜湊太嚴也太鬆；會繞過範圍檢查 |
| `physics_config_comparison` 註記 | 延後 | 目前沒有使用者；J15 無法沿用 J14。觸發：出現需要比較物理設定的研究；屆時差異須經 `evidence_records` 取得 run record 的 `effective_config`，處理 `probe_version` 差異，缺少 `effective_config` 時一律失敗 |
| 依 SE 自適應停止、以加密掃描作為證據 | 刪除 | optional stopping 偏差 |
| 量測主導區 σ(1/R) 作為 benchmark | 刪除 | 改為擬合器單元測試 |
| C++ 雙軌幾何格式 | 刪除 | 改為由 C++ 的 `simspec convert` 先轉成 spec/2 |
| 新的 core 驗證器、重寫徑跡與多重散射公式 | 刪除 | 重用 `contracts/schema.py`、`tracker_resolution.py`、`multiple_scattering.py` |
| 欄位對照放進 contracts | 刪除 | 留在 adapter（`layered_sim.output/2`） |
| contracts 4.0 | 刪除 | 新增選用區塊與閘控規則屬 minor |
| 離子源與 Birks 可見能量（未來 J16） | 延後 | 觸發：有宇宙線核素研究需求，且 PVT 的 Birks 常數有文獻紀錄。實作時依 11.4.3：在 `GeneratePrimaries` 中以 `GetIon(Z, A)` 取得離子；在 `Construct` 設定 kB、PreInit 設定 `SetBirksActive(true)`，再以 `G4LossTableManager::Instance()->EmSaturation()` 取得 |
| 規則版本範圍、物理知識外移 | 延後 | 觸發：支援第二個 Geant4 版本 |
| benchmark registry | 延後 | 由契約對照表與 enum 一致性測試取代；觸發：benchmark 數量使測試不足 |
| `inspect` 與 Linux 環境 | 延後 | 觸發：有使用者需要在 CVMFS 或 LCG 上執行；需要新的環境編號 |
| GDML、field map、邊緣場 | 延後 | 觸發：研究需要真實幾何或場形 |
| 使用者應用後端、可嵌入探針 | 延後 | 觸發：第一個實驗組應用；需重新核准 G5 |
| ReferenceMaterial 契約 | 延後 | 觸發：第一個非平板幾何的 reference benchmark |
| 欄式輸出 | 延後 | 觸發：需要 per-hit 資料且 root-uproot adapter 可用 |
| 模擬內 bootstrap、內容定址快取、新執行器、replay 後端 | 刪除或延後 | 目前規模不需要；快取鍵難以完整 |
| Python 綁定（pybind11 等） | 不採用 | 使用者決定以獨立執行檔交換 JSON/CSV（2026-10-22） |
| `skills/hep-detector/scripts/digitize_reconstruct.py` | 刪除 | 改為 C++ 的 `simreco`，介面為 `geant4_run.py reco`、`table` |
| 一般化 `scoped_upgrade` | 延後 | 觸發：第二種研究類型需要升級（目前只有 Geant4 study record） |
| Geant4 10.x 探針 | 延後 | 觸發：第一個使用 10.x 的應用；`StreamInfo`（10.2 起）、`FluctuationType()`（11.x 起）等 API 需依版本條件編譯 |

---

## 8. 統計規格彙整

| 項目 | 規格 | 章節 |
|---|---|---|
| 停止 | 只依事先宣告的 N；未達標判 unresolved，不補跑 | 4.5 |
| 兩階段係數 | SE 來自 K = 16 子 run：f = F₀.₉₀(15,15) ≈ 1.97；來自大樣本 bootstrap：1.2 | 4.5 |
| 收斂閘門 | IUT：通過用 q₀.₉₅，失敗用 q₁₋α/m；SE 為估計值時 q 用 t（差值約 ν = 30），否則用 z；se 是差值的 SE；事先設 se ≤ tol/4 | 4.5 |
| 確定性閘門 | charged geantino 的場精度與最大步長 | 6.7 |
| MPV | 16 個分割子 run 的 MPV 平均；固定分格寬度；SE = sd/√16；t₁₅；全樣本 MPV 只作診斷 | 4.5 |
| bootstrap | 64 位元計數器雜湊、反 CDF、全域唯一事件鍵、R ≥ 400；不用於 MPV | 4.5 |
| 種子 | `H(study_id, role, point_id, k)` → 兩個正整數 | 4.5 |
| negative control | 觀測量位移、正負兩個方向 | 4.4 |
| 證據相關性 | `evidence_overlap` | 4.5 |
| 新區塊版本 | `probe_version`、`column_map_version`、`evidence_overlap_version` | 4.5、5.6 |
| 計算位置 | 階段 1 在 Python；階段 2 起由 `simstat`（C++）計算，門檻與判定留在 Python | 5.8 |

---

## 9. 契約與版本

| 物件 | 位置 | 版本 |
|---|---|---|
| simulated dataset-record、execution trace | `contracts/validate.py`、`core/trace.py` | 3.2.0、3.5.0（既有） |
| 範圍比對（observable kind）、benchmark 對照表、等級不得自行宣告、configuration 與隔離規則、`extension.simulation` 選用屬性 | `contracts/validate.py`、`contracts/dependencies.py`、`ext_computational_run.json` | C1（minor、閘控、sci-fix） |
| schema 關鍵字擴充 | `contracts/schema.py` | 不升版 |
| 對照表加入 verification；重建紀錄作為 simulated 表格的輸入 | `contracts/validate.py`、`contracts/dependencies.py` | C2（minor、閘控） |
| `effective_config`、`evidence_overlap` | computational-run 的自由格式區塊 | 不改契約 |
| `layered_sim.spec/2`、`layered_sim.output/2`、`column_map` | adapter | adapter 0.2.0、0.3.0 |
| `GRADES`、kind 與 configuration 的輸出 | hep-detector | 隨 plugin 版本 |
| 幾何存取器 | `core/geometry/layered.py` | 隨 plugin 版本 |
| `simcore`（`simspec`、`simstat`、`simreco`） | adapter（C++） | adapter 0.2.0、0.3.0 |

computational-run schema 的擁有者是 hep-computing；本提案不修改該 schema。

---

## 10. 每個階段結束時的檢查

- `run_all_checks.py`（含 CI lock 環境）
- `check_layering.py`、`check_relocation.py`、`check_ownership.py`、`check_packaging.py`
- `measure_entrypoints.py`（hep-detector quick load ≤ 25,600 bytes）
- `reference_inventory.py --check`、`capability_map.py --check`、`check_routing_static.py`
- 每份 study record 都通過 `validate.py --strict` 與 `dependencies.py`
- `tests.adapters.test_geant4` 離線與 live（`HEP_GEANT4_LIVE_TEST=1`）
- `simcore` 的建置、ctest 與等價測試（CI 必要工作，不需 Geant4）
- `python3 -m unittest discover -s tests/contracts -t .`（整體執行，以抓測試順序相依）
- `tools/scifix_advisories.py check`（有 advisory 的階段）
- 由沒參與撰寫的 agent 執行一個新問題，並附通過條件
- VALIDATION 條目、CHANGELOG、release manifest

---

## 11. 待維護者決定的事項與殘餘風險

**待決定：**
1. 階段 1 的版本歸類。本提案依閘控設在 x.y.0 的慣例，定為 C1（minor）加 sci-fix。
2. 逐位元相同若在同主機也無法達成，是否接受改為統計比對（在 VALIDATION 記錄原因）。
3. G5「未複製範例程式碼」的確認方式。
4. `ext_computational_run.json` 加入選用的 `simulation` 屬性，以及 C2 的「衍生模擬」標記：需要 schema 擁有者 hep-computing 同意。
5. 新增必要的 CI 工作建置 `simcore`（需要 C++17 編譯器）；目前 adapter 沒有任何必要的 CI 工作。

**殘餘風險：**
1. J14 的偵測極限可能因子 run 估計量、t 分位數與觀測量單位的控制組而改變，需要重新設計控制組。
2. 子 run MPV 平均和全樣本 MPV 有小偏差（審查者的 toy 約 0.25 %），在 sci-fix 紀錄中說明。
3. quick load 只剩 931 bytes。
4. 取樣比例的參考需要 PDG 的 μ 能損表；選用的 PVT benchmark 需要 Sternheimer 參數。兩者都要經 hep-citations 取得文獻紀錄後才能使用。
5. 量能器簇射主導 CPU 時間；後漏的收斂每點約需 5000 個簇射，事件數由 trial run 決定並記錄。
6. 探針假設 worker 和 master 的設定相同；若發現 thread-local 差異，改為逐執行緒傾印。
7. `longitudinal-profile` 的 `target_slabs` 由人宣告；契約只能以 `target_geometry_sha256` 比對宣告與 benchmark，無法判定目標堆疊就是論文中的配置，仍需審查者核對。
8. 工作量：原型估計階段 1 約 8–12 個工作天，另加 Geant4 執行時間（4.1、4.2、4.6 約 1 天；4.3 1–2 天；4.4 1–2 天；4.5 3–5 天；sci-fix 流程約 1 天）。階段 2 另需把統計量移植到 `simstat` 並建立 CI 工作，原型未估計。
9. 兩種語言的維護成本：核心邏輯分在 C++ 與 Python；以 principle 11 的分工規則與等價測試控制，同一個量只有一份正式實作。
10. 浮點等價：不同編譯器與最佳化（例如 FMA）可能讓 `simstat` 與 Python oracle 在最後幾位不同；等價測試以相對差 ≤ 1e-12 判定，逐位元相同只要求 `simspec` 的放置數值（同一建置）。

---

## 12. 依 0.21.0 重新核對（2026-10-21；歷史紀錄，目前狀態見第 13 節）

本文件原以 0.20.0 撰寫。0.21.0（`main` 的 `c4f7954`）合併後，在隔離的 worktree（分支 `worktree-geant4-architecture`）中逐項重新核對。

**0.21.0 的變更及其影響**

| 0.21.0 變更 | 對本提案的影響 | 處理 |
|---|---|---|
| contracts 3.2.0：simulated dataset-record | 本提案原定的 3.2.0 已被使用 | 當時改為 3.3.0、3.4.0；這兩個版本後來也被使用，現改用 C1、C2（第 13 節） |
| simulated dataset-record：輸入 study record 為 `validated-in-scope` 時，表格可不帶 `unvalidated` | 範圍漏洞（D1、D2）會經由這條路徑傳到表格 | advisory 一併說明（4.7）；J15 的重建表格以此格式發布（6.5） |
| 新的 reference benchmark `longitudinal-profile`（ALICE FoCal-E） | 契約對照表要加入；它的「目標」是整個取樣堆疊，原本「唯一一片平板」的 isolated 定義會誤判它 | 對照表加入（4.1）；configuration 改以「benchmark 目標」定義，並輸出目標幾何雜湊（4.3） |
| study spec 的 benchmark enum 仍未列 `shower-containment`，也未列 `longitudinal-profile` | D8 擴大 | 4.6 兩者都補上 |
| layered_sim 支援混合材料（`components`） | 階段 3 不需再做；spec/1 → spec/2 轉換和逐位元相同要處理材料順序 | 5.3、5.5、6.4 |
| `multiple_scattering.py` 輸出 `intrinsic_coefficient` 並在 N < 10 時警告；回報值仍用 Gluckstern | 6.2 的說明需更新 | 6.2 |
| `check_routing_static.py` 從 `docs/researcher-journeys.md` 讀取 journey | J15 列入表後就必須有路由案例 | 6.11 |
| `geant4.def` 固定基底映像的 digest | 無影響 | — |

**仍然存在的現行缺陷（0.21.0 行號）**

| # | 位置 | 狀態 |
|---|---|---|
| D1 | `validate.py` `_scope_inside()` 行 327；`check_geant4_study.py` `scope_within()` 行 481 | 未修正 |
| D2 | `validate.py` `_study_upgrade()` 行 373，篩選行 397 | 未修正 |
| D3 | `geant4_benchmarks.py` 行 678 | 未修正 |
| D4 | `check_geant4_study.py` 行 358 | 未修正 |
| D5 | `geant4_benchmarks.py` 行 369 | 未修正 |
| D8 | study spec enum 7 個、`GRADES` 9 個 | 擴大 |

**其他核對結果**

| 項目 | 0.21.0 的值 |
|---|---|
| `CONTRACTS_VERSION` | 3.2.0 |
| `GEANT4_UPGRADE_FROM` | 3.1.0（行 324） |
| `SUPPORTED_KEYWORDS` | 仍無 maxItems、maximum、exclusiveMaximum |
| `SIM_SOURCES` | 11 個檔案，未變 |
| `validate_spec()` | 仍在 `geant4_run.py` 行 103，新增混合材料的檢查 |
| `DetectorScriptCount` | 21；`docs/capability-matrix.md` 行 47 仍寫「twenty-one scripts」 |
| adapter geant4 | 0.1.0，`demonstrated-on-synthetic-data` |
| 共享 stanza 點 5 | 仍寫「3.1.0 upgrade rule」 |
| J14 `recorded/` | 2,447,979 bytes |
| hep-detector quick load | 24,669 / 25,600 bytes |
| `check_packaging.py` MAX_BYTES | 2 MiB |
| advisory | 最新 SFA-2026-035 |
| journey 表 | J1–J14 |

---

---

## 13. 依目前 main 的第二次深度檢查（2026-10-22）

基準為 `main` 的 `9f08796`（0.23.0 加未發布的變更，contracts 3.5.0）。工作分支 `worktree-geant4-architecture` 已 rebase 到這個提交。檢查分三部分：一位沒參與撰寫的 agent 以 0.22.0、0.23.0 與未發布的變更審查本提案（含 0.21.0 新增的部分與中英對照）；另一位在獨立的 worktree 中照階段 1 的規格做原型；主要證據由撰寫者重新核對。

**0.22.0、0.23.0 與未發布變更的影響**

| 變更 | 對本提案的影響 | 處理 |
|---|---|---|
| contracts 3.3.0（審查格式）、3.4.0（審查篩選）、3.5.0（execution trace）已被使用 | 原定的 3.3.0、3.4.0 失效 | 改用 C1、C2 記法 |
| execution trace：`provenance.code_paths`、`code_tags`、`trace.tag()` | 新的寫入者需加 `trace.provenance()`；新的共用函式應加 tag；import `contracts.validate` 會改變 `code_paths` | 4.5、6.5 |
| `scifix_advisories.py check`：鍵必須可區分、advisory 與 ledger 等級一致、範圍與 `introduced_basis` | 原 advisory 寫法無法通過；simulated 表格無法用鍵區分；D5 是 S1 | 4.7 |
| `core/status.py`：`refused` 是負向判定，`rejected` 是無法使用的輸入；exit 0/1/2/3 | unresolved、未達標、探針、新腳本的狀態 | 4.5、5.6、6.5 |
| partition：manifest 內重複種子被拒；`make_manifest` 的種子規則；`cmd_chunk` 的 `start + 1` | 原種子公式與既有程式衝突；子 run 不是切分既有 run | 4.5 |
| `check_layering.py` 更嚴、`core/OWNERS.json` 需 steward | 幾何存取器放在 `core/`；不得寫實驗名稱 | 2、5.4、6.11 |
| `measure_entrypoints.py` 完整量測折疊描述 | hep-detector 描述 1,018 / 1,024 字元 | 6.11 |
| `check_packaging.py` 掃描所有文字檔 | 探針寫出的路徑經 `tilde()` | 5.6 |
| 獨立審查工具 `review.py`（0.22.0） | 可作為各階段文件的 advisory 審查 | 6.11 |

**階段 1 原型的結果**（程式與測試變更見 `prototype/phase1-core.patch`，可直接套用到 `9f08796`）

| 項目 | 結果 |
|---|---|
| 實作範圍 | 4.1、4.2、4.3、4.6；跳過 4.4、4.5 |
| 測試 | 四個相關模組 55 個測試通過；`tests/skills/hep_detector` 346 個通過；`check_layering`、`reference_inventory --check`、`check_ownership`、`check_packaging` 通過 |
| J14 | 離線重播重產後，7 份 study record 都通過 `validate.py --strict` 與 `dependencies.py`；27 個準則全部通過。舊的已提交紀錄在 `--strict` 下以 `geant4.upgrade_scope_outside` 失敗，不加 `--strict` 時通過，證明閘控有效 |
| 被推翻或修正的宣稱 | 版本號已過時；「舊紀錄在 `--strict` 下失敗」只對帶 `validated-in-scope` 者成立；4.1–4.3 不需 live 重錄；「J14 不受影響」只對判定成立；`longitudinal-profile` 照字面推導一律 `embedded`，只比 particle 與 energy 會放寬範圍 |
| 規格不足處（本版已補） | kind 存放位置、benchmark kind 的來源、等級檢查的適用範圍、宣告缺少維度、雜湊的正規形式、`run_record` 為選用、重複放置、場的判定、CSV 與 run record 無法以雜湊連結、D8 在執行時沒有作用 |
| 工作量 | 階段 1 約 8–12 個工作天，另加 Geant4 執行時間 |

原型在獨立 worktree 中重跑的結果已由撰寫者確認（55 個測試通過）。D10 也已在乾淨的 main 上重現：`tests/contracts` 整體執行有 5 個錯誤，單獨執行 `test_simulated_dataset` 則通過。

**目前的缺陷位置（`9f08796`）**

| # | 位置 | 狀態 |
|---|---|---|
| D1 | `validate.py` `_scope_inside()` 行 349；`check_geant4_study.py` `scope_within()` 行 482 | 未修正 |
| D2 | `validate.py` `_study_upgrade()` 行 395，篩選行 419 | 未修正 |
| D3 | `geant4_benchmarks.py` 行 678 | 未修正 |
| D4 | `check_geant4_study.py` 行 359 | 未修正 |
| D5 | `geant4_benchmarks.py` 行 369 | 未修正 |
| D8 | study spec enum 7 個、`GRADES` 9 個 | 未修正 |
| D10 | `tests/contracts` 的測試順序相依 | 新發現，未修正 |

**其他核對結果**

| 項目 | 目前的值 |
|---|---|
| `CONTRACTS_VERSION` | 3.5.0 |
| `GEANT4_UPGRADE_FROM` | 3.1.0（行 346） |
| J14 study record | contract 3.5.0，帶 `code_paths`、`code_tags` |
| J14 世界材料 | `G4_Galactic` |
| advisory | 最新 SFA-2026-037 |
| hep-detector | quick load 24,669 / 25,600 bytes；description 1,018 / 1,024 字元 |
| `longitudinal-profile` 設定 | 只有 `layers: [{t, column}]`，沒有放置清單 |
| benchmark 輸出的 scope | `material`、`thickness_mm` 取自設定（`longitudinal-profile` 通常為 null），`observable` 為自由文字 |

**尚未做的檢查**：本版新增的文字還沒有經過獨立審查。建議在維護者本機以 `review.py` 審查本提案（依 `independent-review.md`，需先關閉 fork 子代理並重啟 host，且文件在 host 上沒有其他副本）。

## 附錄 A：數值

計算程式：`j15_design_estimates.py`（隨本文件提供；只用標準函式庫，scipy 可選；A_N 以精確有理數最小平方核對閉式）。

**幾何**
- Si 中心：−500、−340、−180、−20、140、300 mm；L = 0.800 m。
- 場區：−520 … 320 mm；兩端邊距各 19.85 mm。
- TOF1 兩層 −810 … −800、−790 … −780；TOF2 兩層 490 … 500、510 … 520；站中心距 D = 1.300 m；世界 ±1200 mm。

**徑跡**
- A_N = 720 (N−1)³ / [(N−2) N (N+1)(N+2)]：A₄ = 81.0、A₆ = 66.96、A₈ = 57.17（N 點等距含兩端、等權重）。
- MDR（只算量測項）= C B L² / (ε √A_N)：C = 0.2998 時為 1172 GV（C = 0.3 時為 1173 GV）。
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
| 1000 GV | 66.0 | 25.0 … 65.0 | 74.5、75.5 |

若方向和偏轉相同（−50 mrad）：0.6 GV 在 Si6 的 y = −151 mm、1 GV 為 −116 mm，都錯過 Si6。

**TOF**：每站兩層、兩層獨立時，σ_站 = σ_層 / √2，σβ/β = √2 σ_站 c / D = σ_層 c / D；每層 80、100、150 ps 對應 1.8 %、2.3 %、3.5 %（每站一層時為 2.6 %、3.3 %、4.9 %）。同站兩層之間 β = 1 的飛行時間為 66.7 ps，兩層時間差的解析度為 √2 σ_層（100 ps 時 141 ps）。

**量能器**：18.41 X₀、0.886 λ_I、35 cm；有效 Molière 半徑 3.95 cm；mip 能損比 0.284 只是 dE/dx_min 之比，**不是**參考值。

**量能器前的物質**：11.32 % X₀（四層 TOF 9.40 %，佔 83 %；Si 1.92 %）、5.46 % λ_I；其中 TOF1 在徑跡之前，佔 4.70 % X₀。

**統計**
- 達標機率：以真實 SE 判定時 P(χ²₁₅ ≥ 15/f)；f = 1.2 為 0.641，f = 1.755 為 0.90。以估計 SE 判定時 P(F₁₅,₁₅ ≤ f)；f = 1.2 為 0.636，f = 1.755 為 0.856，**f = 1.972 為 0.90**。
- t₀.₉₅(30) = 1.697，t₀.₉₅(15) = 1.753，t₀.₉₇₅(15) = 2.131。
- 事件數（差值 se ≤ tol/4）：10 GeV 電子總沉積（容許 1 %）約 392；後漏（絕對容許 0.002）約 5000。

## 附錄 B：出處

- PDG Atomic and Nuclear Properties（2026-10-21 取得）：[Silicon](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/silicon_Si.html)、[Lead](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/lead_Pb.html)、[Polyvinyltoluene](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/polyvinyltoluene.html)
- PDG Review of Particle Physics 2024，第 34 章：式 34.5、34.12、34.16、34.34–34.36（式號依 plugin 的 VALIDATION GEANT4-STUDY）
- Geant4 v11.4.3 原始碼（`github.com/Geant4/geant4`，tag `v11.4.3`），審查中讀過的檔案包括：`G4RunManager.cc`、`G4RunManagerKernel.cc`、`G4MTRunManager.cc`、`G4TaskRunManager.cc`、`G4WorkerRunManager.cc`、`G4EmParameters.cc`、`G4EmParametersMessenger.cc`、`G4EmExtraParametersMessenger.cc`、`G4ProductionCutsTable`、`G4HadronicInteraction.hh`、`G4HadronicProcess.hh`、`source/analysis/`、`G4FieldManager.hh`、`G4ChordFinder.hh`、`G4PropagatorInField.cc`、`G4FieldBuilder`、`G4FieldParameters`、`G4LogicalVolume`、`G4ChargedGeantino.cc`、`G4EmBuilder`、`G4EmSaturation`、`G4LossTableManager`、`G4IonisParamMat`、`G4IonTable`、`FTFP_BERT.cc`、`G4PhysListFactory`、`G4NistMaterialBuilder.cc`、`G4PVPlacement`、`G4QuickRand.hh`、`G4GeomTestVolume.cc`
- Geant4 Book for Application Developers，[Basic Examples](https://geant4.web.cern.ch/documentation/dev/bfad_html/ForApplicationDevelopers/Examples/BasicCodes.html)（B4、B5；開發版文件）
- hep-research 0.21.0（`c4f7954`）：`contracts/validate.py`、`contracts/schema.py`、`contracts/stanzas/context-resolution.md`、`skills/hep-detector/`（`SKILL.md`、`README.md`、`check_geant4_study.py`、`geant4_benchmarks.py`、`tracker_resolution.py`、`multiple_scattering.py`、`toy_spectrometer.py`）、`adapters/geant4/`、`examples/geant4-thin-silicon/`、`docs/maintenance.md`、`docs/capability-matrix.md`、`tools/measure_entrypoints.py`、`tools/check_packaging.py`、`tests/skills/test_documented_output_claims.py`、`CHANGELOG.md`、`VALIDATION.md`
- 待取得：PDG 的 μ 能損表（Groom, Mokhov & Striganov）；Sternheimer, Berger & Seltzer (1984), *Atomic Data and Nuclear Data Tables* 30, 261

## 附錄 C：版本歷程

| 版本 | 主要內容 | 審查與主要更正 |
|---|---|---|
| v2 | 四層架構、四份契約、三種後端 | 兩份審查：探針時機、EM 參數鎖定、SE 停止偏差、`uses-validated-physics`；發現現行範圍檢查缺陷 |
| v3 | 縮小為三批次 | — |
| 探測器文件 | 單軸疊層磁譜儀 | Gluckstern 小 N 公式更正 |
| v4 | 整合為五階段 | 三份審查：幾何不自洽、J14 會失效、收斂不可行、契約不強制升級限制、重複實作 |
| v5 | 三階段 | 兩份審查：磁場方向、場檢查網格、MPV 估計量、F 分布係數（0.74 更正為 0.64）、等級自行宣告、隔離漏洞、種子索引、多處 plugin 事實 |
| 最終版 | 三階段；所有審查發現已處理 | — |
| 最終版（0.21.0 基準） | 依 0.21.0 重新核對：契約版本順延、`longitudinal-profile`、混合材料、simulated dataset-record、journey 檢查 | 見第 12 節 |
| 最終版（main `9f08796` 基準） | 第二次深度檢查：差異審查與階段 1 原型；版本改為 C1、C2；隔離規則移到階段 1；`longitudinal-profile` 的目標與 kind；sci-fix 拆分；種子與退出碼；D10 | 見第 13 節 |
| J15 修訂（2026-10-22） | TOF1、TOF2 各改為兩層，四層同材料；TOF 解析度、上游能損、物質預算、接受度與場檢查網格重算；新增 `tof-layer-consistency` | 數值由 `j15_design_estimates.py` 重算 |
| **語言分工（2026-10-22）** | **計算核心改用 C++：新的 `simcore`（`simspec`、`simstat`、`simreco`）；Python 為介面與判斷層；以獨立執行檔交換 JSON/CSV；hep-detector 不新增腳本** | 使用者決定 |
