@echo off
title Robot Bi
echo ========================================
echo    Robot Bi - Khoi dong he thong
echo ========================================

REM === Cloudflare Named Tunnel ===
REM De dung URL co dinh (khong thay doi sau moi restart):
REM 1. Tao tunnel tai https://one.dash.cloudflare.com
REM 2. Copy token vao .env: CLOUDFLARE_TUNNEL_TOKEN=eyJ...
REM 3. Copy URL vao .env:   CLOUDFLARE_TUNNEL_URL=https://ten-ban.domain.com
REM Neu de trong se dung quick tunnel (URL thay doi moi lan restart)

python sync.py

:: Tao SSL certificate neu chua co
if not exist "ssl\cert.pem" (
    echo [SSL] Tao SSL certificate...
    python generate_ssl.py
)

:loop
echo [%time%] Khoi dong Robot Bi...
python -m src_brain.main_loop
echo [%time%] Robot Bi da thoat. Khoi dong lai sau 5 giay...
timeout /t 5 /nobreak
goto loop
