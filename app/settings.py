from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_key: str
    files_root: str = "fake_files"
    qdrant_path: str = "qdrant_data"
    qdrant_url: str = ""  # set to use a Qdrant server instead of local mode
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_api_version: str
    embed_model: str = "text-embedding-3-small"
    classifier_model: str = "gpt-5-mini"
    azure_openai_deployment: str = "gpt-5.2"  # chat model
    ocr_url: str
    sql_server: str
    sql_port: int = 1433
    sql_database: str
    sql_user: str
    sql_password: str
    attachments_base_url: str
    attachments_upload_path: str
    attachments_download_path: str
    attachments_token: str
    data_dir: str = "data"  # deliverables and custom templates
    cors_origins: str = "*"  # comma-separated list of frontend origins


settings = Settings()
