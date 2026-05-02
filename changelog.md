# Changelog

Todas as mudanças relevantes deste projeto são documentadas aqui.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

## 2026-05-02

### Added

- **`get_meeting_participants`**  
  Nova tool para listar nome e UPN dos participantes de uma reunião via `call_id`.

- **`get_teams_incident_detail`**  
  Nova tool para consultar o detalhe estruturado de um item específico de Service Health do Microsoft Teams por `issue_id`.

- **`get_user_activity_report`**  
  Nova tool baseada na Reports API para breakdown de atividade, com foco em áudio, vídeo e screen share.

- **Teste de `Retry-After` em formato HTTP-date**  
  Cobertura adicionada para parsing de `Retry-After` em data HTTP no cliente Graph.

### Fixed

- **`get_recent_meetings` passou a incluir `groupCall` e `peerToPeer`**  
  O output agora mostra tipo de interação, duração total e resumo mais aderente ao portal.

- **`get_recent_meetings` corrigido para fallback adequado em `403` de `onlineMeetings`**  
  Quando `Application Access Policy` está ausente, a tool cai corretamente para `callRecords`.

- **Filtro de participante em `callRecords` corrigido**  
  Ajustado para `participants_v2/any(p:p/id eq '{userId}')`.

- **`diagnose_call_quality` corrigida para leitura de telemetria em `streams[]`**  
  Ajuste de parsing das durações ISO 8601 e correção do threshold de VBSS para `<1fps`.

- **`check_known_teams_incidents` refinada**  
  Agora filtra apenas itens em aberto do serviço exatamente `Microsoft Teams`, separa incidentes de advisories e exibe `issue_id`.

- **Tabela de incidentes com resumo derivado do histórico**  
  A coluna `Resumo das atividades` passou a ser construída a partir dos updates do item, e não apenas do título.

- **`get_teams_incident_detail` refinada para pt-BR e melhor leitura operacional**  
  Output com `Impacto`, `Causa Raiz` e `Atualizações`, evitando repetição desnecessária de boilerplate.

- **Cliente Graph com parsing robusto de `Retry-After`**  
  Suporte a valor inteiro e HTTP-date.

- **Tools tenant-wide com limites e concorrência configuráveis**  
  Redução do risco de throttling em scans amplos de tenant.

- **Logging com semântica corrigida**  
  A docstring do decorator `audited` foi ajustada para refletir que hoje ele faz execution logging, não trilha de auditoria persistente.

### Removed

- **Tools de mensagens, políticas e auditoria removidas da superfície pública**
  - `get_recent_channel_messages`
  - `search_channel_messages`
  - `summarize_channel_activity`
  - `compare_user_policies`
  - `detect_policy_conflicts`
  - `execution_history`
  - `who_did_what`
  - `support_case_summary`

- **`list_poor_quality_calls`**  
  Removida por heurística incorreta para classificação de qualidade.

- **`diagnose_meeting_issues`**  
  Removida por redundância com `get_recent_meetings`, `get_meeting_participants` e `diagnose_call_quality`.

- **Módulos órfãos de device/voice removidos do código**
  - `get_user_devices`
  - `detect_device_problems`
  - `get_voice_configuration`
  - `validate_voice_routing`
  - `detect_voice_misconfiguration`

### Changed

- **Escopo público de Hardware e Infraestrutura reduzido**
  - `check_known_teams_incidents`
  - `get_teams_incident_detail`

- **`get_user_activity_report` ficou restrita ao uso de breakdown da Reports API**  
  Não deve ser usada como resumo semanal principal de chamadas/reuniões.

- **`get_recent_meetings` virou a referência principal para resumo semanal**  
  Especialmente para cenários em que o objetivo é aderência ao comportamento do portal.

- **`list_teams_without_members` e `list_teams_by_member_count` passaram a respeitar limites configuráveis**
  - `GRAPH_TEAM_COUNTS_CONCURRENCY`
  - `GRAPH_TEAM_RANKINGS_CONCURRENCY`
  - `GRAPH_TEAM_SCAN_MAX_TEAMS`

- **`get_call_quality_summary` e `list_failed_calls` passaram a respeitar limites configuráveis**
  - `GRAPH_CALL_RECORDS_MAX_PAGES`
  - `GRAPH_CALL_RECORD_DETAIL_BATCH_SIZE`

- **Total atual de tools expostas: `27`**

---

## 2026-05-01

### Added

- **Novas tools tenant-wide**
  - `get_tenant_teams_stats`
  - `list_all_teams`
  - `list_orphaned_teams`
  - `list_teams_without_members`
  - `list_teams_by_member_count`

- **`graph_get_paged`**  
  Novo helper de paginação preservando `@odata.count`, `has_more` e `pages_fetched`.

- **Endpoints auxiliares de contagem para grupos e owners**

### Fixed

- **Timeouts e paginação das tools tenant-wide ajustados**

- **Contagem usando `@odata.count` corrigida**

- **Filtros não suportados em grupos tratados corretamente**

### Changed

- **`list_all_teams` com `include_counts=True` por padrão**

- **Docstrings reforçadas para uso correto de GUIDs, UPNs e limitações da Graph API**
