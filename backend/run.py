#!/usr/bin/env python3
"""
Deep Research Agent - Web 全栈一体化服务一键启动脚本
自动检测可用端口并启动 FastAPI (含 React 现代化前端界面)
"""

import sys
import socket
from pathlib import Path

# 确保 backend 目录在 sys.path 中
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

def is_port_in_use(port: int) -> bool:
    """检测端口是否已被占用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def find_available_port(preferred_port: int = 8000) -> int:
    """寻找可用端口"""
    for p in [preferred_port, 8001, 8080, 8888, 5000]:
        if not is_port_in_use(p):
            return p
    return preferred_port

if __name__ == "__main__":
    import uvicorn
    
    port = find_available_port(8000)
    
    print("=" * 70)
    print("🚀 Deep Research Agent (AI 深度研究助手) 服务已启动！")
    print(f"✨ 现代化 Web 前端交互界面: http://127.0.0.1:{port}")
    print(f"📖 Swagger 在线 API 接口文档: http://127.0.0.1:{port}/docs")
    print(f"🩺 后端服务健康检查:         http://127.0.0.1:{port}/health")
    print("=" * 70 + "\n")
    
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
