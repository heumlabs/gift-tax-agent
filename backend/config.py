from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    애플리케이션 설정

    환경 변수 로드 우선순위:
    1. Lambda 환경 변수 (프로덕션)
    2. .env 파일 (로컬 개발)
    """

    ENVIRONMENT: str = "local"
    DATABASE_URL: str
    GEMINI_API_KEY: str
    CORS_ALLOW_ORIGIN: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()  # type: ignore
