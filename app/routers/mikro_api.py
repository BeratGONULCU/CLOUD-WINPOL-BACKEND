import json
import requests
from fastapi import HTTPException

from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.tenant.tenant import MikroApiSettings
from app.utils.mikro_main_file import build_mikro_request


def get_mikro_settings(db: Session, firma_guid):
    settings = (
        db.query(MikroApiSettings)
        .filter(
            MikroApiSettings.firma_Guid == firma_guid,
            MikroApiSettings.api_kilitli == False
        )
        .first()
    )

    if not settings:
        raise HTTPException(
            status_code=404,
            detail="Firma için Mikro API ayarları bulunamadı"
        )

    return settings


def call_mikro_api(
    *,
    db: Session,
    firma_guid,
    endpoint: str,
    body: Optional[Dict[str ,Any]] = None
    ):
    settings = get_mikro_settings(db, firma_guid)
    base_url, mikro_auth = build_mikro_request(settings)

    url = f"{base_url}/{endpoint}"

    payload = {
        "Mikro": mikro_auth
    }

    if body:
        payload.update(body)

    try:
        response = requests.post(
            url,
            data=json.dumps(payload),
            headers={
                "Content-Type": "application/json; charset=utf-8"
            },
            timeout=30
        )
        response.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Mikro API çağrısı başarısız: {str(e)}"
        )

    return response.json()
