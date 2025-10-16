from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from urllib.parse import quote_plus, urlparse, urlunparse


class Settings(BaseSettings):
    """
    애플리케이션 설정

    환경 변수 로드 우선순위:
    1. Lambda 환경 변수 (프로덕션)
    2. .env 파일 (로컬 개발)
    """

    # 환경 설정
    ENVIRONMENT: str = "local"
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
        """DATABASE_URL 반환 (없으면 개별 필드로 조합)
        
        비밀번호와 사용자명의 특수문자를 자동으로 URL 인코딩합니다.
        """
        if self.DATABASE_URL:
            return self._encode_database_url(self.DATABASE_URL)

        if all([self.DB_HOST, self.DB_NAME, self.DB_USER, self.DB_PASS]):
            # 개별 필드로 조합할 때도 URL 인코딩 적용
            encoded_user = quote_plus(self.DB_USER)
            encoded_pass = quote_plus(self.DB_PASS)
            return f"postgresql://{encoded_user}:{encoded_pass}@{self.DB_HOST}:5432/{self.DB_NAME}"

        raise ValueError("DATABASE_URL or DB_* fields must be provided")
    
    def _encode_database_url(self, url: str) -> str:
        """DATABASE_URL의 사용자명과 비밀번호를 URL 인코딩"""
        try:
            parsed = urlparse(url)
            
            # 이미 올바르게 인코딩되어 있는지 확인
            if parsed.username and parsed.password:
                # 사용자명과 비밀번호를 URL 인코딩
                encoded_user = quote_plus(parsed.username)
                encoded_pass = quote_plus(parsed.password)
                
                # 새로운 netloc 구성
                netloc = f"{encoded_user}:{encoded_pass}@{parsed.hostname}"
                if parsed.port:
                    netloc += f":{parsed.port}"
                
                # URL 재구성
                return urlunparse((
                    parsed.scheme,
                    netloc,
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment
                ))
            
            return url
        except Exception:
            # 파싱 실패 시 원본 URL 반환
            return url

    @property
    def api_key(self) -> str:
        """API 키 반환 (GEMINI_API_KEY 우선, 없으면 GOOGLE_API_KEY)"""
        return self.GEMINI_API_KEY or self.GOOGLE_API_KEY or ""


settings = Settings()  # type: ignore
