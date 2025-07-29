import os
from hashlib import sha256

from flask import Flask, request, abort, jsonify
import psycopg2
from psycopg2.extras import Json
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DB_HOST     = os.getenv("DB_HOST")
DB_PORT     = os.getenv("DB_PORT")
DB_NAME     = os.getenv("DB_NAME")
DB_USER     = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


conn = psycopg2.connect(
    host=DB_HOST,
    port=DB_PORT,
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD
)


def insert_call_event(data: dict, event_type: str):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO call_events (
                event_type,
                agent_id,
                conversation_id,
                status,
                user_id,
                transcript,
                metadata,
                analysis,
                conversation_initiation_client_data
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                event_type,
                data.get("agent_id"),
                data.get("conversation_id"),
                data.get("status"),
                data.get("user_id"),
                Json(data.get("transcript")),
                Json(data.get("metadata")),
                Json(data.get("analysis")),
                Json(data.get("conversation_initiation_client_data"))
            )
        )
    conn.commit()




def upsert_transcript_evaluation(
    conversation_id: str,
    decision: str,
    reason: str,
    attention_score: int
):
    """
    Inserta o actualiza la evaluación de una conversación en la tabla transcript_evaluations.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO transcript_evaluations (
                conversation_id,
                decision,
                reason,
                attention_score,
                evaluated_at
            ) VALUES (
                %s, %s, %s, %s, NOW()
            )
            ON CONFLICT (conversation_id) DO UPDATE
              SET decision        = EXCLUDED.decision,
                  reason          = EXCLUDED.reason,
                  attention_score = EXCLUDED.attention_score,
                  evaluated_at    = NOW();
            """,
            (
                conversation_id,
                decision,
                reason,
                attention_score
            )
        )
    conn.commit()




def extract_agent_user_text(transcript):
    """
    Dado transcript (lista de dicts), retorna sólo los mensajes
    de 'agent' y 'user' en orden, como [{'role':..., 'message':...}, ...].
    """
    dialogue = []
    for turn in transcript:
        role = turn.get("role", "").lower()
        msg  = turn.get("message")
        if role in ("agent", "user") and msg:
            dialogue.append({"role": role, "message": msg})
    return dialogue


def get_conversations():
    """
    Obtiene todas las conversaciones de la tabla call_events.
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT
              transcript,
              conversation_id,
              agent_id,
              received_at,
              analysis,
              decision,
              reason,
              score
            FROM call_summary_view
            ORDER BY received_at DESC;
        """)
        rows = cur.fetchall()

    # Agregar campo parsed_transcript a cada fila
    for row in rows:
        row["transcript"] = extract_agent_user_text(row["transcript"])

    return rows
