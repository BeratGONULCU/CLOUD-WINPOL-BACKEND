from app.models.master.master import Company, TenantDB
from app.db.tenant_provisioning import create_tenant_db

def provision_company(db, data):
    company = Company(
        company_code=data.company_code,
        name=data.name,
        status="ACTIVE"
    )
    db.add(company)
    db.flush()

    tenant_db_name = f"tenant_{data.company_code.lower()}"

    tenant_db = TenantDB(
        company_id=company.id,
        db_name=tenant_db_name,
        db_user="postgres",
        db_password="postgres"
    )
    db.add(tenant_db)

    create_tenant_db(tenant_db_name)

    db.commit()
    return company
