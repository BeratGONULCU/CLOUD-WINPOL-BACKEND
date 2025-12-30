from datetime import timedelta
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, text
from typing import Optional, Generator
from passlib.context import CryptContext

from app.core.session import SessionContext
from app.db.router import get_tenant_db_from_session
from app.db.session import SessionLocal
from app.dependencies.auth import require_master
from app.models.tenant.tenant import Firm, User
from app.services.tenant_service import connect_tenant_by_vergiNo
from app.core.security import create_access_token

router = APIRouter(prefix="/tenant", tags=["Tenant DB"])


# =====================================================
# MASTER DB SESSION (sadece gerekirse)
# =====================================================

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =====================================================
# PASSWORD HASHING
# =====================================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# =====================================================
# PASSWORD VERIFY
# =====================================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# =====================================================
# TENANT DB DEPENDENCY
# =====================================================

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


# =====================================================
# TENANT INFO (TEST)
# =====================================================

@router.get("/tenant-info")
def tenant_info(
    tenant_db: Session = Depends(get_tenant_db_from_session)
):
    db_name = tenant_db.execute(
        text("SELECT current_database();")
    ).scalar()

    return {
        "connected_database": db_name
    }


# =====================================================
# TENANT FIRM CREATE
# =====================================================

@router.post("/tenant-firm-create")
def tenant_firm_create(
    firma_create_user: int,
    firma_unvan: str,
    firma_TCkimlik: Optional[str] = None,
    firma_FVergiNo: Optional[str] = None,
    session: SessionContext = Depends(require_master),
    tenant_db: Session = Depends(get_tenant_db_from_session),
    master_db: Session = Depends(get_db),
):
    #  Identity kontrol
    if bool(firma_TCkimlik) == bool(firma_FVergiNo):
        raise HTTPException(
            status_code=400,
            detail="Firma için sadece TC Kimlik No veya Vergi No girilmelidir."
        )

    #  Hangi tenant DB’deyiz?
    tenant_db_name = tenant_db.execute(
        text("SELECT current_database()")
    ).scalar()

    #  Master DB’den firma GUID çek
    firma_guid = master_db.execute(
        text("""
            SELECT company_id
            FROM tenant_dbs
            WHERE db_name = :db_name
        """),
        {"db_name": tenant_db_name}
    ).scalar()

    if not firma_guid:
        raise HTTPException(
            status_code=404,
            detail="Master DB'de bu tenant için firma bulunamadı"
        )

    #  Tenant DB → firms insert
    result = tenant_db.execute(
        text("""
            INSERT INTO firms (
                "firma_Guid",
                firma_create_user,
                firma_unvan,
                "firma_TCkimlik",
                "firma_FVergiNo"
            )
            VALUES (
                :firma_Guid,
                :firma_create_user,
                :firma_unvan,
                :firma_TCkimlik,
                :firma_FVergiNo
            )
            RETURNING "firma_Guid", firma_sirano;
        """),
        {
            "firma_Guid": firma_guid,
            "firma_create_user": firma_create_user,
            "firma_unvan": firma_unvan,
            "firma_TCkimlik": firma_TCkimlik,
            "firma_FVergiNo": firma_FVergiNo,
        }
    )

    row = result.fetchone()
    tenant_db.commit()

    return {
        "firma_Guid": str(row.firma_Guid),
        "firma_sirano": row.firma_sirano,
        "firma_unvan": firma_unvan
    }


# =====================================================
# TENANT USER REGISTER FİRMA VERGİ NO İLE
# =====================================================

@router.post("/user-register-to-firmby-vergino")
def user_register_to_firmby_vergino(
    vergi_no: str,
    username: str,
    password: str,
):
    tenant_db: Session = connect_tenant_by_vergiNo(vergi_no)

    try:
        # Firmayı bul
        firm = tenant_db.execute(
            select(Firm).where(Firm.firma_FVergiNo == vergi_no)
        ).scalar_one_or_none()

        if not firm:
            raise HTTPException(
                status_code=404,
                detail="Bu vergi numarasına ait firma bulunamadı."
            )

        # Kullanıcı oluştur
        new_user = User(
            kullanici_Guid=uuid.uuid4(),
            firma_siraNo=firm.firma_sirano,
            kullanici_name=username,
            kullanici_pw=hash_password(password),  # aşağıda hash önerisi var
            kullanici_pasif=False
        )

        tenant_db.add(new_user)
        tenant_db.commit()
        tenant_db.refresh(new_user)

        return {
            "user_id": str(new_user.kullanici_Guid),
            "username": new_user.kullanici_name,
            "firma_siraNo": firm.firma_sirano
        }

    except HTTPException:
        tenant_db.rollback()
        raise
    except Exception as e:
        tenant_db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Kullanıcı oluşturulurken hata oluştu: {str(e)}"
        )
    finally:
        tenant_db.close()

# =====================================================
# TENANT LOGIN FİRMA VERGİ NO İLE
# =====================================================

@router.post("/user-login-to-firmby-vergino")
def user_login_to_firmby_vergino(
    vergi_no: str,
    username: str,
    password: str
):
    tenant_db: Session = connect_tenant_by_vergiNo(vergi_no)

    try:
        user = tenant_db.execute(
            select(User).where(
                User.kullanici_name == username,
                User.kullanici_pasif == False
            )
        ).scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not verify_password(password, user.kullanici_pw):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        #token = create_access_token({"sub": str(user.kullanici_Guid)})
        token = create_access_token(
        {
            "sub": str(user.kullanici_Guid),
            "domain": "tenant",
            "tenant_id": vergi_no,
            "role_id": user.role_id
        },
        expires_delta=timedelta(days=3)
        )

        return {
            "access_token": token,
            "token_type": "bearer",
            "user_id": str(user.kullanici_Guid),
            "username": user.kullanici_name
        }

    finally:
        tenant_db.close()

# =====================================================
# new endpoint 
# =====================================================


@router.post("/user-login-to-firmby-vergino2")
def user_login_to_firmby_vergino2(
    vergi_no: str,
    email: str,
    password: str
):
    tenant_db: Session = connect_tenant_by_vergiNo(vergi_no)

    try:
        user = tenant_db.execute(
            select(User).where(
                User.kullanici_EMail == email,
                User.kullanici_pasif == False
            )
        ).scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not verify_password(password, user.kullanici_pw):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        #token = create_access_token({"sub": str(user.kullanici_Guid)})
        token = create_access_token(
        {
        "sub": str(user.kullanici_Guid),
        "domain": "tenant",
        "tenant_id": vergi_no,
        "role_id": str(user.role_id) if user.role_id else None
        },
        expires_delta=timedelta(days=3)
        )


        return {
            "access_token": token,
            "token_type": "bearer",
            "user_id": str(user.kullanici_Guid),
            "username": user.kullanici_name
        }

    finally:
        tenant_db.close()