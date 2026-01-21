from pydantic import BaseModel, Field
from typing import Optional
from typing_extensions import Annotated

class MikroApiUpdateSchema(BaseModel):
    api_ip: Annotated[str, Field(max_length=64)]
    api_port: int
    api_protocol: Annotated[str, Field(default="http", max_length=10)]
    api_firmakodu: Annotated[str, Field(max_length=50)]
    api_calismayili: Annotated[str, Field(max_length=4)]
    api_kullanici: Optional[Annotated[str, Field(max_length=100)]]
    api_pw_non_hash: str
    api_key: Optional[Annotated[str, Field(max_length=255)]]
    #api_firmano: Optional[Annotated[str, Field(max_length=20)]]
    sube_no: Optional[int]
