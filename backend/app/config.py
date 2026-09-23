from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://releasegate:releasegate@localhost:5435/releasegate"
    jwt_secret_key: str = "dev-only-secret-key-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    enable_graphiql: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
