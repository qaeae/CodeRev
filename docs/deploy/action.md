# 用 GitHub Action 跑 CodeRev

> 目标：3 步接入，PR 一开就出评论。不需要服务器，模型 key 用你自己的。

---

## 1. 准备模型 key

支持任何 OpenAI 兼容接口：

| 供应商 | base-url | model 示例 |
|---|---|---|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| Moonshot | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| Ollama（自建） | `http://your-host:11434/v1` | `qwen2.5-coder` |

把 key 存到仓库 Secrets：`Settings → Secrets and variables → Actions → New repository secret`，名字用 `CODEREV_API_KEY`。

---

## 2. 加一个 workflow

`.github/workflows/coderev.yml`：

```yaml
name: CodeRev

on:
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]

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
          rules: rules/examples
```

> **锁版本**：`@v0.2.0` 是发布标签，稳定；`@main` 跟随主线，可能有未发布改动。生产仓库建议锁标签。

提交后开一个 PR，Actions 里能看到运行过程，PR 里会出现一条摘要评论 + 若干 inline 评论。

---

## 3. 配置

在仓库根目录放 `.coderev.yml`（可从 [`.coderev.example.yml`](../../.coderev.example.yml) 复制）：

```yaml
version: 1
review:
  provider: openai
  model: deepseek-chat
  base_url: https://api.deepseek.com/v1
  rules: rules/examples
  min_confidence: 0.6
  max_findings: 8
  ignore_paths:
    - "**/generated/**"
```

优先级：**命令行参数 > `.coderev.yml` > 默认值**。

---

## 4. 权限与安全

- 必须给 `pull-requests: write`（回写评论），`contents: read`（读代码）。
- **不要**给 `contents: write`——CodeRev 不改代码。
- 模型 key 只通过 Secrets 注入，不会落盘。
- 审查过程**不执行**仓库里的任何代码，只读 diff 文本。

---

## 5. 成本控制

单次审查只调用模型一次（不分块），token 上限由 `max_findings` 和 diff 截断控制。
如果担心花钱，先把 `min_confidence` 调到 0.75、`max_findings` 调到 5。

---

## 6. 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| `403 Resource not accessible` | workflow 缺 `pull-requests: write` | 补权限后重跑 |
| 没有评论，日志显示跳过 | diff 里没有新增行（纯删除/纯重命名） | 正常行为 |
| `422 line must be part of the diff` | 模型给了不存在的行号 | 守卫本应拦截，若出现请提 issue |
| 评论重复堆积 | 旧版本没有幂等标记 | 升级到当前版本，会按 marker 去重 |
| 中文乱码 | runner 编码 | workflow 里加 `LANG=C.UTF-8` |

---

## 7. 已知限制（v0.2）

- 只支持 GitHub，GitLab 在 v1.0 路线图里。
- 不做全仓索引，只审本次 diff（这是刻意的成本选择）。
- draft PR 也会触发；如需跳过，自行在 workflow 里加 `if: github.event.pull_request.draft == false`。
