# Huong Dan Chay Robot Bi

## Yeu cau truoc khi chay
1. Dien API key vao file `.env`:
   - `GROQ_API_KEY` — lay tai console.groq.com (free tier: 14.400 req/ngay)
   - `GEMINI_API_KEY` — lay tai aistudio.google.com (free tier: 1.000 req/ngay)
2. Co ket noi internet (Groq + Gemini API + edge-tts can internet)

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
Them vao file `.env`:
```
PIN_CODE=pin_moi_cua_ban
```

## Tao tai khoan lan dau
1. Mo `.env`, dat `REGISTRATION_ENABLED=true`
2. Khoi dong robot
3. Mo app, dang ky tai khoan admin
4. Tat lai: `REGISTRATION_ENABLED=false`, restart robot

## Cai app len dien thoai (PWA)
1. Mo Chrome tren Android
2. Vao dia chi Parent App
3. Menu -> "Add to Home screen"
4. App hien trong man hinh home nhu app that

## Cau truc thu muc chinh
```
Robot_Bi_Project/
  .env                         <- API keys (KHONG commit)
  config.json                  <- Cau hinh robot
  src_brain/
    main_loop.py               <- Entry point chinh
    ai_core/core_ai.py         <- LLM (Groq Llama 70B / Gemini Flash-Lite)
    senses/ear_stt.py          <- STT (Whisper large-v2 CUDA)
    senses/mouth_tts.py        <- TTS (edge-tts + pyttsx3 fallback)
    memory_rag/                <- ChromaDB RAG
    network/api_server.py      <- Parent App API
  start_robot.bat              <- Auto-restart script
  requirements.txt             <- Dependencies
```

## Debug
```bash
# Test tung module
python src_brain/senses/ear_stt.py
python src_brain/senses/mouth_tts.py
python src_brain/ai_core/core_ai.py

# Chat text (khong can mic/loa)
python src_brain/train_text.py

# Do RAM va latency
python stress_test.py
```

## Cai dat URL co dinh (Cloudflare Named Tunnel)

Mac dinh robot dung quick tunnel — URL thay doi moi lan restart, phai quet QR lai.
De co URL co dinh:

1. Truy cap https://one.dash.cloudflare.com → Zero Trust → Networks → Tunnels
2. Tao tunnel moi, dat ten (vi du: robot-bi)
3. Chon "Windows" → copy token (bat dau bang `eyJ...`)
4. Them Public Hostname: `subdomain.yourdomain.com` → `localhost:8443` (HTTPS) hoac `localhost:8000` (HTTP)
5. Dan vao file `.env`:
   ```
   CLOUDFLARE_TUNNEL_TOKEN=eyJhGci...
   CLOUDFLARE_TUNNEL_URL=https://subdomain.yourdomain.com
   ```
6. Restart robot → URL khong con thay doi sau moi restart

## Bat WebRTC tren Ubuntu
```bash
pip install -r requirements-ubuntu.txt
```
Kiem tra khi khoi dong: `_AIORTC_AVAILABLE` se = `True` neu aiortc da cai dung.

## Khi co phan cung robot
1. Train openWakeWord model "bi_oi" tu 30+ audio samples
2. Dat model vao src_brain/senses/models/bi_oi.onnx
3. Set WAKEWORD_ENABLED = True trong ear_stt.py
4. Implement ESP32 motor control (Sprint 4)
