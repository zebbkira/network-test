# TCPing Monitor

持续 TCP Ping 网络监控工具，带有 Web 可视化面板。支持多目标监控、暂停/恢复、延迟图表和丢包统计。

## 功能特性

- **多目标监控** - 同时监控多个 `host:port` 的 TCP 连通性
- **实时 Web 面板** - 浏览器查看延迟趋势图、丢包率等统计
- **暂停 / 恢复** - 可随时暂停和恢复单个监控目标
- **数据持久化** - 使用 SQLite 存储探测记录，重启后自动恢复监控
- **REST API** - 完整的 API 接口，方便集成
- **单文件打包** - 支持 PyInstaller 打包为 Windows 可执行文件

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动服务

```bash
# 默认监听 127.0.0.1:8599
python main.py

# 自定义监听地址和端口
python main.py --host 0.0.0.0 --port 8080

# 启动时添加监控目标
python main.py --add baidu.com:443 google.com:80
```

启动后访问 [http://127.0.0.1:8599](http://127.0.0.1:8599) 打开 Web 面板。

## 项目结构

```
├── main.py                 # 入口文件
├── requirements.txt        # Python 依赖
├── static/
│   └── index.html          # Web 面板前端页面
├── data/
│   └── tcping.db           # SQLite 数据库（运行时生成）
└── tcping_monitor/
    ├── __init__.py
    ├── config.py            # 配置（路径、默认参数）
    ├── core.py              # TCP Ping 异步探测引擎
    ├── db.py                # 数据库操作层
    └── web.py               # FastAPI Web 服务与 API
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/targets` | 获取所有监控目标 |
| `POST` | `/api/targets` | 添加监控目标 `{"host": "...", "port": 443}` |
| `DELETE` | `/api/targets?host=...&port=...` | 删除监控目标 |
| `POST` | `/api/targets/pause` | 暂停监控 `{"host": "...", "port": 443}` |
| `POST` | `/api/targets/resume` | 恢复监控 `{"host": "...", "port": 443}` |
| `GET` | `/api/stats?target=...&port=...&minutes=60` | 获取统计数据 |
| `GET` | `/api/history?target=...&port=...&minutes=60` | 获取探测历史 |
| `GET` | `/api/losses?target=...&port=...&minutes=60` | 获取丢包记录 |

## 技术栈

- **后端**: Python 3, FastAPI, Uvicorn, aiosqlite
- **前端**: HTML / CSS / JavaScript（原生）
- **数据库**: SQLite
- **打包**: PyInstaller

## 许可证

MIT
