"""SSH隧道管理服务"""

import logging
from typing import Optional

from sshtunnel import SSHTunnelForwarder

from shared.config import get_config
from shared.utils import decrypt_value

logger = logging.getLogger(__name__)


class SSHTunnelManager:
    """SSH隧道管理器"""

    def __init__(self):
        self.tunnel: Optional[SSHTunnelForwarder] = None
        self._config = get_config()

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
        if self.tunnel and self.tunnel.is_active:
            logger.info("SSH隧道已经在运行")
            return self.tunnel.local_bind_host, self.tunnel.local_bind_port

        auth_type = ssh_config.get("auth_type", "password")

        ssh_kwargs = {
            "ssh_address_or_host": (ssh_config["host"], ssh_config.get("port", 22)),
            "ssh_username": ssh_config["username"],
            "remote_bind_address": (
                ssh_config.get("remote_host", "127.0.0.1"),
                ssh_config.get("remote_port", 3306),
            ),
            "local_bind_address": ("127.0.0.1", 0),  # 自动分配端口
        }

        if auth_type == "password":
            # 优先使用明文密码，兼容加密格式
            if ssh_config.get("password"):
                ssh_kwargs["ssh_password"] = ssh_config["password"]
            elif ssh_config.get("encrypted_credential"):
                ssh_kwargs["ssh_password"] = decrypt_value(ssh_config["encrypted_credential"])
        else:  # key
            from pathlib import Path
            if ssh_config.get("key_path"):
                ssh_kwargs["ssh_pkey"] = str(Path(ssh_config["key_path"]).expanduser())
            elif ssh_config.get("encrypted_credential"):
                ssh_kwargs["ssh_pkey"] = decrypt_value(ssh_config["encrypted_credential"])

        try:
            self.tunnel = SSHTunnelForwarder(**ssh_kwargs)
            self.tunnel.start()
            logger.info(
                f"SSH隧道已启动: {self.tunnel.local_bind_host}:{self.tunnel.local_bind_port}"
            )
            return self.tunnel.local_bind_host, self.tunnel.local_bind_port
        except Exception as e:
            logger.error(f"启动SSH隧道失败: {e}")
            raise

    def stop(self):
        """停止SSH隧道"""
        if self.tunnel and self.tunnel.is_active:
            self.tunnel.stop()
            logger.info("SSH隧道已停止")
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
