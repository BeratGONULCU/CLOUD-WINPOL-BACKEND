from dataclasses import dataclass
from uuid import UUID
from typing import Optional

@dataclass
class SessionContext:
    user_id: UUID
    domain: str              # "master" | "tenant"
    tenant_id: Optional[int]
    role_id: int
    jti: str
