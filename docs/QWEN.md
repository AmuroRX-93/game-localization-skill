# Qwen Code 安装与使用

本技能支持日文或英文游戏译为中文。这里指通义的 Qwen Code 编程工具；普通聊天界面能否执行工程取决于其文件和脚本能力。

1. 解压总包，打开 `04-Qwen-Code`；或解压单独的 Qwen 包。
2. 将其中 `.qwen/skills/game-localization` 文件夹放到你的汉化项目内，最终文件为 `项目/.qwen/skills/game-localization/SKILL.md`。
3. 在该项目中开始 Qwen Code 新会话，使用 `/skills` 查看技能列表，再用 `/game-localization` 调用。模型也可按相关性自动使用。

示例：

> /game-localization 检查这个日文游戏的现有汉化。先核对加载版本，列出按键说明、菜单贴图与字幕的覆盖情况，不要调整模拟器设置。

需要所有项目共享时，放到用户主目录 `~/.qwen/skills/game-localization/`。项目级和用户级任选一种，已有同名技能先比较差异，不覆盖定制内容。

macOS Finder 用 `Command+Shift+.` 显示隐藏文件夹。Windows 的 `~` 表示用户主目录。仅复制本技能，不替换整个 `.qwen` 设置目录。

保留完整技能文件夹；检查器需要 Python 3.9+。不修改模型、API 配置或执行权限。

已核对目录、入口和完整性；尚未在 Qwen Code 客户端内验证加载和执行。

依据：[Qwen Code 官方 Skills 文档](https://github.com/QwenLM/qwen-code/blob/main/docs/users/features/skills.md)，查阅于 2026-09-20。
