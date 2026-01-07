from typing import Generator, Optional
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException, Query, Response,Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.session import SessionContext
from app.db.session import SessionLocal
from app.dependencies.auth import require_master
from app.models.master.master import AdminUser, Company, License
from app.core.security import hash_password, verify_password, create_access_token
from app.core.logger import logger
from app.core.auth_context import get_current_token
from app.core.security import decode_access_token
from datetime import datetime, timedelta, timezone

from app.services.tenant_service import connect_tenant_by_vergiNo


router = APIRouter(prefix="/admin", tags=["Admin Auth"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_tenant_db(
    vergi_no: str = Query(..., description="Tenant Vergi No")
) -> Generator[Session, None, None]:
    """
    Global tenant DB dependency
    """
    tenant_db = connect_tenant_by_vergiNo(vergi_no)

    # güvenlik: yanlış DB bağlanmasın
    current_db = tenant_db.execute(
        text("SELECT current_database()")
    ).scalar()

    if current_db != vergi_no:
        tenant_db.close()
        raise HTTPException(
            status_code=500,
            detail="Tenant database mismatch"
        )

    try:
        yield tenant_db
    finally:
        tenant_db.close()


def get_tenant_db_session(vergi_no: str) -> Session:
    tenant_db = connect_tenant_by_vergiNo(vergi_no)

    current_db = tenant_db.execute(
        text("SELECT current_database()")
    ).scalar()

    if current_db != vergi_no:
        tenant_db.close()
        raise HTTPException(
            status_code=500,
            detail="Tenant database mismatch"
        )

    return tenant_db



@router.post("/register")
def admin_register(email: str, username: str, password: str, db: Session = Depends(get_db)):
    if db.query(AdminUser).filter(AdminUser.email == email).first():
        raise HTTPException(400, "Admin already exists")

    admin = AdminUser(
        email=email,
        username=username,
        password_hash=hash_password(password)
    )
    db.add(admin)
    db.commit()
    return {"message": "Admin created"}


"""
@router.post("/login")
def admin_login(
    response: Response,
    email: str,
    password: str,
    db: Session = Depends(get_db)
):
    admin = db.query(AdminUser).filter(AdminUser.email == email).first()
    if not admin or not verify_password(password, admin.password_hash):
        logger.warning(f"LOGIN FAILED | email={email}")
        raise HTTPException(401, "Invalid credentials")

    token = create_access_token({"sub": str(admin.id)})

    # WEB için cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False  # prod'da True
    )

    logger.info(
        f"LOGIN SUCCESS | admin_id={admin.id} | email={email}"
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }

"""


# LOGIN - ENDPOINT

@router.post("/login")
def admin_login(
    response: Response,
    email: str,
    password: str,
    db: Session = Depends(get_db),
):
    admin = db.query(AdminUser).filter(AdminUser.email == email).first()
    if not admin or not verify_password(password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    admin.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(admin)

    token = create_access_token(
        {
            "sub": str(admin.id),
            "domain": "master",
            "tenant_id": None,
        },
        expires_delta=timedelta(days=3),
    )

    # WEB İÇİN COOKIE SET
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,        # PROD'DA True
        max_age=60 * 60 * 24 * 3,
        path="/",
    )

    return {
        "access_token": token,
        "token_type": "bearer",
    }


# LOGOUT ENDPOINT
@router.post("/logout")
def admin_logout(
    response: Response,
    token: str = Depends(get_current_token),
):
    """
    Admin logout endpoint
    - JWT stateless (server-side silinmez)
    - WEB için cookie silinir
    - MOBİL için client token siler
    """

    payload = decode_access_token(token)

    admin_id = payload.get("sub")
    domain = payload.get("domain")

    logger.info(
        f"LOGOUT | admin_id={admin_id} | domain={domain}"
    )

    # WEB: COOKIE SİL
    response.delete_cookie(
        key="access_token",
        path="/",
    )

    return {
        "message": "Logout successful"
    }



# ping - login
@router.get("/ping-login")
def ping_login(
    request: Request,
    token: str = Depends(get_current_token)
):
    payload = decode_access_token(token)

    source = "cookie" if request.cookies.get("access_token") else "header"

    logger.info(
        f"PING LOGIN | user_id={payload.get('sub')} | source={source}"
    )

    return {
        "status": "authenticated",
        "user_id": payload.get("sub"),
        "token_source": source
    }


"""
@router.get("/me")
def get_admin_details(
    admin_id: str = Depends(get_current_admin_id),
    db: Session = Depends(get_db),
):
    admin = db.query(AdminUser).filter(AdminUser.id == admin_id).first()
    if not admin:
        raise HTTPException(404, "Admin not found")

    return {
        "id": str(admin.id),
        "email": admin.email,
        "username": admin.username
    }
"""

@router.get("/all-companies")
def get_all_companies(db: Session = Depends(get_db)):
    companies = db.query(Company).all()

    if not companies:
        raise HTTPException(
            status_code=404,
            detail="No companies found"
        )

    return [
        {
            "id": str(company.id),
            "name": company.name,
            "vergi_no": company.vergi_no,
            "company_code": company.company_code,
            "status": company.status,              # enum / string
            "status_message": company.status_message,
            "created_at": company.created_at.isoformat()
            if company.created_at else None,
        }
        for company in companies
    ]

  
      


@router.get("/all-users")
def get_all_adminusers(db: Session = Depends(get_db)):
    admins = db.query(AdminUser).all()
    return [
        {
            "id": str(admin.id),
            "email": admin.email,
            "username": admin.username
        }
        for admin in admins
    ]   
      

@router.get("/ping")
def ping():
    return {"status": "ok"}

# ---------------------------------
# firm tablosu insert endpoint - admin ekranında kullanılacak
# veri varsa update yoksa insert yapar.
# ---------------------------------

@router.post("/firm-init")
def admin_firm_init(
    firma_FVergiNo: str,
    firma_unvan: str,
    firma_unvan2: str = None,
    firma_TCkimlik: str = None,
    firma_FVergiDaire: str = None,
    firma_web_sayfasi: str = None,

    master_db: Session = Depends(get_db),
    session: SessionContext = Depends(require_master),  
):

    admin_id = session.user_id   # <-- UUID

    # Tenant DB var mı? (master kontrol)
    firma_guid = master_db.execute(
        text("""
            SELECT company_id
            FROM tenant_dbs
            WHERE db_name = :db_name
        """),
        {"db_name": firma_FVergiNo}
    ).scalar()

    if not firma_guid:
        raise HTTPException(
            status_code=404,
            detail="Bu vergi numarasına ait tenant DB yok"
        )

    # Tenant DB session (yield YOK)
    tenant_db = get_tenant_db_session(firma_FVergiNo)

    try:
        # firms count
        firm_count = tenant_db.execute(
            text("SELECT COUNT(*) FROM firms")
        ).scalar()

        # INSERT
        if firm_count == 0:
            row = tenant_db.execute(
                text("""
                    INSERT INTO firms (
                        "firma_Guid",
                        firma_create_user,
                        firma_create_date,
                        firma_kilitli,
                        firma_unvan,
                        firma_unvan2,
                        "firma_TCkimlik",
                        "firma_FVergiNo",
                        "firma_FVergiDaire",
                        "firma_web_sayfasi"
                    )
                    VALUES (
                        :guid, :user, NOW(),
                        false,
                        :unvan,:unvan2, :tck, :vno, :vd, :web
                    )
                    RETURNING firma_sirano;
                """),
                {
                    "guid": firma_guid,
                    "user": admin_id,  
                    "unvan": firma_unvan,
                    "unvan2": firma_unvan2,
                    "tck": firma_TCkimlik,
                    "vno": firma_FVergiNo,
                    "vd": firma_FVergiDaire,
                    "web": firma_web_sayfasi
                }
            ).fetchone()

            action = "inserted"

        # UPDATE
        elif firm_count == 1:
            row = tenant_db.execute(
                text("""
                    UPDATE firms
                    SET
                        firma_lastup_user = :user,
                        firma_lastup_date = NOW(),
                        firma_unvan = :unvan,
                        firma_unvan2 = :unvan2,
                        "firma_TCkimlik" = :tck,
                        "firma_FVergiDaire" = :vd,
                        "firma_web_sayfasi" = :web
                    RETURNING firma_sirano;
                """),
                {
                    "user": admin_id,   # UUID
                    "unvan": firma_unvan,
                    "unvan2": firma_unvan2,
                    "tck": firma_TCkimlik,
                    "vd": firma_FVergiDaire,
                    "vno": firma_FVergiNo,
                    "web": firma_web_sayfasi
                }
            ).fetchone()

            action = "updated"

        else:
            raise HTTPException(
                status_code=500,
                detail="firms tablosunda birden fazla kayıt var (data corruption)"
            )

        tenant_db.commit()

        return {
            "status": action,
            "firma_FVergiNo": firma_FVergiNo,
            "firma_sirano": row.firma_sirano,
            "admin_id": str(admin_id),
        }

    except HTTPException:
        tenant_db.rollback()
        raise

    except Exception as e:
        tenant_db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        tenant_db.close()


# ---------------------------------
# licences tablosu CRUD işlemleri
# ---------------------------------

# GET ALL LICENSE
@router.get("/get-all-license")
def get_all_license(db: Session = Depends(get_db)):
    licenses = db.query(License).all()

    if not licenses:
        raise HTTPException(
            status_code=404,
            detail="any licence found"
        )

    return [
        {
            "id": str(item.id),
            "company_id": str(item.company_id),
            "is_active": "aktif" if item.is_active else "aktif değil",
        }
        for item in licenses
    ]


# CREATE LICENSE

#@router.post("/create-license")
#def create_licenses():
