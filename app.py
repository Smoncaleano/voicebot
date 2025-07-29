from flask import Flask, jsonify, request, abort
import hmac
from hashlib import sha256
import time
import os
import sys
from dotenv import load_dotenv

from LLM.evaluate_llm import evaluate_transcript_with_gemini
from service.save_analysis_service import get_conversations, insert_call_event

load_dotenv()

# Guardar logs en logs.txt

app = Flask(__name__)
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")



@app.route("/calls", methods=["GET"])
def list_calls():
    return jsonify(get_conversations())

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
        insert_call_event(data, event_type)
        conversation_id = data.get("conversation_id")
        evaluate_transcript_with_gemini(data.get("transcript"), conversation_id)
        print(f"Call ended. Conversation {conversation_id}")
    elif event_type == "post_call_audio":
        conversation_id = data.get("conversation_id")
        print(f"Received audio for conversation {conversation_id}")
    else:
        print(f"Unknown event type: {event_type}")

    return {"status": "received"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)), debug=True)
