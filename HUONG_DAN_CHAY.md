# Huong Dan Chay Robot Bi

## Yeu cau truoc khi chay
1. Ollama dang chay: `ollama serve` (terminal rieng)
2. Model da tai: `ollama pull qwen2.5:7b`
3. Co ket noi internet (edge-tts can internet lan dau)

## Cach chay

### Chay thu cong (test)
```
python -m src_brain.main_loop
```

### Chay tu dong restart khi crash (khuyen nghi)
```
start_robot.bat
```

## Truy cap Parent App
1. Chay robot
2. Quet QR code hien trong terminal
3. Hoac mo: `http://[IP-may-tinh]:8000`
4. PIN mac dinh: `123456`

## Doi PIN mac dinh
Tao file `.env` trong thu muc goc:
```
PIN_CODE=pin_moi_cua_ban
```

## Cai app len dien thoai (PWA)
1. Mo Chrome tren Android
2. Vao dia chi Parent App
3. Menu -> "Add to Home screen"
4. App hien trong man hinh home nhu app that

## Cau truc thu muc chinh
```
Robot_Bi_Project/
  src_brain/
    main_loop.py          <- Entry point chinh
    ai_core/core_ai.py    <- LLM (Qwen 2.5 7B)
    senses/ear_stt.py     <- STT (Whisper small)
    senses/mouth_tts.py   <- TTS (edge-tts + pyttsx3 fallback)
    memory_rag/           <- ChromaDB RAG
    network/api_server.py <- Parent App API
  start_robot.bat         <- Auto-restart script
  requirements.txt        <- Dependencies
```

## Debug
```bash
# Kiem tra Ollama
ollama list

# Test tung module
python src_brain/senses/ear_stt.py
python src_brain/senses/mouth_tts.py
python src_brain/ai_core/core_ai.py

# Chat text (khong can mic/loa)
python src_brain/train_text.py

# Do RAM va latency
python stress_test.py
```

## Khi co phan cung robot
1. Train openWakeWord model "bi_oi" tu 30+ audio samples
2. Dat model vao src_brain/senses/models/bi_oi.onnx
3. Set WAKEWORD_ENABLED = True trong ear_stt.py
4. Implement ESP32 motor control (Sprint 4)
