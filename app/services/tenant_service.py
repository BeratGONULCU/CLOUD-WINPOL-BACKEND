from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# vergiNo is also the name of the tenant databases
def connect_tenant_by_vergiNo(vergi_no: str):

    tenant_db_name = vergi_no

    DATABASE_URL = (
        f"postgresql://{settings.POSTGRES_USER}:"
        f"{settings.POSTGRES_PASSWORD}@"
        f"{settings.POSTGRES_HOST}:"
        f"{settings.POSTGRES_PORT}/"
        f"{tenant_db_name}"
    )

    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True
    )

    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )

    return SessionLocal()

# TC Kimlik No validation 
# String olarak gelen 11 nolu tc kimlik no'da her hane rakam mı?
def validate_tc_kimlik(tc: str) -> bool:
    if not tc or len(tc) != 11 or not tc.isdigit():
        return False

    if tc[0] == "0":
        return False

    digits = list(map(int, tc))

    odd_sum = sum(digits[0:9:2])
    even_sum = sum(digits[1:8:2])

    digit10 = ((odd_sum * 7) - even_sum) % 10
    digit11 = sum(digits[:10]) % 10

    return digit10 == digits[9] and digit11 == digits[10]

# vergi no validation for 10 digit Turkish tax IDs
def validate_vergi_no(vergi_no: str) -> bool:
    if not vergi_no or len(vergi_no) != 10 or not vergi_no.isdigit():
        return False

    digits = list(map(int, vergi_no))
    total = 0

    for i in range(9):
        tmp = (digits[i] + (9 - i)) % 10
        total += tmp * (2 ** (9 - i))

    checksum = total % 11
    check_digit = checksum if checksum < 10 else 0

    return check_digit == digits[9]


"""
def validate_firm_identity(tc: str | None, vergi_no: str | None):
    if not tc and not vergi_no:
        raise ValueError("TC Kimlik No veya Vergi No girilmelidir.")

    if tc and not validate_tc_kimlik(tc):
        raise ValueError("Geçersiz TC Kimlik Numarası.")

    if vergi_no and not validate_vergi_no(vergi_no):
        raise ValueError("Geçersiz Vergi Numarası.")

        -----------------------------------------------------------------------

try:
    validate_firm_identity(
        firm.firma_TCkimlik,
        firm.firma_FVergiNo
    )
except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
"""