from fastapi import Depends
from sqlalchemy.orm import Session
from typing import Generator

from app.dependencies.auth import require_tenant
from app.core.session import SessionContext
from app.services.tenant_service import connect_tenant_by_vergiNo

def get_tenant_db_from_session(
    session: SessionContext = Depends(require_tenant)
) -> Generator[Session, None, None]:
    tenant_db = connect_tenant_by_vergiNo(session.tenant_id)
    try:
        yield tenant_db
    finally:
        tenant_db.close()
