"""SSH隧道管理服务"""

import logging
import threading
import time
from typing import Optional

from sshtunnel import SSHTunnelForwarder

from shared.config import get_config
from shared.utils import decrypt_value

logger = logging.getLogger(__name__)


class SSHTunnelManager:
    """SSH隧道管理器（支持自动重连）"""

    def __init__(self):
        self.tunnel: Optional[SSHTunnelForwarder] = None
        self._config = get_config()
        self._ssh_config = None
        self._lock = threading.Lock()
        self._reconnect_thread: Optional[threading.Thread] = None
        self._should_stop = False
        self._max_retries = 5
        self._retry_delay = 2

    def start(self, ssh_config: dict) -> tuple[str, int]:
        """
        启动SSH隧道

        Args:
            ssh_config: SSH配置字典，包含:
                - host: SSH服务器地址
                - port: SSH端口
                - username: SSH用户名
                - auth_type: 认证类型 (password/key)
                - password: SSH密码（password模式）
                - key_path: SSH密钥路径（key模式）
                - encrypted_credential: 加密的密码或密钥路径（兼容旧格式）
                - remote_host: 远程MySQL主机
                - remote_port: 远程MySQL端口

        Returns:
            (local_host, local_port) 本地绑定地址和端口
        """
        self._ssh_config = ssh_config

        # 检查是否已有活跃隧道
        if self.tunnel and self.tunnel.is_active:
            logger.info("SSH隧道已经在运行")
            return self.tunnel.local_bind_host, self.tunnel.local_bind_port

        return self._start_tunnel()

    def _start_tunnel(self, retry_count: int = 0) -> tuple[str, int]:
        """内部启动隧道方法（支持重试）"""
        auth_type = self._ssh_config.get("auth_type", "password")

        ssh_kwargs = {
            "ssh_address_or_host": (self._ssh_config["host"], self._ssh_config.get("port", 22)),
            "ssh_username": self._ssh_config["username"],
            "remote_bind_address": (
                self._ssh_config.get("remote_host", "127.0.0.1"),
                self._ssh_config.get("remote_port", 3306),
            ),
            "local_bind_address": ("127.0.0.1", 0),  # 自动分配端口
        }

        if auth_type == "password":
            if self._ssh_config.get("password"):
                ssh_kwargs["ssh_password"] = self._ssh_config["password"]
            elif self._ssh_config.get("encrypted_credential"):
                ssh_kwargs["ssh_password"] = decrypt_value(self._ssh_config["encrypted_credential"])
        else:  # key
            from pathlib import Path
            if self._ssh_config.get("key_path"):
                ssh_kwargs["ssh_pkey"] = str(Path(self._ssh_config["key_path"]).expanduser())
            elif self._ssh_config.get("encrypted_credential"):
                ssh_kwargs["ssh_pkey"] = decrypt_value(self._ssh_config["encrypted_credential"])

        try:
            # 清理旧隧道
            if self.tunnel:
                try:
                    self.tunnel.stop()
                except Exception:
                    pass
                self.tunnel = None

            self.tunnel = SSHTunnelForwarder(**ssh_kwargs)
            self.tunnel.start()
            logger.info(
                f"SSH隧道已启动: {self.tunnel.local_bind_host}:{self.tunnel.local_bind_port}"
            )
            return self.tunnel.local_bind_host, self.tunnel.local_bind_port

        except Exception as e:
            logger.error(f"启动SSH隧道失败: {e}")
            if retry_count < self._max_retries:
                delay = self._retry_delay * (2 ** retry_count)  # 指数退避
                logger.info(f"将在 {delay} 秒后重试 ({retry_count + 1}/{self._max_retries})...")
                time.sleep(delay)
                return self._start_tunnel(retry_count + 1)
            raise

    def ensure_connection(self) -> Optional[tuple[str, int]]:
        """确保隧道连接正常，断开时自动重连"""
        with self._lock:
            if self.tunnel and self.tunnel.is_active:
                return self.tunnel.local_bind_host, self.tunnel.local_bind_port

            if not self._ssh_config:
                logger.warning("SSH配置未设置，无法重连")
                return None

            logger.warning("检测到SSH隧道断开，尝试重新连接...")
            try:
                return self._start_tunnel()
            except Exception as e:
                logger.error(f"SSH隧道重连失败: {e}")
                return None

    def stop(self):
        """停止SSH隧道"""
        self._should_stop = True
        with self._lock:
            if self.tunnel and self.tunnel.is_active:
                try:
                    self.tunnel.stop()
                    logger.info("SSH隧道已停止")
                except Exception as e:
                    logger.warning(f"停止SSH隧道时出错: {e}")
                finally:
                    self.tunnel = None

    def is_active(self) -> bool:
        """检查隧道是否活跃"""
        return self.tunnel is not None and self.tunnel.is_active

    def get_local_bind_address(self) -> Optional[tuple[str, int]]:
        """获取本地绑定地址"""
        if self.tunnel and self.tunnel.is_active:
            return self.tunnel.local_bind_host, self.tunnel.local_bind_port
        return None


# 全局单例
_tunnel_manager: Optional[SSHTunnelManager] = None


def get_tunnel_manager() -> SSHTunnelManager:
    """获取全局SSH隧道管理器"""
    global _tunnel_manager
    if _tunnel_manager is None:
        _tunnel_manager = SSHTunnelManager()
    return _tunnel_manager
