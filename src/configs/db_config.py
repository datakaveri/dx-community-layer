from typing import AsyncGenerator
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from .env_config import env_config


# ------------------------------------------------------------------------------
# Database Configuration
# ------------------------------------------------------------------------------

engine = create_async_engine(
    env_config.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,
    pool_pre_ping=True,
    pool_size=20,  # Core connections always available
    max_overflow=30,  # Temporary burst connections (scales to 50)
    pool_timeout=30,  # Wait max 30s for a free conn
    pool_recycle=1800,  # Recycle conns every 30 mins
)

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


db_session = AsyncSessionLocal()
