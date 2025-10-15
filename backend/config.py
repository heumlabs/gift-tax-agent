from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_STAGE: str = "local"

    DB_HOST: str
    DB_NAME: str
    DB_USER: str
    DB_PASS: str

    GOOGLE_API_KEY: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def db_string(self):
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}/{self.DB_NAME}"



settings = Settings() # type: ignore