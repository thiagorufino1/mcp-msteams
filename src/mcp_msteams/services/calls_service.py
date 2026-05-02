from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from mcp_msteams.config import settings
from mcp_msteams.graph import endpoints
from mcp_msteams.graph.client import graph_get, graph_get_all
from mcp_msteams.security.permissions import SCOPES
from mcp_msteams.services.users_service import get_user_profile
from mcp_msteams.utils.date_utils import graph_date_filter, utc_now

_DATA_LAG_WARNING = "Note: Due to Microsoft Graph API limitations, only the most recent global tenant calls are scanned. Older calls for this user may not appear unless Call Record Webhooks are configured."
_CALL_RESULT_SUCCESS = "success"
_CALL_RECORDS_MAX_PAGES = settings.graph_call_records_max_pages
_CALL_RECORD_DETAILS_BATCH_SIZE = settings.graph_call_record_detail_batch_size
_CALL_RECORD_DETAILS_CONCURRENCY = min(settings.graph_call_record_detail_batch_size, 10)

def _is_failed(result: str) -> bool:
    return result.lower() not in (_CALL_RESULT_SUCCESS, "")


def _has_participant(record: dict[str, Any], user_id: str, upn: str) -> bool:
    participants = record.get("participants_v2", [])
    normalized_upn = upn.lower()
    for participant in participants:
        if not isinstance(participant, dict):
            continue
        if str(participant.get("id", "")).lower() == user_id.lower():
            return True
        identity = participant.get("identity") or {}
        user = identity.get("user") or {}
        if str(user.get("id", "")).lower() == user_id.lower():
            return True
        if str(user.get("userPrincipalName", "")).lower() == normalized_upn:
            return True
    return False


def _call_records_date_filter(days: int) -> str:
    if days < 30:
        return graph_date_filter("startDateTime", days)

    # Stay slightly inside Graph's 30-day retention window to avoid boundary rejections.
    since = utc_now() - timedelta(days=30) + timedelta(minutes=5)
    return f"startDateTime ge {since.strftime('%Y-%m-%dT%H:%M:%SZ')}"


async def _get_call_record_with_participants(call_id: str) -> dict[str, Any]:
    return await graph_get(
        f"{endpoints.call_record(call_id)}?$expand=participants_v2",
        scopes=SCOPES["call_records"],
        cache_key=f"callrecord:participants:{call_id}",
        ttl=settings.cache_ttl_calls,
    )


async def _get_user_call_records(upn: str, days: int) -> list[dict[str, Any]]:
    profile = await get_user_profile(upn)
    user_id = profile.get("id")
    if not user_id:
        return []

    date_filter = _call_records_date_filter(days)
    # Correct path is p/id (top-level participant id), not p/identity/user/id.
    participant_filter = f"participants_v2/any(p:p/id eq '{user_id}')"

    data = await graph_get_all(
        "/communications/callRecords",
        scopes=SCOPES["call_records"],
        params={"$filter": f"{participant_filter} and {date_filter}"},
        max_pages=_CALL_RECORDS_MAX_PAGES,
        extra_headers={"Prefer": "odata.maxpagesize=60"},
    )
    candidate_ids = [record.get("id") for record in data if record.get("id")]
    if not candidate_ids:
        return []

    sem = asyncio.Semaphore(_CALL_RECORD_DETAILS_CONCURRENCY)

    async def _safe_fetch(call_id: str) -> dict[str, Any] | None:
        async with sem:
            try:
                return await _get_call_record_with_participants(call_id)
            except Exception:
                return None

    matched_records = []
    for i in range(0, len(candidate_ids), _CALL_RECORD_DETAILS_BATCH_SIZE):
        chunk = candidate_ids[i:i + _CALL_RECORD_DETAILS_BATCH_SIZE]
        detailed_records = await asyncio.gather(
            *(_safe_fetch(call_id) for call_id in chunk),
        )
        matched_records.extend([
            record for record in detailed_records
            if isinstance(record, dict) and _has_participant(record, user_id, upn)
        ])

    return sorted(matched_records, key=lambda record: record.get("startDateTime", ""), reverse=True)


async def get_call_quality_summary(upn: str, days: int = 7) -> dict[str, Any]:
    records = await _get_user_call_records(upn, days)
    total = len(records)
    failed = [r for r in records if _is_failed(r.get("result", ""))]
    lines = [f"## Call Quality Summary: {upn} (last {days} days)", _DATA_LAG_WARNING]
    lines.append(f"- **Total calls:** {total}")
    lines.append(f"- **Failed calls:** {len(failed)}")
    if total > 0:
        lines.append(f"- **Success rate:** {(total - len(failed)) / total * 100:.1f}%")
    return {
        "upn": upn,
        "days": days,
        "total_calls": total,
        "failed_calls": len(failed),
        "records": records,
        "data_lag_warning": _DATA_LAG_WARNING,
        "markdown": "\n".join(lines),
    }


import re as _re

def _iso_duration_to_ms(value: Any) -> float | None:
    """Convert ISO 8601 duration (PT0.021S) to milliseconds."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) * 1000
    m = _re.match(r"PT(\d+(?:\.\d+)?)S", str(value))
    return round(float(m.group(1)) * 1000, 3) if m else None


def _fmt_ms(value: float | None) -> str:
    return f"{round(value, 1)} ms" if value is not None else "N/A"


def _fmt_pct(value: float | None) -> str:
    return f"{round(value * 100, 2)}%" if value is not None else "N/A"


def _fmt_fps(value: float | None) -> str:
    return f"{round(value, 1)} fps" if value is not None else "N/A"


# Microsoft CQD official thresholds — stream is Poor if value exceeds threshold
# Source: learn.microsoft.com/en-us/microsoftteams/stream-classification-in-call-quality-dashboard
_CQD_AUDIO_POOR = {
    "jitter_ms":     30,     # avg jitter > 30ms → Poor
    "rtt_ms":        500,    # avg RTT > 500ms → Poor
    "packet_loss":   0.10,   # avg packet loss rate > 10% → Poor
}
_CQD_VIDEO_POOR = {
    "frame_loss_pct": 50.0,  # avg frame loss > 50% → Poor (step 1)
    "frame_rate_fps": 7,     # avg frame rate < 7fps → Poor (step 2)
    "post_fec_plr":   0.15,  # post-FEC packet loss > 15% → Poor (step 3)
}
_CQD_VBSS_POOR = {
    "frame_loss_pct": 50.0,  # frame loss > 50% (inbound non-H264S) → Poor
    "frame_rate_fps": 1,     # avg frame rate < 1fps → Poor (VBSS threshold, not 7fps)
}
_MIN_PACKET_UTIL = 500  # streams with < 500 packets are Unclassified


def _classify_audio_stream(s: dict) -> tuple[str, str]:
    """Returns (status, reason). status: good/poor/unclassified."""
    if (s.get("packetUtilization") or 0) <= _MIN_PACKET_UTIL:
        return "unclassified", ""
    jitter = _iso_duration_to_ms(s.get("averageJitter"))
    rtt = _iso_duration_to_ms(s.get("averageRoundTripTime"))
    loss = s.get("averagePacketLossRate")
    reasons = []
    if jitter is not None and jitter > _CQD_AUDIO_POOR["jitter_ms"]:
        reasons.append(f"Jitter {_fmt_ms(jitter)}")
    if rtt is not None and rtt > _CQD_AUDIO_POOR["rtt_ms"]:
        reasons.append(f"RTT {_fmt_ms(rtt)}")
    if loss is not None and loss > _CQD_AUDIO_POOR["packet_loss"]:
        reasons.append(f"Packet Loss {_fmt_pct(loss)}")
    if reasons:
        return "poor", ", ".join(reasons)
    return "good", ""


def _classify_video_stream(s: dict) -> tuple[str, str]:
    """Returns (status, reason). Cascade per CQD."""
    if (s.get("packetUtilization") or 0) <= _MIN_PACKET_UTIL:
        return "unclassified", ""
    frame_loss = s.get("averageVideoFrameLossPercentage")
    if frame_loss is not None:
        if frame_loss > _CQD_VIDEO_POOR["frame_loss_pct"]:
            return "poor", f"Frame Loss {_fmt_pct(frame_loss / 100)}"
        return "good", ""
    frame_rate = s.get("averageVideoFrameRate")
    if frame_rate is not None:
        if frame_rate < _CQD_VIDEO_POOR["frame_rate_fps"]:
            return "poor", f"Frame Rate {_fmt_fps(frame_rate)}"
        return "good", ""
    fec_plr = s.get("postForwardErrorCorrectionPacketLossRate")
    if fec_plr is not None:
        if fec_plr > _CQD_VIDEO_POOR["post_fec_plr"]:
            return "poor", f"Post-FEC PLR {_fmt_pct(fec_plr)}"
        return "good", ""
    return "unclassified", ""


def _classify_vbss_stream(s: dict) -> tuple[str, str]:
    """Returns (status, reason)."""
    frame_loss = s.get("averageVideoFrameLossPercentage")
    codec = (s.get("videoCodec") or "").lower()
    direction = (s.get("streamDirection") or "").lower()
    if frame_loss is not None and codec != "h264s" and "inbound" in direction:
        if frame_loss > _CQD_VBSS_POOR["frame_loss_pct"]:
            return "poor", f"Frame Loss {_fmt_pct(frame_loss / 100)}"
        return "good", ""
    frame_rate = s.get("averageVideoFrameRate")
    if frame_rate is not None:
        if frame_rate < _CQD_VBSS_POOR["frame_rate_fps"]:
            return "poor", f"Frame Rate {_fmt_fps(frame_rate)}"
        return "good", ""
    return "unclassified", ""


def _rate(value: float | None, threshold: float, inverted: bool = False) -> str:
    """Simple Good/Poor rating per CQD — no 'Acceptable' tier (Microsoft doesn't use it)."""
    if value is None:
        return "—"
    is_poor = (value < threshold) if inverted else (value > threshold)
    return "🔴 Poor" if is_poor else "✅ Good"


def _streams_for_label(all_media: list[dict], label_substr: str) -> list[dict]:
    streams = []
    for media in all_media:
        if label_substr in (media.get("label") or ""):
            streams.extend(media.get("streams") or [])
    return streams


def _agg(streams: list[dict]) -> dict[str, Any]:
    def _floats(key: str) -> list[float]:
        return [s[key] for s in streams if isinstance(s.get(key), (int, float))]
    def _dms(key: str) -> list[float]:
        return [v for s in streams if (v := _iso_duration_to_ms(s.get(key))) is not None]
    def _avg(lst: list) -> float | None:
        return round(sum(lst) / len(lst), 4) if lst else None
    def _mx(lst: list) -> float | None:
        return max(lst) if lst else None
    return {
        "avg_jitter_ms":        _avg(_dms("averageJitter")),
        "max_jitter_ms":        _mx(_dms("maxJitter")),
        "avg_rtt_ms":           _avg(_dms("averageRoundTripTime")),
        "max_rtt_ms":           _mx(_dms("maxRoundTripTime")),
        "avg_packet_loss":      _avg(_floats("averagePacketLossRate")),
        "max_packet_loss":      _mx(_floats("maxPacketLossRate")),
        "avg_mos_degradation":  _avg(_floats("averageAudioDegradation")),
        "avg_concealed":        _avg(_floats("averageRatioOfConcealedSamples")),
        "avg_frame_loss":       _avg(_floats("averageVideoFrameLossPercentage")),
        "avg_frame_rate":       _avg(_floats("averageVideoFrameRate")),
        "audio_codecs":         list({s["audioCodec"] for s in streams if s.get("audioCodec") and s["audioCodec"] != "unknown"}),
        "video_codecs":         list({s["videoCodec"] for s in streams if s.get("videoCodec") and s["videoCodec"] != "unknown"}),
        "count":                len(streams),
    }


def _classify_streams_by_category(all_media: list[dict]) -> dict[str, dict]:
    """Classify each stream individually per Microsoft CQD methodology. Tracks poor reasons."""
    cats: dict[str, dict] = {
        "Audio":          {"streams": [], "poor": 0, "good": 0, "unclassified": 0, "poor_reasons": {}},
        "Video":          {"streams": [], "poor": 0, "good": 0, "unclassified": 0, "poor_reasons": {}},
        "Screen Sharing": {"streams": [], "poor": 0, "good": 0, "unclassified": 0, "poor_reasons": {}},
    }
    for media in all_media:
        label = (media.get("label") or "").lower()
        if "audio" in label:
            cat, fn = "Audio", _classify_audio_stream
        elif "applicationsharing" in label:
            cat, fn = "Screen Sharing", _classify_vbss_stream
        elif "video" in label:
            cat, fn = "Video", _classify_video_stream
        else:
            continue
        for stream in (media.get("streams") or []):
            status, reason = fn(stream)
            cats[cat]["streams"].append(stream)
            cats[cat][status] += 1
            if status == "poor" and reason:
                for part in reason.split(", "):
                    words = part.split(" ")
                    # "Frame Loss 12%", "Frame Rate 3fps" → 2 words; "Jitter 30ms" → 1 word
                    metric = " ".join(words[:2]) if words[0] in ("Frame", "Post-FEC", "Packet") else words[0]
                    cats[cat]["poor_reasons"][metric] = cats[cat]["poor_reasons"].get(metric, 0) + 1
    return cats


def _poor_stream_rate(stats: dict) -> str:
    total = stats["good"] + stats["poor"]
    if total == 0:
        return "N/A"
    rate = stats["poor"] / total
    return f"{stats['poor']}/{total} ({round(rate * 100, 1)}%)"


def _media_table(label: str, cat_stats: dict) -> list[str]:
    streams = cat_stats["streams"]
    if not streams:
        return []
    q = _agg(streams)
    is_audio = "Audio" in label
    is_vbss = "Screen" in label

    codecs = ", ".join(q["audio_codecs"] + q["video_codecs"]) or "unknown"
    poor_rate = _poor_stream_rate(cat_stats)
    total = cat_stats["good"] + cat_stats["poor"] + cat_stats["unclassified"]

    reasons = cat_stats.get("poor_reasons", {})

    def _poor_count(metric_key: str) -> str:
        n = reasons.get(metric_key, 0)
        return f"🔴 {n} streams" if n > 0 else "—"

    lines = [f"### {label} ({total} streams — Poor Stream Rate: {poor_rate})"]
    lines.append(f"**Codec:** {codecs}")
    lines.append("")
    lines.append("| Métrica | Avg (todos) | Max | Threshold CQD | Avg Status | Streams Poor |")
    lines.append("|---------|-------------|-----|---------------|------------|--------------|")

    if is_audio:
        lines.append(f"| Jitter | {_fmt_ms(q['avg_jitter_ms'])} | {_fmt_ms(q['max_jitter_ms'])} | >30ms = Poor | {_rate(q['avg_jitter_ms'], 30)} | {_poor_count('Jitter')} |")
        lines.append(f"| RTT | {_fmt_ms(q['avg_rtt_ms'])} | {_fmt_ms(q['max_rtt_ms'])} | >500ms = Poor | {_rate(q['avg_rtt_ms'], 500)} | {_poor_count('RTT')} |")
        lines.append(f"| Packet Loss | {_fmt_pct(q['avg_packet_loss'])} | {_fmt_pct(q['max_packet_loss'])} | >10% = Poor | {_rate(q['avg_packet_loss'], 0.10)} | {_poor_count('Packet')} |")
        mos = round(q['avg_mos_degradation'], 4) if q['avg_mos_degradation'] is not None else None
        lines.append(f"| MOS Degradation | {mos if mos is not None else 'N/A'} | — | >1.0 = Poor | {_rate(mos, 1.0)} | — |")
        lines.append(f"| Concealed Samples | {_fmt_pct(q['avg_concealed'])} | — | >7% = Poor | {_rate(q['avg_concealed'], 0.07)} | — |")
    elif is_vbss:
        lines.append(f"| Frame Loss | {_fmt_pct(q['avg_frame_loss'])} | — | >50% = Poor | {_rate(q['avg_frame_loss'], 50.0)} | {_poor_count('Frame Loss')} |")
        lines.append(f"| Frame Rate | {_fmt_fps(q['avg_frame_rate'])} | — | <1fps = Poor | {_rate(q['avg_frame_rate'], 1.0, inverted=True)} | {_poor_count('Frame Rate')} |")
    else:
        lines.append(f"| Frame Loss | {_fmt_pct(q['avg_frame_loss'])} | — | >50% = Poor | {_rate(q['avg_frame_loss'], 50.0)} | {_poor_count('Frame Loss')} |")
        lines.append(f"| Frame Rate | {_fmt_fps(q['avg_frame_rate'])} | — | <7fps = Poor | {_rate(q['avg_frame_rate'], 7.0, inverted=True)} | {_poor_count('Frame Rate')} |")
        lines.append(f"| Packet Loss | {_fmt_pct(q['avg_packet_loss'])} | {_fmt_pct(q['max_packet_loss'])} | >10% = Poor | {_rate(q['avg_packet_loss'], 0.10)} | {_poor_count('Packet')} |")

    if cat_stats["poor"] > 0:
        lines.append("")
        lines.append("> *Avg Status reflete a média de todos os streams. Streams Poor indica quantos streams individuais excederam o threshold CQD.*")

    return lines


def _network_table(all_media: list[dict]) -> list[str]:
    protocols, conn_types = set(), set()
    delay_ratios, bw_ratios = [], []
    for media in all_media:
        net = media.get("callerNetwork") or {}
        if net.get("networkTransportProtocol"):
            protocols.add(net["networkTransportProtocol"])
        if net.get("connectionType"):
            conn_types.add(net["connectionType"])
        if isinstance(net.get("delayEventRatio"), (int, float)):
            delay_ratios.append(net["delayEventRatio"])
        if isinstance(net.get("bandwidthLowEventRatio"), (int, float)):
            bw_ratios.append(net["bandwidthLowEventRatio"])

    def _avg(lst: list) -> float | None:
        return round(sum(lst) / len(lst), 4) if lst else None

    avg_delay = _avg(delay_ratios)
    avg_bw = _avg(bw_ratios)

    lines = ["### 🌐 Network"]
    lines.append(f"**Protocol:** {', '.join(protocols) or 'N/A'} | **Connection:** {', '.join(conn_types) or 'N/A'}")
    lines.append("")
    lines.append("| Métrica | Valor | Status |")
    lines.append("|---------|-------|--------|")
    delay_status = "✅ Good" if avg_delay is not None and avg_delay < 0.05 else ("🔴 Poor" if avg_delay is not None and avg_delay >= 0.05 else "—")
    bw_status = "✅ Good" if avg_bw is not None and avg_bw < 0.05 else ("🔴 Poor" if avg_bw is not None and avg_bw >= 0.05 else "—")
    lines.append(f"| Delay Event Ratio | {_fmt_pct(avg_delay)} | {delay_status} |")
    lines.append(f"| Bandwidth Low Event Ratio | {_fmt_pct(avg_bw)} | {bw_status} |")
    return lines


def _system_table(all_media: list[dict]) -> list[str]:
    devices, glitch_ratios, cpu_ratios = set(), [], []
    for media in all_media:
        dev = media.get("callerDevice") or {}
        if dev.get("captureDeviceName"):
            devices.add(dev["captureDeviceName"])
        if dev.get("renderDeviceName"):
            devices.add(dev["renderDeviceName"])
        if isinstance(dev.get("deviceGlitchEventRatio"), (int, float)):
            glitch_ratios.append(dev["deviceGlitchEventRatio"])
        if isinstance(dev.get("cpuInsufficentEventRatio"), (int, float)):
            cpu_ratios.append(dev["cpuInsufficentEventRatio"])

    def _avg(lst: list) -> float | None:
        return round(sum(lst) / len(lst), 4) if lst else None

    avg_glitch = _avg(glitch_ratios)
    avg_cpu = _avg(cpu_ratios)

    lines = ["### 🖥️ System / Device"]
    if devices:
        lines.append(f"**Devices:** {', '.join(list(devices)[:4])}")
    lines.append("")
    lines.append("| Métrica | Valor | Status |")
    lines.append("|---------|-------|--------|")
    glitch_status = "✅ Good" if avg_glitch is not None and avg_glitch < 0.01 else ("🔴 Poor" if avg_glitch is not None and avg_glitch >= 0.05 else ("🟡 Acceptable" if avg_glitch is not None else "—"))
    cpu_status = "✅ Good" if avg_cpu is not None and avg_cpu < 0.01 else ("🔴 Poor" if avg_cpu is not None and avg_cpu >= 0.05 else ("🟡 Acceptable" if avg_cpu is not None else "—"))
    lines.append(f"| Device Glitch Ratio | {_fmt_pct(avg_glitch)} | {glitch_status} |")
    lines.append(f"| CPU Insufficient Ratio | {_fmt_pct(avg_cpu)} | {cpu_status} |")
    return lines


def _overall_verdict(cat_classifications: dict[str, dict]) -> tuple[str, str]:
    """
    3-tier verdict based on max Poor Stream Rate across categories.
    < 5%  = Good (minor/isolated issues, user unlikely to notice)
    5-30% = Degraded (noticeable quality issues)
    > 30% = Poor (significant call quality problem)
    """
    max_rate = 0.0
    details = []
    for cat, stats in cat_classifications.items():
        total = stats["good"] + stats["poor"]
        if total == 0 or stats["poor"] == 0:
            continue
        rate = stats["poor"] / total
        max_rate = max(max_rate, rate)
        reasons = stats.get("poor_reasons", {})
        reason_str = ""
        if reasons:
            top = sorted(reasons.items(), key=lambda x: x[1], reverse=True)
            reason_str = " | causa: " + ", ".join(f"{m} ({c} streams)" for m, c in top[:3])
        details.append(f"- {cat}: {stats['poor']}/{total} streams Poor ({round(rate * 100, 1)}%){reason_str}")

    note = (
        "\n\n> *Classificação por stream individual (CQD). "
        "Avg Status = média de todos os streams. "
        "Streams Poor = streams individuais que excederam o threshold.*"
    )

    if not details:
        return "✅ Boa qualidade", f"Nenhum stream classificado como Poor. A chamada ocorreu sem problemas de qualidade detectados.{note}"

    body = "\n".join(details) + note

    if max_rate < 0.05:
        return (
            "🟡 Qualidade aceitável",
            f"Problemas pontuais em menos de 5% dos streams. Improvável que o usuário tenha percebido.\n{body}"
        )
    if max_rate < 0.30:
        return (
            "🔴 Qualidade degradada",
            f"Entre 5% e 30% dos streams com problemas. Usuários provavelmente perceberam degradação.\n{body}"
        )
    return (
        "🔴 Qualidade ruim",
        f"Mais de 30% dos streams com problemas. Impacto significativo na experiência.\n{body}"
    )


def _user_matches_endpoint(endpoint: dict | None, user_id: str, upn: str) -> bool:
    if not endpoint:
        return False
    identity = (endpoint.get("identity") or {})
    user = identity.get("user") or {}
    return (
        str(user.get("id", "")).lower() == user_id.lower() or
        str(user.get("userPrincipalName", "")).lower() == upn.lower()
    )


async def diagnose_call_quality(call_id: str, upn: str | None = None) -> dict[str, Any]:
    record = await graph_get(
        endpoints.call_record(call_id),
        scopes=SCOPES["call_records"],
        cache_key=f"callrecord:{call_id}",
        ttl=settings.cache_ttl_calls,
    )
    sessions_data = await graph_get(
        f"{endpoints.call_record_sessions(call_id)}?$expand=segments",
        scopes=SCOPES["call_records"],
        cache_key=f"callsessions:segments:{call_id}",
        ttl=settings.cache_ttl_calls,
    )
    sessions = sessions_data.get("value", [])
    result = record.get("result", "unknown")
    participants = record.get("participants", [])

    # Resolve user identity for per-user filtering
    user_id = ""
    user_display = ""
    if upn:
        profile = await get_user_profile(upn)
        user_id = profile.get("id", "")
        user_display = profile.get("displayName", upn)

    all_media: list[dict] = []
    for session in sessions:
        for segment in (session.get("segments") or []):
            if upn and user_id:
                caller = segment.get("caller") or {}
                callee = segment.get("callee") or {}
                if not (_user_matches_endpoint(caller, user_id, upn) or
                        _user_matches_endpoint(callee, user_id, upn)):
                    continue
            all_media.extend(segment.get("media") or [])

    all_streams: list[dict] = []
    for media in all_media:
        all_streams.extend(media.get("streams") or [])

    cat_classifications = _classify_streams_by_category(all_media)
    verdict_label, verdict_detail = _overall_verdict(cat_classifications)

    from datetime import datetime, timezone, timedelta
    _BRT = timezone(timedelta(hours=-3))
    start_raw = record.get("startDateTime", "")
    try:
        start_brt = datetime.fromisoformat(start_raw.replace("Z", "+00:00")).astimezone(_BRT).strftime("%d/%m/%Y %H:%M BRT")
    except Exception:
        start_brt = start_raw

    scope_label = f"para **{user_display}** (`{upn}`)" if upn else f"**{len(participants)} participantes**"
    lines = [
        f"## Call Diagnosis: `{call_id}`",
        f"- **Start:** {start_brt}",
        f"- **Escopo:** {scope_label} | **Sessions:** {len(sessions)} | **Streams analisados:** {len(all_streams)}",
        "",
    ]

    if not all_streams:
        if upn and user_id:
            # Check if user was actually in the call
            participant_ids = {
                (p.get("user") or {}).get("id", "").lower()
                for p in participants
                if isinstance(p, dict)
            }
            if user_id.lower() not in participant_ids:
                lines.append(
                    f"> ❌ **{user_display}** (`{upn}`) **não participou desta reunião**. "
                    "Verifique o Call ID ou o UPN informado."
                )
                return {"call_id": call_id, "result": result, "upn_found": False, "markdown": "\n".join(lines)}
        lines.append("> ⚠️ Sem dados de telemetria. O registro ainda pode estar sendo processado pela Microsoft (até 15 min de latência).")
        return {"call_id": call_id, "result": result, "markdown": "\n".join(lines)}

    for cat, stats in cat_classifications.items():
        if stats["streams"]:
            icon = {"Audio": "🔊", "Video": "📹", "Screen Sharing": "🖥️"}.get(cat, "")
            lines.extend(_media_table(f"{icon} {cat}", stats))
            lines.append("")

    lines.extend(_network_table(all_media))
    lines.append("")
    lines.extend(_system_table(all_media))
    lines.append("")
    lines.append("---")
    lines.append(f"### Diagnóstico Geral: {verdict_label}")
    lines.append(verdict_detail)
    lines.append("")
    lines.append("*Thresholds Microsoft CQD: Áudio — Jitter >30ms, RTT >500ms, Packet Loss >10% = Poor | Vídeo — Frame Loss >50%, Frame Rate <7fps = Poor | VBSS — Frame Rate <1fps = Poor*")

    return {
        "call_id": call_id,
        "result": result,
        "participant_count": len(participants),
        "session_count": len(sessions),
        "stream_count": len(all_streams),
        "categories": {k: {"good": v["good"], "poor": v["poor"], "unclassified": v["unclassified"]} for k, v in cat_classifications.items() if v["streams"]},
        "markdown": "\n".join(lines),
    }


async def list_failed_calls(upn: str, days: int = 7) -> dict[str, Any]:
    records = await _get_user_call_records(upn, days)
    failed = [r for r in records if _is_failed(r.get("result", ""))]
    lines = [f"## Failed Calls: {upn} (last {days} days)", _DATA_LAG_WARNING, f"- **Count:** {len(failed)}"]
    for r in failed:
        lines.append(f"\n- **{r.get('startDateTime', '?')}** — result: {r.get('result', '?')} | id: {r.get('id', '?')}")
    return {
        "upn": upn,
        "days": days,
        "failed_calls": failed,
        "count": len(failed),
        "data_lag_warning": _DATA_LAG_WARNING,
        "markdown": "\n".join(lines),
    }
