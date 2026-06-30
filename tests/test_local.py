# tests/test_local.py — Simulador de chat en terminal

"""
Prueba al bot de Cuentitas sin WhatsApp, simulando una conversación en la terminal.

Pega contra la API REAL de Cuentitas (CUENTITAS_API_URL) con la BOT_API_KEY del .env,
así probás el flujo completo de punta a punta. Requiere un modelo con tool calling
accesible en OLLAMA_BASE_URL (ej: OpenRouter).

Flujo de prueba sugerido:
  1) En la web (cuentitas.site) → Ajustes → WhatsApp → "Generar código".
  2) Acá escribí: "vinculá mi cuenta con el código ABC234" (el que te dio la web).
  3) Probá: "gasté 5 lucas en el super", "¿cuánto tengo?", "resumen del mes".
El número de prueba es 'test-local-001'; podés desvincularlo después desde la web.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.brain import generar_respuesta
from agent.prompts import construir_system_prompt
from agent.memory import init_db

NUMERO_TEST = "test-local-001"


async def main():
    await init_db()
    system_prompt = construir_system_prompt()
    historial: list[dict] = []

    print()
    print("=" * 55)
    print("   Cuentitas — Test Local (LLM + API real)")
    print("=" * 55)
    print()
    print("  Hablale como por WhatsApp. Por ejemplo:")
    print('    "vinculá mi cuenta con el código ABC234"')
    print('    "gasté 5 lucas en el super"')
    print('    "¿cuánto tengo?"')
    print('    "resumen del mes"')
    print()
    print("  Comandos: 'limpiar' borra el historial de chat | 'salir' termina")
    print("-" * 55)
    print()

    while True:
        try:
            mensaje = input("Tu: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nTest finalizado.")
            break

        if not mensaje:
            continue
        if mensaje.lower() == "salir":
            print("\nTest finalizado.")
            break
        if mensaje.lower() == "limpiar":
            historial.clear()
            print("[Historial de chat borrado]\n")
            continue

        print("\nCuentitas: ", end="", flush=True)
        respuesta = await generar_respuesta(historial, mensaje, system_prompt, NUMERO_TEST)
        print(respuesta)
        print()

        historial.append({"role": "user", "content": mensaje})
        historial.append({"role": "assistant", "content": respuesta})


if __name__ == "__main__":
    asyncio.run(main())
