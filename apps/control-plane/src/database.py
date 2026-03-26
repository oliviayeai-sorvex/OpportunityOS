import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

# Fallback to in-memory sqlite for tests or if not configured
# Pydantic is already validating envs but we provide a default just in case
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://aigov:aigov_secret@localhost:5433/opportunity_db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
