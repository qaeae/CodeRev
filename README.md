# CodeRev

**开源免费的 PR 审查与变更追溯工具。自托管、BYOK、代码不出内网。**

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Status](https://img.shields.io/badge/release-v0.2.0-blue.svg)](CHANGELOG.md)

> **v0.2.0 已发布**：GitHub Action 可用，真实 PR 上验证过（24 秒出结果、评论幂等）。
> Before you start: everything here is documented in Chinese. English issues and PRs are welcome.

---

## 30 秒试跑（不需要 API key）

```bash
git clone git@github.com:qaeae/CodeRev.git && cd CodeRev
pip install -e ".[dev]"

# 用内置 mock 模型跑一遍完整流水线
coderev review \
  --diff tests/fixtures/example.diff \
  --provider mock \
  --mock-response tests/fixtures/mock-response.json \
  --rules rules/examples \
  --markdown
```

输出是一条可直接贴到 PR 的评论：命中 1 条问题，自动丢弃 4 条（路径不在 diff、行号不存在、置信度不足、重复）。

接真模型只需换参数：

```bash
export CODEREV_API_KEY=sk-...
coderev review --diff pr.diff --provider openai --model deepseek-chat \
  --base-url https://api.deepseek.com/v1 --rules rules/examples
```

---

## 接入 GitHub

```yaml
# .github/workflows/coderev.yml
on: [pull_request]
permissions:
  contents: read
  pull-requests: write
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: qaeae/CodeRev@v0.2.0
        with:
          api-key: ${{ secrets.CODEREV_API_KEY }}
          model: deepseek-chat
          base-url: https://api.deepseek.com/v1
```

> 建议锁版本（`@v0.2.0`）而不是 `@main`，避免上游改动直接影响你的 CI。升级时改这一行即可。

行为：

- 每次 PR 生成**一条摘要评论**（同一个 PR 重复跑会原地更新，不堆积）；
- 每条问题挂一条 **inline 评论**，带文件、行号、规则、置信度；
- 无法定位或置信度不足的意见**直接丢弃**，不会出现在 PR 里。

详见 [部署文档](docs/deploy/action.md)。配置写 `.coderev.yml`（见 [示例](.coderev.example.yml)），优先级：**命令行 > 环境变量 > 配置文件 > 默认值**。

## 自托管（Docker Compose）

```bash
cp .env.compose.example .env    # 填 CODEREV_API_KEY / MODEL / BASE_URL
docker compose up -d --build
curl localhost:8080/healthz     # {"status":"ok","version":"0.2.0"}
```

也可以直接用官方镜像（自 v0.3.0 起）：`docker run --rm -p 8080:8080 ghcr.io/qaeae/coderev:0.3.0`

当前镜像提供健康检查（`/healthz`、`/readyz`）与 GitHub webhook 常驻服务（验签、去重、异步审查）。
部署细节见 [docs/deploy/docker.md](docs/deploy/docker.md)；接 GitHub 的完整步骤见 [docs/deploy/webhook.md](docs/deploy/webhook.md)。

---

## 它解决什么问题

AI 审查工具已经很多，但有三个坑没人填：

1. **误报淹没一切**。每天 5 条"这行建议加个注释"，团队第二周就把它关了。
2. **审查和需求脱节**。模型不知道这个 PR 服务哪条需求，只能按通用规则挑毛病。
3. **规则不可控**。想加一条团队规范，得去某个后台点表单，不能 review、不能 diff、不能回滚。

CodeRev 的做法：

- **每条意见必须可定位**：文件、行号、规则 ID、置信度。定位不到的结论直接丢弃。
- **规则即代码**：`rules/*.yaml` 跟仓库走，社区提 PR 就能加规则，每条规则带 golden test。
- **顺手指出测试缺口**：变更里没被测到的分支，给 3 条以内的用例建议——**只建议，不生成代码、不执行**。
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
