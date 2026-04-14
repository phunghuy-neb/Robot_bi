@echo off
title Robot Bi
:loop
echo [%time%] Khoi dong Robot Bi...
python -m src_brain.main_loop
echo [%time%] Robot Bi da thoat. Khoi dong lai sau 5 giay...
timeout /t 5 /nobreak
goto loop
