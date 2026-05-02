from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    azure_tenant_id: str
    azure_client_id: str
    azure_client_secret: SecretStr

    fastmcp_transport: str = "http"
    fastmcp_host: str = "127.0.0.1"
    fastmcp_port: int = 8000
    log_level: str = "INFO"
    log_format: str = "json"

    audit_buffer_size: int = 500
    cache_ttl_presence: int = 30
    cache_ttl_user: int = 300
    cache_ttl_teams: int = 600
    cache_ttl_policies: int = 900
    cache_ttl_calls: int = 120
    cache_ttl_incidents: int = 300
    cache_ttl_devices: int = 300

    graph_call_records_max_pages: int = 12
    graph_call_record_detail_batch_size: int = 20
    graph_team_counts_concurrency: int = 20
    graph_team_rankings_concurrency: int = 40
    graph_team_scan_max_teams: int = 2000


settings = Settings()
