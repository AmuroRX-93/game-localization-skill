# Kimi Code 安装与使用

本技能用于日文或英文游戏译为中文，包含完整流程、参考资料和清单检查器。适配对象是支持文件型 Skill 的 Kimi Code CLI，不等于普通 Kimi 网页聊天能自动执行本机工程。

1. 解压总包，打开 `03-Kimi-Code`；或解压单独的 Kimi 包。
2. 将其中 `.kimi-code/skills/game-localization` 文件夹复制到用户主目录的 `.kimi-code/skills/`，最终文件为 `~/.kimi-code/skills/game-localization/SKILL.md`。
3. 如果设置了 `KIMI_CODE_HOME`，改放该目录下的 `skills/game-localization/`。已有同名技能先比较修改，不直接覆盖。
4. 开始新会话，输入 `/skill:game-localization` 并附上任务。模型也可按相关性自动调用。

示例：

> /skill:game-localization 将这个英文游戏的文本整理成英文原文与中文并列表格。先核对版本、资源和稳定 ID，给我五条真实内容的小样，暂时不回填游戏。

只在单个项目使用时，也可以放到项目根目录的 `.kimi-code/skills/game-localization/`；官方以向上查找最近的 `.git` 目录确定项目根目录，不确定时用上述用户级路径。不要同时安装多份同名技能。

macOS Finder 用 `Command+Shift+.` 显示隐藏文件夹。Windows 的 `~` 表示用户主目录，按目录结构复制即可。仅复制本技能，不替换整个 `.kimi-code` 设置目录。

保留整个技能文件夹，脚本依赖 Python 3.9+。模型、账户、权限和工具仍由 Kimi Code 管理，本包不会修改它们。

已核对目录、入口和完整性；尚未在 Kimi Code 客户端内验证加载和执行。

依据：[Kimi Code 官方 Skills 文档](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/skills.html)，查阅于 2026-09-20。
