# hep-research 跨 artifact 分析檢查(Cross-Artifact Analysis Check)— 最終架構規格

## 0. 文件說明

### 0.1 基本資訊

| 項目 | 內容 |
| --- | --- |
| 對象 | hep-research 的跨 artifact analysis check(以下簡稱 **checker**),以及與它相關的元件 |
| 版本 | 2026-10-22 定稿;第二次結構整理版(內容與整理前相同,只調整組織與用語) |
| 地位 | **唯一有效的架構文件。** 其他方案與備忘錄都已取代(§16) |
| 語言 | 中文版(本文件)與英文版 `cross-artifact-check-architecture.en.md` 內容一致;兩者若有出入,以中文版為準 |
| 讀者 | maintainer、審查者,以及執行實作的 agent(例如 Claude) |
| 規則狀態 | checker 的全部規則維持 **shadow mode**;本文件**不啟用**任何 gate 條件 |

### 0.2 量測基準

| 項目 | 內容 |
| --- | --- |
| 首次量測 | hep-research 0.21.0(contracts 3.2.0) |
| 目前基準 | hep-research **0.24.1**(contracts 3.6.0),2026-10-22 全部重新量測;`plugin_release()` 驗證為 0.24.1(已發布的 release) |
| 0.21.0 → 0.24.1 之間 checker 的變化 | **沒有。** checker 的程式、suite、registry、catalog、coverage、相關 schema 與 `docs/dev/v6.3/` 都逐位元相同。0.24.x 的變更在 independent review 的 expert 角色、advisory 與 sci-fix,不涉及 checker |
| 在 0.24.1 上重跑的結果 | F1–F9(§1)、§8.1 的相容性事實、205 個既有測試、`rule_registry.py check`(23 條規則、71 個 V case)、10 個 gap probe 都與先前相同;以舊版凍結的 bundle 在 0.24.1 上 check 仍為 complete |
| 更正 | 本文件先前稱為「0.23.0」的基準,其實是 0.23.0 之後、尚未發布的開發版(`plugin.json` 寫 0.23.0,但 CHANGELOG 有 `Unreleased` 段落,`plugin_release()` 回傳 `unreleased`) |
| release 的寫法 | 本計畫的 release 一律以相對代號 R1–R3 表示(§8.2),不寫絕對版本號 |

### 0.3 一頁摘要

- **checker 是什麼:** 對一個凍結的分析(bundle)做跨 artifact 的一致性檢查,產生 advisory 診斷。
- **現況:** 規則層的設計是對的,但有 22 個已重現的缺口(G1–G22),而且**沒有任何真實流程在執行它**(F2、F3)。
- **核心判斷:** 先取得價值的證據(價值閘門,§10),再決定是否修正與擴充。
- **架構:** 兩個平面(§5.1,DR-11 待決)。診斷平面 A 現在做;保證平面 B 只寫設計。
- **路線:** 第 0 期(基礎,不改任何規則 outcome)→ 第 1 期(價值閘門)→ 決策點(繼續、縮小或停止)→ 第 2 期(修正缺口)。
- **已決定:** DR-1 至 DR-8 的原文已採用;它們審查後的修訂仍**待確認**。
- **待決:** DR-9 至 DR-15。
- **另外的工作包 WP-R:** 把程式代號「v6.3 / v63」改為描述性名稱。工具已完成,並已在 0.24.1 上驗證改名前後的完整檢查結果完全相同(§8.3);是否採用取決於 DR-15。
- **下一步:** 計畫負責人決定 DR-9、DR-11、DR-12、DR-13(第 0 期的前置條件)。

### 0.4 依需要找章節

| 想知道 | 看 |
| --- | --- |
| 現況與證據 | §1 |
| 術語與 ID | §2 |
| 範圍(做什麼、不做什麼) | §3 |
| 規範性原則 | §4 |
| 架構、平面與元件 | §5 |
| 缺口 | §6 |
| 某件事是否已決定 | §7。**標為「待決」或「待確認」的內容,不得當成已決定來實作** |
| 版本、相容性、release | §8.1、§8.2 |
| 改名(WP-R) | §8.3 |
| 該做什麼、什麼時候做 | §9;每一期都列出「前置條件 → 工作 → 禁止事項 → 結束條件」 |
| 價值閘門、入口、探針 | §10、§11、§12 |
| 誰負責、記錄慣例、退場 | §13 |
| 風險與未決事項 | §14 |
| 實作時的規則 | §15(**實作前必讀**) |
| 哪些文件有效 | §16 |
| 如何重現證據 | 附錄 A |

### 0.5 用語與證據等級

| 用語 | 意思 |
| --- | --- |
| **必須 / MUST** | 強制要求 |
| **不得 / MUST NOT** | 強制禁止 |
| **應 / SHOULD** | 建議;偏離時要寫明理由 |
| **Confirmed** | 已在 0.21.0 副本中實測或讀碼確認,並在 0.24.1 複核,附有證據 |
| **Inferred** | 由已確認的事實推得,未直接量測 |
| **Unresolved** | 尚未知道答案 |
| **待決** | 尚未決定的決策項目(§7) |
| **待確認** | 已提出、但要等計畫負責人以有日期的段落確認才生效的修訂(§7.1) |

**容易混淆的代號:** `R1`–`R3` 是本計畫的 release(§8.2);`RN-1`–`RN-7` 是改名的安全規則(§8.3.3);`R-AUX`、`r-real.*` 等是 checker 的規則名稱。三者無關。

---

## 1. 背景與現況(全部 Confirmed)

| # | 事實 | 證據 |
| --- | --- | --- |
| F1 | 分析檢查計畫新增約 4,000 行 checker 相關程式碼,以及 205 個測試(不含另外加入的 `test_cross_artifact_check_gap_probes.py`) | `wc -l`;`tests/contracts/test_v63_*.py` |
| F2 | **沒有任何程式化的真實流程執行 checker。** 唯一的程式入口是選用旗標 `review_measurement_spec.py --check-bundle` | grep 呼叫者 |
| F3 | 8 個 `SKILL.md` 都沒有提到 checker;路由測試案例(0.21 有 415 個,0.24.1 有 419 個)都不會呼叫它;20 個範例都沒有執行它 | `skills/*/SKILL.md`;`tests/routing/cases.json`;`examples/*/run.py` |
| F4 | 5 份 skill reference 與 plugin README 教 agent **手動**執行 `freeze` 與 `check` | `preservation-checklist.md`、`analysis-workflows.md`、`time-series-inference.md`、`nuisance-modeling.md`、`review-and-artifacts.md`;README 第 275–312 行 |
| F5 | `freeze` 需要 recipe 與 check-context;整個 plugin 只有一份參考用的 recipe,也沒有工具會產生 recipe 或 check-context | `contracts/semantics/recipes/flux_from_counts.json` |
| F6 | 目前沒有任何角色可以接受 check report 作為證據 | `docs/dev/v6.3/decision-enforce.md:69` |
| F7 | 目前沒有任何 host 設定通過私有或 blinded 資料的資格審查 | `docs/protected-data-architecture.md:5` |
| F8 | 架構的設計是:固定的 recipe 加上有界的 operator-semantics table,並「never omits scientific review」;closure 測試屬於 T3 的控制 | `protected-data-architecture.md:379`、`:358` |
| F9 | S3 執行與 formal use 是兩個不同的 scope;gate 位於 plugin 的 agent 端程式之外 | `protected-data-architecture.md:433` |
| F10 | 已知缺口 G1–G22(§6)都已用測試或腳本重現 | `final/test_cross_artifact_check_gap_probes.py`(G1–G10)與 `archive/evidence/` |

**結論:** checker 的規則層設計是對的,需要修正,不需要重寫。目前缺的是**價值的證據**;是否要建立更方便的入口,取決於證據。

---

## 2. 名詞定義

### 2.1 checker 的概念

| 術語 | 定義 |
| --- | --- |
| 分析檢查計畫 | plugin 內部代號為「v6.3」的開發計畫(2026-10-16 起),建立了 checker。記錄位於 `docs/dev/v6.3/`,測試為 `tests/contracts/test_v63_*.py`;若 DR-15 採用,改名為 `docs/dev/cross-artifact-check/` 與 `test_analysis_check_*`(§8.3)。本文件以「分析檢查計畫」稱呼它 |
| checker | `contracts/analysis_check.py` 與 `contracts/analysis_checks/`:對一個凍結的分析做跨 artifact 檢查 |
| bundle(v2) | `freeze` 產生的凍結分析,格式 `hep-research-analysis-bundle/2`;內含 items、check-context、semantic-lock |
| check-context | bundle 中描述分析意圖的文件:roots、recipe instances、bindings、declarations、凍結的 obligation 清單 |
| suite | 一組規則與 obligation generator,例如 `counting-chain/1.0.0`、`ratio-subset`、`model-card`、`run-lineage` |
| obligation | 某條規則對某個 subject 的一項檢查;結果是五種狀態之一 |
| 五種狀態 | `satisfied`、`violated`、`not_applicable`、`unverified`、`unsupported`;coverage 只計算前三種(已決定的),不是通過率 |
| declaration-based | 結果依賴 agent 撰寫的宣告;formal-use 檢視中視為 unverified |
| semantic-lock | 凍結時所用定義的 digest(suite、registry、coverage、table、catalog) |
| snapshot | 以內容定址儲存的定義副本,讓舊 subject 能以舊語意重現(D11b) |
| `lock_differences` / `installed_differences` | 凍結的定義與目前定義不同;前者是沒有 snapshot 時的差異,後者是以 snapshot 重現時記錄的差異 |
| 版本守衛 | 規則、generator 或輸入檢查的版本與 suite 指定的不同時,不評估而給 `rule_not_run` |
| L1 / L2 | `validate.py`(單一 artifact)/ `recipe_semantics.py`(recipe 語意);在分析檢查計畫之前就存在 |

### 2.2 本架構的概念

| 術語 | 定義 |
| --- | --- |
| 診斷平面(A) | 在 agent 端執行的 checker;只產生 advisory 診斷 |
| 保證平面(B) | 位於 custodian formal-use gate 的檢查;由 custodian 自己重跑並判斷輸入的保管 |
| 受保護輸入 | `core/protected/trusted_input.read_protected()` 判定、只可能由 custodian 寫入的檔案 |
| `plugin_release` | `core/protected/identity.plugin_release()` 的結果:副本與某個 release manifest 完全一致時回傳該版本,否則回傳 `unreleased` |
| `.in_use/` | plugin 系統在已安裝副本的根目錄寫入的執行期資料夾;0.24.0 起不計入副本的身分 |
| 價值閘門 | 擴充之前的量測:checker 相對於既有防線,能多抓到多少錯誤(§10) |
| 入口 | 協助產生 v2 bundle 的工具(`analysis_check.py draft`);是否建立依 DR-14(§11) |
| 期別 | 路線圖的階段:第 0、1、2 期與覆蓋擴充(§9) |
| session | 估計工作量的單位:一次連續的實作工作 |
| WP-R | 程式代號改名的工作包(§8.3,依 DR-15) |

### 2.3 ID 族群

| ID | 意思 | 定義所在 |
| --- | --- | --- |
| F1–F10 | 現況事實 | §1 |
| P1–P10 | 設計原則 | §4 |
| G1–G22 / A1–A6 | 缺口 / 附帶問題 | §6 |
| DR-1–DR-15 | 本計畫的決策項目 | §7 |
| R1–R3 | 本計畫的 release(相對代號) | §8.2 |
| RN-1–RN-7 | 改名的安全規則 | §8.3.3 |
| V01–V91 | registry 中的驗證案例;V01–V71 已存在,V72–V91 為本計畫新增 | `contracts/rules/registry.json`;§6 |
| O、C、HC、D12b、D11b、G-ENFORCE、T3、S3 | plugin 既有的開放問題、條件、硬性約束、記錄慣例、決策關卡、威脅類別與執行 scope | `docs/dev/v6.3/` 與 `docs/protected-data-architecture.md` |

---

## 3. 目標與範圍

### 3.1 目標

1. 讓 checker 成為**審查者可靠的一致性輔助工具**:診斷結果正確,而且誠實。
2. 在投入更多開發之前,**取得價值的證據**。
3. 為未來的保證機制**保留正確的位置**(保證平面),但現在不實作。

### 3.2 不做的事(non-goals)

- 不啟用 gate,不讓任何規則離開 shadow mode。
- 不修改 permit 與 attestation 的 schema;不修改 `core/partition/`、`core/protected/`。
- 不在樹內保留舊版規則實作;舊結果以當時的 release 重現。
- 不從執行記錄或 argv 推導 operator(除非 §12 的探針證明可行)。
- 不以數值相等判斷兩筆觀測是否相同。
- 不設固定的容差上限。
- 不支援 model-card 的 joint evaluation(O03)。
- 不事後補升 0.14.0 的版本標籤(A2)。
- 不建立更細的 semantic-lock(只釘選用到的定義);它需要「規則到定義」的對應表,而這張表目前不存在。
- 不宣稱能防偽造:即使在保證平面,也防不了偽造的 `state.json` 或 chunk 檔。

---

## 4. 設計原則(規範性)

| # | 原則 |
| --- | --- |
| P1 | agent 端的 check report **必須**只作為 advisory 診斷,**不得**被表述或使用為授權(HC-05)。 |
| P2 | checker 比對描述與工具產生的 artifact,**不得**宣稱它代表實際執行的計算。 |
| P3 | 規則、obligation generator 與輸入檢查**必須**受版本守衛:版本不符時給 `rule_not_run`,**不得**以新程式碼評估舊版本。規則修正**必須**以新版本發布。 |
| P4 | 對 agent 可寫的輸入做刪減或放寬,**不得**讓 status 上升或 obligation 減少。工具產生的草稿**不得**自動寫入宣告或 binding。 |
| P5 | 規則**必須**先彙整全部證據再判斷;結果**不得**依賴輸入的順序。 |
| P6 | 有 dependency-missing 或 `lock_differences` 時,status **不得**是 `complete`(與 exit code 一致)。以 snapshot 重現舊語意而產生的 `installed_differences`,依 D11b **可以**是 complete。 |
| P7 | blinding 的允許**必須**追溯到資料葉節點;只有結果自己的標籤時,**必須**判為 unverified。 |
| P8 | (只適用於保證平面)只有 custodian 保管、位於專案之外、以 digest 引用的檔案,才算事實;保管狀態**必須**以具名的分析者帳號判斷,而不是以執行中的帳號判斷。 |
| P9 | 任何擴充(規則修正、入口、新 suite)**必須**在價值閘門之後。 |
| P10 | 某條規則拿來比對的欄位,**不得**從該規則讀取的同一個來源自動產生。 |

---

## 5. 架構

### 5.1 兩個平面(依 DR-11;**待決**)

| 項目 | 診斷平面 A | 保證平面 B |
| --- | --- | --- |
| 目的 | 找出描述之間的矛盾與誠實的錯誤 | 給 formal-use gate 可依賴的結果 |
| 執行者 | agent | custodian 的 formal-use gate(不是 S3 執行) |
| 何時實作 | **現在** | custodian 身分、合格的 host、O14 的角色都存在之後;**現在只寫設計** |
| checker 版本 | 已安裝的版本,受版本守衛 | 由 purpose policy 的 `checker_digests` 指定;**不得**由 bundle 決定 |
| 定義 | 已安裝的定義,或依 D11b 由 snapshot 重現 | 拒絕分析者提供的 snapshot 與 bundle 自帶的定義,或使用已發布定義的索引 |
| `check-report` 的角色 | 便宜的拒絕條件:dependency-missing、`lock_differences`、預發布 suite、與 frozen inventory 不符 | gate 邏輯:V60、V65、V66、保管判斷、與審查報告的比對 |
| 信任標記 | `declaration_based` 只作提示;G8、A3 一律標記 | P8;分析者帳號的來源需要定案 |
| 報告格式 | report 1.0.0 | report 1.1.0(`assessment.inputs`、`basis_summary`);`recheck_record.json`;`plugin_release` 為 `unreleased` 時,不得視為已重跑(§8.1) |
| 與人工審查 | 報告是審查的參考資料 | **必須**與審查者接受的報告比對 |
| 變異測試運算子 | relabel、rename、copy、copy+perturb、drop、loosen、toggle-optional、reorder、edit-report | unprotect、forge-definition |

**若 DR-11 不被採用:** 保證相關的處置回到 v3.1 的 WP1(custody 與宣稱)與 WP6(`check-report` 強化與 recheck),在診斷平面實作;第 2 期約再加 5–7 sessions。

### 5.2 資料流

```text
診斷平面 A(agent 端)
  專案中的 artifact(spec、recipe、response、dataset-record、calibration)
    → 手寫 bundle(DR-14 通過後:draft → 人工補齊 TODO)
    → freeze(snapshot 預設寫入 <root>/.hep-research/snapshots/)
    → check(版本守衛;P4–P7;run 記錄以 --results 傳入)
    → summary → 分析者與審查者(advisory)

                │ 審查者接受的報告,作為 attestation 的 evidence
                ▼
保證平面 B(custodian 的 formal-use gate;只設計)
  以 policy 指定的 checker release,對 custodian 保管的 bundle 副本重跑
    → 保管判斷(P8)→ 與審查報告比對 → check-report 的 gate 邏輯
```

### 5.3 元件登記

| 元件 | 路徑 | 行數 | 平面 | 目前的使用(Confirmed) | 處置 |
| --- | --- | ---: | --- | --- | --- |
| freeze、check、summary | `contracts/analysis_check.py` | 847 | A | `--check-bundle`、`migrate.py`;文件教手動使用 | 保留並修正 |
| chain 與 ratio 規則 | `contracts/analysis_checks/rules.py` | 757 | A | 只隨 checker 執行 | 保留;第 2 期修正 |
| model-card suite | `contracts/analysis_checks/model.py` | 321 | A | 只在測試;兩份 hep-statistics reference 提到 | 凍結;第 2 期只修 G5、G12;適用 §13.4 的退場程序 |
| run-lineage suite 與 result binding | `contracts/analysis_checks/runs.py` | 411 | A | 只在測試;hep-computing reference 教 agent 撰寫 binding | 保留;第 2 期修正 |
| lock 與 snapshot | `contracts/analysis_checks/lock.py` 等 | 173+ | A | 每次 freeze 與 check 都會建立 lock | 保留;snapshot 預設開啟;P6 |
| effect catalog 與 coverage | `contracts/effect_catalog.py`、`contracts/semantics/` | 206 | A | 只隨 checker 執行 | 保留 |
| 遷移 | `contracts/migrate.py` | 151 | A | 只有開發記錄與 CHANGELOG 提到 | 保留;第 2 期加入 context 1.0→1.1 的轉換 |
| rule registry | `contracts/rule_registry.py`、`contracts/rules/registry.json` | 217 | 共用 | **CI gate**(`tools/run_all_checks.py:312`) | 保留;schema 依 §8 更新 |
| custody 盤點 | `contracts/custody.py` | 102 | B(依 DR-11) | 沒有程式呼叫者;README 與 detector-atlas 提到 | 凍結 |
| check-report | `contracts/permit.py` 的 `report_check` | (427 的一部分) | A 的便宜拒絕條件;其餘屬於 B | 只在測試;V60、V65、V66 的唯一實作 | **重新定位,不棄用** |
| L2 recipe 語意 | `contracts/recipe_semantics.py` | 349 | 基準 | 0.6 起就有的獨立 CLI | 不屬於分析檢查計畫;作為價值閘門的比較基準 |
| run 驗證 | `contracts/verify_run.py` | 78 | 基準 | 0.5 起就有的獨立 CLI | 同上 |
| permit 驗證、attestation | `contracts/permit.py`、`contracts/attestation.py` | 427 + 285 | B | `hepdata_export.py` 的 protected 路徑、`protected_use.py:63`;唯一的範例以非 protected 模式執行 | 不在範圍內 |
| protected guard | `core/protected/` | — | B | **有在用**:8 支 skill 腳本與 3 個 adapter | 保證平面直接使用;不修改 |

---

## 6. 缺口登記

**欄位說明:**
- **平面:** A = 診斷平面;B = 保證平面。
- **期別:** 依 §9。
- **V case:** 驗收時要通過的 registry 案例。

| ID | 缺口 | 證據 | 平面 | 處置 | 期別 | V case |
| --- | --- | --- | --- | --- | --- | --- |
| G1 | spec 少寫 corrections,檢查就變少,結果仍是 complete | probe `test_g1` | A | DR-8:`r-real.undescribed` | 2 | V86 |
| G2 | `required: false` 是未登記的豁免,能蓋掉 violated | probe `test_g2` | A | DR-2:check-context 1.1.0 移除 | 2 | V78 |
| G3 | validation record 的判斷取決於 item ID 的排序 | probe `test_g3` | A | P5;`r-ratio.correlation` 1.1.0 | 2 | V77 |
| G4 | factor table 自選容差 | probe `test_g4` | A | DR-6 | 2 | V79 |
| G5 | 複製觀測檔可繞過 R-AUX | probe `test_g5` | A | DR-3 | 2 | V85 |
| G6 | campaign closure 沒有連回分析 | probe `test_g6` | A | `campaigns[].inputs`:沒有分析輸入 → unverified;digest 不符 → violated(`closure_mismatch`) | 2 | V82 |
| G7 | blinding 信任自報的 status | probe `test_g7` | A(lineage)/ B(標籤) | DR-7 | 2 / B | V83 |
| G8 | 自報 `asserted_by.kind: person` 可拿掉標記 | probe `test_g8` | A(一律標記)/ B(保管) | DR-1 | 2 / B | V88 |
| G9 | report 的 `result_binding` 段可手改 | probe `test_g9` | B | 保證平面設計 | B | — |
| G10 | `CHECKER_FILES` 沒有涵蓋執行時載入的模組 | probe `test_g10` | 共用 | 以執行時載入的模組為準 | 0 | V74 |
| G11 | 刪改 report 的 obligations,`check-report` 不察覺 | `review/p_new2.py` | A(便宜比對)/ B(偽造) | 與 frozen inventory 比對 | 0 / B | V75 |
| G12 | 單一 model 內的 `shared_parameters` 隱藏 V07 | `review/p_new1.py` | A | 限 1.1.0 判 input-invalid;修正 shadow 分類 | 2 | V80 |
| G13 | blinding 是否適用只看 spec 的旗標 | `review/p_new4.py` | A | 依 DR-9 的對應鍵 | 2 | V84 |
| G14 | factor obligation 取決於 calibration 的對應鍵 | `review/p_new5.py` | A | 掛在 parent 或 child 都產生 obligation | 2 | V87 |
| G15 | 兩份 bundle coverage 其中一份被默默忽略 | `review/p_new5.py` | A | 限 1.1.0 判 input-invalid | 2 | V81 |
| G16 | 容差可以是 NaN 或字串;calibration 沒有 schema | `review/p_new5.py` | A | 限 1.1.0 判 input-invalid;calibration shape | 2 | V79 |
| G17 | `_exclusion` 依宣告順序判斷 | `review/p_new5.py` | A | P5;`r-rep.repetition` 1.1.0 | 2 | V77 |
| G18 | 規則程式碼沒有版本 | `review/p_drift.py` | 共用 | 版本守衛的機制與函式層級 digest;第 0 期只建機制 | 0 | V72 |
| G19 | 偽造的 suite 與定義漂移,`check-report` 都不察覺 | `review3/p1_snapsuite.py` | A(漂移)/ B(偽造) | `check-report` 的便宜拒絕條件;偽造屬於 B | 0 / B | V75 |
| G20 | status 是 complete,exit 卻是 3 | `review3/p1_snapsuite.py` | A | P6 | 0 | V73 |
| G21 | 工具產生的 recipe 片段組合後 L2 失敗 | `review4/sf_recipe.py` | A | 第 0 期分類;修改 semantics table 會改變 digest、影響 recipe 綁定與 `LEGACY_TABLE_SHA` 測試,需另做決定 | 0 / 2 | — |
| G22 | root 的 unit 沒有被檢查是否有效,也沒有與 estimand 比對 | `review5/unit_probe.py`、`review6/g22_unit.py` | A | 第 2 期:freeze 拒絕空的與佔位的 unit。完整檢查需要單位解析器,列入覆蓋擴充 | 2 / 擴充 | V89 |
| A1 | generator digest 只雜湊一個檔案 | 讀碼 | 共用 | 併入 G10 | 0 | V74 |
| A2 | 0.14.0 改了內容但版本標籤沒升 | release manifests | — | 不補升(補升會造成漂移) | — | — |
| A3 | bundle 自帶的 coverage contract 沒有標記 | 讀碼 | A / B | 併入 G8 的處置 | 2 / B | V88 |
| A4 | `runs.py` 在純函式層讀檔 | 讀碼 | A | 隨 run-lineage 的修正把 I/O 上移 | 2 | — |
| A5 | eras、per-sign factor、`simulated` 沒有建模 | 讀碼 | A | 覆蓋擴充 | 擴充 | — |
| A6 | `luminosity`、`fakes`、`fiducial` 沒有 operator 覆蓋 | 讀碼 | A | 覆蓋擴充 | 擴充 | — |

**其他 V case:** V76 = 變異測試骨架(第 0 期);V90 = context 1.0→1.1 轉換(第 2 期);V91 = 入口(第 2 期,只有 DR-14 通過才登記)。

---

## 7. 決策登記

### 7.1 規則

- DR-1 到 DR-8 已於 2026-10-22 依 maintainer 在 session 中的指示採用(「the maintainer's instruction in the session was to follow the recommendation」)。
- 表中「待確認」的內容,**必須**等計畫負責人以有日期的段落確認後才生效(D12b);在此之前,**不得**當成已決定來實作。
- 「依賴 DR-11」的內容,另外要等 DR-11 決定。

### 7.2 登記表

| DR | 已採用的內容 | 審查後的修訂(**待確認**) | 依賴 DR-11 的變更(**待確認**) |
| --- | --- | --- | --- |
| DR-1 | 依保管判斷信任;`asserted_by.kind` 不影響信任 | 只有專案之外、以 digest 引用的檔案才可能受保護;以具名的分析者帳號判斷;`check-report` 自行重判 | 拆開:G8、A3 一律標記留在 A;保管判斷移到 B |
| DR-2 | check-context 1.1.0 移除 `required`;擱置只能走 exceptions | 依 1.0.0 suite 評估的 subject 會先遇到版本守衛 | — |
| DR-3 | 觀測身分 = 來源身分 + pointer;不比對數值 | **推翻原文:** 沒有 envelope 時改用 canonical digest;多加一個 key 的副本偵測不到,屬於已知限制 | — |
| DR-4 | 防偽造只靠 custodian 重跑;`require_recheck` | `recheck_record.json`;防不了偽造的 `state.json` | 移到 B |
| DR-5 | snapshot 預設開啟;舊規則以 release 重跑 | snapshot 中的定義必須是已發布的定義 | 拆開:預設開啟、版本守衛、P6 留在 A;已發布定義的索引、custodian 副本、release 重跑移到 B |
| DR-6 | 容差由宣告的有效位數推導 | **推翻原文:** 未宣告時維持 1e-9(原文為 1e-12);核對值的實際位數;k 改用 Σ\|power\| | — |
| DR-7 | blinding 依 lineage;`simulated` 可以允許 | 沒有資料葉節點 → `lineage_no_data`;只有標籤 → unverified;dataset 與 envelope 的 status 詞彙分開 | 「custodian 核准的 derivative」那一列移到 B |
| DR-8 | 新增 `r-real.undescribed` | **推翻原文:** 不含 root 覆蓋(→ DR-10)。只有非空的 `backgrounds` 才算描述;`no_backgrounds_reason` 加上實際套用的 background → `description_contradicted`;class 比對限於 spec 列出的 members | — |
| DR-9 | — | — | **待決:** project `blinded` 清單與 spec 的對應鍵。建議:spec 的 `artifact_id` |
| DR-10 | — | — | **待決:** root 覆蓋的 subject。建議:延後到覆蓋擴充 |
| DR-11 | — | — | **待決:** 採用兩平面的劃分。建議:採用 |
| DR-12 | — | — | **待決:** 探針的範圍與上限。建議:§12 |
| DR-13 | — | — | **待決:** 價值閘門的設計與門檻,**必須在量測之前決定**。建議:§10 |
| DR-14 | — | — | **待決:** 建立入口,條件是價值閘門通過。建議:§11 |
| DR-15 | — | — | **待決:** 把程式代號「v6.3 / v63」改為描述性名稱,採用 §8.3 的對照表與安全規則。建議:採用,排入第 0 期第 11 項 |

### 7.3 相關的既有開放問題

| ID | 問題 | 與本計畫的關係 |
| --- | --- | --- |
| O03 | model-card 的支援配對 | joint evaluation 不在範圍內 |
| O04 | 非作者的審查者 | 植入錯誤的人、人工審查者 |
| O09 | effective exposure 的 efficiency members 未定義 | 影響價值閘門的旗艦案例 |
| O14 | 可接受報告的角色 | 保證平面的前提 |
| O16 | 哪些 skill 呼叫 checker | 改動 `SKILL.md` 需要新決定 |
| O17 | custodian 是否採用 gate requirement | 保證平面的前提 |

---

## 8. 版本、相容性與發布

### 8.1 相容性事實與目標

| 物件 | 事實(Confirmed;0.21 量測,0.24.1 複核) | 目標 |
| --- | --- | --- |
| SemVer 預發布版本 | `semver.parse('1.1.0-dev.1')` 丟出 `not a version`;registry 的 rule `version` pattern 與 context 的 suite version pattern 都是 `^\d+\.\d+\.\d+$`(`v_cases` 的 pattern `^V\d{2}$` 與版本無關) | R2 起接受 `1.1.0-dev.N`;`check-report` 拒絕預發布 suite(`permit.report_prerelease_suite`);任何 purpose policy 都不接受預發布 suite |
| registry schema | `registry_version` 的 enum 只有 `1.0.0`;rule 物件是 `additionalProperties: false`;`work_packages` 為 `^D\d{2}[a-d]?$`;`slice` 為 M1–M3/D11b 的 enum;同一個 `rule_id` 出現兩次 → `registry.duplicate_rule` | R1:registry 1.1.0(rule 的原始碼 digest 欄位、新的期別與工作包的值)。R2:唯一鍵改為 (rule_id, version);退休的版本以 `lifecycle` 標示 |
| semantic-lock | 1.0.0;釘選整份 registry、整份 coverage、整份 table,以及被任何 operator 引用的 effect(CASE-CHAIN 有 14 個) | **不變。** 漂移由預設開啟的 snapshot 吸收 |
| check-context | `context_version` 是 const;拒絕 1.1.0(freeze 給 `bundle.context_schema`,check 判 input-invalid);未知的 declaration 型別在 1.0.0 只產生 context finding | R2:1.1.0 |
| report | `report_version` 是 const;把 1.1.0 判為 `report_missing`;頂層 `additionalProperties: false`;`assessment` 與 obligation 物件是開放的 | 診斷平面維持 1.0.0(R1 在 `assessment` 中加入 `plugin_release`);1.1.0 屬於保證平面 |
| result binding | 給 `schema.const` 與 `schema.additional`,判 input-invalid | R2:1.1.0(`campaigns[].inputs`) |
| suites | 四個都是 1.0.0 | R2:`1.1.0-dev.N`;R3:1.1.0 stable(counting-chain、ratio-subset、run-lineage、model-card) |
| effect catalog | `effect_catalog.json` 的 `catalog_version` enum 只有 `1.0.0` | R3:1.1.0(`description_required`) |
| `plugin_release` | bundle v2 已有此欄位;dev 樹與任何多出、缺少或改動檔案的副本回傳 `unreleased`。**0.24.0 起**,已安裝的 release 副本回傳自己的版本(0.24.1 實測);在此之前,`.in_use/` 讓每個已安裝副本都回傳 `unreleased` | R1 寫入 report 的 `assessment`。因為 0.24.0 的修正,「`unreleased` 不得視為已重跑」(§5.1)在已安裝的副本上才可行 |

### 8.2 發布對應

| release | 期別 | contracts | 格式變更 | 規則 outcome 是否改變 |
| --- | --- | --- | --- | --- |
| R1 | 第 0 期 | +1 minor | registry schema 1.1.0;WP-R 改名(若 DR-15 採用) | **否** |
| R2 | 第 2 期前半 | +2 minor | SemVer 預發布的 pattern(semver、registry、context);registry 唯一鍵;check-context 1.1.0;calibration shape;result binding 1.1.0 | 是(只在 `1.1.0-dev.N` suite 中) |
| R3 | 第 2 期後半 | +3 minor | catalog 1.1.0 | 是(suite 1.1.0 stable) |

**release 代號:**
- R1 = 本計畫的第一個 release,也就是開始實作時已安裝版本之後的下一個 minor。以 2026-10-22 已安裝的 0.24.1 而言,R1 是 0.25.0。
- R2、R3 依序遞增。
- contracts 欄的「+n minor」相對於 R1 之前的 contracts 版本;每個有格式變更的 release 只升一次 contracts minor。

**預設 suite 政策:**
- R1:suite 1.0.0 的結果與 0.21 相同。
- R2:stable suite 仍為 1.0.0,但其中被修改的規則給 `rule_not_run`;release note **必須**說明,並建議以 R1 重現 1.0.0 的結果。
- R3 起:預設 suite 為 1.1.0。

### 8.3 程式代號改名(WP-R,依 DR-15)

#### 8.3.1 目的、狀態與時機

| 項目 | 內容 |
| --- | --- |
| 目的 | 把沒有意義的程式代號「v6.3 / v63」改為描述性名稱,同時不改變任何行為、不改寫任何歷史記錄 |
| 狀態 | 工具已完成並已驗證(§8.3.5);**是否採用取決於 DR-15(待決)** |
| 時機 | 第 0 期第 11 項(§9.1):**必須**在第 5 項(snapshot 預設開啟)之後,並與第 2 項(registry schema 1.1.0)在**同一個 release**(R1)發布 |
| 時機的理由 | 改名會修改 `contracts/rules/registry.json`,而它的 digest 被 semantic-lock 釘選(RN-4) |
| 工具 | `rename_analysis_check_ids.py`;交付時放入 plugin 的 `tools/` |

#### 8.3.2 對照表

| 舊名稱 | 新名稱 |
| --- | --- |
| `docs/dev/v6.3/` | `docs/dev/cross-artifact-check/`(舊路徑留一個轉址 `README.md`) |
| `test_v63_baseline_gaps` | `test_analysis_check_baseline_gaps` |
| `test_v63_d03a` | `test_analysis_check_profile_loading` |
| `test_v63_d04` | `test_analysis_check_effect_catalog` |
| `test_v63_d05a` | `test_analysis_check_identity_and_instances` |
| `test_v63_d05b` | `test_analysis_check_bundle_and_context` |
| `test_v63_d05c` | `test_analysis_check_report` |
| `test_v63_d05d` | `test_analysis_check_run_lineage` |
| `test_v63_d06` | `test_analysis_check_chain_rules` |
| `test_v63_d07` | `test_analysis_check_ratio_rules` |
| `test_v63_d07_model` | `test_analysis_check_model_rules` |
| `test_v63_d09` | `test_analysis_check_shadow_and_refusal` |
| `test_v63_d10` | `test_analysis_check_report_permit` |
| `test_v63_d11a` | `test_analysis_check_coverage_reader` |
| `test_v63_d11b` | `test_analysis_check_snapshots` |
| `test_v63_d12b` | `test_analysis_check_custody` |
| `test_v63_d17` | `test_analysis_check_review_integration` |
| `test_v63_refusal_blockers` | `test_analysis_check_refusal_blockers` |
| `test_v63_review_fixes` | `test_analysis_check_review_fixes` |
| `test_v63_rule_registry` | `test_analysis_check_rule_registry` |
| `v63_cases`、`v63_runs`(測試輔助模組) | `analysis_check_cases`、`analysis_check_runs` |
| `tests/core/test_v63_evidence_query` | `tests/core/test_evidence_query` |

以上都在 `tests/contracts/`,除非另有註明。

#### 8.3.3 安全規則(規範性)

| # | 規則 | 理由 |
| --- | --- | --- |
| RN-1 | 只替換對照表中的**完整識別字**,前後不得緊接字母、數字或底線;**不得**全域替換 `v63` 或 `v6.3` | Confirmed:`test_v63_submission_bundle_digests` 是以驗證案例 **V63** 命名的測試方法,不是計畫代號;全域替換會把它改壞 |
| RN-2 | **不得**修改:release manifests、`CHANGELOG.md`、`VALIDATION.md`、所有 `docs/dev/**/decision-*.md`、被移動的記錄的內容、釘選的定義(`contracts/vocab/effects.json`、`contracts/semantics/**`、`contracts/rules/suites/**`)、`contracts/schemas/**` | 歷史記錄不得改寫(D12b);改動釘選的定義會改變 digest,讓沒有 snapshot 的已凍結分析無法重現 |
| RN-3 | 記錄以 `git mv` 移動(保留歷史),內容不變;舊路徑留一個轉址 `README.md`,讓所有寫著 `docs/dev/v6.3/<檔名>` 的舊引用仍能找到檔案(檔名不變) | 釘選的定義與歷史記錄中寫死了舊路徑 |
| RN-4 | `contracts/rules/registry.json` 中的測試 ID **必須**一起更新;它的 digest 被 semantic-lock 1.0.0 釘選,所以改名只能在 snapshot 預設開啟之後,並與其他 registry 變更在同一個 release 發布 | Confirmed(0.24.1):改名後,以舊 checker 凍結、沒有 snapshot 的 bundle 得到 13 項 `semantics_unreproducible`(exit 3);有 snapshot 時仍是 complete |
| RN-5 | 工具必須冪等:第二次執行不得改變任何內容 | 可安全重跑 |
| RN-6 | 驗收:工具的 `--verify` 為 ok,而且完整檢查(`tools/run_all_checks.py`)的失敗集合與改名前**完全相同**。只出現在單側、且在兩邊重跑都通過的計時型測試,記為不穩定,不算差異 | 改名不得改變任何行為 |
| RN-7 | 改寫內容之後,**必須**重新產生被改到的已提交衍生檔案:只執行 `tools/reference_inventory.py`、`tools/build_stanzas.py`、`tools/capability_map.py` 中 `--check` 失敗的那幾個;`--verify` 要求三者的 `--check` 全部通過 | Confirmed:`skills/hep-authoring/references/independent-review.md` 引用了四個 `docs/dev/v6.3/` 路徑;改寫後檔案大小改變,`docs/reference-inventory.{json,md}` 隨即過期,造成 `reference_inventory`、soft-budget 與 timeout 三個測試失敗(timeout 測試在內部執行 inventory 測試) |

#### 8.3.4 工具的行為

| 項目 | 內容 |
| --- | --- |
| 模式 | `ROOT`(dry-run:列出要移動與修改的檔案)、`ROOT --apply --date YYYY-MM-DD`(執行後自動 verify)、`ROOT --verify`(只稽核) |
| exit code | 0 = ok;1 = verify 失敗;2 = 用法錯誤或拒絕執行(例如目標已存在) |
| 會做的事 | 1. 依對照表移動(git work tree 中用 `git mv`);2. 在非受保護的文字檔中替換完整識別字(RN-1);3. 重新產生過期的衍生檔案(RN-7);4. 在舊路徑寫入轉址 `README.md`;5. 刪除 `__pycache__` |
| 不會做的事 | 修改 RN-2 列出的檔案;移動後再編輯被移動的記錄 |
| `--verify` 檢查 | 沒有殘留的舊識別字;所有目標都存在、沒有遺留的來源;轉址存在,而且舊目錄只剩轉址;registry 的 107 個測試 ID 都能解析到存在的模組;三個衍生檔案的 `--check` 都通過 |
| 限制 | 只用標準函式庫;跳過 `.git`、`__pycache__`、`.in_use`、`node_modules` |

#### 8.3.5 驗證結果(2026-10-22,0.24.1;Confirmed)

驗證環境:兩份從已安裝的 0.24.1 複製的拋棄式副本(改名前、改名後),都是 git work tree,以相同的 exclude 規則忽略快取,並移除根目錄的 `.in_use/`。步驟見附錄 A.4。

| 檢查 | 結果 |
| --- | --- |
| 移動 | 23 項(1 個目錄、22 個測試模組);git 判定 17 份記錄為 R100(內容完全相同),原目錄索引逐位元相同 |
| 修改 | 改寫 12 個檔案;重新產生 2 個衍生檔案(`docs/reference-inventory.json`、`.md`);新增 1 個轉址 |
| 受保護的檔案 | 全部未變 |
| 冪等 | 第二次執行後 `git status` 為空 |
| `--verify` | ok:沒有殘留、107 個測試 ID 全部能解析、三個衍生檔案檢查全部通過 |
| 完整檢查(RN-6) | **通過。** 改名前後 check 都是 24 pass / 2 fail(`unittest`、`ams_optional`)/ 1 skip(找不到 codex CLI);單元測試兩邊都是 4905 個、408 個模組,共同失敗 16 個(環境因素:缺 sympy、LaTeX、外部 CLI);**只在單側出現的失敗:0 個**,所有計數完全相同;每次約 32 分鐘 |
| semantic-lock(RN-4) | 以改名前的副本凍結、改名後的副本 check:沒有 snapshot store 時 13 項 `semantics_unreproducible`(exit 3);有 snapshot 時 complete(exit 0) |
| `plugin_release` | 改名後的副本回傳 `unreleased`(檔案已改動),直到改名所屬的 release 產生自己的 manifest 為止。這是預期的;改名只能隨 release 發布(RN-4) |

#### 8.3.6 驗證時學到的注意事項

- **衍生檔案會過期。** 第一次比較,改名後多了 4 個失敗,原因是工具沒有重新產生 reference inventory。已加入 RN-7。
- **驗證環境要對等。** 第一次比較中,改名後的副本是沒有忽略規則的 git repo,packaging 檢查把測試快取也算進去(3120 個檔案、48.3 MB),多出的失敗是驗證環境造成的,不是改名。兩份副本**必須**用相同的 exclude 規則。
- **不要用殘留的副本當來源。** 完整檢查中的 `ams_optional` 會把 plugin 複製到 `/tmp/hep research no ams …`,逾時時不會清除。改名的來源**必須**是已安裝或 repository 中乾淨的 plugin。
- **先確認版本是真的 release。** 以 `plugin_release()` 確認基準副本確實是已發布的 release;先前的「0.23.0」基準就是因此被發現其實是開發版(§0.2)。

---

## 9. 路線圖

### 9.1 第 0 期:基礎(release R1,估計 6–8 sessions)

- **前置條件:** DR-9、DR-11、DR-12、DR-13 已決定(DR-13 必須在第 1 期量測前決定)。
- **工作:**
  1. 版本守衛的機制:dispatch 以 (rule_id, version) 為鍵;generator 守衛;輸入檢查依 context 版本啟用(G18)。
  2. 函式層級的原始碼 digest;registry schema 1.1.0;`rule_registry.py check` 在 digest 改變但版本未變時失敗。
  3. checker 身分以執行時載入的模組為準;generator digest 涵蓋 `obligations.py`、`model.py`、`effect_catalog.py`(G10、A1)。
  4. P6:status 與 exit code 一致(G20)。
  5. snapshot 預設開啟:
     - snapshot 寫入 `<root>/.hep-research/snapshots/`;
     - freeze 把 bundle 路徑寫入 `<root>/.hep-research/bundles.json`;
     - `snapshots gc` 只刪除沒有被索引參照的 digest,預設 dry-run。
  6. `check-report` 的便宜拒絕條件:dependency-missing、`lock_differences`、預發布 suite、與 frozen inventory 不符(G11、G19 的診斷部分)。
  7. `assessment.plugin_release`。
  8. G21 分類。
  9. 補上 G11–G22 的 probe;變異測試骨架。
  10. 確認舊 release 的取得管道(git tag)。
  11. **程式代號改名(WP-R,只在 DR-15 採用時):** 以 `rename_analysis_check_ids.py` 執行 §8.3。**必須**在第 5 項之後,並與第 2 項在同一個 release 發布(RN-4)。
- **禁止事項:** **不得改變任何規則的 outcome。**
- **結束條件:**
  - V72–V76 通過;
  - 既有測試通過;
  - `run_all_checks.py` 全綠;
  - suite 1.0.0 在 R1 上的結果與 0.21 相同;
  - 若執行了第 11 項:RN-6 通過;
  - gate record 由計畫負責人確認。

### 9.2 第 1 期:證據(估計 4–10 sessions)

- **前置條件:** 第 0 期完成;DR-13 已決定並登記於 `decision-value-gate.md`。
- **工作:**
  1. 價值閘門(§10),使用手寫 bundle 與 suite 1.0.0(3–4 sessions)。
  2. 選用的探針(§12,0–4 sessions)。
  3. 保證平面的設計文件(1–2 sessions,並行)。
- **禁止事項:** 不得修改規則;不得事後調整門檻。
- **結束條件:** 閘門結果已記錄於 `decision-value-gate.md`。

### 9.3 決策點

計畫負責人依閘門結果決定**繼續、縮小或停止**(§13.3)。

### 9.4 第 2 期:診斷完成(release R2 → R3,估計 11–16 sessions,只在決定「繼續」時執行)

- **前置條件:** 決策點的決定為「繼續」;DR-1 至 DR-8 的待確認修訂已由計畫負責人確認。
- **工作:**
  - **R2:**
    - SemVer 預發布版本與 registry 唯一鍵;
    - check-context 1.1.0 與 context 轉換(V90);
    - calibration shape;
    - result binding 1.1.0;
    - G2–G8、G12、G13、G15–G17、G22 的修正,以 `1.1.0-dev.N` suite 發布。
  - **R3:**
    - G1、G14;
    - catalog 1.1.0;
    - 四個 suite 升為 1.1.0 stable;
    - 變異測試完整;
    - 入口(若 DR-14 通過,2–3 sessions)。
  - **G21:** 若第 0 期判定需要修正,另行決定與估計。
- **結束條件:** V77–V90(以及 V91,若適用)通過;shadow review 中 unclassified 為 0。

### 9.5 覆蓋擴充(逐項決定與估計)

O09、forward folding、per-sign ratio、eras、截面分析、完整的單位檢查(G22)、DR-10。

### 9.6 合計

| 範圍 | sessions |
| --- | --- |
| 到決策點(第 0 期 6–8 + 第 1 期 4–10) | 約 10–18 |
| 第 2 期 | 約 11–16 |
| 全部 | 約 21–34 |

### 9.7 每期共同的 gate

- 該期的 probe 與新 V case 通過;
- 既有測試通過,或修改的斷言逐項列在 VALIDATION;
- `tools/run_all_checks.py` 全綠;
- shadow review 中 unclassified 為 0;
- gate record 由計畫負責人確認。

---

## 10. 價值閘門規程(依 DR-13,待決)

| 步驟 | 內容 |
| --- | --- |
| 1. 對象 | ams-flux-ratio 的 spec 與 response,配上一份**如實描述其 TSVD unfolding** 的手寫 recipe:subtract_background → unfold → correct_efficiency → divide_exposure → divide_bin_width |
| 2. 定義造成的結果 | 以目前的 coverage,這份 recipe 會因 `trigger_efficiency` 而得到 4 個 `unrealized_correction`(Confirmed:`correct_efficiency` 只涵蓋 `selection_efficiency`,但程式同時除以兩者);改用 `divide_effective_exposure` 則得到 `incomplete`(O09)。**事先登記的處理:**<br>• 這類結果列入誤報組的「定義造成」類別;<br>• 另以一份列入兩個 members 的 bundle 自帶 coverage(會被標記 A3)跑一次,作為敏感度分析;<br>• 兩者都不算偵測 |
| 3. 錯誤分類 | 事先凍結,依類別而不是依規則;參考 T3、`crflux-review.md` 與已發表的勘誤 |
| 4. 植入 | 由非作者植入至少 20 個錯誤,每一個同時植入程式碼與描述;植入者不得看到規則。人選優先為 O04 所指的人;若暫時由另一個 agent 擔任,結果標示為「AI 植入」 |
| 5. 計分 | 逐層計分:closure 測試 → `validate.py` 與 L2 → checker(suite 1.0.0,於 R1 執行)。主要指標是 checker 的**增量偵測** |
| 6. 誤報組 | 合法的重構,加上第 2 步的「定義造成」類別 |
| 7. 成本 | 記錄每個手寫 bundle 的欄位數,以及哪些欄位理論上可以自動推導(DR-14 的依據) |
| 8. 可重現 | 量測腳本放進 repository |
| 9. 門檻 | 事先登記於 DR-13(`decision-value-gate.md`);量測後**不得**修改 |

**若 DR-13 不被採用:** 計畫停在第 0 期之後,不進入第 2 期。

---

## 11. 入口規格(依 DR-14,條件是價值閘門通過)

| 項目 | 規格 |
| --- | --- |
| 指令 | `analysis_check.py draft --root DIR --spec SPEC` |
| 會做的事 | 列出 items(spec、response、dataset-record、calibration);把 semantics table 複製進專案;指出 environment-lock 的來源;推導 scope axes |
| **不得做的事** | 自動寫入 roots、instances、bindings、declarations(一律寫成 `TODO`,P4、P10);掃描 run 記錄(run 記錄在 check 時以 `--results` 傳入);從 argv 推導 operator |
| freeze 的配合 | 拒絕任何 `TODO`;拒絕 unit 為空或佔位字的 root(G22 的最小修正) |
| skill 的導向 | 改動 `SKILL.md` 需要計畫負責人就 O16 做新決定 |
| 不在範圍內 | recipe 範本(只有 `cosmic_ray_flux` 宣告了 operators,對 TSVD 類的 recipe 沒有幫助) |

---

## 12. 有界的探針(依 DR-12,選用)

- **問題:** 在一條新的合成分析鏈上,只用有 contract 的工具,能不能從 run 記錄推導出 instance 與資料流?能省下多少手寫欄位?
- **上限:** 3–4 sessions;超出就停止,並記錄結果。
- **限制:** 不從 argv 推導 operator(`cosmic_ray_flux.json:76`:exposure 是否含 efficiency 是呼叫者的宣告)。

---

## 13. 治理

### 13.1 負責人

| 工作 | 負責人 |
| --- | --- |
| 計畫負責人;DR-9 至 DR-15 的決定;待確認修訂的確認;價值閘門結果的判定;gate record 的確認 | hchouTW(`decision-enforce.md` 指定的計畫負責人) |
| `decision-architecture.md`、`decision-value-gate.md` 的起草 | 實作者起草;計畫負責人填寫 Decision 段 |
| 價值閘門的執行與量測腳本 | 實作者 |
| WP-R 改名的執行與驗證 | 實作者;依 §8.3 與附錄 A.4 |
| 植入錯誤 | 待指定(O04);不得是規則作者 |
| 保證平面的設計文件 | 實作者起草;custodian 審閱(O17) |
| 非作者審查者、可接受報告的角色 | 待指定(O04、O14) |
| registry 中各規則的 `owner` | 維持現行的 skill 名稱;非作者審查前,`review_status` 一律為 `unreviewed` |

### 13.2 記錄慣例(D12b)

- decision record 寫定後**不得改寫**;變更以新的有日期段落記錄。
- 每個 gate 一份 `decision-<gate>.md`;本計畫新增 `decision-architecture.md` 與 `decision-value-gate.md`。

### 13.3 價值閘門的後果

| 結果 | 處置 |
| --- | --- |
| 通過 | 進入第 2 期;DR-14 依 §10 第 7 步的成本資料決定 |
| 縮小 | 只保留 chain 與 ratio suite 的修正;model-card、run-lineage、`custody.py` 依 §13.4 退場 |
| 停止 | 程式碼凍結;`--check-bundle` 保留但標為 experimental;skill reference 中的手動指引加上同樣的標示;不再新增 suite;第 0 期的成果保留(它們不改變規則) |

### 13.4 沒有呼叫者的元件,退場程序

- **觸發條件:**
  - 價值閘門判定縮小或停止;或
  - **決策點之後**,連續兩個 minor release 沒有任何非測試的呼叫者,也沒有 gate 使用。

  被指派到保證平面的元件(`check-report`、`custody.py`),在保證平面的設計決定之前不適用。
- **步驟:**
  1. 在一個 release 中標為 deprecated(CHANGELOG、README、相關 reference);
  2. 下一個 minor release 移除程式碼;
  3. 舊格式由讀者明確拒絕(維持 refusal matrix)。

### 13.5 shadow mode 的結束條件

任一規則要變成強制條件,以下**全部**都要成立:
- G-ENFORCE 的六項條件;
- 價值閘門通過;
- 非作者的人工審查完成(C15、O04);
- custodian 採用 gate requirement(O17);
- 允許接受報告的角色已決定(O14)。

這會改變 `decision-enforce.md` 的結束條件,所以**必須**以有日期的段落記錄。

---

## 14. 風險與未決事項

### 14.1 風險

| 風險 | 狀態 | 對策 |
| --- | --- | --- |
| 價值閘門由 AI 植入錯誤,仍有偏差 | 已知 | 優先由人植入;否則標示並在決策時打折看待 |
| 旗艦案例產生「定義造成」的違規 | Confirmed | §10 第 2 步的事先登記 |
| G21 需要修改 semantics table | Unresolved | 第 0 期分類;修改要另做決定 |
| 無關的定義變更造成 `lock_differences` | 已知 | 由預設開啟的 snapshot 吸收 |
| R2 中,suite 1.0.0 的部分規則給 `rule_not_run` | 預期中 | §8.2 的預設 suite 政策 |
| 舊 release 的取得 | Unresolved:m0-baseline 只記錄了 monorepo 中的 0.11.0 tag | 第 0 期確認 |
| 非作者的人工審查仍然缺少 | 已知 | §13.5 |
| 改名讓沒有 snapshot 的已凍結 bundle 無法重現 | Confirmed(RN-4) | 改名排在 snapshot 預設開啟之後,並與 registry 變更同一個 release |
| 實作開始時已安裝的版本與本文件的基準不同 | 已知(plugin 在 2026-10-22 一天內從 0.21 更新到 0.24.1) | §15 第 13 條:開始前重跑附錄 A.1 並確認版本 |

### 14.2 未決事項

| 項目 | 何時處理 |
| --- | --- |
| G21 的性質與修正成本 | 第 0 期 |
| 舊 release 的取得 | 第 0 期 |
| 植入錯誤的人、非作者審查者 | 第 0 期(O04) |
| member-set closure digest 是否包含 `catalog_version` | 第 2 期升 catalog 之前 |
| 「規則到定義」的對應表 | 不排入;有需要時另行提案 |
| 完整的單位一致性檢查(G22) | 覆蓋擴充 |
| `unfold`、`correct_efficiency` 沒有有 contract 的工具 | 覆蓋擴充 |
| 分析者帳號的來源;`read_protected` 的效能與 Windows 行為 | 保證平面設計 |

---

## 15. Agent 作業規則

執行本計畫的 agent(包括 Claude)**必須**遵守以下規則:

1. **先查決定狀態。** 開始任何工作前,檢查 §7:相關的 DR 若為「待決」或「待確認」,只能做準備工作或提出草稿,**不得**實作被它影響的部分。
2. **不改寫記錄。** 對 `docs/dev/v6.3/decision-*.md`(改名後為 `docs/dev/cross-artifact-check/decision-*.md`)等記錄,只新增有日期的段落;Decision 段由計畫負責人填寫,agent **不得**代填。
3. **第 0 期不改規則。** 第 0 期的任何變更,都**不得**改變 suite 1.0.0 的規則 outcome;以「suite 1.0.0 在 R1 與 0.21 上結果相同」驗證。
4. **規則變更必須升版。** 改變 outcome 的規則修正,**必須**提升該規則的版本,並經由預發布 suite 發布(P3)。
5. **不自動寫入意圖。** 任何工具**不得**自動產生 check-context 的 roots、instances、bindings、declarations(P4、P10)。
6. **報告只是診斷。** 回報 checker 結果時,**必須**說明它是 advisory,**不得**表述為授權或通過(P1)。
7. **先重現,再修正。** 修正任一缺口前,先讓它的 probe 失敗;修正後讓它通過;不得只改斷言。
8. **不事後改門檻。** 價值閘門的門檻,量測後**不得**修改。
9. **保證平面只寫設計。** 在 §5.1 的前提成立之前,**不得**實作保證平面的功能。
10. **不改受保護區域。** **不得**修改 `core/partition/`、`core/protected/`,以及 permit 與 attestation 的 schema。
11. **標明證據等級。** 文件與回報中的陳述,使用 Confirmed、Inferred、Unresolved 標記,並附上證據。
12. **改名只用工具。** 程式代號改名**必須**使用 `rename_analysis_check_ids.py` 並遵守 §8.3.3 的 RN-1–RN-7;**不得**手動或以全域替換的方式改名。
13. **開始前確認基準。** 實作開始前,在當時已安裝的版本上重跑附錄 A.1,並以 `plugin_release()` 確認它是已發布的 release;結果與 §0.2 不同時,先更新本文件(§0.2、§1、§8.1),再開始實作。

---

## 16. 文件地圖與去留

### 16.1 本計畫的工作文件(scratchpad)

| 文件 | 狀態 |
| --- | --- |
| `final/cross-artifact-check-architecture.zh.md`(本文件,中文) | **有效** |
| `final/cross-artifact-check-architecture.en.md`(英文) | **有效**,與本文件內容一致 |
| `final/test_cross_artifact_check_gap_probes.py` | **有效**;目前涵蓋 G1–G10,第 0 期補上 G11–G22 |
| `final/rename_analysis_check_ids.py` | **有效**:WP-R 的改名工具(§8.3.4);交付時放入 plugin 的 `tools/` |
| `final/cross-artifact-check-decision-rationale.zh.md` | **理由附錄**:證據與推理可參考,但**不得直接貼用其中的 Decision 文字**。已被推翻的說法:DR-5「只需要可用性」、DR-1「S2 以上自動成為事實」、DR-3 用 bytes digest、DR-6 的 1e-12 與單純的 k、DR-7「只有標籤」那一列、DR-8 的 root 覆蓋 |
| `archive/plans/cross-artifact-check-architecture-pre-cleanup-2.zh.md`、`.en.md` | 已取代(本次整理前的同內容版本) |
| `archive/plans/cross-artifact-check-architecture-pre-restructure.zh.md` | 已取代(第一次整理前的同內容版本,含兩次審查的完整處置表) |
| `archive/plans/cross-artifact-check-plan-v2.zh.md`(v2) | 已取代;保留 §12 的審查記錄 |
| `archive/plans/cross-artifact-check-plan-v3.1.zh.md`、`-en.md` | 已取代;保留 §11 的審查記錄;若 DR-11 不被採用,其 WP1、WP6 重新成為依據 |
| `archive/plans/cross-artifact-check-architecture-rethink.zh.md` | 已取代;保留 §9 的審查記錄 |
| `archive/evidence/`(`review/`、`review3/`–`review6/`、`probe*.py`、`proto_*.py`、`usage.py`) | 保留:重現腳本。執行時從 plugin 根目錄執行,並把 `PYTHONPATH` 指向腳本所在的資料夾;`review5/callers.py` 需要以根目錄為參數;`review6/p6_scope.py` 只能在拋棄式副本中執行 |
| `archive/evidence/rename/`(`compare.py`、`lockprobe.py`) | 保留:WP-R 的重現腳本(附錄 A.4) |
| `v241/`(`pristine/`、`proto/`、`lockp/`) | 保留到第 0 期開始:0.24.1 的乾淨快照與 §8.3.5 的驗證副本與輸出 |
| `rename-proto/` | 保留到第 0 期開始:在 0.23.0 之後的開發版上的第一次改名驗證(含抓到 RN-7 的比較) |
| `hr/`(plugin 副本) | 保留到第 0 期開始;0.21.0 的副本,不是乾淨的副本(含 probe 測試;`plugin_release()` 回傳 `unreleased`) |

### 16.2 plugin 中的文件(建議;尚未修改)

若 DR-15 採用,下列 `docs/dev/v6.3/` 的路徑改為 `docs/dev/cross-artifact-check/`。

| 文件 | 建議 |
| --- | --- |
| `docs/dev/v6.3/README.md` | 新增本架構與兩份新 decision record 的索引 |
| **新增** `decision-architecture.md` | DR-1 至 DR-15 的現況與理由;每一項一個 Decision 段;取代 v3.1 提議的 `decision-hardening.md` |
| **新增** `decision-value-gate.md` | DR-13 的設計與事先登記的門檻;量測後記錄結果與決定 |
| `decision-enforce.md` | 原文不改;新增有日期的段落:結束條件加入價值閘門;以本文件的期別取代原本的 stacked-PR 計畫 |
| `decision-m2a.md`、`m2a-design.md` | 原文不改;新增有日期的段落:DR-2 移除 `root_not_required`;版本守衛;P6 |
| `decision-m0.md`、`decision-m2b.md` | 不改 |
| `m2b-model-design.md` | 新增有日期的段落:G5、G12 |
| `m2c-design.md`、`m2c-proposal.md` | DR-11 確認後,新增有日期的段落:DR-1、DR-7 的變更 |
| `custodian-gate-requirement.md` | 新增有日期的段落:保證平面的位置、與審查報告的比對、`check-report` 的重新定位 |
| `review-packet.md` | 新增有日期的段落:對抗式審查(執行 probe 與變異測試) |
| `o16-agent-interface.md` | 新增有日期的段落;改動 `SKILL.md` 需要新決定 |
| `refusal-matrix.md`、`shadow-review.md` | 格式變更時,以有日期的段落重新量測 |
| `m0-baseline.md`、`m0-budget.md`、`o03-model-pairings.md`、`crflux-review.md` | 不改 |
| plugin `README.md`(第 275–312 行) | 註明診斷平面與目前的使用狀況 |
| `docs/protected-data-architecture.md` | 加入保證平面在 formal-use gate 中的位置;更正第 556 行過時的「four contracts」(目前有 9 份) |

---

## 17. 演進與審查摘要

| 階段 | 結果 | 被推翻或修正的關鍵 |
| --- | --- | --- |
| 兩輪程式碼檢查 | 找到 10 個缺口,寫成 probe | — |
| 方案 v1 → v2(第 1 次獨立審查) | 18 個缺口;新增前置工作包 | 把已核准的決定當成 bug;低估相容性代價 |
| 決策研究 DR-1–8 | 提出「信任看保管」 | DR-3、DR-6、DR-7、DR-8 的初步建議被推翻 |
| 方案 v3 → v3.1(第 2 次獨立審查) | 新增 G19 | snapshot 可偽造;專案內的檔案不可能受保護;`1.1.0-dev` 不合法 |
| 架構再思考 v1 → v2(第 3 次獨立審查) | 兩個平面;價值閘門 | 描述模型是刻意的;執行橋不可行;閘門有循環性 |
| 使用狀況盤點 | checker 沒有被真實流程執行 | — |
| 最終架構(第 4、5 次獨立審查) | 單一架構;G20–G22;治理 | 入口不得自動寫入意圖;第 0 期不改規則;P6 改為與 exit 一致;G22 降為最小修正 |
| 程式代號改名(WP-R,DR-15) | 改名工具;安全規則 RN-1–RN-7 | 第一次比較抓到 reference inventory 過期(新增 RN-7)。在 0.23.0 之後的開發版上的比較:4859 個測試、共同失敗 16 個、改名後才失敗的 0 個;唯一的單側失敗是計時型測試 `test_scaling_check_rejects_a_quadratic_scan`,兩邊各重跑 5 次全部通過,記為不穩定 |
| 依 0.24.1 複核 | 事實、相容性、測試與 lock 結果全部不變;改名的完整檢查前後完全相同 | 先前的「0.23.0」基準其實是未發布的開發版;`plugin_release` 自 0.24.0 起在已安裝副本上回傳版本 |
| 第二次結構整理 | 新增一頁摘要、量測基準表、ID 族群表;§8.3 分成六節;附錄 A 改為步驟 | 改名安全規則從 R-1–R-7 改稱 RN-1–RN-7,避免與 release R1–R3 混淆;內容不變 |

**限制:** 五次審查的審查者都是 AI;C15 所要求的非作者人工審查(O04)仍然需要。完整的審查處置表見 `archive/plans/` 中各文件的審查記錄。

---

## 附錄 A:重現證據

所有指令都從 plugin 根目錄執行,除非另有註明。

### A.1 基線(§15 第 13 條)

1. `python3 -c "import sys; sys.path.insert(0, '.'); from core.protected import identity; print(identity.plugin_release())"`:應回傳已發布的版本,而不是 `unreleased`。
2. `python3 -m unittest discover -s tests/contracts -t . -p 'test_v63_*.py'`:205 個既有測試通過(改名後改用 `-p 'test_analysis_check_*.py'`)。
3. `python3 contracts/rule_registry.py check`:pass;23 條規則、71 個 V case。

### A.2 probe 測試

1. 把 `final/test_cross_artifact_check_gap_probes.py` 放到 plugin 的 `tests/contracts/`。
2. 執行 `python3 -m unittest tests.contracts.test_cross_artifact_check_gap_probes -v`。

目前 10 項全部失敗,這是預期的結果:每一項 probe 描述的是「應有的行為」。

### A.3 審查腳本

執行 `PYTHONPATH=<腳本所在資料夾> python3 <腳本>`;個別限制見 §16.1 的 `archive/evidence/` 列。

### A.4 改名驗證(WP-R)

1. **取得乾淨的來源:** 已安裝或 repository 中的 plugin;**不得**使用 `/tmp/hep research no ams …` 之類的殘留副本(§8.3.6)。
2. **建立兩份副本**(改名前、改名後):移除根目錄的 `.in_use/` 與所有 `__pycache__`;各自 `git init`;在 `.git/info/exclude` 寫入 `__pycache__/`、`*.pyc`、`.pytest_cache/`、`.hypothesis/`、`.DS_Store`、`/.in_use/`;`git add -A` 並 commit。
3. **dry-run:** 在改名後的副本執行 `python3 rename_analysis_check_ids.py .`,確認 23 項移動、所有來源存在、所有目標不存在。
4. **執行:** `python3 rename_analysis_check_ids.py . --apply --date YYYY-MM-DD`;輸出的 `status` 必須是 `ok`。
5. **冪等:** commit 後再執行一次第 4 步,`git status --porcelain` 必須為空。
6. **受保護的檔案:** `git diff -M --name-status HEAD~1` 中,RN-2 列出的檔案只能以 R100 出現(純移動)。
7. **完整檢查:** 兩份副本各執行一次 `python3 tools/run_all_checks.py --out DIR`(每次約 32 分鐘;依序執行,不要並行,以免計時型測試受影響)。
8. **比較:** `python3 archive/evidence/rename/compare.py OUT_BEFORE OUT_AFTER`:把改名前的測試 ID 以工具的對照規則換成新名稱,再比較 check 狀態、失敗集合與計數。
9. **單側失敗:** 只在一邊出現的失敗,在兩邊各重跑 5 次;兩邊都全部通過時記為不穩定(RN-6)。
10. **lock 影響:** `python3 archive/evidence/rename/lockprobe.py BEFORE_TREE AFTER_TREE`(需以 `git archive` 匯出的乾淨樹):預期沒有 snapshot 時 13 項 `semantics_unreproducible`,有 snapshot 時 complete(RN-4)。

## 有日期的附註（退場）

本架構描述的是 2026-10-22（0.24.1）時的 checker。之後的發展：第 0 期在 0.25.0 發布；價值閘門兩次量測都是 I = 0／28；
Shrink 在 0.28.0 移除了 `model-card` 與 `run-lineage`；`decision-retire.md` 提議讓其餘部分退場，規則改寫為
hep-measurement 與 hep-statistics 中的審查問題，經由 hep-review 使用。用語：R0–R3 現在指 hep-review 的保證等級；
本文所稱的 release R1–R3 即 0.25.0 與 0.26.0。本附註不改寫以上各節。
