# agent/cuentitas_api.py — Cliente HTTP de la API de Cuentitas (superficie solo-bot)

"""
El bot NO toca la base de Cuentitas directo: habla con su API por la superficie
solo-bot, autenticándose con `BOT_API_KEY` (header X-Bot-Key). En cada request
manda el teléfono y la API resuelve teléfono→usuario y hace el scoping.

Esta es la diferencia clave con Rimainder: allá las tools pegaban a una tabla
`eventos` local; acá pegan a estos endpoints HTTP de Cuentitas.
"""

import os
import logging
import httpx

logger = logging.getLogger("cuentitasbot")


class CuentitasError(Exception):
    """Error de negocio devuelto por la API (con su mensaje y datos extra)."""

    def __init__(self, mensaje: str, data: dict | None = None):
        super().__init__(mensaje)
        self.data = data or {}


class CuentitasAPI:
    def __init__(self):
        self.base = os.getenv("CUENTITAS_API_URL", "").rstrip("/")
        self.key = os.getenv("BOT_API_KEY", "")

    async def _post(self, path: str, body: dict) -> dict:
        if not self.base or not self.key:
            raise CuentitasError(
                "El bot no está configurado: falta CUENTITAS_API_URL o BOT_API_KEY."
            )
        url = f"{self.base}{path}"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                headers={"X-Bot-Key": self.key, "Content-Type": "application/json"},
                json=body,
                timeout=15.0,
            )
        if resp.status_code == 200:
            return resp.json()

        # Error: extraer el mensaje legible de Nest ({statusCode, message, ...}).
        try:
            data = resp.json()
        except Exception:
            data = {"message": resp.text}
        if not isinstance(data, dict):
            data = {"message": str(data)}
        msg = data.get("message") or f"Error {resp.status_code}"
        logger.info("API %s → %s: %s", path, resp.status_code, msg)
        raise CuentitasError(msg, data)

    # ── Vinculación ──────────────────────────────────────────────────────
    async def vincular(self, telefono: str, codigo: str) -> dict:
        return await self._post("/bot/vincular", {"telefono": telefono, "codigo": codigo})

    async def resolver(self, telefono: str) -> dict:
        return await self._post("/bot/resolver", {"telefono": telefono})

    # ── Lectura ──────────────────────────────────────────────────────────
    async def saldos(self, telefono: str) -> dict:
        return await self._post("/bot/saldos", {"telefono": telefono})

    async def resumen(self, telefono: str, mes: str | None = None) -> dict:
        body: dict = {"telefono": telefono}
        if mes:
            body["mes"] = mes
        return await self._post("/bot/resumen", body)

    # ── Escritura ────────────────────────────────────────────────────────
    async def movimiento(
        self,
        telefono: str,
        tipo: str,
        monto: float,
        descripcion: str,
        cuenta: str | None = None,
        cuenta_id: int | None = None,
    ) -> dict:
        body: dict = {
            "telefono": telefono,
            "tipo": tipo,
            "monto": monto,
            "descripcion": descripcion,
        }
        if cuenta:
            body["cuenta"] = cuenta
        if cuenta_id is not None:
            body["cuentaId"] = cuenta_id
        return await self._post("/bot/movimiento", body)


api = CuentitasAPI()
