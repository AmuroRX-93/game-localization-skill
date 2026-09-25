# 工具来源与便携化说明

本包脚本是本仓库作者汉化工程中自编脚本的便携整理版，继续采用仓库 MIT 许可；它不是对游戏本体、字体、翻译资产或第三方软件重新授权。

- `suiten_formats.py` 的 XMB 节点/字符串池逻辑来自水天之泪工程 `xmb_text.py`，BfPk/FPK/TEX 的索引逻辑来自该工程的资源抽取与界面修订流程。移除了预设根目录、游戏安装路径和批量写回入口，增加边界、指纹、ID 及未知变体拒绝。
- `ui_texture.py` 的 BC3 编码、文字布局和未选块保留逻辑来自该工程 `build_menu_labels.py`。移除了具体游戏标签、系统字体路径和固定 TTC 索引，改为显式字体与标签输入；限制为已观察 GTF 布局，增加结构与字形检查。此编码器偏向 UI 色彩范围，不是高质量通用纹理压缩器。
- `delta.py` 沿用已使用的 copy/add 差分思想，加入大文件只读映射、流式回填、基线/载荷/结果 SHA 和干净目录往返验证。它不携带任何游戏补丁内容。
- `localization_toolkit.py` 将资源盘点、逐条回填、token/字形检查、UV 原点校验和工具诊断统一到参数化 CLI。`make_toolkit_demo.py` / `toolkit_selftest.py` 使用完全虚构的数据，方便别的 agent 独立验收。

可选依赖：Pillow、NumPy、fontTools 使用各自许可证；本包只列出依赖，不内置它们。字体、FFmpeg、ffprobe、xdelta3 等工具需由使用者按项目环境提供。外部格式库、SDAT 认证工具和 PS2/FromSoftware 专用链并未冒充通用模块打入本包。

开发验证用了本地合法持有的真实样本；公开仓库只包含格式代码、合成样本生成器及测试，不包含这些样本或本机路径。格式支持和运行证据详见 [toolkit.md](toolkit.md) 及仓库验证记录。
