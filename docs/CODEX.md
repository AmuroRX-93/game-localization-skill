# Codex／通用包安装

支持日文或英文游戏译为中文。把这里的整个 `game-localization` 文件夹放到 `~/.codex/skills/`；配置了 `CODEX_HOME` 时，使用该目录下的 `skills/`。

最终入口为 `skills/game-localization/SKILL.md`，不要只复制单个 Markdown 文件。已有同名技能先比较差异，不覆盖个人修改。新会话中使用：

> 使用 $game-localization 处理这个游戏的汉化。先核对版本、原文语言和资源，建立覆盖清单，再完成本轮指定任务。

Skill 已在作者本机被 Codex 识别。检查脚本需要 Python 3.9+；安装技能不等于任何游戏已经通过汉化验证。

其他文件型 Skill 工具可将同一完整文件夹放到它们约定的技能目录；`agents/openai.yaml` 为 Codex 界面信息，核心流程和脚本不依赖它。
