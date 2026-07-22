# sdd-workflow

> 版本 v0.1.0 ｜ [English](./README.en.md)

一份跨 AI coding agent 共用的 **SDD（Spec-Driven Development，規格驅動開發）** skill。核心理念一句話：**動手寫程式之前，先把要做什麼寫清楚、讓人確認，再開始做。**

它把每個需求切成三個階段，各階段結束都會停下來等你確認，不會一路暴衝：

| 階段 | 觸發詞 | 做什麼 |
| --- | --- | --- |
| 1. 提案 | `提案` | 取短名稱、判斷類型（新功能／修 bug／重構），產出 `sdd/<短名稱>/proposal.md` 與 `tasks.md`，然後**停下等確認，不寫程式** |
| 2. 實作 | `實作` / `開始實作` | 逐條完成 `tasks.md`，一次一條、做完打勾回報；發現規格不對就停下來問 |
| 3. 歸檔 | `歸檔` | 確認全部打勾後，把 `sdd/<短名稱>/` 移到 `sdd/archive/<日期>-<短名稱>/` |

產出物都是純文字，留在你的專案 `sdd/` 目錄，跟著 git 一起版控。

**這個 repo 唯一維護的流程來源是 [`skills/sdd-workflow/SKILL.md`](./skills/sdd-workflow/SKILL.md)。** 安裝到各工具的副本只是可重新產生的安裝產物，不是第二份來源。

## 支援的工具與觸發語法

| 工具 | 顯式觸發 | 也可自然語言觸發 |
| --- | --- | --- |
| [Claude Code](https://claude.com/claude-code)（Anthropic） | `/sdd-workflow 提案 …` | 直接說「提案：…」／「開始實作」／「歸檔」 |
| [Codex](https://github.com/openai/codex)（OpenAI/GPT） | `$sdd-workflow 提案 …` | 直接說「提案：…」／「開始實作」／「歸檔」 |

顯式語法是首選（明確、可預期）；自然語言觸發是便利功能，靠模型依 skill 描述自動選用。

> Skill 指令本體為英文（利於跨工具維護），但**觸發詞與對你的輸出維持繁中**。

## 使用方式

安裝後，建議在**新的對話／session** 用顯式語法開始，確認工具真的載入了 skill：

```text
# Claude Code
/sdd-workflow 提案 建立一個測試文字檔

# Codex
$sdd-workflow 提案 建立一個測試文字檔
```

正常流程會分三步走：

1. **提案**：agent 只會建立 `sdd/<短名稱>/proposal.md` 與 `sdd/<短名稱>/tasks.md`，然後停下來等你確認。這一步不應該修改產品程式碼。
2. **實作**：你看完提案後，明確回覆「開始實作」或「實作」。agent 會一次完成 `tasks.md` 的一條任務，做完打勾並回報；如果發現規格不對，應停下來問。
3. **歸檔**：你驗收完成後，回覆「歸檔」。agent 會確認 tasks 全部完成，再把 `sdd/<短名稱>/` 移到 `sdd/archive/<日期>-<短名稱>/`。

自然語言也可觸發，例如「提案：建立一個測試文字檔」。若工具沒有自動選到 skill，請改用上表的顯式語法。

## 安裝

以下三種通路擇一。各通路的目的地由該安裝工具自己管理，本 repo 不提供面向一般使用者的自製 installer。

### 1. Codex 原生（內建 skill-installer）

在 Codex 對話中請它從本 repo 安裝：

```
$skill-installer 從 GitHub 安裝 kurotanshi/sdd-workflow 的 skills/sdd-workflow
```

底層等同 `install-skill-from-github.py --repo kurotanshi/sdd-workflow --path skills/sdd-workflow`，會裝進 `~/.codex/skills/sdd-workflow/`，並在**下一個 turn** 生效。

### 2. 跨 agent Skills CLI（第三方）

[`npx skills`](https://skills.sh/) 是開放 agent skills 生態的套件管理器，可一次餵給多種 agent：

```bash
npx skills add kurotanshi/sdd-workflow --skill sdd-workflow -g -y
```

`-g` 裝在使用者層、`-y` 略過確認。安裝來源會記錄在該工具的 lock file。

> ⚠️ **這是第三方工具（skills.sh），不是 OpenAI 或 Anthropic 官方 installer。** 它把 skill 放進共用的 `~/.agents/skills/`。**請自行確認你的 agent 真的會載入該目錄**——不同工具讀取的 skill 路徑不同（例如 Codex 內建工具鏈使用 `~/.codex/skills`）；若沒被載入，請改用通路 1 或 3。

### 3. 手動複製（fallback）

把**整個 `skills/sdd-workflow/` 資料夾**（含 `agents/`，不是只複製 `SKILL.md`）放到你的工具支援的使用者層 skills 目錄：

```bash
# Claude Code（v2.1.203+ 亦支援 symlinked skill）
cp -R skills/sdd-workflow ~/.claude/skills/sdd-workflow

# Codex
cp -R skills/sdd-workflow ~/.codex/skills/sdd-workflow
```

## 更新與移除

| 通路 | 更新 | 移除 |
| --- | --- | --- |
| Codex skill-installer | 先刪 `${CODEX_HOME:-$HOME/.codex}/skills/sdd-workflow` 再重裝（installer 遇既有目錄會中止） | 刪除 `${CODEX_HOME:-$HOME/.codex}/skills/sdd-workflow` |
| Skills CLI（第三方） | `npx skills update sdd-workflow -g -y` | `npx skills remove sdd-workflow -g -y` |
| 手動複製 | 先刪舊資料夾，再重新複製完整 `skills/sdd-workflow/` | 刪除你複製的資料夾 |

## 作者／貢獻者：本機開發

若你要**修改這個 repo 的 skill** 並即時生效，用 dev-link 腳本把 repo 的 canonical skill 資料夾 symlink 進工具的 skills 目錄（**這是作者工具，不是一般使用者的安裝方式**）：

```bash
scripts/link-dev.sh                # link 進 Claude Code 與 Codex
scripts/link-dev.sh --claude-only  # 只 Claude
scripts/link-dev.sh --codex-only   # 只 Codex
scripts/link-dev.sh --unlink       # 移除本 repo 建立的 dev link
scripts/link-dev.sh --help
```

它只在**目的地不存在**時建立 symlink，只移除**解析後正好指向本 repo** 的 symlink；遇到其他既有檔案／目錄／symlink 一律停止不動。目標目錄可用 `CLAUDE_SKILLS_DIR`、`CODEX_SKILLS_DIR` 覆寫（供 hermetic 測試或指定已驗證的 Codex skill root）。

> symlinked skill 在使用前，請分別在 Claude Code 與 Codex 的**新 session** 確認真的被載入。

## 致謝

本 repo / skill 受到 @kaochenlong 在 2026 AI 年會分享的 [SimpleSDD](https://gist.github.com/kaochenlong/27ade9a6218244c2584777fa276d1214) 啟發。

## License

MIT（見 [LICENSE](./LICENSE)）
