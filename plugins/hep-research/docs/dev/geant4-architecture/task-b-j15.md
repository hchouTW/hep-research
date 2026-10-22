# 任務 B：J15 最小磁譜儀

> 文件類型：實作規格（給執行的 agent 與審查者）。狀態：提案，待維護者核准
> 順序：**在任務 A（[`task-a-core.md`](task-a-core.md)）的兩個階段都合併後才開始**
> 基準：撰寫時同任務 A（hep-research `main` 的 `9f08796`，contracts 3.5.0，Geant4 11.4.3）；開始前必須重新核對（§0）
> 日期：2026-10-22
> 語言：繁體中文原文；英文版 [`task-b-j15.en.md`](task-b-j15.en.md) 內容相同。兩者不一致時以中文為準，並同時修正英文
> 範例性質：J15 是**合成幾何**，是 verification 的載體，不是任何實驗的偵測器

---

## 0. 任務卡

**目標。** 以一個最小磁譜儀（J15）示範磁場、多個子系統與重建鏈，並建立 `verification` 等級：場區、平面穿越 scorer、以 C++ 的 `simreco` 做數位化與重建，以及讓重建紀錄成為 simulated 表格的輸入。

| 內容 | 版本 | 對 J14 的影響 |
|---|---|---|
| 場區（`field`）、平面穿越 scorer 與 ROOT 檔的 `crossings` 層級、`simreco`（數位化與重建；混合材料 0.21.0 已支援）、`verification` 等級、重建紀錄作為 simulated 表格的輸入 | adapter **0.3.0**、contracts **C2**（minor） | 不重錄；之後 live 重跑的 `sources_sha256` 會改變（預期） |

**不在範圍內：** 任務 A 的任何介面變更（若必要，先在任務 A 的範圍內以 adapter 修補版處理）；離子源與 Birks（未來 J16）；真實幾何與場圖（§11）。

**交付物：** layered_sim 的場與平面穿越、`simreco`、`geant4_run.py reco` 與 `table`、J15 範例（`examples/` 下的新資料夾、README、recorded 資料）、C2 契約變更、J15 journey 與路由案例、VALIDATION 條目 GEANT4-J15、CHANGELOG、release manifest。

**完成的定義：** §10 的驗收清單全部打勾，任務 A §10 的檢查全部通過。

**主要決定：**
1. **驗證等級依參考的性質決定**（任務 A 原則 9）。參考值是輸入的精確推論的（解析螺旋、運動學），屬於 verification，不能用來升級。
2. **場精度用確定性檢查。** 以 charged geantino 對解析螺旋比較，不需要統計（B2.2）。
3. **J15 是 verification 的載體。** 完整探測器中的所有結果都是 `unvalidated`；只有在孤立平板中執行的選用 benchmark 示範新材料的升級路徑（B2.1、B1.5）。
4. **hep-detector 不新增腳本。** 重建在 C++ 的 `simreco`，介面在 adapter；quick load 與 description 都不變（§9）。

**開始前必做：**
1. 確認任務 A 的階段 1（C1）與階段 2（adapter 0.2.0）都已合併，且 §2 列的介面都存在。
2. 依任務 A 附錄 B.2 的方法，以當時的 `main` 重新核對本文件引用的事實（quick load、description 長度、journey 清單、`DetectorScriptCount`、contracts 版本），並更新本文件（中英兩版）。
3. 讀任務 A 的 §2（硬性限制）與 §1（名詞）；本文件不重複。

---

## 1. 名詞與記法

| 名詞 | 意義 |
|---|---|
| J15 | 本任務的最小磁譜儀（合成幾何） |
| 偏轉平面 | x–y 平面（B 沿 z）；非偏轉方向為 z |
| 剛度 R | p/|q|，單位 GV；C = 0.2998 GV/(T·m) |
| MDR | 最大可偵測剛度：只算量測項時 σ_R/R = 1 的剛度 |
| TOF 站 | TOF1 或 TOF2；每站兩層（a、b） |
| charged geantino | Geant4 中只受場作用、無物質交互作用的帶電測試粒子（質量 0，β = 1） |
| verification | 參考值是輸入的精確推論的檢查等級；不計入升級（C2 加入契約表） |
| C2 | 任務 B 合併時下一個未使用的 contracts minor（在 C1 之後） |
| 章節記法 | 「B1.3」是本文件的工作項；「§4.2」是本文件的節；「A1.6」「A2.9」是任務 A 的工作項；「任務 A §2」是任務 A 的節 |

**主要檔案（相對 `plugins/hep-research/`）：** `adapters/geant4/assets/layered_sim/`（新增 `FieldSetup.*`，擴充 scorer 與 `EventFile.*`）；`adapters/geant4/assets/simcore/`（新增 `simreco`）；`adapters/geant4/assets/geant4_run.py`（新增 `reco`、`table`）；`contracts/validate.py`、`contracts/dependencies.py`（C2）；`skills/hep-detector/scripts/geant4_benchmarks.py`（`GRADES`）；`skills/hep-detector/assets/geant4-study-spec.schema.json`；`skills/hep-detector/references/geant4-study-protocol.md`；`docs/researcher-journeys.md`、`docs/maintenance.md`、`docs/capability-matrix.md`、`docs/capability-map`；`tests/examples/test_geant4_minimal_spectrometer.py`（新增）。

---

## 2. 前提：任務 A 提供的介面

| 任務 A 提供 | 任務 B 的用法 |
|---|---|
| C1：benchmark 對照表、範圍比對 kind、configuration 與隔離規則（A1.1–A1.3） | J15 的 benchmark 都是 `embedded`，不計入升級；C2 在對照表加入 `verification`（B1.5） |
| 統計規格：IUT 閘門、兩階段事件數、種子 `H(study_id, role, point_id, k)`、子 run（A1.5–A1.8） | 收斂掃描與 benchmark 的事件數與判定（B2.1、B2.2） |
| spec/2（A2.2）預留的 `field` 區塊；adapter 0.2.0 對非空 `field` 以 `rejected` 拒絕 | 實作 `field`（B1.1），解除拒絕 |
| `G4StepLimiterPhysics` 的加入條件（A2.3） | 有場時也加入 |
| spec/2 的 gun 欄位 `energy_MeV`（A2.2） | 加入 `ekin_per_nucleon_MeV` |
| 探針（A2.6）與 column map `layered_sim.output/2`（A2.7） | 探針加記錄場參數（B1.1）；column map 加入 `crossings` 的欄位 |
| `simcore`（A2.8）與其必要的 CI 工作 | 新增執行檔 `simreco`（B1.3），在同一個 CI 工作中建置與測試 |
| 逐事件 ROOT 檔（A2.9）與 `simroot`（A2.10） | 加入 `crossings` 層級與 ntuple（B1.2）；`simreco` 經 `simroot dump` 讀取 |

---

## 3. 硬性限制

任務 A §2 的全部限制都適用。另外：

1. 不修改 `skills/hep-detector/SKILL.md` 與 hep-detector 的 description（quick load 只剩 931 bytes；description 1,018 / 1,024 字元）。J15 的路由案例必須沿用 description 中已有的觸發詞。
2. `skills/` 與 `contracts/` 中不得出現實驗名稱（含 ALICE）；契約表與 protocol 引用 `longitudinal-profile` 的參考時用引用鍵。
3. 場的程式依 Geant4 API 撰寫，不複製或改寫 B5 範例的程式碼（G5）。
4. 共享 stanza 的文字不改（點 5 寫的是「3.1.0 upgrade rule」；修改會牽動全部 SKILL.md 與 live 路由重跑）。
5. J15 的 `recorded/` 每檔 ≤ 2 MiB、總和 ≤ 3 MB；ROOT 檔不提交（§7）。
6. J15 的所有結果都是 `unvalidated`；任何 J15 benchmark 都不得計入升級。

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

| 元件 | 材料 | 前表面 `at_mm` | 厚度 | 範圍 | 橫向（y × z） |
|---|---|---|---|---|---|
| 世界 | `G4_Galactic` | — | 2400 | −1200 … 1200 | 1200 × 1200 |
| 粒子源 | — | x = −1000，y = z = 0 | — | — | — |
| TOF1a、TOF1b | `G4_PLASTIC_SC_VINYLTOLUENE` | −810、−790 | 各 10 | −810 … −800、−790 … −780 | 300 × 300 |
| 場區母體 | `G4_Galactic` | −520 | 840 | −520 … 320 | 300 × 300 |
| Si1–Si6（子體） | `G4_Si` | −500.15 + 160k | 0.3 | 中心 −500、−340、−180、−20、140、300 | 200 × 200 |
| TOF2a、TOF2b | `G4_PLASTIC_SC_VINYLTOLUENE`（和 TOF1 相同） | 490、510 | 各 10 | 490 … 500、510 … 520 | 400 × 400 |
| 量能器 | 50 × (`G4_Pb` 2 + PVT 5) | 550 | 350 | 550 … 900 | 500 × 500 |

**TOF 站。** TOF1 與 TOF2 各由兩層組成；四層同材料（`G4_PLASTIC_SC_VINYLTOLUENE`）、同厚度（10 mm），每站兩層之間有 10 mm 的真空間隙。每層是一整片平板，不分割、不設 paddle 方向（刻意的簡化）；兩層提供兩次獨立的時間量測與 dE/dx 取樣，並讓同站兩層之間的一致性成為一項檢查（B2.1）。

**核對**（附錄 A 的程式，測試中重算）：
- 量測臂長 L = 0.800 m；Si1 前緣和 Si6 後緣距母體邊界各 19.85 mm。
- 場在量測區兩端各多延伸 20 mm。
- TOF 站中心（兩層的中點：−795、505 mm）之間的距離 D = 1.300 m。
- TOF2 後層的後表面（520）距量能器前表面（550）30 mm；TOF1 前層（−810）在粒子源（−1000）之後。
- 世界包含粒子源與量能器後端。

材料（11.4.3 的 NIST 定義對照 PDG）：`G4_PLASTIC_SC_VINYLTOLUENE` 為 1.032 g/cm³、I = 64.7 eV，和 PDG 一致；`G4_Si` 為 2.33 g/cm³（PDG 2.329）。

**刻意的簡化**（J15 的 README 逐條列出）：均勻場與銳利邊界、無磁鐵材料、矽為整片平面（無條帶、無電荷分享、未模擬 δ 射線造成的重心偏移）、TOF 每層不分割（無 paddle、無方向）、無光學光子、無觸發與讀出電子學。

### 4.2 參數與接受度

| 參數 | 值 | 依據 |
|---|---|---|
| B | 0.5 T | 多重散射項等於量測項的剛度約 16–22 GV（μ），與 B 無關。0.5 T 讓 1–10 GV 與 100–1000 GV 各有一個十倍區間 |
| Si 層數 | 6 | N = 4 時偏轉平面只有 1 個自由度；N = 8 的 MDR 只改善約 8 % |
| MDR | 約 1172 GV | 只算量測項時 σ_R/R = 1。參考值取自 `tracker_resolution.py` 的精確最小平方（常數 0.2998）。`multiple_scattering.py` 的 `mdr_intrinsic_only_gv` 是同一定義，但以 Gluckstern 近似計算（N = 6 時約 1131 GV）；0.21.0 起它另外輸出 `intrinsic_coefficient`（含本文件使用的精確係數）並在 N < 10 時警告 |
| TOF | 每站兩層；σβ/β ≈ 2.3 %（每層 100 ps、兩層獨立、β = 1；每站一層時為 3.3 %） | D = 1.3 m；站時間取兩層平均，σ_站 = σ_層 / √2 |
| 量能器 | 18.4 X₀、0.886 λ_I、寬 50 cm | 0.89 λ_I 足以用簇射形狀分離 e/p，不足以量強子能量 |

**多重散射項。** 設計估計用 Highland 公式，對總厚度取 log 項，再乘 1.0–1.4 的係數。審查以離散散射平面做精確最小平方，得到的係數為 1.02（加權擬合）到 1.06（不加權）。`multiple_scattering.py` 依其約定**不含** log 項；比較時寫明兩種約定的差異。

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

整體門檻 0.75 GV；只要求徑跡加 TOF 時為 0.51 GV。低於 0.364 GV 的軌跡從場區側面離開，之後在無場的世界中走直線。

電子：簇射軸在 1 GeV 時於量能器前、後表面分別偏離 82 mm 與 127 mm，5 GeV 時為 16 mm 與 25 mm。上游 11.3 % X₀（四層 TOF 佔 83 %）產生的軔致輻射光子不受偏轉，所以簇射軸不是直線外推；79 mm 的邊距是幾何估計，上游物質比單層設計多一倍，簇射檢查要以實際的橫向能量分布核對。電子的簇射檢查限 1 GeV 以上。

**上游能損**（Bethe 積分，TOF1 兩層共 2 cm PVT）：

| 質子剛度 | 動能 | TOF1 能損（兩層） | Δp/p | β 在兩個 TOF 站中心之間的變化 |
|---|---|---|---|---|
| 0.6 GV | 175 MeV | 10.23 MeV | 3.20 % | 2.87 % |
| 1 GV | 433 MeV | 6.00 MeV | 0.82 % | 0.46 % |
| 2 GV | 1271 MeV | 4.34 MeV | 0.24 % | 0.05 % |

0.6 GV 時 β 在兩站之間變化 2.87 %，大於 TOF 的解析度（2.3 %）：TOF 量到的是路徑上的平均 β，所以低剛度的 β 比較要用含能損的 β 模型，或限於 2 GV 以上。TOF1 在第一片 Si 之前，只改變入射方向與動量，不影響曲率解析度；剛度真值取自 Si 平面的穿越紀錄，不受 TOF1 影響。

**不能沿用 J14。** J15 的 Si 平面和 J14 的材料（`G4_Si` 對 `Si_study`）、物理設定、cut 都不同，而且 J15 只記錄入射，組不出 J14 的 E_in − E_exit 觀測量。

---

## 5. 實作工作項

### B1.1 場的實作

**修改：** `layered_sim`（新增 `FieldSetup.*`；spec/2 的 `field` 區塊解除拒絕）；探針；`SIM_SOURCES` 加入 `FieldSetup.*`。

- 在 `ConstructSDandField` 中建立 `G4UniformMagField`、`G4FieldManager`、`G4ChordFinder`，以 `G4ThreadLocal` 儲存；master 與每個 worker 各有一份。在 `Construct()` 中建立會讓 worker 共用非執行緒安全的 chord finder。
- 以 `SetFieldManager(fm, true)` 附在場區母體上，傳遞到所有子體。
- 有場時加入 `G4StepLimiterPhysics`（A2.3 的組成規則）。
- stepper 類別寫入 spec，並由探針記錄（helix stepper 會讓場傳輸檢查失去意義）。
- 依 API 撰寫，不複製或改寫 B5 範例的程式碼（G5）。

| 參數 | 名義值 | 備註 |
|---|---|---|
| `delta_chord_mm` | 0.25 | 最大步長小於約 80 mm 時不起作用，只記錄不掃描 |
| `delta_one_step_mm` | 0.01 | 均勻場中 Runge–Kutta 的截斷誤差遠小於交點誤差，預期掃描無影響；做一次確認 |
| `delta_intersection_mm` | **1e-5**（0.01 µm） | 決定穿越點的精度 |
| `min_epsilon_step` | 5e-5 | |
| `max_epsilon_step` | 1e-3 | epsilon = delta one step / 步長，會被夾在這個上限 |
| `max_step_mm` | 10 | 需要 `G4StepLimiterPhysics`；`G4UserLimits` 必須逐體積設定，不會傳遞到子體 |
| `stepper` | DormandPrince745 | 11.4.3 `G4FieldParameters` 的預設 |

- **探針：** 走訪 `G4LogicalVolumeStore`，以 `GetFieldManager()` 讀回 B、chord finder 與各精度參數；依指標去重，記錄原始附加的體積；註明 master 只看到 master 的副本。
- **MT 測試：** 只在測試建置中存在的 UI 指令，回報每個執行緒的 field manager 指標，必須彼此不同。
- gun 欄位加入 `ekin_per_nucleon_MeV`。

### B1.2 平面穿越 scorer 與 ROOT 檔的 `crossings` 層級

**修改：** `layered_sim` 的 scorer 與 `EventFile.*`；column map；`simroot` 的測試。

| 項目 | 規格 |
|---|---|
| 平面穿越 scorer | 主粒子（track ID 1）在 tracker 或 tof 平面**第一次**進入時（前步點狀態為 `fGeomBoundary` 且所在體積為該平面），記錄前步點的位置、方向、動能、全域時間、PDG 碼；每個平面一個「已記錄」旗標。粒子源若位於平面內，不會出現 `fGeomBoundary`，該平面不寫列 |
| 混合材料 | 0.21.0 已支援（`materials[].components`），J15 不需新增；PVT 與 Pb 直接用 NIST 材料 |
| 輸出 | 逐事件 ROOT 檔（A2.9，`crossings` 層級）：事件真值、10 片平面的穿越紀錄（6 片 Si、4 層 TOF）、逐體積沉積（含量能器逐層）；逐事件 CSV 只保留摘要欄（主粒子真值、各子系統總沉積）；column map 同時描述兩者，自動產生 |

**`crossings` 層級。** `output.event_file.level` 加入 `crossings`（包含 `summary` 的全部 ntuple），`event_file_version` 加一，ntuple 結構記為 `layered_sim.events/2`（只增加，不改既有 ntuple）：

| ntuple | 層級 | 每列 | 欄位 |
|---|---|---|---|
| `crossings` | `crossings` 起（`hits` 也包含） | 每事件 × 每個被穿越的平面一列 | `event_id`、`plane_id`、`track_id`、PDG 碼、前步點位置、方向、動能、全域時間（上表的平面穿越 scorer）；未穿越的平面不寫列 |

`simroot` 的往返與內容雜湊測試加入 `crossings` 層級（§10）。

### B1.3 數位化與重建（`simreco`）

**修改：** `adapters/geant4/assets/simcore/`（新增 `simreco`，`SIMCORE_SOURCES` 加入其原始碼）；`geant4_run.py`（新增 `reco`）；hep-detector 擁有的 reco spec（參數 ε、σ_t、名義 B、標定樣本）。hep-detector 不新增腳本。

輸入：`simroot dump` 從 ROOT 檔取出的 `crossings` 與 `deposits`（依鍵排序，經管線傳遞、不另存）以及摘要 CSV。

| 步驟 | 內容 |
|---|---|
| 矽 | 穿越點加高斯誤差：偏轉方向（y）ε = 10 µm，非偏轉方向（z）30 µm；擬合使用的 x 和 scorer 相同（入射面） |
| TOF | 每層的時間加獨立的高斯誤差 σ_t = 100 ps；站時間 = 兩層時間的平均（先以擬合軌跡把兩層的時間換算到站中心）；另外輸出每層的 dE/dx 與同站兩層的時間差 |
| 徑跡 | x–y 平面圓擬合，含多重散射共變異（否則 1 GV 時 χ²/dof 上千）；x–z 平面直線擬合；輸出 R、χ²、自由度；使用名義 B |
| 剛度真值 | 六片平面穿越紀錄的 C·B / p_T,i 取平均（C = 0.2998），使用橫向動量 |
| β | 路徑長以兩站中心為端點，包含 TOF1→Si1、Si6→TOF2 的直線段與三維傾角；低 β 時回報 β 在兩站之間的變化 |
| 量能器 | 主動層總沉積除以**電子**取樣比例；取樣比例由 `calibration` 角色的 10 GeV 電子樣本求得；另外輸出 e/mip |
| 亂數 | 計數器雜湊，和 Geant4 的亂數流分開 |

- `geant4_run.py reco` 每次執行寫一份 computational-run 紀錄（含 `**trace.provenance()` 與 `simreco` 的程式雜湊），輸入為 adapter 的 run record（含雜湊與 ROOT 檔的 `content_sha256`），並記錄 dump 的 ntuple 與欄位清單。改變數位化參數不需要重跑模擬。
- `simreco` 與 `geant4_run.py reco` 的退出碼依 `core/status.py`：0 ok、1 負向判定、2 `rejected`（無法讀取的輸入，含缺檔）、3 incomplete；`reco` 在 `tests/skills/test_cli_robustness.py` 的 `MISSING_FILE_ARGS` 登記。
- 擬合器以 Python 的 `tracker_resolution.py`（獨立實作）作為單元測試的參考（B2.1）。

### B1.4 重建結果表（simulated dataset-record）與 C2 標記

- 重建後的結果表（例如剛度解析度對剛度）以 **simulated dataset-record** 發布，由 `geant4_run.py table` 寫出（含 `trace.provenance()`）。
- 目前 `dependencies.py` 要求 simulated 表格的每個輸入都是帶 `extension.simulation` 或 `extension.study` 的 computational-run，而重建紀錄兩者都沒有；只列原始 run record 又會讓改變數值的步驟不在輸入鏈中。所以 C2 新增一個標記（例如 `extension.derived_from_simulation`），接受「輸入全是模擬 run 的 computational-run」作為 simulated 表格的輸入（需 hep-computing 同意，§12）。
- J15 的 study record 是 `unvalidated`，表格保持 `unvalidated`；使用它的 communication 會得到 `communication.simulated_source` 警告，圖表標示「Simulation」。

### B1.5 label 與 contracts C2

- 契約的 benchmark 對照表（A1.1）加入 J15 的檢查，等級為 `verification` 或 `sanity`；只有 reference 會被 `_study_upgrade` 計入。
- 隔離規則已在任務 A 的 C1 生效（A1.3）；J15 的所有 benchmark 都是 `embedded`，不會被計入。
- C2 另外包含 B1.4 的標記。
- **J15 的定位：** verification 載體。完整探測器中的所有結果都是 `unvalidated`，README 與 study record 都寫明。
- `geant4_benchmarks.py` 的 `GRADES` 與 study spec 的 grade enum 都加入 `verification`。

---

## 6. 驗證工作項

### B2.1 驗證梯

| 檢查 | 等級 | 參考 | 規格 | negative control |
|---|---|---|---|---|
| overlap | 實作 | — | — | 平移一片 Si 造成重疊 |
| 逐事件能量平衡（J15 幾何） | 實作 | 能量守恆 | — | 不加 2 mₑc²、重複計入 |
| 物質預算（geantino） | 實作 | PDG X₀ 加總 | 容許約 2 %（Geant4 的 X₀ 公式和 PDG 約差 1 %）；用來抓幾何與材料指定錯誤 | Pb 密度 ± δ |
| `field-propagation` | **verification** | charged geantino 對解析螺旋（檢驗數值積分精度） | 見 B2.2 | Geant4 端 B × (1 ± δ) |
| `field-propagation-muon` | **sanity** | 平面平均的 1/R 真值（B1.3） | μ⁻ 1、10、100 GV；容許 = t·SE + 0.05 %；N ≈ 400（1 GV）、≈ 7400（100 GV） | Geant4 端 B × (1 ± 1 %) |
| 擬合器單元測試 | 測試（不是 benchmark） | 玩具真值（R ≥ 300 GV）：`simreco` 的 C++ 擬合對 Python 的 `tracker_resolution.py`（獨立實作） | — | — |
| 多重散射一次性比較 | sanity | `multiple_scattering.py` 的解析項（不含 log，依其約定）；可另用 `toy_spectrometer.py`（需 NumPy） | μ 與 p，1–10 GV，含 β | — |
| `tof-beta` | **verification**（bookkeeping） | 沿真實軌跡的運動學 | — | scorer 測試旗標注入時間偏移；沒有 Geant4 端的物理控制組，文件中註明 |
| `tof-layer-consistency` | **verification**（bookkeeping） | 同站兩層的時間差對「層間路徑長 / βc」（β = 1、正入射時 66.7 ps） | 殘差平均為 0；寬度為 √2 σ_t（100 ps 時 141 ps） | 以測試旗標在一層的 scorer 時間注入偏移 |
| `sampling-fraction` | sanity | PDG 的 μ 能損表（Groom 等，透過 hep-citations 取得）在 run 動量下的游離 dE/dx 比 | μ⁻ 1 GeV；統計量為 Σ PVT 沉積 / Σ（PVT + Pb）沉積；合理範圍 ±10 %（審查者的 Bethe 估計約 0.271）；和 `calibration` 樣本用不同種子 | PVT 密度 ± δ |
| 簇射包容 | sanity | PDG gamma 剖面，混合物有效臨界能約 10.2 MeV | 電子 1–100 GeV | — |
| `longitudinal-profile`（0.21.0） | 不適用 | 它的參考是已發表的 ALICE FoCal-E 量測，只對該堆疊有效；J15 的量能器不同，而且是 embedded | — | — |
| 選用：孤立 PVT 平板的 stopping power | reference（`configuration: isolated`） | Bethe（RPP 2024 式 34.5） | p、T = 200–600 MeV（βγ ≈ 0.67–1.37，低於 PVT 的 10^x₀ ≈ 1.40，所以密度修正為 0）、1 cm 平板、排除核作用（約 1 %）；Sternheimer 參數須取自 Sternheimer, Berger & Seltzer (1984) 並以 hep-citations 核對 | PVT 密度 ± δ |

選用的最後一項在孤立平板中執行，不是 J15 探測器的一部分，用來示範新材料的升級路徑。事件數與判定依 A1.5–A1.8。

### B2.2 收斂掃描

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
- 樣本：10 GeV e⁻；先跑 trial，再依 A1.7 決定 N。
- 觀測量：總沉積（相對容許 1 %，約 400 個簇射/點）、後漏比例（以既有的 `leak_rear_MeV` 計算，只算後表面；**絕對**容許 0.002，約 5000 個簇射/點）。
- 每點事件數取兩者的較大值。
- 判定依 A1.5（IUT 閘門）。

Si 的 production cut 不在 J15 收斂：它只影響 Si 的沉積，而 J15 的 Si 結果不作為證據。study spec 的 `convergence_plan.observables` enum 目前只有四個薄層觀測量，本任務加入總沉積與後漏比例。各 benchmark 依賴的參數組在 study spec 中事先宣告，並以探針的實際設定核對。

### B2.3 variation

| variation | 範圍 | 規則 |
|---|---|---|
| EM option4 對 option3 | 量能器剖面、取樣比例 | `G4R-PRECISION-EM` |
| FTFP_BERT_EMZ 對 **QGSP_BIC_EMZ** | 只看量能器中的作用機率與第一次作用深度；1.5 GeV 以下核子 | `G4R-BIC-RANGE`；3 GeV 以下 π、6–12 GeV 強子兩者模型相同，不得作為 variation |
| 真空對空氣 | 多重散射、剛度解析度 | — |

---

## 7. recorded 資料預算

- `check_packaging.py` 的單檔上限是 2 MiB；J14 的 `recorded/` 為 2,447,979 bytes（2.45 MB）。
- ROOT 檔不提交（二進位）。run record 只記錄路徑、檔案 sha256、`content_sha256`、各 ntuple 的列數與檔案大小；測試需要的 ROOT 檔在 live 測試中產生。
- J15 的 ROOT 檔（`crossings` 層級）壓縮前每事件最多約 4 kB：`crossings` 10 列 × 80 B、`deposits` 最多 110 列 × 28 B、`events` 約 120 B；10⁵ 事件壓縮前最多約 400 MB。
- J15 的逐事件 CSV 只有摘要欄；逐層與穿越資料在 ROOT 檔中。
- J15 只提交：縮減欄位的摘要 CSV 重播檔（比照 J14 的 `REDUCED`）、以 `simroot dump --events` 取出的縮減穿越與沉積紀錄（供離線重播 `simreco`；事件子集依預算決定）、數位化與重建的輸出、探針與 column map。
- 驗收：每檔 ≤ 2 MiB，J15 的 `recorded/` 總和 ≤ 3 MB。

---

## 8. 契約與版本

| 物件 | 位置 | 版本 |
|---|---|---|
| 對照表加入 `verification` 與 J15 的檢查；重建紀錄作為 simulated 表格輸入的標記 | `contracts/validate.py`、`contracts/dependencies.py` | C2（minor、閘控） |
| `field` 區塊、`ekin_per_nucleon_MeV`、`layered_sim.events/2`（`crossings`）、column map 的新欄位 | adapter | adapter 0.3.0 |
| `simreco` | adapter（C++，`simcore`） | adapter 0.3.0 |
| `GRADES` 與 study spec 的 grade enum 加入 `verification`；`convergence_plan.observables` 加入總沉積與後漏比例 | hep-detector | 隨 plugin 版本 |

C2 的閘控方式同 C1：`strict or _at_least(contract_version, C2)`，無 warning 分支。

---

## 9. 註冊與文件

| 項目 | 內容 |
|---|---|
| 腳本計數 | hep-detector 不新增腳本（重建在 `simreco`，介面在 adapter），`DetectorScriptCount` 維持 21，`docs/capability-matrix.md` 行 47 不變 |
| CLI 登記 | `geant4_run.py reco`、`table` 在 `tests/skills/test_cli_robustness.py` 與 adapter 測試中登記；`simcore` 的原始碼列入 `adapter.json` 的 `assets` |
| 路由表 | 不修改 `skills/hep-detector/SKILL.md`，quick load 不變；J15 與 `simreco` 的說明放在 `geant4-study-protocol.md` 與 adapter 文件 |
| journey | J15；`docs/researcher-journeys.md`、`docs/maintenance.md` 範例表；`tests/examples/test_geant4_minimal_spectrometer.py`（重播並和已提交輸出比對） |
| capability | `docs/capability-map`（在 `full-detector-simulation` 下新增項目，執行 `capability_map.py --write`）、`docs/capability-matrix.md` |
| 路由 | 新增 J15 的路由案例；`check_routing_static.py` 從 `docs/researcher-journeys.md` 讀取 journey 清單，所以 J15 一列入表就**必須**有路由案例。重跑 live 的 Geant4 案例，包括既有的繁中欠規格案例 `g4-underspec-2` |
| 描述長度 | hep-detector 的 description 目前 1,018 / 1,024 字元（`measure_entrypoints.py` 會完整量測折疊描述）；J15 的路由案例沿用描述中已有的觸發詞，不改描述 |
| 實驗名稱 | `skills/`、`contracts/` 中不出現實驗名稱；引用 `longitudinal-profile` 的參考時用引用鍵 |
| 獨立審查 | 本任務的 Markdown（protocol 變更、J15 README、本文件）以 0.22.0 的 `review.py` 審查（`--lens-model design=<最強模型>`、`--filter-model`）；紀錄只是 advisory，依 O04/O14 不取代人工的 G5 確認 |
| 共享 stanza | 文字不改 |
| 其他 | `reference_inventory.py --check`、CHANGELOG、release manifest、adapter 0.3.0、`SIM_SOURCES` 加入 `FieldSetup.*`、`SIMCORE_SOURCES` 加入 `simreco` 的原始碼 |

---

## 10. 驗收

- [ ] J15 幾何通過 overlap、物質預算、逐事件能量平衡；§4.1 與 §4.2 的核對數值由測試重算。
- [ ] MT 測試指令回報的各執行緒 field manager 指標彼此不同；探針記錄的場參數和 spec 一致。
- [ ] B2.2 的確定性場檢查在名義值下通過；delta intersection 1e-3 mm 如預期不通過。
- [ ] `field-propagation`、`field-propagation-muon`、`tof-beta`、`tof-layer-consistency`、`sampling-fraction` 執行完成；各自的 negative control 依 B2.1 被抓到，或註明沒有控制組。
- [ ] `simroot` 的往返與內容雜湊測試在 `crossings` 層級通過；同種子、不同執行緒數的兩次 MT run，`content_sha256` 相同。
- [ ] `simreco` 的擬合器單元測試以 Python 的 `tracker_resolution.py` 為參考通過；`simreco` 在 CI 的 `simcore` 工作中建置與測試。
- [ ] 隔離規則的契約測試：缺少 configuration、`embedded`、等級和契約表不符時，都被拒絕；J14 在 `--strict` 下仍通過。
- [ ] C2：`verification` 等級不計入升級；重建紀錄經 B1.4 的標記被 `dependencies.py` 接受為 simulated 表格的輸入；J15 的表格保持 `unvalidated`。
- [ ] recorded 預算、註冊項目、文件全部完成；VALIDATION 條目 GEANT4-J15。
- [ ] 獨立 agent 只依文件與工具完成「1 GV 質子在 J15 的剛度解析度」：結果紀錄通過 `validate.py --strict`、label 為 `unvalidated`、解析度落在 §4.2 表格的範圍內，過程不需要維護者協助。

---

## 11. 不做與延後

| 項目 | 決定 | 理由 / 觸發條件 |
|---|---|---|
| 量測主導區 σ(1/R) 作為 benchmark | 不做 | 改為擬合器單元測試 |
| 離子源與 Birks 可見能量（未來 J16） | 延後 | 觸發：有宇宙線核素研究需求，且 PVT 的 Birks 常數有文獻紀錄。實作時依 11.4.3：在 `GeneratePrimaries` 中以 `GetIon(Z, A)` 取得離子；在 `Construct` 設定 kB、PreInit 設定 `SetBirksActive(true)`，再以 `G4LossTableManager::Instance()->EmSaturation()` 取得 |
| GDML、field map、邊緣場 | 延後 | 觸發：研究需要真實幾何或場形 |
| `skills/hep-detector/scripts/digitize_reconstruct.py` | 不做 | 改為 C++ 的 `simreco`，介面為 `geant4_run.py reco`、`table` |

其他不做與延後的項目（含 `physics_config_comparison`、RNTuple、Python 綁定）見任務 A §11。

---

## 12. 待維護者決定的事項與殘餘風險

**待決定：**
1. C2 的「衍生模擬」標記（`extension.derived_from_simulation`，B1.4）：需要 computational-run schema 的擁有者 hep-computing 同意。
2. C2 的版本歸類：依閘控設在 x.y.0 的慣例，定為 minor。

**殘餘風險：**
1. 取樣比例的參考需要 PDG 的 μ 能損表；選用的 PVT benchmark 需要 Sternheimer 參數。兩者都要經 hep-citations 取得文獻紀錄後才能使用。
2. 量能器簇射主導 CPU 時間；後漏的收斂每點約需 5000 個簇射，事件數由 trial run 決定並記錄。
3. 場區與平面穿越會改變之後 live 重跑的 J14 `sources_sha256`；這是預期的變化，已提交的 J14 紀錄不重錄。
4. quick load 只剩 931 bytes、description 為 1,018 / 1,024 字元：本任務不得修改 `skills/hep-detector/SKILL.md` 與 description（§9）。
5. 工作量尚未估計；任務 A 完成後，依實際的 `simcore` 與 `simroot` 再估計。
6. 任務 A 的殘餘風險（探針假設 worker 與 master 設定相同、`G4RootAnalysisReader` 的讀取能力、ROOT 檔的磁碟與記憶體用量）同樣適用，見任務 A §12。

---

## 13. 建議的執行步驟

1. 開始前檢查（§0）；確認 §2 的介面都存在。
2. B1.1：場（`FieldSetup.*`、`field` 解除拒絕、步長限制、探針）與 MT 測試；接著 B2.2 的確定性場檢查（不需統計，可最早驗證）。
3. 建立 J15 的 spec/2 幾何（§4.1）；通過 overlap、物質預算、能量平衡，並以測試重算 §4.1、§4.2 的核對數值。
4. B1.2：平面穿越 scorer 與 `crossings` 層級；`simroot` 測試加入 `crossings`。
5. B1.3：`simreco` 與 `geant4_run.py reco`，先做擬合器單元測試，再接 `simroot dump` 的輸入。
6. B1.4、B1.5：`geant4_run.py table`、C2 的契約變更與測試、`GRADES` 與 enum。
7. B2.1、B2.2（量能器 cut）、B2.3：在 E2 執行 benchmark、收斂掃描與 variation。
8. §7 的 recorded 資料、§9 的註冊與文件、獨立 agent 的驗收題；§10 全部打勾，跑任務 A §10 的檢查。

---

## 附錄 A：數值

計算程式：`j15_design_estimates.py`（本資料夾；只用標準函式庫，scipy 可選；A_N 以精確有理數最小平方核對閉式）。統計的達標機率與 t 分位數見任務 A 附錄 A。

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

**事件數**（差值 se ≤ tol/4）：10 GeV 電子總沉積（容許 1 %）約 392；後漏（絕對容許 0.002）約 5000。

---

## 附錄 B：出處

- PDG Atomic and Nuclear Properties（2026-10-21 取得）：[Silicon](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/silicon_Si.html)、[Lead](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/lead_Pb.html)、[Polyvinyltoluene](https://pdg.lbl.gov/2020/AtomicNuclearProperties/HTML/polyvinyltoluene.html)
- PDG Review of Particle Physics 2024，第 34 章：式 34.5、34.12、34.16、34.34–34.36（式號依 plugin 的 VALIDATION GEANT4-STUDY）
- Geant4 v11.4.3 原始碼（tag `v11.4.3`），與場相關：`G4FieldManager.hh`、`G4ChordFinder.hh`、`G4PropagatorInField.cc`、`G4FieldBuilder`、`G4FieldParameters`、`G4LogicalVolume`、`G4ChargedGeantino.cc`、`G4EmSaturation`、`G4LossTableManager`、`G4IonTable`、`G4NistMaterialBuilder.cc`；完整清單見任務 A 附錄 C
- Geant4 Book for Application Developers，[Basic Examples](https://geant4.web.cern.ch/documentation/dev/bfad_html/ForApplicationDevelopers/Examples/BasicCodes.html)（B4、B5；開發版文件）
- hep-research：`skills/hep-detector/scripts/tracker_resolution.py`、`multiple_scattering.py`、`toy_spectrometer.py`
- 待取得：PDG 的 μ 能損表（Groom, Mokhov & Striganov）；Sternheimer, Berger & Seltzer (1984), *Atomic Data and Nuclear Data Tables* 30, 261

---

## 附錄 C：版本歷程

拆分前的完整歷程見任務 A 附錄 D。

| 版本 | 主要內容 | 審查與主要更正 |
|---|---|---|
| 探測器文件 | 單軸疊層磁譜儀 | Gluckstern 小 N 公式更正 |
| v5 | 磁場方向、場檢查網格 | 兩份審查（見任務 A 附錄 D） |
| J15 修訂（2026-10-22） | TOF1、TOF2 各改為兩層，四層同材料；TOF 解析度、上游能損、物質預算、接受度與場檢查網格重算；新增 `tof-layer-consistency` | 數值由 `j15_design_estimates.py` 重算 |
| 語言分工（2026-10-22） | 數位化與重建改為 C++ 的 `simreco`；hep-detector 不新增腳本 | 使用者決定 |
| 逐事件 ROOT 檔（2026-10-22） | J15 的穿越與逐層沉積寫入 ROOT 檔；摘要 CSV | 使用者決定 |
| 任務拆分（2026-10-22） | 自原提案拆出為任務 B，在任務 A 之後進行；`crossings` 層級定義移到本任務 | 使用者決定 |
| **整理為實作規格（2026-10-22）** | **加入任務卡、名詞表、前提介面、硬性限制、工作項編號（B1.x、B2.x）、契約與版本、建議執行步驟；章節重新編號；內容不刪減** | 使用者要求 |
