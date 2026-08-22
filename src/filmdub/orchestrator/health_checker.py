"""
qwen-tts Service 健康检查器

定期检查 qwen-tts 服务健康状态，必要时触发重启
"""

import asyncio
import logging
from typing import Optional, Callable
from pathlib import Path
import subprocess
import json

logger = logging.getLogger(__name__)


class QwenTTSServiceHealthChecker:
    """qwen-tts 服务健康检查器"""

    def __init__(
        self,
        check_interval: int = 30,
        service_name: str = "qwen-tts.service",
        on_healthy: Optional[Callable] = None,
        on_unhealthy: Optional[Callable] = None,
        on_restarted: Optional[Callable] = None
    ):
        """
        初始化健康检查器

        Args:
            check_interval: 检查间隔（秒）
            service_name: systemd 服务名称
            on_healthy: 健康时回调
            on_unhealthy: 不健康时回调
            on_restarted: 重启后回调
        """
        self.check_interval = check_interval
        self.service_name = service_name
        self.on_healthy = on_healthy
        self.on_unhealthy = on_unhealthy
        self.on_restarted = on_restarted
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._unhealthy_count = 0
        self._max_unhealthy_before_restart = 3
        
        logger.info(
            f"QwenTTSServiceHealthChecker initialized: "
            f"interval={check_interval}s, service={service_name}"
        )

    async def check_service_health(self) -> bool:
        """
        检查服务健康状态

        Returns:
            是否健康
        """
        try:
            # 使用 systemctl 检查服务状态
            result = await asyncio.create_subprocess_exec(
                "systemctl",
                "is-active",
                self.service_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                status = stdout.decode().strip()
                is_healthy = status == "active"
                
                if is_healthy:
                    logger.debug(f"Service {self.service_name} is healthy: {status}")
                else:
                    logger.warning(f"Service {self.service_name} is not active: {status}")
                
                return is_healthy
            else:
                logger.error(f"Failed to check service status: {stderr.decode().strip()}")
                return False
                
        except FileNotFoundError:
            logger.error("systemctl command not found")
            return False
        except Exception as e:
            logger.error(f"Error checking service health: {e}")
            return False

    async def restart_service(self) -> bool:
        """
        重启服务

        Returns:
            是否成功
        """
        try:
            logger.info(f"Attempting to restart {self.service_name}...")
            
            result = await asyncio.create_subprocess_exec(
                "systemctl",
                "restart",
                self.service_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                logger.info(f"Successfully restarted {self.service_name}")
                
                # 等待服务启动
                await asyncio.sleep(5)
                
                # 触发重启回调
                if self.on_restarted:
                    await self.on_restarted()
                
                return True
            else:
                logger.error(f"Failed to restart service: {stderr.decode().strip()}")
                return False
                
        except Exception as e:
            logger.error(f"Error restarting service: {e}")
            return False

    async def _health_check_loop(self):
        """健康检查循环"""
        logger.info(f"Starting health check loop for {self.service_name}")
        
        while self._running:
            is_healthy = await self.check_service_health()
            
            if is_healthy:
                if self._unhealthy_count > 0:
                    logger.info(f"Service recovered after {self._unhealthy_count} unhealthy checks")
                    self._unhealthy_count = 0
                    
                if self.on_healthy:
                    await self.on_healthy()
            else:
                self._unhealthy_count += 1
                logger.warning(
                    f"Service unhealthy check {self._unhealthy_count}/"
                    f"{self._max_unhealthy_before_restart}"
                )
                
                if self.on_unhealthy:
                    await self.on_unhealthy()
                
                # 连续不健康达到阈值，尝试重启
                if self._unhealthy_count >= self._max_unhealthy_before_restart:
                    logger.warning(
                        f"Service unhealthy for {self._unhealthy_count} checks, "
                        f"attempting restart"
                    )
                    
                    success = await self.restart_service()
                    
                    if success:
                        self._unhealthy_count = 0
                    else:
                        logger.error("Failed to restart service, will retry on next check")
            
            # 等待下一次检查
            await asyncio.sleep(self.check_interval)

    async def start(self):
        """启动健康检查"""
        if self._running:
            logger.warning("Health checker is already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._health_check_loop())
        logger.info("Health checker started")

    async def stop(self):
        """停止健康检查"""
        if not self._running:
            return
        
        logger.info("Stopping health checker...")
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("Health checker stopped")

    def is_running(self) -> bool:
        """检查是否正在运行"""
        return self._running
