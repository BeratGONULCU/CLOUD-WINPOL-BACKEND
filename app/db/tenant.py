from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

def get_tenant_engine(db_name: str):
    url = (
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{db_name}"
    )
    return create_engine(url, pool_pre_ping=True)

def get_tenant_db(db_name: str):
    engine = get_tenant_engine(db_name)
    Session = sessionmaker(bind=engine)
    return Session()
