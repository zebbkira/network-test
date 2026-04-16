"""
TCPing Monitor - 持续 TCP Ping 网络监控工具
用法:
  python main.py                           # 启动，默认监听 127.0.0.1:8599
  python main.py --add baidu.com:443       # 启动时添加监控目标
  python main.py --host 0.0.0.0 --port 80  # 自定义监听地址
"""
import argparse
import asyncio
import logging
import os
import sys
import uvicorn

# --noconsole 打包后 stdout/stderr 为 None，需重定向避免 uvicorn 日志崩溃
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from tcping_monitor.config import DEFAULT_WEB_HOST, DEFAULT_WEB_PORT
from tcping_monitor.core import TCPingEngine, PingResult
from tcping_monitor.db import Database
from tcping_monitor.web import create_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("tcping")


async def on_result(db: Database, result: PingResult):
    """探测结果回调 - 写入数据库"""
    await db.save_result(
        target=result.target,
        port=result.port,
        timestamp=result.timestamp,
        latency_ms=result.latency_ms,
        success=result.success,
        error_msg=result.error_msg,
    )


def parse_target(s: str):
    """解析 host:port 格式"""
    if ":" not in s:
        raise ValueError(f"格式错误: {s}，应为 host:port")
    parts = s.rsplit(":", 1)
    return parts[0], int(parts[1])


async def main_async(args):
    db = Database()
    await db.init()

    engine = TCPingEngine()
    engine.set_result_callback(lambda r: on_result(db, r))

    # 恢复之前保存的监控目标
    saved_targets = await db.get_targets()
    for t in saved_targets:
        engine.add_target(t["host"], t["port"])
        logger.info(f"恢复监控: {t['host']}:{t['port']}")

    # 添加命令行指定的目标
    if args.add:
        for target_str in args.add:
            try:
                host, port = parse_target(target_str)
                await db.add_target(host, port)
                engine.add_target(host, port)
                logger.info(f"添加监控: {host}:{port}")
            except (ValueError, IndexError) as e:
                logger.error(f"无法解析目标 '{target_str}': {e}")

    app = create_app(db, engine)

    logger.info(f"Web 面板: http://{args.host}:{args.port}")

    config = uvicorn.Config(
        app, host=args.host, port=args.port,
        log_level="warning", access_log=False,
    )
    server = uvicorn.Server(config)
    try:
        await server.serve()
    finally:
        engine.stop_all()
        await db.close()


def main():
    parser = argparse.ArgumentParser(description="TCPing Monitor - TCP Ping 网络监控")
    parser.add_argument("--host", default=DEFAULT_WEB_HOST, help="Web 面板监听地址")
    parser.add_argument("--port", type=int, default=DEFAULT_WEB_PORT, help="Web 面板监听端口")
    parser.add_argument("--add", nargs="*", metavar="HOST:PORT", help="启动时添加监控目标")
    args = parser.parse_args()

    try:
        asyncio.run(main_async(args))
    except KeyboardInterrupt:
        logger.info("已停止")


if __name__ == "__main__":
    main()
