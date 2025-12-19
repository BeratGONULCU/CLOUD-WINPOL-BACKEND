from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

MASTER_URL = (
    f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.MASTER_DB_NAME}"
)

engine = create_engine(MASTER_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

def get_master_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
