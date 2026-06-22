"""UI 操作串行化锁。

鼠标/键盘/剪贴板/前台焦点是全局独占资源，多线程并发操作会互相打架，
故所有 UI 写操作用一个全局可重入锁串行化。
"""
import threading
import functools


class LockManager:
    """全局锁管理器。"""
    thread_lock = threading.RLock()


def uilock(func):
    """装饰器：保证被装饰的 UI 自动化方法串行执行。"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with LockManager.thread_lock:
            return func(*args, **kwargs)
    return wrapper
