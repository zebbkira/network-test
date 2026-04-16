import aiosqlite
import time
import logging
from typing import List, Dict, Any, Optional
from .config import get_db_path

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS ping_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target TEXT NOT NULL,
    port INTEGER NOT NULL,
    timestamp REAL NOT NULL,
    latency_ms REAL,
    success INTEGER NOT NULL,
    error_msg TEXT
);
"""
CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_target_ts ON ping_log (target, port, timestamp);
"""
CREATE_TARGETS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    host TEXT NOT NULL,
    port INTEGER NOT NULL,
    added_at REAL NOT NULL,
    UNIQUE(host, port)
);
"""


class Database:
    def __init__(self):
        self._db_path = str(get_db_path())
        self._db: Optional[aiosqlite.Connection] = None

    async def init(self):
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute(CREATE_TABLE_SQL)
        await self._db.execute(CREATE_INDEX_SQL)
        await self._db.execute(CREATE_TARGETS_TABLE_SQL)
        await self._db.commit()
        logger.info(f"数据库已初始化: {self._db_path}")

    async def close(self):
        if self._db:
            await self._db.close()

    async def save_result(self, target: str, port: int, timestamp: float,
                          latency_ms: Optional[float], success: bool,
                          error_msg: Optional[str] = None):
        await self._db.execute(
            "INSERT INTO ping_log (target, port, timestamp, latency_ms, success, error_msg) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (target, port, timestamp, latency_ms, 1 if success else 0, error_msg),
        )
        await self._db.commit()

    async def add_target(self, host: str, port: int) -> bool:
        try:
            await self._db.execute(
                "INSERT OR IGNORE INTO targets (host, port, added_at) VALUES (?, ?, ?)",
                (host, port, time.time()),
            )
            await self._db.commit()
            return True
        except Exception as e:
            logger.error(f"添加目标失败: {e}")
            return False

    async def remove_target(self, host: str, port: int):
        await self._db.execute("DELETE FROM targets WHERE host=? AND port=?", (host, port))
        await self._db.commit()

    async def get_targets(self) -> List[Dict[str, Any]]:
        cursor = await self._db.execute("SELECT host, port FROM targets")
        rows = await cursor.fetchall()
        return [{"host": r["host"], "port": r["port"]} for r in rows]

    async def get_history(self, target: str, port: int,
                          minutes: Optional[int] = 60) -> List[Dict[str, Any]]:
        if minutes:
            since = time.time() - minutes * 60
            cursor = await self._db.execute(
                "SELECT timestamp, latency_ms, success, error_msg "
                "FROM ping_log WHERE target=? AND port=? AND timestamp>=? "
                "ORDER BY timestamp ASC",
                (target, port, since),
            )
        else:
            cursor = await self._db.execute(
                "SELECT timestamp, latency_ms, success, error_msg "
                "FROM ping_log WHERE target=? AND port=? "
                "ORDER BY timestamp ASC",
                (target, port),
            )
        rows = await cursor.fetchall()
        return [
            {
                "timestamp": r["timestamp"],
                "latency_ms": r["latency_ms"],
                "success": bool(r["success"]),
                "error_msg": r["error_msg"],
            }
            for r in rows
        ]

    async def get_stats(self, target: str, port: int,
                        minutes: Optional[int] = None) -> Dict[str, Any]:
        if minutes:
            since = time.time() - minutes * 60
            where = "WHERE target=? AND port=? AND timestamp>=?"
            params = (target, port, since)
        else:
            where = "WHERE target=? AND port=?"
            params = (target, port)

        cursor = await self._db.execute(
            f"SELECT COUNT(*) as total, "
            f"SUM(CASE WHEN success=0 THEN 1 ELSE 0 END) as lost, "
            f"AVG(CASE WHEN success=1 THEN latency_ms END) as avg_ms, "
            f"MIN(CASE WHEN success=1 THEN latency_ms END) as min_ms, "
            f"MAX(CASE WHEN success=1 THEN latency_ms END) as max_ms "
            f"FROM ping_log {where}",
            params,
        )
        row = await cursor.fetchone()
        total = row["total"] or 0
        lost = row["lost"] or 0
        return {
            "total": total,
            "lost": lost,
            "loss_rate": round(lost / total * 100, 2) if total > 0 else 0,
            "avg_ms": round(row["avg_ms"], 2) if row["avg_ms"] else None,
            "min_ms": round(row["min_ms"], 2) if row["min_ms"] else None,
            "max_ms": round(row["max_ms"], 2) if row["max_ms"] else None,
        }

    async def get_losses(self, target: str, port: int,
                         minutes: Optional[int] = None) -> List[Dict[str, Any]]:
        if minutes:
            since = time.time() - minutes * 60
            cursor = await self._db.execute(
                "SELECT timestamp, error_msg FROM ping_log "
                "WHERE target=? AND port=? AND success=0 AND timestamp>=? "
                "ORDER BY timestamp DESC LIMIT 500",
                (target, port, since),
            )
        else:
            cursor = await self._db.execute(
                "SELECT timestamp, error_msg FROM ping_log "
                "WHERE target=? AND port=? AND success=0 "
                "ORDER BY timestamp DESC LIMIT 500",
                (target, port),
            )
        rows = await cursor.fetchall()
        return [{"timestamp": r["timestamp"], "error_msg": r["error_msg"]} for r in rows]
