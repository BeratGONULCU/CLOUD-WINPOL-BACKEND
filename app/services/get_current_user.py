from app.models.master.master import Company, TenantDB
from app.db.tenant_provisioning import create_tenant_db, drop_tenant_db
from app.core.security import generate_password
from fastapi import Request, HTTPException, Depends

def get_current_user(request: Request):
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_access_token(token)
    user_id = payload.get("sub")

    return user_id
