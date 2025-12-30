from fastapi import APIRouter, Depends, HTTPException, Response,Request
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.master.master import AdminUser
from app.core.security import hash_password, verify_password, create_access_token
from app.core.logger import logger
from app.core.auth_context import get_current_token
from app.core.security import decode_access_token
from datetime import timedelta


router = APIRouter(prefix="/admin", tags=["Admin Auth"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/register")
def admin_register(email: str, username: str, password: str, db: Session = Depends(get_db)):
    if db.query(AdminUser).filter(AdminUser.email == email).first():
        raise HTTPException(400, "Admin already exists")

    admin = AdminUser(
        email=email,
        username=username,
        password_hash=hash_password(password)
    )
    db.add(admin)
    db.commit()
    return {"message": "Admin created"}


"""
@router.post("/login")
def admin_login(
    response: Response,
    email: str,
    password: str,
    db: Session = Depends(get_db)
):
    admin = db.query(AdminUser).filter(AdminUser.email == email).first()
    if not admin or not verify_password(password, admin.password_hash):
        logger.warning(f"LOGIN FAILED | email={email}")
        raise HTTPException(401, "Invalid credentials")

    token = create_access_token({"sub": str(admin.id)})

    # WEB için cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False  # prod'da True
    )

    logger.info(
        f"LOGIN SUCCESS | admin_id={admin.id} | email={email}"
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }

"""




@router.post("/login")
def admin_login(email: str, password: str, db: Session = Depends(get_db)):
    admin = db.query(AdminUser).filter(AdminUser.email == email).first()
    if not admin or not verify_password(password, admin.password_hash):
        raise HTTPException(401, "Invalid credentials")

    #token = create_access_token({"sub": str(admin.id)})
    token = create_access_token(
    {
        "sub": str(admin.id),
        "domain": "master",
        "tenant_id": None
    },
    expires_delta=timedelta(days=3)
)
    return {"access_token": token}




@router.get("/ping-login")
def ping_login(
    request: Request,
    token: str = Depends(get_current_token)
):
    payload = decode_access_token(token)

    source = "cookie" if request.cookies.get("access_token") else "header"

    logger.info(
        f"PING LOGIN | user_id={payload.get('sub')} | source={source}"
    )

    return {
        "status": "authenticated",
        "user_id": payload.get("sub"),
        "token_source": source
    }


"""
@router.get("/me")
def get_admin_details(
    admin_id: str = Depends(get_current_admin_id),
    db: Session = Depends(get_db),
):
    admin = db.query(AdminUser).filter(AdminUser.id == admin_id).first()
    if not admin:
        raise HTTPException(404, "Admin not found")

    return {
        "id": str(admin.id),
        "email": admin.email,
        "username": admin.username
    }
"""

@router.get("/all")
def get_all_adminusers(db: Session = Depends(get_db)):
    admins = db.query(AdminUser).all()
    return [
        {
            "id": str(admin.id),
            "email": admin.email,
            "username": admin.username
        }
        for admin in admins
    ]   
      

@router.get("/ping")
def ping():
    return {"status": "ok"}
