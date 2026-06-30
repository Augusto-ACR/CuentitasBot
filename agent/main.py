# agent/main.py — Servidor FastAPI + Webhook de OpenWA

"""
Servidor principal del bot de Cuentitas.

Flujo:
  OpenWA → webhook POST /webhook (firmado con HMAC)
         → parsear mensaje → recuperar historial (DB local)
         → generar respuesta (LLM con tool calling contra la API de Cuentitas)
         → guardar historial → enviar respuesta vía OpenWA
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv

from agent.brain import generar_respuesta
from agent.memory import init_db, guardar_mensaje, obtener_historial
from agent.prompts import construir_system_prompt
from agent.providers import obtener_proveedor

load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
log_level = logging.DEBUG if ENVIRONMENT == "development" else logging.INFO
logging.basicConfig(level=log_level)
logger = logging.getLogger("cuentitasbot")

proveedor = obtener_proveedor()
SYSTEM_PROMPT = construir_system_prompt()
PORT = int(os.getenv("PORT", 8000))

# Header donde OpenWA envía la firma HMAC (confirmado en su doc: X-OpenWA-Signature).
SIGNATURE_HEADER = os.getenv("WEBHOOK_SIGNATURE_HEADER", "x-openwa-signature").lower()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa la base de datos al arrancar."""
    await init_db()
    logger.info("Bot de Cuentitas corriendo en puerto %s", PORT)
    logger.info("Proveedor de WhatsApp: %s", proveedor.__class__.__name__)
    yield


app = FastAPI(title="Cuentitas — Bot de WhatsApp", version="1.0.0", lifespan=lifespan)


@app.get("/")
@app.get("/health")
async def health_check():
    """Endpoint de salud para monitoreo."""
    return {"status": "ok", "service": "cuentitasbot"}


@app.post("/webhook")
async def webhook_handler(request: Request):
    """Recibe eventos de OpenWA, genera respuesta y la envía de vuelta."""
    payload_bytes = await request.body()
    signature = request.headers.get(SIGNATURE_HEADER, "")

    if not proveedor.verificar_webhook(payload_bytes, signature):
        logger.warning(
            "Firma HMAC inválida. Buscando header '%s'. Headers recibidos: %s",
            SIGNATURE_HEADER, list(request.headers.keys()),
        )
        raise HTTPException(status_code=401, detail="Firma inválida")

    payload = await request.json()
    mensaje = proveedor.parsear_mensaje(payload)

    if mensaje is None:
        return {"status": "ignored"}

    numero = mensaje["numero"]
    texto = mensaje["texto"]
    logger.info("Mensaje de %s: %s", numero, texto)

    try:
        # Historial ANTES de guardar el mensaje actual (brain agrega el actual)
        historial = await obtener_historial(numero)

        respuesta = await generar_respuesta(historial, texto, SYSTEM_PROMPT, numero)

        await guardar_mensaje(numero, "user", texto)
        await guardar_mensaje(numero, "assistant", respuesta)

        await proveedor.enviar_mensaje(numero, respuesta)
        logger.info("Respuesta a %s: %s", numero, respuesta)

        return {"status": "ok"}

    except Exception as e:
        logger.error("Error en webhook: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
