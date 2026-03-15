"""平台兼容工具模块 - 集中处理 Windows/Unix 差异"""

import os
import signal
import sys
import time

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


def kill_process(pid: int, timeout: float = 3.0, force: bool = False):
    """
    终止进程（跨平台）

    Args:
        pid: 进程 ID
        timeout: 等待进程退出的超时时间（秒）
        force: 是否立即强制终止（跳过 SIGTERM）
    """
    if IS_WINDOWS:
        # Windows 下使用 taskkill 强制终止
        import subprocess

        subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        # Unix: 先发送 SIGTERM，等待后强制 SIGKILL
        try:
            if force:
                os.kill(pid, signal.SIGKILL)
            else:
                os.kill(pid, signal.SIGTERM)

                # 等待进程退出
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    if not is_process_running(pid):
                        return
                    time.sleep(0.1)

                # 超时后强制杀死
                if is_process_running(pid):
                    os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass  # 进程已经不存在


def kill_process_tree(pid: int, timeout: float = 5.0):
    """
    终止进程及其所有子进程（仅 Unix）

    Args:
        pid: 进程 ID
        timeout: 等待进程退出的超时时间（秒）
    """
    if IS_WINDOWS:
        # Windows 下使用 taskkill /F /T 终止进程树
        import subprocess

        subprocess.run(
            ["taskkill", "/PID", str(pid), "/F", "/T"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        try:
            # 发送 SIGTERM 到进程组
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                # 如果进程组不存在，只杀死进程本身
                os.kill(pid, signal.SIGTERM)

            # 等待进程退出
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if not is_process_running(pid):
                    return
                time.sleep(0.1)

            # 超时后强制杀死整个进程组
            if is_process_running(pid):
                try:
                    os.killpg(os.getpgid(pid), signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass  # 进程已经不存在


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
