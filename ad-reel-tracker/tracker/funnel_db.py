"""
Funnel DB queries against Neon PostgreSQL (landing page sessions).
Reads chat_versions from config to split analysis by version cutoff.
"""

import json
import logging
import os
import urllib.request
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# KST = UTC+9
_KST_OFFSET = 9 * 3600


def _kst_to_utc(kst_str: str) -> str:
    """Convert 'YYYY-MM-DD HH:MM:SS' KST string to UTC ISO string with tz."""
    dt = datetime.strptime(kst_str, "%Y-%m-%d %H:%M:%S")
    ts = dt.timestamp() - _KST_OFFSET  # subtract 9h to get UTC epoch
    utc = datetime.fromtimestamp(ts, tz=timezone.utc)
    return utc.strftime("%Y-%m-%d %H:%M:%S+00")


def _query(conn_str: str, sql: str) -> list[dict]:
    host = conn_str.split("@")[1].split("/")[0]
    body = json.dumps({"query": sql, "params": []}).encode()
    req = urllib.request.Request(
        f"https://{host}/sql",
        data=body,
        headers={
            "Neon-Connection-String": conn_str,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())["rows"]


def _build_versions(chat_versions: list[dict]) -> list[dict]:
    """
    Returns list of dicts with resolved UTC cutoff timestamps:
      [{"version": "v1", "label": "...", "start_utc": None, "end_utc": "...+00"}, ...]
    """
    out = []
    for v in chat_versions:
        start_utc = _kst_to_utc(v["start_kst"]) if v.get("start_kst") else None
        end_utc = _kst_to_utc(v["end_kst"]) if v.get("end_kst") else None
        out.append({
            "version": v["version"],
            "label": v.get("label", v["version"]),
            "start_utc": start_utc,
            "end_utc": end_utc,
        })
    return out


def _version_case_sql(versions: list[dict]) -> str:
    """Build a CASE WHEN SQL fragment mapping created_at → version label."""
    parts = []
    for v in versions:
        conditions = []
        if v["start_utc"]:
            conditions.append(f"created_at >= '{v['start_utc']}'")
        if v["end_utc"]:
            conditions.append(f"created_at < '{v['end_utc']}'")
        if conditions:
            parts.append(f"WHEN {' AND '.join(conditions)} THEN '{v['version']} ({v['label']})'")
        else:
            parts.append(f"ELSE '{v['version']} ({v['label']})'")
    # Fall-through for any rows not matching (shouldn't happen with well-formed versions)
    sql = "CASE\n" + "\n".join(parts) + "\nELSE 'unknown' END"
    return sql


def get_funnel_by_version(cfg: dict) -> dict:
    """
    Returns funnel metrics split by chat version and by referral code.

    Result shape:
    {
      "versions": [...],          # version metadata
      "by_version": [...],        # overall funnel per version
      "by_code_version": [...],   # per referral_code × version
    }
    """
    conn_str = os.environ.get("NEON_CONNECTION_STRING") or cfg.get("funnel_db", {}).get("connection_string", "")
    if not conn_str:
        logger.warning("No NEON_CONNECTION_STRING configured — skipping funnel data")
        return {}

    chat_versions = cfg.get("chat_versions", [])
    if not chat_versions:
        logger.warning("No chat_versions configured — skipping version split")
        return {}

    referral_codes = cfg.get("funnel_db", {}).get("referral_codes", [])
    if not referral_codes:
        return {}

    versions = _build_versions(chat_versions)
    ver_case = _version_case_sql(versions)
    codes_in = ", ".join(f"'{c}'" for c in referral_codes)

    try:
        by_version = _query(conn_str, f"""
            SELECT
                {ver_case} AS version,
                COUNT(*)                                                    AS sessions,
                COUNT(*) FILTER (WHERE chat_count > 0)                     AS chatted,
                COUNT(*) FILTER (WHERE chat_count = 3)                     AS reached_cta,
                COUNT(*) FILTER (WHERE phone_submitted)                    AS phone_sub,
                ROUND(COUNT(*) FILTER (WHERE chat_count > 0)::numeric
                      / NULLIF(COUNT(*), 0) * 100, 1)                      AS chat_rate,
                ROUND(COUNT(*) FILTER (WHERE chat_count = 3)::numeric
                      / NULLIF(COUNT(*) FILTER (WHERE chat_count > 0), 0) * 100, 1) AS cta_of_chat,
                ROUND(COUNT(*) FILTER (WHERE phone_submitted)::numeric
                      / NULLIF(COUNT(*) FILTER (WHERE chat_count = 3), 0) * 100, 1) AS cta_conv,
                ROUND(COUNT(*) FILTER (WHERE phone_submitted)::numeric
                      / NULLIF(COUNT(*), 0) * 100, 2)                     AS phone_rate
            FROM landing_page_sessions
            WHERE referral_code IN ({codes_in})
            GROUP BY version
            ORDER BY MIN(created_at)
        """)

        by_code_version = _query(conn_str, f"""
            SELECT
                referral_code,
                {ver_case} AS version,
                COUNT(*)                                                    AS sessions,
                COUNT(*) FILTER (WHERE chat_count > 0)                     AS chatted,
                COUNT(*) FILTER (WHERE phone_submitted)                    AS phone_sub,
                ROUND(COUNT(*) FILTER (WHERE chat_count > 0)::numeric
                      / NULLIF(COUNT(*), 0) * 100, 1)                      AS chat_rate,
                ROUND(COUNT(*) FILTER (WHERE phone_submitted)::numeric
                      / NULLIF(COUNT(*), 0) * 100, 2)                     AS phone_rate,
                ROUND(COUNT(*) FILTER (WHERE phone_submitted)::numeric
                      / NULLIF(COUNT(*) FILTER (WHERE chat_count = 3), 0) * 100, 1) AS cta_conv
            FROM landing_page_sessions
            WHERE referral_code IN ({codes_in})
            GROUP BY referral_code, version
            ORDER BY referral_code, MIN(created_at)
        """)

    except Exception as e:
        logger.error(f"Funnel DB query failed: {e}")
        return {}

    return {
        "versions": versions,
        "by_version": by_version,
        "by_code_version": by_code_version,
    }
