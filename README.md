# sdd-workflow

一組跨 AI coding agent 共用的 **SDD（Spec-Driven Development，規格驅動開發）** slash commands。

核心理念只有一句：**動手寫程式之前，先把要做什麼寫清楚、讓人確認，再開始做。**

把需求拆成三個階段，每個階段都是一支指令，各自結束時都會停下來等你確認，不會一路暴衝：

| 階段 | 指令 | 做什麼 |
| --- | --- | --- |
| 1. 提案 | `/propose <需求描述>` | 取短名稱、判斷類型（新功能/修 bug/重構），產出 `sdd/<短名稱>/proposal.md` 與 `tasks.md`，然後**停下等確認，不寫程式** |
| 2. 實作 | `/implement [短名稱]` | 逐條完成 `tasks.md`，一次只做一條、做完打勾回報；發現規格不對就停下來問 |
| 3. 歸檔 | `/archive [短名稱]` | 確認全部打勾後，把 `sdd/<短名稱>/` 搬到 `sdd/archive/<日期>-<短名稱>/` |

產出物都是純文字，留在你的專案 `sdd/` 目錄裡，跟著 git 一起版控。

## 支援的工具

| 工具 | 安裝位置 | 說明 |
| --- | --- | --- |
| [Claude Code](https://claude.com/claude-code)（Anthropic） | `~/.claude/commands/*.md` | 保留 YAML frontmatter（`description` / `argument-hint`） |
| [Codex](https://github.com/openai/codex)（OpenAI/GPT） | `~/.codex/prompts/*.md` | 安裝時自動去除 frontmatter，避免當成純文字送進 prompt |

兩邊的指令主體完全相同，都靠 `$ARGUMENTS` 帶入需求描述，所以同一份規格檔在哪個工具都能接續。

## 安裝

```bash
git clone https://github.com/kurotanshi/sdd-workflow.git
cd sdd-workflow
./install.sh
```

只裝其中一個工具：

```bash
./install.sh --claude-only
./install.sh --codex-only
```

其他選項：

```bash
./install.sh --force        # 覆蓋既有檔案（會先備份成 *.bak）
./install.sh --help
```

自訂安裝目錄：

```bash
CLAUDE_COMMANDS_DIR=/somewhere CODEX_PROMPTS_DIR=/elsewhere ./install.sh
```

裝好後，在任一工具輸入 `/propose`、`/implement`、`/archive` 即可。

## 手動安裝

如果不想用腳本：

- **Claude Code**：把 `commands/*.md` 直接複製到 `~/.claude/commands/`。
- **Codex**：把 `commands/*.md` 複製到 `~/.codex/prompts/`，並自行刪掉檔案最上方 `---` 之間的 frontmatter 區塊。

## 一個典型流程

```
/propose 幫待辦清單加上「標記完成」功能
   → 產出 sdd/mark-todo-done/proposal.md 與 tasks.md，停下等你確認

（你看過覺得 OK）

/implement
   → 逐條完成 tasks.md，每條做完打勾回報

（你驗收成果沒問題）

/archive
   → 搬到 sdd/archive/2026-07-22-mark-todo-done/，並一句話總結
```

## License

MIT
