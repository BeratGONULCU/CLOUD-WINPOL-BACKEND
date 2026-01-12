from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from app.db.master import get_master_db
from app.db.session import SessionLocal
from app.db.tenant import get_tenant_db
from app.models.tenant.tenant import Firm
from app.routers.mikro_api import call_mikro_api

router = APIRouter(prefix="/test", tags=["Mikro Test"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/mikro/{endpoint}")
def test_mikro_call(
    endpoint: str,
    body: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_tenant_db),
):
    # --------------------------------------------------
    # Tenant DB'den firma_guid al
    # --------------------------------------------------
    firm = db.query(Firm).first()

    if not firm:
        raise HTTPException(
            status_code=500,
            detail="Tenant DB içinde firma kaydı bulunamadı"
        )

    firma_guid = str(firm.firma_Guid)

    # --------------------------------------------------
    # Mikro API çağrısı
    # --------------------------------------------------
    return call_mikro_api(
        db=db,
        firma_guid=firma_guid,
        endpoint=endpoint,
        body=body
    )


