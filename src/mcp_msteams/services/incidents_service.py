from __future__ import annotations

import asyncio
import re
from typing import Any

from mcp_msteams.graph import endpoints
from mcp_msteams.graph.client import graph_get, graph_get_all
from mcp_msteams.security.permissions import SCOPES


def _is_open_issue(issue: dict[str, Any]) -> bool:
    status = str(issue.get("status", "")).strip().lower()
    if not status:
        return True
    closed_markers = {
        "servicerestored",
        "resolved",
        "closed",
        "postincidentreviewpublished",
    }
    return status not in closed_markers


def _issue_kind(issue: dict[str, Any]) -> str:
    classification = str(issue.get("classification", "")).strip().lower()
    if classification == "incident":
        return "incident"
    if classification in {"advisory", "planforchange", "messagecenter"}:
        return "advisory"
    return "other"


def _issue_kind_label(issue: dict[str, Any]) -> str:
    kind = _issue_kind(issue)
    if kind == "incident":
        return "incidente"
    if kind == "advisory":
        return "aviso"
    return "outro"


def _issue_summary(issue: dict[str, Any]) -> str:
    summary = (
        issue.get("impactDescription")
        or issue.get("description")
        or issue.get("feature")
        or issue.get("status")
        or "N/A"
    )
    text = " ".join(str(summary).split())
    if len(text) > 140:
        return text[:137] + "..."
    return text


def _clean_text(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _post_summary(post: dict[str, Any]) -> str:
    description = post.get("description") or {}
    content = description.get("content") if isinstance(description, dict) else description
    text = _clean_text(content)
    return text or "N/A"


def _extract_overview_update_text(text: str) -> str:
    normalized = _clean_text(text)
    normalized = re.sub(
        r"^title:\s.*?(?=current status:|scope of impact:|root cause:|next update by:|final status:|more info:)",
        "",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"user impact:\s.*?(?=current status:|scope of impact:|root cause:|next update by:|final status:|more info:)",
        "",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(r"current status:\s*", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"root cause:\s*", "Causa raiz: ", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"scope of impact:\s*", "Escopo: ", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"next update by:\s*", "Próxima atualização até: ", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"more info:\s*", "Mais informações: ", normalized, flags=re.IGNORECASE)
    return normalized.strip(" -")


def _extract_field(text: str, label: str) -> str:
    match = re.search(
        rf"{re.escape(label)}\s*(.*?)(?=current status:|scope of impact:|root cause:|next update by:|estimated time to resolve:|more info:|start time:|final status:|$)",
        text,
        flags=re.IGNORECASE,
    )
    return _clean_text(match.group(1)) if match else ""


def _post_message_only(post: dict[str, Any]) -> str:
    text = _post_summary(post)
    pieces: list[str] = []

    current_status = _extract_field(text, "Current status:")
    more_info = _extract_field(text, "More info:")
    eta = _extract_field(text, "Estimated time to resolve:")
    next_update = _extract_field(text, "Next update by:")

    if current_status:
        pieces.append(current_status)
    if more_info:
        pieces.append(f"Mais informações: {more_info}")
    if eta:
        pieces.append(f"Previsão de resolução: {eta}")
    elif next_update:
        pieces.append(f"Próxima atualização até: {next_update}")

    if pieces:
        return " ".join(pieces)

    return _extract_overview_update_text(text) or text


def _overview_summary_from_detail(issue: dict[str, Any]) -> str:
    posts = issue.get("posts") or []
    if not posts:
        return _issue_summary(issue)

    latest_text = _post_summary(posts[-1])
    latest_status = _extract_field(latest_text, "Current status:")
    latest_root = _extract_field(latest_text, "Root cause:")
    latest_eta = _extract_field(latest_text, "Estimated time to resolve:")
    latest_next = _extract_field(latest_text, "Next update by:")
    latest_more = _extract_field(latest_text, "More info:")

    parts: list[str] = []
    if latest_root:
        parts.append(f"Causa raiz: {latest_root}")
    if latest_status:
        parts.append(latest_status)
    if latest_more:
        parts.append(f"Mitigação/info: {latest_more}")
    if latest_eta:
        parts.append(f"ETA: {latest_eta}")
    elif latest_next:
        parts.append(f"Próxima atualização até: {latest_next}")

    if parts:
        return " ".join(parts)

    latest_compact = _extract_overview_update_text(latest_text)
    if latest_compact and latest_compact != "N/A":
        return latest_compact
    return _issue_summary(issue)


async def _get_issue_detail(issue_id: str) -> dict[str, Any]:
    return await graph_get(
        endpoints.service_announcement_issue(issue_id),
        scopes=SCOPES["service_health"],
        cache_key=f"service-issue:{issue_id}",
        ttl=60,
    )


async def check_known_teams_incidents() -> dict[str, Any]:
    issues = await graph_get_all(
        endpoints.service_announcement_issues(),
        scopes=SCOPES["service_health"],
        max_pages=5,
    )
    teams_issues = [
        issue
        for issue in issues
        if str(issue.get("service", "")).strip().lower() == "microsoft teams" and _is_open_issue(issue)
    ]
    incidents = [issue for issue in teams_issues if _issue_kind(issue) == "incident"]
    advisories = [issue for issue in teams_issues if _issue_kind(issue) == "advisory"]
    others = [issue for issue in teams_issues if _issue_kind(issue) == "other"]

    detail_targets = teams_issues[:20]
    detail_results = await asyncio.gather(
        *[_get_issue_detail(str(issue.get("id", ""))) for issue in detail_targets],
        return_exceptions=True,
    )
    detail_map: dict[str, dict[str, Any]] = {}
    for issue, detail in zip(detail_targets, detail_results):
        issue_id = str(issue.get("id", ""))
        if isinstance(detail, Exception):
            continue
        detail_map[issue_id] = detail

    lines = [f"## Integridade do Serviço do Teams ({len(teams_issues)})"]
    lines.append(
        f"- **Incidentes:** {len(incidents)} | **Avisos:** {len(advisories)} | **Outros:** {len(others)}"
    )

    if incidents:
        lines.append("")
        lines.append("### Incidentes")
        lines.append("| ID | Título | Resumo das atividades |")
        lines.append("|---|---|---|")
        for issue in incidents[:20]:
            detail = detail_map.get(str(issue.get("id", "")), issue)
            lines.append(
                f"| `{issue.get('id', '?')}` | {issue.get('title', issue.get('id', '?'))} | {_overview_summary_from_detail(detail)} |"
            )

    if advisories:
        lines.append("")
        lines.append("### Avisos")
        lines.append("| ID | Título | Resumo das atividades |")
        lines.append("|---|---|---|")
        for issue in advisories[:20]:
            detail = detail_map.get(str(issue.get("id", "")), issue)
            lines.append(
                f"| `{issue.get('id', '?')}` | {issue.get('title', issue.get('id', '?'))} | {_overview_summary_from_detail(detail)} |"
            )

    if others:
        lines.append("")
        lines.append("### Outros")
        lines.append("| ID | Título | Resumo das atividades |")
        lines.append("|---|---|---|")
        for issue in others[:20]:
            detail = detail_map.get(str(issue.get("id", "")), issue)
            lines.append(
                f"| `{issue.get('id', '?')}` | {issue.get('title', issue.get('id', '?'))} | {_overview_summary_from_detail(detail)} |"
            )

    return {
        "issues": teams_issues,
        "count": len(teams_issues),
        "incident_count": len(incidents),
        "advisory_count": len(advisories),
        "other_count": len(others),
        "markdown": "\n".join(lines),
    }


async def get_teams_incident_detail(issue_id: str) -> dict[str, Any]:
    issue = await _get_issue_detail(issue_id)

    service = str(issue.get("service", "")).strip()
    if service.lower() != "microsoft teams":
        raise ValueError(f"Issue '{issue_id}' is not from Microsoft Teams service.")

    lines = [f"## Detalhe de Saúde do Teams: {issue.get('id', issue_id)}"]
    lines.append(f"- **Título:** {issue.get('title', 'N/A')}")
    lines.append(f"- **Serviço:** {service or 'N/A'}")
    lines.append(f"- **Tipo:** {_issue_kind_label(issue)}")
    lines.append(f"- **Status:** {issue.get('status', 'N/A')}")
    lines.append(f"- **Classificação:** {issue.get('classification', 'N/A')}")
    lines.append(f"- **Recurso:** {issue.get('feature', 'N/A')}")
    lines.append(f"- **Origem:** {issue.get('origin', 'N/A')}")
    lines.append(f"- **Início:** {issue.get('startDateTime', 'N/A')}")
    lines.append(f"- **Fim:** {issue.get('endDateTime', 'N/A')}")
    lines.append(f"- **Última atualização:** {issue.get('lastModifiedDateTime', 'N/A')}")

    if issue.get("impactDescription"):
        lines.append("")
        lines.append("### Impacto")
        lines.append(str(issue["impactDescription"]))

    posts = issue.get("posts") or []
    root_cause = ""
    for post in reversed(posts):
        root_cause = _extract_field(_post_summary(post), "Root cause:")
        if root_cause:
            break

    if root_cause:
        lines.append("")
        lines.append("### Causa Raiz")
        lines.append(root_cause)

    if issue.get("description"):
        lines.append("")
        lines.append("### Resumo")
        lines.append(str(issue["description"]))

    if issue.get("remediation"):
        lines.append("")
        lines.append("### Remediação")
        lines.append(str(issue["remediation"]))

    if posts:
        lines.append("")
        lines.append("### Atualizações")
        for index, post in enumerate(posts[:10], 1):
            lines.append("")
            lines.append(f"#### Atualização {index}")
            lines.append(f"- **Data:** {post.get('createdDateTime', 'N/A')}")
            lines.append(f"- **Tipo:** {post.get('postType', 'N/A')}")
            lines.append(f"- **Mensagem:** {_post_message_only(post)}")

    return {
        "id": issue.get("id", issue_id),
        "title": issue.get("title"),
        "service": service,
        "type": _issue_kind(issue),
        "status": issue.get("status"),
        "classification": issue.get("classification"),
        "feature": issue.get("feature"),
        "origin": issue.get("origin"),
        "start": issue.get("startDateTime"),
        "end": issue.get("endDateTime"),
        "last_updated": issue.get("lastModifiedDateTime"),
        "impact_description": issue.get("impactDescription"),
        "description": issue.get("description"),
        "remediation": issue.get("remediation"),
        "posts": posts,
        "raw": issue,
        "markdown": "\n".join(lines),
    }
