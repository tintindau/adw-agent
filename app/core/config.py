from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    oracle_user: str
    oracle_password: str
    oracle_dsn: str
    wallet_location: str
    wallet_password: str = Field(
        validation_alias=AliasChoices(
            "WALLET_PASSWORD",
            "WALLET_PASSWORD_KGR_568912345",
        )
    )


settings = Settings()