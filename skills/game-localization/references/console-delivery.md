# 主机与多端交付（PS2 / PS3）

适用于为 PC 模拟器、安卓手机与原主机实机规划 PS2/PS3 汉化分发、更新封装与实机验证边界。实施时需绑定具体游戏版本、模拟器/加载器版本与实测证据。

## 1. 先分清三层概念

- **传输包装**：`7z` / `ZIP`，负责下载、分卷与归档，通常先解压。
- **运行内容**：PS2 光盘镜像、PS3 本体目录/专用 ISO/原生数字版安装内容，取决于宿主支持。
- **更新方式**：PS3 可用的更新 `PKG`，或在精确基线上合成新版文件/镜像的差分补丁。`PKG` 是安装容器，不是二进制差分（把 `.bsdiff`/`.xdelta` 塞进 PKG 不会自动打补丁）。

同一译文构建可导出多个平台出口；解压成功、PKG 安装成功、游戏加载汉化成功须分开记录。

## 2. 六种常见场景路线

| 场景 | 本体形态 | 推荐更新方式 | 关键边界 |
|---|---|---|---|
| PS2 · PC | 保留可校验原始镜像作基线（DVD 为 ISO，CD 保留轨道布局）；运行副本可另转 CHD | 校验基线的差分 → 合成新版镜像 | 禁止把 ISO 偏移补丁直接打在 CHD 上 |
| PS2 · 安卓 | 解压后导入目标模拟器支持的镜像 | 经验证支持对应算法与大文件的安卓修补器，或电脑合成后传入 | 无通用 PS2 更新 PKG；无合适修补器时如实说明 |
| PS2 · 实机 | 电脑/手机解压修补后，按 OPL 版本与介质（USB/MX4SIO/SMB/HDD）部署 | 合成新版镜像替换对应游戏，保留记忆卡/VMC | 逐项核对文件系统与介质限制；分卷 7z 不是可运行分片镜像 |
| PS3 · PC | 保留可核查本体目录或匹配数字版安装内容 | 经游戏加载验证的更新 PKG（由模拟器安装） | 核对 TITLE_ID、地区、官方更新与读取优先级 |
| PS3 · 安卓 | 选择目标模拟器支持更新 PKG 的本体形态 | 模拟器内安装同一份已验更新 PKG | 核对目标模拟器版本是否支持该本体形态 + 更新，安装成功不等于加载成功 |
| PS3 · 实机 | 按目标 CFW/HEN/加载器支持的 PS3 ISO 或目录部署 | 适配该环境的更新 PKG（Package Manager 安装） | CFW 与 HEN 分开验证；模拟器接受的签名不等于实机接受 |

## 3. PS3 更新 PKG 边界

1. 固定 `TITLE_ID`、地区、光盘/数字版、官方更新版本与输入哈希；汉化发行号与 `PARAM.SFO` 的官方 `APP_VER` 分开记录，不随意抬高 `APP_VER` 绕过检查。
2. 证明游戏实际从更新目录加载目标资源；不能假设光盘 `USRDIR` 任意文件放到更新目录就会覆盖。
3. 作者侧先生成完整目标资源再封装；不将本体、DLC 与更新混为一包。首装包与累计更新写清最低底座及与官方更新的安装顺序。
4. 若游戏不支持更新目录覆盖，采用经验证的本体差分/重建方案或明确标出暂不支持；**“优先 PKG”不等于把 PS2 或所有 PS3 光盘本体硬转成数字版 PKG**。

## 4. PS3 ISO、签名校验与 CFW/HEN 实机边界

- **目录制 ISO**：固定输入哈希与清单，本体包含 `PS3_GAME` 与对应光盘文件，不把 `dev_hdd0/game/<TITLE_ID>` 的更新/DLC 硬塞进本体 ISO。使用专用 PS3 ISO 工具（如 `makeps3iso`），产出后独立遍历 ISO9660/Joliet 文件系统核对 PS3 头、大小写、扇区边界与逐文件哈希。
- **三类校验不可混淆**：
  1. 文件哈希/归档 CRC（传输完整性）；
  2. `SDAT`/`EDAT` 内容校验、头/元数据签名与 `SELF`/`NPDRM`（内容格式与加载条件）；
  3. 实机执行（特定 CFW/Cobra 或 HEN 下的启动、音画、DLC 与存读档）。
- 内容 MAC 更新不等于 ECDSA 签名有效；验签工具必须用无效签名和篡改摘要做负例检验（防止误接受零签名）。不按后缀猜授权条件，能保留已知正常可执行文件时不盲目重签或降级。
- 公开重签路线（如 HAN 头签名）不等同官方签名，也不证明元数据签名通过；CFW 与 HEN 实机接受情况分开标证据。

## 5. 大文件、压缩与手机端成本

- 超过 1 GB 的分发包优先考虑 `7z`（适中 LZMA2 参数，谨慎使用大字典或单一巨大固实块），小型差分可用 `ZIP`；需直接安装的 PKG 可保留独立入口避免多层嵌套。
- FAT32 单文件上限小于 4 GiB；分卷压缩只解决传输，不让解压后的大 ISO/PKG 自动适配 FAT32。
- 手机端预留空间按“原下载包 + 解压产物 + 安装/转换临时输出 + 保留旧版”估算；安卓遵循系统文件选择器与应用授权，不默认可任意写入私有目录。

## 6. 参考来源（按具体版本复核）

- [RPCS3 `unpkg.cpp`](https://github.com/RPCS3/rpcs3/blob/master/rpcs3/Crypto/unpkg.cpp)、[RPCSX Android](https://github.com/RPCSX/rpcsx-ui-android/blob/master/app/src/main/java/net/rpcsx/ui/navigation/AppNavHost.kt)、[PCSX2 `ChdFileReader.cpp`](https://github.com/PCSX2/pcsx2/blob/master/pcsx2/CDVD/ChdFileReader.cpp)
- [Open-PS2-Loader](https://github.com/ps2homebrew/Open-PS2-Loader)、[ps3iso-utils](https://github.com/bucanero/ps3iso-utils)、[webMAN MOD 路径](https://github.com/aldostools/webMAN-MOD/wiki/Game-Paths-%26-Covers)、[PS3HEN](https://github.com/PS3Xploit/PS3HEN)
- [7z 格式说明](https://www.7-zip.org/7z.html)
