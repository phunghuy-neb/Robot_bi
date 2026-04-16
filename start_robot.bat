@echo off
title Robot Bi
echo ========================================
echo    Robot Bi - Khoi dong he thong
echo ========================================

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
