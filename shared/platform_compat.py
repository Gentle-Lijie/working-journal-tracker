"""平台兼容工具模块 - 集中处理 Windows/Unix 差异"""

import os
import signal
import sys

IS_WINDOWS = sys.platform == "win32"


def is_process_running(pid: int) -> bool:
    """检查进程是否在运行"""
    if IS_WINDOWS:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        # PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = kernel32.OpenProcess(0x1000, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False


def kill_process(pid: int):
    """终止进程（跨平台）"""
    if IS_WINDOWS:
        # Windows 下使用 taskkill 强制终止
        import subprocess

        subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        os.kill(pid, signal.SIGTERM)


def secure_chmod(path, mode=0o600):
    """设置文件权限（Windows 下跳过，ACL 模型不同）"""
    if not IS_WINDOWS:
        os.chmod(path, mode)


def detach_process_args() -> dict:
    """返回 subprocess.Popen 的平台特定参数，用于创建分离进程"""
    if IS_WINDOWS:
        import subprocess

        return {
            "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.DETACHED_PROCESS
        }
    else:
        return {"start_new_session": True}
