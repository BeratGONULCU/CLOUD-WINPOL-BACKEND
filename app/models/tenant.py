import uuid
from sqlalchemy import (
    Column, String, Boolean, Integer,
    ForeignKey, DateTime, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class Firm(Base):
    __tablename__ = "firms"

    firma_Guid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firma_sirano = Column(Integer, unique=True, nullable=False)

    firma_kilitli = Column(Boolean, default=False)
    firma_create_user = Column(Integer)
    firma_create_date = Column(DateTime, server_default=func.now())
    firma_lastup_user = Column(Integer)
    firma_lastup_date = Column(DateTime)

    firma_unvan = Column(String(127))
    firma_unvan2 = Column(String(127))
    firma_TCkimlik = Column(String(15))
    firma_FVergiDaire = Column(String(10))
    firma_FVergiNo = Column(String(20))
    firma_web_sayfasi = Column(String(50))

    branches = relationship("Branch", back_populates="firm")
    users = relationship("User", back_populates="firm")
    mikro_settings = relationship("MikroApiSettings", back_populates="firm")


class Branch(Base):
    __tablename__ = "branches"

    sube_Guid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    sube_kilitli = Column(Boolean, default=False)
    sube_create_user = Column(Integer)
    sube_create_date = Column(DateTime, server_default=func.now())
    sube_lastup_user = Column(Integer)
    sube_lastup_date = Column(DateTime)

    # FIRMA → firma_sirano (INT)
    sube_bag_firma = Column(Integer, ForeignKey("firms.firma_sirano"), nullable=False)

    sube_no = Column(Integer)
    sube_adi = Column(String(50))
    sube_kodu = Column(String(15))
    sube_MersisNo = Column(String(25))

    sube_Cadde = Column(String(50))
    sube_Mahalle = Column(String(50))
    sube_Sokak = Column(String(50))
    sube_Semt = Column(String(25))
    sube_Apt_No = Column(String(10))
    sube_Daire_No = Column(String(10))
    sube_Posta_Kodu = Column(String(8))
    sube_Ilce = Column(String(50))
    sube_Il = Column(String(50))
    sube_Ulke = Column(String(50))
    sube_TelNo1 = Column(String(10))

    firm = relationship(
        "Firm",
        primaryjoin="Firm.firma_sirano == Branch.sube_bag_firma",
        back_populates="branches"
    )

class Role(Base):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)
    description = Column(String)

    permissions = relationship("RolePermission", back_populates="role")



class Permission(Base):
    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String, unique=True, nullable=False)
    description = Column(String)

    roles = relationship("RolePermission", back_populates="permission")


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True)
    permission_id = Column(UUID(as_uuid=True), ForeignKey("permissions.id"), primary_key=True)

    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")


class User(Base):
    __tablename__ = "users"

    kullanici_Guid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    firma_siraNo = Column(
        Integer,
        ForeignKey("firms.firma_sirano"),
        nullable=False
    )

    kullanici_create_user = Column(Integer)
    kullanici_create_date = Column(DateTime, server_default=func.now())
    kullanici_lastup_user = Column(Integer)
    kullanici_lastup_date = Column(DateTime)

    kullanici_no = Column(Integer)
    kullanici_name = Column(String(20))
    kullanici_pw = Column(String(127))
    kullanici_LongName = Column(String(50))
    kullanici_EMail = Column(String(50))
    kullanici_SifreTipi = Column(Integer)
    kullanici_SifreDegisim_date = Column(DateTime)
    kullanici_pasif = Column(Boolean, default=False)
    kullanici_Ceptel = Column(String(20))

    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"))

    firm = relationship(
        "Firm",
        primaryjoin="Firm.firma_sirano == User.firma_siraNo",
        back_populates="users"
    )
    role = relationship("Role")


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.kullanici_Guid"))
    check_type = Column(String)  # IN / OUT
    created_at = Column(DateTime, server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id = Column(UUID(as_uuid=True))  # user or service
    action = Column(String)
    target_type = Column(String)
    target_external_id = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class MikroApiSettings(Base):
    __tablename__ = "mikro_api_settings"

    api_Guid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    firma_Guid = Column(
        UUID(as_uuid=True),
        ForeignKey("firms.firma_Guid"),
        nullable=False
    )

    firma_siraNo = Column(
        Integer,
        ForeignKey("firms.firma_sirano"),
        nullable=False
    )

    api_kilitli = Column(Boolean, default=False)
    api_create_user = Column(Integer)
    api_create_date = Column(DateTime, server_default=func.now())
    api_lastup_user = Column(Integer)
    api_lastup_date = Column(DateTime)

    api_key = Column(String)
    api_firmano = Column(String)
    api_subeno = Column(String)
    api_veritabani = Column(String)
    api_kullanici = Column(String)
    api_pw = Column(String)

    firm = relationship("Firm", back_populates="mikro_settings")
