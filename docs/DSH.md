# DeepSeek Harness (DSH) 安装说明

## 安装方式

- **方式 A（界面导入）**：若已安装 Skill Manager 插件，在 DSH 的 **Settings → Skills → Import ZIP** 中导入对应压缩包，选择安装到全局或当前工作区。
- **方式 B（手动解压）**：将包内的 `.dsh/skills/game-localization/` 复制到全局目录 `~/.dsh/skills/game-localization/`（或 `~/.agents/skills/game-localization/`），或放到单个工作区的 `<workspace>/.dsh/skills/game-localization/`。

确保最终路径为 `.../skills/game-localization/SKILL.md`。

## 使用建议

- 将技能目录视为只读参考源，所有候选产物、脚本与临时文件写入当前任务工作区。
- 在 DSH 中生成或检查 XLSX 校对表、DOCX 手误记录时，可配合内置 `office-xlsx`、`office-docx`、`office-render` 技能与 `load_workspace_dependencies` 提供的 Python 环境。
- 首次使用可运行自检：
  ```sh
  python3 ~/.dsh/skills/game-localization/scripts/localization_toolkit.py doctor
  python3 ~/.dsh/skills/game-localization/scripts/toolkit_selftest.py
  ```
