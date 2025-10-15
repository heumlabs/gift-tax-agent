from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """
    애플리케이션 설정
    
    환경 변수 로드 우선순위:
    1. Lambda 환경 변수 (프로덕션)
    2. .env 파일 (로컬 개발)
    """

    # 환경 설정
    ENVIRONMENT: str = "local"
    APP_STAGE: str = "local"  # 하위 호환성
    CORS_ALLOW_ORIGIN: str = "http://localhost:5173"

    # API 키
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None

    # 데이터베이스 (DATABASE_URL 우선, 없으면 개별 필드 조합)
    DATABASE_URL: Optional[str] = None
    DB_HOST: Optional[str] = None
    DB_NAME: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_PASS: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        """DATABASE_URL 반환 (없으면 개별 필드로 조합)"""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        
        if all([self.DB_HOST, self.DB_NAME, self.DB_USER, self.DB_PASS]):
            return f"postgresql://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:5432/{self.DB_NAME}"
        
        raise ValueError("DATABASE_URL or DB_* fields must be provided")

    @property
    def api_key(self) -> str:
        """API 키 반환 (GEMINI_API_KEY 우선, 없으면 GOOGLE_API_KEY)"""
        return self.GEMINI_API_KEY or self.GOOGLE_API_KEY or ""


settings = Settings()  # type: ignore
