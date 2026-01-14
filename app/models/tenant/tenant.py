import uuid
from sqlalchemy import (
    CheckConstraint, Column, Identity, String, Boolean, Integer,
    ForeignKey, DateTime, UniqueConstraint, text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_tenant import TenantBase


# =====================================================
# FIRM
# =====================================================

class Firm(TenantBase):
    __tablename__ = "firms"

    firma_Guid = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )

    firma_sirano = Column(
        Integer,
        Identity(start=1),
        nullable=False,
        unique=True
    )

    firma_kilitli = Column(Boolean, nullable=False, default=False)

    firma_create_user = Column(UUID(as_uuid=True), nullable=True)
    firma_lastup_user = Column(UUID(as_uuid=True), nullable=True)

    firma_create_date = Column(DateTime, server_default=func.now())
    firma_lastup_date = Column(DateTime, onupdate=func.now())

    firma_unvan = Column(String(127))
    firma_unvan2 = Column(String(127))

    firma_TCkimlik = Column(String(11), unique=True, nullable=True)
    firma_FVergiNo = Column(String(10), unique=True, nullable=False)
    firma_FVergiDaire = Column(String(50))
    firma_web_sayfasi = Column(String(50))

    branches = relationship(
        "Branch",
        back_populates="firm",
        cascade="all, delete-orphan"
    )

    users = relationship(
        "User",
        back_populates="firm",
        cascade="all, delete-orphan"
    )

    mikro_api_settings = relationship(
        "MikroApiSettings",
        back_populates="firm",
        cascade="all, delete-orphan",
        foreign_keys="MikroApiSettings.firma_Guid"
    )

    __table_args__ = (
    CheckConstraint(
        """
        (
            "firma_TCkimlik" IS NOT NULL
            AND "firma_FVergiNo" IS NOT NULL
            AND length("firma_TCkimlik") = 11
            AND length("firma_FVergiNo") = 11
        )
        OR
        (
            "firma_TCkimlik" IS NULL
            AND "firma_FVergiNo" IS NOT NULL
            AND length("firma_FVergiNo") = 10
        )
        """,
        name="ck_firm_tax_identity"
    ),
)



    
    """
    endpoint içerisinde kontrol 

    if not firm.firma_TCkimlik and not firm.firma_FVergiNo:
    raise HTTPException(
        status_code=400,
        detail="Firma için TC Kimlik No veya Vergi No girilmelidir."
    )
"""


# =====================================================
# BRANCH
# =====================================================

class Branch(TenantBase):
    __tablename__ = "branches"

    sube_Guid = Column(
    UUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4
    )

    sube_kilitli = Column(Boolean, default=False)
    sube_create_user = Column(Integer)
    sube_create_date = Column(DateTime, server_default=func.now())
    sube_lastup_user = Column(Integer)
    sube_lastup_date = Column(DateTime)

    sube_bag_firma = Column(
        Integer,
        ForeignKey("firms.firma_sirano"),
        nullable=False
    )

    sube_no = Column(Integer)
    sube_adi = Column(String(100))
    sube_kodu = Column(String(20))
    sube_MersisNo = Column(String(16),unique=True)
    sube_Cadde = Column(String(50))
    sube_Mahalle = Column(String(50))
    sube_Sokak = Column(String(50))
    sube_Semt = Column(String(25))
    sube_Apt_No = Column(String(10))
    sube_Daire_No = Column(String(10))
    sube_Posta_Kodu = Column(String(8))
    sube_Ilce = Column(String(50))
    sube_Il = Column(String(50))
    sube_Ulke = Column(String(50), default="Türkiye")
    sube_TelNo1 = Column(String(10))

    firm = relationship("Firm", back_populates="branches")


# =====================================================
# ROLE & PERMISSION
# =====================================================

class Role(TenantBase):
    __tablename__ = "roles"

    id = Column(
    UUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4
    )
    name = Column(String, unique=True, nullable=False)
    description = Column(String)

    permissions = relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="roles"
    )


class Permission(TenantBase):
    __tablename__ = "permissions"

    id = Column(
    UUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4
    )
    code = Column(String, unique=True, nullable=False)
    description = Column(String)

    roles = relationship(
        "Role",
        secondary="role_permissions",
        back_populates="permissions"
    )


class RolePermission(TenantBase):
    __tablename__ = "role_permissions"

    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True)
    permission_id = Column(UUID(as_uuid=True), ForeignKey("permissions.id"), primary_key=True)


# =====================================================
# USER
# =====================================================

class User(TenantBase):
    __tablename__ = "users"

    kullanici_Guid = Column(
    UUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4
    )   


    firma_siraNo = Column(
    Integer,
    ForeignKey("firms.firma_sirano"),
    nullable=False
    )

    kullanici_create_user = Column(UUID(as_uuid=True), nullable=True)
    kullanici_create_date = Column(DateTime, server_default=func.now())
    kullanici_lastup_user = Column(Integer)
    kullanici_lastup_date = Column(DateTime)

    # bu kısımdadki kullanıcı bilgileri güncellendi
    kullanici_no = Column(Integer,autoincrement=True, unique=True)
    kullanici_name = Column(String(20),unique=True, nullable=False)
    kullanici_pw = Column(String(127), nullable=False)
    kullanici_LongName = Column(String(50))
    kullanici_EMail = Column(String(50), unique=True,  nullable=False)
    kullanici_SifreTipi = Column(Integer)
    kullanici_SifreDegisim_date = Column(DateTime)
    kullanici_pasif = Column(Boolean, default=False)
    kullanici_Ceptel = Column(String(11)) 

    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"))

    firm = relationship("Firm", back_populates="users")
    role = relationship("Role")
    favorites = relationship(
    "UserFavorite",
    back_populates="user",
    cascade="all, delete-orphan"
    )



# =====================================================
# ATTENDANCE
# =====================================================

class AttendanceLog(TenantBase):
    __tablename__ = "attendance_logs"

    id = Column(
    UUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.kullanici_Guid"))
    check_type = Column(String)  # IN / OUT
    created_at = Column(DateTime, server_default=func.now())


# =====================================================
# AUDIT LOG
# =====================================================

class AuditLog(TenantBase):
    __tablename__ = "audit_logs"

    id = Column(
    UUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4
    )       
    actor_id = Column(UUID(as_uuid=True))
    action = Column(String)
    target_type = Column(String)
    target_external_id = Column(String)
    created_at = Column(DateTime, server_default=func.now())


# =====================================================
# MIKRO API SETTINGS (TENANT)
# =====================================================

# eski mikro_api tablosu (şuanda masterdb içerisinde tutuluyor , firms içerisindeki firma_sirano ile bağlı)



class MikroApiSettings(TenantBase):
    __tablename__ = "mikro_api_settings"

    # =======================
    # PRIMARY KEY
    # =======================
    api_Guid = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # =======================
    # FIRM RELATION
    # =======================
    firma_Guid = Column(
        UUID(as_uuid=True),
        ForeignKey("firms.firma_Guid", ondelete="CASCADE"),
        nullable=False
    )

    firma_siraNo = Column(
        Integer,
        ForeignKey("firms.firma_sirano", ondelete="CASCADE"),
        nullable=False
    )

    # =======================
    # AUDIT / STATE
    # =======================
    api_kilitli = Column(
        Boolean,
        nullable=False,
        server_default="false"
    )

    api_create_user = Column(UUID(as_uuid=True), nullable=True)
    api_lastup_user = Column(UUID(as_uuid=True), nullable=True)

    api_create_date = Column(
        DateTime,
        server_default=func.now()
    )

    api_lastup_date = Column(
        DateTime,
        onupdate=func.now()
    )

    # =======================
    # CONNECTION INFO
    # =======================
    api_ip = Column(
        String(64),
        nullable=False,
        comment="Mikro ERP API IP / Host"
    )

    api_port = Column(
        Integer,
        nullable=False,
        comment="Mikro ERP API Port"
    )

    api_protocol = Column(
        String(10),
        nullable=False,
        server_default="http",
        comment="http | https"
    )

    # =======================
    # MIKRO INFO
    # =======================
    api_firmakodu = Column(
        String(50),
        nullable=False
    )

    api_calismayili = Column(
        String(4),
        nullable=False
    )

    api_kullanici = Column(String(100))
    api_pw = Column(String(255))
    api_key = Column(String(255))

    api_firmano = Column(String(20))
    api_subeno = Column(String(20))
    api_veritabani = Column(String(100))

    # =======================
    # RELATIONSHIP
    # =======================
    firm = relationship(
        "Firm",
        back_populates="mikro_api_settings",
        foreign_keys=[firma_Guid]
    )


# =====================================================
# USER FAVORITES
# =====================================================

class UserFavorite(TenantBase):
    __tablename__ = "user_favorites"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.kullanici_Guid", ondelete="CASCADE"),
        nullable=False
    )

    module_key = Column(
        String(50),
        nullable=False
    )

    created_at = Column(
        DateTime,
        server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "module_key",
            name="uq_user_favorites_user_module"
        ),
    )

    user = relationship(
        "User",
        back_populates="favorites"
    )

