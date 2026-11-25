# 不同助手的兼容范围

本 Skill 不绑定模型。模型负责理解和推理，编程助手负责发现 Skill、读写文件和执行工具；两者应分别判断。日文与英文译为中文都在本版工作流程范围内，实际质量仍需审校。

| 工具 | 安装目录示例 | 说明 |
|---|---|---|
| Codex | `~/.codex/skills/game-localization/` | 保留 `agents/openai.yaml` 与 `scripts/build_mission_review.mjs` |
| Antigravity | `~/.gemini/config/skills/game-localization/` 或项目 `.agents/skills/game-localization/` | [Antigravity 安装说明](ANTIGRAVITY.md) |
| DeepSeek Harness (DSH) | `~/.dsh/skills/game-localization/` 或工作区 `.dsh/skills/game-localization/` | [DSH 安装说明](DSH.md) |
| Cursor | `~/.cursor/skills/game-localization/` 或项目 `.cursor/skills/game-localization/` | [Cursor 安装说明](CURSOR.md) |
| Kimi Code | `~/.kimi-code/skills/game-localization/` | [Kimi Code 安装说明](KIMI.md) |
| Qwen Code（通义） | `.qwen/skills/game-localization/` 或 `~/.qwen/skills/game-localization/` | [Qwen Code 安装说明](QWEN.md) |
| CodeBuddy（腾讯） | `.codebuddy/skills/game-localization/` 或 `~/.codebuddy/skills/game-localization/` | [CodeBuddy 安装说明](CODEBUDDY.md) |

`agents/openai.yaml` 与 `scripts/build_mission_review.mjs`（依赖 `@oai/artifact-tool`）仅用于 Codex 可选扩展；核心说明、10 份参考资料与纯 Python 工具不依赖它们。

普通网页聊天模型可参考文档；只有具备所需文件和脚本工具的运行环境，才能执行抽取、回填和检查。

官方资料：

- [Cursor Skills](https://cursor.com/docs/skills)
- [Kimi Code Skills](https://www.kimi.com/code/docs/en/kimi-code-cli/customization/skills.html)
- [Qwen Code Skills](https://github.com/QwenLM/qwen-code/blob/main/docs/users/features/skills.md)
- [CodeBuddy Skills](https://www.codebuddy.ai/docs/cli/skills)
