from sqlalchemy import create_engine, text
from app.db.base_tenant import TenantBase
from app.core.config import settings
from app.models.tenant import * 
import app.models.tenant 

def _get_admin_engine():
    return create_engine(
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/postgres",
        isolation_level="AUTOCOMMIT"
    )


def create_tenant_db(db_name: str):
    admin_engine = _get_admin_engine()
    tenant_engine = None

    print(f"[TENANT] Provisioning started: {db_name}")

    try:
        #  DB var mı? Yoksa oluştur
        with admin_engine.begin() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db"),
                {"db": db_name}
            ).scalar()

            if not exists:
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                print("[TENANT] Database created")

        #  Tenant engine
        tenant_engine = create_engine(
            f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
            f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{db_name}",
            isolation_level="AUTOCOMMIT",  
            pool_pre_ping=True
        )

        with tenant_engine.begin() as conn:
            #  EXTENSION → TABLOLARDAN ÖNCE
            conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
            print("[TENANT] uuid-ossp extension ensured")

            #  TABLOLAR
            TenantBase.metadata.create_all(bind=conn)
            print("[TENANT] Tables created")

    except Exception as e:
        raise RuntimeError(f"Tenant DB provisioning failed: {db_name}") from e

    finally:
        admin_engine.dispose()
        if tenant_engine:
            tenant_engine.dispose()


def drop_tenant_db(db_name: str):
    admin_engine = _get_admin_engine()

    try:
        with admin_engine.connect() as conn:
            # aktif bağlantıları kapat
            conn.execute(
                text("""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = :db_name
                  AND pid <> pg_backend_pid()
                """),
                {"db_name": db_name}
            )

            conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))

    finally:
        admin_engine.dispose()
