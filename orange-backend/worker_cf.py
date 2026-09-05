
import sys
import os

# === 第一步：设置 CF 模式（必须在导入 cf_db_adapter 之前） ===
os.environ["CF_WORKER"] = "1"

# === 第二步：Mock resend 库（CF 环境不安装 resend） ===
class _ResendMock:
    api_key = None
sys.modules["resend"] = _ResendMock()

# === 第三步：Monkey-Patch sqlite3 -> D1 ===
from cf_db_adapter import set_cf_env

# === 第四步：导入 Flask 应用 ===
from app_cf import app, init_db

# === 第五步：初始化数据库（D1 支持 CREATE TABLE IF NOT EXISTS） ===
init_db()

# === 第六步：使用 pywrangler 包装 Flask 为 Workers 兼容 ===
try:
    from pywrangler import PyWrangler
    worker = PyWrangler(app)
except ImportError:
    # 降级方案：手动 WSGI 适配器
    from werkzeug.test import EnvironBuilder
    from werkzeug.wrappers import Response as WerkzeugResponse

    def handler(request, env, ctx):
        set_cf_env(env)

        # 读取请求体
        body = b""
        if request.body:
            body = request.body

        # 构建 WSGI 环境
        url = request.url
        headers = [(k, v) for k, v in request.headers.items()]
        builder = EnvironBuilder(
            method=request.method,
            path=url.path,
            query_string=url.query,
            headers=headers,
            body=body,
            content_length=len(body),
        )
        wsgi_env = builder.get_environ()

        # 调用 Flask
        response_body = []
        response_headers = []
        status_code = [500]

        def start_response(status, headers, exc_info=None):
            status_code[0] = int(status.split()[0])
            response_headers = [(h, v) for h, v in headers]

        result = app.wsgi_app(wsgi_env, start_response)
        if result:
            response_body = b"".join(result)

        # 返回 Workers Response
        from js import Response, Headers
        cf_headers = Headers()
        for h, v in response_headers:
            cf_headers.set(h, v)
        return Response(response_body, status=status_code[0], headers=cf_headers)