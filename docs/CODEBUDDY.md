# CodeBuddy 安装与使用

本技能支持日文或英文游戏译为中文，适配腾讯 CodeBuddy Code 的文件型 Skills。

1. 解压总包，打开 `05-CodeBuddy`；或解压单独的 CodeBuddy 包。
2. 将其中 `.codebuddy/skills/game-localization` 文件夹放到汉化项目内，最终文件为 `项目/.codebuddy/skills/game-localization/SKILL.md`。
3. 在该项目开始新会话，用 `/skills` 确认已发现 `game-localization`，然后明确要求使用它。模型可按任务和技能说明自动选择。

示例：

> 使用 game-localization 技能处理这个英文游戏的汉化。先检查实际资源、控制码和字库支持，再做少量文本抽取与回填验证，不要发布。

也可装到用户主目录 `~/.codebuddy/skills/game-localization/` 供所有项目使用。只选择一种安装范围；已有同名技能先比较修改，不直接覆盖。

macOS Finder 用 `Command+Shift+.` 显示隐藏文件夹。Windows 的 `~` 表示用户主目录。仅复制本技能，不替换整个 `.codebuddy` 设置目录。

完整文件夹包含参考资料及依赖 Python 3.9+ 的只读检查器。本包无需 Hooks、MCP 或全局规则，不修改模型和工具权限。

已核对目录、发现入口和完整性；尚未在 CodeBuddy 客户端内验证加载和执行。

依据：[CodeBuddy 官方 Skills 文档](https://www.codebuddy.ai/docs/cli/skills)，查阅于 2026-09-20。
