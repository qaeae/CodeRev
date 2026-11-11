# 贡献指南

> CodeRev 目前处于**设计阶段**：文档齐全，代码还没开始写。现在加入，你影响的是"它长成什么样"，而不只是修 bug。
> *This project is documented in Chinese. English issues and PRs are welcome.*

---

## 你能做的三类事

| 类型 | 从哪开始 | 适合 |
|---|---|---|
| **提问题 / 提方案** | [Issue 模板](https://github.com/qaeae/CodeRev/issues/new/choose) | 所有人，10 分钟 |
| **改文档** | 标了 `good first issue` 的文档任务 | 想先熟悉项目的人 |
| **写代码 / 写规则** | 见下方"开发环境" | 有一定工程经验 |

> 第一次参与，先读 [新人上手](docs/onboarding.md)。

---

## 开发环境

### 现在需要

| 工具 | 版本 | 用途 |
|---|---|---|
| Git | 2.30+ | 版本控制 |
| Python | 3.11+ | 文档生成脚本、后续后端 |
| Docker | 24+ | 本地跑 Postgres / Redis（v0.2 起） |

> **Windows 提示**：第一次跑 `docker compose` 前，先确认 `docker version` 能打印出 **Server 版本**。
> 如果报 `failed to connect to the docker API ... dockerDesktopLinuxEngine`，说明 Docker Desktop 没启动（不是项目问题）——
> 从开始菜单启动它，等鲸鱼图标变绿，或运行 `docker version` 直到能看到 Server 段。

### 本地跑起来（v0.2 之后才有）

```bash
git clone git@github.com:qaeae/CodeRev.git
cd CodeRev
pip install -e ".[dev]"
pytest -q                     # 17 个用例，全部离线
```

离线跑一次完整审查（不需要 API key）：

```bash
coderev review --diff tests/fixtures/example.diff --provider mock \
  --mock-response tests/fixtures/mock-response.json \
  --rules rules/examples --markdown
```

### 代码结构

```
src/coderev/
├── diff.py        解析 unified diff，产出「哪些行是新增的」
├── rules.py       加载 / 匹配规则包（rules-as-code）
├── prompt.py      拼 prompt：系统约束 + 规则 + diff
├── providers/     模型适配（mock 离线 / OpenAI 兼容）
├── validate.py    守卫：路径、行号、置信度、去重、截断
├── render.py      渲染成 GitHub 评论
└── cli.py         命令行入口
tests/             单元测试 + fixtures（真实 diff + 模型响应）
rules/examples/    示例规则包
```

**加功能前先想清楚它属于哪一层**：解析、规则、提示、校验、渲染各自的边界很清楚，跨层改动要先开 issue。

---

## 分支与提交

### 分支

| 分支 | 用途 |
|---|---|
| `main` | 门户文档与索引，只接受评审后的合并 |
| `feat/b-change-trace` | B 轨道（变更追溯） |
| `feat/a-pr-review` | A 轨道（PR 审查） |

**从子分支切你的工作分支，不要直接改子分支：**

```bash
git checkout feat/a-pr-review
git checkout -b feat/a-rules-loader
```

### 提交信息

```
<类型>(<范围>): <一句话>

类型：docs | feat | fix | refactor | chore | test
范围：a | b | design | rules | deploy
```

例：`feat(a): 支持从 .coderev.yml 加载规则包`

---

## PR 要求

1. **小而单一**。一个 PR 只做一件事；文档改动和代码改动分开提。
2. **自检清单全勾**。PR 模板里有 6 条，见 [pull_request_template](.github/pull_request_template.md)。
3. **关联 issue**。没有 issue 的 PR，先开 issue 讨论——避免写完被拒。
4. **文档同步**。改了行为就改文档；改了文档就检查链接。

---

## 规则包贡献规范

规则是本项目最重要的社区资产。一个新规则 = 一个 PR，包含：

```
rules/java-spring/transaction-boundary.yaml   # 规则定义
rules/java-spring/transaction-boundary/
  ├── bad.java                                # 正例：应命中
  ├── good.java                               # 反例：不应命中
  └── expected.json                           # 期望输出（行号 + 级别）
```

**要求**

- 每条规则必须带 `bad` / `good` 样例，CI 会跑 golden test。
- 规则的 `intent` 要写清楚"为什么这是问题"，不能只写"这不好"。
- 误报率是核心指标：**宁可少报，不可误报**。

---

## 评审与合并

- 小改动：**lazy consensus**——PR 发出后 7 天无人反对即合并。
- 大改动（改架构、改输出契约、加依赖）：先开 RFC issue，讨论通过再写代码。
- 合并由 maintainer 执行，作者不自行合并。

---

## 我们不接受什么

明确写在 [ROADMAP 的 Non-goals](ROADMAP.md#non-goals) 里。当前包括：IDE 插件、代码托管、自动合并、通用代码补全。提之前先看一眼，能省双方时间。

---

## 行为准则

参与即视为同意 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。违规会被警告、临时或永久移出社区。

---

## 许可

提交代码即表示你同意以 [Apache-2.0](LICENSE) 授权你的贡献，并授予项目使用你贡献中专利的权利（见 LICENSE 第 3、5 条）。
