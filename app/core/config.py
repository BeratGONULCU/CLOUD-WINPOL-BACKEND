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

    @property
    def MASTER_DB_URL(self) -> str:
        return (
            f"postgresql+psycopg2://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}"
            f"/{self.MASTER_DB_NAME}"
        )


settings = Settings()
