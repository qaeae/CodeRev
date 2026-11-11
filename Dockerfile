FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# 默认以非 root 运行
RUN useradd --create-home --uid 10001 coderev
USER coderev

ENTRYPOINT ["coderev"]
CMD ["--help"]
