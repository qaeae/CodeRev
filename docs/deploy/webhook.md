# Webhook 常驻服务部署

> 目标：把 CodeRev 跑成常驻服务，GitHub 上一开 PR 就自动审查。
> 与 GitHub Action 的区别：Action 每次跑在 GitHub 的机器上；常驻服务跑在你自己的机器上，**代码不出内网**。

---

## 1. 前置条件

| 需要 | 说明 |
|---|---|
| 一台能跑 Docker 的机器 | 2C2G 足够 |
| 一个公网 HTTPS 地址 | GitHub 只能回调公网地址；内网机器用 tunnel 或反代 |
| GitHub PAT | fine-grained，权限：`Contents: read`、`Pull requests: write` |
| 模型 key | 任何 OpenAI 兼容接口 |

---

## 2. 配置

### 2.1 白名单（服务端维护）

```bash
cp config/server.example.yml config/server.yml
```

编辑 `repos:`，只写**允许使用本服务**的仓库：

```yaml
repos:
  - your-org/your-repo

limits:
  max_changed_lines: 1500
```

> 这份文件在服务端，不在被审仓库里——仓库无权把自己加进白名单。
> 改完不用重启，服务按 mtime 自动重载。

### 2.2 环境变量

```bash
cp .env.compose.example .env
```

填四项：

```ini
CODEREV_API_KEY=sk-...
CODEREV_MODEL=deepseek-chat
CODEREV_BASE_URL=https://api.deepseek.com/v1

CODEREV_WEBHOOK_SECRET=<自己生成一串随机字符>
GITHUB_TOKEN=github_pat_...
```

生成 secret：

```bash
openssl rand -hex 24
```

---

## 3. 启动

```bash
docker compose up -d --build
docker compose logs -f app
```

看到这行就说明起来了：

```
coderev 0.2.0 listening on http://0.0.0.0:8080 (allowlist=1 repos, db=data/coderev.db)
```

---

## 4. 让 GitHub 能访问到

GitHub 的回调地址必须是**公网 HTTPS**。三种方式：

### A. cloudflared（最快，适合试用）

```bash
cloudflared tunnel --url http://localhost:8080
```

它会输出一个 `https://xxx.trycloudflare.com` 地址，临时可用（重启就变）。

### B. 固定域名 + 反代

Caddy：

```
review.example.com {
    reverse_proxy 127.0.0.1:8080
}
```

### C. 内网穿透工具

frp / ngrok 同理。

---

## 5. 在 GitHub 上配置 webhook

仓库 → `Settings` → `Webhooks` → `Add webhook`：

| 字段 | 值 |
|---|---|
| Payload URL | `https://<你的地址>/webhook` |
| Content type | `application/json` |
| Secret | 与 `CODEREV_WEBHOOK_SECRET` 一致 |
| Which events | **Let me select individual events** → 只勾 **Pull requests** |
| Active | ✅ |

保存后 GitHub 会立刻发一个 `ping` 事件。服务端返回 204（忽略非 PR 事件），这是正常的。

---

## 6. 验证

开一个 PR（改动里带点真代码），然后：

```bash
docker compose logs -f app
```

预期看到：

```
reviewed your-org/your-repo#12: 2 findings, 1 gaps
```

PR 里出现摘要评论 + inline 评论。

再 push 一次，评论应**原地更新**，不重复堆积。

---

## 7. 排错

| 现象 | 原因 | 处理 |
|---|---|---|
| GitHub 显示 `401` | Secret 不一致 | 两边重新对齐 |
| GitHub 显示 `204` 且没有审查 | 仓库不在白名单 / 不是 PR 事件 / draft | 看 `docker compose logs` 里的 `webhook skipped:` |
| `503 webhook secret not configured` | `.env` 没填或没重启 | 填好后 `docker compose up -d` |
| `202` 但没有评论 | worker 失败（模型 401 / token 权限） | 日志里看 `worker: ... 失败` |
| 评论重复堆积 | 用的是旧版本 | 升级到 v0.3+ |
| 容器起不来 | 端口占用 / 镜像构建失败 | `docker compose logs app` |

---

## 8. 安全提醒

- `GITHUB_TOKEN` 和模型 key **只放 `.env`**，不要提交。
- PAT 权限收窄到需要的仓库；定期轮换。
- 服务暴露在公网，只有 `/webhook` 需要外网可达；`/healthz`、`/runs/*` 可以考虑在反代层限制来源。
- 服务**不执行**仓库代码，只读 diff。

---

## 9. 与 GitHub Action 怎么选

| | Webhook 常驻服务 | GitHub Action |
|---|---|---|
| 代码位置 | 自己的机器 | GitHub 的 runner |
| 首次配置 | 较重（公网地址、webhook、PAT） | 3 行 YAML |
| 内网仓库 | ✅ 可以用 | ❌ 用不了 |
| 成本 | 自己的机器 + 模型调用 | GitHub 分钟数 + 模型调用 |
| 推荐 | 企业 / 私有仓库 | 开源项目 / 快速试用 |
