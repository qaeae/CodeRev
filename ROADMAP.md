# 路线图

> 这份路线图是**承诺的边界**，不是愿望清单。想加东西，先开 issue 讨论。

## 当前：v0.1 设计与文档（进行中）

- [x] 变更管理设计与四份模板（B 轨道）
- [x] PR 审查 PRD（A 轨道）
- [x] 平台愿景与变更影响引擎设计
- [x] 仓库门户、贡献指南、治理文件
- [ ] 开源化改造：License 落地、部署文档骨架

**这一版没有可运行代码。** 目标是让任何人 30 分钟内看懂要做什么、怎么参与。

---

## v0.2 GitHub Action MVP（进行中）

最小可用：一个 workflow 文件，PR 打开就出评论。

已完成：

- [x] diff 解析与新增行定位（`diff.py`）
- [x] 规则加载与匹配，rules-as-code（`rules.py`）
- [x] 结构化输出 + JSON 校验（`models.py`）
- [x] 守卫：路径 / 行号 / 置信度 / 去重 / 截断（`validate.py`）
- [x] Markdown 评论渲染（`render.py`）
- [x] 模型适配：Mock + OpenAI 兼容（`providers/`）
- [x] GitHub API：拉 PR diff、摘要评论、inline 评论、幂等更新（`github.py` / `publish.py`）
- [x] `action.yml`（composite action）
- [x] `.coderev.yml` 配置加载（`config.py`）
- [x] 32 个单测，离线可跑
- [x] Dockerfile + 部署文档（`docs/deploy/action.md`）

待完成：

- [x] 端到端验证：真实 PR 上跑通（DeepSeek），摘要评论 + 2 条 inline 评论，二次推送验证幂等
- [x] 部署文档 `docs/deploy/action.md`

**验收**：在一个真实仓库里，加 3 行 YAML 就能跑出第一条评论。✅ 2026-11-11 在 PR #1 上完成

> 实测：PR 触发 → 24 秒出结果；命中硬编码密钥（阻断）与裸 except（警告）；再次推送后摘要评论原地更新（同一 id），inline 评论先删后建，没有重复堆积。

---

## v0.3 自托管服务

> 任务拆解（可直接提 issue）：[docs/roadmap/v0.3-tasks.md](docs/roadmap/v0.3-tasks.md)

- [ ] `docker compose up` 一键起（Postgres + Redis + app）
- [ ] GitHub App 模式（自建 App，webhook 验签）
- [ ] 配置即代码：`.coderev.yml`
- [ ] 部署文档：Docker / 反代 / 备份

**验收**：不看源码，只按文档，30 分钟能跑起来。

---

## v0.4 规则即代码

- [ ] `rules/` 目录 + 加载器
- [ ] 每条规则带 golden test（bad / good / expected）
- [ ] CI 跑规则回归
- [ ] 社区规则包索引

**验收**：社区提一个规则 PR，不需要改核心代码。

---

## v0.5 测试闭环（进行中）

- [x] 测试缺口识别 + 测试点建议（输出 `test_gaps`，仅建议不执行）
- [ ] 覆盖率上报 API（JaCoCo / lcov / go-cover）
- [ ] 增量覆盖率评论

---

## v1.0 稳定

- [ ] 输出契约冻结（semver）
- [ ] 多平台：GitLab
- [ ] 评测集公开（脱敏）
- [ ] 至少 3 名 maintainer、2 个外部贡献者

---

## Non-goals

以下**明确不做**，提 issue 也会被关：

| 不做 | 原因 |
|---|---|
| IDE 插件 / 代码补全 | 与 Copilot、Cursor 正面竞争，无胜算 |
| 代码托管 / 项目管理 | 不重复造 GitLab、Jira |
| 自动合并、自动修复后直接提交 | 责任边界不清，事故成本高 |
| 官方托管 SaaS | 成本与滥用不可控；鼓励自托管 |
| 专有规则市场 | 规则应开源可审计 |

---

## 怎么影响路线

| 你想要 | 怎么做 |
|---|---|
| 加一个功能 | 开「功能 / 方案建议」issue，说明场景与替代方案 |
| 调整优先级 | 在相关 issue 下说明你的使用场景 + 影响多少人 |
| 自己动手 | 认领标了 `help wanted` 的 issue，先留言避免重复劳动 |

路线图每季度更新一次，变更记录在 issue 里。
