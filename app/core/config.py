from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    MASTER_DB_NAME: str

    BASE_URL: str
    ENV: str = "local"

    class Config:
        env_file = ".env"

settings = Settings()
