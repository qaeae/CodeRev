# 治理

> 目标：让"谁能决定什么"是可预测的，而不是靠谁嗓门大。

## 角色

| 角色 | 能做什么 | 怎么获得 |
|---|---|---|
| **User** | 用、提 issue、参与讨论 | 自动 |
| **Contributor** | 提 PR | 第一个被合并的 PR |
| **Reviewer** | 评审 PR、打标签、关 issue | 3 个高质量 PR + 1 位 maintainer 提名 |
| **Maintainer** | 合并 PR、发布版本、管仓库设置 | 持续贡献 ≥3 个月 + 现有 maintainer 多数同意 |
| **Emeritus** | 保留头衔，不再有合并权 | 连续 6 个月不活跃，或主动退出 |

## 权限矩阵

| 动作 | Contributor | Reviewer | Maintainer |
|---|---|---|---|
| 提 PR | ✅ | ✅ | ✅ |
| 评审 PR | — | ✅ | ✅ |
| 合并到子分支 | — | ✅ | ✅ |
| 合并到 `main` | — | — | ✅ |
| 发布版本 | — | — | ✅ |
| 改 LICENSE / 治理文件 | — | — | ✅（需 RFC） |

## 决策机制

### 小改动：lazy consensus

PR 或 issue 发出后 **7 天**内无人明确反对，即视为通过。

### 大改动：RFC

以下改动必须先开 RFC issue（模板见 `.github/ISSUE_TEMPLATE/`），讨论 ≥7 天：

- 改输出契约（JSON schema）
- 改许可证、治理结构、商标政策
- 引入新的运行时依赖（数据库、队列、框架）
- 改核心流水线（webhook → 审查 → 评论）
- 新增一个"官方支持"的 Git 平台

RFC 通过条件：**没有 maintainer 的明确反对**，且至少 1 位 maintainer 明确支持。

### 僵局

维护者之间意见不一致时：

1. 先找数据（跑评测集、看用户反馈），不靠辩论。
2. 仍不一致 → 由项目发起人（BDFL）裁决，并在 RFC 里记录理由。
3. 裁决结果 12 个月内可被新的 RFC 推翻。

## 冲突与行为

- 技术分歧：对事不对人，用数据和例子说话。
- 人身冲突：按 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) 处理。
- 贡献者与 maintainer 冲突：可要求第二位 maintainer 介入。

## 不活跃处理

- 连续 6 个月无贡献（issue 回复、PR、评审都算）→ 转 Emeritus。
- 转 Emeritus 不是惩罚，回归后可恢复。
- 关键路径（发布权限）始终至少保留 2 名活跃 maintainer。

## 资金

- 赞助收入优先用于：CI 分钟数、域名、模型 API 测试费用。
- 收支公开在 `FUNDING.md`（启用赞助后创建）。
- 不接受附带产品决策权的赞助。

## 修改本文件

需 RFC + 全部 maintainer 同意。
