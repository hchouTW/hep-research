# hep-research Geant4 研究架構（整合版）

> 狀態：架構提案，整合 2026-10-21 至 2026-10-22 的全部討論，並已依第三次深度檢查（§13）修正；待使用者確認 §11.2 的提議、維護者決定 §11.3 的事項
> 取代：`architecture-revision.md`（重新評估與通用性評估，內容已併入本文件）。`task-a-core.md` 與 `task-b-j15.md` 是上一版架構的實作規格，本文件核准後依 §12 改寫
> 基準：hep-research `main` 的 `9f08796`（0.23.0 加未發布的變更），contracts 3.5.0，adapter geant4 0.1.0，Geant4 11.4.3
> 日期：2026-10-22
> 語言：繁體中文原文；英文版 [`architecture.en.md`](architecture.en.md) 內容相同

---

## 0. 摘要

**要解決的問題。** hep-research 的 Geant4 研究流程有兩類問題。第一類是正確性：結果可能被錯誤地標成 `validated-in-scope`，因為範圍檢查跳過觀測量、benchmark 的等級由紀錄自己宣告，統計規則也有漏洞（D1–D10，§1）。第二類是結構：研究層綁死 `layered_sim` 的欄名與平板幾何，無法接其他後端、其他幾何或其他類型的研究。

**架構的核心（五句話）：**
1. **兩個平面。** 逐事件的處理在 C++（資料平面）；對每個 run 數十到數百個數字的推論、判定、紀錄與契約在 Python（控制平面）。
2. **一個邊界產物。** 觀測量在事件發生處被量化成整數並累加成可合併的充分統計量，寫成 `simulation-summary/1`（每個 chunk 一份，約數 kB，自帶合併規則）。Python 只讀 summary。
3. **後端自我描述。** 任何後端只要交出 summary、觀測量對照（column map）、實際設定（effective config，含實際的幾何樹），就能進入閘門、benchmark 與 label。
4. **可升級的事實由契約從證據重新推導。** 等級、kind、範圍的維度、configuration、目標雜湊都不接受自行宣告。
5. **一種變異數方法。** 所有證據 run 都分成 K ≥ 16 個獨立 chunk，SE 一律以 batch means 估計；計數很少時改用精確區間，閘門以區間端點判定。

**階段：**

| 階段 | 內容 | 版本 |
|---|---|---|
| A1 | 正確性修正（sci-fix），維持 Python：契約、統計規則、通用化的範圍與隔離定義；summary schema 第一版由 Python 從 chunk CSV 產生 | contracts C1 |
| A2a | spec/2、`layered_sim convert`、探針（引擎無關外框、實際幾何樹）、雙格式存取器 | adapter 0.2.0 |
| A2b | summary 改由 C++ 在事件中累加；逐事件重設種子；後端介面；CSV 全精度 | adapter 0.3.0 |
| B0 | 逐事件 ROOT 檔與 `simroot` | adapter 0.4.0 |
| B1 | J15 最小磁譜儀：場、平面穿越、`simreco`、`verification`、C2 | adapter 0.5.0、contracts C2 |

A1、A2a、A2b 是「任務 A」，B0、B1 是「任務 B」；任務 B 在任務 A 合併後才開始。每個階段都可以單獨合併。

---

## 1. 背景

### 1.1 已確認的缺陷（`9f08796`）

| # | 缺陷 | 位置 | 後果 |
|---|---|---|---|
| D1 | 範圍檢查不比對觀測量；宣告缺少的維度不受限制 | `validate.py` `_scope_inside()`（行 349 起）；`check_geant4_study.py` `scope_within()`（行 482–493） | 用 MPV benchmark 通過的研究可以把其他觀測量標成 `validated-in-scope` |
| D2 | benchmark 的等級由紀錄自己宣告 | `_study_upgrade`（行 395；篩選行 419） | 寫 `"grade": "reference"` 就能升級 |
| D3 | negative control 在不同單位間比較、只測單向 | `geant4_benchmarks.py` 行 678 | 偵測極限在觀測量上未被證明 |
| D4 | 收斂閘門無等價檢定 | `check_geant4_study.py` 行 359 | 真實差值等於容許值時約 50 % 通過 |
| D5 | MPV 的 SE 用 bootstrap | `geant4_benchmarks.py` 行 369 | 變異數估計不一致 |
| D6 | 停止規則未禁止依結果加跑 | protocol 第 4 節 | optional stopping 偏差 |
| D7 | 證據相關性未揭露 | J14 的 nominal run 被多個判定共用 | 被當作獨立證據 |
| D8 | study spec 的 benchmark enum 缺兩項 | `geant4-study-spec.schema.json` | 一致性缺口（執行時沒有作用） |
| D9 | 研究層綁死 layered_sim 的資料格式 | `derived()`、`summarize`、benchmark 讀固定欄名 | 其他後端無法進入 |
| D10 | 測試順序相依 | `tests/contracts` 整體執行有 5 個錯誤 | 錯誤依執行順序而定 |

### 1.2 這個架構是怎麼來的

| 時間 | 事件 | 對架構的影響 |
|---|---|---|
| 2026-10-21 前 | 三輪獨立審查（7 份報告）、依 0.21.0 與 `9f08796` 的兩次核對、階段 1 原型 | 契約與統計規則成形（§6、§5） |
| 2026-10-22 | 使用者決定：核心程式用 C++，Python 只作介面；以獨立執行檔交換 JSON/CSV | 第一版把逐 run 的統計也移到 C++（`simstat`） |
| 2026-10-22 | 使用者決定：詳細的逐事件資訊存成 ROOT 檔 | 加入 ROOT 檔與 `simroot` |
| 2026-10-22 | 使用者決定：J15 與其他部分拆成兩個任務，J15 後做 | 任務 A、任務 B |
| 2026-10-22 | 合理性評估 | 邊界放錯地方（§1.3 的 P1–P7） |
| 2026-10-22 | 通用性評估 | 十處鎖死通用性的地方（§1.3 的 G1–G10） |
| 2026-10-22 | 第三次深度檢查（兩位獨立審查者與撰寫者核對） | 統計、量化、種子、重播紀錄、雜湊版本等 25 項修正（§13） |

### 1.3 上一版架構的問題

**合理性（P）：**

| # | 問題 |
|---|---|
| P1 | 逐 run 的統計（`mpv()`、`bootstrap()` 各約 7 行；資料 2.6 MB）移到 C++ 沒有效能收益，卻讓 J14 的離線重播需要編譯器；跨編譯器與架構（例如 aarch64 的 FMA 融合）可能讓逐位元重播失敗；Python oracle 仍要維護 |
| P2 | 階段 2 一次包含 spec/2、轉換、scorer、探針、column map、統計移植、ROOT 與 `simroot`；ROOT 在任務 A 沒有使用者 |
| P3 | 子 run MPV 的有限樣本偏差沒有門檻 |
| P4 | 兩套 SE 方法（子 run 與計數器雜湊 bootstrap）、兩個兩階段係數 |
| P5 | 後端介面是 column map 加逐事件 CSV，新後端仍要輸出逐事件表格 |
| P6 | chunk 的數值經 partition 依欄名 token 合併（`mpv` 曾被靜默加總） |
| P7 | 任務 A 需要一個不連結 Geant4 的 C++ 專案與新的必要 CI 工作 |

**通用性（G）：**

| # | 鎖死的地方 |
|---|---|
| G1 | configuration 與目標雜湊只能從 spec 的 slab 清單推導 |
| G2 | 範圍的維度寫死為 particle、material、energy、thickness（`validate.py` 行 350–355） |
| G3 | 有場就不可能 isolated |
| G4 | 累加沒有權重（CSV 已有 `weight` 欄但下游未使用） |
| G5 | 每個觀測量只有一維；沒有逐事件組合與事件選擇 |
| G6 | 只有一種 SE 方法；稀有計數時失效 |
| G7 | 粒子源只有 `gun` |
| G8 | `effective_config` 是 Geant4 專屬格式 |
| G9 | 衍生模擬標記只有一層 |
| G10 | chunk 數固定為 16 |

P1、P4、P5、P6 的共同根源是**邊界放錯地方**：交給 Python 的是逐事件資料。G1–G10 的共同根源是**介面照著第一個用例（平板、gun、Geant4）設計**。本架構分別以「把邊界移到充分統計量」與「介面一開始就可擴充、實作只做眼前需要」處理。

---

## 2. 目標、限制與原則

### 2.1 目標

| 目標 | 由什麼保證 |
|---|---|
| `validated-in-scope` 不能被錯誤取得 | 契約從證據重新推導的事實（§6） |
| 數值可重現、可審查 | 小而有雜湊、整數精確的中間產物（§4.2）；重播的逐位元相同限於 CI 平台，跨平台以相對差 ≤ 1e-12 比較（§5.8） |
| 研究層不綁死後端、幾何或研究類型 | 三個邊界產物構成的後端介面（§4.6） |
| 示範磁場、多子系統與重建 | J15（B1） |

### 2.2 限制

- Python 只用標準函式庫。
- G5 授權邊界：Python 只和獨立執行檔交換 JSON 與 CSV；不複製 Geant4 範例程式碼。
- 分層：skill 腳本與 adapter 只 import `core`、`contracts`；`skills/`、`contracts/` 不出現實驗名稱。
- 狀態與退出碼（`core/status.py`）：0 ok、1 負向判定、2 `rejected`、3 `incomplete`。
- 檔案 ≤ 2 MiB；hep-detector quick load ≤ 25,600 bytes（目前 24,669）、description ≤ 1,024 字元（目前 1,018）。
- J14 的離線重播必須永遠可以執行，並在 CI 平台上逐位元重現已提交的輸出。

### 2.3 原則

1. **正確性先於擴充。** A1 合併前，不合併任何新功能。
2. **邊界在充分統計量。** 處理逐事件資料的程式在資料平面（C++）；處理 summary 的程式在控制平面（Python）。同一個量只有一份正式實作；另一種語言的實作只能出現在測試中作為 oracle。
3. **相信實際狀態，宣告只是退路。** 幾何、場與物理設定以探針讀到的為準；只有宣告時要標記 `source: declared`，且不能用來升級。
4. **可升級的事實由契約認定。** 等級、kind、範圍維度、configuration、目標雜湊都不得由紀錄自行宣告。
5. **驗證等級依參考的性質決定。** 參考值是輸入的精確推論的，屬於 verification（不能升級）；參考值是 Geant4 所近似的物理模型或已發表的量測，才可能是 reference 或 sanity。
6. **證據的停止規則、格點與 chunk 數事先宣告。** 加跑、加密、重做控制組都不得依結果決定。
7. **精確而與順序無關。** 跨執行緒、chunk、機器合併的數值一律先量化成整數再累加。
8. **介面可擴充，實作只做眼前需要。** 不做通用運算式語言，不做外掛系統。
9. **先找現有實作。** 重用 `contracts/schema.py`、`tracker_resolution.py`、`multiple_scattering.py`；oracle 不 import 被測模組。
10. **最小變動。**

---

## 3. 架構總覽

```
控制平面（Python，標準函式庫）
  hep-detector      規則、參考公式、推論（MPV、batch means、精確區間、IUT、negative control）、判定、label
  adapters/geant4   spec 驗證、建置、執行、chunk、紀錄（trace.provenance()）、simulated 表格；
                    A1 起由 chunk CSV 產生 summary（A2b 起只作為 oracle）
  core              雙格式幾何存取器、trace、status
  contracts         等級與維度表、範圍、configuration 與隔離（C1）；verification、遞移的衍生模擬標記（C2）
        ▲
        │  邊界產物（JSON；小、可提交、可雜湊）
        │    summary              simulation-summary/1     （§4.2）
        │    column map           layered_sim.output/2     （§4.4）
        │    effective config     引擎無關外框 + 幾何樹     （§4.3）
        │
資料平面（C++）
  SimSummary.hh     只依賴標準函式庫：量化、雙字組 128 位元整數累加器、合併、JSON 寫出
  SimProbe.hh       依賴 Geant4：探針（設定與幾何樹）；layered_sim 與使用者的 Geant4 應用共用
  layered_sim       連結 Geant4：模擬、scorer、在事件結束時累加觀測量；逐事件 CSV；
                    `convert` 子命令（spec/1 → spec/2）；（B0）逐事件 ROOT 檔；（B1）場與平面穿越
  simroot           （B0）只連結 Geant4 的 analysis 函式庫：ROOT 檔的 info / dump / hash
  simreco           （B1）不連結 Geant4：逐事件數位化與重建，輸出 summary 與逐事件結果
  其他後端           使用者的 Geant4 應用（引入 SimSummary.hh 與 SimProbe.hh）或其他引擎，交出同樣的三個邊界產物
```

| 元件 | 語言 | 階段 | 依賴 |
|---|---|---|---|
| 契約變更 | Python | A1（C1）、B1（C2） | — |
| hep-detector 的推論與判定 | Python | A1 | — |
| summary 的 Python 產生器（由 chunk CSV） | Python | A1；A2b 起只在測試中作為 oracle | — |
| `core/geometry/layered.py` | Python | A2a | — |
| `layered_sim`（含 `convert`） | C++ | A2a | Geant4 |
| `SimProbe.hh` | C++ | A2a | Geant4 |
| `SimSummary.hh` | C++ | A2b | 只有標準函式庫 |
| `simroot` | C++ | B0 | Geant4 analysis（g4tools） |
| `simreco` | C++ | B1 | 標準函式庫、`SimSummary.hh`、`MiniJson.hh` |

名詞：**effective spec** 是 `layered_sim` 實際執行的 spec/2（由 spec/1 轉換或使用者直接給出）；**effective config** 是探針讀到的實際設定（§4.3）。

---

## 4. 介面

### 4.1 spec/2

| 區塊 | 內容 | 階段 |
|---|---|---|
| 座標 | 世界中心為原點，堆疊軸 x，mm；`at_mm` 是元件**未平移**的前表面世界座標，平移另存於 `shift_mm`（中心 = (`at_mm` + t/2) + `shift_mm`，和舊 `Detector.cc` 的運算順序相同）；巢狀一層 | A2a |
| `elements`、`materials` | 元件、材料（含混合材料，順序保留） | A2a |
| `field` | A2a 只預留（非空時以 exit 2 拒絕）；B1 實作均勻場與精度參數 | A2a / B1 |
| `source` | 以 `type` 區分：`gun`（A2a）；`gps`、`event-file` 只定義介面（§9） | A2a |
| `output.observables` | 宣告觀測量：來源欄、量化步長 q、以 q 的整數倍表示的分格邊界與門檻；A1 起由 Python 使用，A2b 起由 C++ 使用；組合與選擇只定義介面（§9） | A1 / A2b |
| `output.event_file` | `level`：`none`（預設）、`summary`、`hits`、`crossings` | B0 / B1 |
| `run` | 執行緒、種子、事件數；`seeding`：`stream`（舊行為，spec/1 轉換的預設）或 `per-event`（A2b 起，新 spec 的預設；§4.2） | A2a / A2b |

spec/1 以 `layered_sim convert` 轉成 spec/2：同一個編譯單元沿用舊 `Detector.cc` 的浮點運算順序，輸出 `%.17g`。同主機上新舊版對 TestEm3、TestEm5 mirror 與 J14 必須逐位元相同（CSV 與每個放置的 hex-float 傾印）；因為平移另存，`shift_mm ≠ 0` 也逐位元相同。schema 只用 `contracts/schema.py` 支援的關鍵字（A2a 加入 `maxItems`、`maximum`、`exclusiveMaximum`，不升契約版本）；跨欄位規則留在 Python 的 `cross_field_checks()`。

### 4.2 summary（`simulation-summary/1`）

每個 run（每個 chunk）一份 JSON。schema 名稱與引擎無關；它和既有、由 `summarize` 產生的 `geant4-run-summary/1` 不同（後者在 A2b 後只供舊紀錄重播）。

| 欄位 | 內容 |
|---|---|
| `run` | spec 與 effective spec 的 sha256、種子與 `seeding`、chunk 索引、事件數、`summary_version`、各量化步長、產生者（`python-csv` 或 `layered_sim` 等）與其版本 |
| `observables[]` | 每個宣告的觀測量：語意名稱（對應 column map）、單位、q、累加器 |
| 量化 | 每個事件先量化：X = round(x/q)、W = round(w/q_w)，round 為**四捨六入五成雙**（C++ 以 `std::nearbyint` 在 `FE_TONEAREST` 下、Python 以 `round()`），之後只做整數運算 |
| 累加器 | `n`、`ΣW`、`ΣW²`、`ΣW·X`、`ΣW·X²`、`min X`、`max X`、`hist`（邊界為 q 的整數倍，以 X 分格；每格 ΣW 與計數；溢位與下溢分開）、`count_if[]`（門檻為 q 的整數倍；ΣW 與計數）；B1 起可有 `profile` 與二維 `hist`（§9） |
| 數值形式 | 所有和以**雙字組 128 位元整數**累加（`SimSummary.hh` 自行實作，只用標準函式庫，不依賴編譯器擴充），寫成十進位字串 |
| `merge` | 每個累加器的合併規則：`sum`、`min`、`max`、`hist` |
| `overflow` | 任何累加溢位時為 true；這個 run 判為 incomplete（exit 3），原因寫入紀錄 |

**權重。** `layered_sim` 的沉積已經乘上 track 權重（`Actions.cc` 行 113），而 CSV 的 `weight` 欄只是主粒子頂點的權重。為避免重複加權：A2b 要求事件權重 w = 1（違反時 exit 2），累加器保留 W 欄位作為介面；biasing 研究（含事件權重的定義）延後（§9.3）。

**事件種子（A2b）。** `seeding: per-event` 時，每個事件在開始時以 `H(chunk seed, 全域事件編號)` 重設亂數。serial 與任何執行緒數的 MT 因此得到相同的事件，summary 逐位元相同。`seeding: stream` 保留舊行為（serial 為連續亂數流；MT 由 master 分批產生每事件種子），只用於 spec/1 轉換來的 spec 與逐位元比對。

**精確性與誤差。**
- 整數加法可交換也可結合，所以結果和執行緒數、worker 合併順序、編譯器、架構都無關。MT 下以自訂的 `G4VAccumulable` 合併：worker 在自己的 `EndOfRunAction` 呼叫 `G4AccumulableManager::Merge()`，master 在自己的 `EndOfRunAction` 寫出；master 與 worker 的註冊順序相同。
- 量化誤差依每個統計量傳遞後才和該統計量的容許值比較：平均的誤差 ≤ q/2；比例與 `count_if` 沒有量化誤差（門檻是 q 的整數倍）；分位數與眾數的誤差 ≤ 分格寬度的一半加 q/2。Python 在推論時檢查。
- 預設步長：能量 1 eV、長度 1 nm、時間 1 fs、權重 2⁻²⁰。

**重算與 oracle。** A1 的 Python 產生器由 chunk CSV 依同一宣告產生 summary。A2b 起 `layered_sim` 以 `%.17g` 寫 CSV（`layered_sim.output/2` 的版本加一；舊的 `%.10g` 精度不足以重現量化）；測試中 Python 由這些 CSV 重算的 summary 必須和 `layered_sim` 寫出的逐位元相同。A2b 之前錄製的 CSV 不做這個比對。

### 4.3 effective config

```
{ "engine": "geant4", "engine_version": "11.4.3", "probe_version": "...",
  "source": "probe" | "declared", "recorded": true, "config_sha256": "...",
  "geometry": { "tree": [...], "tree_sha256": "...", "hash_scheme": "tree-v1" },
  "environment_ref": "<build record 的雜湊>",
  "sections": { "geant4": { ... } } }
```

| 部分 | 內容 |
|---|---|
| 外框 | 與引擎無關；規則依 `engine` 選擇規則包（目前只有 Geant4 的 `G4R-*`） |
| `geometry.tree` | `G4PhysicalVolumeStore` 是依建立順序的平面清單，所以由每個體積的母邏輯體積重建樹；每個放置記錄名稱、copy number、solid 類型與參數、材料（組成與密度）、轉換矩陣、母體、附加的 field manager 與參數；數值以 Python `float.hex()` 的格式寫出。replica 與 parameterised 體積記錄其參數化描述，不展開 copy |
| `sections.geant4` | `G4EmParameters::StreamInfo` 全文與解析欄位；逐 couple 的 cut 與能量閾值；逐 process、逐模型的能量範圍；run manager 型別與種子模式；`G4UserLimits`、biasing |
| 資料集 | 資料集路徑與內容雜湊只在 build／環境紀錄中計算一次；探針以 `environment_ref` 引用，不在每個 chunk 重算 |
| 時機 | master 的 `BeginOfRunAction`（在 `RunInitialization` 之後）、`G4State_GeomClosed` 且 couple 數大於 0；否則 `recorded: false`（layered_sim 仍 exit 0），該 run 視同只有宣告，不能升級 |
| 場 | field manager 是逐執行緒的；master 也會呼叫 `ConstructSDandField`，所以 `layered_sim` 的 master 能看到場。若 spec 宣告了場而 master 看不到（例如使用者應用只在 worker 設定），標記 `source: declared` |
| 路徑 | 經 `tilde()` 寫出 |

規則與 variation 的模型指派優先讀探針；只有宣告時輸出 `source: declared`；兩者都有而不一致時報錯。

### 4.4 column map（`layered_sim.output/2`）

每個觀測量與輸出欄的語意名稱、實際欄名、單位、操作定義；標明所在檔案（`csv`、`root` 的哪個 ntuple、`summary`）；附 `column_map_version`。只允許宣告式運算（改名、單位換算、加總、篩選）；需要計算的轉換必須是另一個有紀錄的步驟。

### 4.5 逐事件檔（B0）

| 項目 | 規格 |
|---|---|
| 逐事件 CSV | 摘要表（主粒子真值、各子系統總沉積）；A2b 起全精度 |
| ROOT 檔 | `layered_sim` 經 `G4AnalysisManager`（g4tools，不需安裝 ROOT）寫出；MT 下 `SetNtupleMerging(true)` 合併成一檔；扁平 ntuple、只用純量欄、每列帶鍵；結構 `layered_sim.events/1`，ntuple 有 `run`、`events`、`deposits`、`hits`，B1 加 `crossings`（`events/2`） |
| 列的順序 | 合併後不固定；讀取端一律依鍵排序 |
| 雜湊 | 檔案位元組含寫出時間，不逐位元相同；run record 同時記錄檔案 sha256（完整性）與 `simroot hash` 的 `content_sha256`（比對與 provenance）；`seeding: per-event` 時，serial 與不同執行緒數的 `content_sha256` 相同 |
| `simroot` | `info`、`dump`（依鍵排序後輸出 CSV，`%.17g`）、`hash`；只連結 Geant4 的 analysis 函式庫（`G4RootAnalysisReader`），不建立 run manager |
| 讀取端 | Python 與 `simreco` 不解析 ROOT，經 `simroot dump`；研究者可自行用 ROOT 或 uproot |
| 大小 | 不提交；run record 記錄路徑、雜湊、各 ntuple 列數與大小；`hits` 有事件數上限（`max_events_hits`，預設 100） |
| 試作 | B0 開始時先以一天確認 `G4RootAnalysisReader` 能讀 MT 合併、壓縮過的檔案與字串欄；不足時 `simroot` 只讀扁平純量欄，字串改寫 JSON 旁檔 |

### 4.6 後端介面

一個後端要進入閘門、benchmark 與 label，必須對 spec/2（或它自己的輸入，並附雜湊）交出：

1. 每個 chunk 一份 summary（§4.2）；
2. column map（§4.4）；
3. effective config（§4.3）。只有宣告（`source: declared` 或 `recorded: false`）時，研究仍可執行與發布，但不能升級。

使用者自己的 Geant4 應用引入 `SimSummary.hh` 與 `SimProbe.hh` 即可滿足。A2b 的驗收以一個**只檢查介面的合成後端**代替：測試夾具由 J14 已提交的資料產生三個邊界產物（改名欄位、不同的產生者名稱），必須通過 J14 的閘門與 benchmark；它不需要 Geant4，所以可在一般 CI 中執行。以真正的使用者 Geant4 應用驗證，是 live 測試中的選用項目。

---

## 5. 統計方法

### 5.1 chunk 與種子

每個證據 run 分成 K 個獨立 chunk，K 事先宣告、下限 16。chunk 種子為 `H(study_id, role, point_id, k)`，映射為 [1, 2³¹) 內的整數；`seeding: stream` 時 layered_sim 的第二個種子為 `start + 1`；同一研究的所有 run record 中種子對不得重複。

### 5.2 估計量與 SE

- 每個 chunk 由 summary 算 θ_k（平均、比例、比值、分位數、眾數）；回報 θ̄ = 平均。
- **預設 SE：** batch means，SE = sd(θ_k)/√K，自由度 K − 1。
- **多個觀測量：** 每個 chunk 的估計量向量一起保存；觀測量之間的共變異由這些向量估計。
- **全樣本值：** 平均與比例另由合併累加器算出，和 θ̄ 的差寫入紀錄作為診斷。
- **分位數：** X 的直方圖內線性內插；分格寬度須小於該觀測量容許值的 1/10；分位數落在溢位或下溢格時，該估計判為 incomplete。

### 5.3 計數很少時

- 適用條件：計數型估計量（比例、`count_if`）在任一 chunk 為 0，或合併總數 < 100（門檻可宣告）。
- 權重全為 1 時：比例用 Clopper–Pearson、計數用 Garwood，由合併累加器計算；兩個 run 的比較用精確條件二項法求兩個率之比的區間，相對差 = 比 − 1。
- 權重不全為 1 時：用以 n_eff 縮放的 Poisson 區間，並在紀錄中標為近似。
- 這些情況沒有 SE，閘門以區間端點判定（§5.5）；事件數規劃用試探 run 的 Poisson 變異數。

### 5.4 MPV

- 每個 chunk 的直方圖取最大分格，以它和相鄰兩格做三點拋物線內插；回報 K 個眾數的平均。
- **偏差門檻（設計時）：** 在宣告的 N/K 與分格寬度下以 toy 估計偏差，toy 的 95 % 上界須 ≤ tol/10。toy 的分布用 Landau–Vavilov，並以一次高統計 Geant4 run 的直方圖形狀核對。
- **實測核對（每次）：** θ̄ 與合併直方圖的三點內插眾數之差須 ≤ tol/5 + 2·SE；不成立時該 benchmark 判為 incomplete。

### 5.5 收斂閘門

- **差值的定義：** 相對差 diff = (a − b)/b，b 為較細的設定（沿用 `check_geant4_study.py` 行 357 的慣例）；se_diff = √(se_a² + se_b²)/|b|（兩個點是獨立的 run）；ν 以 Welch 公式逐對計算（等變異數、K = 16 時為 30，變異數比 4 時約 22）。
- **事件數目標：** 每個點的 se 目標為 tol/(4√2)，使 se_diff ≤ tol/4。
- **判定（intersection-union test）：** 通過：|diff| + t₀.₉₅(ν)·se_diff ≤ tol；失敗：|diff| − t_{1−α/m}(ν)·se_diff > tol，m 為（參數 × 觀測量）組數；其他為 unresolved。計數很少時（§5.3）改用區間端點：通過 = 90 % 區間落在 [−tol, tol] 內；失敗 = 單邊 1 − α/m 區間完全落在外側。
- **回報：** unresolved 與未達標以 `incomplete`（exit 3）回報，label 保持 `unvalidated`；只有失敗是 `failed`（exit 1）。

**操作特性**（α = 0.05，以 t(30) 與估計的 se 模擬 2×10⁶ 次；以本資料夾的 `gate_operating_characteristics.py` 重算）：

| 真實差值 | 通過（se = 目標，最壞情況） | 通過（兩階段設計下的 se 分布） | 失敗 m = 1（se = 目標） | 失敗 m = 30（se = 目標） | 失敗 m = 30（兩階段設計） |
|---|---|---|---|---|---|
| 0 | 0.976 | 0.989 | 0.000 | 0.000 | 0.000 |
| tol/2 | 0.621 | 0.830 | 0.000 | 0.000 | 0.000 |
| tol | 0.050 | 0.050 | 0.050 | 0.002 | 0.002 |
| 2 tol | 0.000 | 0.000 | 0.988 | 0.780 | 0.933 |

真實差值為 tol 時約 90 % 的結果是 unresolved，這是等價檢定的本質；文件中寫明預期的 incomplete 比例。A1 的閘門 toy 以這張表為準，容許 ±3σ_MC。

### 5.6 兩階段事件數

N = ceil(N_trial·(SE_trial/target)²·f)，f = F₀.₉₀(K − 1, K_trial − 1)（兩者都是 16 時 ≈ 1.97）。在這個設計下約 10 % 的證據 run 會未達標，未達標判為 incomplete，不得補跑；若要降低這個比例，改用 F₀.₉₅（16 與 16 時 ≈ 2.40；§11.2 第 8 項）。

### 5.7 negative control 與偵測極限

- 判定量為觀測量上的位移 shift = (control − nominal)/reference，SE 由兩個 run 合成。
- **偵測極限：** DL = tol + |rel| + t_{0.977}(ν)·se_rel，即「在已觀測的偏差下，以 97.7 % 的檢定力抓到」的最小注入量。
- **設計要求：** 以 toy 證明在 DL 注入時抓到的機率 ≥ 0.977；這是 A1 的驗收條件。
- **實現的控制組：** 正負兩個方向都注入（否則宣稱限縮為單向）；位於偵測極限的條件為 caught 且 |shift| ≤ 1.1 × DL。單次實現未抓到時，記錄為發現並說明，不自動使 A1 失敗；不得換種子重跑。

### 5.8 停止規則、證據相關性與跨平台

- 停止規則、掃描格點、K、unresolved 的處理在第一個證據 run 前寫入 study spec。
- `extension.study.evidence_overlap` 列出被多個判定共用的 run。
- Python 的 `math` 函式依賴平台的數學函式庫，t、F 與精確區間的分位數在不同平台上最後一位可能不同。重播的逐位元相同只在 CI 平台上要求；跨平台以相對差 ≤ 1e-12 比較。

刪除：計數器雜湊 bootstrap、全域唯一事件鍵與其重複檢查、第二個兩階段係數（1.2）。

---

## 6. 契約

### 6.1 benchmark 表（C1）

`contracts/validate.py` 自帶表格，`_study_upgrade` 只從表取得等級、kind 與範圍維度：

| benchmark | 等級 | 支持的 kind | 範圍維度 |
|---|---|---|---|
| `stopping-power` | reference | `stopping-power` | particle、material、energy、thickness |
| `range` | reference | `range` | particle、material、energy、thickness |
| `thin-layer-mpv` | reference | `most-probable-value` | particle、material、energy、thickness |
| `thin-layer-width` | sanity | `thin-layer-width` | particle、material、energy、thickness |
| `multiple-scattering` | sanity | — | — |
| `em-shower-shape` | sanity | — | — |
| `shower-containment` | sanity | — | — |
| `longitudinal-profile` | reference | `shower-maximum` | particle、energy、目標雜湊 |
| `published-data` | interface | — | — |

紀錄中的 `grade` 和表不一致、或名稱不在表中，判為 error（適用所有帶 Geant4 study 區塊的紀錄）。`geant4_benchmarks.py` 的 `GRADES` 保留給工具，以測試確保一致。

### 6.2 範圍（C1）

- 比對受控的 `observable.kind`；`label` 把它寫入 `declared_scope.observable_kind`。
- 維度清單**依 benchmark 宣告**（6.1 的第四欄），每個維度有型別：類別（例如 particle）或數值區間（例如 energy）；純量視為 [v, v]。新的用例加入維度時只改表格（資料），比對邏輯不變。
- 宣告範圍缺少 benchmark 有的維度，視為超出範圍。
- 以目標雜湊為維度的 benchmark，宣告範圍必須帶相同的 `target_geometry_sha256` **與相同的 `hash_scheme`**。
- 閘控：`strict or _at_least(contract_version, C1)`，無 warning 分支；3.5.0 以下的紀錄只在 `--strict` 下受約束。

### 6.3 configuration 與隔離（C1）

- **目標**：benchmark 設定宣告 `target_slabs`（A1）或目標體積清單（A2a 起，對應幾何樹中的放置）。
- **真空**：世界材料為 `G4_Galactic`，或密度 < 1e-20 g/cm³。
- **isolated**：世界是真空，世界以外的每個放置都屬於目標；場只附加在目標內的體積上時，屬於目標的一部分並計入目標雜湊；場延伸到目標以外則為 embedded。
- **推導來源與雜湊版本：**

| 階段 | 推導自 | `hash_scheme` | 正規形式 |
|---|---|---|---|
| A1 | `layered_sim` 的 spec（對 `layered_sim` 而言 spec 就是實際幾何，A2a 以放置傾印證明） | `spec-v1` | 依序的 slab、厚度、橫向尺寸、材料名稱與宣告的組成；數值以 `float.hex()` |
| A2a 起 | effective config 的幾何樹 | `tree-v1` | 依序的放置、solid 參數、Geant4 解析後的材料組成與密度、轉換、附加的場；數值以 `float.hex()` |

- 比對只在相同的 `hash_scheme` 之間進行；`dependencies.py` 依紀錄中的 `hash_scheme` 重新推導。A2a 起新的紀錄使用 `tree-v1`；`spec-v1` 的紀錄繼續有效，但不能和 `tree-v1` 的 benchmark 比對（J14 不使用目標雜湊維度，所以不受影響）。
- 其他後端只有宣告時，可以執行與發布，但不能升級。
- **契約規則**：每個被計入的 benchmark 必須是 `isolated`；`dependencies.py` 必須從 `evidence_records` 中的 run record 重新推導 configuration 與雜湊並比對。

### 6.4 C2（B1）

- 表格加入 `verification` 等級與 J15 的檢查；只有 reference 會被計入。
- **遞移的衍生模擬標記**：simulated 表格的輸入鏈可以有任意層（模擬 → 數位化 → 重建 → 分析），只要每一層都是有紀錄的 computational-run，而且鏈的每個根都是模擬 run。
- 閘控方式同 C1。

### 6.5 sci-fix 與 advisory（A1）

| 缺陷 | ledger 條目 | 等級 |
|---|---|---|
| D1（含依 benchmark 宣告的範圍維度） | scope-kind | S2 |
| D2 | grade-table | S2 |
| D3（含偵測極限的新定義） | control-shift | S2 |
| D4（含差值與 se 的定義） | gate-IUT | S2 |
| D5（含 batch means 取代 bootstrap、精確計數區間、可宣告的 K、MPV 內插） | variance-method | **S1** |
| 隔離定義（含場的規則與真空的定義） | isolation | S2 |
| D6 | stopping-rule | S3 |

S1 與 S2 各發一份 advisory（鍵 `artifact_types: [computational-run]`、`extension_keys: ["study", "evidence_records"]`；introduced 0.20.0）。simulated dataset-record 無法用鍵區分，remedy 要求持有者對每個 simulated 表格執行 `contracts/dependencies.py`。

---

## 7. 程式與 CI

| 位置 | 變更 |
|---|---|
| `contracts/validate.py`、`dependencies.py` | 6.1–6.4 |
| `contracts/schema.py` | `maxItems`、`maximum`、`exclusiveMaximum`；`test_schema_keywords.py` 也掃描 adapter 的 schema |
| `contracts/schemas/ext_computational_run.json` | 選用的自由格式屬性 `simulation`（需 hep-computing 同意） |
| `skills/hep-detector/scripts/` | 推論與判定（§5），只讀 summary；不新增腳本，`SKILL.md` 與 description 不改 |
| `core/geometry/layered.py` | 雙格式幾何存取器（steward hep-detector） |
| `adapters/geant4/assets/` | `geant4_run.py`（`chunk` 依 §5.1 的種子、A1 起由 chunk CSV 產生 summary、B1 加 `reco` 與 `table`）、`layered_sim/`（`convert`、`seeding`、累加、全精度 CSV、B0 事件檔、B1 場與穿越）、`SimSummary.hh`、`SimProbe.hh`、B0 `simroot`、B1 `simreco` |
| `SIM_SOURCES` | 隨新原始碼更新，讓 `sources_sha256` 涵蓋全部 |
| CI | 任務 A 不需要新的必要 CI 工作；`SimSummary.hh` 的 ctest 可作為選用工作。B1 的 `simreco` 需要必要的 C++17 CI 工作 |
| trace | 新的紀錄寫入者呼叫 `trace.provenance()`；新的共用函式呼叫 `trace.tag()`；呼叫 C++ 執行檔時記錄執行檔與原始碼的 sha256、版本、子命令 |

---

## 8. 階段與驗收

### 8.0 J14 在各階段的錄製內容

| 階段 | 新增或改變的 recorded 內容 | 重播 |
|---|---|---|
| 目前 | 5 個 run 的單一縮減 CSV（`events/`，5 欄）；13 個掃描與 variation run 只有 `geant4-run-summary/1`（一個值加 bootstrap SE）；共 2.6 MB | 純 Python |
| A1 | 所有證據 run（掃描、variation、nominal、控制組）都以 K = 16 chunk live 重錄；每個 chunk 提交 Python 產生的 `simulation-summary/1`（約數 kB）；benchmark run 另保留縮減 CSV。預估總量仍在數 MB 內，實際值在 A1 中量測並受 `check_packaging.py` 限制 | 由 summary，純 Python |
| A2a | 每個 run 的 effective config；同主機逐位元比對的紀錄 | 同上 |
| A2b | live 重錄：`seeding: per-event`、C++ 產生的 summary、全精度 CSV（用於 oracle 測試） | 由 summary，純 Python |

### A1 正確性修正（contracts C1，sci-fix）

**內容：** §6.1–6.3（A1 以 spec 推導，`hash_scheme: spec-v1`）、§6.5；§5 的全部統計規則；summary schema 第一版與 Python 產生器（由 chunk CSV）；D8 enum、D10 測試、protocol 第 4 節；`simulation` 屬性。

**驗收：**
- [ ] kind 不符、宣告缺少維度、等級與表不符、configuration 缺少或 embedded、目標雜湊或 `hash_scheme` 不符的紀錄，在 `--strict` 與 C1 下被拒；`dependencies.py` 重新推導不符時被拒。
- [ ] 重產的 J14 study record 通過 `validate.py --strict` 與 `dependencies.py`；判定的任何改變都記錄並說明原因。
- [ ] 閘門 toy（每格 10⁴ 次）和 §5.5 的表一致到 ±3σ_MC；unresolved 以 exit 3 回報；計數很少時的區間判定有測試。
- [ ] batch means 覆蓋率 toy：J14 各類估計量（平均、比例、分位數、眾數）的名義 90 % 區間，實際覆蓋率滿足 |覆蓋率 − 0.90| ≤ 0.02 + 3σ_MC，逐類回報。
- [ ] MPV：偏差 toy 的 95 % 上界 ≤ tol/10；每次的實測核對（§5.4）生效。
- [ ] 偵測極限：toy 證明在 DL 注入時抓到的機率 ≥ 0.977；J14 的實現控制組結果記錄於 VALIDATION。
- [ ] `python3 -m unittest discover -s tests/contracts -t .` 沒有錯誤。
- [ ] ledger、兩份 advisory 通過 `scifix_advisories.py check`；VALIDATION GEANT4-CORRECTNESS；CHANGELOG；release manifest。

### A2a spec/2 與探針（adapter 0.2.0）

**內容：** §4.1（`field` 預留、`source.type = gun`、`shift_mm` 另存）、`layered_sim convert`、§4.3 探針（`SimProbe.hh`）、雙格式存取器、schema 關鍵字與 `cross_field_checks()`。

**驗收：**
- [ ] 同主機逐位元相同（CSV、放置傾印），包括 `shift_mm ≠ 0` 的 spec。
- [ ] 非空的 `field` 以 exit 2 拒絕。
- [ ] J14 每個 run 都有 effective config；`tree-v1` 推導的 configuration 和 `spec-v1` 推導的一致（雜湊不同、判定相同）；故意的不一致被抓到。
- [ ] 探針在錯誤時機（測試指令）寫出 `recorded: false`，該 run 不能升級。
- [ ] 存取器對 spec/1 與 spec/2 結果一致；兩條薄層規則在兩種格式下都觸發。
- [ ] `contracts.schema.validate()` 加 `cross_field_checks()` 的結論和原 `validate_spec()` 一致。
- [ ] J14 在 E2 重錄；VALIDATION GEANT4-SPEC2。

### A2b summary 由 C++ 產生與後端介面（adapter 0.3.0）

**內容：** `SimSummary.hh`、事件中累加與 MT 合併、`seeding: per-event`、全精度 CSV、column map；J14 live 重錄；合成後端測試。

**驗收：**
- [ ] `seeding: per-event` 下，同種子的 serial 與 1、2、4 執行緒 MT run，summary 逐位元相同。
- [ ] 任何順序合併 chunk summary 的結果相同，且等於 Python 由這些 chunk 的全精度 CSV 累加的結果。
- [ ] Python 由全精度 CSV 重算的 summary 和 `layered_sim` 寫出的逐位元相同（量化、捨入、分格與門檻的約定都經測試）。
- [ ] 溢位被偵測並判為 incomplete；事件權重 ≠ 1 時 exit 2；量化誤差依統計量檢查生效。
- [ ] J14 離線重播在 CI 平台上逐位元重現已提交輸出，且在沒有編譯器的環境中執行。
- [ ] 合成後端（只交出三個邊界產物）通過 J14 的閘門與 benchmark。
- [ ] 正式程式中 summary 只由 C++ 產生；Python 產生器只在測試中作為 oracle。
- [ ] VALIDATION GEANT4-SUMMARY；CHANGELOG；release manifest。

### B0 逐事件 ROOT 檔（adapter 0.4.0）

**內容：** §4.5；先做 `G4RootAnalysisReader` 試作。

**驗收：**
- [ ] `level = none` 時輸出與 A2b 逐位元相同；開啟 `summary` 不改變 CSV 與 summary。
- [ ] `simroot` 往返：各層級、I、D、S 欄的值逐位元相同；`seeding: per-event` 下 serial 與不同執行緒數的 `content_sha256` 相同。
- [ ] ROOT 檔的 `deposits` 依事件加總等於 CSV 的子系統總沉積；`hits` 超過上限時 exit 2；run 中斷時 incomplete。

### B1 J15 最小磁譜儀（adapter 0.5.0、contracts C2）

**內容：** J15 的設計見 `task-b-j15.md` §4（幾何、參數、接受度：B = 0.5 T、六片 Si、每站兩層 TOF、50 層 Pb/PVT 量能器）；場（`ConstructSDandField`、thread-local、`delta_intersection` 1e-5 mm、DormandPrince745）；平面穿越 scorer 與 `crossings` ntuple；`simreco`（輸出 summary 與逐事件結果）；驗證梯（`field-propagation` 等）、確定性場檢查、量能器 cut 收斂、variation；`verification` 與遞移標記（C2）；J15 journey 與路由案例。

**驗收：** 見 `task-b-j15.md` §10，另加：
- [ ] `simreco` 的 summary 通過與 A2b 相同的逐位元與重算測試。
- [ ] 三層以上的輸入鏈（模擬 → 重建 → 表格）被 `dependencies.py` 接受；根不是模擬 run 時被拒。

---

## 9. 通用性

### 9.1 涵蓋的用例

| 用例 | 由什麼支援 | 狀態 |
|---|---|---|
| 材料層級的參考（J14 類） | §6.1 表、孤立平板 | A1 |
| 有場的磁譜儀（J15、太空與宇宙線探測器） | 場計入目標（§6.3）、`verification`、重建鏈 | B1 |
| 試束或對撞機模組（非平板、與數據比較） | 幾何樹推導 configuration；依 benchmark 宣告範圍維度；以目標雜湊對應已發表量測的配置 | 契約在 A1、A2a 已就緒；`layered_sim` 本身仍是平板（使用者應用可用） |
| 稀有事件 | 精確計數區間 | A1 |
| biasing、事件權重 | 累加器的 W 欄位（介面） | 介面在 A2b；A2b 要求 w = 1，權重的語意與規則延後 |
| 其他引擎、快速模擬、ML 代理模型 | 三個邊界產物、引擎無關的 effective config 外框 | 介面在 A2a、A2b；規則包延後 |

### 9.2 現在只定義介面的項目

| 介面 | 內容 | 第一個用例 |
|---|---|---|
| 觀測量的組合與選擇 | 欄位的線性組合、兩欄之比；欄位與常數比較的 AND 選擇。再複雜就是有紀錄的程式步驟 | 第一個需要事件選擇的研究 |
| profile 與二維直方圖 | 依 x 分格的 n、ΣW·Y、ΣW·Y²；二維 ΣW | 第一個能譜源研究（例如解析度對連續剛度）；J15 以固定剛度執行，不需要 |
| 粒子源 | `gps`（`G4GeneralParticleSource`，只允許宣告式設定）、`event-file`（HepMC 等）；summary 記錄通量歸一化所需的源面積與立體角 | 第一個能譜或通量研究 |
| `simreduce` | 讀 ROOT 事件檔，依宣告輸出 summary，讓事後決定的觀測量不必重跑模擬 | B0 之後的第一個需要 |

### 9.3 延後（附觸發條件）

| 項目 | 觸發條件 |
|---|---|
| `layered_sim` 支援非平板幾何（GDML、圓柱、旋轉） | 第一個需要非平板、又不能用使用者應用的研究 |
| 其他引擎的規則包與探針 | 第一個非 Geant4 的後端 |
| biasing 與事件權重（權重語意、n_eff 下限、相關規則） | 第一個使用 biasing 的研究 |
| 光學光子、長時間窗、衰變鏈 | 第一個閃爍體或稀有事件研究 |
| 離子源與 Birks（J16） | 宇宙線核素研究，且 PVT 的 Birks 常數有文獻紀錄 |
| 多個 Geant4 版本的探針 | 第一個使用 11.4 以外版本的應用 |
| `physics_config_comparison` | 需要比較物理設定的研究 |
| RNTuple、vector 欄 | ROOT 檔大小或讀取速度成為瓶頸 |
| 一般化 `scoped_upgrade` | 第二種研究類型需要升級 |

### 9.4 刻意不做

- 通用的運算式語言（會變成第二個需要驗證的程式語言）。
- 估計量的外掛系統（估計量是少量、有測試的 Python 函式）。
- 跨引擎的統一探針內容（只統一外框）。
- 自適應分格或近似分位數草圖（合併結果和順序有關，破壞精確性）。
- 依 SE 自適應停止、以加密掃描作為證據、未抓到時換種子重跑控制組（optional stopping）。
- `uses-validated-physics` label、contracts 4.0、Python 綁定、內容定址快取。
- 把統計移到 C++（`simstat`）、不連結 Geant4 的 `simcore` 專案（任務 A 不需要）。

---

## 10. 殘餘風險

1. J14 的偵測極限可能因 batch means、t 分位數與觀測量單位的控制組而改變，需要重新設計控制組。
2. batch means 對偏斜分布的比值、分位數與眾數有 O(1/每個 chunk 的事件數) 的偏差，不隨 K 減少；覆蓋率 toy 以 ±0.02 容許，必要時加大每個 chunk 的事件數。
3. 兩階段設計下約 10 % 的證據 run 會未達標而判為 incomplete（§5.6）。
4. MPV 的偏差 toy 用模型分布；實測核對（§5.4）是第二道防線。
5. 自訂 `G4VAccumulable` 的 MT 合併已依 11.4.3 原始碼確認介面，仍需 MT 測試確認行為。
6. A1 需要以 K = 16 chunk live 重錄 J14 的所有證據 run；Geant4 初始化時間與 recorded 大小在 A1 中量測。
7. 探針假設 worker 與 master 設定相同；若發現 thread-local 差異，改為逐執行緒傾印。
8. 以目標雜湊對應已發表量測時，契約只能比對雜湊，無法判定目標就是論文中的配置；仍需審查者核對。
9. `G4RootAnalysisReader` 的讀取能力未驗證（B0 試作）。
10. quick load 只剩 931 bytes；J15 不改 `SKILL.md` 與 description。
11. 工作量：原型估計 A1 的契約部分約 8–12 個工作天，另加 Geant4 執行時間；統計方法與 summary 產生器的改變、A2a、A2b、B0、B1 未估計。

---

## 11. 決策紀錄

### 11.1 使用者已決定

| 日期 | 決定 | 在本架構中的位置 |
|---|---|---|
| 2026-10-22 | 核心程式用 C++，Python 作為介面；計算核心用 C++、參考值留在 Python；以獨立執行檔交換 JSON/CSV，不用 Python 綁定 | §2.3 原則 2（依 11.2 第 1 項的詮釋） |
| 2026-10-22 | J15 的 TOF1、TOF2 各兩層，四層同材料 | B1 |
| 2026-10-22 | 詳細的逐事件資訊存成 ROOT 檔 | §4.5、B0 |
| 2026-10-22 | J15 與其他部分拆成兩個任務，J15 後做 | 任務 A（A1、A2a、A2b）、任務 B（B0、B1） |

### 11.2 本文件的提議（需要使用者確認）

1. **語言分工的詮釋：** 「核心」指逐事件的計算，在 C++；對 summary 的推論在 Python。不做 `simstat` 與 `simcore` 專案。
2. **邊界產物改為 `simulation-summary/1`**（事件中量化、128 位元整數累加、自帶合併規則）；A1 由 Python 從 chunk CSV 產生，A2b 改由 C++ 產生；J14 以 summary 重播。
3. **所有 SE 改用 batch means**（K ≥ 16，可宣告），刪除 bootstrap；計數很少時用精確區間；MPV 用三點內插並設偏差門檻與實測核對；偵測極限改用 t 分位數。這擴大 D5 的 sci-fix（S1）。
4. **ROOT 檔與 `simroot` 移到 B0**，和第一個使用者 `simreco` 一起做。
5. **五個階段**（A1、A2a、A2b、B0、B1），各自單獨合併。
6. **通用化放進 C1：** 範圍維度依 benchmark 宣告、場計入目標的隔離定義、目標雜湊帶版本；configuration 在 A2a 起由幾何樹推導；effective config 採引擎無關外框；衍生模擬標記在 C2 改為遞移。
7. **A2b 的 `seeding: per-event`**（每個事件以 H(chunk seed, 事件編號) 重設亂數），讓 serial 與 MT 的結果相同；舊的 `stream` 只保留給 spec/1 轉換與逐位元比對。
8. 兩階段係數用 F₀.₉₀（約 10 % 未達標）或 F₀.₉₅（約 5 %，事件數多約 22 %）。
9. 預設量化步長（1 eV、1 nm、1 fs、權重 2⁻²⁰）與精確區間的切換門檻（任一 chunk 為 0 或總數 < 100）。

### 11.3 待維護者決定

1. C1 的版本歸類（建議 minor 加 sci-fix）。
2. 同主機也無法逐位元相同時，是否接受統計比對。
3. G5「未複製範例程式碼」的確認方式。
4. hep-computing 同意 `simulation` 屬性與 C2 的遞移衍生模擬標記。
5. B1 的 `simreco` 需要一個必要的 C++17 CI 工作。
6. ROOT 檔的存放位置與保留期限。
7. A1 的 J14 live 重錄量（所有證據 run 改為 16 chunk）與 recorded 大小的上限。

---

## 12. 和現行任務規格的對照與後續

| 現行規格 | 本架構 |
|---|---|
| `task-a-core.md` A1.1–A1.3（契約） | A1，加上依 benchmark 宣告的範圍維度、場與真空的隔離定義、`hash_scheme` |
| A1.4–A1.10（統計與其他修正） | A1，bootstrap 改為 batch means、差值與 se 的定義、精確區間、MPV 內插與兩道偏差檢查、t 分位數的偵測極限、K 可宣告；summary schema 與 Python 產生器 |
| A1.11（sci-fix） | §6.5（D5 擴大為 variance-method；新增 isolation 條目） |
| A2.2–A2.7（spec/2、轉換、存取器、schema、探針、column map） | A2a（轉換改為 `layered_sim convert`；`shift_mm` 另存；探針加外框與幾何樹） |
| A2.8（`simcore`、`simstat`） | 刪除；推論留在 Python；A2b 改由 C++ 產生 summary |
| A2.9–A2.10（ROOT 檔、`simroot`） | B0 |
| `task-b-j15.md` 全部 | B1（`crossings` 在 B0 定義介面、B1 實作；`simreco` 輸出 summary；C2 標記改為遞移） |

**核准後的步驟：**
1. 依本文件改寫 `task-a-core.md`（A1、A2a、A2b）與 `task-b-j15.md`（B0、B1），中英兩版同步，沿用目前的實作規格格式（任務卡、名詞、硬性限制、工作項、驗收、執行步驟）。
2. 更新 `README.md`。
3. 對改寫後的規格再做一次獨立審查。

---

## 13. 第三次深度檢查（2026-10-22）

### 13.1 方法

兩位沒參與撰寫的審查者分別檢查統計設計（含以 2×10⁶ 次模擬重算操作特性）與 Geant4 和實作的可行性（含讀 Geant4 11.4.3 原始碼與本 repo 的程式）；撰寫者另外列出自己的發現，並以程式核對審查者的主要宣稱：CSV 以 `%.10g` 寫出（`Actions.cc` 行 23）、沉積已乘 track 權重（行 113）、`recorded/` 的內容（5 個縮減 CSV、其餘只有單值摘要，2.6 MB）、閘門的相對差（`check_geant4_study.py` 行 357）、偵測極限公式（`geant4_benchmarks.py` 行 274）、平移的運算順序（`Detector.cc` 行 89）。

### 13.2 發現與處理

| # | 發現 | 來源 | 處理 |
|---|---|---|---|
| R1 | 操作特性表用 z 與已知 se 算出，和規則（t、估計的 se）不符；A1 的閘門 toy 驗收因此不可能通過（m = 30 的格差約 16σ） | 統計審查（CONFIRMED） | §5.5 表改為 t 與估計 se 的值，並加兩階段設計下的值 |
| R2 | 表假設 se = 目標，兩階段設計實際上約 10 % 未達標、平均 se 約 0.18 tol | 統計審查 | §5.5 表加一欄；§5.6 寫明未達標比例；§11.2 第 8 項 |
| R3 | 精確區間沒有 se，閘門與事件數公式在計數很少時沒有定義；兩個計數的差沒有精確方法 | 撰寫者、統計審查 | §5.3、§5.5 改以區間端點判定；比較用條件二項法 |
| R4 | 精確區間不適用於加權計數 | 統計審查 | §5.3 只在權重全為 1 時使用 |
| R5 | 量化誤差上限 n·q/2 拿和的誤差比平均的容許值；乘積、捨入方式、分格是否量化都沒定義 | 統計與可行性審查 | §4.2 定義先量化再整數運算、五成雙捨入、分格與門檻為 q 的整數倍、誤差逐統計量傳遞 |
| R6 | 閘門的差值（絕對或相對）、se 與每點目標沒有定義 | 統計審查 | §5.5 定義相對差、se_diff 與每點目標 tol/(4√2) |
| R7 | 偵測極限沒有隨新方法重新定義；單次控制組實現有 3–5 % 機率漏抓 | 統計審查 | §5.7 改用 t_{0.977}；以 toy 驗證檢定力；單次未抓到記錄而不失敗、不換種子 |
| R8 | 覆蓋率驗收以精確 0.90 為虛無假設，偏斜估計量的 O(1/n) 偏差會讓它在 toy 夠多時失敗 | 統計審查 | §8 A1 改為 ±0.02 + 3σ_MC，逐類回報 |
| R9 | MPV 偏差 toy 用模型分布，不代表 Geant4；toy 本身的不確定度沒規則 | 統計審查 | §5.4 用 95 % 上界並以高統計 Geant4 核對；加每次的實測核對 |
| R10 | 分位數落在溢位格、試探 run 的 K 不同、Welch ν 不一定是 30 | 統計審查 | §5.2、§5.6、§5.5 |
| R11 | serial 與 MT 不可能逐位元相同（serial 不逐事件重設種子）；「合併 chunk 等於單一 run」不成立 | 撰寫者、可行性審查（CONFIRMED） | 新增 `seeding: per-event`（§4.1、§4.2）；A2b 驗收改寫 |
| R12 | 以 `%.10g` 的 CSV 無法逐位元重算量化後的 summary | 可行性審查（CONFIRMED） | A2b 起 CSV 以 `%.17g`；oracle 只用之後錄製的 CSV |
| R13 | 沉積已乘 track 權重，ΣW·X 會重複加權 | 可行性審查（CONFIRMED） | A2b 要求事件權重 = 1；權重語意延後 |
| R14 | J14 的 `recorded/` 不足以支援 A1 的 batch means；A2b 需要 live 重錄；「J14 判定不變」和控制組可能重設計矛盾 | 撰寫者、可行性審查（CONFIRMED） | 新增 §8.0 各階段的錄製內容；A1 起 summary 由 Python 產生並提交；驗收改為「改變需記錄並說明」 |
| R15 | spec 推導與幾何樹推導的目標雜湊必然不同；「真空」與 hex-float 的寫法沒定義 | 撰寫者、可行性審查 | §6.3 加 `hash_scheme`（`spec-v1`、`tree-v1`）、真空定義、`float.hex()` 格式 |
| R16 | int128 是編譯器擴充，不是標準 C++17；Python 與 C++ 的預設捨入不同 | 統計與可行性審查 | §4.2 自行實作雙字組 128 位元整數；兩邊都用五成雙 |
| R17 | Python 的數學函式依平台，重播不是跨機器逐位元相同 | 可行性審查 | §2.1、§5.8：逐位元只在 CI 平台；跨平台相對差 ≤ 1e-12 |
| R18 | `shift_mm ≠ 0` 時新的中心算法和舊的運算順序不同 | 可行性審查（CONFIRMED） | §4.1 平移另存，運算順序相同 |
| R19 | 「探針標頭」不在元件表；「第二後端」若要通過物理 benchmark 必須是 Geant4 應用，需要 Geant4 的 CI | 可行性審查 | §3 加 `SimProbe.hh`；§4.6 改為只檢查介面的合成後端 |
| R20 | 每個 chunk 雜湊數 GB 的資料集太昂貴；field manager 逐執行緒，master 可能看不到 | 可行性審查 | §4.3 資料集只在 build 紀錄雜湊；看不到場時標記 declared |
| R21 | `G4PhysicalVolumeStore` 是平面清單；replica 與 parameterised 體積的 copy number 有歧義 | 可行性審查 | §4.3 由母邏輯體積重建樹；參數化體積記錄描述 |
| R22 | `G4AccumulableManager::Merge()` 只在 worker 上作用，合併順序依 worker 結束順序 | 可行性審查（CONFIRMED） | §4.2 寫明呼叫位置與註冊順序；整數累加使順序無關 |
| R23 | MT 的每事件種子是分批產生，不是全部「預先」 | 可行性審查（CONFIRMED） | §4.2 用詞更正 |
| R24 | 名詞：effective spec 與 effective config 混用；`layered_sim.summary/1` 名稱綁後端，且和 `geant4-run-summary/1` 衝突；`recorded: false` 的效果未定義 | 可行性審查 | §3 名詞說明；改名 `simulation-summary/1`；`recorded: false` 不能升級 |
| R25 | 觀測量之間的相關「自動處理」只在保存每個 chunk 的估計量向量時成立 | 統計審查 | §5.2 寫明 |

### 13.3 尚未處理

- 本次修正後的文字沒有再經獨立審查；改寫任務規格後一併審查（§12 第 3 步）。
- 審查者的模擬程式已放入本資料夾（`gate_operating_characteristics.py`，需要 numpy 與 scipy，只作設計輔助）；改寫任務規格時，把操作特性的 toy 以標準函式庫重寫並納入 A1 的測試。
