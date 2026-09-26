# 音频转写与影片字幕工具

这是可选媒体工具链，不影响原有纯 Python 汉化工具。入口 `scripts/media_toolkit.py`，Python 3.9+；不含游戏影片、模型权重、FFmpeg、商用字体，不自动下载或调用云端服务。所有输出是新候选，拒绝覆盖，未直接写回游戏。

## 工具与依赖

| 工作 | 本包入口 | 外部依赖与限制 |
|---|---|---|
| 检查流/声道/时间基 | `probe` | ffprobe |
| 选音轨、选声道、制作识别用 WAV | `extract` | FFmpeg；不改原音轨 |
| 听音频生成带时间戳的原文候选 | `transcribe` | faster-whisper + 完整本地多语言模型；当前封装 CPU/int8 |
| 空字幕、重叠、越界、未审稿、阅读速度 | `check` | 标准库；不验证翻译准确性 |
| SRT/ASS 导出 | `export` | 标准库；不自动翻译或回写 |
| 把字幕烧进观看用 MP4 | `burn-preview` | FFmpeg 的 libass/subtitles、libx264、AAC |
| 固定矩形/限定时段的简单去字候选 | `delogo-preview` | FFmpeg delogo；周围像素插值，不是复杂背景重建 |

先运行 `python3 scripts/media_toolkit.py doctor`。可用全局 `--ffmpeg /path/to/ffmpeg --ffprobe /path/to/ffprobe` 指定已有程序；Windows 用相应 exe 路径。各机器实际编译选项不同，不能只看“已装 FFmpeg”。脚本不提供 GPU 自动选择或依赖自动安装器。外部程序若失败只保留错误，临时输出不发布成成功结果。

## 1. 提取并听辨音轨

```sh
python3 scripts/media_toolkit.py probe movie.mp4
python3 scripts/media_toolkit.py extract movie.mp4 speech.wav --audio 0
# 仅在已听辨确定所需声道后选择它；声道 2 并非所有影片的对白声道
python3 scripts/media_toolkit.py extract movie.mp4 center.wav --audio 0 --channel 2
```

`--audio` 为从 0 开始的音频流序号，不是 ffprobe 的绝对 stream index；`--channel` 为该流内声道序号。未选声道时混为单声道。先听完整混音和单独声道样本，保留原片与原音轨；识别用 16 kHz/单声道/PCM16 WAV 不能替代发行音轨。左右反相、BGM 遮盖、无线电滤波、说话重叠需人工复核，不能因为转写为空就判无对白。

提取以选中音轨的首个解码样本为起点，不继承原容器 PTS。用 probe 检查视频/音频 start_time，在播放器里对齐首句；有剪辑片段、前导静音、非零 PTS 时记录切片起点和校正偏移，不直接把局部时轴当整片时轴。当前转写 `--offset` 仅支持非负秒；负偏移需在校订 JSON 中显式处理片首裁切并重新检查。

## 2. 本地 ASR（音频识别原文）

在单独 Python 环境按 [faster-whisper 官方说明](https://github.com/SYSTRAN/faster-whisper) 安装依赖，准备完整的本地 CTranslate2 模型目录；不要把 `.en` 英语专用模型用于日语。本工具要求 `model.bin/config.json/tokenizer.json/preprocessor_config.json` 都在目录中，缺失即报错，不回退联网下载。模型的来源、许可、大小与硬件需求单独记录。

```sh
python3 scripts/media_toolkit.py transcribe speech.wav asr.json --model-dir /path/to/local-model --language ja --threads 4
# 分段音频的整片起点，例如 120 秒
python3 scripts/media_toolkit.py transcribe part.wav part-asr.json --model-dir /path/to/local-model --language ja --offset 120
python3 scripts/media_toolkit.py export asr.json source-review.srt --field source --format srt
```

这条命令是 **transcribe 原文识别**，不是把日文语音直接译成中文。保存源音频 SHA、模型 SHA、原文、句段/词时间戳与识别分数；中文 `text` 初始为空、`reviewed` 为 false。分数不是“译文正确率”，VAD 可能漏短呼声、背景音乐可能诱发幻觉；疑点回听，记录不确定词，不能编造。识别后另存译稿、按术语翻译，再复听对时。

替代后端：[whisper.cpp](https://github.com/ggml-org/whisper.cpp) 支持 Apple Silicon 和其他平台，可按其当前 CLI 导出 JSON/SRT，但本包尚未封装它的输出适配器。需要逐词强制对齐或说话人分离时参考 [WhisperX](https://github.com/m-bain/whisperX)；对齐模型有语言边界，speaker 标签不能直接当成角色名，额外模型/授权分别准备。不要将识别、翻译、强制对齐和说话人身份识别混称一个已完成的功能。

## 3. 统一字幕稿、检查与导出

```json
{"schema":"localization-cues-v1","cues":[
  {"id":"movie01-line001","start":1.2,"end":3.8,"source":"Example source.","text":"示例译文。","reviewed":true}
]}
```

保留稳定 id，不随排版拆句覆盖原 ASR；拆分时记录父 ID 和来源区间。时间为整片秒数。`reviewed` 只有实际审过才改为 true，建议另存审校者/证据；脚本不判断该自述真假。

```sh
python3 scripts/media_toolkit.py check translated.json --duration 120 --max-cps 15 --max-line 24
python3 scripts/media_toolkit.py export translated.json chinese.srt --format srt
python3 scripts/media_toolkit.py export translated.json chinese.ass --format ass --font "Source Han Sans SC" --size 36 --width 1280 --height 720
```

15 字/秒、每行24字、最多两行是可调的初筛值，不是所有游戏必须遵循的规格。`check` 返回 0 表示无该类提示，1 表示待查看，2 表示错误；有意的双人重叠单独记录，不自动改时轴。导出仍允许未审候选用于预览；空中文不会偷偷用原文顶替。ASS 导出为纯文本样式，拒绝大括号/反斜杠以免把内容当覆盖代码；要特效、竖排或复杂定位，用字幕编辑器单独编辑并复查。SRT 不能含空白分隔段，过短时间区间因精度归零时拒绝导出。

## 4. 原片无字幕 → 加中文字幕

优先评估游戏是否支持原生字幕；需要视频烧录时，先保留可编辑字幕源，在 [Aegisub](https://aegisub.org/) 等工具里检查切镜、口型/音频、行宽、安全区和字体。时间码按实际音轨，不随意改变帧率。先做普通播放预览：

```sh
python3 scripts/media_toolkit.py burn-preview movie.mp4 chinese.ass viewing-preview.mp4
```

本命令保留第一路视频、全部可映射音轨，重编码为 H.264/AAC MP4，仅供观看预览；音频不是原样 copy。没有保留专用游戏容器、所有元数据、HDR 规范或原音频位流的承诺。原帧率/画幅/时间戳也要与 probe 比对。若原片非方形像素、有旋转元数据或非零起始时间，先制作明确归一化的观看副本并核对时轴，再预览；正式游戏候选按 [影音与字幕](media.md) 的原封装限制单独构建。

字体名称不是字体文件；缺字体可能回退，必须看实际字形/缺字。桌面 MP4 成功不等于 PMF/PAM/PSS/其他游戏影片回装成功。

## 5. 原片有硬字幕 → 清底 → 重做中文字幕

优先级：同版本无字母版/可拆字幕轨 → 原游戏独立字幕层 → 有依据的背景恢复 → 视频修复模型候选。软字幕直接替换字幕轨或事件文字，不对画面做去字。画面写死的字幕不能“关掉”。原音轨、片长和逐帧时序保持可追溯。

简单固定字幕区域可以先用限定时段的候选检查：

```sh
python3 scripts/media_toolkit.py delogo-preview movie.mp4 clean-candidate.mp4 --box 80 580 1100 70 --start 2.5 --end 6.0
```

坐标是解码画面的左上像素 X/Y/W/H；必须先确认宽高、旋转、字幕描边阴影和背景。矩形四周需留像素，时间区间为 `[start,end)`。本命令仅一个固定矩形和时段，全片输出是重编码预览；它不是字幕检测/跟踪器，也不能批量恢复复杂场景。无字幕时段不启用去字过滤，但有损重编码仍可改变整帧。纯色/平缓背景可能适用，人物、机体、光效或移动纹理不得只用模糊块盖掉。

复杂场景按镜头切分，制作与原片同尺寸同帧序的逐帧遮罩，覆盖字面/描边/阴影并跟踪移动文字；镜头切换不得把上一镜的背景传播到下一镜。只修字幕遮罩区域，保留区外原画；处理前后对照静帧和连续播放，检查残字、拖影、边缘光晕、纹理跳变和时序闪烁。不可恢复的细节明确标注为生成/推测，不叫无损还原。

可用 [ProPainter](https://github.com/sczhou/ProPainter) 作为外部视频修复候选：按其项目说明准备视频和遮罩、记录版本/模型/分辨率/分段参数。**本包没有内置模型或自动调用适配器，未验证所有 Mac/Windows 环境；其代码和模型有非商业许可限制，不能当作本仓库 MIT 内容再分发。** 遮罩跟踪、OCR 自动定位、复杂修复和批量调度仍是外部步骤，不宣称已经一键支持。先检查干净候选，再烧入中文；不能用新字幕掩盖旧字残片来跳过检查。

技术参数依据：[FFmpeg subtitles](https://ffmpeg.org/ffmpeg-filters.html#subtitles)、[FFmpeg delogo](https://ffmpeg.org/ffmpeg-filters.html#delogo)。滤镜及模型选择需按当前版本核对。

## 还值得增加的能力（未实现）

- OCR/逐帧字幕框跟踪与镜头切分，输出可复查遮罩；先服务真实影片，避免把装饰标题也去掉。
- 脚本原文与 ASR 的稳定 ID 自动对齐、疑点队列、跨片术语检查。
- SRT/ASS 导入与校订差分回收，支持回写原生字幕资源；当前只有 JSON→字幕导出。
- 实際模型的日英语音回归样本、短呼声/静音幻觉对照，及 Windows/Intel Mac/Apple Silicon 三种环境验收。
- 游戏专用影片重封装适配器与首帧/跳过/转场测试；不把观看用 MP4 当游戏可用成品。

以上是后续方向，不因列在 Skill 中就成为已完成功能。
