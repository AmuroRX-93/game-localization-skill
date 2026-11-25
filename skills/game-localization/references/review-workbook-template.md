# 可选任务校对稿样表与生成脚本

适用于按任务/关卡整理简报、参数、对白与系统提示的 XLSX 校对稿。本版式是可选参考样表（结构定义见 [mission-review-format.json](mission-review-format.json)），不强制用于部件表、邮件或所有项目；用户提供新样表时以新样表为准。

## 1. 版式约定

- 工作表名：`任务文本汇总`，首行直接为表头，不加额外大标题、统计卡或工程列。
- **A–I 列顺序**：关卡序号、STAGE（关卡名）、委托人、预付报酬、成功报酬、条目类别、条目编号、说话人、内容（中文/校对栏）。
- **J:P 横向合并栏**：逐行横向合并作为原文栏（默认表头“日文原文”，英文项目改为“英文原文”，混合来源逐条注明语言）。未知原文留空并在配套映射标缺失，不以机器回译填充。
- **合并与样式**：A–E 按任务分别纵向合并（相邻任务报酬相同也不跨任务合并）；F–I 每条一行，保留换行；全表宋体 11，A–I 表头深蓝 `#305496` 白字加粗，任务块白/浅蓝 `#F2F7FC` 交替，细灰边框 `#BFBFBF`；J:P 原文栏表头橙色 `#FFCC99` 字色 `#3F3F76` 正文白底；冻结首行，不给合并块套自动筛选/排序。
- **列宽与行高**：A–I 依次 `10/26/24/10/10/12/12/10/70`，J–P 各 `8.43`；表头高 `22.05`，正文最低 `28.8` 并按换行自动增高。表格宋体仅用于文档排版，不代表游戏内字库选择。

## 2. 生成脚本（可选 Node 依赖）

`scripts/build_mission_review.mjs` 按上述版式生成 XLSX 与同名 `.mapping.json`，不修改输入或游戏。该脚本依赖 Node.js 与 `@oai/artifact-tool`（可选文档生成依赖，非核心 Python 工具要求）：

```sh
node scripts/build_mission_review.mjs input.json output.xlsx --preview preview.png
# 若依赖位于自定义目录：
node scripts/build_mission_review.mjs input.json output.xlsx --node-modules /path/to/node_modules --preview preview.png
```

缺少 `@oai/artifact-tool` 时脚本会报错且不自动下载；无此库的环境可依据 [mission-review-format.json](mission-review-format.json) 用 `openpyxl` / `exceljs` 等工具按同样规范生成。

输入 JSON 结构示例（虚构数据）：

```json
{
  "baseline": "游戏版本及资源清单SHA256",
  "source_header": "日文原文",
  "missions": [{
    "id": "M01", "stage": "示例关卡", "client": "示例委托人",
    "advance": 0, "reward": 1000,
    "entries": [{
      "uid": "版本/容器/成员/文本ID",
      "category": "任务简报", "number": "M01-1", "speaker": "",
      "content": "示例中文。", "source": null,
      "locator": {"resource": "相对资源路径", "entry_id": "源条目ID"}
    }]
  }]
}
```

`advance/reward` 为非负整数或 `null`（未知不写 0）；`source` 为确证原文或 `null`。脚本会拒绝重复 `uid`、已有输出与错误类型。显示编号（如 `M01-F`）允许重复，不作为唯一技术 ID。

## 3. 回收与验收

- 配套 `.mapping.json` 记录构建基线、稳定 `uid`、资源定位、原中文、原文指纹与导出行号；**行号仅辅助定位**，回收时按上下文与稳定映射对齐，遇到重复编号无法消歧、未知 ID、源指纹变化或冲突编辑必须报错，不猜测回写。若需支持任意排序后的自动回写，需先在用户允许的隐藏元数据中随行携带 `uid` 并编写对应导入器。
- 生成后重读 XLSX，核对任务数、条数、合并范围、空原文数，确认以 `=` 开头的正文未变成公式；渲染完整任务块检查最长中文、原文、跨行元数据与任务边界。
