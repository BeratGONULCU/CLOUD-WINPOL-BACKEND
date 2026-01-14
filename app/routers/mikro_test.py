from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from app.core.session import SessionContext
from app.db.master import get_master_db
from app.db.session import SessionLocal
from app.db.tenant import get_tenant_db
from app.dependencies.auth import require_tenant
from app.models.tenant.tenant import Firm
from app.routers.mikro_api import call_mikro_api
from app.services.tenant_service import connect_tenant_by_vergiNo

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
    body: Optional[Dict[str, Any]] = Body(None),
    tenant_db: Session = Depends(get_tenant_db),
):
    # --------------------------------------------------
    # Tenant DB'den firma_guid al
    # boş veri olabileceği için Kilitli olmayanı aldık.
    # --------------------------------------------------
    firm = tenant_db.execute(
        select(Firm).where(Firm.firma_kilitli != True) 
    ).scalar_one_or_none()

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
        db=tenant_db,
        firma_guid=firma_guid,
        endpoint=endpoint,
        body=body
    )

"""
// BU ENDPOİNT DE OLUR AMA 

@router.post("/mikro/{endpoint}")
def deneme_mikro(
    endpoint: str,
    body: Optional[Dict[str, Any]] = Body[None],
    tenant_db: Session = Depends(get_tenant_db)
):

    firm = tenant_db.query(Firm).first()

    if not firm:
        raise HTTPException(
            status_code=404,
            detail="mikro bağlanamadı"
        )
    
    firma_guid = str(Firm.firma_Guid)

    return call_mikro_api(
        db= tenant_db,
        firma_guid=firma_guid,
        endpoint=endpoint,
        body=body
    )
    
    """