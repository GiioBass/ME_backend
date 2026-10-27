#!/usr/bin/env python3
"""
Mystic Explorers - Backend Launcher
Inicia el servidor FastAPI con Uvicorn, detectando automáticamente la IP local y el entorno virtual.
"""

import os
import sys
import socket
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

# 1. Asegurar uso del entorno virtual 'venv' si existe y no está activo
VENV_PYTHON = os.path.join(BASE_DIR, "venv", "bin", "python")
if os.path.exists(VENV_PYTHON) and sys.executable != VENV_PYTHON:
    # Re-ejecutar con el Python del virtualenv
    try:
        os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)
    except Exception as e:
        print(f"Aviso: No se pudo conmutar al venv: {e}")

# 2. Verificar archivo de variables de entorno (.env)
env_file = os.path.join(BASE_DIR, ".env")
env_example = os.path.join(BASE_DIR, ".env.example")
if not os.path.exists(env_file) and os.path.exists(env_example):
    import secrets
    with open(env_example, "r") as f:
        content = f.read()
    new_secret = secrets.token_hex(32)
    content = content.replace("SECRET_KEY=your_secret_key_here", f"SECRET_KEY={new_secret}")
    with open(env_file, "w") as f:
        f.write(content)
    print("✅ Archivo .env generado automáticamente.")

# 3. Detectar IP local de red para facilitar conexión móvil
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

LOCAL_IP = get_local_ip()
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8001))

# 4. Liberar puerto si está ocupado
try:
    pids = subprocess.check_output(["lsof", "-ti", f":{PORT}"], stderr=subprocess.DEVNULL).decode().strip().split()
    for pid in pids:
        if pid and int(pid) != os.getpid():
            print(f"⚠️  Liberando puerto {PORT} (PID anterior: {pid})...")
            subprocess.run(["kill", "-9", pid], stderr=subprocess.DEVNULL)
except Exception:
    pass

# 5. Banner informativo
print("=" * 58)
print("    🚀 Mystic Explorers - Servidor Backend (FastAPI)")
print("=" * 58)
print(f"📡 Direcciones de enlace:")
print(f"   - Local (PC):         http://127.0.0.1:{PORT}")
print(f"   - App Móvil / Red:    http://{LOCAL_IP}:{PORT}")
print(f"   - Swagger UI (Docs):  http://127.0.0.1:{PORT}/docs")
print(f"   - WebSocket Link:     ws://{LOCAL_IP}:{PORT}/ws")
print()
print(f"💡 En la App Móvil (Pestaña 'Servidor'):")
print(f"   Configura Host: {LOCAL_IP}  |  Puerto: {PORT}")
print("=" * 58)
print(f"Iniciando Uvicorn en {HOST}:{PORT}...")
print()

# 6. Iniciar Uvicorn
import uvicorn
if __name__ == "__main__":
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
