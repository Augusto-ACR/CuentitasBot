# agent/tools.py — Herramientas (function calling) del bot de Cuentitas

"""
Define las herramientas que el bot puede invocar y el ejecutor que las corre
contra la API de Cuentitas (no contra una base local).

El número de teléfono NO lo decide el modelo: lo inyecta el servidor en cada
llamada, de modo que cada usuario sólo toca SU propia cuenta.

Alcance v1 (deliberadamente chico): registrar gastos/ingresos en pesos y
consultar saldos/resumen. Metas y dólares quedan para la web (v2).
"""

import logging

from agent.cuentitas_api import api, CuentitasError

logger = logging.getLogger("cuentitasbot")


def _parsear_monto(valor) -> float:
    """Convierte el monto a float, tolerando strings con coma o separador de miles."""
    if isinstance(valor, (int, float)):
        return float(valor)
    s = str(valor).strip().replace(".", "").replace(",", ".")
    return float(s)


# ── Esquema de herramientas (formato OpenAI / OpenRouter) ─────────────

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "vincular_cuenta",
            "description": (
                "Vincula este WhatsApp con la cuenta de Cuentitas del usuario usando el "
                "código de un solo uso que él generó en la web (Ajustes → WhatsApp). "
                "Usala cuando el usuario te dicte un código (6 caracteres, letras y números)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "codigo": {"type": "string", "description": "El código que dictó el usuario, ej: ABC234."},
                },
                "required": ["codigo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "registrar_gasto",
            "description": (
                "Registra un GASTO (egreso) en pesos en la cuenta del usuario. "
                "IMPORTANTE: confirmá con el usuario ANTES de llamar esta herramienta "
                "(es plata real). Sólo invocala cuando ya te dijo que sí."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "monto": {"type": "number", "description": "Monto en pesos, mayor que cero."},
                    "descripcion": {"type": "string", "description": "En qué fue el gasto, ej: 'super', 'nafta'."},
                    "cuenta": {"type": "string", "description": "Nombre de la cuenta/billetera si el usuario la mencionó (ej: 'Naranja'). Omitir si no la dijo."},
                },
                "required": ["monto", "descripcion"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "registrar_ingreso",
            "description": (
                "Registra un INGRESO en pesos en la cuenta del usuario. "
                "IMPORTANTE: confirmá con el usuario ANTES de llamar esta herramienta. "
                "Sólo invocala cuando ya te dijo que sí."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "monto": {"type": "number", "description": "Monto en pesos, mayor que cero."},
                    "descripcion": {"type": "string", "description": "De qué es el ingreso, ej: 'sueldo', 'venta'."},
                    "cuenta": {"type": "string", "description": "Nombre de la cuenta/billetera si la mencionó. Omitir si no la dijo."},
                },
                "required": ["monto", "descripcion"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ver_saldos",
            "description": (
                "Devuelve las cuentas/billeteras del usuario con su saldo actual y el total "
                "en pesos. Usala para responder '¿cuánto tengo?', '¿cómo vengo?', 'saldos'. "
                "Respondé EXACTAMENTE los números que devuelve; no inventes ni redondees de memoria."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ver_resumen",
            "description": (
                "Devuelve el resumen del mes: total de ingresos, gastos y balance. "
                "Por defecto el mes actual; pasá 'mes' (YYYY-MM) sólo si el usuario pide otro. "
                "Respondé EXACTAMENTE los números que devuelve la herramienta."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "mes": {"type": "string", "description": "Mes en formato YYYY-MM. Opcional; default mes actual."},
                },
                "required": [],
            },
        },
    },
]


# ── Ejecutor ──────────────────────────────────────────────────────────

async def ejecutar_tool(nombre: str, args: dict, numero: str) -> dict:
    """Ejecuta una herramienta contra la API de Cuentitas y devuelve un dict serializable."""
    try:
        if nombre == "vincular_cuenta":
            codigo = str(args.get("codigo", "")).strip()
            r = await api.vincular(numero, codigo)
            return {"ok": True, **r}

        if nombre in ("registrar_gasto", "registrar_ingreso"):
            tipo = "gasto" if nombre == "registrar_gasto" else "ingreso"
            monto = _parsear_monto(args.get("monto"))
            r = await api.movimiento(
                numero,
                tipo,
                monto,
                str(args.get("descripcion", "")).strip(),
                cuenta=args.get("cuenta"),
            )
            return {"ok": True, **r}

        if nombre == "ver_saldos":
            r = await api.saldos(numero)
            return {"ok": True, **r}

        if nombre == "ver_resumen":
            r = await api.resumen(numero, args.get("mes"))
            return {"ok": True, **r}

        return {"ok": False, "error": f"Herramienta desconocida: {nombre}"}

    except CuentitasError as e:
        # Errores de negocio (no vinculado, código vencido, cuenta ambigua...): devolvemos
        # SOLO el mensaje legible. NO spreadear e.data crudo: trae {"error":"Bad Request",
        # "statusCode":400}, que hace que el modelo lo lea como falla técnica y responda
        # "problema técnico" en vez de relayar el mensaje real. Adjuntamos la lista de
        # cuentas si vino (caso cuenta ambigua) para que el modelo pueda preguntar.
        resultado = {"ok": False, "error": str(e)}
        if isinstance(e.data, dict) and e.data.get("cuentas"):
            resultado["cuentas"] = e.data["cuentas"]
        return resultado
    except Exception as e:
        logger.error("Error ejecutando tool %s: %s", nombre, e)
        return {"ok": False, "error": str(e)}
