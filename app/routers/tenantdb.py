from datetime import date, timedelta
import hashlib
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy import UUID, select, text
from typing import Optional, Generator
from passlib.context import CryptContext

from sqlalchemy.exc import SQLAlchemyError
from app.core.auth_context import get_current_token
from app.core.session import SessionContext
from app.db.master import get_master_db
from app.db.router import get_tenant_db_from_session
from app.db.session import SessionLocal
from app.db.tenant_engine import get_engine_by_db_name
from app.dependencies.auth import require_master, require_tenant
from app.models.tenant.tenant import Branch, Firm, MikroApiSettings, Role, User, UserFavorite
from app.schemas.mikro_api import MikroApiUpdateSchema
from app.services.get_current_user import get_current_user
from app.services.tenant_service import connect_tenant_by_vergiNo
from app.core.security import create_access_token, decode_access_token
from fastapi import Depends, HTTPException, status
from jose import jwt, JWTError
from datetime import datetime,timezone
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
from sqlalchemy.orm import sessionmaker


logger = logging.getLogger("uvicorn.error")

bearer_scheme = HTTPBearer()

router = APIRouter(prefix="/tenant", tags=["Tenant DB"])

# =====================================================
# api_pw_non_hash kolonunu generate_mikro_md5 
# =====================================================

def generate_mikro_md5(password: str) -> str:
    """
    Node.js karşılığı:
    CryptoJS.MD5(`${YYYY-MM-DD} ${password}`)
    """
    current_date = date.today().strftime("%Y-%m-%d")
    raw = f"{current_date} {password}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


# =====================================================
# MASTER DB SESSION 
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


def get_role_id(tenant_db: Session, role_name: str):
    return tenant_db.execute(
        text("SELECT id FROM roles WHERE name = :name"),
        {"name": role_name}
    ).scalar()



# =====================================================
# TENANT DB DEPENDENCY
# =====================================================

def get_tenant_db(
    session: SessionContext = Depends(require_tenant),
) -> Generator[Session, None, None]:

    vergi_no = session.tenant_id  # JWT’den geliyor

    if not vergi_no:
        raise HTTPException(
            status_code=403,
            detail="Tenant context bulunamadı"
        )

    tenant_db = connect_tenant_by_vergiNo(vergi_no)

    # Güvenlik: yanlış DB’ye bağlanılmasın
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
# yardımcı fonk.
# =====================================================

def get_optional_tenant_db_from_session():
    try:
        return get_tenant_db_from_session()  # mevcut fonksiyonunu çağır
    except Exception:
        return None

# =====================================================
# yardımcı fonk.
# =====================================================

def resolve_tenant_db_name(
    *,
    master_db: Session,
    tenant_db: Optional[Session],
    db_name: Optional[str],
    company_id: Optional[str],
) -> str:
    # 1) Eğer tenant context içindeysek: current_database()
    if tenant_db is not None:
        name = tenant_db.execute(text("SELECT current_database()")).scalar()
        if not name:
            raise HTTPException(500, "Tenant DB adı alınamadı")
        return name

    # 2) Master’dan çağrılıyorsa: db_name veya company_id zorunlu
    if db_name:
        return db_name

    if company_id:
        name = master_db.execute(
            text("""SELECT db_name FROM tenant_dbs WHERE company_id = :company_id"""),
            {"company_id": company_id},
        ).scalar()
        if not name:
            raise HTTPException(404, "Bu company_id için tenant db_name bulunamadı")
        return name

    raise HTTPException(
        status_code=400,
        detail="Tenant context yok. Master'dan çağırırken db_name veya company_id vermelisin."
    )

# =====================================================
# yardımcı fonk.
# =====================================================

def resolve_company_id_from_db_name(master_db: Session, tenant_db_name: str) -> str:
    company_id = master_db.execute(
        text("""SELECT company_id FROM tenant_dbs WHERE db_name = :db_name"""),
        {"db_name": tenant_db_name},
    ).scalar()
    if not company_id:
        raise HTTPException(404, "Master DB'de bu tenant için firma(company_id) bulunamadı")
    return str(company_id)


# =====================================================
# TENANT INFO (TEST)
# =====================================================
@router.get("/tenant-info")
def tenant_info(
    session: SessionContext = Depends(require_tenant),
):
    # require_tenant zaten JWT'yi doğruladı
    tenant_id = session.tenant_id
    domain = session.domain

    if domain != "tenant" or not tenant_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid tenant token"
        )

    tenant_db = connect_tenant_by_vergiNo(tenant_id)

    try:
        db_name = tenant_db.execute(
            text("SELECT current_database();")
        ).scalar()

        return {
            "connected_database": db_name,
        }
    finally:
        tenant_db.close()

# =====================================================
# TENANT INFO (TEST)
# =====================================================
@router.get("/tenant-api-pw-info")
def tenant_api_pw_info(
    tenant_db: Session = Depends(get_tenant_db)
):
    try:
        api_pw_non_hash = tenant_db.execute(
            select(MikroApiSettings.api_pw_non_hash).limit(1)
        ).scalar_one_or_none()

        if not api_pw_non_hash:
            return False
        
        return True

    finally:
        tenant_db.close()

    

# =====================================================
# TENANT FIRM CREATE
# =====================================================


@router.post("/tenant-firm-create")
def tenant_firm_create(
    firma_unvan: str,
    firma_TCkimlik: Optional[str] = None,
    firma_FVergiNo: Optional[str] = None,
    master_db: Session = Depends(get_db),
):
    # Kimlik kontrol
    if bool(firma_TCkimlik) == bool(firma_FVergiNo):
        raise HTTPException(
            status_code=400,
            detail="Firma için sadece TC Kimlik No veya Vergi No girilmelidir."
        )

    # Master DB → company bul
    company = master_db.execute(
        text("""
            SELECT id
            FROM companies
            WHERE vergi_no = :vergi_no
        """),
        {"vergi_no": firma_FVergiNo}
    ).scalar()

    if not company:
        raise HTTPException(404, "Company bulunamadı")

    # Tenant DB bilgisini al
    tenant_db_name = master_db.execute(
        text("""
            SELECT db_name
            FROM tenant_dbs
            WHERE company_id = :company_id
        """),
        {"company_id": company}
    ).scalar()

    if not tenant_db_name:
        raise HTTPException(404, "Tenant DB bulunamadı")

    # Tenant DB’ye MANUEL bağlan
    tenant_engine = get_engine_by_db_name(tenant_db_name)
    TenantSession = sessionmaker(bind=tenant_engine)
    tenant_db = TenantSession()

    # Firm insert
    result = tenant_db.execute(
        text("""
            INSERT INTO firms (
                "firma_Guid",
                firma_unvan,
                "firma_TCkimlik",
                "firma_FVergiNo"
            )
            VALUES (
                :firma_Guid,
                :firma_unvan,
                :firma_TCkimlik,
                :firma_FVergiNo
            )
            RETURNING "firma_Guid", firma_sirano;
        """),
        {
            "firma_Guid": company,
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
# TENANT DELETE SELECTED FİRM - FİRMA VERGİ NO İLE
# =====================================================

@router.delete("/tenant-firm-delete/{company_id}")
def tenant_firm_delete(
    company_id: str,
    session: SessionContext = Depends(require_master),
    master_db: Session = Depends(get_db),
):
    """
    Bu endpoint:
    1) tenant DB adını bulur
    2) tenant DB'yi DROP eder
    3) masterDB'de company + tenant kayıtlarını siler
    """

    # --------------------------------------------------
    # Tenant DB adını bul
    # --------------------------------------------------
    row = master_db.execute(
        text("""
            SELECT db_name
            FROM tenant_dbs
            WHERE company_id = :company_id
        """),
        {"company_id": company_id}
    ).fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Bu company_id için tenant DB bulunamadı"
        )

    tenant_db_name = row.db_name

    # --------------------------------------------------
    # Tenant DB DROP (transaction DIŞINDA!)
    # --------------------------------------------------
    try:
        master_db.execute(
            text(f'DROP DATABASE "{tenant_db_name}"')
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Tenant DB silinemedi: {str(e)}"
        )

    # --------------------------------------------------
    # Master DB cleanup (transaction içinde)
    # --------------------------------------------------
    try:
        master_db.begin()

        master_db.execute(
            text("DELETE FROM tenant_dbs WHERE company_id = :company_id"),
            {"company_id": company_id}
        )

        master_db.execute(
            text("DELETE FROM companies WHERE id = :company_id"),
            {"company_id": company_id}
        )

        # (Varsa CASCADE otomatik temizler)
        # licenses
        # company_modules

        master_db.execute(
            text("""
                INSERT INTO system_logs (
                    actor_id,
                    action,
                    target_type,
                    target_id,
                    status,
                    message,
                    created_at
                )
                VALUES (
                    :actor_id,
                    'COMPANY_DELETED',
                    'COMPANY',
                    :company_id,
                    'SUCCESS',
                    :message,
                    NOW()
                )
            """),
            {
                "actor_id": session.user_id,
                "company_id": company_id,
                "message": f"{tenant_db_name} tenant DB ve company silindi"
            }
        )

        master_db.commit()

    except Exception as e:
        master_db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Master DB cleanup başarısız: {str(e)}"
        )

    # --------------------------------------------------
    # RESPONSE
    # --------------------------------------------------
    return {
        "status": "success",
        "company_id": company_id,
        "tenant_db": tenant_db_name,
        "message": "Tenant DB ve master kayıtları başarıyla silindi"
    }


# =====================================================
# TENANT UPDATE SELECTED FİRM - FİRMA VERGİ NO İLE
# =====================================================

@router.put("/update-firm-by-vergiNo")
def update_firm_by_vergiNo(
    vergiNo: str,

    firma_unvan: Optional[str] = None,
    firma_unvan2: Optional[str] = None,
    firma_TCkimlik: Optional[str] = None,
    firma_FVergiDaire: Optional[str] = None,
    firma_web_sayfasi: Optional[str] = None,
):

    tenant_db: Session = connect_tenant_by_vergiNo(vergiNo)

    firm = tenant_db.execute(
        select(Firm).where(Firm.firma_FVergiNo == vergiNo)
    ).scalar_one_or_none()

    if not firm:
        raise HTTPException(
            status_code=404,
            detail="Aranan firma bulunamadı"
        )

    # --- Sadece gelen alanlar güncellenir ---
    if firma_unvan is not None:
        firm.firma_unvan = firma_unvan
        
    if firma_unvan2 is not None:
        firm.firma_unvan2 = firma_unvan2

    if firma_TCkimlik is not None:
        firm.firma_TCkimlik = firma_TCkimlik

    if firma_FVergiDaire is not None:
        firm.firma_FVergiDaire = firma_FVergiDaire

    if firma_web_sayfasi is not None:
        firm.firma_web_sayfasi = firma_web_sayfasi

    # Audit alanları
    firm.firma_lastup_user = "system"  # JWT varsa buradan al
    firm.firma_lastup_date = datetime.now()

    tenant_db.commit()
    tenant_db.refresh(firm) 

    return {
        "message": "Firma başarıyla güncellendi",
        "firma_guid": firm.firma_Guid,
        "firma_vergi_no": firm.firma_FVergiNo
    }

# =====================================================
# TENANT UPDATE SELECTED FİRM - FİRMA VERGİ NO İLE
# =====================================================


@router.post("/firm-init")
def tenant_firm_init(
    firma_unvan: str,
    firma_TCkimlik: str = None,
    firma_FVergiDaire: str = None,

    tenant_db: Session = Depends(get_tenant_db),
    session: SessionContext = Depends(require_tenant)
):

    # TENANT DB ADI = VERGİ NO
    firma_FVergiNo = tenant_db.execute(
        text("SELECT current_database()")
    ).scalar()

    # TENANT USER UUID
    tenant_user_id = session.user_id   # UUID

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
                        "firma_TCkimlik",
                        "firma_FVergiNo",
                        "firma_FVergiDaire"
                    )
                    VALUES (
                        gen_random_uuid(),
                        :user,
                        NOW(),
                        false,
                        :unvan,
                        :tck,
                        :vno,
                        :vd
                    )
                    RETURNING firma_sirano;
                """),
                {
                    "user": tenant_user_id,
                    "unvan": firma_unvan,
                    "tck": firma_TCkimlik,
                    "vno": firma_FVergiNo,
                    "vd": firma_FVergiDaire,
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
                        "firma_TCkimlik" = :tck,
                        "firma_FVergiDaire" = :vd
                    RETURNING firma_sirano;
                """),
                {
                    "user": tenant_user_id,
                    "unvan": firma_unvan,
                    "tck": firma_TCkimlik,
                    "vd": firma_FVergiDaire,
                }
            ).fetchone()

            action = "updated"

        # DATA CORRUPTION
        else:
            raise HTTPException(
                status_code=500,
                detail="firms tablosunda birden fazla kayıt var"
            )

        tenant_db.commit()

        return {
            "status": action,
            "firma_FVergiNo": firma_FVergiNo,
            "firma_sirano": row.firma_sirano,
        }

    except HTTPException:
        tenant_db.rollback()
        raise

    except Exception as e:
        tenant_db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# TENANT INSERT FİRM - FİRMA VERGİ NO İLE
# =====================================================

@router.post("/insert-firm")
def insert_firm(
    vergiNo: str,

    firma_unvan: str,
    firma_unvan2: str = None,
    firma_TCkimlik: str = None,
    firma_FVergiDaire: str = None,
    firma_web_sayfasi: str = None,
):
    tenant_db: Session = connect_tenant_by_vergiNo(vergiNo)

    # --- Aynı vergi no var mı kontrol ---
    existing_firm = tenant_db.execute(
        select(Firm).where(Firm.firma_FVergiNo == vergiNo)
    ).scalar_one_or_none()

    if existing_firm:
        raise HTTPException(
            status_code=409,
            detail="Bu vergi numarasına ait firma zaten mevcut"
        )

    new_firm = Firm(
        firma_Guid=str(uuid.uuid4()),
        firma_sirano=1,  # Eğer otomatik artıyorsa burayı kaldır
        firma_kilitli=False,

        firma_create_user="system",  # JWT varsa buradan al
        firma_create_date=datetime.utcnow(),

        firma_unvan=firma_unvan,
        firma_unvan2=firma_unvan2,
        firma_TCkimlik=firma_TCkimlik,
        firma_FVergiDaire=firma_FVergiDaire,
        firma_FVergiNo=vergiNo,
        firma_web_sayfasi=firma_web_sayfasi,
    )

    tenant_db.add(new_firm)
    tenant_db.commit()
    tenant_db.refresh(new_firm)

    return {
        "message": "Firma başarıyla oluşturuldu",
        "firma_guid": new_firm.firma_Guid,
        "firma_vergi_no": new_firm.firma_FVergiNo
    }


# =====================================================
# TENANT ALL FİRM LİSTESİ - FİRMA VERGİ NO İLE
# =====================================================

@router.get("/get-all-firmsby-vergiNo")
def Get_All_Firms(
    #vergiNo: str, # 10 haneli olacak ve required olacak
    tenant_db: Session = Depends(get_tenant_db)
):

    try:
        firms = tenant_db.execute(
            select(Firm).where(Firm)
        ).scalar_one_or_none()

        if not firms: 
            raise HTTPException(
                status_code=404,
                detail="bu vergi no ile firma kaydı bulunamadı."
            )
    
        if not firms: # böyle bir şeyin olma ihtimali çok düşük
            raise HTTPException(
                status_code=404,
                detail="yanlış vergi no değeri girildi"
            )
        
        return firms

    finally:
        tenant_db.close()

# =====================================================
# TENANT USER REGISTER FİRMA VERGİ NO İLE
# =====================================================
# - kullanici_create_user eklenecek - Session ile 
# - role-id seçtirilecek (foreign key nasıl yapılacak)

@router.post("/user-register-to-firmby-vergino")
def user_register_to_firm(
    username: str,
    password: str,
    role_id: Optional[str] = None,
    longName: Optional[str] = None,
    cepTel: Optional[str] = None,
    email: Optional[str] = None,
    tenant_db: Session = Depends(get_tenant_db),
):
    #tenant_db: Session = connect_tenant_by_vergiNo(vergi_no)

    try:
        # Firmayı bul
        firm = tenant_db.execute(
            select(Firm).where(Firm)
        ).scalar_one_or_none()

        if not firm:
            raise HTTPException(
                status_code=404,
                detail="Bu vergi numarasına ait firma bulunamadı."
            )

        # Yeni kullanıcı numarası
        user_no = tenant_db.execute(
            text("SELECT COALESCE(MAX(kullanici_no), 0) + 1 FROM users")
        ).scalar()

        if not user_no:
            raise HTTPException(
                status_code=500,
                detail="Kullanıcı numarası üretilemedi."
            )

        # Kullanıcı oluştur
        new_user = User(
            kullanici_Guid=uuid.uuid4(),
            firma_siraNo=firm.firma_sirano,
            kullanici_name=username,
            kullanici_pw=hash_password(password),
            kullanici_pasif=False,
            role_id=role_id,
            kullanici_LongName=longName,
            kullanici_EMail=email,
            kullanici_Ceptel=cepTel,
            kullanici_no=user_no,
            kullanici_create_user=None,  # REGISTER → SYSTEM
        )

        tenant_db.add(new_user)
        tenant_db.commit()
        tenant_db.refresh(new_user)

        return {
            "user_id": str(new_user.kullanici_Guid),
            "username": new_user.kullanici_name,
            "firma_siraNo": firm.firma_sirano,
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
# TENANT-MIKRO USER REGISTER 
# =====================================================
# bu register uygulama içindeki - hem mikro hem tenant içine eklemek için kullanılacak

@router.post("/user-register-with-mikro")
def user_register_with_mikro(
    username: str,
    password: str,
    mikroPersonelGuid: Optional[str] = None,
    mikroPersonelKod: Optional[str] = None,
    role_id: Optional[str] = None,
    longName: Optional[str] = None,
    cepTel: Optional[str] = None,
    email: Optional[str] = None,
    tenant_db: Session = Depends(get_tenant_db),
):

    if not mikroPersonelGuid and not mikroPersonelKod:
        raise HTTPException(
            status_code=400,
            detail="mikroPersonelGuid veya mikroPersonelKod alanlarından en az biri zorunludur"
        )

    parsed_mikro_guid = None
    if mikroPersonelGuid:
        try:
            parsed_mikro_guid = uuid.UUID(mikroPersonelGuid)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="mikroPersonelGuid geçerli bir UUID değil"
            )

    if parsed_mikro_guid:
        existing = tenant_db.execute(
            select(User).where(User.mikro_personel_guid == parsed_mikro_guid)
        ).scalar_one_or_none()

        if existing:
            return {
                "user_id": str(existing.kullanici_Guid),
                "username": existing.kullanici_name,
                "firma_siraNo": existing.firma_siraNo,
                "message": "Bu Mikro personel zaten kullanıcıya bağlı"
            }

    if mikroPersonelKod:
        existing = tenant_db.execute(
            select(User).where(User.mikro_personel_kod == mikroPersonelKod)
        ).scalar_one_or_none()

        if existing:
            return {
                "user_id": str(existing.kullanici_Guid),
                "username": existing.kullanici_name,
                "firma_siraNo": existing.firma_siraNo,
                "message": "Bu per_kod zaten kullanıcıya bağlı"
            }   


    try:
        # Firmayı bul
        firm = tenant_db.execute(
            select(Firm).where(Firm.firma_kilitli != True)
        ).scalars().first()


        if not firm:
            raise HTTPException(
                status_code=404,
                detail="Bu firma bulunamadı."
            )

        # Yeni kullanıcı numarası
        user_no = tenant_db.execute(
            text("SELECT COALESCE(MAX(kullanici_no), 0) + 1 FROM users")
        ).scalar()

        if not user_no:
            raise HTTPException(
                status_code=500,
                detail="Kullanıcı numarası üretilemedi."
            )

        # Kullanıcı oluştur
        new_user = User(
        kullanici_Guid=uuid.uuid4(),
        firma_siraNo=firm.firma_sirano,
        kullanici_name=username.strip(),
        kullanici_pw=hash_password(password),
        kullanici_pasif=False,
        role_id=role_id,
        kullanici_LongName=longName,
        kullanici_EMail=email,
        kullanici_Ceptel=cepTel,
        kullanici_no=user_no,
        kullanici_create_user=None,
        mikro_personel_guid=parsed_mikro_guid,
        mikro_personel_kod=mikroPersonelKod,
        mikro_last_sync=datetime.now(),
    )


        tenant_db.add(new_user)
        tenant_db.commit()
        tenant_db.refresh(new_user)

        return {
            "user_id": str(new_user.kullanici_Guid),
            "username": new_user.kullanici_name,
            "firma_siraNo": firm.firma_sirano,
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
# UPDATE USER 
# =====================================================



# =====================================================
# GET CURRENT USER TEST
# =====================================================


"""
@router.get("/get")
def get_current_user_from_token(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        username = payload.get("sub")
        user_guid = payload.get("user_guid")

        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        return {
            "username": username,
            "user_guid": user_guid
        }

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    """    
        
# =====================================================
# TENANT USER UPDATE FİRMA VERGİ NO İLE
# =====================================================
"""
Güncelle içerisinde;

- kullanici_lastup_user --
- kullanici_lastup_date --
- Kullanici_SifreDegisim_date -> buna gerek yok
"""


@router.put("/user-update-by-vergino")
def user_update_to_firmby_vergino(
    vergi_no: str,
    username: str,
    password: str,
    role_id: str,  # checkbox ile seçtiricez.
    # user_no: Optional[int], # (son kullanıcı no +1)
    longName: Optional[str] = None, # isteğe bağlı
    cepTel: Optional[str] = None,  # isteğe bağlı ama bunu number olarak alıp sonra str olarak kaydet
    email: Optional[str] = None,  # isteğe bağlı
    session: SessionContext = Depends(require_tenant)
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
        
        user_no = tenant_db.execute(
            text("SELECT COALESCE(MAX(kullanici_no), 0) + 1 FROM users")
        ).scalar()  

        if not user_no: 
            raise HTTPException(
                status_code=404,
                detail="Kullanıcı numarası bulunamadı."
            )

        # Kullanıcı oluştur
        new_user = User(
            kullanici_Guid=uuid.uuid4(),
            firma_siraNo=firm.firma_sirano,
            kullanici_name=username,
            kullanici_pw=hash_password(password),  # aşağıda hash önerisi var
            kullanici_pasif=False,
            kullanici_LongName=longName,
            kullanici_EMail=email,
            kullanici_Ceptel=cepTel,
            kullanici_no=user_no,
            kullanici_lastup_user=session.user_id,
            kullanici_lastup_date=datetime.now(timezone.utc),
            kullanici_SifreDegisim_date=datetime.now(timezone.utc)
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
# ROLE INSERT FİRMA VERGİ NO İLE
# =====================================================

from sqlalchemy.exc import IntegrityError

@router.post("/role-insert-vergino")
def role_insert_vergino(
    name: str,
    description: str,
    tenant_db: Session = Depends(get_tenant_db),
):
    try:
        new_role = Role(
            id=uuid.uuid4(),
            name=name,
            description=description
        )

        tenant_db.add(new_role)
        tenant_db.commit()
        tenant_db.refresh(new_role)

        return {
            "role_id": str(new_role.id),
            "name": new_role.name,
            "description": new_role.description
        }

    except IntegrityError as e:
        tenant_db.rollback()

        # UNIQUE violation kontrolü
        if "roles_name_key" in str(e):
            raise HTTPException(
                status_code=409,
                detail="Bu isimde bir rol zaten mevcut."
            )

        raise HTTPException(
            status_code=500,
            detail="Veritabanı hatası oluştu."
        )

    except Exception as e:
        tenant_db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Role eklenirken hata oluştu: {str(e)}"
        )
    finally:
        tenant_db.close()

# =====================================================
# ALL ROLES 
# =====================================================

@router.get("/get-all-roles")
def get_all_roles(
    tenantdb: Session = Depends(get_tenant_db),
):

    try:
        roles = tenantdb.execute(
            select(Role)
        ).scalars().all()

        return {
            "count": len(roles),
            "roles": [
                {
                    "id": str(role.id),
                    "name": role.name,
                    "description": role.description,
                }
                for role in roles
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Roller alınırken hata oluştu: {str(e)}"
        ) 
    finally:
        tenantdb.close()



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
# user login  
# =====================================================

@router.post("/user-login-to-firmby-vergino2")
def user_login_to_firmby_vergino2(
    vergi_no: str,
    email: str,
    password: str
):
    tenant_db: Session = connect_tenant_by_vergiNo(vergi_no)

    try:
        # ================= USER AUTH =================
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

        # ================= TOKEN =================
        token = create_access_token(
            {
                "sub": str(user.kullanici_Guid),
                "domain": "tenant",
                "tenant_id": vergi_no,
                "role_id": str(user.role_id) if user.role_id else None
            },
            expires_delta=timedelta(days=3)
        )

        # ================= MIKRO API PASSWORD HASH =================
        try:
            mikro = tenant_db.execute(
                select(MikroApiSettings).limit(1)
            ).scalar_one_or_none()

            if mikro and mikro.api_pw_non_hash:
                api_pw = generate_mikro_md5(mikro.api_pw_non_hash)

                mikro.api_pw = api_pw

                tenant_db.commit()

        except Exception as e:
            # Login’i ASLA bozma
            tenant_db.rollback()
            print("Mikro API hash update failed:", str(e))

        # ================= RESPONSE =================
        return {
            "access_token": token,
            "token_type": "bearer",
            "user_id": str(user.kullanici_Guid),
            "username": user.kullanici_name
        }

    finally:
        tenant_db.close()

## =====================================================
# get all admin personel 
# =====================================================

@router.post("/logout")
def tenant_logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    token = credentials.credentials

    payload = decode_access_token(token)

    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    domain = payload.get("domain")

    if domain != "tenant":
        raise HTTPException(
            status_code=403,
            detail="Invalid token domain"
        )

    logger.info(
        f"TENANT LOGOUT | user_id={user_id} | tenant_id={tenant_id}"
    )

    return {
        "message": "Tenant logout successful"
    }


# =====================================================
# get all admin personel 
# =====================================================

@router.get("/get-all-admins")
def get_admin_users(
    tenant_db: Session = Depends(get_tenant_db),
    session: SessionContext = Depends(require_tenant),
):
    admin_role_id = get_role_id(tenant_db, "ADMIN")

    if not admin_role_id:
        return []

    users = tenant_db.execute(
        select(User).where(
            User.role_id == admin_role_id,
            User.kullanici_pasif == False
        )
    ).scalars().all()

    return users

# =====================================================
# get all worker personel 
# =====================================================

@router.get("/get-all-workers")
def get_worker_users(
    tenant_db: Session = Depends(get_tenant_db),
    session: SessionContext = Depends(require_tenant),
):
    worker_role_id = get_role_id(tenant_db, "WORKER")

    if not worker_role_id:
        return []
    
    workers = tenant_db.execute(
        select(User).where(
            User.role_id == worker_role_id,
            User.kullanici_pasif == False
        )
    ).scalars().all()

    return workers

# =====================================================
# get all worker personel 
# =====================================================

@router.get("/get-all-users")
def get_all_users(
    tenant_db: Session = Depends(get_tenant_db),
    session: SessionContext = Depends(require_tenant),
):
    users = tenant_db.execute(
        select(User)
    ).scalars().all()

    if not users:
        raise HTTPException(
            status_code=404,
            detail="herhangi bir kullanıcı bulunamadı."
        )

    return users


# =====================================================
# get all branches 
# =====================================================

@router.get("/get-all-branches")
def get_all_branches(
    tenant_db: Session = Depends(get_tenant_db),
    session: SessionContext = Depends(require_tenant),
):
    branches = tenant_db.execute(
        select(Branch)
    ).scalars().all()

    if not branches:
        raise HTTPException(
            status_code=404,
            detail="herhangi bir şube bulunamadı."
        )

    return branches

# =====================================================
# get MikroAPI Info 
# =====================================================

@router.get("/get-all-mikro-info")
def get_API_Info(
    tenant_db: Session = Depends(get_tenant_db),
    session: SessionContext = Depends(require_tenant),
):
    try:
        api_list = tenant_db.execute(
            select(MikroApiSettings)
        ).scalars().all()

        # İŞ KURALI HATASI
        if not api_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mikro API bilgileri henüz tanımlanmamış."
            )

        return api_list

    except SQLAlchemyError as e:
        # GERÇEK SİSTEM HATASI
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Veritabanı hatası"
        )

# =====================================================
# GET ALL user_favorites 
# =====================================================

@router.get("/get-all-favorites")
def get_all_favorites( 
    tenant_db: Session = Depends(get_tenant_db),
    session: SessionContext = Depends(require_tenant),
    ):
   
   try:
       favorite_list = tenant_db.execute(
           select(UserFavorite)
       ).scalars().all()

       if not favorite_list:
           raise HTTPException(
               status_code=status.HTTP_404_NOT_FOUND,
               detail="favori bilgileri yok."
           )
       
       return favorite_list
   except SQLAlchemyError:
       raise HTTPException(
           status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
           detail="veritabanı hatası"
       )
   
# =====================================================
# GET ALL user_favorites BY ID
# =====================================================

@router.get("/get-favorite-by-id")
def get_favorite_by_id(
    module_key:str,
    current_user: User = Depends(get_current_user),
    tenant_db: Session = Depends(get_tenant_db),
    session: SessionContext = Depends(require_tenant),
    ):
    
    try: 
        favorite_list_id = tenant_db.execute(
            select(UserFavorite).where(
                UserFavorite.user_id == current_user.kullanici_Guid,
                UserFavorite.module_key == module_key,
                )
        ).scalar_one_or_none()

        if not favorite_list_id: 
            raise HTTPException(
               status_code=status.HTTP_404_NOT_FOUND,
               detail="böyle bir veri yok."
           )
        
        return favorite_list_id
    
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="veritabanı hatası"
        )
    

# =====================================================
# INSERT mikro_api_settings
# =====================================================

@router.put("/push-mikro-info")
def push_mikro_infos(
    payload: MikroApiUpdateSchema,
    request: Request,
    tenant_db: Session = Depends(get_tenant_db),
):
    print("==== DEBUG AUTH ====")
    print("Authorization header:", request.headers.get("authorization"))
    print("All headers:", dict(request.headers))
    print("====================")

    
    firm = tenant_db.execute(
        select(Firm).where(Firm.firma_kilitli != True)
    ).scalar_one_or_none()

    if not firm:
        raise HTTPException(
            status_code=404,
            detail="firma bilgisi yok."
        )
    
    mikro = tenant_db.execute(
        select(MikroApiSettings).where(MikroApiSettings.firma_Guid == firm.firma_Guid)
    ).scalar_one_or_none()
    

    if not mikro:
        raise HTTPException(
            status_code=404,
            detail="bu guid değeri ile mikro API bilgileri bulunamadı!"
        )
    
    """    
    BU HASH MANTIĞI POSTMAN İÇERİSİNDEKİ GİBİ OLACAK. O GÜN VE ŞİFREYİ ALIP MD5 E ÇEVİRİP KAYDEDECEK.
    (YYYY-MM-DD ŞİFRE) = MD5PASSWORD

    hashed_pw = hashlib.md5(
    f"{payload.api_pw}{payload.api_calismayili}".encode()
    ).hexdigest()
    """

    # ===== MD5 ŞİFRELEME =====
    current_date = datetime.now().strftime("%Y-%m-%d")
    hash_input = f"{current_date} {payload.api_pw_non_hash}"
    hashed_pw = hashlib.md5(hash_input.encode("utf-8")).hexdigest()

    mikro.api_ip = payload.api_ip    
    mikro.api_port = payload.api_port
    mikro.api_protocol = payload.api_protocol
    mikro.api_firmakodu = payload.api_firmakodu
    mikro.api_calismayili = payload.api_calismayili
    mikro.api_kullanici = payload.api_kullanici
    mikro.api_pw = hashed_pw 
    mikro.api_pw_non_hash = payload.api_pw_non_hash
    mikro.api_key = payload.api_key
    mikro.api_firmano = payload.api_firmano
    mikro.sube_no = payload.sube_no
    
    # Audit alanları
    #mikro.api_lastup_user = current_user # JWT varsa buradan al
    mikro.api_lastup_date = datetime.now()

    tenant_db.commit()
    tenant_db.refresh(mikro) 

    return {
        "message": "Mikro API Bilgileri başarıyla güncellendi",
    }

# =====================================================
# GET mikro_api_settings
# =====================================================

@router.get("/get-mikro-info")
def get_mikro_info(
    tenant_db: Session = Depends(get_tenant_db),
    session: SessionContext = Depends(require_tenant),
):
    mikro_info = tenant_db.execute(
        select(MikroApiSettings)
    ).scalar_one_or_none()

    if not mikro_info:
        raise HTTPException(
            status_code=404,
            detail="Mikro API bilgileri bulunamadı."
        )

    return mikro_info   

