from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.dependencies.auth import require_master
from app.core.session import SessionContext
from app.db.master import get_master_db
from app.models.master.master import Company
from app.services.company_service import create_company

router = APIRouter(prefix="/companies", tags=["Companies"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

        
@router.post("/create-company")
def create_company_endpoint(
    vergi_no: str,
    name: str,
    company_code: str,
    session: SessionContext = Depends(require_master),  # MASTER KORUMASI
    db: Session = Depends(get_db)                        # MASTER DB
):
    
    if len(vergi_no) not in (10, 11):
        raise HTTPException(
            status_code=400,
            detail="Vergi numarası 10 veya 11 haneli olmalıdır"
        )

    # Aynı vergi_no var mı?
    existing_company = db.query(Company).filter(
        Company.vergi_no == vergi_no
    ).first()

    if existing_company:
        raise HTTPException(
            status_code=400,
            detail="Bu vergi numarası ile kayıtlı bir firma zaten var"
        )

    # Company oluştur
    company = create_company(
        db=db,
        vergi_no=vergi_no,
        name=name,
        company_code=company_code
    )

    return {
        "company_id": str(company.id),
        "vergi_no": company.vergi_no,
        "company_code": company.company_code,
        "name": company.name,
        "status": company.status
    }





@router.get("/get-all-companies")
def get_all_companies(
    db: Session = Depends(get_db)
):
    companies = db.query(Company).all()

    if not companies:
        raise HTTPException(
            status_code=400,
            detail="herhangi bir şirket bulunamadı"
        )

    return companies