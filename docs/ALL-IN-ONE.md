# 游戏汉化 Skill 总包 — 先看这里

支持日文→中文、英文→中文。一个压缩包包含七种工具的完整技能、参考资料、汉化实用脚本和各自安装说明。**按你使用的工具选一个文件夹，不要把总包整个放进技能扫描目录。**

| 文件夹 | 对应工具 | 下一步 |
|---|---|---|
| `01-Codex` | Codex／通用文件型 Skill | 阅读里面的 `先看这里.md` |
| `02-Cursor` | Cursor | 阅读里面的 `先看这里.md` |
| `03-Kimi-Code` | Kimi Code | 阅读里面的 `先看这里.md` |
| `04-Qwen-Code` | 通义 Qwen Code | 阅读里面的 `先看这里.md` |
| `05-CodeBuddy` | 腾讯 CodeBuddy | 阅读里面的 `先看这里.md` |
| `06-DSH` | DeepSeek Harness (DSH) | 阅读里面的 `先看这里.md` |
| `07-Antigravity` | Google Antigravity | 阅读里面的 `先看这里.md` |

解压后若只看到说明，看不到以点开头的文件夹，macOS Finder 按 `Command+Shift+.` 显示隐藏项目。只复制目标工具下的本技能，不替换整套应用配置。已装同名技能的用户先比较差异，保留个人定制。

各份核心内容来自同一源码。非 Codex 包自动省略 Codex 专属的 `agents/openai.yaml` 与 `scripts/build_mission_review.mjs`；差别在目录和安装／调用方式。

这是可复用的汉化工程方法，不是所有游戏通用的解包器。脚本需要 Python 3.9+；首次使用可先运行 `scripts/localization_toolkit.py doctor` 和 `scripts/toolkit_selftest.py`。核心只依赖标准库，图像/字体功能按需安装 `scripts/requirements-ui.txt`。

公开内容采用包内 MIT 许可；不含游戏镜像、字体、存档或私人记录。

项目：https://github.com/AmuroRX-93/game-localization-skill
