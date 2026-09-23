from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"
    database_url: str = "postgresql+psycopg2://releasegate:releasegate@localhost:5435/releasegate"
    jwt_secret_key: str = "dev-only-secret-key-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    enable_graphiql: bool = True
    frontend_origins: str = "http://localhost:3000,http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]

    @property
    def graphiql_enabled(self) -> bool:
        return self.enable_graphiql and self.environment != "production"


settings = Settings()
