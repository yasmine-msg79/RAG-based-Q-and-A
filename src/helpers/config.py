import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str
    APP_VERSION: str
    FILE_ALLOWED_TYPES: list
    FILE_MAX_SIZE: int
    OLLAMA_HOST: str
    DB_HOST: str 
    DB_PORT: int
    DB_NAME: str 
    DB_USER: str
    DB_PASSWORD: str
    CHROMA_HOST: str
    CHROMA_PORT: int

    class Config:
        env_file = ".env"


def get_settings():
    return Settings()


def get_base_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_files_path():
    return os.path.join(get_base_dir(), "assets", "files")