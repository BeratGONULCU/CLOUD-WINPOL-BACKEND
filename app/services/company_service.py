from app.models.master.master import Company, TenantDB
from app.db.tenant_provisioning import create_tenant_db, drop_tenant_db
from app.core.security import generate_password

# service to handle new company creation if anything added to the company table 
# this service only creates tenantDB , adding nothing in it.
def create_company(db, vergi_no: str, name: str, company_code: str):
    tenant_db_name = vergi_no  

    try:
        company = Company(
            vergi_no=vergi_no,
            name=name,
            company_code=company_code,
            status="PROVISIONING"
        )
        db.add(company)
        db.flush()

        tenant_db = TenantDB(
            company_id=company.id,
            db_name=tenant_db_name,        
            db_user=f"tenant_{company_code.lower()}",
            db_password=generate_password(),
            ssl_mode="disable"
        )
        db.add(tenant_db)

        db.commit()  # master kesinleşir

        create_tenant_db(tenant_db_name)   

        company.status = "ACTIVE"
        db.commit()

        return company

    except Exception:
        db.rollback()
        drop_tenant_db(tenant_db_name)    
        raise
