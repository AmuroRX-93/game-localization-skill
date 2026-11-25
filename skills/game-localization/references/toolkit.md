# 可执行工具包与清单审计手册

本技能附带离线命令行脚本（位于 `scripts/`），供可读写本地文件并执行 Python 3.9+ 的环境使用。**所有写入均指定新输出路径，拒绝覆盖输入与已有输出；不安装到游戏、不启动模拟器、不自动联网下载依赖。**

## 1. 环境诊断与自测

```sh
python3 scripts/localization_toolkit.py doctor
python3 scripts/localization_toolkit.py --help
python3 scripts/toolkit_selftest.py
```

- 退出码约定：`0` = 命令正常完成；`1` = 检查发现待处理项或问题；`2` = 格式、依赖、路径或指纹校验失败。`0` 不代表游戏运行已通过。
- 核心命令仅依赖 Python 标准库；`font-check` 需要 `fontTools`，`gtf-*` 贴图命令需要 `Pillow`、`NumPy`、`fontTools`（见 `scripts/requirements-ui.txt`）。
- 大型容器操作需预留最多约两倍候选大小的磁盘空间；参数含中文或空格时加引号。

## 2. 命令分层：通用工具 vs 单游戏示例适配器

`scripts/localization_toolkit.py` 包含两类能力，使用时须明确边界：

### 通用离线工具（跨游戏）
| 命令 | 能力 | 限制 |
|---|---|---|
| `inventory` | 生成相对路径、大小、SHA-256 清单 | 跳过符号链接，不等于解析或翻译覆盖率 |
| `text-check` | 检查显式 `protected_tokens`、缺字表、换行与同原文异译 | 控制码必须由调用方/适配器提供，不自动判断语义 |
| `font-check` | 检查 TTF/OTF/TTC 的 Unicode cmap 覆盖 | 不验证引擎塑形或游戏私有码表 |
| `uv` | 像素矩形到顶/底原点 UV 换算 | 不自动修动画、网格或包围盒 |
| `delta create/apply` | 任意文件的 copy/add 差分与前后 SHA 校验 | 流式重建新文件，非游戏专用安装器 |

### 已观察变体示例适配器（仅限特定格式）
来自实际工程的便携整理模块（`scripts/toolkit/suiten_formats.py`、`ui_texture.py`），未知变体直接拒绝，**不是万能解包器**：
| 命令 | 已验证格式范围 | 限制 |
|---|---|---|
| `container list/extract/replace` | 《水天之泪》BLJS10050 已观察到的 BfPk 大端 ARB、FPK、TEX | ARB 可追加变长成员改索引；FPK/TEX 仅等长替换；替换须传 `--expect-member-sha256` |
| `xmb export/import` | 上述变体的 5-key、32 字节记录、UTF-8 字符池语言表 | 校验源 SHA、ID、源文与零填充；非通用 XML/XMB |
| `gtf-typeset/preview` | 单纹理、128 字节头、2D、2 次幂尺寸的 0x88 BC3 / 0xa5 线性 ARGB | 保留未触及压缩块/像素，需显式字体；`background:"interpolate"` 仅适合简单横向背景 |

其他引擎/格式（如 FromSoftware BND/DCX、PS2 码表与 ISO 回装、SDAT 认证加解密等）未塞入本包，按 [workflow.md](workflow.md#4-跨游戏适配器约定) 单独开发并往返测试。

## 3. 快速小样闭环（无需游戏文件）

```sh
python3 scripts/make_toolkit_demo.py --output demo
python3 scripts/localization_toolkit.py xmb export demo/sample.xmb --output demo/table.json
# 编辑 demo/table.json 的 translation 字段（null=保留原文，""=有意置空）并填写 protected_tokens
python3 scripts/localization_toolkit.py text-check demo/table.json
python3 scripts/localization_toolkit.py xmb import demo/sample.xmb --table demo/table.json --output demo/translated.xmb
python3 scripts/localization_toolkit.py delta create demo/sample.xmb demo/translated.xmb --output demo/patch
python3 scripts/localization_toolkit.py delta apply demo/sample.xmb demo/patch --output demo/restored.xmb
```

`scripts/toolkit_selftest.py` 可一键运行完整合成样本测试并验证错误基线与覆盖拒绝。

## 4. 项目清单审计（`audit_ledger.py`）

`scripts/audit_ledger.py`（纯标准库、只读）用于检查项目进度 JSON 中的漏项与状态矛盾，虚构示例见 [demo-ledger.json](demo-ledger.json)：

```sh
python3 scripts/audit_ledger.py project-ledger.json
```

关键结构要求（`schema_version: 1`）：
- `scope`：`game`、`platform`、`revision`、`inventory_basis`、`inventory_complete`、`build_sha256`。
- `resources`：唯一 `id`、`path`、`kind`、`sha256`、`disposition`（`pending|extracted|not_text|excluded`）、`expected_entries`；已提取需 `extraction_complete`，已分类需 `evidence`，非文本/排除需 `reason`。
- `entries`：唯一 `id`、`resource_id`、`locator`（同资源不重复）、`source`、`target`、`decision`（`pending|translate|retain|exclude`）、`review`（`pending|accepted`）、`writeback`（`pending|passed|not_applicable`）、`token_mode`（`unverified|ordered|multiset|none`）及 `source_tokens`/`target_tokens`。
- `tests`：唯一 `id`、`scenario`、`build_sha256`、`status`（`pending|passed|failed`）；构建哈希变化后旧测试标记过期。

禁止通过删行或改小 `expected_entries` 制造“0 缺口”。

## 5. 来源与许可边界

上述脚本为仓库作者自编工程脚本的便携整理版，沿用本仓库 MIT 许可（不含游戏数据、商业字体、第三方二进制或外部格式库）。可选依赖（`Pillow`、`NumPy`、`fontTools`、`FFmpeg`、`xdelta3`）遵循各自许可证，由使用者按需提供。
