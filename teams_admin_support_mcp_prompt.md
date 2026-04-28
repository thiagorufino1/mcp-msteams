# Prompt para Claude

Crie um projeto completo em **Python + FastMCP** para um **Microsoft Teams Admin Support MCP Server**, com foco **100% consultivo/read-only**, usando **Microsoft Graph API**.

O MCP será usado por suporte/admins para consultar informações parecidas com o que existe no `admin.teams.microsoft.com`, principalmente na visão de usuário, chamadas, diagnósticos, políticas, dispositivos e Teams.

## Regras obrigatórias

- Não criar nenhuma ferramenta de escrita.
- Não criar tools para enviar mensagens.
- Não criar tools para adicionar/remover usuários.
- Não criar tools para criar/alterar/excluir Teams, canais ou chats.
- Todas as tools devem ser **read-only**.
- Usar **Python**.
- Usar **FastMCP**.
- Usar **Microsoft Graph API**.
- Usar autenticação segura via **MSAL / Entra ID App Registration**.
- Separar bem arquitetura, serviços, clientes, tools, schemas e configuração.
- Aplicar boas práticas de segurança corporativa.
- Nunca logar tokens, secrets ou dados sensíveis.
- Validar entradas das tools.
- Tratar erros do Graph API com clareza.
- Retornar respostas estruturadas em JSON.
- Incluir auditoria de chamadas às tools, sem registrar conteúdo sensível.

## Objetivo do projeto

Construir um MCP Server chamado:

```text
teams-admin-support-mcp
```

Ele deve expor tools para suporte técnico consultar:

```text
- usuário
- times
- canais
- membros
- owners
- políticas
- presença
- chamadas
- call records
- qualidade de chamada
- reuniões
- dispositivos
- voice / Teams Phone
- incidentes conhecidos
```

## Lista de tools MCP

Implemente a estrutura para as seguintes tools:

```text
# Overview / Usuário
get_user_overview
get_user_profile
list_user_teams
get_user_presence

# Teams / Channels
list_team_channels
list_team_members
get_team_owners
get_team_settings
get_channel_settings
check_private_shared_channels
detect_orphaned_team
detect_team_without_owner

# Policies
get_user_assigned_policies
compare_user_policies
detect_policy_conflicts

# Mensagens - somente consulta
get_recent_channel_messages
search_channel_messages
summarize_channel_activity

# Calls / Call History
find_user_calls
get_call_record
get_call_sessions
get_call_participants
list_failed_calls
list_poor_quality_calls

# Call Analytics / Diagnóstico
get_call_quality_summary
diagnose_call_quality

# Meetings
get_recent_meetings
diagnose_meeting_issues

# Devices
get_user_devices
detect_device_problems

# Voice / Teams Phone
get_voice_configuration
validate_voice_routing
detect_voice_misconfiguration

# Known Issues / Incidents
check_known_teams_incidents

# Auditoria / Suporte
execution_history
who_did_what
support_case_summary
```

## Arquitetura esperada

Sugira e implemente uma organização de pastas como:

```text
teams-admin-support-mcp/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── logging_config.py
│   ├── security/
│   │   ├── auth.py
│   │   ├── permissions.py
│   │   └── input_validation.py
│   ├── graph/
│   │   ├── client.py
│   │   ├── endpoints.py
│   │   ├── errors.py
│   │   └── models.py
│   ├── services/
│   │   ├── users_service.py
│   │   ├── teams_service.py
│   │   ├── policies_service.py
│   │   ├── messages_service.py
│   │   ├── calls_service.py
│   │   ├── meetings_service.py
│   │   ├── devices_service.py
│   │   ├── voice_service.py
│   │   ├── incidents_service.py
│   │   └── audit_service.py
│   ├── tools/
│   │   ├── users_tools.py
│   │   ├── teams_tools.py
│   │   ├── policies_tools.py
│   │   ├── messages_tools.py
│   │   ├── calls_tools.py
│   │   ├── meetings_tools.py
│   │   ├── devices_tools.py
│   │   ├── voice_tools.py
│   │   └── audit_tools.py
│   ├── schemas/
│   │   ├── users.py
│   │   ├── teams.py
│   │   ├── calls.py
│   │   ├── diagnostics.py
│   │   └── common.py
│   └── utils/
│       ├── date_utils.py
│       ├── sanitization.py
│       └── response.py
├── tests/
├── .env.example
├── pyproject.toml
├── README.md
└── docker-compose.yml
```

## Permissões Graph sugeridas

Considerar permissões read-only como:

```text
User.Read.All
Directory.Read.All
Group.Read.All
Team.ReadBasic.All
TeamMember.Read.All
Channel.ReadBasic.All
ChannelSettings.Read.All
Presence.Read.All
CallRecords.Read.All
Reports.Read.All
ServiceHealth.Read.All
```

Não usar permissões de escrita como:

```text
Group.ReadWrite.All
TeamMember.ReadWrite.All
ChannelMessage.Send
ChatMessage.Send
```

## Segurança

Inclua:

```text
- princípio do menor privilégio
- separação de responsabilidades
- validação de entrada
- sanitização de logs
- timeout nas chamadas Graph
- retry com backoff
- tratamento de throttling 429
- controle de escopo por tool
- auditoria de execução
- mascaramento de dados sensíveis
- allowlist de domínios/tenant, se aplicável
```

## Requisitos técnicos

Use:

```text
Python 3.11+
FastMCP
httpx
pydantic
pydantic-settings
msal
tenacity
structlog ou logging padrão
pytest
ruff
mypy
```

## Entregáveis

Gere:

```text
1. Estrutura completa do projeto
2. Código base funcional
3. Exemplos de tools FastMCP
4. Cliente Graph reutilizável
5. Autenticação com MSAL client credentials
6. .env.example
7. README com setup local
8. Exemplos de chamadas
9. Estratégia de testes
10. Lista de permissões necessárias
11. Boas práticas de deploy
12. Observações sobre limitações da Call Records API
```

## Importante

Para tools complexas, implemente pelo menos o esqueleto funcional com TODOs claros, mas mantenha a arquitetura pronta para expansão.

Priorize qualidade, segurança, clareza e manutenibilidade.

