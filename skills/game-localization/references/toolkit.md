# 可执行汉化工具包（v0.4.0）

从既有汉化工程的实际脚本整理为离线命令行工具，供能够读写本地文件、运行 Python 的 agent 使用。**所有写入都指定新输出，拒绝覆盖输入和已有输出；不安装到游戏、不启动模拟器、不自动下载依赖。** 未知格式报错，不凭 `.xmb` / `.fpk` 后缀猜版本。

## 入口、依赖、结果

入口：技能目录下 `scripts/localization_toolkit.py`。Python 3.9+，核心命令只依赖标准库；Windows 用 `py -3`，macOS/Linux 常用 `python3`。命令参数始终加引号以支持中文和空格路径。下面示例在技能目录运行；从其他工作目录调用时使用脚本的实际路径。

```sh
python3 scripts/localization_toolkit.py doctor
python3 scripts/localization_toolkit.py --help
```

输出为 JSON：退出码 0 代表该命令完成；1 代表文本/字体检查发现问题；2 代表格式、依赖、路径或版本校验失败。不存在“0 = 游戏汉化完美”的含义。只读清单输出到 stdout，重定向时避免覆盖已有文件。

`font-check` 需要 fontTools；贴图命令需要 Pillow、NumPy、fontTools。按需在自己的虚拟环境中安装 `scripts/requirements-ui.txt`。核心功能不必安装这些库。`doctor` 只报告已安装能力，不会安装任何东西。打包未内置 Python、第三方二进制或字体。

```sh
python3 -m venv .venv
# 激活方式按当前 shell 选择，再运行：
python3 -m pip install -r scripts/requirements-ui.txt
```

核心只写新候选；大型容器操作需为临时输出和最终输出预留最多 **两倍候选大小**的磁盘空间。源文件通过只读方式打开，不把游戏源文件硬链接为候选。候选完成后自行按项目的安装、备份和运行验收流程处理。

## 支持边界

| 命令 | 实际支持 | 限制 |
|---|---|---|
| `inventory` | 文件相对路径、大小、SHA-256 清单 | 跳过符号链接，不代表解析或翻译覆盖率 |
| `container list/extract/replace` | 水天之泪 BLJS10050 已观察到的 BfPk 大端 ARB、FPK 内嵌资源、TEX 图集容器 | ARB 可追加变长成员并改索引；FPK/TEX 只做等长替换。按 magic 和结构核验，不承诺其他游戏变体 |
| `xmb export/import` | 本作 5-key、32 字节记录、UTF-8 字符池的语言表 | 校验源 SHA、ID、源文、节点与零填充；非通用 XML/XMB 转换器 |
| `text-check` | 显式控制 token、缺字表、换行与同原文异译提示 | 必须由 agent/适配器填写 protected_tokens；不自动判断语义正确性 |
| `font-check` | TTF/OTF/TTC 的 Unicode cmap | 不验证排版塑形或游戏私有码表 |
| `gtf-typeset/preview` | 单纹理、128 字节头、2D、2 次幂尺寸；0x88 BC3、0xa5 线性 ARGB 的已观察 GTF 布局 | 改字保留头、大小、未触及压缩块/像素；需要显式字体；其他纹理变体拒绝 |
| `uv` | 像素矩形到顶/底原点 UV 范围 | 不自动修动画、网格或场景包围盒 |
| `delta create/apply` | 任意文件的 copy/add 差分、前后 SHA 校验 | 生成/重建新文件，不是游戏专用安装器，不自动处理缓存或更新副本 |

这些格式逻辑来自本作工程；便携化后通过真实资源离线往返及虚构数据测试，但没有用本工具新建候选进行游戏运行验收。原版特定脚本有运行经验，并不自动证明本工具所有参数组合正确。

## 一个不需要游戏文件的小样

```sh
python3 scripts/make_toolkit_demo.py --output demo
python3 scripts/localization_toolkit.py xmb export demo/sample.xmb --output demo/table.json
```

在 `table.json` 的 `entries` 中填写 `translation`，保留 `id`、`source` 和 `source_sha256`。`null` 表示保留原文，`""` 表示有意置空；不要把未译条目填空字符串。第二句 `Hello, [$name]!` 的 `protected_tokens` 填 `["[$name]"]`。翻译前先从游戏格式/上下文确定控制码，不能默认空列表就已经保护控制码。

```sh
python3 scripts/localization_toolkit.py text-check demo/table.json
python3 scripts/localization_toolkit.py xmb import demo/sample.xmb --table demo/table.json --output demo/translated.xmb
python3 scripts/localization_toolkit.py xmb export demo/translated.xmb --output demo/roundtrip.json
python3 scripts/localization_toolkit.py delta create demo/sample.xmb demo/translated.xmb --output demo/patch
python3 scripts/localization_toolkit.py delta apply demo/sample.xmb demo/patch --output demo/restored.xmb
```

比较 `translated.xmb` 和 `restored.xmb` 的 SHA 应相同；查看 `roundtrip.json` 确认译文和占位符。重跑时换一个新目录，工具不会覆盖之前的候选。`scripts/toolkit_selftest.py` 可一键完成这个完整小样并检查错误基线拒绝。

## 容器操作

```sh
python3 scripts/localization_toolkit.py container list demo/sample.arb
python3 scripts/localization_toolkit.py container extract demo/sample.arb --member game/language/demo.xmb --output demo/extracted.xmb
```

从抽取命令的 JSON 取得 `sha256`，替换命令必须显式提供这个源成员指纹：

```sh
python3 scripts/localization_toolkit.py container replace demo/sample.arb --member game/language/demo.xmb --replacement demo/translated.xmb --expect-member-sha256 '<抽取结果里的SHA256>' --output demo/candidate.arb
```

抽取一次只写明确指定的输出文件，不将归档内 `../`、绝对路径或 `Z:` 名称当作本机输出路径。变长 ARB 追加到容器末尾，旧成员字节保留，引用改到新位置；这是保守候选构建策略，不承诺游戏允许任意变长。大型改动要检查资源预算与运行行为。

## 贴图、字库和 UV

```sh
python3 scripts/localization_toolkit.py gtf-preview source.gtf --output before.png
python3 scripts/localization_toolkit.py font-check --font your-font.ttf --text translated-text.txt
python3 scripts/localization_toolkit.py gtf-typeset source.gtf --labels labels.json --font your-font.ttf --font-index 0 --expect-sha256 '<源GTF的SHA256>' --output candidate.gtf
python3 scripts/localization_toolkit.py gtf-preview candidate.gtf --output after.png
python3 scripts/localization_toolkit.py uv --box 8 46 74 82 --size 256 128 --origin bottom
```

`labels.json` 是数组，例如：

```json
[{"text":"能源","box":[8,46,74,82],"align":"center","ink_height":16}]
```

box 是左上原点像素矩形，右/下边界不包含。默认参考旧字的墨迹高度与颜色；该矩形需要确有旧字。使用自己的、有权使用的字体；TTC 子字体通过 `--font-index` 指定。`background:"interpolate"` 仅适合简单横向背景，不是通用去字或背景重绘。可用 `color:[255,255,255]` 明确字色。

不要只看整张图集：对照真正 UV、包围盒、切片与动画节点检查字形是否被裁切。BC3 是有损格式，压缩块边界会带来块内变化；仅声称未选中的块保持原字节。底原点 UV 结果不等于游戏已经正确显示。

## 外部工具与未打包能力

- 影音仍按 [media.md](media.md) 使用已有 FFmpeg/ffprobe；本包不自动重编码影片或把 ASR 当定稿。
- FromSoftware BND/DCX、ACFF PS2 码表与 ISO 回装、SDAT 的认证加解密属于另外的格式/平台工具链，未作为万能适配器塞入本包。沿用各项目已验证版本；需要增加支持时按 [adapters.md](adapters.md) 单独移植并往返测试。
- 没有打包游戏数据、译文全集、商业字体、私人路径、聊天、存档、授权材料；没有打包 QuickBMS、Noesis、模拟器、PS3 固件或外部工具可执行文件。

## 其他 agent 的最小交接

把整个技能目录交给 agent，保留 `scripts/toolkit/` 相对结构。先让它执行 `doctor` 和 `toolkit_selftest.py`，再让它读当前输入的 adapter 边界。支持 Skill 的客户端按各自说明安装；其他能执行 Python 的 agent 可直接读本页并调用脚本。仅能文字聊天、不能读写文件的模型无法运行这些工具。

可直接交给另一 agent：

> 读取该技能的 references/toolkit.md，先运行 doctor 和 toolkit_selftest.py。使用新输出目录；核对输入格式与指纹，用虚构小样走通抽取、翻译、回填、差分重建，再处理我提供的候选资源。不要启动模拟器或改我的游戏目录，遇到不支持格式就报告具体限制。

实现来源和便携化边界见 [工具来源](toolkit-provenance.md)。

## 可选影音工具

音轨探测/提取、本地 ASR 候选、字幕检查、SRT/ASS 导出、烧录和简单矩形去字预览，使用 `scripts/media_toolkit.py`。依赖、命令、验证限制和复杂背景外部流程见 [media-tools.md](media-tools.md)；不包含模型和游戏专用影片封装器。
