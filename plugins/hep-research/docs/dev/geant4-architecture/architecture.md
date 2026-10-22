# hep-research 模擬研究架構（參考實際實驗的重新設計）

> 狀態：架構提案，待使用者確認 §12.2、維護者決定 §12.3。取代同名文件的前一版（`2d32342`，「整合版」）；前一版的內容與三次檢查的結論，凡仍適用者都已併入，被取代的設計列在 §13
> 基準：hep-research `main` 的 `9f08796`（0.23.0 加未發布的變更），contracts 3.5.0，adapter geant4 0.1.0，Geant4 11.4.3
> 日期：2026-10-22
> 語言：繁體中文原文；英文版 [`architecture.en.md`](architecture.en.md) 內容相同
> 讀法：§0 是一頁摘要；§1 是從實際實驗得到的設計依據；§2–§9 是架構本身；§10–§13 是階段、風險、決策與演進紀錄
> 記法：本文件中的「contracts C1、C2」即計畫（[`plan.md`](plan.md) §5）中的契約版本 CV1、CV2；任務 C 的階段記為 C1–C3。階段、編號與待決事項以計畫為準，工作項與驗收以任務規格為準；本文件只說明設計理由

---

## 0. 摘要

**目的。** 讓 hep-research 裡的模擬研究（目前是 Geant4）做到三件事：結果不會被錯誤地標成 `validated-in-scope`；數值與判定可重現、可追溯；研究層不綁死在某一個模擬程式、某一種幾何或某一類研究上。

**設計的出發點。** 大型實驗已經解決過同樣的問題，只是規模大得多。本架構只取它們經過時間考驗、而且在 plugin 的限制下（Python 只用標準函式庫、以獨立執行檔交換 JSON/CSV、最小變動）做得到的做法：

| 問題 | 實際實驗的做法 | 本架構 |
|---|---|---|
| 平行執行下的可重現性 | ATLAS 每個事件依事件與 run 編號重設亂數；Allpix² 依事件編號給種子，「worker 數不同仍可重現」 | 每個事件以 H(邏輯 run 種子, 事件編號) 重設亂數；工作切分與執行緒數不影響事件內容（§5） |
| 大量平行工作的結果合併 | CMS DQM：工作各自填直方圖，harvesting 步驟合併後才做品質判定 | 模擬程式寫出可合併的 run summary；Python 只在合併後推論與判定（§4） |
| 設定與處理鏈的追溯 | CMS 以參數集的雜湊與 process history 記錄每個處理步驟 | 每個步驟的設定雜湊、輸入雜湊與程式雜湊寫入紀錄；多層鏈可遞移追溯（§7） |
| 支援多個模擬引擎 | ALICE 的 Virtual MC 在使用者程式與引擎之間加隔離層，但幾何分離多年仍在進行 | 不在 API 層抽象化；在**輸出**層抽象化：任何後端交出三個邊界產物即可（§3） |
| 不同元件共用資料 | Key4hep 以 EDM4hep 作為元件間的共同資料模型，舊工具以轉換接入 | 邊界產物就是共同資料模型；其他框架以縮減工具轉換接入（§3.4） |
| 模擬是否可信 | Geant4 以 geant-val 對實驗數據做跨版本比較；CMS 先用試束數據選 physics list，再用碰撞數據檢查；ATLAS 快速模擬以 Geant4 為參考 | 五種驗證類別，各有自己的參考、統計方法與可否升級的規則（§6） |
| 軟體改版是否改變結果 | Belle II 每晚執行驗證腳本、跨版本比較並可二分搜尋造成退化的提交；geant-val 每月執行 | 回歸類別：和前一版比較，只偵測改變，不升級（§6.4） |
| 資料量分層 | ATLAS：HITS → RDO → AOD；只保留下游需要的層級 | 四層資料：事件細節（不提交）→ 逐事件摘要 → run summary → 判定紀錄（§4.1） |

**架構的核心（六句話）：**
1. **兩個平面。** 逐事件的處理在 C++（資料平面：模擬、數位化、重建）；合併後的推論、判定、紀錄與契約在 Python（控制平面）。
2. **輸出層的後端介面。** 任何後端交出 run summary、column map、effective config（含實際幾何樹）三個邊界產物，就能進入閘門、benchmark 與 label。
3. **事件決定性。** 事件內容只由邏輯 run 種子與事件編號決定；工作切分、執行緒數、執行順序都不影響。
4. **可重現的定義是「判定相同」。** 重播時判定與 label 必須完全相同，數值在相對差 1e-9 內；接近門檻的判定會被標記。來源檔案以雜湊追溯。
5. **一種變異數方法。** run summary 依事件編號分成 K 個區塊；SE 一律以區塊的 batch means 估計，計數很少時用精確區間。
6. **驗證分成五類。** verification、物理參考、配置對應的量測、回歸、模型對模型；只有物理參考與配置對應的量測能升級，而且條件由契約從證據重新推導。

**階段：**

| 階段 | 內容 | 版本 |
|---|---|---|
| A1 | 正確性修正（sci-fix）：契約、統計規則；J14 以現有逐事件資料離線重算，只重錄缺少逐事件資料的 run | contracts C1 |
| A2 | 共用 Geant4 輔助程式庫；`layered_sim` 寫出三個邊界產物與逐事件種子選項；研究層只讀邊界產物 | adapter 0.2.0 |
| B1 | `element_sim`：盒狀元件、巢狀、場、平面穿越、逐事件 ROOT 檔與 `simroot` | adapter 0.3.0 |
| B2 | `simreco`；J15 研究；verification、回歸、模型對模型類別與遞移的處理鏈（C2） | adapter 0.4.0、contracts C2 |

A1、A2 是「任務 A」；B1、B2 是「任務 B」，在任務 A 合併後才開始。每個階段單獨合併。

---

## 1. 設計依據：從實際實驗學到的事

本節每一點都附出處（§14）。「取用」是本架構採用的部分；「不取用」是刻意不做的部分與理由。

### 1.1 亂數與可重現性

- **ATLAS（AthenaMT）：** 不同用途的亂數流以使用它的演算法名稱區分；每個事件依事件與 run 編號重設亂數狀態；目標是「亂數序列必須和事件的處理順序無關」。
- **Allpix²：** 主執行緒依事件建立順序從中央種子產生器給每個事件種子；worker 執行前才設定；設計目標是「即使 worker 數不同，相同輸入仍得到相同結果」。需要依序輸出的模組以緩衝佇列等待，並保存亂數狀態。
- **CMS：** 另一種做法：每個模組、每個 stream 一個亂數引擎，並可把引擎狀態存進事件，之後還原以精確重播。
- **取用：** ATLAS 與 Allpix² 的逐事件重設種子。它最簡單，而且讓「把一個邏輯 run 切成多個工作」與「單一工作」產生完全相同的事件。**不取用：** CMS 的狀態保存（需要在每個事件保存引擎狀態，對我們的規模不必要）。

### 1.2 結果合併與判定的位置

- **CMS DQM：** 資料被切成任意多個工作、亂序且大量平行地處理；每個工作填 MonitorElement（主要是直方圖）；harvesting 步驟合併各檔案中相同的直方圖，之後才在單執行緒中依序做品質測試與衍生量。
- **取用：** 模擬程式只填「可合併的累加量」（計數、和、直方圖）；所有判定在合併之後、在 Python 中進行。這就是 run summary 與控制平面的分工。

### 1.3 追溯

- **CMS：** 以參數集的雜湊識別設定，並以 process history 記錄資料經過的每個處理步驟。
- **取用：** 每個步驟（模擬、數位化、重建、表格）都寫一份紀錄，含設定、輸入、程式的雜湊；simulated 表格的輸入鏈可以任意深，契約遞移地檢查（§7.4）。

### 1.4 多引擎

- **ALICE Virtual MC：** 在使用者程式與傳輸引擎之間加一層隔離，讓幾何與 hit 產生的程式只寫一次；當時 Geant3 用於生產，Geant4 只用於物理驗證，FLUKA 尚未完成，幾何與傳輸的分離仍在進行。
- **ATLAS AtlFast3：** 依粒子種類與能量把工作分給 Geant4、FastCaloSim V2、FastCaloGAN；快速模擬以「重建後和 Geant4 無可分辨的差異」來驗證。
- **取用：** 在**輸出**層抽象化，而不是在 stepping API 層：後端怎麼模擬都可以，只要交出相同的邊界產物。混合多個模擬器的後端，在 effective config 中描述其分派方式。快速模擬與 ML 代理模型以 Geant4 為參考時，屬於「模型對模型」驗證（§6.5）。**不取用：** 寫一個 VMC 式的引擎抽象層（ALICE 的經驗顯示成本高、週期長）。

### 1.5 共同資料模型與幾何

- **Key4hep：** Gaudi 處理框架、DD4hep 幾何、EDM4hep（以 podio 建立）資料模型；EDM4hep 是元件之間在記憶體與檔案中的交換格式；舊的 iLCSoft 處理器在進出時和 EDM4hep 互相轉換，不必改寫。
- **取用：** 邊界產物就是我們的共同資料模型；外部框架以「縮減工具」轉換接入（例如把 EDM4hep 檔縮減成 run summary）。幾何以後端的實際幾何（as-built）為準。**不取用：** Gaudi、DD4hep 作為依賴（plugin 的限制）。
- **GDML：** Geant4 能把實際幾何寫成 GDML，但需要建置時開啟 GDML；本 plugin 的建置是 `GEANT4_USE_GDML: OFF`（`geant4_build.py` 行 53）。所以實際幾何由探針自行走訪（§3.3）；使用者的建置有 GDML 時可另外附上。

### 1.6 驗證

- **geant-val（Geant4 合作組）：** 社群的驗證測試每月以開發版執行，結果存入資料庫，跨版本比較，並對分布做 χ² 與 KS 檢定。
- **CMS：** 先以試束數據調校並選定 physics list，再以碰撞數據中的孤立帶電粒子檢查量能器的響應與解析度；在多個 Geant4 版本之間比較後才採用，並在速度與準確度之間取捨。
- **Belle II：** 每個軟體套件都有驗證腳本產生直方圖；每晚集中執行、跨版本比較，並有工具二分搜尋造成退化的提交。
- **取用：** 把「驗證」分成性質不同的五類（§6）：精確推論的 verification；孤立目標對物理模型的參考（geant-val 的薄靶測試屬此類）；和同一配置量測的比較（CMS 的試束）；跨版本回歸（Belle II、geant-val 的每月比較）；模型對模型（ATLAS 快速模擬）。

### 1.7 資料分層

- **ATLAS：** 模擬輸出 HITS 檔；數位化輸出 RDO（概念上類似探測器的原始數據）；重建輸出 AOD。
- **取用：** 四層資料，各有保存規則（§4.1）。

### 1.8 實際儀器（J15 的對照）

- **PAMELA：** 0.43 T 永久磁鐵；6 片雙面矽微條平面，解析度優於 4 µm；MDR 超過 1 TV；三個 TOF 平面（S1–S3，分割成 paddle）；鎢／矽成像量能器 16.3 X₀、0.6 λ；另有反符合、S4 與中子偵測器。
- **AMS-02：** TOF 四個平面（8、8、10、8 個計數器）；系統對質子約 140 ps。
- **取用：** J15（0.5 T、6 片 Si、MDR 約 1.17 TV、每站兩層 TOF、18.4 X₀ 量能器）和 PAMELA 幾乎同型，可作為合理性的對照；TOF 每層 100 ps 比 AMS-02 樂觀，所以 J15 對 σ_t 做 100 與 150 ps 的敏感度掃描（§10 B2）。J15 仍是合成幾何，不代表任何實驗。

---

## 2. 目標、限制與原則

### 2.1 目標

| 目標 | 由什麼保證 |
|---|---|
| `validated-in-scope` 不能被錯誤取得 | 契約從證據重新推導的事實（§7） |
| 判定可重現、數值可追溯 | 事件決定性（§5.1）、合併後推論（§4）、判定相同的重現定義（§5.6）、每個步驟的雜湊（§7.4） |
| 研究層不綁死後端、幾何或研究類型 | 輸出層的後端介面（§3） |
| 示範磁場、多子系統與重建 | J15（B1、B2） |

### 2.2 限制

- Python 只用標準函式庫。
- G5 授權邊界：Python 只和獨立執行檔交換 JSON 與 CSV；不複製 Geant4 範例程式碼。
- 分層：skill 腳本與 adapter 只 import `core`、`contracts`；`skills/`、`contracts/` 不出現實驗名稱（實驗名稱可以出現在 `docs/` 與 `examples/`）。
- 狀態與退出碼（`core/status.py`）：0 ok、1 負向判定、2 `rejected`、3 `incomplete`。
- 檔案 ≤ 2 MiB；hep-detector quick load ≤ 25,600 bytes（目前 24,669）、description ≤ 1,024 字元（`measure_entrypoints.py` 回報 1,016）。
- J14 的離線重播必須永遠可以執行，不需要 Geant4 與編譯器。

### 2.3 原則

1. **正確性先於擴充。** A1 合併前，不合併任何新功能。
2. **逐事件在 C++，合併後在 Python。** 處理逐事件資料的程式在資料平面；處理合併後累加量的程式在控制平面。同一個量只有一份正式實作；另一種語言的實作只能在測試中作為 oracle。
3. **在輸出層抽象化。** 研究層只認邊界產物，不認後端的欄名、spec 格式或 UI 指令。
4. **相信實際狀態，宣告只是退路。** 幾何、場與物理設定以探針讀到的為準；只有宣告時標記 `source: declared`，不能升級。
5. **可升級的事實由契約認定。** 等級、kind、範圍維度、configuration、目標雜湊都不得由紀錄自行宣告。
6. **驗證類別依參考的性質決定**（§6）。
7. **事件決定性。** 事件內容只由邏輯 run 種子與事件編號決定。
8. **重現的是判定。** 數值以容差比較，判定必須相同；來源以雜湊追溯。
9. **證據的停止規則、格點與區塊數事先宣告。** 加跑、加密、重做控制組都不得依結果決定。
10. **介面可擴充，實作只做眼前需要。** 不做通用運算式語言，不做外掛系統，不做引擎抽象層。
11. **先找現有實作；最小變動。**

---

## 3. 架構總覽

### 3.1 兩個平面與元件

```
控制平面（Python，標準函式庫）
  hep-detector      規則、參考公式、推論（batch means、精確區間、MPV、IUT、negative control、分布比較）、判定、label
  adapters/geant4   spec 驗證、建置、執行、工作切分、紀錄（trace.provenance()）、simulated 表格；
                    A1 由逐事件 CSV 產生 run summary（A2 起只在測試中作為 oracle）
  core              trace、status
  contracts         驗證類別與等級表、範圍、configuration 與隔離（C1）；新類別、遞移的處理鏈（C2）
        ▲
        │  三個邊界產物（JSON；小、可提交、可雜湊）
        │    run summary        simulation-summary/1    （§4）
        │    column map         simulation-columns/1    （§3.5）
        │    effective config   引擎無關外框 + 實際幾何樹 （§3.3）
        │
資料平面（C++）
  g4sim/         共用 Geant4 輔助程式庫（標頭檔）：
                      SimSeed.hh     逐事件種子 H(邏輯 run 種子, 事件編號)
                      SimSummary.hh  區塊累加器、合併、JSON 寫出（只依賴標準函式庫）
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
| 契約 | Python | A1（C1）、B2（C2） | — |
| 推論與判定 | Python | A1 | — |
| run summary 的 Python 產生器（由逐事件 CSV） | Python | A1；A2 起只作為 oracle | — |
| `g4sim`（`SimSeed.hh`、`SimSummary.hh`、`SimProbe.hh`、輔助） | C++ | A2 | Geant4（`SimSummary.hh` 只依賴標準函式庫） |
| `layered_sim` | C++ | 既有；A2 加 `g4sim` | Geant4 |
| `element_sim` | C++ | B1 | Geant4、`g4sim` |
| `simroot` | C++ | B1 | Geant4 analysis（g4tools） |
| `simreco` | C++ | B2 | 標準函式庫、`SimSummary.hh`、`MiniJson.hh` |

### 3.2 後端

| 後端 | 用途 | 幾何 | 狀態 |
|---|---|---|---|
| `layered_sim` | 材料層級的平板研究（J14） | spec/1：沿 x 的平板堆疊 | 既有；A2 後只做維護與 `g4sim` 整合，不再加幾何功能 |
| `element_sim` | 探測器層級的研究（J15 起） | 盒狀元件、一層巢狀、場區 | B1 新增；之後的幾何功能都加在這裡 |
| 使用者的 Geant4 應用 | 實驗組自己的幾何 | 任意（含 GDML） | 引入 `g4sim` 即可交出邊界產物 |
| 其他引擎或框架 | FLUKA、快速模擬、ML 代理模型、Key4hep 等 | 任意 | 以縮減工具把其輸出轉成邊界產物；探針只有宣告（`source: declared`）時不能升級 |

**為什麼新增 `element_sim` 而不是改造 `layered_sim`。** 把 `layered_sim` 改成新的幾何格式，需要 spec 轉換與同主機逐位元相同的驗證，還要永久維護雙格式存取器；這是上一版成本最高、價值最低的一步（§13）。新增一個程式則讓 J14 的程式完全不動，並從第一天就有兩個真正的後端驗證輸出層介面。兩者共用 `g4sim`，避免重複。

### 3.3 effective config

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

### 3.4 縮減工具（外部後端的接入點）

不能引入 `g4sim` 的後端（其他引擎、Key4hep 的 EDM4hep 檔、ML 代理模型）以一個有紀錄的縮減步驟接入：讀它的逐事件輸出，依 `output.observables` 的宣告寫出 run summary 與 column map；effective config 只有宣告。這個步驟本身是一份 computational-run 紀錄，列在處理鏈中（§7.4）。第一個縮減工具 `simreduce` 讀 `simroot dump` 的輸出（B1 之後、第一個需要時實作）。

### 3.5 column map（`simulation-columns/1`）

每個觀測量與輸出欄的語意名稱、實際欄名、單位、操作定義、所在檔案（`csv`、`root` 的哪個 ntuple、`summary`）；附 `column_map_version`。只允許宣告式運算（改名、單位換算、加總、篩選）；需要計算的轉換是另一個有紀錄的步驟。

---

## 4. 資料分層與 run summary

### 4.1 四層資料

| 層 | 內容 | 對應 | 保存 |
|---|---|---|---|
| T1 事件細節 | ROOT 檔：逐體積沉積、平面穿越、逐步 hit | ATLAS 的 HITS | 不提交；紀錄保存路徑、檔案雜湊、內容雜湊、各 ntuple 列數 |
| T2 逐事件摘要 | CSV：主粒子真值、各子系統總沉積、宣告的觀測量 | 縮減的事件表 | benchmark run 提交縮減欄位版本；其餘不提交 |
| T3 run summary | `simulation-summary/1`：依事件區塊的可合併累加量 | CMS DQM 的 MonitorElement | 全部提交（每個 run 數 kB） |
| T4 判定紀錄 | study record、benchmark 結果、label | — | 全部提交 |

J14 的離線重播只需要 T3 與 T4；T2 只用於可選的 oracle 測試與 MPV 的高統計核對。

### 4.2 run summary（`simulation-summary/1`）

每個工作（job）一份 JSON。

| 欄位 | 內容 |
|---|---|
| `run` | 邏輯 run 的識別與種子、這個工作涵蓋的事件編號範圍、`seeding`、區塊大小 B 與區塊數 K、spec 與 effective config 的雜湊、產生者（`layered_sim`、`element_sim`、`simreco`、`python-csv`、縮減工具）與版本 |
| `observables[]` | 每個宣告的觀測量：語意名稱（對應 column map）、單位、累加器 |
| 區塊 | 事件依編號分入區塊：區塊 b 涵蓋事件 [b·B, (b+1)·B)；每個區塊有自己的一組累加器 |
| 累加器 | 整數：`n`、直方圖每格的計數（宣告的固定分格；溢位與下溢分開）、`count_if[]`（宣告門檻的計數）；浮點：Σx、Σx²、`min`、`max`，以 Neumaier 補償加總；B2 起可有 `profile` 與二維直方圖（§9） |
| `merge` | 每個累加器的合併規則（`sum`、`min`、`max`、`hist`）；同一個邏輯 run 的多個工作依區塊編號合併 |

**事件權重。** `layered_sim` 的沉積已經乘上 track 權重，CSV 的 `weight` 欄只是主粒子頂點的權重。為避免重複加權，目前要求事件權重為 1（否則 exit 2）；加權累加的語意與 biasing 的規則延後（§9.3）。

**數值精度。** 整數累加量（計數、直方圖、`count_if`）精確。浮點和以補償加總計算；不同工作切分或執行緒數下，合併順序不同，只造成約 1e-15 的相對差異，遠小於重現的容差（§5.6）。

---

## 5. 執行、種子、區塊與重現

### 5.1 邏輯 run 與事件決定性

- 一個**邏輯 run** 由 spec、後端與邏輯 run 種子 S 決定，含 N 個事件，編號 0 … N−1。
- `seeding: per-event`（新 spec 的預設）：事件 i 在開始時以 H(S, i) 重設亂數。所以：
  - 把邏輯 run 切成任意多個工作（各自涵蓋一段事件編號），得到的事件和單一工作完全相同；
  - serial 與任何執行緒數的 MT，事件內容相同。
- `seeding: stream`：舊行為（serial 為連續亂數流；MT 由 master 分批產生每事件種子）。只用於 J14 既有的 spec，讓 A2 的回歸檢查可以要求 CSV 逐位元相同。
- 種子：S = H(study_id, role, point_id)，映射到 [1, 2³¹)；角色有 trial、nominal、scan、control、variation、calibration、regression；正負兩個方向的控制組用不同的 point_id。同一研究中 S 不得重複。

### 5.2 區塊與 batch means

- 區塊大小 B 與區塊數 K（K ≥ 16）在第一個證據 run 前宣告；N = K·B。
- 每個區塊 b 由 summary 算出估計量 θ_b（平均、比例、比值、分位數、眾數）；回報 θ̄ = 平均；SE = sd(θ_b)/√K，自由度 K − 1。
- 區塊是同一個 run 中不重疊的事件範圍。事件彼此獨立（`per-event` 時由種子保證；`stream` 時是 Monte Carlo 的標準假設），所以區塊估計量彼此獨立。
- 一個 run 就足以估計 SE，不需要為統計開多個行程；工作切分只為了平行化。
- 前提：事件之間沒有狀態（例如會自我調整的 biasing、跨事件的快取）。探針記錄 biasing 與相關設定，有疑慮時改為多個獨立的邏輯 run。

### 5.3 估計量

- **多個觀測量：** 每個區塊的估計量向量一起保存，觀測量之間的共變異由這些向量估計。
- **全樣本值：** 平均與比例另由合併累加器算出，和 θ̄ 的差寫入紀錄作為診斷。
- **分位數：** 直方圖內線性內插；分格寬度須小於容許值的 1/10；落在溢位或下溢格時判為 incomplete。
- **MPV：** 每個區塊的直方圖取最大格，以它和相鄰兩格做三點拋物線內插；回報 K 個眾數的平均。設計時以 toy 證明偏差的 95 % 上界 ≤ tol/10（toy 用 Landau–Vavilov，並以一次高統計 Geant4 run 的形狀核對）；每次執行時，θ̄ 與合併直方圖的眾數之差須 ≤ tol/5 + 2·SE，否則該 benchmark 判為 incomplete。

### 5.4 計數很少時

- 計數型估計量在任一區塊為 0、或合併總數 < 100（門檻可宣告）時，改用合併累加器上的精確區間：比例用 Clopper–Pearson，計數用 Garwood；兩個 run 的比較用精確條件二項法求率之比的區間，相對差 = 比 − 1。
- 這些情況沒有 SE；閘門以區間端點判定（§6.6），事件數規劃用試探 run 的 Poisson 變異數。

### 5.5 兩階段事件數

N = ceil(N_trial·(SE_trial/target)²·f)，f = F₀.₉₀(K − 1, K_trial − 1)（兩者都是 16 時 ≈ 1.97）。約 10 % 的證據 run 會未達標而判為 incomplete，不得補跑；改用 F₀.₉₅（≈ 2.40）可降到約 5 %，事件數多約 22 %。

### 5.6 重現的定義

| 層次 | 要求 |
|---|---|
| 追溯 | 每份紀錄保存 spec、effective config、程式（`sources_sha256`）、種子、輸入與輸出檔案的雜湊 |
| 重新執行 | 同一建置與平台、同一邏輯 run，事件內容相同；summary 的整數累加量相同，浮點累加量相對差 ≤ 1e-12 |
| 重播（由已提交的 T3、T4） | 判定與 label 完全相同；數值相對差 ≤ 1e-9；任何判定的邊距 < 1e-9（相對）時，在紀錄中標記「接近門檻」 |
| 回歸檢查（A2） | J14 的既有 spec（`seeding: stream`）在同一主機上產生和 A2 前逐位元相同的 CSV；只新增檔案，不改原有輸出 |

---

## 6. 驗證類別與判定

### 6.1 五種類別

| 類別 | 參考 | 例子 | 統計 | 能否升級 |
|---|---|---|---|---|
| verification | 輸入的精確推論 | charged geantino 對解析螺旋、運動學、最小平方代數 | 確定性比較或 IUT | 不能 |
| 物理參考（reference） | Geant4 所近似的物理模型或已發表的薄靶量測，在孤立目標上 | Bethe stopping power、Landau–Vavilov MPV、geant-val 式的薄靶測試 | IUT（純量）；χ²（分布，§9.2） | 能（範圍內） |
| 配置對應的量測（setup-matched） | 已發表的量測，且目標雜湊和量測配置相同 | 試束的縱向剖面、模組的響應與解析度 | 同上，加量測不確定度 | 能（範圍內） |
| 回歸（regression） | 同一研究在前一個軟體或 Geant4 版本的結果 | 改版前後的 MPV、直方圖形狀 | 純量的差值與 SE；直方圖的 χ² p 值 | 不能；只標記「改變」並可觸發 advisory |
| 模型對模型（surrogate） | 以 Geant4 等完整模擬為參考的快速模擬或 ML 代理模型 | 參數化量能器對 Geant4 | IUT 或 χ² | 不能升級物理 label；代理模型自己可得到「在範圍內與參考模擬一致」的標記 |

另有 `sanity`（粗略的合理範圍檢查）與 `interface`（介面檢查），兩者都不能升級。

### 6.2 benchmark 表（C1，C2 擴充）

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
| C2 加入：J15 的檢查（`field-propagation` 等） | verification 或 sanity | — | — |
| C2 加入：`regression`、`surrogate` 兩個類別的通用條目 | regression、surrogate | 任何 | 和被比較的研究相同 |

紀錄中的類別或等級和表不一致、或名稱不在表中，判為 error。`geant4_benchmarks.py` 的 `GRADES` 保留給工具，以測試確保一致。

### 6.3 範圍（C1）

- 比對受控的 `observable.kind`；`label` 把它寫入 `declared_scope.observable_kind`。
- 維度清單依 benchmark 宣告（6.2 的第四欄），每個維度有型別：類別或數值區間；純量視為 [v, v]。新用例加維度只改表格。
- 宣告範圍缺少 benchmark 有的維度，視為超出範圍。
- 以目標雜湊為維度時，宣告範圍必須帶相同的 `target_geometry_sha256` 與 `hash_scheme`。
- 閘控：`strict or _at_least(contract_version, C1)`，無 warning 分支。

### 6.4 configuration 與隔離（C1）

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
- **契約規則：** 每個被計入的 benchmark 必須是 isolated（reference）或目標雜湊相符（setup-matched）；`dependencies.py` 必須從 `evidence_records` 中的 run record 重新推導並比對。

### 6.5 回歸與模型對模型（C2）

- **回歸：** 對同一研究、同一設定，在新舊兩個版本（plugin、後端或 Geant4）上各執行一次（point_id 為版本標籤，樣本獨立），比較每個純量觀測量。三種判定：`changed`（|diff| − t_{1−α/m}·se_diff > tol）、`unchanged`（§6.6 的通過規則）、`unresolved`；「不顯著」不等於「沒有改變」。直方圖的比較延後到分布層級的 benchmark。不影響 label；reference 觀測量 `changed` 時可觸發 sci-fix 的檢查。
- **模型對模型：** 代理模型永遠不改變物理 label。代理模型的研究宣告它的參考研究（study record）與範圍；以 IUT 判定（χ² 只作診斷）。通過時記錄 `extension.study.surrogate`（參考研究的引用與雜湊、範圍取兩者的交集）。

### 6.6 收斂閘門（IUT）

- **差值：** a 為最細的設定，b 為第二細的設定；`relative` 模式 diff = (a − b)/b、se_diff = √(se_a² + se_b²)/|b|，`absolute` 模式 diff = a − b、se_diff = √(se_a² + se_b²)（兩個點是獨立的邏輯 run）；ν 以 Welch 公式逐對計算。
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

### 6.7 negative control 與偵測極限

- 判定量：shift = (control − nominal)/reference，SE 由兩個 run 合成。
- 偵測極限：DL = tol + |rel| + t_{0.977}(ν)·se_rel。
- caught：控制組的 benchmark 判定為失敗（|rel_c| > tol）。
- 設計要求：toy 證明在 DL 注入時抓到的機率 ≥ 0.977；真實檢定力在 0.977 附近，所以驗收門檻為 0.977 − 3σ_MC（A1 的驗收條件）。
- 實現：正負兩個方向都注入（否則宣稱限縮為單向）；位於偵測極限 = caught 且 |shift| ≤ 1.1 × DL。單次未抓到時記錄並說明，不自動失敗，不得換種子重跑。

### 6.8 停止規則與證據相關性

- 停止規則、掃描格點、K 與 B、unresolved 的處理在第一個證據 run 前寫入 study spec。
- `extension.study.evidence_overlap` 列出被多個判定共用的 run。

---

## 7. 契約、追溯與 sci-fix

### 7.1 C1（A1）

§6.2–6.4 的表格、範圍與隔離規則；`dependencies.py` 的重新推導；`ext_computational_run.json` 加入選用的 `simulation` 屬性（需 hep-computing 同意）。

### 7.2 C2（B2）

§6.2 的新條目（verification、regression、surrogate）；§6.5 的規則；§7.4 的遞移處理鏈。閘控方式同 C1。

### 7.3 sci-fix 與 advisory（A1）

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

### 7.4 處理鏈的追溯

- 每個處理步驟（模擬、縮減、數位化與重建、表格）寫一份 computational-run 紀錄，含 `**trace.provenance()`、設定雜湊、輸入紀錄與檔案的雜湊、程式雜湊。
- simulated 表格的輸入鏈可以任意深，只要每一層都是有紀錄的 computational-run，而且鏈的每個根都是模擬 run（C2；以前只允許一層）。
- 呼叫 C++ 執行檔時，Python 記錄執行檔與原始碼的 sha256、版本與子命令，並以 `trace.tag()` 標記。

---

## 8. 程式與 CI

| 位置 | 變更 |
|---|---|
| `contracts/validate.py`、`dependencies.py` | §6、§7 |
| `contracts/schema.py` | `maxItems`、`maximum`、`exclusiveMaximum`（`element_sim` 的 schema 需要；不升契約版本） |
| `core/stats/`、`core/simulation/` | 區塊估計量、判定引擎（equivalence、threshold、change、order）、分布函式、summary 的讀取與 schema。放在 `core/` 是因為 hep-detector 的腳本與 adapter（`geant4`、任務 C 的 `detector-design`）都要用，而分層規則只允許 adapter import `core` 與 `contracts`（任務 A §4.4） |
| `skills/hep-detector/scripts/` | 推論與判定只讀邊界產物；幾何事實（最小厚度、configuration）從 effective config 讀取，A2 前的紀錄仍從 spec/1 讀取；不新增腳本，`SKILL.md` 與 description 不改 |
| `adapters/geant4/assets/` | `g4sim/`；`layered_sim/` 加入 `g4sim`；`geant4_run.py`（邏輯 run 與工作切分、A1 的 Python summary 產生器、B2 的 `reco` 與 `table`）；B1 `element_sim/` 與 `simroot`；B2 `simreco` |
| `SIM_SOURCES` | 涵蓋 `g4sim` 與各程式的原始碼 |
| CI | 任務 A 不需要新的必要 CI 工作；`SimSummary.hh` 的 ctest 可作為選用工作。B2 的 `simreco` 需要必要的 C++17 CI 工作 |

---

## 9. 通用性

### 9.1 涵蓋的用例

| 用例 | 由什麼支援 | 狀態 |
|---|---|---|
| 材料層級的參考（J14 類） | reference 類別、孤立平板 | A1 |
| 有場的磁譜儀（J15，對照 PAMELA、AMS-02） | `element_sim`、場計入目標、verification、重建鏈 | B1、B2 |
| 試束或模組（和數據比較） | setup-matched 類別、幾何樹推導的目標雜湊、依 benchmark 宣告的範圍維度 | 契約在 A1、A2；幾何用使用者應用或 `element_sim` |
| 稀有事件 | 精確計數區間 | A1 |
| 軟體或 Geant4 改版 | regression 類別 | B2 |
| 快速模擬、ML 代理模型 | surrogate 類別、縮減工具 | B2（契約）；縮減工具在第一個需要時 |
| 其他引擎或框架（FLUKA、Key4hep） | 輸出層介面、縮減工具 | 介面已備；轉換工具延後 |

### 9.2 現在只定義介面的項目

| 介面 | 內容 | 第一個用例 |
|---|---|---|
| 分布層級的比較 | 以 summary 的直方圖做 χ²（兩邊都有統計不確定度；參考是量測時加量測不確定度） | 第一個以形狀為觀測量的 benchmark，或第一個回歸檢查 |
| 觀測量的組合與選擇 | 欄位的線性組合、兩欄之比；欄位與常數比較的 AND 選擇 | 第一個需要事件選擇的研究 |
| profile 與二維直方圖 | 依 x 分格的 n、Σy、Σy²；二維計數 | 第一個能譜源研究；J15 以固定剛度執行，不需要 |
| 粒子源 | `gps`（只允許宣告式設定）、`event-file`；summary 記錄通量歸一化所需的源面積與立體角 | 第一個能譜或通量研究 |
| `simreduce` | 讀事件檔（經 `simroot`）或外部格式，依宣告輸出 summary | 第一個事後才決定的觀測量，或第一個外部後端 |

### 9.3 延後（附觸發條件）

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

### 9.4 刻意不做

- 引擎抽象層（VMC 式）：在輸出層抽象化已足夠，ALICE 的經驗顯示 API 層抽象的成本高。
- 處理框架（Gaudi 式）、驗證資料庫與網站（geant-val 式）：它們解決大型合作組的規模問題，違反 plugin 的限制。
- 通用運算式語言、估計量的外掛系統、跨引擎的統一探針內容。
- 整數量化與逐位元相同的統計量（§13）。
- 依結果加跑、加密、換種子重跑控制組。
- `uses-validated-physics` label、contracts 4.0、Python 綁定、內容定址快取、`simstat`、不連結 Geant4 的 `simcore`。

---

## 10. 階段與驗收

本節在 2026-10-23 以前複製了各階段的內容與驗收，容易和任務規格不一致，因此改為指向。階段的順序、內容邊界、介面擁有權、閘門與待決事項以 [`plan.md`](plan.md) 為準；每個階段的工作項與驗收以任務規格為準。

| 階段 | 一句話 | 規格 |
|---|---|---|
| A1 | 修正錯誤發出 `validated-in-scope` 的缺陷；統計與 summary 的共用模組放進 `core/`（contracts CV1） | [`task-a-core.md`](task-a-core.md) §5 |
| A2 | `g4sim`、`per-event` 種子、`layered_sim` 寫出三個邊界產物、研究層只讀邊界產物 | [`task-a-core.md`](task-a-core.md) §6 |
| B1 | `element_sim`、場、平面穿越、量能器漏失、逐事件 ROOT 檔、`simroot`、`check-spec` | [`task-b-j15.md`](task-b-j15.md) §5 |
| B2 | `simreco`、處理鏈、verification／regression／surrogate（contracts CV2） | [`task-b-j15.md`](task-b-j15.md) §6 |
| B3 | J15 研究 | [`task-b-j15.md`](task-b-j15.md) §7 |
| C1 | 需求、元件目錄、F0 搜尋、封閉測試 | [`task-c-design-search.md`](task-c-design-search.md) §5 |
| C2 | F1/F2 評估、確認 run、需求判定、配對比較（contracts CV3） | [`task-c-design-search.md`](task-c-design-search.md) §6 |
| C3 | J16 自動設計範例、選用的 MOBO | [`task-c-design-search.md`](task-c-design-search.md) §7 |

---

## 11. 殘餘風險

1. J14 的偵測極限可能因區塊 batch means、t 分位數與觀測量單位的控制組而改變，需要重新設計控制組。
2. 區塊 batch means 對偏斜分布的比值、分位數與眾數有 O(1/B) 的偏差，不隨 K 減少；覆蓋率 toy 容許 ±0.02，必要時加大 B。
3. 區塊獨立的前提在事件之間有狀態時不成立；探針記錄相關設定，有疑慮時改為多個獨立的邏輯 run。
4. 兩階段設計下約 10 % 的證據 run 未達標（§5.5）。
5. 以容差比較時，接近門檻的判定在不同平台可能不同；以邊距標記與「CI 平台為準」處理。
6. 兩個 Geant4 程式：`layered_sim` 凍結於維護模式，靠 `g4sim` 控制重複。
7. 探針假設 worker 與 master 設定相同；若發現 thread-local 差異，改為逐執行緒傾印。
8. 以目標雜湊對應已發表量測時，契約只能比對雜湊，無法判定目標就是論文中的配置；仍需審查者核對。
9. `G4RootAnalysisReader` 的讀取能力未驗證（B1 的試作）。
10. quick load 只剩 931 bytes；本架構不改 `SKILL.md` 與 description。
11. 工作量：原型估計 A1 的契約部分約 8–12 個工作天，另加 Geant4 執行時間；其餘未估計。

---

## 12. 決策紀錄

### 12.1 使用者已決定

| 日期 | 決定 | 位置 |
|---|---|---|
| 2026-10-22 | 核心程式用 C++，Python 作為介面；計算核心用 C++、參考值留在 Python；以獨立執行檔交換 JSON/CSV，不用 Python 綁定 | 原則 2（依 12.2 第 1 項的詮釋） |
| 2026-10-22 | J15 的 TOF1、TOF2 各兩層，四層同材料 | B2 |
| 2026-10-22 | 詳細的逐事件資訊存成 ROOT 檔 | §4.1 T1、B1 |
| 2026-10-22 | J15 與其他部分拆成兩個任務，J15 後做 | 任務 A（A1、A2）、任務 B（B1、B2） |

### 12.2 本文件的提議（需要使用者確認）

1. **語言分工的詮釋：** 逐事件的計算（模擬、數位化、重建、累加）在 C++；合併後的推論在 Python。
2. **輸出層的後端介面**（三個邊界產物），不做引擎抽象層。
3. **事件決定性：** 新 spec 預設 `seeding: per-event`；工作切分與執行緒數不影響事件。
4. **重現的定義是「判定相同」**，數值以容差比較；不做整數量化與逐位元相同的統計量。
5. **區塊 batch means：** 一個 run 內依事件編號分 K ≥ 16 個區塊；J14 有逐事件資料的 run 離線重算，不重錄。
6. **新增 `element_sim`**，`layered_sim` 不改 spec 格式；兩者共用 `g4sim`。
7. **五種驗證類別**，其中 regression 與 surrogate 在 C2 加入。
8. **四個階段**（A1、A2、B1、B2），ROOT 檔與 `simroot` 在 B1。
9. 兩階段係數用 F₀.₉₀ 或 F₀.₉₅；精確區間的切換門檻（任一區塊為 0 或總數 < 100）。

### 12.3 待維護者決定

1. C1 的版本歸類（建議 minor 加 sci-fix）。
2. G5「未複製範例程式碼」的確認方式。
3. hep-computing 同意 `simulation` 屬性與 C2 的遞移處理鏈。
4. B2 的 `simreco` 需要一個必要的 C++17 CI 工作。
5. ROOT 檔的存放位置與保留期限。
6. A1 中 J14 掃描與 variation run 的 live 重錄，以及 recorded 大小的上限。
7. `element_sim` 作為第二個 Geant4 程式的維護歸屬（hep-detector）。

---

## 13. 演進紀錄：被取代的設計

| 前一版的設計 | 取代為 | 依據 |
|---|---|---|
| `simstat` 與不連結 Geant4 的 `simcore`：把逐 run 的統計搬到 C++ | 推論留在 Python，讀合併後的 summary | 程式與資料量小，C++ 無收益，且使重播需要編譯器（合理性評估 P1）；CMS DQM 也在合併後才判定 |
| spec/2、`layered_sim convert`、雙格式存取器、同主機逐位元相同的閘門 | `layered_sim` 不改格式；新增 `element_sim` | 成本最高、價值最低；新增程式讓 J14 不動，並得到真正的第二後端 |
| 整數量化、雙字組 128 位元整數、五成雙捨入、`%.17g` 才能重算 | 浮點補償加總；整數只用於計數與直方圖；重現定義為判定相同 | 逐位元相同不是科學需求；實際實驗追求可重現的事件與可追溯的來源 |
| 每個證據 run 16 個獨立行程 | 一個 run 內依事件編號分區塊 | batch means 本來就是 run 內分批；逐事件種子讓工作切分與統計無關 |
| 強制逐事件種子只為了逐位元相同 | 逐事件種子作為新 spec 的預設，目的是事件決定性 | ATLAS、Allpix² 的做法 |
| 只檢查介面的合成後端 | `element_sim` 是真正的第二後端 | 第三次檢查 R19 |
| 驗證只有等級（reference、sanity、verification、interface） | 五種驗證類別，加入 regression 與 surrogate | geant-val、Belle II、ATLAS AtlFast3 |

仍然有效的前一版內容（已併入本文件）：缺陷 D1–D10 的修正、契約的等級表與依 benchmark 宣告的範圍維度、隔離與場的定義、目標雜湊的版本、IUT 閘門與 t 分位數的操作特性、精確計數區間、MPV 的內插與兩道偏差檢查、t 分位數的偵測極限、兩階段事件數、事件權重的限制、探針的內容與時機、ROOT 檔的設計、J15 的設計。第三次深度檢查的 25 項發現中，R11、R12、R16、R18 因設計改變而不再適用，R19 由 `element_sim` 解決，其餘都已併入。

---

## 14. 出處

- ATLAS Collaboration, *Software and computing for Run 3 of the ATLAS experiment at the LHC*, [arXiv:2404.06335](https://arxiv.org/pdf/2404.06335)（亂數：§3.1；資料格式：§2.3）
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
