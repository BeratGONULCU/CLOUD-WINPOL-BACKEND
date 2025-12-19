from sqlalchemy import create_engine, text
from app.db.base_tenant import TenantBase
from app.core.config import settings

def create_tenant_db(db_name: str):
    admin_engine = create_engine(
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/postgres",
        isolation_level="AUTOCOMMIT"
    )

    # database oluştur (varsa patlamasın diye kontrol iyi olur)
    with admin_engine.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{db_name}"'))

    # tenant engine
    tenant_engine = create_engine(
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{db_name}",
        pool_pre_ping=True
    )

    TenantBase.metadata.create_all(bind=tenant_engine)
