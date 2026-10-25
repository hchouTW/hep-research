# hep-detector 前端電子學：重建、模擬與校準的內化（評估、已完成的工作與後續階段）

> 文件類型：評估結果與實作規格（給執行的 agent、審查者與維護者）。結構依 hep-computing 的任務格式
> （`skills/hep-computing/assets/task-template.md`），可用 `skills/hep-computing/scripts/lint_task.py` 檢查。
> 基準：hep-research `main` 的 `bc7b1c18`（plugin 0.38.0）。已完成的工作在本地分支 `worktree-frontend-reco-sim`
> （三個 commit，未推送；見 Background「已完成」）。日期：2026-10-25。
> 語言：繁體中文；檔名、指令、欄位、識別字維持英文。
> **執行環境：每個階段都在自己的 isolated git worktree 中執行**（Technical Approach §0），不修改主要 checkout 或其他
> worktree。
> 證據標記：**[C]** Confirmed（repo、使用者或已讀來源直接支持）、**[I]** Inferred（由 [C] 推得的結論）、
> **[U]** Unresolved（未知，列在 Open Questions，不得自行補值）。

## Background

#### 給執行的 agent：怎麼讀

1. 先讀本節的「現況一覽」與「已完成」，知道哪些已經做完、不要重做。
2. 讀 Technical Approach §0（isolated worktree），建立你這個階段的 worktree。
3. 再讀 Technical Approach 中你的階段（F0–F5），以及 Acceptance Criteria、Validation 中同代號的條目。
4. 公式、單位與符號慣例在 Repository Context「慣例與公式」；不要從記憶補。
5. 遇到 [U] 項目就停在那一步，回報給維護者，不要猜。

#### 現況一覽

| 面向 | 評估前（main `bc7b1c18`） | 現在（分支 `worktree-frontend-reco-sim`） | 還沒做 |
|---|---|---|---|
| 解析關係（ENC、Rice、Campbell、CFD、SiPM、dead time…） | 正確；十個子命令 [C] | 不變 | — |
| 重建：取樣波形的振幅與時間 | 只有文字，文件數字無工具可重現 [C] | `optimal-filter`（含約束、時間誤差）[C] | — |
| 重建：門檻效率與雜訊佔有率 | 固定電荷 Φ((Q−T)/σ) [C] | `hit-efficiency`（Landau／Gauss、操作窗口）[C] | 實測電荷譜輸入（F1） |
| 模擬：digitization 與 overlay | 五條要點 [C] | 新參考檔 `readout-digitization-and-overlay.md` [C] | — |
| 模擬：波形層級 sim→reco | 無 [C] | `waveform-toy`（AR(1) 雜訊）[C] | 實測共變異雜訊（F2） |
| 校準：電子學校準鏈 | 七個一行項目 [C] | 有順序的校準鏈、`s-curve`、`threshold-trim` [C] | 多通道批次 S-curve（F3） |
| simreco 的 noise-digitization | 參數與電子學脫鉤 [C] | 未改 [C] | 連動（F4，需維護者決定） |
| 完整檢查 | — | 靜態 27/27；單元測試見下 [C] | E2 完整重跑（F0） |

#### 評估的結論

- 原有的 `front-end-electronics-and-signal-processing.md` 在解析關係上正確。參考檔中原本無工具可重現的數值，已用 NumPy／SciPy
  獨立重算並吻合 [C]：CR-RC、t_p 25 ns、5 個 sample、ρ 0.6 時 template 1.117、最大 sample 1.066、optimal filter 1.037
  （文件寫 1.12、1.07、1.04）；CR-RC⁴ 白雜訊的相位偏差 −0.041 % / −0.333 %（±2 ns）、−0.787 % / −1.538 %（±5 ns）；
  ρ 0.6 時 +0.93 % / −1.79 %（∓2 ns）、−5.81 %（+5 ns）。
- 問題在覆蓋範圍，不在正確性 [C]：

| 代號 | 缺口 | 處理（已完成，除非標明） |
|---|---|---|
| R1 | optimal filter 無權重、無 pileup 相依的 R、無約束 | `optimal-filter` |
| R2 | 無取樣波形的時間誤差 | 振幅–時間聯合擬合 Fisher 誤差 |
| R3 | 門檻效率假設固定電荷 | `hit-efficiency`：Landau／Gauss、電荷比例、門檻分散、操作窗口 |
| R4 | 雜訊佔有率只有 Rice 式 | 「連續 vs 取樣比較」與門檻分散的閉式平均 |
| R5 | ToT 反轉、頻寬、數位脈衝處理、PSD 未涵蓋 | 參考檔小節 |
| S1 | digitization 無可執行的順序 | 九步 recipe |
| S2 | 雜訊生成方法未指定 | Cholesky／頻譜合成規則；工具只有 AR(1) → **F2** |
| S3 | 無 overlay／premixing 規則 | 五條規則（含引用 HSF 白皮書） |
| S4 | 無 digitization closure | pedestal、S-curve、振幅、電荷分享、校準 closure |
| S5 | 無波形層級 sim→reco 工具 | `waveform-toy` |
| S6 | simreco `noise-digitization` 與電子學脫鉤 | **F4（未做，需維護者決定）** |
| C1 | 校準無順序 | 校準鏈 pedestal → 雜訊共變異 → gain → 門檻與 trim → timing → template／權重 → 物理刻度 |
| C2 | S-curve 無擬合方法與誤差 | `s-curve`：二項 ML、Fisher 誤差、deviance、設計模式；多通道 → **F3** |
| C3 | trim 後分散未量化 | `threshold-trim` |
| C4 | injection gain 當成訊號 gain | 改寫；引用 ATLAS LAr 的 M_phys/M_cali |
| C5 | 無模擬中的校準 closure | 參考檔兩處 |

#### 已完成（分支 `worktree-frontend-reco-sim`，基底 `bc7b1c18`）

| commit | 內容 |
|---|---|
| `3fa93a77` feat(detector): front-end electronics for reconstruction and simulation | `optimal-filter`、`hit-efficiency`、`waveform-toy`；參考檔六個主題；新檔 `readout-digitization-and-overlay.md`；交叉連結；tool contract 13 operations；`test_frontend_waveforms.py` 26 個測試 |
| `a32df2aa` feat(detector): electronics calibration chain, S-curve fit and threshold trim | `s-curve`、`threshold-trim`；校準鏈改寫；校準 closure；tool contract 15 operations；共 31 個測試 |
| 第三個 commit（本文件與引用） | 本文件；ATLAS LAr 與 HSF 白皮書的引用與文獻條目 |

驗證結果 [C]（細節在 `VALIDATION.md` 的 `FRONTEND-RECO-SIM`）：

- Landau 與 SciPy 1.18.1 相差 3.5e-13，與振盪積分式獨立實作相差 2e-6；`hit-efficiency` 與 `scipy.integrate.quad`
  （0.98796331）及 4e6 事件 MC（0.987947 ± 0.000055）一致。
- `optimal-filter` 的 Lagrange 條件與約束成立至 1e-10；聯合擬合誤差與 least-squares MC 一致（0.431 ns）。
- `waveform-toy` closure |z| < 4（σ 誤差改用四階動差後；Gaussian 公式在指數 pileup 下高估 z）。
- `s-curve` 與 SciPy Nelder-Mead 相差 < 1e-3 e；2000 次掃描 MC 的 σ_T 17.9 e、σ_σ 17.5 e（設計模式 18.3、17.3），
  pull 寬 0.98、1.02。`threshold-trim` 與 2e6 通道 MC 吻合（441.6 vs 441.8 e；18.24 % vs 18.28 %）。
- Mutation：8 個 mutant 殺掉 6 個，1 個等價，1 個事後補測試。
- `tools/run_all_checks.py --part static --no-cli`：27/27 pass；ruff 乾淨；tool contract pass。
- 完整單元測試（加入校準前）：5549 個中 5237 pass，18 個失敗或錯誤，全部與本工作無關：16 個缺 SymPy／mpmath
  （該環境無法連到 PyPI），`test_paper_skeleton` 與 `test_ci_plan.RunnerRecord` 在乾淨的 main 上同樣失敗。

## Objective

已完成的前端電子學內化（重建、模擬、校準）在 E2 環境通過完整檢查並可供合併（F0）；之後依序完成 F1–F3 三個獨立的
工具擴充，F4、F5 在維護者決定後執行。每個階段結束時：程式、tool contract、測試、參考檔、CHANGELOG 與 VALIDATION
彼此一致，且 `tools/run_all_checks.py` 除了 host CLI 檢查外全部通過。

## Scope

### In Scope

- **F0** 合併前驗收：在 E2（有 SymPy、mpmath）完整重跑檢查，修正任何由本工作造成的失敗，補齊 VALIDATION 的環境欄。
- **F1** `hit-efficiency` 接受量測或模擬的電荷譜（表格 CDF）作為訊號模型，修正 Landau 低側尾部過薄的問題。
- **F2** `waveform-toy` 接受量測的樣本雜訊共變異矩陣（含非指數相關），以 Cholesky 生成雜訊，並以同一矩陣計算權重與預測。
- **F3** `s-curve` 多通道批次擬合（CSV），輸出每通道結果與門檻分散摘要，可直接接到 `threshold-trim` 與 `hit-efficiency`。
- **F4**（需維護者決定，見 Open Questions）simreco `noise-digitization` 的參數可由 `hit-efficiency` 推得。
- **F5**（可選）把前端參考檔的 photosensor 與 LAr TPC 小節拆成獨立參考檔，使其低於 24 KB 的警告線。

### Out of Scope

- ASIC／FPGA 設計、ADC 架構選擇、韌體撰寫（參考檔的 Scope 已排除）。
- 任何實驗的正式 digitization 程式碼（hep-computing 的交付物）；ML 波形重建或學習式 fast digitization（hep-ml）。
- 修改 `SKILL.md`、技能描述或 Resources 表（會觸發 live routing 重跑；本工作刻意不動）。
- 版本號與發佈（release manifest）；推送 `main` 或開 pull request（需維護者核准）。
- 改動 `core/` 或 `contracts/` 的版本（F0–F3 只新增 tool contract 的 operation 或選項）。

## Repository Context

以下路徑皆在基準 `bc7b1c18` 或分支 `worktree-frontend-reco-sim` 上確認存在 [C]（相對於 plugin 根目錄
`plugins/hep-research/`）。

#### 檔案

| 路徑 | 角色 |
|---|---|
| `skills/hep-detector/scripts/frontend_response.py` | 所有前端子命令（15 個）；標準函式庫加 `core.stats._linalg.solve` 與 `core.stats.statistical_toys.chi2_sf` |
| `contracts/tool_contracts/frontend_response.json` | 每個子命令一個 operation；選項、輸入、輸出與 `--help` 必須一致 |
| `tests/contracts/test_tool_contract.py` | `FRONTEND_OPS`：每個 operation 一組成功與一組 invalid-input 參數；`FrontendResponseContractTests` |
| `tests/skills/hep_detector/test_frontend_response.py` | 原有十個子命令的測試 |
| `tests/skills/hep_detector/test_frontend_waveforms.py` | 新子命令的測試（31 個），每個數值有獨立 oracle |
| `skills/hep-detector/references/front-end-electronics-and-signal-processing.md` | 前端參考檔（約 39 KB） |
| `skills/hep-detector/references/readout-digitization-and-overlay.md` | digitization recipe、overlay 規則、closure 驗證 |
| `skills/hep-detector/references/detector-simulation.md` | Digitization 節連到上面的檔案 |
| `skills/hep-detector/references/detector-principles-bibliography.md` | 文獻；每條記錄如何核對 |
| `adapters/geant4/assets/simreco/simreco.cc` | simreco；`noise-digitization` 的 `Strips`（pitch、sharing、threshold、efficiency、noise_hits_per_plane）與 `StripSigma` |
| `core/stats/_linalg.py` | `solve`、`cholesky`（拒絕非正定矩陣並記錄位移） |
| `tools/run_all_checks.py`、`tools/reference_inventory.py`、`tools/measure_entrypoints.py` | 總檢查、參考檔清單（改參考檔後必須重新產生）、SKILL.md 預算 |
| `docs/maintenance.md` | 檢查、sci-fix 規則與證據等級（C1–C4、D1–D3） |
| `docs/dev/geant4-architecture/geant4-program.md` | §P.10：維護者的 isolated worktree 規定（本文件沿用） |
| `CHANGELOG.md`、`VALIDATION.md`、`docs/capability-matrix.md`、`skills/hep-detector/README.md` | 每個階段都要同步 |

#### 規則（違反會讓檢查失敗）

- CLI：成功 exit 0 並印出 JSON；`ValueError` 經 `parser.error` 成為 exit 2、`error_kind` `invalid-input`；不是有限數的
  結果為 exit 1。每個子命令有 `--status`（預設 `unvalidated`）並原樣輸出；合成結果另有 `status_label: synthetic` [C]。
- 新增或改動子命令選項時，同時改 tool contract 與 `FRONTEND_OPS`；`python3 contracts/tool_contract.py` 必須 pass [C]。
- `skills/*/scripts` 只能 import `core` 與 `contracts`（`tools/check_layering.py`）[C]。
- 技能的參考檔與程式中，實驗名稱（例如 ATLAS、CMS）只能出現在 `<!-- example: ... -->` 與 `<!-- /example -->` 之間；
  引用某實驗的方法時照 `calibration-and-alignment.md` 的「source citation」寫法（`tools/check_layering.py`）[C]。
- 改了任何參考檔就重跑 `python3 tools/reference_inventory.py`，否則 `reference_inventory` 檢查失敗 [C]。
- `skills/hep-detector/references/detector-principles-summary.md` 的路由部分不得超過 4096 bytes（這次加入連結時曾超過，
  因此新參考檔不放進該索引）[C]。
- 改變既有數值、判定或方法指引的修正用 `sci-fix:` 前綴並附回歸測試；新功能用 `feat:`（`docs/maintenance.md`）[C]。
- commit 結尾附 trailer（`Co-Authored-By: ...`，見該 session 的規定）[I]。

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

## Technical Approach

#### §0 isolated worktree（每個階段都適用）

沿用維護者在 `docs/dev/geant4-architecture/geant4-program.md` §P.10 的規定 [C]：

1. **一個階段、一個 worktree、一個分支**：位置 `.claude/worktrees/frontend-<階段>`（小寫，例如
   `.claude/worktrees/frontend-f1`），分支 `worktree-frontend-<階段>`。
2. **基底**：
   - F0：分支 `worktree-frontend-reco-sim`。若遠端沒有這個分支（目前未推送 [C]），從 `origin/main` 建 worktree，
     再以 `git am` 依序套用 patch `0001`–`0003`（隨本文件一起交付；已在乾淨的 worktree 上確認可無衝突套用，結果與分支
     的檔案樹相同）。套用後的 commit hash 會與上表不同，以 commit 訊息辨識。
   - F1–F5：F0 合併後的最新 `origin/main`；F0 未合併前，以 `worktree-frontend-reco-sim` 為基底，且之後要 rebase。
3. **建立**：
   - Claude Code：以 `EnterWorktree`（name `frontend-<階段>`）建立並進入；把實作委派給 subagent 時，Agent 工具使用
     `isolation: "worktree"`。
   - 其他環境：
     ```bash
     git fetch origin
     git worktree add .claude/worktrees/frontend-f1 -b worktree-frontend-f1 origin/main
     ```
4. **開始前確認**（結果寫進該階段 VALIDATION 條目的環境欄）：`git rev-parse --show-toplevel` 是該 worktree、
   `git branch --show-current` 是該階段分支、`git status` 乾淨、前提 commit 滿足
   `git merge-base --is-ancestor <commit> HEAD`。
5. **在 worktree 中的規則**：所有編輯、測試、MC 都在該 worktree；不 `cd` 到主要 checkout 或其他 worktree；**不用裸的
   `git stash`**（所有 worktree 共用），需要暫存就做 WIP commit；暫存輸出放在不提交的目錄（例如 `work/`）；只提交到
   該階段分支；未經維護者核准不推送 `main`、不開 pull request。
6. **結束**：合併後 `git worktree remove .claude/worktrees/frontend-<階段>` 並刪除本地分支；放棄時同樣移除，不在主要
   checkout 做任何清理。
7. F1、F2、F3 改的都是 `frontend_response.py`、同一份 contract 與同一個測試檔：**可以平行，但後合併者必須 rebase 並重跑
   全部檢查**；同一階段不由兩個 agent 同時實作 [I]。

#### §F0 合併前驗收

1. 在 E2（有 NumPy、SciPy、SymPy、mpmath）建立 worktree 並確認（§0）。
2. 執行 `python3 tools/run_all_checks.py --out work/checks`（含 host CLI；沒有 CLI 時加 `--no-cli` 並在紀錄中寫明）。
3. 任何失敗先在乾淨的 `origin/main` 上重跑同一個測試，判斷是否由本工作造成；由本工作造成的就修正並補回歸測試。
4. 在 `VALIDATION.md` 的 `FRONTEND-RECO-SIM` 加入 E2 的結果與環境欄（Python、NumPy、SciPy、SymPy 版本、commit）。

#### §F1 `hit-efficiency` 的表格訊號模型

1. 新增 `--signal-model table` 與 `--spectrum FILE`：CSV 兩欄 `charge,density`（或 `charge,count`），電荷遞增。
2. 由表格建立單調 CDF（梯形積分後歸一化；對 count 以 bin 邊界處理），在表格範圍外以 0 與 1 延伸並在 `validity` 標示。
3. `--signal-fraction` 對表格同樣縮放電荷軸；`--threshold-dispersion` 與佔有率計算不變。
4. 讀檔錯誤（不存在、非數字、非遞增、負值、總和為零）是 invalid-input（exit 2，JSON），不是 traceback。
5. 參考檔「Efficiency with a fluctuating signal」一段加一句：低於 1 % 的低側尾部用 `table` 模型與量測譜。

#### §F2 `waveform-toy` 的量測雜訊共變異

1. 新增 `--noise-covariance FILE`：JSON `{"covariance": [[...]]}`，維度等於 `--samples`，單位為每 sample 的雜訊 σ²；與
   `--rho` 互斥。
2. 用 `core.stats._linalg.cholesky` 分解（非正定就 invalid-input，不得自行修補矩陣）；每個事件以 `L·z` 生成雜訊。
3. 權重與預測使用同一個矩陣（加上 Campbell pileup 項）；`optimal-filter` 也接受同一選項，兩者共用一個讀檔函式。
4. 輸出增加 `noise_model`（`ar1` 或 `measured`）與矩陣的 SHA-256。

#### §F3 `s-curve` 多通道批次

1. 新增 `--scan-file FILE`：CSV 欄位 `channel,charge,injections,hits`；與 `--charges/--hits` 互斥。
2. 每個通道呼叫現有 `scurve_fit`；失敗的通道（未跨過 50 %、矩陣奇異）列在 `failed_channels` 並附原因，不中斷整批。
3. 摘要：門檻的平均、標準差、以 MAD 估的穩健分散、noise 的中位數、fit p < 1e-3 的通道數。
4. 摘要中的門檻分散可直接作為 `threshold-trim --spread` 與 `hit-efficiency --threshold-dispersion` 的輸入；在 `note` 中寫明
   這個分散包含每通道擬合誤差（`sqrt(sd² − mean(σ_T²))` 為去除擬合誤差後的估計，另列）。

#### §F4 simreco 連動（需維護者決定後才開始）

1. 目標：`noise-digitization` 的 `efficiency` 與 `noise_hits_per_plane` 可以由 `hit-efficiency` 的結果填入，門檻改以
   ENC 為單位表示的選項並存（不刪除現行的電荷比例門檻）。
2. 這會改變 simreco 的輸出與 F4 qualification 路徑上的數值，屬於 `sci-fix` 或需要新的規格版本；依 `docs/maintenance.md`
   的證據等級與 Geant4 規格的閘門處理，並重新記錄 J15。細節由維護者在決定時指定 [U]。

#### §F5 參考檔拆分（可選）

1. 把 `## Photosensor readout` 與 `## LAr TPC signal processing` 移到新參考檔（例如 photosensor-and-tpc-readout），原處
   留一行指引；用 `move:` 前綴的 commit，不改內容。
2. 所有指向舊錨點的連結改到新檔；`tests/skills/test_reference_links.py` 與 `reference_inventory --check` 通過；
   `detector-principles-summary.md` 不加連結（路由預算）。

## Deliverables

- F0：E2 的完整檢查紀錄（`work/checks/check-run-*.json` 的摘要寫入 `VALIDATION.md` 的 `FRONTEND-RECO-SIM`）；必要的修正 commit。
- F1：`frontend_response.py` 的 `table` 訊號模型；contract 與 `FRONTEND_OPS` 更新；測試；參考檔一句；CHANGELOG、VALIDATION 條目。
- F2：`--noise-covariance`（`waveform-toy`、`optimal-filter`）；contract、測試、CHANGELOG、VALIDATION。
- F3：`--scan-file` 批次模式；contract、測試、CHANGELOG、VALIDATION。
- F4：依維護者決定的規格交付（目前無）。
- F5：新參考檔、更新的連結、重新產生的 reference inventory、README 的參考檔數目。
- 每個階段：一個分支、一個或數個 commit，附 trailer；不推送 `main`。

## Acceptance Criteria

- **F0-1** `tools/run_all_checks.py` 在 E2 除 host CLI 外全部 pass；若有失敗，每一個都附「在乾淨 main 上同樣失敗」的紀錄。
- **F0-2** `VALIDATION.md` 的 `FRONTEND-RECO-SIM` 有 E2 環境欄（版本與 commit）。
- **F1-1** 以 Landau 模型在細格點上取樣產生的表格，`table` 模型的效率與 `landau` 模型相差 < 1e-5（門檻 2000–12000 e，
  MPV 23000 e、ξ 1500 e、σ 1000 e）。
- **F1-2** Gaussian 表格的效率等於閉式 Φ 至 1e-6。
- **F1-3** 五種壞檔案各得 exit 2 與 `error_kind: invalid-input`，stderr 無 traceback。
- **F2-1** 給定 ρ^|i−j| 矩陣時，`--noise-covariance` 的 `predicted_sigma` 與 `--rho` 相同至 1e-12，且同一 seed 下 MC 結果在
  統計誤差內一致（closure |z| < 4）。
- **F2-2** 一個非指數相關的正定矩陣（例如加 common-mode 常數項）下，20 000 事件的樣本共變異與輸入矩陣每個元素相差在
  4 個標準誤以內，closure |z| < 4。
- **F2-3** 非正定或維度不符的矩陣得 invalid-input；矩陣不被修補。
- **F3-1** 以 `scurve_fit` 逐通道計算的結果與批次輸出完全相同。
- **F3-2** 合成 200 通道（門檻 N(3700, 150²) e、σ 300 e、100 次注入）時，去除擬合誤差後的分散估計與 150 e 相差在其 MC
  標準誤的 3 倍內。
- **F3-3** 含一個不跨 50 % 的通道時，整批仍完成，該通道出現在 `failed_channels`。
- **全部階段** `python3 contracts/tool_contract.py` pass；`ruff check` 對改動的 Python 檔無錯；`reference_inventory --check`
  pass；`tools/measure_entrypoints.py` 的 hep-detector `quick_load_bytes` ≤ 25,600。

## Validation

在該階段 worktree 的 `plugins/hep-research` 目錄下執行（最後一行是 F0 與合併前的完整檢查，在 E2 執行）：

```bash
python3 -m unittest tests.skills.hep_detector.test_frontend_waveforms \
  tests.skills.hep_detector.test_frontend_response tests.contracts.test_tool_contract \
  tests.skills.test_cli_contract tests.skills.test_cli_robustness tests.skills.test_reference_links
python3 contracts/tool_contract.py contracts/tool_contracts/frontend_response.json
python3 tools/reference_inventory.py --check
ruff check skills/hep-detector/scripts/frontend_response.py tests/skills/hep_detector/test_frontend_waveforms.py
python3 tools/run_all_checks.py --part static --no-cli --out work/checks
python3 tools/run_all_checks.py --out work/checks
```

- 每個新數值至少一個獨立 oracle（解析、閉式、獨立實作或 MC），寫在測試檔頂端的 oracle 清單；比照
  `test_frontend_waveforms.py` 的做法。
- 對改動的函式做 revert mutant：把修正還原時，至少一個新測試必須失敗（`docs/maintenance.md` 的 D 等級）。
- 已知與本工作無關的失敗：缺 SymPy／mpmath 的 16 個測試、`test_paper_skeleton`、`test_ci_plan.RunnerRecord`（在乾淨 main
  上也失敗）；在 E2 若仍失敗，以同樣方式在乾淨 main 上確認。

## Open Questions

- **[U] D-F0 合併路徑**：分支 `worktree-frontend-reco-sim` 由誰推送、以單一 PR 還是分 commit 合併？這次算哪個版本號？
  （Requires Confirmation，維護者）
- **[U] D-F4 simreco 連動**：要不要做？若做，是 `sci-fix` 還是新的 Geant4 規格版本？J15 要重新記錄到哪個程度？
  （Requires Confirmation，維護者）
- **[U] F1 的量測電荷譜**：是否有可公開放進 `assets/` 的薄矽電荷譜範例？沒有時只用合成表格做測試。（Open Question）
- **[U] F5 是否需要**：24 KB 是警告不是錯誤；是否要拆？（Open Question）
- **[U] E2 環境**：目前的 E2 版本組合（Python、SciPy、SymPy）以維護者紀錄為準。（Requires Confirmation）

## References

- 任務格式：`skills/hep-computing/assets/task-template.md`、`skills/hep-computing/references/task-authoring-guide.md`、
  `skills/hep-computing/references/task-quality-checklist.md`、`skills/hep-computing/references/acceptance-criteria.md`。
- 維護規則：`docs/maintenance.md`；worktree 規定：`docs/dev/geant4-architecture/geant4-program.md` §P.10。
- 內容：`skills/hep-detector/references/front-end-electronics-and-signal-processing.md`、
  `skills/hep-detector/references/readout-digitization-and-overlay.md`、`skills/hep-detector/references/detector-simulation.md`、
  `skills/hep-detector/references/calibration-and-alignment.md`。
- 證據：`VALIDATION.md` 的 `FRONTEND-RECO-SIM`；`CHANGELOG.md` 的 Unreleased。
- 外部來源（已讀，2026-10-25）：
  - W. E. Cleland, E. G. Stern, Nucl. Instrum. Methods A338 (1994) 467（optimal filtering 與 pileup 雜訊）。
  - M. Aharrouche et al., arXiv:0709.1094（ATLAS LAr：以 g、g′ 與 pedestal-run 自相關的 Lagrange 乘數求 OF 係數）。
  - N. Nikiforou for ATLAS, arXiv:1306.6756（ATLAS LAr 的 M_phys/M_cali 校準比）。
  - J. Apostolakis et al., arXiv:1803.04165（HSF 模擬白皮書：overlay 需要未 zero-suppress 的樣本，訊號相加有非線性）。
  - J. P. Nolan, Stochastic Models 13 (1997) 759, DOI 10.1080/15326349708807450（穩定分布的積分式）。
  - V. T. Jordanov, G. F. Knoll, Nucl. Instrum. Methods A345 (1994) 337（數位梯形整形）。
