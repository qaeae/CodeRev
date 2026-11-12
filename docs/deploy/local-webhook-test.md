# 没有公网 IP 时，怎么联调 webhook

> 适用：本机/内网机器，无法被 GitHub 直接回调。
> 原理：**出站隧道**。本机主动连到 Cloudflare，由它分配一个公网 HTTPS 地址，再把请求转发回 localhost。
> 不需要公网 IP、不需要路由器端口映射、不需要域名。

---

## 0. 前置检查

```bash
docker version --format '{{.Server.Version}}'   # 要能打印 Server 版本
docker compose ps                                # app 应为 healthy
```

如果 `docker version` 报 `failed to connect to the docker API`，先启动 Docker Desktop。

---

## 1. 准备密钥

编辑仓库根目录的 `.env`（已 gitignore），填两个值：

```ini
CODEREV_API_KEY=sk-...          # 模型 key
GITHUB_TOKEN=github_pat_...     # 需要目标仓库的 pull-requests: write
```

`CODEREV_WEBHOOK_SECRET` 保留原值即可，后面要原样填到 GitHub。

> **不需要改 `config/server.yml` 的 secret**，白名单在 `config/server.yml`，secret 在 `.env`。

---

## 2. 启动服务

```bash
docker compose up -d
docker compose logs -f app
```

看到这行说明就绪：

```
coderev 0.3.0 listening on http://0.0.0.0:8080 (allowlist=1 repos, db=data/coderev.db)
```

如果提示 `警告：当前 provider=mock`，说明 `.env` 没被读到 —— 确认 `CODEREV_PROVIDER=openai` 且在仓库根目录执行。

---

## 3. 起隧道（拿到公网地址）

### Windows

```bash
# 下载一次即可
curl -L -o tools/cloudflared.exe https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe

tools\cloudflared.exe tunnel --url http://localhost:8080 --no-autoupdate
```

### macOS / Linux

```bash
# macOS: brew install cloudflared   |   Linux: 见官方 release
cloudflared tunnel --url http://localhost:8080 --no-autoupdate
```

终端里会出现一段横幅，找到这一行：

```
https://<随机单词>-<随机单词>.trycloudflare.com
```

**这就是你的公网地址**。它绑在当前进程上：进程一停地址就失效，重启会换一个新的。

---

## 4. 配置 GitHub webhook

仓库 → `Settings` → `Webhooks` → `Add webhook`：

| 字段 | 值 |
|---|---|
| Payload URL | `https://<上面的地址>/webhook` |
| Content type | `application/json` |
| Secret | `.env` 里的 `CODEREV_WEBHOOK_SECRET` |
| SSL verification | Enable |
| Which events | Let me select individual events → 只勾 **Pull requests** |
| Active | ✅ |

保存后 GitHub 立刻发一个 `ping`。服务端返回 **204**（非 PR 事件，正常），日志出现：

```
webhook skipped: 忽略事件类型 'ping'
```

> 若 GitHub 显示 **401**：Secret 不一致。若显示 **503**：容器里的 `CODEREV_WEBHOOK_SECRET` 为空，检查 `.env` 后 `docker compose up -d`。

---

## 5. 验证

开一个改动代码的 PR，然后看日志：

```bash
docker compose logs -f app
```

预期：

```
reviewed <owner>/<repo>#12: 2 findings, 1 gaps
```

PR 里出现摘要评论 + inline 评论。再 push 一次，评论应**原地更新**，不重复堆积。

---

## 6. 排错

| 现象 | 原因 | 处理 |
|---|---|---|
| GitHub 显示 401 | Secret 不一致 | 两边对齐后重新 Deliver |
| GitHub 显示 503 | 容器没拿到 secret | 填 `.env` 后 `docker compose up -d` |
| GitHub 显示 204 但没审查 | 仓库不在白名单 / draft / 非 PR 事件 | 看日志 `webhook skipped:` |
| 202 但没有评论 | worker 失败 | 日志里找 `worker: ... 失败`，多半是 key 或 token 权限 |
| 本地 curl 不通 | 本机 DNS 解析不到 trycloudflare | 用 `curl --resolve host:443:<IP>` 绕过；GitHub 侧不受影响 |
| 隧道地址打不开 | cloudflared 进程已退出 | 重启隧道，地址会变，记得同步改 webhook |

---

## 7. 收尾

```bash
# 停隧道：Ctrl+C 或杀掉 cloudflared 进程
# 停服务
docker compose down

# 别忘了在 GitHub 上删掉测试用的 webhook
```

---

## 8. 正式部署怎么办

快速隧道只适合联调：地址随机、随进程消失。生产环境用其中之一：

- **命名隧道**（cloudflared 绑定域名，地址固定）
- **反代 + 固定域名**（Caddy / Nginx，见 [webhook.md](webhook.md)）
- **frp / 内网穿透服务**

配置方式见 [webhook.md](webhook.md) 第 4 节。
