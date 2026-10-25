# hep-detector 前端電子學：重建、模擬與校準的內化（評估、已完成的工作與後續階段）

> 文件類型：評估結果與實作規格（給執行的 agent、審查者與維護者）。結構依 hep-computing 的任務格式
> （`skills/hep-computing/assets/task-template.md`），可用 `skills/hep-computing/scripts/lint_task.py` 檢查。
> 基準：hep-research `main` 的 `bc7b1c18`（plugin 0.38.0）。已完成的工作在本地分支 `worktree-frontend-reco-sim`
> （四個 commit，未推送；見 Background「已完成」）。日期：2026-10-25。
> 語言：繁體中文；檔名、指令、欄位、識別字維持英文。
> **執行環境：每個階段都在自己的 isolated git worktree 中執行**（Technical Approach §0），不修改主要 checkout 或其他
> worktree。
> 階段代號：FE0–FE5（FE = front-end）。不要與 hep-detector 設計流程的保真度 F1–F4 混淆；本文提到後者時一律寫成
> 「保真度 F4」。
> 證據標記：**[C]** Confirmed（repo、使用者或已讀來源直接支持）、**[I]** Inferred（由 [C] 推得的結論）、
> **[U]** Unresolved（未知，列在 Open Questions，不得自行補值）。
> 審查：本版已處理獨立審查 R720d9d2e80（`skills/hep-authoring/scripts/review.py`，第 1 輪）的全部發現。

## Background

#### 給執行的 agent：怎麼讀

1. 先讀本節的「現況一覽」與「已完成」，知道哪些已經做完、不要重做。
2. 讀 Technical Approach §0（isolated worktree），建立你這個階段的 worktree。
3. 再讀 Technical Approach 中你的階段（FE0–FE5），以及 Acceptance Criteria 中同代號的條目與 Validation。
4. 公式、單位與符號慣例在 Repository Context「慣例與公式」；不要從記憶補。
5. 遇到 [U] 項目就停在那一步，回報給維護者，不要猜。

#### 現況一覽

| 面向 | 評估前（main `bc7b1c18`） | 現在（分支 `worktree-frontend-reco-sim`） | 還沒做 |
|---|---|---|---|
| 解析關係（ENC、Rice、Campbell、CFD、SiPM、dead time…） | 正確；十個子命令 [C] | 不變 | — |
| 重建：取樣波形的振幅與時間 | 只有文字，文件數字無工具可重現 [C] | `optimal-filter`（含約束、時間誤差）[C] | 量測共變異輸入（FE2） |
| 重建：門檻效率與雜訊佔有率 | 固定電荷 Φ((Q−T)/σ) [C] | `hit-efficiency`（Landau／Gauss、操作窗口）[C] | 量測電荷譜輸入（FE1） |
| 模擬：digitization 與 overlay | 五條要點 [C] | 新參考檔 `readout-digitization-and-overlay.md` [C] | — |
| 模擬：波形層級 sim→reco | 無 [C] | `waveform-toy`（AR(1) 雜訊）[C] | 量測共變異雜訊（FE2） |
| 校準：電子學校準鏈 | 七個一行項目 [C] | 有順序的校準鏈、`s-curve`、`threshold-trim` [C] | 多通道批次 S-curve（FE3） |
| simreco 的 noise-digitization | 參數與電子學脫鉤 [C] | 未改 [C] | 連動（FE4，需維護者決定） |
| 完整檢查 | — | 見「已完成」的驗證結果 [C] | E2 完整重跑（FE0） |

#### 評估的結論

- 原有的 `front-end-electronics-and-signal-processing.md` 在解析關係上正確。參考檔中原本無工具可重現的數值，已用 NumPy／SciPy
  獨立重算並吻合 [C]：CR-RC、t_p 25 ns、5 個 sample 每 25 ns、從峰值前 15 ns 開始、ρ 0.6 時 template 1.117、最大 sample
  1.066、optimal filter 1.037（文件寫 1.12、1.07、1.04）；CR-RC⁴、t_p 45 ns、白雜訊、5 個 sample 從峰值前一個到後三個時的
  相位偏差 −0.041 % / −0.333 %（±2 ns）、−0.787 % / −1.538 %（±5 ns）；ρ 0.6、峰值前後各兩個 sample 時
  +0.93 % / −1.79 %（∓2 ns）、−5.81 %（+5 ns）。
- 主要問題在覆蓋範圍 [C]。唯一改變既有指引的是 C4（injection gain 與訊號 gain），屬於 `docs/maintenance.md` 所稱的
  S3（指引錯誤）；它目前放在 `feat:` commit 中，分類待維護者決定（Open Questions D-C4）。

| 代號 | 缺口 | 處理（已完成，除非標明） |
|---|---|---|
| R1 | optimal filter 無權重、無 pileup 相依的 R、無約束 | `optimal-filter` |
| R2 | 無取樣波形的時間誤差 | 振幅–時間聯合擬合 Fisher 誤差 |
| R3 | 門檻效率假設固定電荷 | `hit-efficiency`：Landau／Gauss、電荷比例、門檻分散、操作窗口；量測譜 → **FE1** |
| R4 | 雜訊佔有率只有 Rice 式 | 「連續 vs 取樣比較」與門檻分散的閉式平均 |
| R5 | ToT 反轉、頻寬、數位脈衝處理、PSD 未涵蓋 | 參考檔小節 |
| S1 | digitization 無可執行的順序 | 九步 recipe |
| S2 | 雜訊生成方法未指定 | Cholesky／頻譜合成規則；工具只有 AR(1) → **FE2** |
| S3 | 無 overlay／premixing 規則 | 五條規則（含引用 HSF 白皮書） |
| S4 | 無 digitization closure | pedestal、S-curve、振幅、電荷分享、校準 closure |
| S5 | 無波形層級 sim→reco 工具 | `waveform-toy` |
| S6 | simreco `noise-digitization` 與電子學脫鉤 | **FE4（未做，需維護者決定）** |
| C1 | 校準無順序 | 校準鏈 pedestal → 雜訊共變異 → gain → 門檻與 trim → timing → template／權重 → 物理刻度 |
| C2 | S-curve 無擬合方法與誤差 | `s-curve`：二項 ML、Fisher 誤差、deviance、設計模式；多通道 → **FE3** |
| C3 | trim 後分散未量化 | `threshold-trim` |
| C4 | injection gain 當成訊號 gain（指引錯誤，S3） | 改寫，兩個有章節定位的來源（見 References）；commit 分類待決（D-C4） |
| C5 | 無模擬中的校準 closure | 參考檔兩處 |

#### 已完成（分支 `worktree-frontend-reco-sim`，基底 `bc7b1c18`）

| commit | 內容 |
|---|---|
| `3fa93a77` feat(detector): front-end electronics for reconstruction and simulation | `optimal-filter`、`hit-efficiency`、`waveform-toy`；參考檔六個主題；新檔 `readout-digitization-and-overlay.md`；交叉連結；tool contract 13 operations；`test_frontend_waveforms.py` 26 個測試 |
| `a32df2aa` feat(detector): electronics calibration chain, S-curve fit and threshold trim | `s-curve`、`threshold-trim`；校準鏈改寫（含 C4）；校準 closure；tool contract 15 operations；共 31 個測試 |
| 之後兩個 commit（docs） | 本文件與 ATLAS LAr、HSF 白皮書的引用；依獨立審查 R720d9d2e80 的修正與 C4 的第二個來源 |

以 `git am` 套用 patch 時 hash 會不同，以 commit 訊息辨識。

驗證結果 [C]（細節在 `VALIDATION.md` 的 `FRONTEND-RECO-SIM`）：

- Landau 與 SciPy 1.18.1 相差 3.5e-13，與振盪積分式獨立實作相差 2e-6；`hit-efficiency` 與 `scipy.integrate.quad`
  （0.98796331）及 4e6 事件 MC（0.987947 ± 0.000055）一致。
- `optimal-filter` 的 Lagrange 條件與約束成立至 1e-10；聯合擬合誤差與 least-squares MC 一致（0.431 ns）。
- `waveform-toy` closure |z| < 4（σ 誤差改用四階動差後；Gaussian 公式在指數 pileup 下高估 z）。
- `s-curve` 與 SciPy Nelder-Mead 相差 < 1e-3 e；2000 次掃描 MC 的 σ_T 17.9 e、σ_σ 17.5 e（設計模式 18.3、17.3），
  pull 寬 0.98、1.02。`threshold-trim` 與 2e6 通道 MC 吻合（441.6 vs 441.8 e；18.24 % vs 18.28 %）。
- Mutation：8 個 mutant 殺掉 6 個，1 個等價，1 個事後補測試。
- 靜態檢查 `tools/run_all_checks.py --part static --no-cli`（加入校準後與本文件之後重跑）：29 項中 27 pass、2 skip
  （host CLI）；ruff 乾淨；tool contract pass；`tools/check_wiring.py --since bc7b1c18` pass。
- 完整檢查 `tools/run_all_checks.py --part all --no-cli --jobs 2`（加入校準前，VALIDATION 記錄的那一次）：31 項中
  27 pass、2 skip（host CLI）、2 fail（`unittest` 與 `ams_optional`）。單元測試 5549 個：5237 pass、294 skipped、
  18 個失敗或錯誤，全部與本工作無關：16 個是缺 SymPy 或 mpmath（該環境無法連到 PyPI）的 `ModuleNotFoundError`，
  `tests.skills.hep_authoring.test_paper_skeleton` 與 `tests.tools.test_ci_plan.RunnerRecord` 在乾淨的 main 上同樣失敗；
  `ams_optional` 也因缺 SymPy 失敗。

## Objective

FE0：已完成的前端電子學內化（重建、模擬、校準）在 E2 環境通過完整檢查（只容許 Acceptance Criteria FE0-1 列出的已知
失敗），C4 的 commit 分類由維護者決定，分支可供合併。FE0 合併到 `main` 後，FE1、FE2、FE3 三個互相獨立的工具擴充可以
平行進行；FE4、FE5 在維護者決定後才開始。每個階段結束時：程式、tool contract、測試、參考檔、CHANGELOG 與 VALIDATION
彼此一致，靜態檢查全部通過；合併前在 E2 跑一次完整檢查，只容許 FE0-1 的已知失敗。

## Scope

### In Scope

- **FE0** 合併前驗收：在 E2 完整重跑檢查，修正任何由本工作造成的失敗，補齊 VALIDATION 的環境欄；依維護者對 D-C4 的決定
  處理 C4 的 commit 分類。
- **FE1** `hit-efficiency` 接受量測或模擬的電荷譜（表格）作為訊號模型，修正 Landau 低側尾部過薄的問題。
- **FE2** `waveform-toy` 與 `optimal-filter` 接受量測的樣本雜訊共變異矩陣（含非指數相關）；`waveform-toy` 以 Cholesky
  生成雜訊，兩者都以同一矩陣計算權重與預測。
- **FE3** `s-curve` 多通道批次擬合（CSV），輸出每通道結果與門檻分散摘要；摘要指定哪一個分散送往哪一個下游工具。
- **FE4**（需維護者決定 D-FE4）simreco `noise-digitization` 的參數可由 `hit-efficiency` 推得。
- **FE5**（需維護者決定 D-FE5）縮小前端參考檔：拆分方案與其接線。

### Out of Scope

- ASIC／FPGA 設計、ADC 架構選擇、韌體撰寫（參考檔的 Scope 已排除）。
- 任何實驗的正式 digitization 程式碼（hep-computing 的交付物）；ML 波形重建或學習式 fast digitization（hep-ml）。
- 修改 `SKILL.md`、技能描述或 Resources 表（會觸發 live routing 重跑；本工作刻意不動）。
- 版本號與發佈（release manifest）；推送 `main` 或開 pull request（需維護者核准）。
- 改動 `core/` 或 `contracts/` 的版本（FE0–FE3 只新增 tool contract 的 operation 或選項）。

## Repository Context

以下路徑皆在基準 `bc7b1c18` 或分支 `worktree-frontend-reco-sim` 上確認存在 [C]（相對於 plugin 根目錄
`plugins/hep-research/`）。

#### 檔案

| 路徑 | 角色 |
|---|---|
| `skills/hep-detector/scripts/frontend_response.py` | 所有前端子命令（15 個）；標準函式庫加 `core.stats._linalg.solve` 與 `core.stats.statistical_toys.chi2_sf` |
| `contracts/tool_contracts/frontend_response.json` | 每個子命令一個 operation；選項、輸入、輸出與 `--help` 必須一致 |
| `tests/contracts/test_tool_contract.py` | `FRONTEND_OPS`：每個 operation 一組成功與一組 invalid-input 參數；`FrontendResponseContractTests` |
| `tests/skills/test_cli_robustness.py` | `NO_INPUT_FILE` 目前列有 `frontend_response.py`（「numbers on the command line」）；加入檔案輸入後要改到 `MISSING_FILE_ARGS` |
| `tests/skills/hep_detector/test_frontend_response.py` | 原有十個子命令的測試 |
| `tests/skills/hep_detector/test_frontend_waveforms.py` | 新子命令的測試（31 個），每個數值有獨立 oracle |
| `skills/hep-detector/references/front-end-electronics-and-signal-processing.md` | 前端參考檔（39,597 bytes） |
| `skills/hep-detector/references/readout-digitization-and-overlay.md` | digitization recipe、overlay 規則、closure 驗證 |
| `skills/hep-detector/references/detector-simulation.md` | Digitization 節連到上面的檔案 |
| `skills/hep-detector/references/detector-principles-bibliography.md` | 文獻；每條記錄如何核對 |
| `adapters/geant4/assets/simreco/simreco.cc` | simreco；`Strips` 結構的欄位 `pitch_y`、`pitch_z`、`sharing`、`threshold`、`efficiency`、`noise_per_plane`（設定鍵 `noise_hits_per_plane` 讀入它）與 `StripSigma` |
| `examples/design-minimal-spectrometer/` 與 `examples/design-search-j16/` | J15、J16；兩者的記錄都用到 `noise-digitization` |
| `core/stats/_linalg.py` | `solve`、`cholesky`（預設拒絕非正定矩陣，不修補） |
| `tools/run_all_checks.py`、`tools/reference_inventory.py`、`tools/measure_entrypoints.py`、`tools/check_wiring.py` | 總檢查、參考檔清單（改參考檔後必須重新產生）、SKILL.md 預算、接線檢查 |
| `docs/maintenance.md` | 檢查、sci-fix 規則與證據等級（C1–C4、D1–D3）、「Adding a topic」的接線步驟 |
| `docs/dev/geant4-architecture/geant4-program.md` | §P.10：維護者的 isolated worktree 規定（本文件沿用，差異寫在 §0） |
| `CHANGELOG.md`、`VALIDATION.md`、`docs/capability-matrix.md`、`skills/hep-detector/README.md` | 每個階段都要同步 |

#### 規則

會讓檢查失敗的：

- CLI：成功 exit 0 並印出 JSON；`ValueError` 經 `parser.error` 成為 exit 2、`error_kind` `invalid-input`；結果不是有限數時
  exit 1。每個子命令有 `--status`（預設 `unvalidated`）並原樣輸出；合成結果另有 `status_label: synthetic` [C]。
- 新增或改動子命令選項時，同時改 tool contract 與 `FRONTEND_OPS`；`python3 contracts/tool_contract.py` 必須 pass [C]。
- 子命令開始讀檔案時，把 `frontend_response.py` 從 `NO_INPUT_FILE` 移到 `MISSING_FILE_ARGS`
  （`tests/skills/test_cli_robustness.py`；`docs/maintenance.md`「Adding a topic」步驟 3）[C]。
- `skills/*/scripts` 只能 import `core` 與 `contracts`（`tools/check_layering.py`）[C]。
- 技能的參考檔與程式中，實驗名稱（例如 ATLAS、CMS）只能出現在 `<!-- example: ... -->` 與 `<!-- /example -->` 之間；
  引用某實驗的方法時照 `calibration-and-alignment.md` 的「source citation」寫法（`tools/check_layering.py`）[C]。
- 改了任何參考檔就重跑 `python3 tools/reference_inventory.py`，否則 `reference_inventory` 檢查失敗 [C]。
- 新的參考檔必須在 Resources 表或入口參考檔路由部分的一步內，或經 `tools/wiring_known_gaps.json` 登記的 hub 兩步內
  （`tools/check_wiring.py`，R1）[C]。
- hep-detector 的 `quick_load_bytes`（SKILL.md 加入口參考檔）不得超過 25,600 bytes（`tools/measure_entrypoints.py`；目前
  24,669）[C]。

只會警告、但要遵守的：

- `skills/hep-detector/references/detector-principles-summary.md` 的路由部分超過 4096 bytes 時，`reference_inventory` 會發出
  警告（不改變 exit code）。目前 4081 bytes，因此新參考檔不放進該索引 [C]。
- 參考檔超過 24 KB 時 `reference_inventory` 警告；前端參考檔已經超過 [C]。

commit 慣例：改變既有數值、判定或方法指引的修正用 `sci-fix:`，附回歸測試，並依 S1–S3 的證據規定（`docs/maintenance.md`）；
純搬移用 `move:`；新功能用 `feat:`（repo 歷史中的慣例，`docs/maintenance.md` 沒有定義它）[C]。commit 結尾附該 session 規定的
trailer [I]。

#### 慣例與公式（工具已實作，擴充時不得改變其意義）

- 脈衝：峰值歸一的 CR-(RC)^n，`g(t) = (t/τ)^n e^(−t/τ) / (n^n e^(−n))`，`t_p = nτ`。
- 取樣：第 i 個 sample 在 `t_p + first_offset + i·period`；`first_offset` 為負表示在峰值前。
- 波形工具的單位：振幅與雜訊以「每個 sample 的電子雜訊 σ」為單位，脈衝峰值為 1。
- 雜訊共變異：`R_ij = ρ^|i−j| + ν⟨a²⟩ ∫ g(t) g(t + t_i − t_j) dt`（Campbell，ν 以 Hz、時間以 ns，程式中乘 1e-9）。
- 約束 OF：`w = R⁻¹C (CᵀR⁻¹C)⁻¹ e₁`，`C = [g, c₁, …]`；phase 約束 `c = g′`，baseline 約束 `c = (1,…,1)`；
  變異 `((CᵀR⁻¹C)⁻¹)₁₁`。
- 相位誤差符號：`dt > 0` 表示脈衝比假設早開始 dt，sample 落在脈衝上較晚的位置（`g(t_i + dt)`）。
- 基線增益：每個 sample 上的常數偏移 b 讓振幅偏 `b·Σw`。
- Landau：Kölbig 的 φ(λ)，MPV 在 `λ = −0.22278298`；等於穩定分布 S1(α=1, β=1, scale π/2, loc 0)，即
  `λ = (π/2) z + ln(π/2)`，z 為 `scipy.stats.landau`；電荷 `Q = f·[MPV + ξ(λ − λ_mp)]`。
- 效率：`1 − E[F_Q(T + s u)]`，`u ~ N(0,1)`，`s² = σ_n² + σ_thr²`。
- 雜訊佔有率（對門檻分散平均，閉式）：每個 sample `Q(T/s)`；每個 window 的 Rice 次數
  `ν₀ (σ_n/s) exp(−T²/2s²) · W`；上限為兩者之和。
- S-curve：`hits ~ Bin(N, Φ((Q − T)/σ))`，二項 ML，Fisher 誤差，deviance 近似 χ²(n−2)。
- Trim：範圍半寬 `h = (2^b − 1)D/2`，邊界 `h + D/2`；範圍內殘差 rms `D/√12`，範圍外殘差 `|x| − h`（閉式）。
- 門檻分散的流向：`threshold-trim --spread` 要 **trim 前**的分散；`hit-efficiency --threshold-dispersion` 要**運作時（trim
  後）**的分散，也就是 `threshold-trim` 的 `residual_dispersion`，或 trim 後重新掃描所得的分散。兩者只在沒有 trim 的讀出
  上相同。

## Technical Approach

#### §0 isolated worktree（每個階段都適用）

沿用 `docs/dev/geant4-architecture/geant4-program.md` §P.10 的規定 [C]，只有第 2 項的例外寫明如下：

1. **一個階段、一個 worktree、一個分支**：位置 `.claude/worktrees/frontend-<階段>`（小寫，例如
   `.claude/worktrees/frontend-fe1`），分支 `worktree-frontend-<階段>`。
2. **基底**：
   - FE0：已完成工作的分支 `worktree-frontend-reco-sim`。遠端目前只有 `main`（`git ls-remote origin` [C]），所以在 E2
     從 `origin/main` 建 worktree，再以 `git am` 依序套用 patch `0001`–`0004`（隨本文件一起交付；已在乾淨的 worktree 上
     確認可無衝突套用，結果與分支的檔案樹相同 [C]）。
   - FE1–FE5：**FE0 合併後**最新的 `origin/main`，與 §P.10.2「已包含全部前提階段的最新 main」一致。FE0 合併前不要開始
     FE1–FE5；若維護者核准提前開始，基底改為 FE0 的分支，合併前必須 rebase 到新的 `main` 並重跑全部檢查（這是對
     §P.10.2 的例外，要在該階段 VALIDATION 條目中寫明）。
3. **建立**：
   - Claude Code：以 `EnterWorktree`（name `frontend-<階段>`）建立並進入；把實作委派給 subagent 時，Agent 工具使用
     `isolation: "worktree"`。
   - 其他環境，FE0：
     ```bash
     git fetch origin
     git worktree add .claude/worktrees/frontend-fe0 -b worktree-frontend-fe0 origin/main
     git -C .claude/worktrees/frontend-fe0 am /path/to/000[1-4]-*.patch
     ```
   - 其他環境，FE1–FE5（FE0 合併後）：
     ```bash
     git fetch origin
     git worktree add .claude/worktrees/frontend-fe1 -b worktree-frontend-fe1 origin/main
     ```
4. **開始前確認**（結果寫進該階段 VALIDATION 條目的環境欄）：`git rev-parse --show-toplevel` 是該 worktree、
   `git branch --show-current` 是該階段分支、`git status` 乾淨；FE1–FE5 另需 FE0 的合併 commit 滿足
   `git merge-base --is-ancestor <commit> HEAD`。
5. **在 worktree 中的規則**（§P.10.3）：
   - 所有編輯、測試、MC 都在該 worktree；不 `cd` 到主要 checkout 或其他 worktree。
   - **不用裸的 `git stash`**（所有 worktree 共用），需要暫存就做 WIP commit。
   - 暫存輸出放在不提交的目錄（例如 `work/`）。
   - 只提交到該階段分支，並推送到同名的遠端分支；沒有推送權限時只在本地提交並回報。未經維護者核准不推送 `main`、不開
     pull request。
6. **結束**：合併後 `git worktree remove .claude/worktrees/frontend-<階段>` 並刪除本地分支；放棄時同樣移除，不在主要
   checkout 做任何清理。
7. **平行**：FE1、FE2、FE3 改的都是 `frontend_response.py`、同一份 contract、同一個測試檔與 `test_cli_robustness.py`：
   可以平行，但後合併者必須 rebase 並重跑全部檢查；同一階段不由兩個 agent 同時實作 [I]。

#### §FE0 合併前驗收

1. 在 E2（Python、NumPy、SciPy、SymPy、mpmath）建立 worktree 並確認（§0）。
2. 執行 `python3 tools/run_all_checks.py --out work/checks`（含 host CLI；沒有 CLI 時加 `--no-cli` 並在紀錄中寫明）。
3. 每個失敗先在乾淨的 `origin/main` 上重跑同一個測試 id。只有 FE0-1 列出的測試 id，而且例外類型與訊息相同時，才算已知
   失敗；其他失敗一律視為本工作造成，修正並補回歸測試。
4. 依維護者對 D-C4 的決定處理 C4：保留在 `feat:` 中並在 CHANGELOG 註明，或把 C4 那段改寫拆成獨立的 `sci-fix:` commit，
   附 S3 證據（References 的兩個有章節定位的來源）。
5. 在 `VALIDATION.md` 的 `FRONTEND-RECO-SIM` 加入 E2 的結果與環境欄（Python、NumPy、SciPy、SymPy、mpmath 的版本與 commit）。

#### §FE1 `hit-efficiency` 的表格訊號模型

1. 新增 `--signal-model table` 與 `--spectrum FILE`：CSV，標題列 `charge,density` 或 `charge,count`，電荷嚴格遞增。
2. 由表格建立單調 CDF（density：梯形積分後歸一化；count：視為 bin 中心並以相鄰中點為邊界），兩點間線性內插；表格範圍外
   以 0 與 1 延伸，並在 `validity` 標示超出範圍的門檻。
3. `--signal-fraction` 對表格同樣縮放電荷軸；`--threshold-dispersion` 與佔有率計算不變。
4. 讀檔錯誤一律是 invalid-input（exit 2，JSON），不是 traceback：檔案不存在或無法讀（`OSError`）、空檔或只有標題、欄位名稱
   或欄數不對、非數字、NaN 或 inf、電荷非遞增、負的 density 或 count、總和為零。`OSError`、`csv.Error` 與
   `UnicodeDecodeError` 要在讀檔函式中轉成 `ValueError`。輸入檔中的非有限數屬於 invalid-input，與「結果不是有限數時 exit 1」
   的規則無關。
5. 把 `frontend_response.py` 移到 `MISSING_FILE_ARGS`（規則一節），並給 `hit-efficiency --spectrum` 一組不存在的路徑參數。
6. 參考檔「Efficiency with a fluctuating signal」一段加一句：低於 1 % 的低側尾部用 `table` 模型與量測譜。

#### §FE2 量測雜訊共變異（`waveform-toy` 與 `optimal-filter`）

1. 新增 `--noise-covariance FILE`：JSON `{"covariance": [[...]]}`，維度等於 `--samples`，單位為每個 sample 的雜訊 σ²；與
   `--rho` 互斥。兩個子命令共用一個讀檔函式。
2. 用 `core.stats._linalg.cholesky` 分解；非正定、非對稱、維度不符、非有限數都是 invalid-input，矩陣不被修補。
   `waveform-toy` 每個事件以 `L·z` 生成雜訊。
3. 權重與預測使用同一個矩陣，再加上 Campbell pileup 項。
4. 輸出增加 `noise_model`（`ar1` 或 `measured`）與 `noise_covariance_sha256`。雜湊的輸入定義為解析後矩陣的正規 JSON：
   `json.dumps(matrix, separators=(",", ":"))` 的 UTF-8 bytes，其中 `matrix` 是 list of lists of float。
5. 讀檔錯誤的處理與 `MISSING_FILE_ARGS` 同 §FE1 第 4、5 步。

#### §FE3 `s-curve` 多通道批次

1. 新增 `--scan-file FILE`：CSV 欄位 `channel,charge,injections,hits`；與 `--charges`、`--hits`、`--design-*` 互斥；讀檔錯誤同
   §FE1 第 4、5 步。
2. 每個通道呼叫現有 `scurve_fit`；擬合拋出錯誤的通道（未跨過 50 %、矩陣奇異）列在 `failed_channels` 並附原因，不中斷整批。
3. **納入規則**：摘要統計只用「已收斂、過渡區（5 %–95 %）至少 2 點、p ≥ 1e-3」的通道。其他通道列在
   `excluded_channels` 並附原因；輸出 `n_included`、`n_excluded`、`n_failed`。排除與失敗的通道合計超過 5 % 時，在
   `validity` 警告分散可能有偏（被排除的通道往往門檻最極端）。
4. **摘要**：門檻平均；樣本標準差 `threshold_sd`；穩健分散 `threshold_mad_sigma = 1.4826 × MAD`；去除擬合誤差的分散
   `threshold_dispersion_corrected = sqrt(max(0, threshold_sd² − mean(σ_T²)))`，根號內 ≤ 0 時回報 0，並在 `validity` 寫
   「分散未高於擬合誤差」；noise 的中位數；p < 1e-3 的通道數。結果永遠是有限數，不會因此 exit 1。
5. **流向**：送往下游的是 `threshold_dispersion_corrected`。掃描在 trim 前做的，送往 `threshold-trim --spread`；掃描在 trim
   後做的，送往 `hit-efficiency --threshold-dispersion`（見「慣例與公式」最後一項）。在輸出的 `note` 寫明這一點。

#### §FE4 simreco 連動（需維護者決定 D-FE4 後才開始）

1. 目標：`noise-digitization` 的 `efficiency` 與 `noise_hits_per_plane` 可以由 `hit-efficiency` 的結果填入；新增以 ENC 為單位
   的門檻選項，與現行的電荷比例門檻並存。
2. 分類取決於預設值是否改變 [I]：
   - 只新增選項、預設不變：現有輸出與 J15、J16 的記錄不變，用 `feat:`，並加測試確認預設輸出逐位元不變。
   - 改變預設或既有數值：用 `sci-fix:`，依 `docs/maintenance.md` 的證據等級與 Geant4 規格的閘門處理，重新記錄 J15
     （`examples/design-minimal-spectrometer/`）與 J16（`examples/design-search-j16/`），兩者都會經過保真度 F4 的
     qualification 路徑。

#### §FE5 縮小前端參考檔（需維護者決定 D-FE5 後才開始）

1. 事實 [C]：前端參考檔 39,597 bytes；24 KB 的警告線是 24,576 bytes。只搬出 `## Photosensor readout` 與
   `## LAr TPC signal processing` 只減少 2,779 bytes（剩約 36.8 KB），達不到警告線；要低於 24 KB，需要搬出約 15 KB，例如
   取樣波形估計器與校準兩大節。
2. 不論搬多少，新頁都必須接線：從 Resources 表、入口參考檔路由部分，或 `tools/wiring_known_gaps.json` 登記的 hub 連到它
   （`tools/check_wiring.py --since <基底>` pass）。本工作不改 SKILL.md 與摘要索引，所以可行的做法是把前端參考檔登記為
   hub（它本身在 Resources 表的一步內），由它連到新頁。
3. 用 `move:` commit，不改內容；舊位置留標題為「... (moved)」的指引一個 minor 版本，並在 `pointers` 記錄移除它的版本
   （`docs/maintenance.md`「Adding a topic」）。

## Deliverables

- FE0：E2 的完整檢查紀錄（`work/checks/check-run-*.json` 的摘要寫入 `VALIDATION.md` 的 `FRONTEND-RECO-SIM`）；必要的修正
  commit；依 D-C4 的 C4 處理。
- FE1：`frontend_response.py` 的 `table` 訊號模型；contract、`FRONTEND_OPS`、`MISSING_FILE_ARGS` 更新；測試；參考檔一句；
  CHANGELOG、VALIDATION 條目。
- FE2：`--noise-covariance`（`waveform-toy`、`optimal-filter`）；contract、測試、CHANGELOG、VALIDATION。
- FE3：`--scan-file` 批次模式；contract、測試、CHANGELOG、VALIDATION。
- FE4：依 D-FE4 的決定交付（目前無）。
- FE5：依 D-FE5 的決定交付；新參考檔、接線（hub 登記）、moved 指引、重新產生的 reference inventory、README 的參考檔數目。
- 每個階段：一個分支、一個或數個 commit，附 trailer；不推送 `main`。

## Acceptance Criteria

- **FE0-1** E2 的 `tools/run_all_checks.py` 中，除 host CLI 外每一項都 pass，或其失敗只來自以下已知清單，且在乾淨的
  `origin/main` 上以相同測試 id、相同例外類型與訊息失敗：
  - `tests.skills.hep_authoring.test_paper_skeleton.PaperSkeleton.test_compiled_bibliography_shows_an_eprint`；
  - `tests.tools.test_ci_plan.RunnerRecord.test_check_ams_optional_runs_only_the_planned_modules`；
  - 在 E2 不應再出現 `ModuleNotFoundError: No module named 'sympy'` 或 `'mpmath'`；若出現，表示 E2 不完整，先修環境；
  - `ams_optional` 只有在其失敗原因同上時才算已知。
- **FE0-2** `VALIDATION.md` 的 `FRONTEND-RECO-SIM` 有 E2 環境欄（Python、NumPy、SciPy、SymPy、mpmath 的版本與 commit）。
- **FE0-3** C4 的處理與維護者對 D-C4 的決定一致，並寫在 CHANGELOG。
- **FE1-1** 由 `landau` 模型（MPV 23000 e、ξ 1500 e、σ 1000 e）以電荷步長 ≤ 150 e（0.1 ξ）取樣的 density 表格，在門檻
  16000–24000 e（每 1000 e；Landau inefficiency 1.8e-6 至 0.36）上，`table` 與 `landau` 的 inefficiency 相對差 < 1e-3。
- **FE1-2** 負對照：把同一表格的電荷軸平移 +300 e（0.2 ξ），FE1-1 的檢查必須失敗；在這些門檻上相對差至少 9 %
  （`hit-efficiency` 以 MPV 23300 e 計算 [C]）。
- **FE1-3** Gaussian 訊號（平均 20000 e、σ 1000 e）以步長 ≤ 50 e（0.05 σ）的 density 表格，在 17000–23000 e 的門檻上，
  效率與閉式 Φ 相差 < 1e-4。
- **FE1-4** §FE1 第 4 步列出的每一種壞檔案各得 exit 2 與 `error_kind: invalid-input`，stderr 無 traceback；
  `tests/skills/test_cli_robustness.py` 中 `frontend_response.py` 位於 `MISSING_FILE_ARGS`。
- **FE2-1** 給定 ρ^|i−j| 矩陣（ρ 0.6，7 個 sample）時，`--noise-covariance` 的 `predicted_sigma` 與 `--rho 0.6` 相同至
  1e-12，且 `waveform-toy` 的 closure |z| < 4。
- **FE2-2** 一個非指數相關的正定矩陣（ρ^|i−j| 加 0.3 的常數 common-mode 項）下，20 000 事件的樣本共變異每個元素與輸入相差
  在 4 個標準誤以內，closure |z| < 4。
- **FE2-3** 非正定、非對稱、維度不符或含非有限數的矩陣得 invalid-input；矩陣不被修補。
- **FE2-4** `noise_model` 在 `--rho` 時為 `ar1`、在 `--noise-covariance` 時為 `measured`；`noise_covariance_sha256` 等於以
  §FE2 第 4 步重新計算的值，改動矩陣任一元素後雜湊改變。
- **FE3-1** 每個通道以 `scurve_fit` 逐一計算的結果與批次輸出完全相同。
- **FE3-2** 合成 200 通道（門檻 N(3700, 150²) e、σ 300 e、8 個電荷點每 200 e、100 次注入）時，
  `threshold_dispersion_corrected` 與 150 e 相差在其 MC 標準誤的 3 倍內（MC 標準誤由至少 50 批估計）。
- **FE3-3** 真實分散 0 e 與 5 e 的合成批次：整批 exit 0，`threshold_dispersion_corrected` 為有限數且 ≥ 0；根號內 ≤ 0 的批次
  在 `validity` 有「分散未高於擬合誤差」。
- **FE3-4** 含一個不跨 50 % 的通道與一個 p < 1e-3 的通道時，整批完成；前者在 `failed_channels`，後者在
  `excluded_channels`，兩者都不進入摘要統計。
- **FE3-5** `threshold_mad_sigma` 對 Gaussian 合成門檻的期望值與真實 σ 相差在 MC 標準誤的 3 倍內；摘要的 noise 中位數與
  p < 1e-3 通道數等於逐通道結果重算的值。
- **全部階段** `python3 contracts/tool_contract.py` pass；`ruff check` 對改動的 Python 檔無錯；`reference_inventory --check`
  pass；`tools/check_wiring.py --since <基底>` pass；`tools/measure_entrypoints.py` 的 hep-detector `quick_load_bytes`
  ≤ 25,600。

## Validation

在該階段 worktree 的 `plugins/hep-research` 目錄下執行。前六行每個階段都跑；最後一行是 FE0 與每個階段合併前在 E2 的完整
檢查，判定依 FE0-1：

```bash
python3 -m unittest tests.skills.hep_detector.test_frontend_waveforms \
  tests.skills.hep_detector.test_frontend_response tests.contracts.test_tool_contract \
  tests.skills.test_cli_contract tests.skills.test_cli_robustness tests.skills.test_reference_links
python3 contracts/tool_contract.py contracts/tool_contracts/frontend_response.json
python3 tools/reference_inventory.py --check
python3 tools/check_wiring.py --since origin/main
ruff check skills/hep-detector/scripts/frontend_response.py tests/skills/hep_detector/test_frontend_waveforms.py
python3 tools/run_all_checks.py --part static --no-cli --out work/checks
python3 tools/run_all_checks.py --out work/checks
```

- 每個新數值至少一個獨立 oracle（解析、閉式、獨立實作或 MC），寫在測試檔頂端的 oracle 清單；比照
  `test_frontend_waveforms.py` 的做法。每個驗收條件至少一個測試；有容差的條件同時有負對照（如 FE1-2）。
- 對改動的函式做 revert mutant：把修正還原時，至少一個新測試必須失敗（`docs/maintenance.md` 的 D 等級）。
- 已知與本工作無關的失敗只依 FE0-1 判定。

## Open Questions

- **[U] D-FE0 合併路徑**：FE0 的分支由誰推送、以單一 PR 還是分 commit 合併？這次算哪個版本號？（Requires Confirmation，
  維護者）
- **[U] D-C4 C4 的 commit 分類**：C4 改寫了既有的方法指引（S3），目前在 `feat:` commit `a32df2aa` 中。保留並在 CHANGELOG
  註明，還是拆成獨立的 `sci-fix:` commit 並附 S3 證據？（Requires Confirmation，維護者）
- **[U] D-FE4 simreco 連動**：要不要做？只新增選項（`feat:`，記錄不變），還是改變預設（`sci-fix:`，重新記錄 J15 與
  J16）？（Requires Confirmation，維護者）
- **[U] D-FE5 參考檔縮小**：要不要做？若做，搬出哪些小節（只搬 photosensor 與 LAr TPC 達不到 24 KB），以及是否把前端參考檔
  登記為 hub？（Requires Confirmation，維護者）
- **[U] FE1 的量測電荷譜**：是否有可公開放進 `assets/` 的薄矽電荷譜範例？沒有時只用合成表格做測試。（Open Question）
- **[U] E2 環境**：目前 E2 的 Python、NumPy、SciPy、SymPy、mpmath 版本以維護者紀錄為準。（Requires Confirmation）

## References

- 任務格式：`skills/hep-computing/assets/task-template.md`、`skills/hep-computing/references/task-authoring-guide.md`、
  `skills/hep-computing/references/task-quality-checklist.md`、`skills/hep-computing/references/acceptance-criteria.md`。
- 維護規則：`docs/maintenance.md`；worktree 規定：`docs/dev/geant4-architecture/geant4-program.md` §P.10。
- 內容：`skills/hep-detector/references/front-end-electronics-and-signal-processing.md`、
  `skills/hep-detector/references/readout-digitization-and-overlay.md`、`skills/hep-detector/references/detector-simulation.md`、
  `skills/hep-detector/references/calibration-and-alignment.md`。
- 證據：`VALIDATION.md` 的 `FRONTEND-RECO-SIM`；`CHANGELOG.md` 的 Unreleased；獨立審查 R720d9d2e80 的報告。
- 外部來源（2026-10-25）：
  - W. E. Cleland, E. G. Stern, Nucl. Instrum. Methods A338 (1994) 467（optimal filtering 與 pileup 雜訊）。
  - M. Aharrouche et al., arXiv:0709.1094, sec. 2.4（ATLAS LAr：以 g、g′ 與 pedestal-run 自相關的 Lagrange 乘數求 OF 係數）。
  - N. Nikiforou for ATLAS, arXiv:1306.6756, sec. II-C（cell energy 公式中的 M_phys/M_cali）。
  - G. Aad et al., arXiv:0912.2642, sec. 3.1.2（`1/(M_phys/M_cali)` 為相同輸入電流下校準脈衝與游離脈衝的響應比；經 PDF 的
    搜尋索引找到該段，未重讀全文）。C4 的第二個有章節定位的來源。
  - J. Apostolakis et al., arXiv:1803.04165, sec. 5（HSF 模擬白皮書：overlay 需要未 zero-suppress 的樣本，訊號相加有非線性）。
  - J. P. Nolan, Stochastic Models 13 (1997) 759, DOI 10.1080/15326349708807450（穩定分布的積分式）。
  - V. T. Jordanov, G. F. Knoll, Nucl. Instrum. Methods A345 (1994) 337（數位梯形整形）。
