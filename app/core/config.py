from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="petstore-workshop", alias="APP_NAME")
    app_env: str = Field(default="dev", alias="APP_ENV")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")

    aws_default_region: str = Field(default="us-east-2", alias="AWS_DEFAULT_REGION")
    users_table: str = Field(default="petstore-g1-users", alias="USERS_TABLE")
    sessions_table: str = Field(default="petstore-g1-sessions", alias="SESSIONS_TABLE")
    pets_table: str = Field(default="petstore-g1-pets", alias="PETS_TABLE")
    orders_table: str = Field(default="petstore-g1-orders", alias="ORDERS_TABLE")
    photos_function: str = Field(default="petstore-g1-photos", alias="PHOTOS_FUNCTION")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
