import uuid
from sqlalchemy import (
    Column, String, Boolean, Integer,
    ForeignKey, DateTime, UniqueConstraint, text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


# =====================================================
# ADMIN USERS
# =====================================================

class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(
    UUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4
    )
    email = Column(String, unique=True, nullable=False)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime(timezone=True),nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# =====================================================
# COMPANY
# =====================================================

class Company(Base):
    __tablename__ = "companies"

    id = Column(
    UUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4
    )
    # vergi no kısmı olabilir
    vergi_no = Column(String(10), unique=True, nullable=False)  # X_VKN
    company_code = Column(String, unique=True, nullable=False)  # X_FIRMA
    name = Column(String, nullable=False)

    status = Column(String)  # PENDING, ACTIVE, FAILED, SUSPENDED
    status_message = Column(String)
    created_at = Column(DateTime, server_default=func.now())

    tenant_dbs = relationship(
        "TenantDB",
        back_populates="company",
        cascade="all, delete-orphan"
    )

    company_modules = relationship(
        "CompanyModule",
        back_populates="company",
        cascade="all, delete-orphan"
    )

    licenses = relationship(
        "License",
        back_populates="company",
        cascade="all, delete-orphan"
    )


# =====================================================
# TENANT DATABASES
# =====================================================

class TenantDB(Base):
    __tablename__ = "tenant_dbs"

    id = Column(
    UUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4
    )   

    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False
    )

    db_name = Column(String, nullable=False)
    db_user = Column(String, nullable=False)
    db_password = Column(String, nullable=False)
    ssl_mode = Column(String)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    company = relationship("Company", back_populates="tenant_dbs")


# =====================================================
# MODULES
# =====================================================

class Module(Base):
    __tablename__ = "modules"

    id = Column(
    UUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4
    )
    code = Column(String, unique=True, nullable=False)  # INVENTORY, SALES
    name = Column(String)
    is_active = Column(Boolean, default=True)

    company_modules = relationship("CompanyModule", back_populates="module")


# =====================================================
# COMPANY MODULES
# =====================================================

class CompanyModule(Base):
    __tablename__ = "company_modules"

    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        primary_key=True
    )

    module_id = Column(
        UUID(as_uuid=True),
        ForeignKey("modules.id", ondelete="CASCADE"),
        primary_key=True
    )

    enabled = Column(Boolean, default=True)

    company = relationship("Company", back_populates="company_modules")
    module = relationship("Module", back_populates="company_modules")
    

# =====================================================
# SYSTEM LOGS
# =====================================================

class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(
    UUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4
    )

    actor_id = Column(UUID(as_uuid=True))
    action = Column(String, nullable=False)

    target_type = Column(String)
    target_id = Column(UUID(as_uuid=True))

    status = Column(String, nullable=False)  # SUCCESS / FAILED
    message = Column(String)

    created_at = Column(DateTime, server_default=func.now())


# =====================================================
# LICENSES
# =====================================================

class License(Base):
    __tablename__ = "licenses"

    id = Column(
    UUID(as_uuid=True),
    primary_key=True,
    default=uuid.uuid4
    )

    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False
    )

    module_id = Column(
        UUID(as_uuid=True),
        ForeignKey("modules.id", ondelete="CASCADE"),
        nullable=False
    )

    is_active = Column(Boolean, default=True)
    is_paid = Column(Boolean, default=False)

    start_date = Column(DateTime)
    end_date = Column(DateTime)

    created_at = Column(DateTime, server_default=func.now())

    company = relationship("Company", back_populates="licenses")
    module = relationship("Module")

    __table_args__ = (
        UniqueConstraint("company_id", "module_id", name="uq_company_module_license"),
    )
