from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import logging

from .config import get_static_dir

logger = logging.getLogger(__name__)


class AddTargetRequest(BaseModel):
    host: str
    port: int


def create_app(db, engine) -> FastAPI:
    app = FastAPI(title="TCPing Monitor")

    # ---------- API ----------

    @app.get("/api/targets")
    async def list_targets():
        # 合并数据库目标 + 引擎运行状态
        db_targets = await db.get_targets()
        for t in db_targets:
            t["paused"] = engine.is_paused(t["host"], t["port"])
        return db_targets

    @app.post("/api/targets")
    async def add_target(req: AddTargetRequest):
        host = req.host.strip()
        if not host or req.port < 1 or req.port > 65535:
            raise HTTPException(400, "无效的目标地址或端口")
        await db.add_target(host, req.port)
        engine.add_target(host, req.port)
        return {"ok": True, "msg": f"已添加 {host}:{req.port}"}

    @app.post("/api/targets/pause")
    async def pause_target(req: AddTargetRequest):
        ok = engine.pause_target(req.host, req.port)
        return {"ok": ok}

    @app.post("/api/targets/resume")
    async def resume_target(req: AddTargetRequest):
        ok = engine.resume_target(req.host, req.port)
        return {"ok": ok}

    @app.delete("/api/targets")
    async def delete_target(host: str, port: int):
        engine.remove_target(host, port)
        await db.remove_target(host, port)
        return {"ok": True}

    @app.get("/api/stats")
    async def get_stats(target: str, port: int, minutes: Optional[int] = None):
        return await db.get_stats(target, port, minutes)

    @app.get("/api/history")
    async def get_history(target: str, port: int, minutes: Optional[int] = 60):
        return await db.get_history(target, port, minutes)

    @app.get("/api/losses")
    async def get_losses(target: str, port: int, minutes: Optional[int] = None):
        return await db.get_losses(target, port, minutes)

    # ---------- 静态文件 ----------

    static_dir = get_static_dir()

    @app.get("/")
    async def index():
        return FileResponse(str(static_dir / "index.html"))

    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app
