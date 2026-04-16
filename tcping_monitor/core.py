import asyncio
import time
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Awaitable

logger = logging.getLogger(__name__)


@dataclass
class PingResult:
    target: str
    port: int
    timestamp: float
    latency_ms: Optional[float]
    success: bool
    error_msg: Optional[str] = None


@dataclass
class TargetInfo:
    host: str
    port: int
    interval: float = 1.0
    timeout: float = 3.0
    paused: bool = False
    task: Optional[asyncio.Task] = field(default=None, repr=False)


class TCPingEngine:
    """持续 TCP Ping 探测引擎"""

    def __init__(self):
        self._targets: Dict[str, TargetInfo] = {}
        self._on_result: Optional[Callable[[PingResult], Awaitable[None]]] = None
        self._running = False

    def set_result_callback(self, callback: Callable[[PingResult], Awaitable[None]]):
        """设置探测结果回调（用于写入数据库）"""
        self._on_result = callback

    @staticmethod
    def make_key(host: str, port: int) -> str:
        return f"{host}:{port}"

    async def _ping_once(self, host: str, port: int, timeout: float) -> PingResult:
        """执行单次 TCP 连接探测"""
        ts = time.time()
        try:
            start = time.perf_counter()
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout,
            )
            elapsed = (time.perf_counter() - start) * 1000  # ms
            writer.close()
            await writer.wait_closed()
            return PingResult(
                target=host, port=port, timestamp=ts,
                latency_ms=round(elapsed, 2), success=True,
            )
        except asyncio.TimeoutError:
            return PingResult(
                target=host, port=port, timestamp=ts,
                latency_ms=None, success=False, error_msg="timeout",
            )
        except OSError as e:
            return PingResult(
                target=host, port=port, timestamp=ts,
                latency_ms=None, success=False, error_msg=str(e),
            )

    async def _ping_loop(self, info: TargetInfo):
        """对单个目标持续探测"""
        logger.info(f"开始监控 {info.host}:{info.port}")
        while True:
            if info.paused:
                await asyncio.sleep(0.5)
                continue
            result = await self._ping_once(info.host, info.port, info.timeout)
            if self._on_result:
                try:
                    await self._on_result(result)
                except Exception as e:
                    logger.error(f"结果回调异常: {e}")
            await asyncio.sleep(info.interval)

    def add_target(self, host: str, port: int,
                   interval: float = 1.0, timeout: float = 3.0) -> bool:
        """添加监控目标并立即开始探测"""
        key = self.make_key(host, port)
        if key in self._targets:
            return False
        info = TargetInfo(host=host, port=port, interval=interval, timeout=timeout)
        info.task = asyncio.get_event_loop().create_task(self._ping_loop(info))
        self._targets[key] = info
        return True

    def remove_target(self, host: str, port: int) -> bool:
        """移除监控目标"""
        key = self.make_key(host, port)
        info = self._targets.pop(key, None)
        if info is None:
            return False
        if info.task:
            info.task.cancel()
        logger.info(f"停止监控 {host}:{port}")
        return True

    def pause_target(self, host: str, port: int) -> bool:
        """暂停指定目标的探测"""
        key = self.make_key(host, port)
        info = self._targets.get(key)
        if info is None:
            return False
        info.paused = True
        logger.info(f"暂停监控 {host}:{port}")
        return True

    def resume_target(self, host: str, port: int) -> bool:
        """恢复指定目标的探测"""
        key = self.make_key(host, port)
        info = self._targets.get(key)
        if info is None:
            return False
        info.paused = False
        logger.info(f"恢复监控 {host}:{port}")
        return True

    def is_paused(self, host: str, port: int) -> bool:
        """检查目标是否暂停"""
        key = self.make_key(host, port)
        info = self._targets.get(key)
        return info.paused if info else False

    def get_targets(self) -> list:
        """获取当前所有监控目标"""
        return [{"host": t.host, "port": t.port, "key": k, "paused": t.paused}
                for k, t in self._targets.items()]

    def stop_all(self):
        """停止所有探测"""
        for info in self._targets.values():
            if info.task:
                info.task.cancel()
        self._targets.clear()
