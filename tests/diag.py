# tests/diag.py — Diagnóstico directo de la vinculación (sin el LLM en el medio)

"""
Prueba /bot/vincular pegándole DIRECTO a la API con el teléfono de prueba, para
aislar si el problema está en la API/código o en el modelo.

Uso (justo después de generar el código en la web):
    .\.venv\Scripts\python.exe tests\diag.py 5JC7Z3
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.cuentitas_api import api, CuentitasError

TELEFONO = "test-local-001"


async def main():
    codigo = (sys.argv[1] if len(sys.argv) > 1 else input("Código: ")).strip()
    print(f"\nAPI base : {api.base}")
    print(f"Teléfono : {TELEFONO}")
    print(f"Código   : {codigo!r}  (len={len(codigo)})")
    print("Pegando a /bot/vincular ...\n")
    try:
        r = await api.vincular(TELEFONO, codigo)
        print("RESULTADO: OK ->", r)
    except CuentitasError as e:
        print("RESULTADO: la API rechazó ->", str(e))
        print("data cruda:", e.data)
    except Exception as e:
        print("RESULTADO: error inesperado ->", type(e).__name__, str(e))


if __name__ == "__main__":
    asyncio.run(main())
