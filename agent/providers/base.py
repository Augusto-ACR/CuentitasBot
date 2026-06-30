# agent/providers/base.py — Clase base para proveedores de WhatsApp
# Generado por AgentKit

"""
Interfaz común que todo proveedor de WhatsApp debe implementar.
Permite cambiar de gateway (OpenWA, Twilio, Meta...) sin tocar el resto del código.
"""

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """Interfaz que cada proveedor de WhatsApp debe implementar."""

    @abstractmethod
    def verificar_webhook(self, payload_bytes: bytes, signature: str) -> bool:
        """Valida la firma HMAC del webhook entrante. Retorna True si es válida."""
        ...

    @abstractmethod
    def parsear_mensaje(self, payload: dict) -> dict | None:
        """
        Normaliza el payload del webhook a un dict común:
            {"numero": str, "texto": str, "tipo": str, "mensaje_id": str}
        Retorna None si el evento debe ignorarse (no es un mensaje de texto entrante).
        """
        ...

    @abstractmethod
    async def enviar_mensaje(self, numero: str, texto: str) -> bool:
        """Envía un mensaje de texto. Retorna True si fue exitoso."""
        ...
