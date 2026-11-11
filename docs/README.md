# 文档索引

## 先读这三份（不限分支，`main` 上就有）

| 文档 | 内容 | 适合谁 |
|---|---|---|
| [项目全貌](00-overview.md) | 做什么、为什么先 B、当前进度、已锁定决策 | 所有人，第一次打开仓库 |
| [新人上手](onboarding.md) | 读什么、分支怎么用、第一次提交怎么写 | 新加入的同学 |
| [平台愿景](design/platform-vision.md) | 从"审代码"到"管交付"的完整链路 | 想理解终局的人 |

---

## 按轨道读

**先读 B（变更追溯）**，它决定 A（PR 审查）能不能做出差异化。

| 顺序 | 文件 | 内容 | 分支 |
|---|---|---|---|
| 1 | [变更管理设计](b/01-change-management-design.md) | 七段变更单、六维定级、挂起与升级、观察期判定标准 | `feat/b-change-trace` |
| 2 | [变更单模板](b/02-change-order-form.md) | A–G 段字段与取值 | `feat/b-change-trace` |
| 3 | [变更台账](b/03-change-ledger.md) | 41 列字段、自动计算列、统计口径 | `feat/b-change-trace` |
| 4 | [变更周报](b/04-weekly-report.md) | 六段式、红线阈值 | `feat/b-change-trace` |
| 5 | [多项目汇总](b/05-portfolio-summary.md) | 19 列、加权口径 | `feat/b-change-trace` |
| 6 | [两周启动方案](b/06-kickoff-plan.md) | 执行表、验收线、止损规则 | `feat/b-change-trace` |
| 7 | [变更影响引擎](design/change-impact-engine.md) | 变更驱动的图谱、传播、契约快照（V2） | `main` |
| 8 | [开源化改造](design/open-source-pivot.md) | **项目转开源免费后的设计变更清单** | `main` |
| 9 | [PR 审查 PRD](a/prd-pr-review.md) | 12 章 + 3 附录 | `feat/a-pr-review` |

> 全部文档已合并到 `main`，路径不再依赖分支。

---

## 文档状态

| 文档 | 版本 | 状态 |
|---|---|---|
| 项目全貌 / 新人上手 | v1.0 | 稳定 |
| 变更管理设计与模板 | v0.1 | 观察期使用中 |
| 启动方案 | v1.0 | 待执行 |
| 平台愿景 / 影响引擎 | v0.1 | 设计稿，未实现 |
| PR 审查 PRD | v0.1 | 待评审 |

---

## 写作约定

- 所有数字口径写在文档里，不靠口头传递；改动口径必须同时改周报、台账、汇总三处。
- 中文文档，术语首次出现给英文原词。
- 图表用 Mermaid 或表格，不贴截图。
- `assets/` 里的 docx/xlsx 是产物，正文以 Markdown 为准。
