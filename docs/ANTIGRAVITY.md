# Antigravity 安装说明

## 安装方式

- **全局安装（所有工作区生效）**：将包内的 `skills/game-localization/` 复制到 `~/.gemini/config/skills/game-localization/`。
- **项目级安装（随仓库共享）**：将 `game-localization/` 复制到项目根目录的 `.agents/skills/game-localization/`。

确保最终路径包含 `SKILL.md`、`references/` 与 `scripts/`。

## 使用建议

- 技能目录保持只读，输出与候选文件写入当前工作区（或默认 scratch 目录）。
- 导出 `gtf-preview`、字形接触表或 UI 重绘对比图后，可直接用 `read_file` 目视验收 PNG。
- 大批量独立文件盘点或跨模块排查可结合 subagent / workflow 并行处理；哈希、token 与容器往返校验仍交给 Python 脚本。
- 首次使用可运行自检：
  ```sh
  python3 ~/.gemini/config/skills/game-localization/scripts/localization_toolkit.py doctor
  python3 ~/.gemini/config/skills/game-localization/scripts/toolkit_selftest.py
  ```
