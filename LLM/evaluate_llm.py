import getpass
from typing import Any, Dict, List, Literal
import google.generativeai as genai
from pydantic import BaseModel # <--- NUEVO

from langchain.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from service.save_analysis_service import upsert_transcript_evaluation


import os

from dotenv import load_dotenv

load_dotenv()


if "GOOGLE_API_KEY" not in os.environ:
    os.environ["GOOGLE_API_KEY"] = getpass.getpass("Enter your Google AI API key: ")



class TranscriptEvaluation(BaseModel):
    decision: Literal["TRUE", "FALSE"]
    reason: str
    attention_score: int
    


def format_transcript(transcript):
    parts = []
    for entry in transcript:
        role = entry.get("role", "").lower()
        # 1) Prefijo según rol
        if role == "agent":
            prefix = "Agente:"
        elif role == "user":
            prefix = "User:"
        else:
            prefix = f"{role.capitalize()}:"

        # 2) Mensaje principal
        msg = entry.get("message")
        if msg:
            parts.append(f"{prefix} {msg}")

        # 3) Herramientas usadas en este turno
        tools = [call["tool_name"] for call in entry.get("tool_calls", []) if call.get("tool_name")]
        if tools:
            parts.append(f"Herramientas usadas: {', '.join(tools)}")

        # 4) Variables actualizadas (dynamic_variable_updates)
        vars_updates = []
        for result in entry.get("tool_results", []):
            for dv in result.get("dynamic_variable_updates", []):
                name = dv.get("name")
                value = dv.get("value")
                if name is not None and value is not None:
                    vars_updates.append(f"{name}={value}")
        if vars_updates:
            parts.append(f"Variables: {', '.join(vars_updates)}")

        # Línea en blanco para separar turnos
        parts.append("")

    # Unimos todo en un solo string
    return "\n".join(parts)


def evaluate_transcript_with_gemini(transcript: List[Dict[str, Any]], conversation_id: str) -> str:    
    
    """
    Envía la transcripción a Gemini para su evaluación y devuelve 'TRUE' o 'FALSE'.
    """
    transcript_str = format_transcript(transcript)

    system_prompt = """
    Eres un sistema de control de calidad que evalúa llamadas realizadas por “Marce”, la agente virtual de BBVA. 
    Tu único objetivo es:
    1. Revisar la transcripción y comprobar si Marce aplicó correctamente el bloqueo de la cuenta del usuario.
    2. No necesitas datos adicionales: todo debe deducirse de la conversación.
    3. La evaluación de tu decisión debe basarse exclusivamente en si el bloqueo fue justificado o no.
    """

    human_prompt = f"""
    Transcripción:
    ---
    {transcript_str}
    ---

    Devuelve **solo** un JSON con estos campos:
    - decision: `"TRUE"` si el bloqueo de la cuenta estaba justificado, o `"FALSE"` si no lo estaba.
    - reason: explicación breve de por qué la decisión es OK o FALSE.
    - attention_score: entero de 0 a 100 valorando la calidad general de la atención del agente.
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt.strip()),
        ("human", human_prompt.strip()),
    ])


    try:
        llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0.0,
        max_tokens=200
    )
        structured_llm = llm.with_structured_output(TranscriptEvaluation)

        # 4️⃣ Crear y ejecutar la cadena
        chain = prompt | structured_llm
        result: TranscriptEvaluation = chain.invoke({})
        upsert_transcript_evaluation(
        conversation_id=conversation_id,
        decision=result.decision,
        reason=result.reason,
        attention_score=result.attention_score
    )
        return result
    except Exception as e:
        print(f"Error al contactar la API de Gemini: {e}")
        # En caso de error con la API, por defecto permitimos
        return "ALLOW"
# -------------------------------------------------------------
