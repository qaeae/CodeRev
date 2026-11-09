# 文档索引

本仓库文档分两条轨道，分别位于两个子分支上。`main` 只保留骨架与索引。

## 阅读顺序

**先读 B（变更追溯）**，它决定 A（PR 审查）能不能做出差异化。

| 顺序 | 文件 | 内容 | 分支 |
|---|---|---|---|
| 1 | `docs/b/01-change-management-design.md` | 变更管理设计：七段变更单、定级规则、挂起与升级、观察期判定标准 | `feat/b-change-trace` |
| 2 | `docs/b/02-change-order-form.md` | 变更单模板（A–G 段字段与取值） | `feat/b-change-trace` |
| 3 | `docs/b/03-change-ledger.md` | 变更台账：41 列字段、自动计算列、统计口径 | `feat/b-change-trace` |
| 4 | `docs/b/04-weekly-report.md` | 周报模板：六段式、红线阈值 | `feat/b-change-trace` |
| 5 | `docs/b/05-portfolio-summary.md` | 多项目汇总：19 列、加权口径 | `feat/b-change-trace` |
| 6 | `docs/b/06-kickoff-plan.md` | 两周启动方案：执行表、验收线、止损规则 | `feat/b-change-trace` |
| 7 | `docs/a/prd-pr-review.md` | PR 审查产品需求文档（12 章 + 3 附录） | `feat/a-pr-review` |

## 文档状态

| 文档 | 版本 | 状态 |
|---|---|---|
| 变更管理设计与模板 | v0.1 | 观察期使用中 |
| 启动方案 | v1.0 | 待执行 |
| PR 审查 PRD | v0.1 | 待评审 |

## 写作约定

- 所有数字口径写在文档里，不靠口头传递；改动口径必须同时改周报、台账、汇总三处。
- 中文文档，术语首次出现给英文原词。
- 图表用 Mermaid 或表格，不贴截图。
