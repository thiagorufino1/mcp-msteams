from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    azure_tenant_id: str
    azure_client_id: str
    azure_client_secret: str

    fastmcp_transport: str = "http"
    fastmcp_host: str = "127.0.0.1"
    fastmcp_port: int = 8000
    log_level: str = "INFO"

    audit_buffer_size: int = 500
    cache_ttl_presence: int = 30
    cache_ttl_user: int = 300
    cache_ttl_teams: int = 600
    cache_ttl_policies: int = 900
    cache_ttl_calls: int = 120
    cache_ttl_incidents: int = 300
    cache_ttl_devices: int = 300


settings = Settings()
