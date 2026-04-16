## SESSION 2026-04-15 - Fix audio output + volume Parent App frontend

### Da sua gi
- Them `setSinkId('default')` ngay sau khi tao `AudioContext` trong `startAudioMonitor()` de uu tien loa ngoai thay vi earpiece tren mobile browser.
- Thay output truc tiep trong `startAudioMonitor()` tu `source.connect(audioContext.destination)` sang `GainNode` voi `gain.value = 2.0` de tang volume.
- Them `setSinkId('default')` cho `momAudioCtx` trong `startMomMic()`.
- Chen `GainNode` vao luong `source -> gainNode -> momScriptProcessor` trong `startMomMic()` de tang muc tin hieu gui di ma khong doi API hay refactor logic.

### Sua file nao
- `src_brain/network/static/index.html`
- `.claude/handoff.md`

### Ly do sua
- Parent App tren mobile co the route audio ra earpiece thay vi loa ngoai.
- Audio monitor trong browser dang phat truc tiep khong qua gain nen volume thap.
- Yeu cau la giu patch nho, an toan, chi cham frontend `index.html`.

### Cach kiem tra
- Xac nhan trong `startAudioMonitor()` da co:
  - `audioContext.setSinkId('default')`
  - `const gainNode = audioContext.createGain();`
  - `source.connect(gainNode);`
  - `gainNode.connect(audioContext.destination);`
- Xac nhan trong `startMomMic()` da co:
  - `momAudioCtx.setSinkId('default')`
  - `const gainNode = momAudioCtx.createGain();`
  - `source.connect(gainNode);`
  - `gainNode.connect(momScriptProcessor);`
- Tim lai trong file va xac nhan khong con `source.connect(audioContext.destination)` o vi tri audio monitor muc tieu.
- Tam tach noi dung `<script>` ra file `.js` va chay `node --check` -> parse thanh cong, khong co syntax error JavaScript.

### Van de con lai neu co
- Chua the xac minh hanh vi loa ngoai / muc am luong tren thiet bi thuc do can test thu cong tren mobile browser.
- `setSinkId()` khong duoc ho tro dong deu tren moi browser; doan code da `catch(() => {})` de fail safe.

---
