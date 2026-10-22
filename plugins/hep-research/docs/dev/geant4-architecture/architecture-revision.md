# Geant4 研究架構：重新評估與新架構提案

> 狀態：提案，待使用者與維護者決定。核准後再改寫 `task-a-core.md` 與 `task-b-j15.md`（中英兩版）
> 日期：2026-10-22
> 依據：目前的任務 A、任務 B 規格（`0d815d6`），以及在 `9f08796` 上核對的程式事實（§1.2）
> 語言：繁體中文原文；英文版 [`architecture-revision.en.md`](architecture-revision.en.md)

---

## 0. 結論

目前架構的**契約與統計規則**（任務 A 階段 1）是對的，應保留。需要重做的是**計算放在哪裡、以什麼介面交換**。

新架構把系統分成兩個平面，中間只有一個小而有版本的產物：

- **資料平面（C++）：** 所有逐事件的處理，包括模擬、scorer、逐事件輸出（CSV、ROOT），以及在事件發生的地方就把資料累加成**可合併的充分統計量**。
- **控制平面（Python）：** spec、流程、對充分統計量做推論（MPV、SE、閘門、negative control）、參考公式、判定、紀錄、契約。
- **邊界產物：** 每個 run（每個 chunk）一份 `run summary`（`layered_sim.summary/1`）。它只包含計數、整數累加的和與平方和、最小與最大值、直方圖，大小約數 kB，可以提交、雜湊、重播。

這個分法帶來四個好處：

1. J14 的離線重播維持**純 Python、逐位元相同**，不需要編譯器。
2. 累加用整數完成，結果和執行緒數、chunk 順序、編譯器都無關。
3. 後端只要交出 summary、column map、effective config 就能接入研究層；這比「只改欄名的假後端」更一般。
4. 任務 A 不再需要不連結 Geant4 的 C++ 專案與新的必要 CI 工作。

另外兩個方法上的改變：
- 所有 SE 統一用 **K = 16 個 chunk 的 batch means** 估計，取代 bootstrap。MPV 本來就需要 K = 16，所以不增加事件數，還少一整套計數器雜湊 bootstrap。
- MPV 改為從直方圖以**三點拋物線內插**求眾數，並加上**偏差門檻**：toy 證明 |偏差| ≤ tol/10。

這些改變重新詮釋了使用者「核心代碼用 C++」的決定：**逐事件的計算在 C++；只有對數十到數百個數字的推論在 Python。** 請使用者確認（§7）。

---

## 1. 重新評估

### 1.1 目標與真正的限制

| 目標 | 由什麼保證 |
|---|---|
| `validated-in-scope` 不能被錯誤取得 | 契約能從證據重新推導的事實（等級、kind、configuration、範圍） |
| 數值可重現、可審查 | 小而有雜湊的中間產物；重播不依賴特定機器 |
| 研究層不綁死後端 | 一個明確的後端介面 |
| 示範磁場、多子系統、重建 | J15（任務 B） |

真正的限制：Python 只用標準函式庫；G5 邊界（獨立執行檔交換 JSON/CSV）；檔案 ≤ 2 MiB；J14 的離線重播目前逐位元重現已提交的輸出（`tests/examples/test_geant4_thin_silicon.py`），而且不需要 Geant4 與編譯器。

### 1.2 核對過的事實

| 事實 | 來源 |
|---|---|
| `mpv()` 與 `bootstrap()` 各約 7 行；`check_geant4_study.py` 加 `geant4_benchmarks.py` 共 1,465 行 | `geant4_benchmarks.py` 行 197、204 |
| J14 的 recorded 資料 2.45 MB；Python 處理是毫秒級 | `examples/geant4-thin-silicon/recorded/` |
| J14 離線重播是純 Python，輸出和已提交的 `output/` 逐位元相同 | `examples/geant4-thin-silicon/run.py` 說明 |
| `layered_sim` 的 MT 用 `G4RunManagerType::MTOnly`，種子在 master 設定 | `layered_sim.cc` 行 150–154 |
| hep-computing 的 partition 合併以名稱 token 判斷是否可加總（`NON_ADDITIVE_TOKENS`） | `core/partition/engine.py` 行 381 |

### 1.3 目前架構的問題

| # | 問題 | 後果 |
|---|---|---|
| P1 | 把 run 層級的統計量（MPV、bootstrap、差值）移到 C++（`simstat`） | 程式量小、資料量小，C++ 沒有效能收益；J14 重播從此需要編譯器；跨編譯器與架構（例如 aarch64 上的 FMA 融合）可能讓逐位元重播失敗；Python oracle 仍要維護，實際上是兩份實作 |
| P2 | 階段 2 一次包含 spec/2、轉換、scorer 重構、探針、column map、統計移植、存取器、schema、ROOT 與 `simroot` | 任何一項卡住（最可能是逐位元相同）全部延後；ROOT 在任務 A 沒有使用者，是盲設計 |
| P3 | 子 run MPV 是 16 個眾數估計的平均，有限樣本偏差不隨 K 平均而消失 | 只記錄、沒有門檻；偏差可能吃掉 benchmark 容許值的一部分 |
| P4 | SE 有兩套方法（子 run 與計數器雜湊 bootstrap），兩階段係數也有兩個（1.97 與 1.2） | 規則與程式都比需要的複雜；bootstrap 需要全域唯一事件鍵與重複檢查 |
| P5 | 「後端介面」實際上是 column map 加逐事件 CSV | 新後端仍要輸出符合欄位語意的逐事件表格；逐事件資料量隨事件數成長 |
| P6 | chunk 的數值經 partition 依名稱 token 合併 | 一個新欄名就可能被靜默加總（`mpv` 已是一例） |
| P7 | 任務 A 需要一個新的、不連結 Geant4 的 C++ 專案與必要 CI 工作 | 維護者待決定事項之一；目前 adapter 沒有任何必要的 CI 工作 |

P1、P4、P5、P6 有共同的根源：**邊界放錯了地方。** 目前交給 Python 的是逐事件資料，所以統計量要嘛在 Python 對大量事件計算，要嘛整段搬去 C++。把邊界移到「可合併的充分統計量」，這四個問題就一起消失。

---

## 2. 新架構

### 2.1 兩個平面

```
控制平面（Python，標準函式庫）
  hep-detector   規則、參考公式、推論（MPV、batch-means SE、IUT、negative control）、判定、label
  adapter 介面   spec 驗證、建置、執行、chunk、紀錄（trace.provenance()）
  contracts      等級表、範圍、configuration、隔離規則（C1）；verification、衍生模擬標記（C2）
        ▲
        │  run summary（layered_sim.summary/1）＋ column map ＋ effective_config（JSON；小、可提交、可雜湊）
        │
資料平面（C++）
  layered_sim    Geant4 模擬、scorer、探針；在事件結束時把觀測量累加進整數累加器；
                 逐事件 CSV（摘要）與 ROOT 檔（細節，任務 B）；`convert` 子命令（spec/1 → spec/2）
  simroot        （任務 B）讀 ROOT 檔：info / dump / hash
  simreco        （任務 B）逐事件數位化與重建，輸出另一份 summary 與逐事件結果
```

**劃線規則（取代原則 11 的措辭）：** 處理逐事件資料的程式在 C++；處理 run summary（每個 run 至多數百個數字）的程式在 Python。同一個量只有一份正式實作。

### 2.2 邊界產物：run summary

每個 run（每個 chunk）一份 JSON，schema `layered_sim.summary/1`：

| 欄位 | 內容 |
|---|---|
| `run` | spec 與 effective spec 的 sha256、種子、chunk 索引、事件數、`summary_version`、量化單位 |
| `observables[]` | 每個宣告的觀測量一筆：語意名稱（對應 column map）、單位、量化步長 q、累加器 |
| 累加器 | `n`（計數）、`sum`（Σ round(x/q)，int64）、`sum2`（Σ round(x/q)²，int128，以十進位字串寫出）、`min`、`max`、`hist`（宣告的固定分格；溢位與下溢分開計數）、`count_if[]`（宣告門檻的計數，用於尾端比例、洩漏比例） |
| `merge` | 每個累加器的合併規則：`sum`、`min`、`max`、`hist`；不靠欄名猜測 |

性質：
- **精確且與順序無關。** 整數加法可交換也可結合，所以結果和執行緒數、worker 合併順序、編譯器、架構都無關。MT 下以自訂的 `G4VAccumulable` 經 `G4AccumulableManager::Merge()` 合併。
- **量化誤差可忽略且有上限。** 每個事件最多 q/2；q 由 spec 宣告，例如能量取 1 eV。
- **小。** J14 一個 run 約數 kB（主要是直方圖），可以直接提交。
- **可重算。** 觀測量的定義（哪個 scorer 欄、分格、門檻）在 spec/2 的 `output.observables` 中宣告式地寫出；已提交的逐事件 CSV 也可以由 Python 重算 summary，作為測試中的 oracle。

### 2.3 後端介面

一個後端只要對 spec/2 交出三樣東西，就能進入閘門、benchmark 與 label：

1. `run summary`（`layered_sim.summary/1`）；
2. `column_map.json`（`layered_sim.output/2`）：觀測量的語意、單位、操作定義；
3. `effective_config`：探針輸出，或宣告並標記 `source: declared`。

使用者自己的 Geant4 應用可以引入一個只依賴標準函式庫的標頭檔（累加器加 JSON 寫出，與 `layered_sim` 共用）來產生 summary。這取代原本「只改欄名的假後端」驗收，也讓延後項目「可嵌入探針」有了自然的形狀。

---

## 3. 方法

### 3.1 統一的變異數方法：batch means

- 每個證據 run 都以 K = 16 個獨立 chunk 執行（種子 `H(study_id, role, point_id, k)`），每個 chunk 一份 summary。
- 對任何觀測量 θ（平均、比例、分位數、MPV）：先在每個 chunk 算 θ_k，回報 θ̄ = 平均，SE = sd(θ_k)/√16，分位數用 t₁₅；兩個估計的差用 Welch 近似（約 ν = 30）。
- 平均與比例另外可以由合併的累加器算出全樣本值；兩者的差寫入紀錄作為診斷。
- 分位數由直方圖以分格內線性內插求得，解析度受分格寬度限制；分格寬度在 spec 中宣告，並須小於該觀測量容許值的 1/10。
- **刪除** 計數器雜湊 bootstrap、全域唯一事件鍵與其重複檢查、第二個兩階段係數（1.2）。兩階段係數只剩 f = F₀.₉₀(15,15) ≈ 1.97。
- 代價：t₁₅ 比 z 寬約 6.6 %；每個掃描點與控制組都要 16 個行程（Geant4 初始化的額外時間；事件數不變）。

### 3.2 MPV

- 每個 chunk 的直方圖（宣告的固定分格）取最大分格，以它和相鄰兩格做**三點拋物線內插**求眾數。這比只取分格中心少了大部分的離散化偏差。
- 回報 16 個 chunk 眾數的平均與其 SE（3.1）。
- **偏差門檻（新）：** 在宣告的 N/K 與分格寬度下，以 Landau–Vavilov toy 證明 |E[θ̄] − 真實眾數| ≤ tol/10；不成立時，加大每個 chunk 的事件數或改變分格寬度後重新宣告（在第一個證據 run 之前）。

### 3.3 spec 轉換放在 `layered_sim` 內

- `layered_sim convert` 子命令，以舊 `Detector.cc` 的同一段程式碼（同一個編譯單元、同一套浮點運算）把 spec/1 轉成 spec/2，輸出 `%.17g`。
- 這保留原 `simspec` 的理由（同一套 double 運算），但不需要另一個 C++ 專案；轉換測試和逐位元比對本來就需要 Geant4，所以都是 live 測試。
- Python 的雙格式幾何存取器不變（J14 的紀錄永遠可以重播）。

### 3.4 ROOT 檔與 `simroot`

- 決定不變：詳細的逐事件資訊寫成 ROOT 檔（g4tools，不需安裝 ROOT），扁平 ntuple，以 `event_id` 為鍵，內容雜湊 `content_sha256`。
- 時程改變：ROOT 檔與 `simroot` 移到**任務 B 的第一段（B0）**，和第一個使用者 `simreco` 一起設計與驗收。任務 A 不需要它們（J14 的 `level` 是 `none`）。
- `G4RootAnalysisReader` 的讀取能力（MT 合併、壓縮、字串欄）在 B0 一開始以一天的試作確認，再定案 `simroot` 的介面。

### 3.5 C++ 專案與 CI

- 任務 A 只有 `layered_sim`（連結 Geant4）。累加器與 JSON 寫出是只依賴標準函式庫的標頭檔，可以用一個小的 ctest 在沒有 Geant4 的 CI 中測試（選用的 CI 工作）。
- 不連結 Geant4 的 C++ 專案（`simreco`）與它的必要 CI 工作在任務 B 才出現。

---

## 4. 新的階段

| 階段 | 內容 | 版本 | 重播 |
|---|---|---|---|
| **A1** 正確性修正（sci-fix） | 契約：等級表、範圍比對 kind、configuration 與隔離規則（C1）；IUT 閘門與 incomplete；negative control 依位移、正負兩向；停止規則事先宣告；種子 H；D8、D10。統計：K = 16 chunk 的 batch means 用於所有 SE（取代 bootstrap）、MPV 拋物線內插與偏差門檻；在 Python 中由 chunk CSV 計算 | contracts C1 | 純 Python |
| **A2a** spec/2 與轉換 | spec/2 讀取、`layered_sim convert`、逐位元比對、雙格式存取器、schema 關鍵字、`field` 預留、探針（`effective_config`） | adapter 0.2.0 | 純 Python |
| **A2b** run summary 與後端介面 | `output.observables`、整數累加器與 MT 合併、`layered_sim.summary/1`、column map；Python 推論改讀 summary；J14 重播改用已提交的 summary；第二後端測試（只交出 summary、column map、effective config） | adapter 0.3.0 | 純 Python |
| **B0** 逐事件 ROOT 檔 | `G4RootAnalysisReader` 試作；`EventFile.*`、`simroot`；`summary`、`hits`、`crossings` 層級 | adapter 0.4.0 | 不需 ROOT |
| **B1** J15 | 場、平面穿越、`simreco`（C++，不連結 Geant4）與其必要 CI 工作、`verification`、衍生模擬標記（C2）、J15 journey | adapter 0.5.0、contracts C2 | 純 Python（重建輸出以 summary 提交） |

每一段都可以單獨合併；A2a 的逐位元比對若卡住，不會擋住 A1。

---

## 5. 和目前規格的差異

| 項目 | 目前規格 | 新架構 |
|---|---|---|
| 契約 C1（等級表、範圍、configuration、隔離） | A1.1–A1.3 | **保留** |
| IUT 閘門、incomplete、停止規則、種子 H、negative control | A1.4、A1.5、A1.7、A1.8、A1.10 | **保留**（兩階段係數只剩 1.97） |
| MPV | 子 run 眾數的平均，偏差只記錄 | 直方圖三點內插 + 偏差門檻 |
| 其他 SE | 計數器雜湊 bootstrap（R ≥ 400） | batch means（K = 16）；bootstrap 刪除 |
| `simstat`、`simcore` 專案、必要 CI 工作 | 階段 2 | **刪除**；推論留在 Python，讀 summary |
| `simspec` | 獨立的 C++ 執行檔 | `layered_sim convert` 子命令 |
| 後端介面 | column map + 逐事件 CSV | run summary + column map + effective config |
| chunk 合併 | partition 依名稱 token | summary 的每個累加器自帶合併規則 |
| ROOT 檔、`simroot` | 任務 A 階段 2 | 任務 B 的 B0，和 `simreco` 一起 |
| `simreco` | `simcore` 的一部分 | 任務 B 中唯一不連結 Geant4 的 C++ 專案 |
| J14 重播 | 階段 2 後需要編譯好的 `simstat` | 永遠是純 Python |
| 逐位元比對範圍 | CSV、`simspec` 放置、`simstat` 相對差 ≤ 1e-12 | CSV、`convert` 放置、summary（整數，跨執行緒與編譯器逐位元相同） |
| J15 的設計（幾何、參數、驗證梯、收斂、variation） | 任務 B | **保留** |

---

## 6. 新方法的驗收重點

- [ ] summary 的整數累加：同種子下 serial 與不同執行緒數的 MT run，summary 逐位元相同；chunk 合併的結果和單一 run 的累加器相同。
- [ ] Python 由已提交的逐事件 CSV 重算的 summary 和 `layered_sim` 寫出的相同（量化後逐位元相同），作為 oracle。
- [ ] batch-means SE 的覆蓋率 toy：在 J14 的觀測量分布下，名義 90 % 區間的實際覆蓋率在 0.90 ± 3σ_MC 內。
- [ ] MPV 偏差 toy：在宣告的 N/K 與分格寬度下 |偏差| ≤ tol/10。
- [ ] J14 的離線重播仍逐位元重現已提交的輸出，而且在沒有編譯器的環境中執行。
- [ ] 第二後端（只交出 summary、column map、effective config）通過 J14 的閘門與 benchmark。

---

## 7. 待決定事項

1. **語言分工的重新詮釋（需要使用者確認）：** 逐事件的計算在 C++，對 run summary 的推論在 Python；`simstat` 與 `simcore` 專案不做。
2. 所有 SE 改用 batch means、刪除 bootstrap：這擴大了 D5 的 sci-fix（回報的 SE 改變，屬 S1），需在 ledger 中說明。
3. ROOT 檔與 `simroot` 移到任務 B 的 B0。
4. 階段改為 A1、A2a、A2b、B0、B1，各自單獨合併（adapter 版本因此多兩個）。
5. 量化步長的預設值（能量 1 eV、長度 1 nm、時間 1 fs）與 `sum2` 以 int128 的十進位字串寫出。

原本的待決定事項中，「新增必要的 CI 工作建置 `simcore`」移到任務 B（`simreco`）；其餘不變（C1 版本歸類、逐位元比對的退路、G5 確認、`simulation` 屬性與衍生模擬標記需 hep-computing 同意、ROOT 檔的存放位置）。

## 8. 殘餘風險

1. 量化讓 summary 不再是浮點的精確和；誤差上限 n·q/2 必須遠小於任何容許值，以宣告的 q 與事件數檢查。
2. batch means 在觀測量分布極度偏斜（例如很小的尾端比例）時，K = 16 的 t 近似可能偏樂觀；覆蓋率 toy 會揭露，必要時加大 K（在第一個證據 run 前宣告）。
3. 16 個行程的 Geant4 初始化時間：J14 每點數秒，總計可接受；量能器研究以 trial run 估計。
4. `G4VAccumulable` 的自訂實作與 `G4AccumulableManager::Merge()` 的行為需在 11.4.3 上以 MT 測試確認。
5. 已記錄的 J14 在 A2b 後改以 summary 重播；舊的 CSV 重播路徑保留在測試中作為 oracle，直到 J14 重錄完成。

## 9. 核准後的步驟

1. 依 §4 與 §5 改寫 `task-a-core.md`（A1、A2a、A2b）與 `task-b-j15.md`（B0、B1），中英兩版同步。
2. 更新 `README.md` 的檔案表、決定與順序。
3. 以沒參與撰寫的 agent 對新規格做一次獨立審查，重點是 summary 的累加與合併、batch means 的覆蓋率、階段之間的介面。
