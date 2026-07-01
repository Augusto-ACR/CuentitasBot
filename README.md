# Cuentitas Bot — Asistente de finanzas por WhatsApp

Bot de WhatsApp que carga **gastos e ingresos** y consulta **saldos y resumen** de
[Cuentitas](https://cuentitas.site) por lenguaje natural. Clona la arquitectura de
**Rimainder** (FastAPI + loop de tool-calling + OpenRouter + gateway OpenWA) y cambia
la capa de datos: en vez de pegarle a una tabla local, le pega a la **API de Cuentitas**
por su superficie solo-bot (`/bot/*`, header `X-Bot-Key`).

## Cómo funciona

```
WhatsApp ─→ OpenWA ─(webhook HMAC)→ agente (FastAPI) ─→ LLM (tool calling)
                                          │
                                          └─(X-Bot-Key, teléfono)→ API de Cuentitas
```

- El bot **no maneja JWTs**: se autentica con `BOT_API_KEY` y manda el teléfono; Cuentitas
  resuelve teléfono→usuario y hace el scoping.
- **Confirmá antes de escribir:** registrar plata pide confirmación al usuario antes de
  ejecutar (regla aprendida de Rimainder: los modelos alucinan confirmaciones).

## Alcance v1 (en pesos)

- `registrar_gasto`, `registrar_ingreso`
- `ver_saldos`, `ver_resumen`
- `vincular_cuenta` (enlazar el WhatsApp con la cuenta vía código de un solo uso)

Editar/borrar, metas y dólares → por ahora se hacen en la web.

## Vinculación

1. En la web: **Ajustes → WhatsApp → Generar código** (6 caracteres, vence en 10 min).
2. Se lo dictás al bot por chat ("vinculá mi cuenta con el código ABC234").
3. El bot llama a `/bot/vincular {telefono, codigo}` y queda enlazado.

## Probar en local (sin WhatsApp)

Requiere que la API de Cuentitas tenga `BOT_API_KEY` configurada (ver el repo Cuentitas)
y un modelo con tool calling (OpenRouter).

```bash
python -m venv .venv && source .venv/bin/activate   # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # completá BOT_API_KEY, LLM_API_KEY, CUENTITAS_API_URL
python tests/test_local.py
```

En local, `DATABASE_URL` por defecto usa SQLite (no necesitás Postgres).

## Deploy en la VPS (requiere chip/número)

Mismo patrón que Rimainder, y puede ser el **mismo OpenWA** (soporta varias sesiones, una
por número; el bot necesita su propia sesión = su propio número). OpenWA corre aparte (crea
la red `openwa-network`), y este compose levanta el agente + su Postgres y se une a esa red.
Los servicios se llaman `cuentitas-bot*` para no chocar con el `agent` de Rimainder; el
webhook de la sesión del bot apunta a `http://cuentitas-bot:8000/webhook`.

```bash
cp .env.example .env        # completá todo, incluido OPENWA_* y WEBHOOK_SECRET
docker compose up -d --build
```

En el `.env` de OpenWA: `WEBHOOK_SSRF_PROTECT=false` (si no, bloquea el webhook interno).

## Variables de entorno

Ver [.env.example](.env.example). Las claves:

| Variable | Para qué |
|---|---|
| `CUENTITAS_API_URL` | Base de la API de Cuentitas (ej: `https://cuentitas.site/api`) |
| `BOT_API_KEY` | Clave del bot; debe coincidir con la de Cuentitas |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` / `LLM_API_KEY` | Modelo (OpenRouter, Ollama...) con tool calling |
| `DATABASE_URL` | Historial de chat (SQLite local / Postgres en VPS) |
| `OPENWA_*` / `WEBHOOK_SECRET` | Gateway de WhatsApp (sólo deploy) |
