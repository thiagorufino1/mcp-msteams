# Changelog

Todas as mudanças notáveis neste projeto serão documentadas aqui.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

## 2026-05-02

### Added

- **`get_meeting_participants`** — nova tool que retorna nome e UPN de todos os participantes de uma reunião via `call_id`. Usa `GET /communications/callRecords/{id}?$expand=participants_v2`.
  - Arquivos: `src/mcp_msteams/tools/meetings_tools.py`, `src/mcp_msteams/services/meetings_service.py`

- **`diagnose_call_quality` — `upn` obrigatório com filtro por participante**
  - Parâmetro `upn` agora obrigatório (sem default). Filtra telemetria apenas para segmentos onde o usuário é caller ou callee.
  - `upn="all"` disponível para análise de toda a chamada (somente quando explicitamente solicitado).
  - Valida se o `upn` participou da reunião — retorna mensagem clara "não participou desta reunião" em vez de "sem dados de telemetria" quando ausente.
  - Arquivo: `src/mcp_msteams/services/calls_service.py`, `src/mcp_msteams/tools/calls_tools.py`

- **`diagnose_call_quality` — telemetria CQD por categoria com veredito em 3 níveis**
  - Output reestruturado em 5 seções: Áudio, Vídeo, Screen Sharing, Network, System/Device.
  - Cada métrica exibe avg, max, threshold CQD e coluna "Streams Poor" (quantos streams individuais excederam o threshold).
  - Classificação por stream individual (metodologia Microsoft CQD oficial).
  - Thresholds: Áudio — Jitter >30ms, RTT >500ms, Packet Loss >10%, MOS >1.0, Concealed >7%; Vídeo — Frame Loss >50%, Frame Rate <7fps, Post-FEC PLR >15%; VBSS — Frame Rate <1fps.
  - Veredito: < 5% Poor = 🟡 Qualidade aceitável; 5-30% = 🔴 Qualidade degradada; > 30% = 🔴 Qualidade ruim.
  - Arquivo: `src/mcp_msteams/services/calls_service.py`

- **`get_recent_meetings` — incluir peerToPeer (chamadas 1:1)**
  - Antes: só groupCall. Agora: inclui peerToPeer também.
  - Nova coluna "Tipo": "Reunião" (groupCall) ou "Chamada 1:1" (peerToPeer).
  - Tabela inclui Call ID, Tipo, início/fim (BRT), Meeting Code, Participantes, Activity Type, Duração.
  - Arquivo: `src/mcp_msteams/services/meetings_service.py`

### Fixed

- **`get_recent_meetings` — filtro de participante retornava 0 resultados**
  - Root cause: path OData errado `participants_v2/any(p:p/identity/user/id eq '...')`. Campo direto é `p/id`.
  - Corrigido para `participants_v2/any(p:p/id eq '{userId}')`.
  - Arquivo: `src/mcp_msteams/services/calls_service.py`

- **`get_recent_meetings` — overflow de contexto ao pedir JSON**
  - JSON retornava dados raw completos (~300k tokens). Corrigido para summary compacto por meeting.
  - Arquivo: `src/mcp_msteams/services/meetings_service.py`

- **`get_recent_meetings` — 403 fallback não ativava corretamente**
  - Check `"403" in str(e)` substituído por `isinstance(e, AuthError) or e.status_code == 403`.
  - Fallback `_get_user_call_records` envolto em try/except com mensagem descritiva.
  - Arquivo: `src/mcp_msteams/services/meetings_service.py`

- **`diagnose_call_quality` — telemetria sempre N/A**
  - Root cause 1: travessia errada `media[]` em vez de `media[].streams[]`.
  - Root cause 2: Jitter/RTT em ISO 8601 duration (`PT0.021S`), não float. Adicionado parser `_iso_duration_to_ms()`.
  - Arquivo: `src/mcp_msteams/services/calls_service.py`

- **`diagnose_call_quality` — VBSS frame rate threshold incorreto**
  - Threshold de vídeo (<7fps) foi aplicado ao screen sharing causando falso positivo.
  - VBSS threshold correto per CQD: <1fps = Poor.
  - Arquivo: `src/mcp_msteams/services/calls_service.py`

- **`diagnose_call_quality` — contexto de erro errado quando UPN inválido**
  - Erro dizia "call record não encontrado" quando o problema era o usuário não encontrado.
  - Arquivo: `src/mcp_msteams/tools/calls_tools.py`

- **`callRecords` — `$expand=participants_v2` rejeitado no endpoint de lista**
  - Graph API não suporta `$expand` em `/communications/callRecords`. Revertido para N+1.
  - Arquivo: `src/mcp_msteams/services/calls_service.py`

### Removed

- **`list_poor_quality_calls`** — heurística errada: flagava chamadas sem campo `modalities` como poor quality. Para identificar qualidade real, usar `diagnose_call_quality` individualmente.
  - Arquivos: `src/mcp_msteams/tools/calls_tools.py`, `src/mcp_msteams/services/calls_service.py`

- **`diagnose_meeting_issues`** — redundante. Informações cobertas por `get_recent_meetings` (metadados), `get_meeting_participants` (participantes) e `diagnose_call_quality` (qualidade).
  - Arquivos: `src/mcp_msteams/tools/meetings_tools.py`, `src/mcp_msteams/services/meetings_service.py`

### Changed

- **Total de tools: 40 → 38**
- **Docstrings melhoradas para guiar comportamento do LLM**
  - `diagnose_call_quality`: `upn` obrigatório, fluxo nome → search_user → diagnose sem confirmação extra.
  - `get_recent_meetings`: instrução de sempre executar `diagnose_call_quality` individualmente ao pedir status de múltiplas chamadas.
  - `search_channel_messages`: limitação documentada (filtro local em ~50 msgs, não Microsoft Search API).
  - `get_voice_configuration` / `validate_voice_routing`: limitações de string matching documentadas.
- **`get_recent_meetings` scope** corrigido de `SCOPES["directory_read"]` para `SCOPES["reports"]`.

---

## 2026-05-01

### Added

- **5 novas tools de análise tenant-wide**
  - `get_tenant_teams_stats` — Panorama consolidado: total de equipes, breakdown por privacidade, grupos sem owners. 3 operações em paralelo.
  - `list_all_teams` — Listagem paginada com filtro por privacidade e contagem de membros/owners. Suporta `top`/`skip`.
  - `list_orphaned_teams` — Equipes sem owner via `owners/$count eq 0`. Inclui contagem de membros.
  - `list_teams_without_members` — Scan paginado completo (até 5000 equipes, concorrência 20). `top` controla exibição, não interrompe scan.
  - `list_teams_by_member_count` — Ranking por membros em 2 fases (paginação + contagem paralela concorrência 100). ~22s para 4400 equipes.
  - Arquivos: `src/mcp_msteams/tools/teams_tools.py`, `src/mcp_msteams/services/teams_service.py`, `src/mcp_msteams/schemas/teams.py`

- **`graph_get_paged`** — novo helper de paginação preservando `@odata.count`, `has_more` e `pages_fetched`.
  - Arquivo: `src/mcp_msteams/graph/client.py`

- **`_get_visibility_counts`** — scan paginado com `$top=999` para breakdown público/privado client-side (Graph API não suporta `$filter=visibility` para grupos).
  - Arquivo: `src/mcp_msteams/services/teams_service.py`

- **Novos endpoints** `groups_count()`, `group_members_count()`, `group_owners_count()`.
  - Arquivo: `src/mcp_msteams/graph/endpoints.py`

### Fixed

- **`list_teams_by_member_count` / `list_teams_without_members` — timeout em tenant com 4400+ equipes**
  - `max_connections` aumentado de 20 para 100; `max_keepalive_connections` de 10 para 50.
  - Timeout ajustado para `Timeout(connect=10, read=30, write=10, pool=5)`.
  - Phase 1 de `list_teams_by_member_count` alterada para `$top=999`, reduzindo páginas de ~45 para ~5. Tempo: ~15s.
  - Arquivos: `src/mcp_msteams/graph/client.py`, `src/mcp_msteams/services/teams_service.py`

- **`list_teams_without_members` — scan sempre parcial**
  - Condição `len(found) < top` encerrava scan cedo. Removida; `top` agora só controla exibição.
  - `max_scan` elevado de 2000 para 5000.

- **`_get_member_count` / `_get_owner_count` sempre retornando 0**
  - Endpoints `$count` retornam `text/plain`; `response.json()` falhava silenciosamente.
  - Substituído por `/groups/{id}/members?$count=true&$top=1` lendo `@odata.count`.

- **`list_orphaned_teams` / `list_teams_without_members` — filtros não suportados**
  - `NOT owners/any()` e `NOT members/any()` retornavam `Request_UnsupportedQuery`.
  - Substituídos por `owners/$count eq 0` e scan paginado com verificação de contagem.

- **`list_all_teams` — filtro por visibilidade não suportado server-side**
  - `$filter=visibility eq 'Public'` retornava erro. Substituído por filtro client-side.

- **`get_team_owners` / `get_team_settings` chamados com display name em vez de GUID**
  - Docstrings atualizadas com aviso `CRITICAL` e instrução de reusar GUID já em contexto.

- **`list_user_teams` chamado com UPN incorreto**
  - LLM usava email alternativo em vez do UPN retornado pelo `search_user`. Docstring corrigida.

### Changed

- **`list_all_teams`** — `include_counts=True` por padrão.
- **`_get_visibility_counts`** — `$top` de 100 para 999 (scan: ~18s → ~2s).
- **`list_orphaned_teams`** — contagem de membros sempre incluída no output.
- **Docstrings** melhoradas em todas as tools tenant-wide e per-team: limitações Graph API, notas de performance, reuso de GUID/UPN.
