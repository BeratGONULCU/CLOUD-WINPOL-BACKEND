from app.models.tenant.tenant import MikroApiSettings


def build_mikro_request(settings: MikroApiSettings):
    base_url = (
        f"http://{settings.api_ip}:{settings.api_port}"
        "/Api/APIMethods"
    )

    mikro_auth = {
        "FirmaKodu": settings.api_firmakodu,
        "CalismaYili": settings.api_calismayili,
        "KullaniciKodu": settings.api_kullanici,
        "Sifre": settings.api_pw,
        "ApiKey": settings.api_key
    }

    return base_url, mikro_auth


"""
MIKRO_BASE_URL = "http://85.95.242.148:8094/Api/APIMethods"

MIKRO_AUTH = {
    "FirmaKodu": "Winpol",
    "CalismaYili": "2026",
    "KullaniciKodu": "SRV",
    "Sifre": "HASHED_PASSWORD",
    "ApiKey": "API_KEY"
}
"""



