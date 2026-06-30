# agent/providers/__init__.py — Factory de proveedores
# Generado por AgentKit

"""
Selecciona el proveedor de WhatsApp. En esta arquitectura el único proveedor
es OpenWA, pero mantenemos el factory por si se agregan otros más adelante.
"""

import os
from agent.providers.base import BaseProvider


def obtener_proveedor() -> BaseProvider:
    """Retorna el proveedor de WhatsApp configurado (default: openwa)."""
    proveedor = os.getenv("WHATSAPP_PROVIDER", "openwa").lower()

    if proveedor == "openwa":
        from agent.providers.openwa import OpenWAProvider
        return OpenWAProvider()

    raise ValueError(f"Proveedor no soportado: {proveedor}. Usa: openwa")
