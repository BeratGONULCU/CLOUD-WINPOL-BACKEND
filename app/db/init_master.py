from sqlalchemy import create_engine
from app.db.base import Base
from app.models import master 
from app.core.config import settings

def init_master_db():
    engine = create_engine(
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.MASTER_DB_NAME}",
        pool_pre_ping=True
    )

    print("MASTER DB INIT STARTED")
    Base.metadata.create_all(bind=engine)
    print("MASTER DB TABLES CREATED")
