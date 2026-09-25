# Cursor 安装与使用

本版支持日文或英文游戏译为中文。Cursor 原生识别 `SKILL.md`，因此沿用同一份 Skill 内容，不另写一套容易过期的规则，也不需要把全文设成始终生效。

## 推荐：安装到汉化项目

1. 打开总包的 `02-Cursor` 文件夹，或下载 Release 附件 `game-localization-cursor-v0.4.0.zip` 并解压。
2. 包中有 `先看这里.md` 和 `.cursor/skills/game-localization/`。把这个 `game-localization` 文件夹放到你项目的 `.cursor/skills/` 下；已有同名文件夹先比较差异，不覆盖自行修改的版本。
3. 用 Cursor 打开该项目，在 Agent 聊天中输入 `/`，搜索并选择 `game-localization`，再描述任务。
4. 如果没发现技能，重新打开项目或新建会话，并检查路径是否多套了一层。可在 Customize → Skills 检查发现状态；界面入口以所用版本为准。

macOS 默认隐藏 `.cursor` 文件夹，在 Finder 中按 `Command+Shift+.` 可显示；Windows 可在资源管理器打开该文件夹。

最终结构：

```text
你的游戏项目/
└── .cursor/
    └── skills/
        └── game-localization/
            ├── SKILL.md
            ├── LICENSE
            ├── references/
            └── scripts/
```

例如：

> /game-localization 这是一个英文游戏的汉化项目。先核对版本和当前资源，按英文原文与中文并列输出一个校对表小样；保留变量和稳定 ID，暂时不要修改游戏文件。

> /game-localization 这是一个日文游戏的汉化移植。先核对实际加载的资源，调查按键说明缺字；不要调整模拟器画面或手柄设置。

## 全局安装（另一种选择）

如果希望多个项目使用，可把同一文件夹放到 `~/.cursor/skills/game-localization/`，Windows 对应用户主目录里的 `.cursor/skills/game-localization/`。项目级与全局安装选择一种即可。

当前 Cursor 也兼容 Codex 技能目录；已经通过该目录发现此技能时，不必再重复安装。个人技能用于云端时另有同步设置，本包不会自动上传本机文件。

## 工具与权限

正文和检查器不绑定模型。检查脚本需要 Python 3.9+，使用 Cursor Agent 可用的终端运行；权限仍由 Cursor 和用户控制。不配置自动执行、全局规则、MCP 或付费服务。

本包按官方文件格式和目录约定制作，已校验文件完整性及脚本；尚未在 Cursor 客户端内实测自动发现或完成游戏汉化。项目为方法和工具，不保证任意模型的语言质量或逆向能力。

官方依据：[Cursor Agent Skills](https://cursor.com/docs/skills)（查阅于 2026-09-20）。本说明使用本地文件安装，不要求通过 GitHub 插件市场导入。
