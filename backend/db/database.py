from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.core.config import settings
from backend.core.logging import logger

logger.info(f"Connecting to database: {settings.DATABASE_URL.split('@')[-1]}")
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
logger.info("SQLAlchemy engine and session factory initialised")