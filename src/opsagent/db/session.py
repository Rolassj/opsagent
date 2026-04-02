"""Gestion de conexion async a PostgreSQL."""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from opsagent.db.models import Base

engine = None
async_session_factory = None


async def init_db(database_url: str) -> None:
    """Inicializar engine y crear tablas si no existen."""
    global engine, async_session_factory
    async_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(async_url, echo=False)
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Cerrar el engine de base de datos."""
    global engine
    if engine:
        await engine.dispose()
        engine = None


async def get_session() -> AsyncSession:
    """Dependency de FastAPI para obtener una session de DB."""
    if async_session_factory is None:
        raise RuntimeError("Base de datos no inicializada. Configurar DATABASE_URL.")
    async with async_session_factory() as session:
        yield session
