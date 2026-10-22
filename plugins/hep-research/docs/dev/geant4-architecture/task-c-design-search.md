# 任務 C：自動化探測器設計搜尋

> 文件類型：設計提案與實作規格（給執行的 agent 與審查者）。狀態：提案，待使用者與維護者核准
> 依據：[`architecture.md`](architecture.md)（模擬架構）、[`task-a-core.md`](task-a-core.md)（統計與邊界產物）、[`task-b-j15.md`](task-b-j15.md)（`element_sim`、`simreco`、J15）
> 順序：C1 只需任務 A；C2 在任務 B 合併後才開始
> 日期：2026-10-23
> 語言：繁體中文原文；英文版 [`task-c-design-search.en.md`](task-c-design-search.en.md) 內容相同。兩者不一致時以中文為準，並同時修正英文
> 一句話：使用者寫下物理需求；Claude 從一份元件目錄自由選擇探測器結構種類並組合，最佳化器在多保真度的模擬上搜尋，最後以獨立的確認 run 回報符合需求的最佳設計與取捨

---

## 0. 任務卡

**目標。** 讓 AI 從「物理需求」出發，自行選擇探測器結構種類（徑跡平面、磁場區、TOF、量能器、被動層……）並自由組合與調整參數，得到符合需求的最佳化設計（或一組取捨的 Pareto 前緣），而且結果經得起統計與來源的檢查。

**兩個階段：**

| 階段 | 內容 | 前提 | 版本 |
|---|---|---|---|
| **C1** 需求、文法與快速搜尋 | 需求規格與設計文法的 schema；元件目錄第一版；設計 → `element_sim.spec/1` 的實現；F0 解析評估；標準函式庫的搜尋器（Sobol、NSGA-II）；搜尋紀錄；封閉測試 | 任務 A 合併；`element_sim.spec/1` 的 schema（B1.1）可先以草案使用 | 新 adapter `detector-design` **0.1.0** |
| **C2** 模擬評估與確認 | F1、F2 評估（`element_sim` 與 `simreco`）；確認 run；穩健性與「利用模擬缺陷」的防護；選用的 MOBO 後端；契約 C3；J16 自動設計範例 | 任務 B 合併 | adapter **0.2.0**、contracts **C3**（minor） |

**不在範圍內：** 可微分模擬與可微分代理模型（MODE 路線，§9）；非盒狀幾何（圓柱形對撞機探測器）；光學物理（Cherenkov、RICH）；強化學習；讓 LLM 單獨決定最佳設計。

**交付物：** `adapters/detector-design/`（schema、目錄、實現、評估、搜尋、報告）；hep-detector 的 reference `detector-design-search.md`（含 agent 協定）；搜尋紀錄的契約規則（C3）；封閉測試；J16 範例；VALIDATION 條目 DESIGN-SEARCH-F0（C1）與 DESIGN-SEARCH（C2）；CHANGELOG；release manifest。

**完成的定義：** C1.9 與 C2.9 的驗收清單全部打勾；任務 A §9 的檢查全部通過。

**主要決定：**
1. **Claude 是設計者，不是裁判。** Claude 選結構種類、提出種子設計、劃定搜尋範圍、解讀結果；但「哪個設計最好、是否符合需求」只由有紀錄的評估與統計判定。Claude 的提案和隨機產生的候選走同一條評估管線，沒有特權（§5.1）。
2. **自由組合，但在文法之內。** 結構的自由度來自「元件目錄 × 組合規則」：任何通過有效性規則的元件序列都是合法設計。新的元件種類只能經由審查過的目錄變更加入，不能在一次搜尋中臨時發明（§5.3）。
3. **多保真度。** F0 解析式（每個設計微秒級）篩選 10⁴–10⁶ 個設計；F1 少量事件的 Geant4 細化數百個；F2 完整統計只給少數決選者（§5.4）。這是 AID(2)E、dRICH 與 MODE 研究的共同做法。
4. **搜尋與確認分開。** 搜尋階段的數值有「贏家詛咒」（從許多帶雜訊的評估中挑最好的，必然偏樂觀），所以只作排序，永遠不當結果回報；回報的性能只來自事先宣告、種子獨立的確認 run（§5.6）。
5. **結果是提案，不是驗證。** 搜尋出的設計 label 一律 `unvalidated`；紀錄寫明「以模擬最佳化的設計」，並附搜尋規模、確認 run 與穩健性。

**開始前必做：** 讀任務 A 的 §1、§2、§4 與 A1.8（閘門）、A1.9（兩階段事件數）；C2 另讀任務 B 的 §4、B1.1、B2.1。依任務 A 附錄 B 的方法核對本文件引用的事實。

---

## 1. 名詞與記法

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
| 記法 | 「C1.3」是本文件的工作項；「A1.8」「B2.1」是任務 A、B 的工作項；「架構 §6」是 `architecture.md` 的節 |

---

## 2. 實際做法的參考與教訓

| 研究 | 做法 | 本設計採用的教訓 |
|---|---|---|
| EIC dRICH（Cisbani 等，JINST 15 (2020) P05009） | 8 個參數；目標為 π/K 分離（兩個動量的調和平均）；Geant4 帶 2.5 % 雜訊；高斯過程貝氏最佳化，每次 20 個設計並行，約 55 次呼叫收斂；優於原設計（3.23 對 2.9）；以後驗推得容差區間 | 雜訊要明確建模；平行批次；以後驗做容差與參數相關性分析；結果「只基於模擬」，需原型驗證 |
| AID(2)E（ePIC，arXiv:2405.16279） | 多目標貝氏最佳化（qNEHVI，Ax/BoTorch）與 NSGA-II；dRICH 7 個參數、200 次評估、150 次收斂；以已知 Pareto 前緣的 DTLZ2 做封閉測試；PanDA 分散執行 | 多目標與 Pareto；目標數 ≤ 4 時用 MOBO，更多或不連續時用遺傳演算法；先做封閉測試；幾何約束（重疊、包絡）在模擬前檢查 |
| MODE（arXiv:2203.13818、2310.05673） | 端到端可微分最佳化；以可微分代理模型取代不可微的模擬；效用函數包含物理目標與成本 | 以單一效用或 Pareto 對齊實驗目標，而非各子系統各自最佳化；代理模型可能把設計導向偏差，必須以完整模擬確認 |
| AIDO 擴散模型量能器（arXiv:2502.02152） | 6 層取樣量能器、12 個參數（厚度與材料）；材料以 softmax 的類別變數處理；成本與長度上限；結果重現已知的量能器原則 | 類別選擇（材料）與成本約束可以進入搜尋；「重現已知原則」是合理的第一個驗收 |
| ECAL 縱向結構（Borysov 等，EPJ Web Conf. 315, 03006） | 半解析模型（以 Geant4 核對）＋遺傳演算法與非支配排序 | 解析模型先篩選、Geant4 核對：即 F0 → F2 的多保真度 |
| SWGO 陣列佈局（arXiv:2310.01857） | 約 6000 個水槽位置的可微分最佳化；效用 = 通量精度 + 能量解析 + 指向解析 + 面積成本 | 效用的權重是宣告的選擇；某些導數項會主導並把設計推向極端，需要檢查 |
| GRACE（arXiv:2602.15039） | LLM agent 從自然語言或論文建立模擬並探索設計變體；有物理檢查器與 provenance | 幾何常需多次重產才符合規格，應在模擬前驗證；agent 注意到異常卻未追查；忽略成本與工程約束 |
| VI-BRATO（arXiv:2604.21804） | LLM agent 指揮 DD4hep/Geant4 的幾何與數位化雙層掃描，46 次 run 達到 2255 點網格的最佳 | agent 擅長分解問題與調整掃描；但結論需獨立核對，且仍需專家把關可實現性 |

綜合：沒有一個實際案例讓 LLM 自己宣告「最佳」；成功的做法都是「明確的目標與約束＋可重現的評估＋有紀錄的最佳化器＋完整模擬確認」。LLM 的價值在於把需求轉成搜尋問題、提出有物理根據的起點、分解問題、追查異常。

---

## 3. 前提：任務 A、B 提供的介面

| 提供者 | 介面 | 任務 C 的用法 |
|---|---|---|
| 任務 A | 區塊 batch means、SE、精確區間、IUT 閘門（A1.6–A1.8）、兩階段事件數（A1.9） | F1、F2 的目標估計與確認判定 |
| 任務 A | 種子 H 與 S = H(study_id, role, point_id)（A1.4） | 每個設計評估的 point_id = 設計雜湊；確認 run 的 role 為 `confirmation` |
| 任務 A | 三個邊界產物、`tree-v1`（A2.3–A2.6） | 評估只讀 summary；設計雜湊以實現後的幾何樹核對 |
| 任務 B | `element_sim.spec/1`（B1.1）、場（B1.2）、量能器漏失（B1.3） | 設計的實現目標 |
| 任務 B | `simreco`（B2.1）：剛度、β、量能器能量 | F1、F2 的重建 |
| 任務 B | surrogate 類別（B2.3） | F0 與 F1 相對 F2 的定位：代理，不改變 label |
| 既有工具 | `tracker_resolution.py`、`multiple_scattering.py` | F0 的徑跡解析度（以子行程呼叫，不重寫公式） |

---

## 4. 硬性限制

任務 A §2 與任務 B §3 的限制都適用。另外：

1. **搜尋器核心只用標準函式庫。** Sobol 序列、NSGA-II、（選用）CMA-ES 以標準函式庫實作。貝氏最佳化（Ax/BoTorch）只作為 adapter 的選用後端，像其他 adapter 的外部工具一樣在 `adapter.json` 記錄測試過的版本；沒有安裝時搜尋仍可執行。
2. **同一個量只有一份正式實作。** F0 的徑跡與多重散射呼叫既有腳本；材料常數取自 Geant4 的 NIST 表或 PDG（經 hep-citations），不另寫一份。
3. **事先宣告。** 需求、目錄版本、文法、搜尋預算、最佳化器設定與種子在第一次評估前寫入搜尋 spec 並取雜湊。之後的任何變更產生新的搜尋版本；舊版本與其結果保留在紀錄中。
4. **搜尋數值不回報。** 搜尋階段的目標值只用於排序；任何對外的性能數字必須引用確認 run。
5. **LLM 提案沒有特權。** Claude 提出的設計以 `proposer: llm` 標記，經相同的有效性檢查與評估；Claude 不得修改評估輸出，不得在看到結果後改需求而不開新版本。
6. **成本與質量模型是宣告的輸入。** plugin 只附占位模型，標記 `assumed`；真實的單價與質量模型由使用者提供並附來源。沒有模型時，成本與質量不作為目標或約束。
7. **實驗名稱** 只出現在 `docs/` 與範例 README；元件目錄用通用名稱。
8. **不修改 `skills/hep-detector/SKILL.md`**，除非維護者核准一行指向 reference 的路由（§10）。

---

## 5. 設計

### 5.1 三個角色

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

### 5.2 需求規格 `detector-requirements/1`

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

### 5.3 設計文法 `detector-design/1` 與元件目錄

**元件目錄第一版**（全部可實現為 `element_sim` 的盒狀元件，最多一層巢狀）：

| 元件種類 | 參數（型別） | 實現 | F0 的評估模型 |
|---|---|---|---|
| `magnet-region` | B（連續，T）、長度、孔徑（連續，mm） | 場區母體（`field`），可容納徑跡與 TOF 子體 | 偏轉；MDR；質量模型（宣告） |
| `tracker-plane` | 材料（類別）、厚度、位置解析度（偏轉／非偏轉）、尺寸 | `tracker-plane` 元件；解析度寫入 reco spec | `tracker_resolution.py`（量測項）、`multiple_scattering.py`（散射項） |
| `tof-layer` | 材料、厚度、σ_t、尺寸 | `tof-layer` 元件 | σβ/β = σ_t c / D（多層平均） |
| `calorimeter-sampling` | 吸收層材料與厚度、主動層材料與厚度、層數（整數）、橫向尺寸 | `calorimeter` 母體 + 重複的取樣層 | X₀、λ_I、有效 Molière 半徑；能量解析度的參數化只作 F0 排序 |
| `calorimeter-homogeneous` | 材料、長度、橫向尺寸 | `calorimeter` 母體 + 單一主動體 | X₀、λ_I |
| `passive` | 材料、厚度、尺寸 | `passive` 元件 | 物質預算、多重散射 |

**組合規則（有效性，模擬前檢查）：**
- 元件沿 x 軸排成序列；序列長度與各種類的數量有上限（宣告於搜尋 spec）。
- 不重疊；全部在包絡內；平面之間的最小間距（宣告）。
- 子體只能放在 `magnet-region` 或 `calorimeter` 母體中，且只有一層巢狀（`element_sim` 的限制）。
- 參數在目錄範圍內；材料在目錄的材料清單中。
- 結構上「不合理」的組合（例如沒有磁場卻要求剛度解析度）**不**由規則禁止，而由目標與約束自然淘汰；規則只處理物理上或程式上不可能的情形。這保留了「自由組合」。

**基因編碼：** 固定數量的槽位（slot），每個槽位有「啟用」位元、元件種類（類別）與該種類的參數；停用的槽位不實現。順序由槽位的 x 位置決定。這讓遺傳演算法可以增刪元件與更換種類（AIDO 以 one-hot 處理材料；這裡以類別基因處理種類與材料）。

**實現：** `realize(design) → (element_sim.spec/1, reco spec)` 是確定性函式；設計雜湊 = 正規化設計 JSON 的 sha256；實現後以 `tree-v1`（A2.4）核對幾何。相同設計雜湊的評估可以重用（快取），但快取鍵包含保真度、目錄版本與程式雜湊。

### 5.4 多保真度評估

| 保真度 | 方法 | 每個設計的成本 | 輸出 | 用途 |
|---|---|---|---|---|
| F0 | 解析式與既有工具（徑跡量測項與散射項、物質預算、接受度的螺旋幾何、TOF 公式、X₀ 與 λ_I） | 微秒到毫秒 | 目標值（無統計誤差，但有模型誤差） | 結構搜尋；篩選 10⁴–10⁶ 個設計 |
| F1 | `element_sim` + `simreco`，每個設計約 10³ 事件，K = 16 | 分鐘 | 目標值 ± SE（區塊 batch means） | 細化數百個設計的連續參數；校正 F0 |
| F2 | 同 F1，事件數依 A1.9 的兩階段設計；收斂閘門（A1.8）與 variation（B2.6） | 小時 | 目標值 ± SE，判定 | 決選者 |
| 確認 | 同 F2，role `confirmation`，種子獨立 | 小時 | 回報的性能與需求判定 | 唯一可回報的數字 |

- **F0 與 F2 的差異** 在每個決選者上記錄（`fidelity_gap`）。若差異超過宣告的門檻，該目標在決選時只依 F2 排序，並在報告中說明 F0 的模型限制。
- F0、F1 在架構上屬於 surrogate 類別（B2.3）：它們從不改變 label。

### 5.5 搜尋策略

| 步驟 | 內容 | 預設方法 | 預算（預設，可宣告） |
|---|---|---|---|
| S0 設計摘要 | Claude 讀需求，寫出候選結構種類、2–6 個種子拓撲與物理理由、問題的分解 | Claude | — |
| S1 結構搜尋 | 在 F0 上搜尋完整基因（結構＋參數）；初始族群 = 種子拓撲 + Sobol 隨機設計 | NSGA-II（標準函式庫） | 族群 200 × 100 代 = 2×10⁴ 次 F0 |
| S2 參數細化 | 取前 K 個**拓撲不同**的設計（以拓撲雜湊去重，保持多樣性），在 F1 上細化連續參數 | NSGA-II 或 CMA-ES；選用 MOBO（qNEHVI），限目標 ≤ 4、參數 ≤ 20 | K = 5，每個約 100 次 F1 |
| S3 決選 | 每個拓撲的最佳設計進入 F2；收斂閘門、variation | — | ≤ 5 個設計 |
| S4 確認 | 決選者的確認 run；需求判定；穩健性 | — | ≤ 5 個設計 |

- 停止規則：預算用完，或超體積（hypervolume）在連續 G 代內改善小於宣告值。不依結果加預算；加預算是新的搜尋版本。
- Claude 在 S0 之後可以加入新的種子拓撲（例如追查一個異常），但這些提案同樣標記為 `proposer: llm`、計入搜尋規模。

### 5.6 統計完整性

| 風險 | 處理 |
|---|---|
| 贏家詛咒 | 搜尋數值只作排序；回報只來自確認 run（role `confirmation`，S 不曾出現在搜尋中）；報告每個決選者的「搜尋估計 − 確認估計」作為診斷 |
| 帶雜訊的約束 | 需求判定沿用 A1.8 的邏輯，但為單邊：「≤ 門檻」的需求，符合 = 估計 + t₀.₉₅·SE ≤ 門檻；不符合 = 估計 − t_{1−α/m}·SE > 門檻；其他為 unresolved（m = 決選者數 × 需求數）。計數很少時用精確區間 |
| 在雜訊中宣稱支配 | 決選者之間的支配關係只在差值超過 t·se_diff 時宣稱；報告「統計上非支配的集合」 |
| 搜尋規模 | 紀錄寫入各保真度評估的設計數、拓撲數、最佳化器設定與種子 |
| 利用模擬缺陷 | 決選者必須通過其相關參數（production cut、最大步長、場精度）的收斂閘門；物理模型 variation（B2.6 的規則）；若設計落在任何 reference benchmark 範圍外的材料或能量區，在報告中標記（label 本來就是 `unvalidated`，這是給讀者的資訊） |
| 穩健性 | 依需求的 `tolerance` 與目錄的製造容差擾動連續參數（F0 全因子或 F1 抽樣），報告性能分布；需求在容差內的最差情形也要判定，結果分為「穩健符合」與「名義符合」 |
| 改需求 | 需求或預算的任何改變是新的搜尋版本；報告列出所有版本 |

### 5.7 紀錄與契約（C3）

搜尋紀錄是帶 `extension.design_search` 的 computational-run：

```
{ "requirements_sha256": "...", "catalogue_version": "1", "catalogue_sha256": "...",
  "search_spec_sha256": "...", "search_version": 1, "previous_versions": [],
  "optimizer": {"name": "nsga2", "implementation": "detector-design 0.1.0", "backend": null, "seed": 12345, "config": {...}},
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

**契約規則（C3，閘控同 C1）：**
- 搜尋紀錄的 label 必須是 `unvalidated`。
- 每個決選者的 `confirmation_runs` 必須存在，role 為 `confirmation`，其 spec 雜湊等於該設計的實現，其種子 S 不在 `evaluations_ref` 所列的任何搜尋評估中（`dependencies.py` 重新推導）。
- 由搜尋紀錄衍生的表格或 communication，其數值必須來自確認 run；引用搜尋階段數值時被拒。
- communication 使用搜尋結果時得到 `communication.simulation_optimized_design` 警告。

---

## 6. 階段 C1：需求、文法與快速搜尋（adapter detector-design 0.1.0）

### C1.1 schema

`detector-requirements/1`、`detector-design/1`、`catalogue/1`、`design-search-spec/1`（需求雜湊、目錄版本、槽位數與上限、預算、最佳化器設定、種子、停止規則），放在 `adapters/detector-design/assets/`，只用 `contracts/schema.py` 支援的關鍵字；跨欄位規則在 Python 中檢查。

### C1.2 元件目錄第一版

§5.3 的六種元件；每種附參數範圍、材料清單（NIST 名稱）、製造容差、質量模型（密度 × 體積；磁鐵質量為宣告的占位模型，標記 `assumed`）、F0 模型、實現規則。目錄的每個條目有單元測試（實現後的幾何、物質預算）。

### C1.3 實現與有效性

`design_search.py realize`：設計 → `element_sim.spec/1` 與 reco spec；以 B1.1 的 schema 與跨欄位規則驗證；不需 Geant4。無效設計回傳原因（重疊、超出包絡、巢狀、範圍），exit 2。

### C1.4 F0 評估

`design_search.py evaluate --fidelity F0`：以子行程呼叫 `tracker_resolution.py`、`multiple_scattering.py`；物質預算與 X₀、λ_I 依 Geant4 NIST 材料的組成計算（和 `geant4_verify.py` 同一方法，必要時抽成 `core/` 的共用函式並指定 steward）；接受度門檻以均勻場中的螺旋與盒狀邊界計算（和任務 B 附錄 A 同一公式）；TOF 解析度依任務 B §4.2 的公式。每個目標附 `model` 欄位說明近似。

### C1.5 搜尋器

`design_search.py search`：Sobol 初始化、NSGA-II（模擬二元交配與多項式突變處理連續與整數；類別基因以均勻交配與隨機重設；槽位啟用位元以位元翻轉）、約束以 constrained-domination 處理。標準函式庫實作；同一種子結果逐位元相同。

### C1.6 搜尋紀錄與報告

`design_search.py report`：Pareto 前緣、每個拓撲的最佳設計、搜尋規模、F0 模型限制；輸出紀錄（§5.7，C1 中確認相關欄位為空，並標記 `fidelity: F0-only`）與一份給使用者的 Markdown 摘要。C1 的結果明確標示「只基於解析模型」。

### C1.7 agent 協定

`skills/hep-detector/references/detector-design-search.md`：§5.1 的角色與限制、需求確認流程、設計摘要的格式、何時升保真度、如何回報（必須說明搜尋規模、確認狀態與穩健性）。

### C1.8 封閉測試

| 測試 | 已知答案 | 通過條件 |
|---|---|---|
| DTLZ2（3 目標，已知 Pareto 前緣） | 解析的前緣 | 2×10⁴ 次評估內超體積達到真值的 95 % 以上（AID(2)E 的封閉測試做法） |
| 平面配置（N = 6、臂長固定、只有量測項） | 在 1/32 臂長的格點上窮舉的最佳 A = 47.66（等距為 66.96，附錄 A） | 搜尋器找到 A ≤ 47.66 × 1.01 的配置 |
| 結構選擇（需求 MDR ≥ 1 TV，給定包絡與質量上限） | 必須選出含 `magnet-region` 與 ≥ 3 片 `tracker-plane` 的拓撲；無磁場的拓撲都不可行 | 所有可行的 Pareto 設計都含磁場區與徑跡平面；B·L² 與解析式一致 |
| 量能器深度（需求 ≥ 16 X₀、長度上限） | 在吸收層材料清單中，高 Z 吸收層使長度最短 | 選出的吸收層與解析排序一致 |
| 可重現 | — | 同一搜尋 spec 與種子，兩次執行的紀錄逐位元相同（時間戳除外） |

### C1.9 C1 驗收

- [ ] 四個 schema 與跨欄位規則的測試；無效設計的每種原因都有測試。
- [ ] 目錄六種元件的實現測試；實現的 spec 通過 `element_sim.spec/1` 的 schema（草案或已合併版本）。
- [ ] F0 的每個目標和既有工具或附錄的解析值一致。
- [ ] C1.8 的封閉測試全部通過。
- [ ] 一個獨立 agent 依 agent 協定，從一段自然語言需求完成：需求確認（由測試扮演使用者）、設計摘要、F0 搜尋、報告；報告標示「只基於解析模型」並列出搜尋規模。
- [ ] VALIDATION DESIGN-SEARCH-F0；CHANGELOG；release manifest；`check_layering`、`check_packaging`。

---

## 7. 階段 C2：模擬評估與確認（adapter 0.2.0、contracts C3）

### C2.1 F1、F2 評估

`design_search.py evaluate --fidelity F1|F2`：實現 → `geant4_run.py`（`element_sim`）→ `simreco` → summary；每個設計評估是一個邏輯 run，point_id = 設計雜湊，role 為 `search-F1`、`search-F2`。事件數：F1 固定（宣告），F2 依 A1.9。批次執行經既有的 partition 與 batch 機制（hep-computing），以設計雜湊快取。

### C2.2 確認與需求判定

`design_search.py confirm`：決選者的確認 run（role `confirmation`）；§5.6 的單邊需求判定；決選者之間的統計支配；`search_minus_confirmation` 與 `fidelity_gap`。

### C2.3 防護與穩健性

決選者的收斂閘門（production cut、最大步長、場精度，A1.8）；variation（B2.6 的規則）；容差擾動；benchmark 範圍外的標記。

### C2.4 選用的 MOBO 後端

Ax/BoTorch（qNEHVI），只在 S2 使用，限目標 ≤ 4、連續參數 ≤ 20；版本記錄在紀錄與 `adapter.json`；沒有安裝時退回 NSGA-II，並在紀錄中註明。測試以 DTLZ2 封閉測試比較兩者。

### C2.5 契約 C3

§5.7 的規則；`dependencies.py` 的重新推導（確認 run 的 spec 雜湊與種子不重疊）；communication 警告。閘控 `strict or _at_least(contract_version, C3)`。

### C2.6 J16：自動設計範例

- 需求：由 J15 的設計目標整理（MDR ≥ 1 TV、σβ/β ≤ 3 %、接受度門檻 ≤ 0.8 GV、量能器 ≥ 16 X₀、上游物質 ≤ 15 % X₀、長度 ≤ 2 m、宣告的質量模型）；**不**提供 J15 的幾何。
- 執行 S0–S4；報告比較搜尋結果與 J15：是否找到 J15 型的拓撲、在哪些目標上更好或更差、原因（例如平面向兩端與中央聚集提高 MDR，但多重散射主導區的解析度變差）。
- 和 J15 一樣是合成研究；README 說明它展示的是流程，不是新的探測器設計（AIDO 與 SWGO 研究的同樣定位）。
- 離子源與 Birks 的研究（原預留 J16）順延為 J17。

### C2.7 文件與註冊

`docs/researcher-journeys.md`、路由案例（沿用 hep-detector description 中已有的「design principles and trade-offs」觸發詞）、capability map、capability matrix、adapter 文件、protocol。

### C2.8 計算預算

F0 2×10⁴ 個設計：分鐘級；F1 約 500 × 10³ 事件；F2 與確認各 ≤ 5 個設計，事件數依 A1.9；量能器簇射主導 CPU。實際預算在 trial 後寫入搜尋 spec。

### C2.9 C2 驗收

- [ ] F1、F2 的 summary 通過任務 A 的一致性測試；評估快取以設計雜湊、保真度、目錄版本與程式雜湊為鍵。
- [ ] 確認 run 的種子不在任何搜尋評估中（契約測試）；引用搜尋數值的表格被拒；搜尋紀錄 label 非 `unvalidated` 時被拒。
- [ ] 單邊需求判定的 toy：在門檻處的「符合」機率 ≤ 0.05 + 3σ_MC。
- [ ] 贏家詛咒的 toy：在純雜訊的設計集合上，搜尋估計顯著偏樂觀，而確認估計無偏（示範 §5.6 的必要性）。
- [ ] J16 執行完成，報告含搜尋規模、確認判定、穩健性與和 J15 的比較。
- [ ] MOBO 後端（若安裝）通過 DTLZ2 封閉測試；未安裝時退回並註明。
- [ ] VALIDATION DESIGN-SEARCH；CHANGELOG；release manifest；任務 A §9 的檢查。

---

## 8. 契約與版本

| 物件 | 位置 | 版本 |
|---|---|---|
| `detector-requirements/1`、`detector-design/1`、`catalogue/1`、`design-search-spec/1`、F0、搜尋器 | `adapters/detector-design/` | adapter 0.1.0（C1） |
| F1、F2、確認、MOBO 後端 | `adapters/detector-design/` | adapter 0.2.0（C2） |
| `extension.design_search` 與其規則 | `contracts/validate.py`、`contracts/dependencies.py` | C3（minor、閘控） |
| agent 協定 | `skills/hep-detector/references/detector-design-search.md` | 隨 plugin 版本 |

---

## 9. 不做與延後

| 項目 | 決定 | 理由 / 觸發條件 |
|---|---|---|
| 讓 LLM 單獨決定最佳設計 | 不做 | 沒有實際案例這樣做；判定必須可重現 |
| 搜尋中臨時發明元件種類 | 不做 | 新元件需要實現規則、F0 模型與測試；經目錄變更加入 |
| 可微分模擬與可微分代理模型（MODE 路線） | 延後 | Geant4 不可微；可微分代理模型對點雲尺度仍不成熟（arXiv:2310.05673）。觸發：一個連續參數 > 20 的問題，且 F1 預算不足 |
| 圓柱與非盒狀幾何、對撞機探測器 | 延後 | `element_sim` 只有盒狀元件。觸發：`element_sim` 加入圓柱元件 |
| Cherenkov、RICH、TRD | 延後 | 需要光學物理與專用重建 |
| 強化學習、大型神經網路代理模型 | 延後 | 資料量與可解釋性；NSGA-II 與 MOBO 對 ≤ 數十個參數已足夠 |
| 真實成本資料庫 | 不附 | 由使用者提供並附來源 |

---

## 10. 待維護者決定的事項與殘餘風險

**待決定：**
1. 新 adapter `detector-design` 的擁有者（建議 hep-detector）。
2. 在 `skills/hep-detector/SKILL.md` 加一行指向 `detector-design-search.md` 的路由（約 120 bytes；quick load 只剩 931 bytes），或只靠 reference 與路由案例。
3. C3 的版本歸類（建議 minor）與 hep-computing 對 `extension.design_search` 的同意。
4. MOBO 後端（Ax/BoTorch）是否列為 adapter 的測試工具。
5. J16 的編號（離子源研究順延為 J17）。

**殘餘風險：**
1. F0 模型的偏差可能讓結構搜尋錯過好的拓撲；以 S2 的拓撲多樣性與 `fidelity_gap` 緩解，但不能排除。
2. 模擬最佳化的設計可能利用 Geant4 在未驗證區的行為；收斂閘門與 variation 只能部分防護，label 維持 `unvalidated`。
3. 質量與成本的占位模型很粗；沒有使用者模型時不應把它們當目標。
4. 目標超過 4 個時，Pareto 前緣難以解讀；需求應把其餘目標寫成約束。
5. Claude 的設計摘要可能帶入「已知儀器」的偏見；以 Sobol 隨機設計與拓撲多樣性抵銷，並在報告中區分 LLM 與隨機提案的貢獻。
6. 計算量：量能器的 F1、F2 評估成本高；預算需在 trial 後調整。
7. 本文件的參考資料（GRACE、VI-BRATO）是 2026 年的預印本，結論尚未經同儕審查。

---

## 11. 建議的執行步驟

**C1**
1. 開始前檢查；schema（C1.1）與目錄（C1.2）。
2. 實現與有效性（C1.3）；F0（C1.4），以既有工具核對。
3. 搜尋器（C1.5）與 DTLZ2、平面配置的封閉測試。
4. 紀錄與報告（C1.6）；agent 協定（C1.7）；其餘封閉測試與獨立 agent 驗收；C1.9。

**C2（任務 B 合併後）**
1. F1、F2（C2.1）；確認與需求判定（C2.2）；契約 C3（C2.5）與 toy。
2. 防護與穩健性（C2.3）；選用的 MOBO（C2.4）。
3. J16（C2.6）；文件與註冊（C2.7）；C2.9。

---

## 附錄 A：數值

**平面配置的封閉測試**（曲率變異 σ_k² = A σ² / L⁴，N = 6，等權重，只有量測項；精確有理數最小平方；計算程式見本資料夾的 `design_search_closure.py`）：

| 配置 | A | 相對等距的 MDR |
|---|---|---|
| 等距（J15） | 66.96 | 1 |
| 兩端與中央各 2 片（重合） | 48.00 | 1.181 |
| 1/16 臂長格點上窮舉的最佳（平面不重合） | 50.34（0, 3/8, 7/16, 1/2, 9/16, 1） | 1.153 |
| 1/32 臂長格點上窮舉的最佳 | 47.66（0, 1/32, 7/16, 15/32, 1/2, 1） | 1.185 |
| 連續極限（N/4、N/2、N/4 聚集） | 256/N = 42.67 | 1.253 |

J15 的 MDR 1172 GV 在 1/32 格點的最佳配置下約為 1389 GV；但聚集的配置在多重散射主導區較差，這正是 J16 要讓搜尋器處理的取捨。

## 附錄 B：出處

- E. Cisbani et al., "AI-optimized detector design for the future Electron-Ion Collider: the dual-radiator RICH case", JINST 15 (2020) P05009, [arXiv:1911.05797](https://arxiv.org/abs/1911.05797)
- AID(2)E collaboration, "AI-Assisted Detector Design for the EIC (AID(2)E)", [arXiv:2405.16279](https://arxiv.org/abs/2405.16279)
- MODE collaboration, "Toward the end-to-end optimization of particle physics instruments with differentiable programming", [arXiv:2203.13818](https://arxiv.org/abs/2203.13818)；"Progress in end-to-end optimization of detectors for fundamental physics with differentiable programming", [arXiv:2310.05673](https://arxiv.org/abs/2310.05673)
- Schmidt et al.（MODE），"End-to-end detector optimization with diffusion models: a case study in sampling calorimeters", [arXiv:2502.02152](https://arxiv.org/abs/2502.02152)
- O. Borysov et al., "Longitudinal structure optimization for a high density electromagnetic calorimeter", [EPJ Web Conf. 315, 03006 (2024)](https://www.epj-conferences.org/10.1051/epjconf/202431503006)
- T. Dorigo et al., "Toward the end-to-end optimization of the SWGO array layout", [arXiv:2310.01857](https://arxiv.org/abs/2310.01857)
- J. Hill, H. J. Ryoo, "GRACE: an agentic AI for particle physics experiment design and simulation", [arXiv:2602.15039](https://arxiv.org/abs/2602.15039)（預印本）
- W. Chung et al., "Agentic-AI detector co-design and optimization in vertically-integrated differentiable full simulations", [arXiv:2604.21804](https://arxiv.org/abs/2604.21804)（預印本）
- 以上於 2026-10-23 取得；作者與期刊資訊在引用前需經 hep-citations 核對

## 附錄 C：版本歷程

| 版本 | 內容 |
|---|---|
| **2026-10-23（本版）** | **初版提案：三個角色、需求規格、元件目錄與設計文法、F0/F1/F2 多保真度、搜尋與確認分開、C3 契約、C1/C2 階段、J16** |
