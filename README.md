# CodeRev

**开源免费的 PR 审查与变更追溯工具。自托管、BYOK、代码不出内网。**

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Status](https://img.shields.io/badge/status-design%20stage-orange.svg)](ROADMAP.md)

> 当前是**设计阶段**：文档齐全，代码未开始。现在参与，你影响的是"它长成什么样"。
> Before you start: everything here is documented in Chinese. English issues and PRs are welcome.

---

## 它解决什么问题

AI 审查工具已经很多，但有三个坑没人填：

1. **误报淹没一切**。每天 5 条"这行建议加个注释"，团队第二周就把它关了。
2. **审查和需求脱节**。模型不知道这个 PR 服务哪条需求，只能按通用规则挑毛病。
3. **规则不可控**。想加一条团队规范，得去某个后台点表单，不能 review、不能 diff、不能回滚。

CodeRev 的做法：

- **每条意见必须可定位**：文件、行号、规则 ID、置信度。定位不到的结论直接丢弃。
- **规则即代码**：`rules/*.yaml` 跟仓库走，社区提 PR 就能加规则，每条规则带 golden test。
- **自托管优先**：Docker 起一个，接自己的模型 key，代码不出内网。

---

## 两条产品线

| | **A 轨道：PR 审查** | **B 轨道：变更追溯** |
|---|---|---|
| 解决 | PR 自动审查、风险摘要、测试建议 | 需求变更从提出到签字的全链路留痕 |
| 形态 | GitHub Action / 自托管服务 | 变更单 + 台账 + 周报（模板） |
| 状态 | PRD 完成，代码未开始 | 设计与模板完成，观察期使用中 |

A 单独做只是"又一个审查工具"；接上 B 的「变更 ↔ 模块 ↔ 需求」数据，它才能说出"这个 PR 服务的是哪条需求、这条需求上个月改过三次"。

---

## 三条设计原则

1. **宁可少报，不可误报**。误报一次，用户流失的成本远高于漏报一次的收益。
2. **默认不阻断**。只评论、不卡合并；阻断是用户显式打开的开关。
3. **配置跟着仓库走**。`.coderev.yml` + `rules/`，能 diff、能 review、能回滚，不需要后台点表单。

---

## 文档

| 你想 | 读 |
|---|---|
| 30 分钟了解全貌 | [项目全貌](docs/00-overview.md) |
| 第一次参与 | [新人上手](docs/onboarding.md) |
| 看产品终局 | [平台愿景](docs/design/platform-vision.md) |
| 看审查引擎设计 | [PR 审查 PRD](docs/a/prd-pr-review.md) |
| 看变更流程设计 | [变更管理设计](docs/b/01-change-management-design.md) |
| 看开源化改造 | [开源化改造](docs/design/open-source-pivot.md) |
| 知道下一步做什么 | [路线图](ROADMAP.md) |

---

## 参与

- 提 issue：[文档纠错](https://github.com/qaeae/CodeRev/issues/new?template=doc-fix.yml) ｜ [功能建议](https://github.com/qaeae/CodeRev/issues/new?template=feature-request.yml)
- 提 PR：先读 [CONTRIBUTING.md](CONTRIBUTING.md)，分支模型见下
- 治理与决策：[GOVERNANCE.md](GOVERNANCE.md)
- 安全问题：[SECURITY.md](SECURITY.md)（**不要公开提 issue**）
- 行为准则：[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

### 分支模型

| 分支 | 内容 |
|---|---|
| `main` | 主干：门户 + A/B 两份轨道内容；只接受评审后的合并 |
| `feat/a-pr-review` | A 轨道工作分支 |
| `feat/b-change-trace` | B 轨道工作分支 |

从子分支切工作分支，不要直接改子分支；合并到 `main` 由 maintainer 执行。

---

## 许可

代码与文档采用 [Apache License 2.0](LICENSE)。
**商标不在此列**——可以 fork、可以商用，但不能用 CodeRev 的名字发布，见 [TRADEMARK.md](TRADEMARK.md)。

---

## 赞助

项目由贡献者业余维护。赞助用于 CI 分钟数、测试用模型 API、域名。见 [.github/FUNDING.yml](.github/FUNDING.yml)。
