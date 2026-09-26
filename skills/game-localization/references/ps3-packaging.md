# PS3 ISO、更新/DLC 与实机候选

仅在用户请求 PS3 封装或实机适配时读取。本节是验证路线，不是通用签名修复器，也不包含游戏、固件、授权文件或密钥。

## 从目录制作 ISO

- 固定输入发行包 SHA 和内部清单，核对本体 TITLE_ID、更新版本与目标地区。游戏目录层级包含 `PS3_GAME` 与相应光盘文件；`dev_hdd0/game/<TITLE_ID>` 的更新/DLC 不直接塞进本体 ISO 代替安装。
- 使用支持 PS3 格式的工具，例如 [ps3iso-utils](https://github.com/bucanero/ps3iso-utils) 的 makeps3iso，记录提交和参数。改扩展名、普通数据盘 ISO 或在桌面能挂载不是 PS3 兼容证据。
- 从产出镜像独立遍历文件系统，核对 PS3 头、TITLE_ID、目录大小写、扇区边界、多 extent 和每个文件的哈希。若同时生成 ISO9660/Joliet，分别核对两套树，不能只验证打包前目录。大于 4 GiB 的文件和 FAT32 的限制需写入实际传输说明。

## 三类校验不可混淆

1. 文件哈希/归档 CRC：传输与封包完整性。
2. SDAT/EDAT 的内容校验、头/元数据签名、SELF/NPDRM：内容格式与目标加载条件。
3. 实机执行：特定 CFW/Cobra 或 HEN 环境里的启动、声音、战斗、DLC、存读档。

内容 MAC 更新不等于 ECDSA 签名已有效；零签名、旧签名、debug 标志和重签方案逐文件记录。验签器须用无效 r/s、篡改摘要等负例检验，不能因为同一个工具说“成功”就确认有效。一次 UC 审计发现原生验签辅助函数会误接受零签名，最终改为独立实现检查。

不按文件后缀猜授权条件；有 EDAT 不等于一定缺 RAP。原 EBOOT 的 SELF 头存在也不等于实际签名已通过。能够保留已知正确可执行文件时，不盲目重签、降级或改固件。

## CFW / HEN 分开标证据

不明环境可做公共本体 ISO＋分开的更新/DLC 候选，清楚说明只选一套、如何备份恢复，以及需要的加载器条件。若内容完全相同则不为形式复制两份大 ISO。

PS3Xploit resigner 的公开 HAN 头签名方法只代表一种候选路线，不是索尼官方签名，也不证明元数据签名或所有 NPDRM 检查通过。UC 某批资源的 262 个 EDAT 仅做过头签名离线验证，CFW/HEN 实机接受情况未测；不能把该处理推广为所有游戏 EDAT/SDAT 的标准修复。

实机说明应依据当前加载器文档写明本体路径（例如 `/dev_hdd0/PS3ISO`）、独立更新目录、目录文件与 PKG 的区别、HEN 启用步骤及原版对照。缓存处理是游戏专用：不能把某作 `cache/game.arb` 的办法套到别作，也不动 `savedata`。

工具依据：[PS3HEN](https://github.com/PS3Xploit/PS3HEN)、[PS3xploit-resigner](https://github.com/PS3Xploit/PS3xploit-resigner)、[webMAN MOD 路径](https://github.com/aldostools/webMAN-MOD/wiki/Game-Paths-%26-Covers)。实际使用前按具体版本核对；这里不固定易过时的固件版本。

交付记录分开列出“生成/离线通过/已安装/模拟器运行/CFW实机/HEN实机”。用户可以要求正式 Release，但发布标签与验证等级是两件事；正式发布也必须保留真实未测范围。最终 ZIP 逐文件回读成功后可清理本轮可重建 staging，保留原输入、成品、脚本与清单；逻辑字节数不等同 APFS 实际回收空间。
