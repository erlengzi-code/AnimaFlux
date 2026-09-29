"""Web 错误映射（§Web Plan §17）。

Web 只把 Core / 请求错误映射成稳定的 HTTP Error，不吞掉核心错误语义，不向浏览器返回堆栈。
错误 code 为稳定字符串（如 LIFE_NOT_FOUND），message 为面向人的可读说明。
"""

from __future__ import annotations


class WebError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


def life_not_found(life_id: str) -> WebError:
    return WebError("LIFE_NOT_FOUND", f"life '{life_id}' not found", 404)


def branch_not_found(branch_id: str) -> WebError:
    return WebError("BRANCH_NOT_FOUND", f"branch '{branch_id}' not found", 404)


def namespace_not_found(namespace: str) -> WebError:
    return WebError("NAMESPACE_NOT_FOUND", f"namespace '{namespace}' not found", 404)


def checkpoint_not_found(checkpoint_id: str) -> WebError:
    return WebError("CHECKPOINT_NOT_FOUND", f"checkpoint '{checkpoint_id}' not found", 404)


def validation_error(message: str) -> WebError:
    return WebError("VALIDATION_ERROR", message, 422)


def no_world(life_id: str) -> WebError:
    return WebError("NO_WORLD", f"life '{life_id}' has no world/scenario", 409)
