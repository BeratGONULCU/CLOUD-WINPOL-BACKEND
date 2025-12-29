import psycopg2
from sqlalchemy.orm import Session
from app.models.master.master import TenantDB, Company
from app.core.config import settings


def create_tenant_db(db_name: str):
    conn = psycopg2.connect(
        dbname="postgres",
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(f'CREATE DATABASE "{db_name}"')
    cur.close()
    conn.close()
""" Bu dosya artık kullanılmıyor. Fiziksel veritabanı oluşturma işlemi app/db/tenant_provisioning.py dosyasına taşındı. """