# agent/providers/openwa.py — Adaptador para OpenWA (gateway self-hosted)
# Generado por AgentKit

"""
OpenWA reemplaza a Twilio/Meta. Es un gateway self-hosted de WhatsApp
(NestJS + whatsapp-web.js) que:
  - Recibe los mensajes de WhatsApp y los reenvía a nuestro webhook con firma HMAC.
  - Expone una REST API para enviar mensajes de vuelta.
"""

import os
import hmac
import hashlib
import logging
import httpx

from agent.providers.base import BaseProvider

logger = logging.getLogger("agentkit")


class OpenWAProvider(BaseProvider):
    """Proveedor de WhatsApp usando OpenWA."""

    def __init__(self):
        self.base_url = os.getenv("OPENWA_URL", "").rstrip("/")
        self.api_key = os.getenv("OPENWA_API_KEY")
        self.session_id = os.getenv("OPENWA_SESSION_ID")
        self.webhook_secret = os.getenv("WEBHOOK_SECRET", "")

    def verificar_webhook(self, payload_bytes: bytes, signature: str) -> bool:
        """Valida la firma HMAC-SHA256 del payload contra WEBHOOK_SECRET.

        OpenWA envía la firma en el header `X-OpenWA-Signature` con el formato
        `sha256=<hexdigest>` (prefijo incluido), calculada sobre el cuerpo crudo
        del webhook. Sacamos el prefijo antes de comparar.
        """
        if not signature:
            return False
        # OpenWA prefija la firma con "sha256="
        if signature.startswith("sha256="):
            signature = signature[len("sha256="):]
        expected = hmac.new(
            self.webhook_secret.encode(),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def parsear_mensaje(self, payload: dict) -> dict | None:
        """Normaliza el evento de OpenWA. Ignora todo lo que no sea mensaje de texto entrante."""
        # OpenWA envía: {"event": "message.received", "data": {...}}
        if payload.get("event") != "message.received":
            return None

        data = payload.get("data", {})

        # Ignorar mensajes de grupos (por flag o por el jid @g.us)
        if data.get("isGroup") or "@g.us" in data.get("from", ""):
            return None

        # Ignorar mensajes propios (enviados por nosotros)
        if data.get("fromMe"):
            return None

        texto = data.get("body", "")
        if not texto:
            return None

        mensaje_id = data.get("id", {})
        if isinstance(mensaje_id, dict):
            mensaje_id = mensaje_id.get("_serialized", "")

        return {
            "numero": data.get("from", "").replace("@c.us", ""),
            "texto": texto,
            "tipo": data.get("type", "chat"),
            "mensaje_id": mensaje_id,
        }

    async def enviar_mensaje(self, numero: str, texto: str) -> bool:
        """Envía un mensaje de texto via la REST API de OpenWA."""
        if not all([self.base_url, self.api_key, self.session_id]):
            logger.warning("Variables de OpenWA no configuradas (URL/API_KEY/SESSION_ID)")
            return False

        # `numero` ya viene como un id de chat enrutable: o un teléfono pelado
        # (le agregamos @c.us) o un jid completo como "...@lid" (se usa tal cual).
        chat_id = numero if "@" in numero else f"{numero}@c.us"

        url = f"{self.base_url}/api/sessions/{self.session_id}/messages/send-text"
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={
                    "X-API-Key": self.api_key,
                    "Content-Type": "application/json",
                },
                json={"chatId": chat_id, "text": texto},
                timeout=10.0,
            )
        if response.status_code not in (200, 201):
            logger.error("Error OpenWA: %s — %s", response.status_code, response.text)
        return response.status_code in (200, 201)
