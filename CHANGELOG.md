# Changelog

本项目遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)，格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [Unreleased]

## [0.3.0] - 2026-11-11

从"能用 Action"到"能自托管常驻服务"。

### 新增

- **Webhook 常驻服务**：`POST /webhook` 接收 GitHub 回调，HMAC-SHA256 验签（常量时间比较），事件过滤（只看 PR、忽略 draft），仓库白名单
- **异步执行**：收到事件立即 202，有界线程池执行审查，**同一 PR 串行**，失败重试一次（退避可配）
- **三层去重**：delivery id（SQLite 主键）、同一 commit、同一 PR 串行
- **服务器配置**：`config/server.yml`（白名单、限流、worker 数），按 mtime **热重载**，无需重启
- **环境变量覆盖**：`CODEREV_PROVIDER` / `MODEL` / `BASE_URL` / `RULES` / `MIN_CONFIDENCE` / `MAX_FINDINGS` / `POST`
- **健康检查**：`/healthz`、`/readyz`（含已接收 delivery 计数）
- **Docker Compose**：`app` 服务 + 健康检查 + 数据卷；SQLite 持久化
- **镜像发布**：打 tag 自动构建推送 GHCR，带 OCI 标签
- **Docker 冒烟测试**：CI 里构建镜像、跑 mock 审查、探 `/healthz`

### 变更

- **审查逻辑抽成 `service.py`**：CLI 与 webhook worker 共用一份实现
- 镜像默认命令改为 `serve`，`EXPOSE 8080`；镜像内置 `rules/`
- `coderev pr` 先校验 token 再解析 provider，错误码更准确（4 = 拉取失败，3 = 模型失败，2 = 输出格式）

### 修复

- `coderev serve` 启动时引用未定义变量，导致容器 CrashLoop
- 建议代码块渲染多出一个空行

### 已知限制

- 认证仍用 **PAT**，不是 GitHub App（v0.4）
- 单实例 + SQLite；多实例需要先换共享存储
- 大 PR 超过 `max_changed_lines` 时是**截断 + 标注**，不是按风险挑选文件
- 真实 GitHub 回调尚未验证（需要公网地址，部署文档已给 cloudflared 方案）

### 验证

- 84 个单测通过（Python 3.11 / 3.12）
- 本机 Docker Compose 实测：签名正确 202、重复投递 200、签名错误 401、非白名单 204；worker 按 5s 退避重试；`/readyz` 计数正确

## [0.2.0] - 2026-11-11

第一个可用的版本：GitHub Action 接入，PR 一开就出评论。

### 新增

- **审查流水线**：diff 解析 → 规则匹配 → 模型调用 → 守卫校验 → 评论渲染（`diff.py` / `rules.py` / `prompt.py` / `validate.py` / `render.py`）
- **命令行**：`coderev review`（本地 diff）、`coderev pr`（GitHub PR）、`coderev rules validate`
- **规则即代码**：`rules/*.yaml` 随仓库走，支持 `**` 通配；内置 Java/Spring 与 Python 两套示例规则
- **守卫**：路径不在 diff、行号非新增、置信度不足、重复意见、超过上限，一律丢弃
- **幂等发布**：摘要评论按隐藏 marker 原地更新，inline 评论先删后建，重复推送不堆积
- **模型适配**：Mock（离线）+ 任意 OpenAI 兼容接口（DeepSeek / OpenAI / Moonshot / Ollama）
- **配置**：`.coderev.yml`，优先级 命令行 > 配置文件 > 默认值
- **测试缺口建议**：变更里没被测到的分支，输出 `test_gaps`，每条带用例建议（仅建议，不生成、不执行）
- **GitHub Action**：`action.yml`，3 行 YAML 接入；配置缺失时给出明确中文报错
- **工程**：Dockerfile、CI（Python 3.11/3.12）、39 个单测

### 修复

- Windows 控制台 GBK 编码导致输出崩溃
- 建议代码块多出一个空行
- Action 缺少 api-key 时只报 GitHub 原生错误，难以定位

### 已知限制

- 只支持 GitHub，GitLab 在 v1.0 路线图
- 不做全仓索引，只审本次 diff（刻意的成本选择）
- 测试建议不生成代码、不执行
- draft PR 也会触发（可在 workflow 里自行过滤）

### 验证

- 2026-11-11 在 PR #1 上完成端到端验证：24 秒出结果，命中硬编码密钥与裸 except；二次推送后摘要评论原地更新、inline 重建，无重复堆积。

[Unreleased]: https://github.com/qaeae/CodeRev/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/qaeae/CodeRev/releases/tag/v0.3.0
[0.2.0]: https://github.com/qaeae/CodeRev/releases/tag/v0.2.0
