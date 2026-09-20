# 不同助手的兼容范围

本 Skill 不绑定模型。模型负责理解和推理，编程助手负责发现 Skill、读写文件和执行工具；两者应分别判断。日文与英文译为中文都在本版工作流程范围内，实际质量仍需审校。

下表依据官方文档于 2026-09-20 核对，只表示相应工具有文件型 Skill 机制，不表示本项目已经在这些工具中逐个实测。

| 工具 | 安装目录示例 | 本项目验证状态 |
|---|---|---|
| Codex | `~/.codex/skills/game-localization/` | 已在作者本机安装并被会话识别 |
| Cursor | 项目内 `.cursor/skills/game-localization/` 或 `~/.cursor/skills/game-localization/` | 有专用目录包，客户端内未实测 |
| Kimi Code | `~/.kimi-code/skills/game-localization/`；设置 `KIMI_CODE_HOME` 时使用其下的 `skills/` | 官方机制核对，未实测 |
| Qwen Code（通义） | `.qwen/skills/game-localization/` 或 `~/.qwen/skills/game-localization/` | 官方机制核对，未实测 |
| CodeBuddy（腾讯） | `.codebuddy/skills/game-localization/` 或 `~/.codebuddy/skills/game-localization/` | 官方机制核对，未实测 |

给国产工具使用时，下载通用包，保留完整 `game-localization` 文件夹，按该工具目录约定安装。`agents/openai.yaml` 是 Codex 界面元数据，核心说明、参考资料与 Python 脚本不依赖它。工具无法加载技能时，可以显式要求它读取 `SKILL.md` 及相关参考，但这不等于自动发现已成功。

普通网页聊天模型可参考文档；只有具备所需文件和脚本工具的运行环境，才能执行抽取、回填和检查。不要将某模型的 API 能力等同于某个聊天产品支持安装技能。

官方资料：

- [Cursor Skills](https://cursor.com/docs/skills)
- [Kimi Code Skills](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/skills.html)
- [Qwen Code Skills](https://github.com/QwenLM/qwen-code/blob/main/docs/users/features/skills.md)
- [CodeBuddy Skills](https://www.codebuddy.ai/docs/cli/skills)
