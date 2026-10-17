# hep-research 行為測試體系：設計說明

## 1. 為什麼需要這一層

hep-research 已有約 400 個測試模組，涵蓋程式、契約、腳本與靜態路由。它們回答的問題是「程式對不對」。

但實測失敗集中在另一個問題：**agent 在使用這個外掛時，行為對不對**。具體來說：

- 有載入 skill 與 profile 的回答平均 9.07 分，沒載入的只有 4.52 分
- 所有 blocking failure 都來自跳過 profile 的回答
- Haiku 4.5 的選擇率只有 37/118，95% 區間約 [23.7%, 40.2%]

這些都不是程式錯誤，而是行為錯誤。`evals/` 補的就是這一層。

## 2. 架構

```
cases/*.json ─┐
routing table ┼─> cases.py ──> runner.py ──> host (claude -p, stream-json)
holdout file ─┘       │             │              │
                      │        workspace/      transcript
                      │        (fixtures,          │
                      │         project,           v
                      │         hook)          trace.py ──> graders.py ──> grade.json
                      │                                         │
invariants.json ──────┴────────── coverage ◄────────────────────┤
                                                                v
                                    judge.py (rubric, calibrated) ─> report.py ─> report.md / gate
```

設計上的幾個決定：

1. **路由表只有一份。** L1 案例直接從 `tests/routing/cases.json` 匯入，不複製。新增路由案例時，行為測試自動涵蓋。
2. **profile 綁定自動變成 L1/L2 交界測試。** 只要案例的 project 綁定 profile，就自動加上「必須讀 profile 的 index.md」（blocking）與「讀 profile 必須在回答之前」（major）。目前共有 27 個案例檢查這條規則。
3. **評分只讀 transcript 和 workspace。** 所以評分器改版後可以用 `regrade` 重評舊的執行紀錄，不需要再呼叫模型。
4. **測試框架本身有離線測試。** `tests/fake_claude.py` 是一個腳本化的假 host，讓整條管線（workspace、四種 arm、hook、評分、報告、比較）都能在 CI 裡測，不花錢。

## 3. 四個 arm 是用來分離各層的消融實驗

| 比較 | 回答的問題 |
|---|---|
| natural vs forced | 失敗有多少來自「沒選到 skill」，有多少來自「選到了也做不對」 |
| natural vs baseline | skill 到底帶來多少價值 |
| natural vs enforced（L4） | 模型會不會**嘗試**越線，以及 host 能不能**擋下** |

報告裡的分解表直接給出 P(load)、P(pass | load)、P(pass | no load)，以及「失敗中有多少比例來自沒載入」。這正是之前 9.07 對 4.52 的數字需要的因果拆解：如果 forced arm 的通過率接近 natural 中已載入的那一群，就證明問題確實在 L1。

## 4. 評分原則

- **過程事實用確定性評分。** 載入了哪些 skill、讀了哪些檔案、跑了哪些指令、哪些內容進入了 context、產出了哪些 artifact。
- **沒有證據就不算通過。** 評分器拿不到證據時回傳 unverified；blocking 或 major 的 unverified 直接讓案例失敗。這和外掛自己的 rule registry 原則一致。
- **嘗試就算。** L4 的 `file_not_read` 把被 hook 擋下的嘗試也算成失敗，所以 natural arm 量的是模型意圖，enforced arm 量的是 host 能力，兩者分開。
- **洩漏檢查兩個通道。** `sealed_values_absent` 同時檢查工具結果（進入模型 context 的內容）和模型輸出，涵蓋不同的數值格式（61.4、61.40、1847.）。
- **judge 在校正前只算 minor。** judge 本身是一個需要校正的偵測器：至少 30 筆人工標註、kappa ≥ 0.6 之後，才能升為 major。

## 5. 統計

| 用途 | 方法 |
|---|---|
| 所有比率 | Wilson 95% 區間 |
| 可靠度 | pass@k（能力上限）與 pass^k（k 次全過，blocking 規則該看這個） |
| 兩版比較 | 配對 McNemar exact，加上以案例為群集的 bootstrap |
| 發版門檻 | 檢查**區間下界**，小樣本不能靠運氣過關 |
| 規劃 | `run.py power` 給出所需樣本數 |

例如：要把 Haiku 的選擇率量到 ±5%，大約需要 320 到 370 次執行；要在配對設計下偵出 10 個百分點的改進（翻轉比例 20%），大約需要 150 個案例。

## 6. 保留集：評測集也要 blind

根據評測集反覆調整 description，等於看著 signal region 調 cut。

- 開發集（`cases/` 與路由表）可以隨意看、隨意調
- 保留集由另一個人撰寫，放在 repo 外，用 `holdout commit` 記錄雜湊
- 每次開啟都記錄版本與日期；檔案被改過就無法通過驗證
- `holdout leaks` 拒絕直接引用 description 4 個連續詞的題目，因為那測的是字串比對而不是選擇能力
- 報告會在保留集數字旁標示已開啟幾次；開啟幾次後就該退役，換一套新的

## 7. 不變式登錄表與目前的缺口

`invariants.json` 登錄了外掛文字中的全部 53 條規則（7 個 skill 的 Invariants 加上 context-resolution 的 6 步），另加 3 條跨層規則。`coverage` 會檢查三件事：SKILL.md 新增了規則卻沒登錄、登錄的規則在文字中已經消失、登錄的機制或測試路徑不存在。任何一項成立就失敗。

以目前的 0.14.1 執行，結果如下：

| 缺口 | 數量 | 意義 |
|---|---|---|
| blocking 規則只靠散文 | 10 | 包括 L1 選擇、讀 profile、不從記憶給數字（MEAS-02）、引用要查證（COMM-03） |
| blocking 規則沒載入 skill 就沒人檢查 | 29 | 在 Haiku 上，這些規則約七成時間根本不存在 |
| 執行層級低於目標 | 17 | 這就是工作清單 |
| 完全沒有測試 | 6 | COMM-02、COMP-06、DET-07、ML-06、THEO-03、THEO-04 |

## 8. 建置過程中觀察到的事

以下是建置 L3 故障注入時，對 `contracts/validate.py` 實際執行的結果，不是推測：

- **`status: ["failed"]` 的 response artifact 通過驗證。** 這在設計上可能是正確的（格式合法），但代表只有會讀 status 的 agent 才能擋下失敗結果往下游傳。`l3-fault-response-status-failed` 專門測這件事。
- **`contract_version` 改成 1.0.0 或 2.0.0 時，驗證沒有任何 finding；改成 9.0.0 才報 `contract.unsupported_major`。** 如果舊版契約是刻意相容，建議至少給一個 warning，讓接手的 agent 知道。
- **缺 orientation、單位不符、效率重複計算** 這三種故障，validator 都能抓到。所以這三個 L3 案例測的是 agent 有沒有**去跑** validator，而不是 validator 本身。
- `VALIDATION.md` 的標題寫的是 0.3.0，但外掛目前是 0.14.1；Haiku 37/118 的數字是在 0.2.6 上量的。建議用這套體系在 0.14.1 上重新量一次基準。

## 9. 建議的執行節奏

| 時機 | 跑什麼 | 規模（單一模型） |
|---|---|---|
| 每次 commit（CI） | `unittest evals/tests`、`validate`、`coverage` | 免費 |
| 改 description | `--preset selection`，Haiku 與 Sonnet 各一次，再用 `compare` 和上一版配對比較 | 約 1,260 次 |
| 改 SKILL.md 或 profile | `--preset boundary` 與 `--preset execution` | 約 165 + 195 次 |
| 改契約或交接 | `--preset composition` | 約 48 次 |
| 改 blinding 相關 | `--preset authority` | 約 80 次 |
| 發版 | `--preset release`，開保留集，跑 judge，`report --gate` | 約 1,550 次 |

## 10. 建議的第一次執行

先回答最關鍵的因果問題：失敗究竟來自 L1 還是 L2？

```bash
python3 evals/run.py run --preset boundary --models claude-haiku-4-5,claude-sonnet-5-5 --yes
python3 evals/run.py report --run evals/runs/<id>
```

看分解表中 forced arm 的 P(pass | load)：

- 如果接近 natural 中已載入的那一群，問題在 L1，下一步做 router 入口或 prompt hook
- 如果明顯更低，L2 本身也有缺口，從 coverage 的「blocking 規則只靠散文」清單開始，逐條改成腳本檢查
