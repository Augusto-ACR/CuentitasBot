# agent/brain.py — Cerebro del agente: LLM + function calling

"""
Lógica de IA del bot de Cuentitas. Usa una API compatible con OpenAI (OpenRouter,
Ollama...) y un loop de "tool calling": el modelo decide cuándo invocar las
herramientas (registrar gasto/ingreso, ver saldos/resumen, vincular), el servidor
las ejecuta contra la API de Cuentitas y le devuelve el resultado, hasta que el
modelo produce la respuesta final en texto.

El modelo DEBE soportar tool calling; si no, "alucina" confirmaciones sin registrar
nada. Probá siempre el smoke-test (tests/test_local.py) al cambiar de modelo.
"""

import os
import json
import logging
from openai import AsyncOpenAI
from dotenv import load_dotenv

from agent.tools import TOOLS_SCHEMA, ejecutar_tool
from agent import tiempo

load_dotenv()
logger = logging.getLogger("cuentitasbot")

client = AsyncOpenAI(
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
    # Ollama no valida la key (cualquier valor sirve); OpenRouter/otras APIs sí.
    api_key=os.getenv("LLM_API_KEY", "ollama"),
)

MODEL = os.getenv("OLLAMA_MODEL", "openai/gpt-4o-mini")
MAX_TOKENS = int(os.getenv("OLLAMA_MAX_TOKENS", "600"))
MAX_ITERACIONES = 5  # tope de vueltas de tool calling por mensaje

FALLBACK = "Disculpá, no te entendí bien. ¿Lo podés decir de otra forma?"


async def generar_respuesta(historial: list[dict], mensaje: str, system_prompt: str, numero: str) -> str:
    """
    Genera la respuesta para un mensaje del usuario, ejecutando herramientas si hace falta.

    Args:
        historial: Mensajes anteriores [{"role": ..., "content": ...}]
        mensaje: Mensaje nuevo del usuario
        system_prompt: Identidad/instrucciones del agente
        numero: Teléfono del usuario (se inyecta a las tools; el modelo no lo ve)
    """
    # Contexto temporal fresco en cada mensaje, para resolver "hoy" y el mes actual.
    contexto_fecha = (
        f"Hoy es {tiempo.hoy_legible()} ({tiempo.hoy_iso()}). "
        f"Mes actual para resúmenes: {tiempo.mes_actual()}."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": contexto_fecha},
    ]
    messages.extend(historial)
    messages.append({"role": "user", "content": mensaje})

    try:
        for _ in range(MAX_ITERACIONES):
            response = await client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS_SCHEMA,
                temperature=0.6,
                max_tokens=MAX_TOKENS,
                stream=False,
            )
            msg = response.choices[0].message

            # Sin tool calls → es la respuesta final
            if not msg.tool_calls:
                respuesta = (msg.content or "").strip()
                return respuesta or FALLBACK

            # Reincorporar el turno del asistente (con sus tool_calls) al historial
            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ],
            })

            # Ejecutar cada herramienta y devolver su resultado al modelo
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                resultado = await ejecutar_tool(tc.function.name, args, numero)
                logger.info("Tool %s(%s) → ok=%s", tc.function.name, args, resultado.get("ok"))
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(resultado, ensure_ascii=False),
                })

        logger.warning("Se alcanzó el tope de iteraciones de tool calling")
        return "Estoy teniendo problemas para procesar eso. ¿Lo intentamos de otra forma?"

    except Exception as e:
        logger.error("Error del modelo: %s", e)
        return "Disculpá, estoy teniendo problemas técnicos. Probá de nuevo en unos minutos."
