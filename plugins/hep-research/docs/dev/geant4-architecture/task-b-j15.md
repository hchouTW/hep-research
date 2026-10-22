# 任務 B：`element_sim`、事件檔與 J15 最小磁譜儀

> 文件類型：實作規格（給執行的 agent 與審查者）。狀態：待維護者核准
> 依據：[`architecture.md`](architecture.md)（設計理由與參考實驗）。本文件是可執行的規格；兩者不一致時，以本文件為準並回報
> 順序：**在任務 A（[`task-a-core.md`](task-a-core.md)）的 A1 與 A2 都合併後才開始**
> 基準：撰寫時同任務 A（hep-research `main` 的 `9f08796`，contracts 3.5.0，Geant4 11.4.3）；開始前必須重新核對（§0）
> 日期：2026-10-22
> 語言：繁體中文原文；英文版 [`task-b-j15.en.md`](task-b-j15.en.md) 內容相同。兩者不一致時以中文為準，並同時修正英文
> 範例性質：J15 是**合成幾何**，是 verification 的載體，不是任何實驗的偵測器；最接近的實際儀器是 PAMELA 與 AMS-02（§4.3）

---

## 0. 任務卡

**目標。** 新增一個通用的盒狀元件 Geant4 程式 `element_sim` 作為第二個後端，加入場、平面穿越與逐事件 ROOT 檔；再以它和重建程式 `simreco` 完成 J15 最小磁譜儀研究，並在契約中加入 verification、regression、surrogate 三個驗證類別與遞移的處理鏈（C2）。

**兩個階段（依序，各自合併）：**

| 階段 | 內容 | 版本 |
|---|---|---|
| **B1** `element_sim` 與事件檔 | `element_sim`（盒狀元件、一層巢狀、場、平面穿越）；逐事件 ROOT 檔；`simroot`；兩個後端的介面一致性 | adapter **0.3.0** |
| **B2** 重建、J15 與 C2 | `simreco`；J15 研究（驗證梯、收斂、variation、TOF 敏感度）；C2（verification、regression、surrogate、遞移的處理鏈）；J15 journey | adapter **0.4.0**、contracts **C2**（minor） |

**不在範圍內：** 任務 A 的任何介面變更（若必要，先在任務 A 範圍內以 adapter 修補版處理）；`layered_sim` 的新幾何功能（它凍結於維護模式）；離子源與 Birks（未來 J17；J16 用於任務 C 的自動設計範例）；真實幾何與場圖（§8）。

**交付物：** `element_sim`、`simroot`、`simreco` 與其測試；`geant4_run.py reco` 與 `table`；J15 範例（`examples/` 下的新資料夾、README、recorded 資料）；C2 契約變更；J15 journey 與路由案例；VALIDATION 條目 GEANT4-ELEMENT（B1）與 GEANT4-J15（B2）；CHANGELOG；release manifest。

**完成的定義：** B1.8 與 B2.11 的驗收清單全部打勾；任務 A §9 的檢查全部通過。

**主要決定：**
1. **新增後端，不改 `layered_sim`。** `element_sim` 讓 J14 的程式不動，並以真正的第二個後端驗證輸出層介面（架構 §3.2）。
2. **場精度用確定性檢查。** charged geantino 對解析螺旋，不需要統計（B2.5）。
3. **J15 是 verification 的載體。** 完整探測器中的所有結果都是 `unvalidated`；只有在孤立平板中執行的選用 benchmark 示範新材料的升級路徑（B2.4）。
4. **hep-detector 不新增腳本。** 重建在 C++ 的 `simreco`，介面在 adapter；quick load 與 description 不變（B2.10）。

**開始前必做：**
1. 確認任務 A 的 A1（C1）與 A2（adapter 0.2.0）都已合併，且 §2 列的介面都存在。
2. 依任務 A 附錄 B 的方法，以當時的 `main` 重新核對本文件引用的事實（quick load、description 長度、journey 清單、`DetectorScriptCount`、contracts 版本），並更新本文件（中英兩版）。
3. 讀任務 A 的 §1（名詞）、§2（硬性限制）、§4（設計摘要）；本文件不重複。

---

## 1. 名詞與記法

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
| 記法 | 「B1.3」是本文件的工作項；「§4.2」是本文件的節；「A1.6」「A2.4」是任務 A 的工作項；「任務 A §2」是任務 A 的節；「架構 §6」是 `architecture.md` 的節 |

**主要檔案（相對 `plugins/hep-research/`）：** `adapters/geant4/assets/g4sim/`（任務 A 建立，本任務擴充）；`adapters/geant4/assets/element_sim/`（新增）；`adapters/geant4/assets/simroot/`（新增）；`adapters/geant4/assets/simreco/`（新增，不連結 Geant4）；`adapters/geant4/assets/geant4_run.py`（新增 `reco`、`table`）；`contracts/validate.py`、`contracts/dependencies.py`（C2）；`skills/hep-detector/scripts/geant4_benchmarks.py`（`GRADES`）；`skills/hep-detector/assets/geant4-study-spec.schema.json`；`skills/hep-detector/references/geant4-study-protocol.md`；`docs/researcher-journeys.md`、`docs/maintenance.md`、`docs/capability-matrix.md`、`docs/capability-map`；`tests/examples/test_geant4_minimal_spectrometer.py`（新增）。

---

## 2. 前提：任務 A 提供的介面

| 任務 A 提供 | 任務 B 的用法 |
|---|---|
| C1：benchmark 表（類別、等級、kind、範圍維度）、範圍比對、configuration 與隔離（A1.1–A1.3） | J15 的 benchmark 都是 embedded，不計入升級；C2 在表中加入 verification、regression、surrogate（B2.3） |
| 統計規格：區塊 batch means、精確區間、MPV、IUT 閘門（含 `tolerance_mode: absolute`）、兩階段事件數、偵測極限（A1.6–A1.10） | J15 的 benchmark、收斂掃描、variation 的判定 |
| study spec 頂層的 `observables` 宣告（含 `selection`）與 `blocks`（A1.12） | J15 的觀測量宣告 |
| 種子 S = H(study_id, role, point_id) 與 `seeding: per-event`（A1.4、A2.2；在 `GeneratePrimaries` 開頭重設） | `element_sim` 只支援 `per-event` |
| `g4sim`：`SimHash.hh`（SHA-256、H、SplitMix64、Box–Muller，不連結 Geant4）、`SimSeed.hh`、`SimSummary.hh`、`MiniJson.hh`、`SimProbe.hh`、材料與 physics list 輔助（A2.1） | `element_sim` 使用全部；`simreco` 只用不連結 Geant4 的 `SimHash.hh`、`SimSummary.hh`、`MiniJson.hh` |
| 三個邊界產物與研究層只讀它們（A2.3–A2.6） | `element_sim` 與 `simreco` 交出同樣的三個產物；研究層不需修改 |
| `tree-v1` 目標雜湊（A2.4） | 場附加在目標內的體積時計入雜湊 |
| schema 關鍵字 `maxItems`、`maximum`、`exclusiveMaximum`（A2.7） | `element_sim.spec/1` 的 schema 使用 |

---

## 3. 硬性限制

任務 A §2 的全部限制都適用。另外：

1. 不修改 `skills/hep-detector/SKILL.md` 與 hep-detector 的 description（quick load 只剩 931 bytes；description 1,016 / 1,024 字元，依 `measure_entrypoints.py`）。J15 的路由案例必須沿用 description 中已有的觸發詞。
2. `skills/` 與 `contracts/` 中不得出現實驗名稱；契約表與 protocol 引用 `longitudinal-profile` 的參考時用引用鍵。實驗名稱（PAMELA、AMS-02）只可出現在 `docs/` 與 J15 的 `examples/` README。
3. 場的程式依 Geant4 API 撰寫，不複製或改寫 B5 範例的程式碼（G5）。
4. 共享 stanza 的文字不改（點 5 寫「3.1.0 upgrade rule」；修改會牽動全部 SKILL.md 與 live 路由重跑）。
5. J15 的 `recorded/` 每檔 ≤ 2 MiB、總和 ≤ 3 MB；ROOT 檔不提交（B2.9）。
6. J15 的所有結果都是 `unvalidated`；任何 J15 benchmark 都不得計入升級。
7. `layered_sim` 不加幾何功能；新的幾何功能只加在 `element_sim`。
8. Python 與 `simreco` 都不直接解析 ROOT；一律經 `simroot`。

---

## 4. J15 的設計

### 4.1 幾何

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

**TOF 站。** TOF1 與 TOF2 各兩層；四層同材料、同厚度（10 mm），每站兩層之間有 10 mm 真空間隙。每層是整片平板，不分割、不設 paddle 方向（刻意的簡化）；兩層提供兩次獨立的時間量測與 dE/dx 取樣，並讓同站兩層的一致性成為一項檢查（B2.4）。

**核對**（附錄 A 的程式，測試中重算）：
- 量測臂長 L = 0.800 m；Si1 前緣和 Si6 後緣距母體邊界各 19.85 mm。
- 場在量測區兩端各多延伸 20 mm。
- TOF 站中心（兩層的中點：−795、505 mm）之間的距離 D = 1.300 m。
- TOF2 後層的後表面（520）距量能器前表面（550）30 mm；TOF1 前層（−810）在粒子源（−1000）之後。
- 世界包含粒子源與量能器後端。

材料（11.4.3 的 NIST 定義對照 PDG）：`G4_PLASTIC_SC_VINYLTOLUENE` 1.032 g/cm³、I = 64.7 eV；`G4_Si` 2.33 g/cm³（PDG 2.329）。

**刻意的簡化**（J15 的 README 逐條列出）：均勻場與銳利邊界、無磁鐵材料、矽為整片平面（無條帶、無電荷分享、未模擬 δ 射線造成的重心偏移）、TOF 每層不分割、無光學光子、無觸發與讀出電子學、無反符合。

### 4.2 參數與接受度

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

### 4.3 和實際儀器的對照

| 儀器 | 配置（出處見架構 §14） | 和 J15 比較 |
|---|---|---|
| PAMELA | 0.43 T 永久磁鐵；6 片雙面矽微條平面，解析度優於 4 µm；MDR 超過 1 TV；三個 TOF 平面（S1–S3，分割成 paddle）；鎢／矽成像量能器 16.3 X₀、0.6 λ；另有反符合、S4、中子偵測器 | 幾乎同型；J15 的 Si 解析度假設 10 µm（較保守）、TOF 不分割、沒有反符合 |
| AMS-02 | TOF 四個平面（8、8、10、8 個計數器）；系統對質子約 140 ps | J15 每層 100 ps 較樂觀，所以做 100 與 150 ps 的敏感度（B2.7） |

J15 的 README 以這張表說明 J15 的合理性，並強調 J15 是合成幾何、不代表任何實驗。

---

## 5. 階段 B1：`element_sim` 與事件檔（adapter 0.3.0）

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
| `source` | `type: gun`：粒子、能量（`energy_MeV` 或 `ekin_per_nucleon_MeV`）、位置、方向；`gps` 與 `event-file` 只定義介面（架構 §9.2），遇到時 exit 2 |
| `run` | 事件數、執行緒、邏輯 run 種子；`seeding` 只允許 `per-event` |
| `output.observables`、`output.blocks` | 同任務 A 的 A2.3 |
| `output.event_file` | `level`：`none`（預設）、`summary`、`crossings`、`hits`；`compression`（預設 1）；`max_events_hits`（預設 100） |

- 跨欄位規則（元件不重疊、子體在母體內、名稱唯一、角色與材料相容）在 Python 的 adapter 中檢查；C++ 只檢查執行所需的最低限度。
- 每個 run 交出三個邊界產物（summary、column map、effective config），與 `layered_sim` 相同。

### B1.2 場

- 在 `ConstructSDandField` 中建立 `G4UniformMagField`、`G4FieldManager`、`G4ChordFinder`，以 `G4ThreadLocal` 儲存；master 與每個 worker 各有一份。在 `Construct()` 中建立會讓 worker 共用非執行緒安全的 chord finder。
- 以 `SetFieldManager(fm, true)` 附在場區母體上，傳遞到所有子體。
- 有場時加入 `G4StepLimiterPhysics`。
- stepper 與 driver **明確建立**：以 `G4Mag_UsualEqRhs` 建立 `G4DormandPrince745`，傳給 `G4ChordFinder`；不用 `G4ChordFinder` 預設建構子所選的 stepper（那不受 `G4FieldParameters` 控制）。stepper 類別寫入 spec，探針以 RTTI 記錄 stepper 與 driver 的實際類別名（helix stepper 會讓場傳輸檢查失去意義）。
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

### B1.3 平面穿越 scorer

- 主粒子（track ID 1）在 `tracker-plane` 或 `tof-layer` 元件**第一次**進入時（前步點狀態為 `fGeomBoundary` 且所在體積為該平面），記錄前步點的位置、方向、動能、全域時間、PDG 碼；每個平面一個「已記錄」旗標。
- 粒子源若位於平面內，不會出現 `fGeomBoundary`，該平面不寫列。
- 逐事件 CSV 只保留摘要欄（主粒子真值、各子系統總沉積、量能器漏失）；穿越與逐層沉積寫入 ROOT 檔（B1.4）。

**量能器漏失。** 角色為 `calorimeter` 的母體元件，記錄每個事件中從母體內部離開母體的粒子帶走的能量（`post` 步點離開該母體的步；正子加 2 mₑc²；乘 track 權重），依離開的面分為 `leak_rear_MeV`（+x 面）、`leak_front_MeV`（−x 面）、`leak_lateral_MeV`（y、z 面），語意和 `layered_sim` 的同名欄相同（`layered_sim` 以世界邊界為面，`element_sim` 以量能器母體為面）。這三欄寫入 CSV、`events` ntuple 與 column map，供 shower-containment（`geant4_benchmarks.py` 行 487）與 B2.5 的後漏比例使用。

### B1.4 逐事件 ROOT 檔

| 項目 | 規格 |
|---|---|
| 寫出 | 經 `G4AnalysisManager`（ROOT 輸出類型）；底層是 Geant4 內附的 g4tools，不需要安裝 ROOT，不新增建置依賴 |
| 檔案 | 每個工作一個檔；MT 下以 `SetNtupleMerging(true)` 由 master 合併成單一檔（11.4.3 中只有 ROOT 輸出支援 ntuple 合併）；路徑經 `tilde()` 寫入 run record |
| 結構 | 扁平 ntuple，只用純量欄（I、D、S），每列帶鍵（`event_id` 加 ntuple 自己的次鍵）；不用 vector 欄 |
| 列的順序 | MT 合併後不固定；讀取端一律依鍵排序 |
| 寫出時機 | `EndOfEventAction` 填列；run 結束時寫檔並關閉。run 中斷時檔案不完整，run 判為 incomplete（exit 3） |
| 版本 | 結構 `element_sim.events/1`，檔內帶 `event_file_version` |
| 雜湊 | 檔案位元組含寫出時間，不逐位元相同；run record 同時記錄檔案 sha256（完整性）與 `simroot hash` 的 `content_sha256`（比對與 provenance）。一個邏輯 run 有多個工作檔時，`content_sha256` 對所有檔案的聯集依鍵排序後計算（`run` ntuple 除外，它逐檔不同），所以和切法無關 |
| 大小 | 不提交；run record 記錄路徑、雜湊、各 ntuple 列數與大小 |

| ntuple | 層級 | 每列 | 欄位 |
|---|---|---|---|
| `run` | `summary` 起 | 每檔一列 | spec 與 column map 的 sha256、程式版本與原始碼雜湊、Geant4 版本、邏輯 run 種子、事件範圍、`event_file_version` |
| `processes` | `summary` 起 | 每個 process 一列 | `process_id`、`name`（`hits` 的 process 編號對照表） |
| `events` | `summary` 起 | 每事件一列 | `event_id`、主粒子 PDG 碼、動能、起點、方向；各子系統總沉積；`leak_rear_MeV`、`leak_front_MeV`、`leak_lateral_MeV`；離開世界體積的能量；旗標 |
| `deposits` | `summary` 起 | 每事件 × 每個有沉積的體積一列 | `event_id`、`volume_id`、`copy`、總沉積、帶電粒子的沉積 |
| `crossings` | `crossings` 起（`hits` 也包含） | 每事件 × 每個被穿越的平面一列 | `event_id`、`plane_id`、`track_id`、PDG 碼、前步點位置、方向、動能、全域時間 |
| `hits` | 只在 `hits` | 每個有沉積的步一列 | `event_id`、`track_id`、`step_index`（該 track 的步序號；和 `event_id`、`track_id` 組成唯一鍵）、`parent_id`、PDG 碼、`volume_id`、`copy`、前後步點位置、時間、沉積、步長、`process_id` |

- `hits` 的事件數超過 `max_events_hits` 時，spec 驗證以 `rejected`（exit 2）拒絕。
- 估計（J15，`crossings` 層級）：壓縮前每事件最多約 4 kB（`crossings` 10 列 × 80 B、`deposits` 最多 110 列 × 28 B、`events` 約 120 B）；10⁵ 事件壓縮前最多約 400 MB。

### B1.5 `simroot`

**位置：** `adapters/geant4/assets/simroot/`（和 `element_sim` 同一個 CMake 專案；只連結 Geant4 的 analysis 函式庫，不建立 run manager）。

- **先做一天的試作：** 確認 `G4RootAnalysisReader` 能讀 MT 合併、壓縮過的檔案與字串欄；不足時 `simroot` 只讀扁平純量欄，`run` 的字串改寫到 JSON 旁檔。

| 子命令 | 內容 |
|---|---|
| `info` | 各 ntuple 的列數與欄位、`run` 列的內容；輸出 JSON |
| `dump` | 依鍵排序後，把指定 ntuple 與欄位寫成 CSV（stdout 或 `--out`），浮點以 `%.17g`；可一次讀多個檔；`--events` 取子集 |
| `hash` | 內容雜湊：各 ntuple 依鍵排序，數值以 hex-float 正規化後計算 sha256；輸出 `content_sha256` |

- 退出碼依 `core/status.py`。研究者可以用 ROOT 或 uproot 直接分析 ROOT 檔，但它們不是管線或必要測試的依賴。

### B1.6 兩個後端的介面一致性

- `element_sim` 交出的三個邊界產物通過和 `layered_sim` 相同的介面測試（schema、雜湊、column map 的語意名稱）。
- **統計一致性只比兩個後端都產生的觀測量。** J14 的 `stopping-power` 與 `thin-layer-mpv` 需要 `primary_eloss_MeV`、`primary_fate`、`primary_end_process`（`geant4_benchmarks.py` 行 233、284、325、365），`element_sim` 不產生這些欄（它只記錄入射穿越），所以不比較 J14 的 benchmark 判定。
- 做法：和 J14 nominal 相同的平板（`Si_study` 以混合材料宣告相同的組成與密度、相同的物理設定與 cut），兩個後端各跑一個邏輯 run（`layered_sim` 用 `stream`、`element_sim` 用 `per-event`，事件不同）；比較矽中沉積 `edep_Si_MeV` 的平均與眾數（A1.7），以及量能器型配置的 `leak_rear_MeV` 比例。每個觀測量的差在 3·se_diff 內。

### B1.7 adapter 變更流程

| 項目 | 內容 |
|---|---|
| 版本 | 0.2.0 → 0.3.0 |
| `adapter.json` | `assets` 加入 `element_sim/`、`simroot/`、`element_sim.spec/1` 的 schema；更新 `purpose` |
| `SIM_SOURCES` | 目前是一個扁平的檔名 tuple，只在 `ASSETS/"layered_sim"` 下計算雜湊（`geant4_run.py` 行 63、327）。改為依程式分組的對照表 `{"layered_sim": [...], "element_sim": [...], "simroot": [...], "g4sim": [...]}`，每個 run record 記錄所用程式及 `g4sim` 的檔案雜湊；`element_sim` 的實際檔名在 B1.1 定案後列出（場的程式放在 `element_sim/Field.hh`、`Field.cc`）；`layered_sim` 的雜湊鍵不變，舊紀錄仍可比對 |
| G5 | 聲明「依 Geant4 API 撰寫，未複製或改寫任何範例程式碼（含 B5）」，由審查者在 VALIDATION 條目中確認；同一條目註明 ROOT 檔類型與 `simroot` |
| 測試 | 離線測試（spec 驗證、跨欄位規則）；live 測試（`HEP_GEANT4_LIVE_TEST=1`）：幾何、場、事件檔、`simroot` 往返 |
| 文件 | `docs/capability-matrix.md` 的 Geant4 列；adapter 文件 |

### B1.8 B1 驗收

- [ ] `element_sim` 的 J15 幾何通過 overlap、物質預算與逐事件能量平衡；§4.1 與 §4.2 的核對數值由測試重算。
- [ ] B1.6 的介面一致性與兩個後端的統計一致性。
- [ ] `per-event` 下，同一邏輯 run 以 1、2、4 個工作與 1、2、4 個執行緒執行，summary 整數相同、浮點相對差 ≤ 1e-12。
- [ ] MT 測試指令回報的各執行緒 field manager 指標彼此不同；探針記錄的場參數和 spec 一致；場計入目標雜湊。
- [ ] B2.5 的確定性場檢查在名義值下通過；各格點的結果都回報；`field-propagation` 的 negative control（Geant4 端 B × (1 ± δ)，δ 由 trial run 選定使偏差超過判定標準）被抓到（場的驗證在 B1 完成，因為它只需要 `element_sim`）。
- [ ] `simroot` 往返：各層級、I、D、S 欄的值相同；serial 與不同執行緒數的 `content_sha256` 相同；`deposits` 依事件加總等於 CSV 的子系統總沉積；`hits` 超過上限時 exit 2；run 中斷時 incomplete。
- [ ] VALIDATION GEANT4-ELEMENT；CHANGELOG；release manifest。

---

## 6. 階段 B2：重建、J15 與 C2（adapter 0.4.0、contracts C2）

### B2.1 `simreco`（數位化與重建）

**位置：** `adapters/geant4/assets/simreco/`（CMake 專案；只用 C++17 標準函式庫與 `g4sim` 中不連結 Geant4 的 `SimHash.hh`、`SimSummary.hh`、`MiniJson.hh`；不連結 Geant4）。介面：`geant4_run.py reco`。參數（ε、σ_t、名義 B、標定樣本）寫在 hep-detector 擁有的 reco spec 中。hep-detector 不新增腳本。

**輸入：** `simroot dump` 從 ROOT 檔取出的 `crossings` 與 `deposits`（依鍵排序，經管線傳遞、不另存）以及摘要 CSV。

| 步驟 | 內容 |
|---|---|
| 矽 | 穿越點加高斯誤差：偏轉方向（y）ε = 10 µm，非偏轉方向（z）30 µm；擬合使用的 x 和 scorer 相同（入射面） |
| TOF | 每層的時間加獨立的高斯誤差 σ_t（100 ps；敏感度另做 150 ps）；站時間 = 兩層時間的平均（先以擬合軌跡把兩層的時間換算到站中心）；另外輸出每層的 dE/dx 與同站兩層的時間差 |
| 徑跡 | x–y 平面圓擬合，含多重散射共變異（否則 1 GV 時 χ²/dof 上千），得到曲率 κ；x–z 平面直線擬合，得到傾角 λ；以名義 B 計算 R_reco = C·B/(κ cos λ)（使用總動量，C = 0.2998 GV/(T·m)）；輸出 R、χ²、自由度 |
| 剛度真值 | 1/R_true = 六片平面穿越紀錄的 \|q\|/p_i 的平均（使用**總動量** p_i，單位電荷時 1/R = 1/p）；R_true 與 R_reco 都用總動量，避免 p 與 p_T 之差（50 mrad 時約 0.125 %，大於 μ 場檢查的 0.05 % 容許） |
| β | 路徑長以兩站中心為端點，包含 TOF1→Si1、Si6→TOF2 的直線段與三維傾角；低 β 時回報 β 在兩站之間的變化 |
| 量能器 | 主動層總沉積除以**電子**取樣比例；取樣比例由 `calibration` 角色的 10 GeV 電子樣本求得；另外輸出 e/mip |
| 亂數 | 每個事件的數位化亂數流以 `SimHash.hh` 的 SplitMix64 產生，種子為 H(S, i, "digi")（A1.4 的 H；S 為邏輯 run 種子，i 為事件編號），常態亂數用 `SimHash.hh` 的 Box–Muller；不用 `std::normal_distribution`（libstdc++ 與 libc++ 的輸出不同）。和 Geant4 的亂數流分開，跨平台結果相同 |

**輸出：** 逐事件結果 CSV（R、χ²、β、量能器能量等）與 run summary（`simulation-summary/1`，產生者 `simreco`；觀測量如 1/R_reco − 1/R_true、β − β_true 的區塊累加）。

- `geant4_run.py reco` 每次執行寫一份 computational-run 紀錄（含 `**trace.provenance()`、`simreco` 的程式雜湊、輸入 run record 的雜湊與 ROOT 檔的 `content_sha256`、dump 的 ntuple 與欄位清單）。改變數位化參數不需要重跑模擬。
- 退出碼依 `core/status.py`：0 ok、1 負向判定、2 `rejected`（無法讀取的輸入，含缺檔）、3 incomplete。
- **CLI 登記：** `tests/skills/test_cli_robustness.py` 的 `MISSING_FILE_ARGS` 目前每個腳本只對應一組 argv，`geant4_run.py` 已被 `run` 佔用（行 130）。擴充為「每個腳本可對應一組或多組 argv」，再加入 `reco` 與 `table`。
- **擬合器的單元測試：** `tracker_resolution.py` 不做擬合，只由拋物線最小平方算出曲率解析度（`curvature_sigma`，行 89）。所以測試比較的是：在無多重散射的 toy（R ≥ 300 GV）上，C++ 擬合的 σ(1/R) 與 pull 寬度，和 `tracker_resolution.py momentum` 給的量測項解析度（`mdr_intrinsic_gev`）在 toy 的 MC 誤差內一致；pull 寬度在 1 ± 3σ_MC 內。

### B2.2 結果表與遞移的處理鏈（C2）

- 重建後的結果表（例如剛度解析度對剛度）以 **simulated dataset-record** 發布，由 `geant4_run.py table` 寫出（含 `trace.provenance()`）。
- **遞移的處理鏈：** 目前 `dependencies.py` 要求 simulated 表格的每個輸入都是帶 `extension.simulation` 或 `extension.study` 的 computational-run；重建紀錄兩者都沒有。C2 改為：輸入鏈可以任意深，只要每一層都是有紀錄的 computational-run，而且鏈的每個根都是模擬 run（需 hep-computing 同意；§9）。
- J15 的 study record 是 `unvalidated`，表格保持 `unvalidated`；使用它的 communication 會得到 `communication.simulated_source` 警告，圖表標示「Simulation」。

### B2.3 C2 的驗證類別

**新增的 benchmark 表條目**（A1.1 的格式；等級即類別；`GRADES` 與 study spec 的 benchmark、grade enum 同步加入；新的計算函式放在 `geant4_benchmarks.py`，只讀 summary）：

| benchmark | 類別 | 支持的 kind | 範圍維度 | 計算位置 |
|---|---|---|---|---|
| `field-propagation` | verification | — | — | `geant4_benchmarks.py` 的 `field_propagation()`，讀 `simroot dump` 的 `crossings` 與解析螺旋 |
| `field-propagation-muon` | sanity | — | — | `field_propagation_muon()`，讀 `simreco` 的 summary（1/R 的區塊累加） |
| `tof-beta` | verification | — | — | `tof_beta()`，讀 `simreco` 的 summary |
| `tof-layer-consistency` | verification | — | — | `tof_layer_consistency()`，讀 `simreco` 的 summary |
| `sampling-fraction` | sanity | — | — | `sampling_fraction()`，讀 `element_sim` 的 summary |
| `regression-comparison` | regression | — | — | `regression_comparison()`，讀兩個版本的 summary |
| `surrogate-comparison` | surrogate | — | — | `surrogate_comparison()`，讀代理模型與參考模擬的 summary |

- **verification：** 不計入升級。
- **regression：** 同一研究、同一設定，在新舊兩個版本（plugin、後端或 Geant4）各執行一次；兩次的 point_id 為版本標籤，所以 S 不同、樣本獨立（不違反 A1.4 的 S 不重複）。只比較純量觀測量（直方圖的比較屬於 §8 延後的分布層級 benchmark）。判定有三種：`changed`：|diff| − t_{1−α/m}·se_diff > tol；`unchanged`：A1.8 的通過規則；其他為 `unresolved`；由判定引擎的 `change`（任務 A A1.8）執行。容許值與 α 事先宣告。紀錄不影響 label；reference 觀測量 `changed` 時可觸發 sci-fix 檢查。
- **surrogate：** 代理模型**永遠不改變物理 label**。代理模型的研究宣告參考研究（一份 study record，不是 run record；run record 不帶升級）與範圍；以 A1.8 的 IUT 判定（χ² 只作診斷，不作通過依據）。通過時記錄 `extension.study.surrogate = {reference_study_ref, reference_sha256, scope}`，scope 為宣告範圍與參考研究範圍的交集。
- 閘控方式同 C1：`strict or _at_least(contract_version, C2)`，無 warning 分支。

### B2.4 J15 的驗證梯

| 檢查 | 類別 | 參考 | 規格 | negative control |
|---|---|---|---|---|
| overlap | 實作 | — | — | 平移一片 Si 造成重疊 |
| 逐事件能量平衡（J15 幾何） | 實作 | 能量守恆 | — | 不加 2 mₑc²、重複計入 |
| 物質預算（geantino） | 實作 | PDG X₀ 加總 | 容許約 2 %（Geant4 的 X₀ 公式和 PDG 約差 1 %） | Pb 密度 ± δ |
| `field-propagation` | **verification** | charged geantino 對解析螺旋 | 見 B2.5 | Geant4 端 B × (1 ± δ) |
| `field-propagation-muon` | **sanity** | 平面平均的 1/R 真值（B2.1） | μ⁻ 1、10、100 GV；觀測量 (1/R_reco − 1/R_true)·R_true 的平均；容許 = t_{K−1}·SE + 0.05 %；相對 SE 目標 0.1 %，N 依 A1.9 由 trial run 決定（估計：1 GV 約 400、100 GV 約 7400，對應 SE 約 0.07 % 與 0.10 %） | Geant4 端 B × (1 ± 1 %) |
| 擬合器單元測試 | 測試（不是 benchmark） | 無多重散射的 toy（R ≥ 300 GV）：`simreco` 的 σ(1/R) 與 pull 寬度對 `tracker_resolution.py` 的量測項解析度（B2.1） | — | — |
| 多重散射一次性比較 | sanity | `multiple_scattering.py` 的解析項（不含 log）；可另用 `toy_spectrometer.py`（需 NumPy） | μ 與 p，1–10 GV，含 β | — |
| `tof-beta` | **verification**（bookkeeping） | 沿真實軌跡的運動學 | — | scorer 測試旗標注入時間偏移；沒有 Geant4 端的物理控制組，文件中註明 |
| `tof-layer-consistency` | **verification**（bookkeeping） | 同站兩層的時間差對「層間路徑長 / βc」（β = 1、正入射時 66.7 ps） | 殘差平均為 0；寬度 √2 σ_t（100 ps 時 141 ps） | 以測試旗標在一層的 scorer 時間注入偏移 |
| `sampling-fraction` | sanity | PDG 的 μ 能損表（Groom 等，經 hep-citations 取得）在 run 動量下的游離 dE/dx 比 | μ⁻ 1 GeV；統計量為 Σ PVT 沉積 / Σ（PVT + Pb）沉積；合理範圍 ±10 %（審查者的 Bethe 估計約 0.271）；和 `calibration` 樣本用不同種子 | PVT 密度 ± δ |
| 簇射包容 | sanity | PDG gamma 剖面，混合物有效臨界能約 10.2 MeV | 電子 1–100 GeV | — |
| `longitudinal-profile`（0.21.0） | 不適用 | 它的參考是已發表的 ALICE FoCal-E 量測，只對該堆疊有效；J15 的量能器不同，而且是 embedded | — | — |
| 選用：孤立 PVT 平板的 stopping power | reference（`configuration: isolated`） | Bethe（RPP 2024 式 34.5） | p、T = 200–600 MeV（βγ ≈ 0.69–1.30，低於 PVT 的 10^x₀ ≈ 1.40，密度修正為 0）、1 cm 平板、排除核作用（約 1 %）；Sternheimer 參數取自 Sternheimer, Berger & Seltzer (1984) 並以 hep-citations 核對 | PVT 密度 ± δ |

選用的最後一項在孤立平板中執行（`element_sim` 的單一元件），不是 J15 探測器的一部分，用來示範新材料的升級路徑。事件數與判定依 A1.6–A1.10。

### B2.5 收斂掃描

**場精度與最大步長（確定性，不需統計；在 B1 完成）：**
- 軌跡：charged geantino（質量 0，β = 1），剛度 0.6、1、10、100、1000 GV。
- 方向：正入射；偏轉平面內 **50 mrad，方向和偏轉相反**（正電荷取 +y）；非偏轉平面 ±50 mrad。
- 附錄 A 核對：在這組方向下，每條軌跡都到達每片 Si 和 TOF2 的兩層，也不離開場區母體。若改成順偏轉方向，0.6 GV 和 1 GV 會錯過 Si6。
- 參考：解析螺旋；軌跡離開場區時改為分段直線，只比較解析軌跡實際到達的平面。

| 掃描 | 格點 | 判定 |
|---|---|---|
| delta intersection | 1e-3、1e-4、1e-5、1e-6 mm | 名義值（1e-5）下，所有平面的平面內距離 √(Δy² + Δz²) ≤ 0.5 µm（ε/20），解析軌跡在平面的 x 上取值；最細兩組相差 ≤ 0.2 µm；另記錄 Geant4 穿越點的 \|x − x_平面\|。各格點的結果都回報，不預設 1e-3 mm 一定不通過（Geant4 的交點誤差主要沿 x，換成平面內誤差只約為斜率 × δ ≤ 0.25 µm） |
| 最大步長 | 100、30、10、3 mm | 同上 |
| delta one step 與 epsilon | 名義值與 1/10 | 預期無變化，做一次確認 |
| TOF2 路徑時間（兩層） | — | \|Δt\| ≤ 1 ps（約 0.3 mm 路徑長），只檢驗路徑長 |

**量能器 production cut：**
- 格點：0.1、0.3、0.7、1.0 mm。
- 樣本：10 GeV e⁻；先跑 trial，再依 A1.9 決定 N。
- 觀測量：總沉積（相對容許 1 %，約 400 個簇射/點）、後漏比例（`element_sim` 的 `leak_rear_MeV`（B1.3）除以入射動能，只算量能器母體的後表面；**絕對**容許 0.002，`tolerance_mode: absolute`，約 5000 個簇射/點）。
- 每點事件數取兩者的較大值；判定依 A1.8（IUT）。

Si 的 production cut 不在 J15 收斂：它只影響 Si 的沉積，而 J15 的 Si 結果不作為證據。study spec 的 `convergence_plan.observables` enum 加入總沉積與後漏比例。各 benchmark 依賴的參數組事先宣告，並以探針的實際設定核對。

### B2.6 variation

| variation | 範圍 | 規則 |
|---|---|---|
| EM option4 對 option3 | 量能器剖面、取樣比例 | `G4R-PRECISION-EM` |
| FTFP_BERT_EMZ 對 **QGSP_BIC_EMZ** | 1.5 GeV 以下核子；觀測量為末態量：第一次作用後 5 層的沉積、作用後的帶電次級粒子能量。作用機率與第一次作用深度只在探針確認兩者的非彈性截面不同時才回報（兩個 physics list 可能共用核子截面，那時差值必為 0，正是 protocol 行 161 警告的假零） | `G4R-BIC-RANGE`；3 GeV 以下 π、6–12 GeV 強子兩者模型相同，不得作為 variation |
| 真空對空氣 | 多重散射、剛度解析度 | — |

### B2.7 TOF 時間解析度的敏感度

- `simreco` 以 σ_t = 100 ps 與 150 ps 各重建一次（同一份模擬，不需重跑）。
- 回報兩者的 σβ/β（預期約 2.3 % 與 3.5 %）與 β 解析度對剛度的影響；README 說明 100 ps 比 AMS-02 的系統解析度（約 140 ps）樂觀。

### B2.8 J15 研究與 journey

- J15 的 study spec 宣告：觀測量（剛度解析度、β 解析度、取樣比例、總沉積、後漏比例）、K 與 B、benchmark、收斂計畫、variation、停止規則。
- 所有結果 `unvalidated`；README 與 study record 寫明「verification 載體」的定位。

### B2.9 recorded 資料預算

- `check_packaging.py` 的單檔上限 2 MiB；J14 的 `recorded/` 為 2.6 MB（參考）。
- ROOT 檔不提交；run record 只記錄路徑、檔案 sha256、`content_sha256`、各 ntuple 列數與大小；測試需要的 ROOT 檔在 live 測試中產生。
- J15 只提交：run summary（模擬與重建）、effective config、column map、縮減欄位的摘要 CSV（benchmark run）、以 `simroot dump --events` 取出的縮減穿越與沉積紀錄（供離線重播 `simreco` 的測試；事件子集依預算決定）、重建的結果表。
- 驗收：每檔 ≤ 2 MiB，J15 的 `recorded/` 總和 ≤ 3 MB。

### B2.10 註冊與文件

| 項目 | 內容 |
|---|---|
| 腳本計數 | hep-detector 不新增腳本，`DetectorScriptCount` 維持 21，`docs/capability-matrix.md` 行 47 不變 |
| CLI 登記 | `geant4_run.py reco`、`table` 在 `tests/skills/test_cli_robustness.py`（依 B2.1 擴充 `MISSING_FILE_ARGS`）與 adapter 測試中登記；`simreco` 的原始碼列入 `adapter.json` 的 `assets` |
| 路由表 | 不修改 `skills/hep-detector/SKILL.md`；J15、`element_sim` 與 `simreco` 的說明放在 `geant4-study-protocol.md` 與 adapter 文件 |
| journey | J15；`docs/researcher-journeys.md`、`docs/maintenance.md` 範例表；`tests/examples/test_geant4_minimal_spectrometer.py`（重播並比對判定） |
| capability | `docs/capability-map`（在 `full-detector-simulation` 下新增項目，執行 `capability_map.py --write`）、`docs/capability-matrix.md` |
| 路由 | 新增 J15 的路由案例；`check_routing_static.py` 從 `docs/researcher-journeys.md` 讀取 journey 清單，所以 J15 一列入表就**必須**有路由案例。重跑 live 的 Geant4 案例，包括既有的繁中欠規格案例 `g4-underspec-2` |
| 描述長度 | description 1,016 / 1,024 字元（`measure_entrypoints.py`）；路由案例沿用已有的觸發詞，不改描述 |
| 獨立審查 | 本任務的 Markdown（protocol 變更、J15 README、本文件）以 0.22.0 的 `review.py` 審查；紀錄只是 advisory，依 O04/O14 不取代人工的 G5 確認 |
| 其他 | `reference_inventory.py --check`、CHANGELOG、release manifest、adapter 0.4.0、`SIM_SOURCES` 的 `simreco` 分組；C++17 CI 工作建置與測試 `simreco`（必要或選用由維護者決定，§9） |

### B2.11 B2 驗收

- [ ] `field-propagation-muon`、`tof-beta`、`tof-layer-consistency`、`sampling-fraction` 執行完成；各自的 negative control 依 B2.4 被抓到，或註明沒有控制組。
- [ ] `simreco` 的擬合器單元測試依 B2.1 通過；`simreco` 在 CI 工作中建置與測試（維護者核准必要工作時為必要工作；否則為選用工作，並附一份本機建置與測試紀錄）。
- [ ] `simreco` 的數位化結果在 Linux（libstdc++）與 macOS（libc++）上逐位元相同。
- [ ] 新增的 benchmark 表條目（B2.3）與 `GRADES`、study spec 的 enum 一致（一致性測試）。
- [ ] `simreco` 的 summary 通過與任務 A 的 A2.9 相同的一致性測試（Python 由逐事件結果 CSV 重算）。
- [ ] 三層以上的處理鏈（模擬 → 重建 → 表格）被 `dependencies.py` 接受；根不是模擬 run 時被拒。
- [ ] verification 類別不計入升級；一個回歸檢查（例如 J14 在兩個 plugin 版本上）產生 `changed`、`unchanged` 或 `unresolved` 的紀錄且不影響 label；surrogate 規則的契約測試：帶 `extension.study.surrogate` 的紀錄宣告 `validated-in-scope` 時被拒絕；參考不是 study record 時被拒絕。
- [ ] 隔離規則的契約測試：缺少 configuration、embedded、類別與表不符時都被拒絕；J14 在 `--strict` 下仍通過。
- [ ] TOF σ_t 的 100 與 150 ps 敏感度已回報。
- [ ] recorded 預算、註冊項目、文件全部完成；VALIDATION GEANT4-J15。
- [ ] 獨立 agent 只依文件與工具完成「1 GV 質子在 J15 的剛度解析度」：結果紀錄通過 `validate.py --strict`、label 為 `unvalidated`、解析度（(1/R_reco − 1/R_true)·R_true 分布的中央 68 % 半寬）落在 §4.2 多重散射表 1 GV 質子一列的範圍內（1.8–2.6 %，量測項在 1 GV 可忽略），過程不需要維護者協助。

---

## 7. 契約與版本

| 物件 | 位置 | 版本 |
|---|---|---|
| verification、regression、surrogate 類別；J15 的檢查；遞移的處理鏈 | `contracts/validate.py`、`contracts/dependencies.py` | C2（minor、閘控） |
| `element_sim`、`element_sim.spec/1`、`element_sim.events/1`、`simroot` | adapter | adapter 0.3.0 |
| `simreco`、reco spec | adapter（C++，不連結 Geant4） | adapter 0.4.0 |
| `GRADES` 與 study spec 的 grade enum 加入 `verification`；`convergence_plan.observables` 加入總沉積與後漏比例 | hep-detector | 隨 plugin 版本 |

---

## 8. 不做與延後

| 項目 | 決定 | 理由 / 觸發條件 |
|---|---|---|
| 量測主導區 σ(1/R) 作為 benchmark | 不做 | 改為擬合器單元測試 |
| `skills/hep-detector/scripts/digitize_reconstruct.py` | 不做 | 改為 C++ 的 `simreco` |
| `layered_sim` 的新幾何功能 | 不做 | 新功能只加在 `element_sim` |
| 管線中以 Python 直接讀 ROOT（uproot） | 不做 | 經 `simroot` |
| 離子源與 Birks 可見能量（未來 J17；J16 用於任務 C 的自動設計範例） | 延後 | 宇宙線核素研究，且 PVT 的 Birks 常數有文獻紀錄。實作時依 11.4.3：在 `GeneratePrimaries` 中以 `GetIon(Z, A)` 取得離子；在 `Construct` 設定 kB（`GetIonisation()->SetBirksConstant`）、PreInit 呼叫 `G4EmParameters::Instance()->SetBirks(true)`，再以 `G4LossTableManager::Instance()->EmSaturation()` 取得（API 名稱實作時以 11.4.3 原始碼核對） |
| `element_sim` 的非盒狀 solid、旋轉、GDML 讀入、field map、邊緣場 | 延後 | 第一個需要它們、又不能用使用者應用的研究 |
| 分布層級的 benchmark（含 regression 的直方圖比較）、觀測量的組合、profile、`gps` 與 `event-file` 粒子源、`simreduce` | 延後（介面已定義於架構 §9.2） | 各自的第一個用例 |
| RNTuple、vector 欄 | 延後 | ROOT 檔大小或讀取速度成為瓶頸 |

其他不做與延後的項目見任務 A §10。

---

## 9. 待維護者決定的事項與殘餘風險

**待決定：**
1. C2 的遞移處理鏈：需要 computational-run schema 的擁有者 hep-computing 同意。
2. C2 的版本歸類（建議 minor）。
3. `simreco` 的 C++17 CI 工作是否為必要工作（B2.11 依此決定驗收方式）。
4. ROOT 檔的存放位置與保留期限（不提交 repo）。
5. `element_sim` 作為第二個 Geant4 程式的維護歸屬（建議 hep-detector）。

**殘餘風險：**
1. 取樣比例的參考需要 PDG 的 μ 能損表；選用的 PVT benchmark 需要 Sternheimer 參數。兩者都要經 hep-citations 取得文獻紀錄後才能使用。
2. 量能器簇射主導 CPU 時間；後漏的收斂每點約需 5000 個簇射，事件數由 trial run 決定並記錄。
3. `G4RootAnalysisReader` 的讀取能力未驗證（B1.5 的試作）。
4. 大樣本的 ROOT 檔可達數百 MB；MT 合併時 worker 的 basket 在 run 結束前留在記憶體中；`hits` 有事件數上限，大小與記憶體在 trial run 中確認。
5. 兩個 Geant4 程式的維護成本；靠 `g4sim` 控制重複。
6. quick load 只剩 931 bytes、description 1,018 / 1,024 字元：本任務不得修改 `SKILL.md` 與 description。
7. 工作量尚未估計；任務 A 完成後依實際的 `g4sim` 再估計。
8. 任務 A 的殘餘風險（區塊獨立的前提、接近門檻的判定、探針假設 worker 與 master 設定相同）同樣適用，見任務 A §11。
9. B2.6 的強子 variation：若兩個 physics list 的核子非彈性截面相同，作用機率不會改變；只回報末態量（B2.6）。
10. 本文件中部分 Geant4 行為（stepper 的建立、Birks 的 API、交點誤差的方向）依審查者的經驗判斷，未逐行核對 11.4.3 原始碼；實作時先核對。

---

## 10. 建議的執行步驟

**B1**
1. 開始前檢查（§0）；確認 §2 的介面都存在。
2. `element_sim` 的 spec、schema、跨欄位規則與幾何（B1.1）；以 J14 相同的平板配置做兩個後端的一致性（B1.6）。
3. 場（B1.2）與 MT 測試；B2.5 的確定性場檢查（不需統計，可最早驗證）。
4. 建立 J15 幾何（§4.1）；通過 overlap、物質預算、能量平衡；以測試重算 §4.1、§4.2 的核對數值。
5. 平面穿越 scorer（B1.3）與 ROOT 檔（B1.4）；`simroot` 先做一天的試作再定案（B1.5）。
6. B1.7 的 adapter 變更項目；B1.8 全部打勾。

**B2**
1. `simreco` 的擬合器單元測試，再接 `simroot dump` 的輸入（B2.1）；建立必要的 CI 工作。
2. `geant4_run.py reco` 與 `table`；C2 的遞移處理鏈與驗證類別（B2.2、B2.3）及契約測試。
3. 在 E2 執行驗證梯、量能器 cut 收斂、variation、TOF 敏感度（B2.4–B2.7）。
4. J15 研究、recorded 資料、註冊與文件、獨立 agent 的驗收題（B2.8–B2.10）；B2.11 全部打勾；跑任務 A §9 的檢查。

---

## 附錄 A：數值

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
| 1000 GV | 66.0 | 25.0 … 65.0 | 74.5、75.5 |

若方向和偏轉相同（−50 mrad）：0.6 GV 在 Si6 的 y = −151 mm、1 GV 為 −116 mm，都錯過 Si6。

**TOF**：σ_站 = σ_層/√2，σβ/β = σ_層 c / D；每層 80、100、150 ps 對應 1.8 %、2.3 %、3.5 %（每站一層時 2.6 %、3.3 %、4.9 %）。同站兩層之間 β = 1 的飛行時間 66.7 ps，兩層時間差的解析度 √2 σ_層（100 ps 時 141 ps）。

**量能器**：18.41 X₀、0.886 λ_I、35 cm；有效 Molière 半徑 3.95 cm；mip 能損比 0.284 只是 dE/dx_min 之比，**不是**參考值。

**量能器前的物質**：11.32 % X₀（四層 TOF 9.40 %，佔 83 %；Si 1.92 %）、5.46 % λ_I；其中 TOF1 在徑跡之前，佔 4.70 % X₀。

**事件數**（差值 se ≤ tol/4）：10 GeV 電子總沉積（容許 1 %）約 392；後漏（絕對容許 0.002）約 5000。

## 附錄 B：出處

- PDG Atomic and Nuclear Properties（2026-10-21 取得）：[Silicon](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/silicon_Si.html)、[Lead](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/lead_Pb.html)、[Polyvinyltoluene](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/polyvinyltoluene.html)
- PDG Review of Particle Physics 2024，第 34 章：式 34.5、34.12、34.16、34.34–34.36（式號依 plugin 的 VALIDATION GEANT4-STUDY）
- Geant4 v11.4.3 原始碼，與場和事件檔相關：`G4FieldManager.hh`、`G4ChordFinder.hh`、`G4PropagatorInField.cc`、`G4FieldParameters`、`G4LogicalVolume`、`G4ChargedGeantino.cc`、`G4VAnalysisManager.hh`、`G4EmSaturation`、`G4LossTableManager`、`G4IonTable`、`G4NistMaterialBuilder.cc`
- Geant4 Book for Application Developers，[Basic Examples](https://geant4.web.cern.ch/documentation/dev/bfad_html/ForApplicationDevelopers/Examples/BasicCodes.html)（B4、B5）
- PAMELA 與 AMS-02 的出處見 [`architecture.md`](architecture.md) §14
- 待取得：PDG 的 μ 能損表（Groom, Mokhov & Striganov）；Sternheimer, Berger & Seltzer (1984), *Atomic Data and Nuclear Data Tables* 30, 261

## 附錄 C：版本歷程

| 版本 | 內容 |
|---|---|
| 探測器文件與 v5 | 單軸疊層磁譜儀；Gluckstern 小 N 公式更正；磁場方向與場檢查網格 |
| 2026-10-22 | TOF1、TOF2 各兩層；數位化與重建改為 C++；逐事件 ROOT 檔；拆分為任務 B |
| 2026-10-22 | 依參考實際實驗重新設計的架構改寫：新增 `element_sim` 作為第二個後端（取代 spec/2 與 `layered_sim` 的改造）；B1（`element_sim`、場、穿越、ROOT 檔、`simroot`）、B2（`simreco`、J15、C2 的 verification、regression、surrogate 與遞移處理鏈）；加入 PAMELA、AMS-02 對照與 TOF 敏感度 |
| **2026-10-23（本版）** | **獨立審查後修正：B1.6 只比兩個後端都產生的觀測量；量能器母體與 `leak_*_MeV`；新增 benchmark 表條目與計算位置；surrogate 永不改變物理 label；regression 三種判定與 point_id；剛度以總動量定義；`MISSING_FILE_ARGS` 擴充；`SIM_SOURCES` 依程式分組；`simreco` 用 `SimHash.hh` 的 SplitMix64 與 Box–Muller；stepper 明確建立；場檢查不預設 1e-3 mm 失敗；強子 variation 改用末態量；ntuple 的 `processes` 與 `step_index`；其他小修正** |
