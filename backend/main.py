from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.core.logging import logger, db_logger
from backend.db.database import Base, engine
import backend.models  # registers all models with Base.metadata

db_logger.info("Running Base.metadata.create_all against PostgreSQL")
Base.metadata.create_all(bind=engine)
db_logger.info("Schema verified / tables created")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="AI-first CRM for Healthcare Professionals",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME}


from backend.api.v1.api import api_router
app.include_router(api_router, prefix=settings.API_V1_STR)

logger.info(f"{settings.PROJECT_NAME} startup complete — environment: {settings.ENVIRONMENT}")
