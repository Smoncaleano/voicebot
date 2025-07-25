from fastapi import FastAPI, Request, HTTPException
import hmac
from hashlib import sha256
import time
import os
import uvicorn

app = FastAPI()
WEBHOOK_SECRET = "wsec_c096fa0d0b3c64207b6707bf4927dc67030870e29c0116a96e5a85e113eda933"

@app.post("/post_call_webhook")
async def post_call_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("elevenlabs-signature")
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing signature header")

    # Parsear cabecera: formato 't=timestamp,v0=hash'
    parts = sig_header.split(",")
    try:
        timestamp = parts[0].split("=")[1]
        signature = parts[1]
    except IndexError:
        raise HTTPException(status_code=400, detail="Invalid signature header format")

    # Validar timestamp (tolerancia de 30 min)
    if int(timestamp) < time.time() - 30 * 60:
        raise HTTPException(status_code=400, detail="Timestamp too old")

    # Calcular HMAC
    signed_payload = f"{timestamp}.{payload.decode()}"
    computed_hmac = hmac.new(
        key=WEBHOOK_SECRET.encode(),
        msg=signed_payload.encode(),
        digestmod=sha256
    ).hexdigest()
    expected_sig = "v0=" + computed_hmac

    if not hmac.compare_digest(expected_sig, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Procesar el payload JSON
    body = await request.json()
    event_type = body.get("type")
    data = body.get("data")

    if event_type == "post_call_transcription":
        conversation_id = data.get("conversation_id")
        transcript = data.get("transcript")
        # Aquí procesas el transcript, análisis, metadatos...
        print(f"Call ended. Conversation {conversation_id}")
    elif event_type == "post_call_audio":
        conversation_id = data.get("conversation_id")
        audio_b64 = data.get("full_audio")
        # Decodifica base64 y guarda o procesa audio
        print(f"Received audio for conversation {conversation_id}")
    else:
        print(f"Unknown event type: {event_type}")

    return {"status": "received"}


if __name__ == "__main__":
    uvicorn.run(
        "prueba:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        reload=os.getenv("ENV", "dev") == "dev",
        log_level="info"
    )