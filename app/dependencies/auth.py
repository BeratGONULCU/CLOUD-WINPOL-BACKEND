from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from uuid import UUID

from app.core.security import decode_access_token
from app.core.session import SessionContext

security = HTTPBearer(auto_error=True)


def get_current_session(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> SessionContext:
    token = credentials.credentials
    payload = decode_access_token(token)

    return SessionContext(
        user_id=UUID(payload["sub"]),
        domain=payload["domain"],
        tenant_id=payload.get("tenant_id"),
        role_id=payload.get("role_id"),
        jti=payload["jti"]
    )


def require_master(
    session: SessionContext = Depends(get_current_session)
):
    if session.domain != "master":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Master access required"
        )
    return session


def require_tenant(
    session: SessionContext = Depends(get_current_session)
):
    if session.domain != "tenant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant access required"
        )
    return session
