# agent/tiempo.py — Fecha/hora en la zona del usuario

"""
El bot sólo necesita saber "hoy" y el "mes actual" para dar contexto al modelo
(las fechas de los movimientos las pone la API de Cuentitas, en horario de Argentina).
"""

import os
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo(os.getenv("TIMEZONE", "America/Argentina/Buenos_Aires"))

_DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
_MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def ahora() -> datetime:
    return datetime.now(TZ)


def hoy_iso() -> str:
    return ahora().strftime("%Y-%m-%d")


def mes_actual() -> str:
    return ahora().strftime("%Y-%m")


def hoy_legible() -> str:
    d = ahora()
    return f"{_DIAS[d.weekday()]} {d.day} de {_MESES[d.month - 1]} de {d.year}"
