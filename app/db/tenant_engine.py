from sqlalchemy import create_engine
from app.core.config import settings

def get_engine_by_db_name(db_name: str):
    """
    db_name: örn. winpol_tenant_123abc
    """
    db_url = (
        f"postgresql+psycopg2://"
        f"{settings.POSTGRES_USER}:"
        f"{settings.POSTGRES_PASSWORD}@"
        f"{settings.POSTGRES_HOST}:"
        f"{settings.POSTGRES_PORT}/"
        f"{db_name}"
    )

    return create_engine(
        db_url,
        pool_pre_ping=True,
        future=True
    )
