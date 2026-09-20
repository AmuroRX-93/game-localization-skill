# 清单检查工具

`scripts/audit_ledger.py` 使用 Python 3.9+ 标准库，仅只读检查 JSON，不修改游戏、不联网。

```sh
python3 path/to/game-localization/scripts/audit_ledger.py project-ledger.json
```

退出码：0＝登记范围内无发现的缺口；1＝存在待办或状态矛盾；2＝格式／读取错误。stdout 为 JSON 报告，格式错误写 stderr。**0 不证明游戏全量，也不证明报告指向的证据真实。** 工具不解析游戏、提取 token、判断译义或打开证据文件；这些由适配器及审校完成。

## 数据字段

- `schema_version`: 整数 1。
- `scope`: `game`、`platform`、`revision`、`inventory_basis`（说明分母来源）、`inventory_complete`（布尔）、`build_sha256`（当前构建小写 SHA-256）。
- `resources`: 对象数组。`id` 唯一；`path` 可表示嵌套容器链；`kind` 自定义类型；`sha256`；`disposition` 为 pending/extracted/not_text/excluded；`expected_entries` 是适配器盘点的物理条目数，未知暂为 0 且状态保持 pending。已提取资源还需布尔 `extraction_complete`；已分类需 `evidence`；非文本／排除需 `reason`。
- `entries`: 对象数组。`id` 唯一；`resource_id`、`locator` 指向物理位置，同一资源不可重复位置；`source`、`target` 可为空字符串；`decision` 为 pending/translate/retain/exclude。保留和排除时目标必须等于原文，并附 `reason`。
- 条目 `review`: pending/accepted；accepted 需 `review_evidence`。`writeback`: pending/passed/not_applicable；后两者需 `writeback_evidence`，翻译条目不能不适用。只做校对表时 writeback 留 pending，它是交付边界，不是表格制作失败。
- 条目 `token_mode`: unverified/ordered/multiset/none；`source_tokens`、`target_tokens` 为适配器提取的字符串数组。无名变量及有序控制指令用 ordered；可重排的命名变量可用 multiset，仍比较重复次数。只有证明无受保护 token 才用 none；除 unverified 外需 `token_evidence`。复杂嵌套／分支语义仍需适配器专用验证。
- `tests`: 对象数组。唯一 `id`、`scenario`、`build_sha256`、`status`（pending/passed/failed），passed 需 `evidence`。旧构建测试标记过期。

额外字段可用于团队负责人、截图位置或翻译记忆。相同词面出现在两个位置时登记两条，相同字面但语义不同不自动合并。`expected_entries` 应来自抽取清单，不能为了通过检查改成当前表格行数。

[demo-ledger.json](demo-ledger.json)是完全虚构的未完成示例，故意返回 1。可复制后填入自己项目的数据。任何 missing/failed/unknown 应保留到明确处理，不准靠删行制造完成率。
