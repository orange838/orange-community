
import os
import asyncio
import sqlite3 as _sqlite3

IS_CF = os.getenv("CF_WORKER") == "1"
_cf_env = None


def set_cf_env(env):
    """在每次请求开始时调用，传入 CF Workers 的 env 对象"""
    global _cf_env
    _cf_env = env


if IS_CF:
    _original_connect = _sqlite3.connect

    def _patched_connect(*args, **kwargs):
        if _cf_env is None:
            raise RuntimeError("CF 环境未初始化，请先调用 set_cf_env()")
        return _D1Connection(_cf_env)

    _sqlite3.connect = _patched_connect


class _D1Connection:
    """D1 数据库连接适配器，伪装成 sqlite3.Connection"""

    def __init__(self, env):
        self.env = env

    def cursor(self):
        return _D1Cursor(self.env)

    def commit(self):
        pass  # D1 自动提交

    def close(self):
        pass


class _D1Cursor:
    """D1 游标适配器，伪装成 sqlite3.Cursor"""

    def __init__(self, env):
        self.env = env
        self._results = None

    def execute(self, query, params=()):
        async def _run():
            stmt = self.env.DB.prepare(query)
            if params:
                results = await stmt.bind(*params).all()
            else:
                results = await stmt.all()
            # D1 返回的是 dict 列表，转换为 tuple 列表以保持与原有代码兼容
            if results and isinstance(results[0], dict):
                columns = list(results[0].keys())
                return [tuple(row.get(col) for col in columns) for row in results]
            return results

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        self._results = loop.run_until_complete(_run())
        return self._results

    def fetchone(self):
        if self._results and len(self._results) > 0:
            return self._results[0]
        return None

    def fetchall(self):
        return self._results or []