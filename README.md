# MCP Microsoft Teams

Servidor MCP de leitura para suporte e administração do Microsoft Teams. Consulte usuários, equipes, políticas, chamadas, reuniões e incidentes via Microsoft Graph API. Projetado para diagnósticos de suporte e administração. Zero operações de escrita.

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
├── .env.example               # Exemplo de configuração local
├── pyproject.toml             # Metadados do projeto e dependências
├── readme.md                  # Este arquivo
└── changelog.md               # Histórico consolidado de mudanças
```

## 🏗️ Arquitetura

O projeto segue uma arquitetura em camadas, pensada para modularidade, clareza e baixo acoplamento:

1. **Ponto de entrada (`server.py`)**  
   Inicializa o servidor `FastMCP` e registra apenas as tools expostas publicamente.

2. **Camada de interface (`tools/`)**  
   Define as ferramentas visíveis ao LLM, com docstrings operacionais, validação de parâmetros e renderização da resposta.

3. **Camada de serviço (`services/`)**  
   Orquestra a lógica de negócio. Toda agregação, transformação e composição de chamadas Graph acontece aqui.

4. **Camada de API (`graph/`)**  
   Abstração sobre a Microsoft Graph API com cliente `httpx` assíncrono, paginação, retry e cache.

5. **Segurança (`security/`)**  
   Autenticação app-only via MSAL com credenciais de aplicativo Azure AD.

6. **Resiliência**  
   Uso de `tenacity` para retry com backoff exponencial em erros transitórios como throttling e indisponibilidade temporária.

## 🛠️ Referência de Ferramentas

Todas as ferramentas são apenas de **leitura**.  
Total atual: **27 ferramentas**.

### 👤 Usuários

- **`search_user`**: resolve nome de exibição ou e-mail parcial em UPN completo. **Use esta ferramenta primeiro** para identificar o usuário antes de qualquer outra consulta.
- **`get_user_overview`**: snapshot combinado de perfil, presença e participação em equipes em uma única chamada.
- **`get_user_profile`**: perfil completo do Azure AD, incluindo cargo, departamento, escritório e telefones.
- **`get_user_presence`**: status de disponibilidade do Teams em tempo real (`Available`, `Away`, `Busy`, etc.).
- **`get_user_assigned_policies`**: lista todas as políticas do Teams atribuídas ao usuário.
- **`list_user_teams`**: lista todas as equipes do Microsoft Teams das quais o usuário é membro.

### 👥 Equipes e Canais

- **`list_team_channels`**: lista todos os canais de uma equipe, incluindo padrão, privado e compartilhado.
- **`list_team_members`**: retorna todos os membros de uma equipe específica.
- **`get_team_owners`**: lista os proprietários/administradores de uma equipe. Requer GUID da equipe.
- **`get_team_settings`**: inspeciona configurações gerais e permissões de uma equipe. Requer GUID da equipe.
- **`get_channel_settings`**: inspeciona configurações e permissões de um canal específico.
- **`check_private_shared_channels`**: identifica canais privados e compartilhados em uma equipe.
- **`detect_orphaned_team`**: detecta se uma equipe não possui membros ativos.
- **`detect_team_without_owner`**: identifica equipes sem proprietários atribuídos.

#### 📊 Visão do Tenant

- **`get_tenant_teams_stats`**: panorama consolidado do tenant, com total de equipes, breakdown por privacidade e grupos sem owners.
- **`list_all_teams`**: listagem paginada de todas as equipes com filtro por privacidade e contagem opcional de membros/owners.
- **`list_orphaned_teams`**: lista equipes sem nenhum owner atribuído, com contagem de membros para identificar grupos totalmente inativos.
- **`list_teams_without_members`**: scan tenant-wide com páginas de 100 equipes, concorrência controlada e limite configurável no servidor. O parâmetro `top` controla quantos resultados são exibidos, sem interromper o scan.
- **`list_teams_by_member_count`**: ranking das maiores equipes por quantidade de membros, usando scan tenant-wide em duas fases com concorrência controlada e limite configurável no servidor.

### 📞 Chamadas e Qualidade

- **`get_call_quality_summary`**: estatísticas agregadas de chamadas para um usuário em N dias, incluindo total, falhas e taxa de sucesso.
- **`list_failed_calls`**: lista chamadas que terminaram em falha de sistema ou rede.
- **`diagnose_call_quality`**: análise detalhada de uma chamada com telemetria por categoria (áudio, vídeo, compartilhamento de tela, rede e dispositivo). O parâmetro `upn` é obrigatório, exceto quando o escopo explícito for toda a chamada.

### 📅 Reuniões

- **`get_recent_meetings`**: lista chamadas e reuniões dos últimos N dias. Inclui `groupCall` e `peerToPeer`, com tabela contendo `Call ID`, tipo, início/fim, `meeting code`, participantes e duração.
- **`get_meeting_participants`**: lista nome e UPN de todos os participantes de uma reunião específica a partir do `call_id`.
- **`get_user_activity_report`**: relatório da Reports API com foco em atividade agregada, incluindo áudio, vídeo e screen share. Indicado para breakdown de mídia, não para resumo semanal principal.

### 🔌 Hardware e Infraestrutura

- **`check_known_teams_incidents`**: verifica apenas itens em aberto do serviço exatamente identificado como `Microsoft Teams`, separando incidentes de advisories e exibindo o `issue_id` com uma coluna de **resumo das atividades** derivada do histórico do problema.
- **`get_teams_incident_detail`**: consulta o detalhe estruturado de um problema específico do Microsoft Teams a partir do `issue_id`, incluindo impacto, causa raiz e atualizações.

## 💻 Stack Tecnológica

| Camada | Tecnologia |
|--------|------------|
| Linguagem | Python 3.11+ |
| MCP Server | FastMCP |
| HTTP Client | httpx assíncrono com pool de conexões |
| Autenticação | MSAL Python |
| Validação | Pydantic v2 |
| Resiliência | tenacity |
| Logging | structlog |
| Testes | pytest |
| Linting | Ruff |

## 🚀 Configuração

### Pré-requisitos

- Registro de aplicativo no Azure com **Permissões de Aplicativo** no Microsoft Graph
- `Client ID`
- `Client Secret`
- `Tenant ID`

### Instalação

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -e ".[dev]"
Copy-Item .env.example .env
```

### Executando o servidor

```powershell
python -m mcp_msteams.server
```

Endpoint padrão:

- `http://127.0.0.1:8000/mcp`

## 🔧 Configuração de Ambiente

Variáveis principais em `.env`:

- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `FASTMCP_TRANSPORT`
- `FASTMCP_HOST`
- `FASTMCP_PORT`
- `LOG_LEVEL`
- `LOG_FORMAT`

Controles operacionais úteis:

- `GRAPH_CALL_RECORDS_MAX_PAGES`
- `GRAPH_CALL_RECORD_DETAIL_BATCH_SIZE`
- `GRAPH_TEAM_COUNTS_CONCURRENCY`
- `GRAPH_TEAM_RANKINGS_CONCURRENCY`
- `GRAPH_TEAM_SCAN_MAX_TEAMS`

## 🔑 Permissões Graph

Permissões de aplicativo normalmente necessárias:

| Permissão | Propósito |
|-----------|-----------|
| `User.Read.All` | Perfis de usuário |
| `Directory.Read.All` | Diretório e grupos |
| `Group.Read.All` | Análises tenant-wide |
| `Team.ReadBasic.All` | Metadados de equipes |
| `TeamMember.Read.All` | Membros das equipes |
| `Channel.ReadBasic.All` | Canais |
| `ChannelSettings.Read.All` | Configurações de canal |
| `Presence.Read.All` | Presença |
| `TeamsUserConfiguration.Read.All` | Políticas efetivas do Teams por usuário |
| `OnlineMeetings.Read.All` | Reuniões online |
| `CallRecords.Read.All` | Histórico e qualidade de chamadas |
| `Reports.Read.All` | Relatórios de atividade |
| `ServiceHealth.Read.All` | Incidentes e saúde de serviço |

## 📊 Metodologia de Qualidade de Chamada

A tool `diagnose_call_quality` segue a metodologia oficial do **Microsoft Call Quality Dashboard (CQD)**.

### Classificação por stream

Cada stream de mídia é classificado individualmente como **Good**, **Poor** ou **Unclassified**. O resultado geral por categoria é expresso por taxa de streams degradados.

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
| 🖥️ Screen Sharing | Frame Rate | < 1 fps |
| 🖥️ Screen Sharing | Frame Loss (inbound não-H264S) | > 50% |

> **Nota:** ultrapassar um threshold não significa necessariamente que o usuário percebeu degradação. O media stack do Teams compensa parte dos problemas antes de afetar a experiência.

Fonte oficial:  
<https://learn.microsoft.com/en-us/microsoftteams/stream-classification-in-call-quality-dashboard>

## ⚠️ Limitações Conhecidas

- **API de Presença**: `Presence.Read.All` pode não estar disponível em todos os tenants.
- **Online Meetings em app-only**: além de `OnlineMeetings.Read.All`, exige **Application Access Policy** no Teams PowerShell.
- **Call Records**: pode haver atraso de até cerca de 15 minutos para chamadas recentes.
- **Listagem de `callRecords`**: o endpoint não suporta `$expand=participants_v2`.
- **Scans tenant-wide**:
  - `list_teams_without_members`
  - `list_teams_by_member_count`
  são mais caros e usam concorrência controlada com limite máximo de times configurável no servidor.
- **Graph API não suporta**:
  - `$filter=visibility` para grupos
  - `$filter=members/$count eq 0` para grupos

## 🩺 Troubleshooting

- **403 em `onlineMeetings`**: normalmente falta `Application Access Policy`.
- **429 no Graph**: reduza volume, janela ou concorrência; o cliente já aplica retry básico.
- **Logging de produção**: o formato padrão é JSON via `LOG_FORMAT=json`. Use `console` apenas para depuração local.
- **404 em `.well-known/oauth-authorization-server`**: esperado quando o cliente faz probe OAuth e o servidor MCP não expõe discovery.
- **Catálogo de tools desatualizado**: reinicie a sessão MCP/Portal.

## ✅ Testes

```powershell
pytest tests -v
```

Se o ambiente local não resolver o pacote `mcp_msteams`, execute com `PYTHONPATH=src`.
