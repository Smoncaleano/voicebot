from flask import Flask, request, abort
import hmac
from hashlib import sha256
import time
import os
import sys

# Guardar logs en logs.txt
log_file = open("logs.txt", "a")
sys.stdout = log_file
sys.stderr = log_file

app = Flask(__name__)
WEBHOOK_SECRET = "wsec_6a0f5200bd1f70fda6095b38f35c3c3cd7562bfed39a44c5df1873a554f4d63a"

@app.route("/post_call_webhook", methods=["POST"])
def post_call_webhook():
    payload = request.data
    sig_header = request.headers.get("elevenlabs-signature")
    if not sig_header:
        abort(400, "Missing signature header")

    try:
        parts = sig_header.split(",")
        timestamp = parts[0].split("=")[1]
        signature = parts[1]
    except IndexError:
        abort(400, "Invalid signature header format")

    if int(timestamp) < time.time() - 30 * 60:
        abort(400, "Timestamp too old")

    signed_payload = f"{timestamp}.{payload.decode()}"
    computed_hmac = hmac.new(
        key=WEBHOOK_SECRET.encode(),
        msg=signed_payload.encode(),
        digestmod=sha256
    ).hexdigest()
    expected_sig = "v0=" + computed_hmac

    if not hmac.compare_digest(expected_sig, signature):
        abort(401, "Invalid signature")

    body = request.get_json()
    event_type = body.get("type")
    data = body.get("data")

    if event_type == "post_call_transcription":
        conversation_id = data.get("conversation_id")
        transcript = data.get("transcript")
        print(f"Call ended. Conversation {conversation_id}")
    elif event_type == "post_call_audio":
        conversation_id = data.get("conversation_id")
        print(f"Received audio for conversation {conversation_id}")
    else:
        print(f"Unknown event type: {event_type}")

    return {"status": "received"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)), debug=True)
