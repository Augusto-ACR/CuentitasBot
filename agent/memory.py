# agent/memory.py — Persistencia: historial de chat

"""
Capa de datos del bot, vía SQLAlchemy async. SÓLO guarda el historial de
conversación por número de teléfono (lo necesita el flujo de "confirmar antes de
registrar": el usuario dice "sí" refiriéndose a la propuesta anterior).

Los datos de negocio (gastos, saldos) NO viven acá: viven en Cuentitas y se tocan
por su API. Esta es la diferencia con Rimainder, que guardaba los eventos local.

Producción: PostgreSQL. Local: SQLite (para probar sin instalar Postgres).
El motor se elige según DATABASE_URL — el código es el mismo.
"""

import os
import logging
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, Integer, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("cuentitasbot")

_raw_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./cuentitasbot.db")
DATABASE_URL = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Conversacion(Base):
    """Un mensaje individual de una conversación."""
    __tablename__ = "conversaciones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    numero = Column(String(40), index=True, nullable=False)
    rol = Column(String(10), nullable=False)  # "user" o "assistant"
    contenido = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


async def init_db():
    """Crea las tablas si no existen (sin migraciones manuales)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Base de datos inicializada (%s)", engine.url.get_backend_name())


async def obtener_historial(numero: str, limite: int = 10) -> list[dict]:
    """Recupera los últimos N mensajes de una conversación en orden cronológico."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Conversacion)
            .where(Conversacion.numero == numero)
            .order_by(Conversacion.timestamp.desc())
            .limit(limite)
        )
        mensajes = result.scalars().all()
        return [{"role": m.rol, "content": m.contenido} for m in reversed(mensajes)]


async def guardar_mensaje(numero: str, rol: str, contenido: str):
    """Guarda un mensaje en el historial."""
    async with AsyncSessionLocal() as session:
        session.add(Conversacion(numero=numero, rol=rol, contenido=contenido))
        await session.commit()
