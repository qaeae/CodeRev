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
- [x] 17 个单测，离线可跑
- [x] Dockerfile

待完成：

- [ ] GitHub API：拉 PR diff、回写 inline 评论、更新已有评论（幂等）
- [ ] `action.yml`（composite 或 docker action）
- [ ] `.coderev.yml` 配置加载（替代一堆命令行参数）
- [ ] 端到端测试仓库（真实 PR 上跑通）

**验收**：在一个真实仓库里，加 3 行 YAML 就能跑出第一条评论。

---

## v0.3 自托管服务

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

## v0.5 测试闭环

- [ ] 测试缺口识别 + 测试点建议
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
