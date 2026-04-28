"""Microsoft Graph API permission scopes for read-only Teams admin support."""

# Client credentials flow uses .default scope.
# Actual permissions are defined in the Azure App Registration's API permissions blade.
GRAPH_DEFAULT_SCOPE = ["https://graph.microsoft.com/.default"]

# Scope mappings by feature domain.
# All map to GRAPH_DEFAULT_SCOPE since client credentials flow merges all permissions.
SCOPES = {
    "user_read": GRAPH_DEFAULT_SCOPE,          # User.Read.All
    "presence_read": GRAPH_DEFAULT_SCOPE,      # Presence.Read.All
    "team_read": GRAPH_DEFAULT_SCOPE,          # Team.ReadBasic.All, TeamMember.Read.All
    "directory_read": GRAPH_DEFAULT_SCOPE,     # Directory.Read.All, Group.Read.All
    "channel_read": GRAPH_DEFAULT_SCOPE,       # Channel.ReadBasic.All, ChannelSettings.Read.All
    "call_records": GRAPH_DEFAULT_SCOPE,       # CallRecords.Read.All
    "reports": GRAPH_DEFAULT_SCOPE,            # Reports.Read.All
    "service_health": GRAPH_DEFAULT_SCOPE,     # ServiceHealth.Read.All
}
