# MCP Microsoft Teams

Servidor MCP de leitura para suporte e administração do Microsoft Teams. Consulte usuários, equipes, políticas, chamadas e muito mais via Microsoft Graph API. Projetado para diagnósticos de suporte e administração. Zero operações de escrita.

## 📂 Estrutura de Pastas

```text
mcp-msteams/
├── src/
│   └── mcp_msteams/           # Pacote principal
│       ├── graph/             # Abstração da API Microsoft Graph (cliente, endpoints, cache)
│       ├── tools/             # Definições de ferramentas MCP categorizadas por domínio
│       ├── services/          # Camada de lógica de negócio entre ferramentas e API
│       ├── schemas/           # Modelos Pydantic para validação de dados
│       ├── security/          # Gestão de autenticação e tokens (MSAL)
│       ├── utils/             # Funções utilitárias comuns
│       ├── server.py          # Ponto de entrada e registro do servidor MCP
│       ├── config.py          # Gestão de configuração e ambiente
│       └── logging_config.py  # Configuração de logging estruturado (structlog)
├── tests/                     # Testes unitários e de integração
├── docs/                      # Documentação detalhada e guias
├── pyproject.toml             # Metadados do projeto e dependências
└── README.md                  # Este arquivo
```

## 🏗️ Arquitetura

O projeto segue uma **arquitetura em camadas** projetada para modularidade, resiliência e clareza:

1. **Ponto de Entrada (`server.py`)**: Inicializa o servidor `FastMCP` e registra as ferramentas.
2. **Camada de Interface (`tools/`)**: Define as ferramentas expostas ao LLM, lidando com validação de entrada e formatação da resposta.
3. **Camada de Serviço (`services/`)**: Orquestra a lógica de negócio. Se uma tarefa exige múltiplas chamadas de API ou transformação de dados, ela acontece aqui.
4. **Camada de API (`graph/`)**: Abstração sobre a Microsoft Graph API usando cliente `httpx` assíncrono com pool de conexões e cache.
5. **Resiliência**: Biblioteca `tenacity` para retentativas com backoff exponencial em erros transitórios (throttling, serviço indisponível).

## 🛠️ Referência de Ferramentas

Todas as ferramentas são apenas de **leitura**. Total: 38 ferramentas.

### 👤 Usuários

- **`search_user`**: Resolve nome de exibição ou e-mail parcial em UPN completo. **Use esta ferramenta primeiro** para identificar o usuário antes de qualquer outra consulta.
- **`get_user_overview`**: Snapshot combinado de perfil, presença e participação em equipes em uma única chamada.
- **`get_user_profile`**: Perfil completo do Azure AD (cargo, departamento, escritório, telefone).
- **`get_user_presence`**: Status de disponibilidade do Teams em tempo real (Available, Away, Busy, etc.).
- **`get_user_assigned_policies`**: Lista todas as políticas do Teams atribuídas ao usuário.
- **`list_user_teams`**: Lista todas as equipes do Microsoft Teams das quais o usuário é membro.

### 👥 Equipes e Canais

- **`list_team_channels`**: Lista todos os canais (padrão, privado, compartilhado) de uma equipe.
- **`list_team_members`**: Retorna todos os membros de uma equipe específica.
- **`get_team_owners`**: Lista os proprietários/administradores de uma equipe. Requer GUID da equipe.
- **`get_team_settings`**: Inspeciona configurações gerais e permissões de uma equipe. Requer GUID da equipe.
- **`get_channel_settings`**: Inspeciona configurações e permissões de um canal específico.
- **`check_private_shared_channels`**: Identifica canais privados e compartilhados em uma equipe.
- **`detect_orphaned_team`**: Detecta se uma equipe não possui membros ativos.
- **`detect_team_without_owner`**: Identifica equipes sem proprietários atribuídos.

#### 📊 Visão Tenant (Análise Global)

- **`get_tenant_teams_stats`**: Panorama consolidado do tenant: total de equipes, breakdown por privacidade (público/privado via scan paginado), grupos sem owners. Use como ponto de partida para análises globais.
- **`list_all_teams`**: Listagem paginada de todas as equipes com filtro por privacidade e contagem de membros/owners por equipe. Suporta `top`/`skip` para navegar entre páginas.
- **`list_orphaned_teams`**: Lista equipes sem nenhum owner atribuído, com contagem de membros por grupo para identificar grupos completamente inativos.
- **`list_teams_without_members`**: Scan paginado completo (até 5000 equipes, 100 por página, concorrência 20). O parâmetro `top` controla quantos resultados são exibidos sem interromper o scan. O total retornado reflete todas as equipes vazias encontradas.
- **`list_teams_by_member_count`**: Ranking das maiores equipes por membros via scan paginado completo em 2 fases (paginação + contagem paralela com concorrência 100). Tempo estimado: ~22s para 4000+ equipes.

### 📞 Chamadas e Qualidade

- **`get_call_quality_summary`**: Estatísticas agregadas de chamadas (total, falhas, taxa de sucesso) para um usuário em N dias.
- **`list_failed_calls`**: Lista chamadas que terminaram em falha de sistema ou rede.
- **`diagnose_call_quality`**: Análise detalhada de uma chamada com telemetria completa por categoria (áudio, vídeo, screen sharing, rede, dispositivo). `upn` obrigatório — filtra telemetria para o participante específico ou `"all"` para toda a chamada. Valida se o usuário participou da reunião. Classifica cada stream individualmente seguindo a metodologia Microsoft CQD com veredito em 3 níveis (Boa qualidade / Qualidade aceitável / Qualidade degradada/ruim). Ver seção abaixo.

### 📅 Reuniões

- **`get_recent_meetings`**: Lista chamadas e reuniões dos últimos N dias (padrão: 7). Inclui groupCall (reuniões) e peerToPeer (chamadas 1:1). Tabela com Call ID, Tipo, início/fim (BRT), meeting code, participantes, activity type e duração. Fallback automático para `callRecords` quando `onlineMeetings` exige Application Access Policy.
- **`get_meeting_participants`**: Lista nome e UPN de todos os participantes de uma reunião específica pelo `call_id`.

### 💬 Mensagens e Atividade

- **`get_recent_channel_messages`**: Recupera as mensagens mais recentes de um canal específico.
- **`search_channel_messages`**: Pesquisa palavras-chave em conversas de canal.
- **`summarize_channel_activity`**: Resume as discussões de um canal em um período de dias.

### 🛡️ Políticas e Segurança

- **`compare_user_policies`**: Compara atribuições de políticas do Teams entre dois usuários lado a lado.
- **`detect_policy_conflicts`**: Identifica combinações de políticas potencialmente conflitantes para um usuário.

### 📊 Auditoria e Suporte

- **`execution_history`**: Exibe log de todas as ferramentas chamadas durante a sessão atual com timestamps e status.
- **`who_did_what`**: Filtra o log de atividade por usuário ou fragmento de domínio.
- **`support_case_summary`**: Gera relatório resumido da investigação para abertura ou documentação de chamado.

### 🔌 Hardware e Infraestrutura

- **`get_user_devices`**: Lista dispositivos certificados pelo Teams registrados para um usuário.
- **`detect_device_problems`**: Detecta problemas de conformidade ou sincronização nos dispositivos do usuário.
- **`check_known_teams_incidents`**: Verifica a integridade do serviço Microsoft 365 para incidentes ativos.
- **`get_voice_configuration`**: Retorna a configuração de Voz e Teams Phone de um usuário.
- **`validate_voice_routing`**: Valida se as políticas de roteamento de voz estão aplicadas corretamente.
- **`detect_voice_misconfiguration`**: Detecta erros comuns de configuração no Teams Phone.

## 💻 Stack Tecnológica

| Camada | Tecnologia |
|--------|------------|
| Linguagem | Python 3.11+ |
| MCP Server | FastMCP 2.0+ |
| HTTP Client | httpx (assíncrono com pool de conexões) |
| Autenticação | MSAL Python (credenciais de aplicativo Azure AD) |
| Validação | Pydantic v2 |
| Resiliência | Tenacity (retry com backoff exponencial) |
| Logging | structlog (logging estruturado) |
| Linting | Ruff |
| Testes | Pytest |

## 🚀 Configuração

### Pré-requisitos

- Registro de Aplicativo no Azure com **Permissões de Aplicativo** (Fluxo de Credenciais do Cliente).
- Client ID, Client Secret e Tenant ID.

### Instalação

```bash
python -m venv .venv
# Windows
. .\.venv\Scripts\Activate.ps1
# macOS/Linux
# source .venv/bin/activate

pip install -e ".[dev]"
copy .env.example .env
# Edite o arquivo .env com suas credenciais do Azure
```

### Executando o Servidor

```bash
# Execução local padrão (HTTP)
python -m mcp_msteams.server

# Claude Desktop (stdio)
# Defina FASTMCP_TRANSPORT=stdio em seu ambiente ou configuração
```

## 🔑 Permissões

Permissões de Aplicativo do Microsoft Graph necessárias:

| Permissão | Propósito |
|-----------|-----------|
| `User.Read.All` | Perfis de usuário |
| `Directory.Read.All` | Grupos e políticas |
| `Team.ReadBasic.All` | Participação em equipes |
| `TeamMember.Read.All` | Membros da equipe |
| `Group.Read.All` | Listagem e filtro de grupos (tenant-wide analytics) |
| `Channel.ReadBasic.All` | Canais |
| `ChannelSettings.Read.All` | Configurações de canal |
| `ChannelMessage.Read.All` | Mensagens de canal |
| `Presence.Read.All` | Status de presença |
| `TeamsUserConfiguration.Read.All` | Políticas efetivas do Teams por usuário |
| `OnlineMeetings.Read.All` | Reuniões online por usuário |
| `CallRecords.Read.All` | Histórico e qualidade de chamadas |
| `Reports.Read.All` | Relatórios de uso |
| `ServiceHealth.Read.All` | Status de incidente/saúde |

---

## 📊 Metodologia de Qualidade de Chamada (CQD)

A ferramenta `diagnose_call_quality` segue a metodologia oficial do **Microsoft Call Quality Dashboard (CQD)**.

### Classificação por Stream

Cada stream de mídia é classificado individualmente como **Good**, **Poor** ou **Unclassified** (streams com menos de 500 pacotes). O resultado geral é expresso como **Poor Stream Rate** por categoria.

| Categoria | Métrica | Threshold Poor |
|-----------|---------|----------------|
| 🔊 Áudio | Jitter médio | > 30 ms |
| 🔊 Áudio | RTT médio | > 500 ms |
| 🔊 Áudio | Packet Loss médio | > 10% |
| 🔊 Áudio | MOS Degradation | > 1.0 |
| 🔊 Áudio | Concealed Samples | > 7% |
| 📹 Vídeo | Frame Loss | > 50% |
| 📹 Vídeo | Frame Rate | < 7 fps |
| 📹 Vídeo | Post-FEC Packet Loss | > 15% |
| 🖥️ VBSS (Screen Sharing) | Frame Rate | < 1 fps |
| 🖥️ VBSS (Screen Sharing) | Frame Loss (inbound não-H264S) | > 50% |

> **Nota Microsoft:** ultrapassar um threshold não significa que o usuário percebeu degradação. O media stack do Teams compensa problemas de rede antes de afetar a experiência.

**Fonte:** [Stream classification in Call Quality Dashboard - Microsoft Learn](https://learn.microsoft.com/en-us/microsoftteams/stream-classification-in-call-quality-dashboard)

---

## ⚠️ Limitações Conhecidas

- **API de Call Records**: Latência de até 15 minutos para chamadas recentes. Telemetria de streams pode retornar `null` enquanto o registro ainda é processado pelo backend da Microsoft.
- **API de Presença**: Requer `Presence.Read.All`, não disponível em todos os tenants.
- **Online Meetings (app-only)**: Além de `OnlineMeetings.Read.All`, exige **Application Access Policy** no Teams PowerShell (`New-CsApplicationAccessPolicy` e `Grant-CsApplicationAccessPolicy`). Sem a policy, `get_recent_meetings` usa fallback automático via `callRecords`.
- **`get_recent_meetings` fallback**: O endpoint `/communications/callRecords` não suporta `$filter` em `participants_v2` nem `$expand` na listagem. O filtro correto usa `participants_v2/any(p:p/id eq '{userId}')` (campo `p/id`, não `p/identity/user/id`).
- **Telemetria CQD via API**: Campos de qualidade ficam em `sessions > segments > media[] > streams[]`. Jitter e RTT são retornados como ISO 8601 duration (`PT0.021S`), não como float.
- Algumas ferramentas estão marcadas como `[STUB]` e retornam status de "não implementado".
- **Listagem tenant-wide**: A Graph API não suporta `$filter=members/$count eq 0` nem ordenação por quantidade de membros. `list_teams_by_member_count` usa scan em 2 fases (tempo estimado ~22s para 4000+ equipes). `list_teams_without_members` usa scan completo com concorrência 20 (tempo estimado 40-80s).
- **Visibilidade de grupos**: A Graph API não suporta `$filter=visibility` para grupos. O breakdown público/privado é obtido via scan paginado client-side em `get_tenant_teams_stats`.
