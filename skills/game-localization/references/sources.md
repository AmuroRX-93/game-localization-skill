# 资料来源与吸收方式

查阅日期：2026-09-20。以下链接是方法来源，不是本仓库已经集成、测试或推荐安装的工具清单。工具版本、API、支持格式随项目核对；此处仅概述，未复制第三方实现。

| 第一方资料 | 本 Skill 吸收的做法 | 适用限制 |
|---|---|---|
| [T.R.A.F.《Guide de la traduction v2》](https://wiki.romhack.org/index.php?title=Guide_de_la_traduction_v2) | 码表、指针、压缩、文本导出与回填、图形翻译和补丁的完整链条 | 传统 ROM 方法不能原样套到所有现代引擎 |
| [Atlas 项目](https://github.com/stevemonaco/Atlas) | 用脚本和自定义码表回填，并显式更新指针 | 无通用游戏格式保证；本仓库不附带 Atlas |
| [Kuriimu2 项目说明](https://github.com/FanTranslatorsInternational/Kuriimu2/blob/imgui/README.md) | 通用基础设施与游戏／格式插件分离 | 能打开或抽取不代表特定变体可安全写回 |
| [Weblate 5.15 检查说明](https://docs.weblate.org/en/weblate-5.15/admin/checks.html) | 把占位符、术语和长度约束转成可执行检查，允许解释误报 | 规则依格式设置，不自动理解游戏脚本 |
| [OmegaT 翻译记忆说明](https://omegat.sourceforge.io/manual-standard/en/chapter.how.to.html) | 复用译文与模糊匹配，同时保留人工判断 | 模糊匹配不等于语义等价或已审校 |
| [Ren'Py 翻译文档](https://www.renpy.org/doc/html/translation.html) | 有源工程时分开处理对白、界面字符串、图片与样式 | 源工程工作流不保证适用于只持有成品 |
| [Unreal 本地化概览](https://dev.epicgames.com/documentation/en-us/unreal-engine/localization-overview-for-unreal-engine) | 语言内容与国际化／文化设置共同决定最终行为 | 跟随目标引擎版本，不硬编码最新文档接口 |
| [Unity 伪本地化](https://docs.unity3d.com/ja/Packages/com.unity.localization%401.4/manual/Pseudo-Localization.html) | 提前暴露文本膨胀、未本地化字符串和拼接问题 | 借鉴测试思想，不要求旧游戏使用 Unity |
| [Aegisub 排字介绍](https://aegisub.org/docs/latest/typesetting/) | 把字幕排字作为独立工序 | 字幕文件可显示不证明专有游戏容器可回装 |

本仓库的覆盖清单、内存／字形验证、发布检查和案例边界，是上述方法与实际工程记录结合后的设计，不是第三方项目的官方规范。对所有平台的适配能力仍需通过新的真实项目逐步积累。
