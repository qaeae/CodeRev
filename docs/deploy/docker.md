# Docker Compose 自托管

> 目标：一台装了 Docker 的机器，5 分钟跑起 CodeRev。

---

## 快速开始

```bash
git clone https://github.com/qaeae/CodeRev.git && cd CodeRev
cp .env.compose.example .env      # 填 CODEREV_API_KEY / MODEL / BASE_URL
docker compose up -d --build
curl localhost:8080/healthz
```

预期返回：

```json
{"status": "ok", "version": "0.2.0"}
```

> **已实测**（2026-11-11，Docker Desktop 29.5.3 / Linux 引擎）：
> `docker compose up -d --build` 构建成功 → `Up 25 seconds (healthy)` → `/healthz` 返回上述 JSON →
> `docker compose run --rm app --version` 输出 `coderev 0.2.0`。

---

## 现在能做什么

| 能力 | 状态 |
|---|---|
| 健康检查 `/healthz` `/readyz` | ✅ v0.3 |
| 命令行审查 | ✅ `docker run --rm coderev:local review ...` |
| **Webhook 常驻服务** | ✅ v0.3，配置见 [webhook.md](webhook.md) |

> 镜像默认启动 `coderev serve`（`docker run -p 8080:8080 coderev:local` 即可），EXPOSE 8080。
> 要接 GitHub 自动审查，按 [webhook.md](webhook.md) 配公网地址、白名单与 Secret；只想快速试跑用 [GitHub Action](action.md)。

### 在容器里跑一次审查

```bash
docker compose run --rm app review \
  --diff tests/fixtures/example.diff \
  --provider mock \
  --mock-response tests/fixtures/mock-response.json \
  --markdown
```

（mock 模式不需要 key，用来验证镜像是否正常。）

---

## 环境变量

| 变量 | 必填 | 说明 |
|---|---|---|
| `CODEREV_API_KEY` | 是（真实审查时） | 模型 key |
| `CODEREV_MODEL` | 是 | 如 `deepseek-chat` |
| `CODEREV_BASE_URL` | 否 | 默认 `https://api.openai.com/v1` |
| `CODEREV_PROVIDER` | 否 | `openai` / `mock` |
| `CODEREV_RULES` | 否 | 规则包路径 |
| `CODEREV_MIN_CONFIDENCE` | 否 | 0–1，默认 0.6 |
| `CODEREV_MAX_FINDINGS` | 否 | 默认 8 |
| `CODEREV_POST` | 否 | `true`/`false`，默认 true |

优先级：**命令行 > 环境变量 > `.coderev.yml` > 默认值**。

`docker compose` 会自动读取同目录的 `.env`。

---

## 使用官方镜像（GHCR）

自 **v0.3.0** 起，推 tag 会自动构建并发布镜像（`.github/workflows/publish-image.yml`）：

```bash
docker pull ghcr.io/qaeae/coderev:0.3.0
docker run --rm -p 8080:8080 ghcr.io/qaeae/coderev:0.3.0
```

| 标签 | 含义 |
|---|---|
| `0.3.0` / `v0.3.0` | 版本号，生产建议锁这个 |
| `sha-<short>` | 对应提交，便于回溯 |
| `latest` | 最新稳定版（`rc/beta/alpha/dev` 不会移动它） |

> 首次发布后包默认可能是 **private**：到仓库的 `Packages` 页面把可见性改成 `public`，否则别人拉不到。
> `v0.2.0` 早于该 workflow，没有对应镜像。

---

## 常用操作

```bash
docker compose logs -f app          # 看日志
docker compose restart app          # 重启
docker compose down                 # 停止（保留镜像）
docker compose up -d --build        # 改代码后重建
```

---

## 反向代理（可选）

想让 GitHub 回调进来（#3 之后），需要一个公网 HTTPS 地址。Caddy 最省事：

```
review.example.com {
    reverse_proxy 127.0.0.1:8080
}
```

---

## 升级与回滚

```bash
git fetch --tags
git checkout v0.2.0        # 或更新的 tag
docker compose up -d --build
```

回滚就是切回上一个 tag 再 build 一次。

---

## 排错

| 现象 | 原因 | 处理 |
|---|---|---|
| `failed to connect to the docker API` | Docker Desktop 没启动 | 启动 Docker Desktop，等引擎就绪（`docker version` 能返回 Server 版本） |
| 构建时 `failed to fetch anonymous token` | 连不上 Docker Hub | 先重试一次（常见瞬时失败），仍失败就配镜像加速器 |
| `healthcheck` 一直 starting | 端口被占用 | 改 `ports` 或停掉占用进程 |
| `curl` 连接被拒 | 容器没起来 | `docker compose logs app` |
| 构建失败在 `pip install` | 网络问题 | 配镜像源或重试 |
| `permission denied` | Docker 权限 | 把用户加入 `docker` 组 |

---

## 目录挂载说明

当前镜像**不挂载宿主目录**，也不需要持久化卷——审查是无状态的。
后续接入数据库时会在 `docker-compose.yml` 里启用 `db` 服务与卷。
