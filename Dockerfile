FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

EXPOSE 8080

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# 自带示例规则包：自托管时开箱可用
COPY rules ./rules

# 默认以非 root 运行
RUN useradd --create-home --uid 10001 coderev
# 预建数据目录并授权：命名卷首次挂载会继承这里的属主
RUN mkdir -p /app/data && chown -R coderev:coderev /app/data
USER coderev

ENTRYPOINT ["coderev"]
# 默认起服务（健康检查在 /healthz）；命令行用法：docker run --rm coderev:local review ...
CMD ["serve", "--host", "0.0.0.0", "--port", "8080"]
