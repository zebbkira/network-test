import os
import sys
from pathlib import Path


def get_base_dir() -> Path:
    """获取基础目录，兼容 PyInstaller 打包后的路径"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def get_static_dir() -> Path:
    """获取静态文件目录，兼容 PyInstaller 打包"""
    if getattr(sys, "frozen", False):
        # PyInstaller --add-data 解压到 _MEIPASS
        return Path(sys._MEIPASS) / "static"
    return Path(__file__).resolve().parent.parent / "static"


def get_db_path() -> Path:
    """获取数据库文件路径"""
    db_dir = get_base_dir() / "data"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "tcping.db"


# 默认配置
DEFAULT_INTERVAL = 1.0   # 探测间隔（秒）
DEFAULT_TIMEOUT = 3.0    # 连接超时（秒）
DEFAULT_WEB_HOST = "127.0.0.1"
DEFAULT_WEB_PORT = 8599
