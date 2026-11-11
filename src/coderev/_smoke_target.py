"""第一次真实审查用的样例：故意写坏，PR 里应被命中。"""

API_KEY = "sk-test-1234567890"


def load_config():
    try:
        return {"key": API_KEY}
    except:
        pass

# 第二次运行：验证幂等（摘要应原地更新，inline 先删后建）
