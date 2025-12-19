import datetime
from sqlalchemy import UUID, Column, String, UniqueConstraint
from app.db.base import Base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, String, Boolean, Integer, ForeignKey, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base
import uuid

class Company(Base):
    __tablename__ = "companies"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_code = Column(String, unique=True)
    name = Column(String, unique=True)
    status = Column(String) # sonradan eklendi
    status_message = Column(String)
    created_at = Column(DateTime,server_default=func.now()) 

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
    mikro_settings = relationship(
        "MikroSettings",
        back_populates="company",
        cascade="all, delete-orphan"
    )
    licenses = relationship(
        "License",
        back_populates="company",
        cascade="all, delete-orphan"
    )

"""
Table companies {
  id uuid [pk]
  company_code varchar [not null, unique] // X_FIRMA
  name varchar [not null]
  status varchar // PENDING, ACTIVE, FAILED, SUSPENDED
  status_message varchar
  created_at timestamp
}
"""

class AdminUser(Base):
    __tablename__ = "admin_users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True)
    username = Column(String, unique=True)
    password_hash = Column(String) # bu kolon nasıl hash olacak
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, server_default=func.now()) # her giriş yaptığında o anki tarih yazılacak
    created_at = Column(DateTime, server_default=func.now()) 

"""
Table admin_users {
  id uuid [pk]
  email varchar [not null, unique]
  username varchar [not null, unique]
  password_hash varchar [not null]
  is_active boolean [default: true]
  last_login_at timestamp
  created_at timestamp
}
"""


class TenantDB(Base):
    __tablename__ = "tenant_dbs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False
    )
    db_name = Column(String,unique=True, nullable=False)
    db_user = Column(String, unique=True, nullable=False)
    db_password = Column(String, nullable=False)
    ssl_mode = Column(String)
    is_active = Column(Boolean, default=True,nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    company = relationship(
        "Company",
        back_populates="tenant_dbs"
    )

"""
Table tenant_dbs {
  id uuid [pk]
  company_id uuid [not null]
  db_name unique [not null] 
  db_user varchar [not null]
  db_password varchar [not null]
  ssl_mode varchar
  is_active boolean [default: true]
  created_at timestamp
}
"""

class Modules(Base):
    __tablename__ = "modules"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String, unique=True,nullable=False) # modül kodu
    name = Column(String)
    is_active = Column(Boolean,default=True)


"""
Table modules {
  id uuid [pk]
  code varchar [not null, unique] // INVENTORY, SALES, PRODUCTION
  name varchar
  is_active boolean [default: true]
}
"""

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

    # RELATIONSHIPS
    company = relationship("Company", back_populates="company_modules")
    modules = relationship("Modules", back_populates="company_modules")
    

"""
Table company_modules {
  company_id uuid [not null]
  module_id uuid [not null]
  enabled boolean [default: true]

  indexes {
    (company_id, module_id) [unique]
  }
}
    """


class MikroSettings(Base):
    __tablename__ = "mikro_settings"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False
    )
    api_url = Column(String, unique=True, nullable=False)
    api_key = Column(String, unique=True, nullable=False)
    db_host = Column(String, nullable=False)
    db_port = Column(String, nullable=False)
    company_code = Column(Integer, unique=True,nullable=False)
    user_code = Column(String, nullable=False) # mikro ana kullanıcı
    user_password = Column(String) # mikro ana kullanıcı şifresi (MD5 HASH olacak)
    departmant_no = Column(Integer) 
    is_active = Column(Boolean,default=True)
    created_at = Column(DateTime, server_default=func.now())
    current_work_year = Column(DateTime, default=lambda: datetime.utcnow().year, nullable=False)

"""
Table mikro_settings {
  id uuid [pk]
  company_id uuid [not null]
  api_url varchar
  api_key varchar
  db_host varchar [not null]
  db_port int [default: 5432]
  company_code int
  user_code varchar
  user_password varchar // MD5 HASH (Mikro ERP credential, NOT user login password)
  deparmant_no int
  is_active boolean [default: true]
  created_at timestamp
  current_work_year varchar
}
"""


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    actor_id = Column(UUID(as_uuid=True), nullable=True)
    actor_type = Column(String, nullable=False)   # ADMIN, SYSTEM, API
    actor_label = Column(String)                  # admin@winpol.local

    action = Column(String, nullable=False)
    target_type = Column(String)
    target_id = Column(UUID(as_uuid=True))

    status = Column(String, nullable=False)       # SUCCESS, FAILED
    message = Column(String)

    created_at = Column(DateTime, server_default=func.now())


"""
Table system_logs {
  id uuid [pk]
  actor_id uuid       // admin_user.id
  action varchar      // COMPANY_CREATED, TENANT_DB_CREATED
  target_type varchar // COMPANY, TENANT_DB, USER
  target_id uuid
  status varchar      // SUCCESS, FAILED
  message varchar
  created_at timestamp
}

"""


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

    is_active = Column(Boolean, default=True, nullable=False)
    is_paid = Column(Boolean, default=False, nullable=False)

    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    company = relationship("Company", back_populates="licenses")
    module = relationship("Modules")

    __table_args__ = (
        UniqueConstraint("company_id", "module_id", name="uq_company_module_license"),
    )

"""
runtime lisans kontrolü:

license = (
    session.query(License)
    .filter(
        License.company_id == company_id,
        License.module_id == module_id,
        License.is_active == True
    )
    .first()
)

if not license:
    raise Exception("Bu modül için lisans yok")

if license.end_date and license.end_date < datetime.utcnow():
    raise Exception("Lisans süresi dolmuş")

"""