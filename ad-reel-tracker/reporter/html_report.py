"""
HTML dashboard report generator for Instagram reel metrics.
Redesigned for clarity and actionable insights.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

COLORS = ["#6366f1", "#a855f7", "#ec4899", "#f59e0b", "#10b981"]
RANK_MEDALS = ["🥇", "🥈", "🥉", "4위", "5위"]


def _fmt(value, suffix="") -> str:
    if value is None:
        return "—"
    if value >= 1_000_000:
        return f"{value/1_000_000:.1f}M{suffix}"
    if value >= 1_000:
        return f"{value/1_000:.1f}K{suffix}"
    return f"{value:,}{suffix}"


def _delta(curr, prev, key: str) -> str:
    if prev is None or curr is None:
        return ""
    c = curr.get(key) or 0
    p = prev.get(key) or 0
    diff = c - p
    if diff == 0:
        return '<span class="d0">±0</span>'
    sign = "+" if diff > 0 else ""
    cls = "dup" if diff > 0 else "ddn"
    return f'<span class="{cls}">{sign}{_fmt(diff)}</span>'


def _replay_rate(views, plays) -> str:
    if not views or not plays or views == 0:
        return "—"
    rate = plays / views
    return f"{rate:.1f}x"


def _insight_text(metrics: list[dict]) -> str:
    """Generate plain-language insight summary."""
    if not metrics:
        return ""
    valid = [m for m in metrics if not m.get("error") and m.get("views")]
    if not valid:
        return ""

    top_views = max(valid, key=lambda m: m.get("views") or 0)
    top_eng = max(valid, key=lambda m: m.get("engagement_rate") or 0)
    top_plays = max(valid, key=lambda m: m.get("plays") or 0)

    lines = []
    tv_name = top_views.get("owner_name") or top_views["label"]
    te_name = top_eng.get("owner_name") or top_eng["label"]
    tp_name = top_plays.get("owner_name") or top_plays["label"]

    lines.append(f"📌 조회수 1위는 <b>{tv_name}</b> ({_fmt(top_views.get('views'))} views) — 노출량 최고")
    if top_eng["shortcode"] != top_views["shortcode"]:
        lines.append(f"💬 참여율 1위는 <b>{te_name}</b> ({top_eng.get('engagement_rate', 0):.2f}%) — 조회수는 낮아도 반응이 뜨거움")
    else:
        lines.append(f"💬 참여율도 <b>{te_name}</b>이 1위 ({top_eng.get('engagement_rate', 0):.2f}%) — 노출·반응 모두 우수")

    if top_plays["shortcode"] != top_views["shortcode"]:
        vr = _replay_rate(top_plays.get("views"), top_plays.get("plays"))
        lines.append(f"🔁 재생률(Replay) 1위는 <b>{tp_name}</b> ({vr}) — 반복 시청 유도력 최고")

    # Flag low engagement despite high views
    for m in valid:
        er = m.get("engagement_rate") or 0
        v = m.get("views") or 0
        if v > 5000 and er < 1.0:
            name = m.get("owner_name") or m["label"]
            lines.append(f"⚠️ <b>{name}</b>은 조회수({_fmt(v)}) 대비 참여율({er:.2f}%)이 낮음 — 광고 소재 개선 검토")

    return "<br>".join(lines)


def _build_funnel_section(funnel: dict) -> str:
    """Build HTML for chat version comparison funnel section."""
    if not funnel or not funnel.get("by_version"):
        return ""

    by_version = funnel["by_version"]
    by_code_version = funnel.get("by_code_version", [])

    # ── Overall version comparison table ──────────────────────────
    header_cells = "".join(
        f"<th>{r['version']}</th>" for r in by_version
    )

    def metric_row(label, key, suffix=""):
        cells = ""
        prev_val = None
        for r in by_version:
            raw = r.get(key)
            val = float(raw) if raw is not None else None
            display = f"{val:g}{suffix}" if val is not None else "—"
            # Highlight change vs previous version
            if prev_val is not None and val is not None:
                diff = val - prev_val
                if abs(diff) > 0.01:
                    sign = "+" if diff > 0 else ""
                    cls = "dup" if diff > 0 else "ddn"
                    display += f' <span class="{cls}">{sign}{diff:.1f}{suffix}</span>'
            prev_val = val
            cells += f"<td>{display}</td>"
        return f"<tr><td class='metric-label'>{label}</td>{cells}</tr>"

    overview_rows = "".join([
        metric_row("세션 수", "sessions"),
        metric_row("채팅 시작율", "chat_rate", "%"),
        metric_row("CTA 도달율 (chat→3번)", "cta_of_chat", "%"),
        metric_row("CTA 전환율 (3번→전화)", "cta_conv", "%"),
        metric_row("최종 전환율 (세션→전화)", "phone_rate", "%"),
        metric_row("전화 제출 수", "phone_sub"),
    ])

    overview_table = f"""
<table class="funnel-table">
  <thead>
    <tr><th>지표</th>{header_cells}</tr>
  </thead>
  <tbody>
    {overview_rows}
  </tbody>
</table>"""

    # ── Per referral-code × version pivot ─────────────────────────
    # Gather unique referral codes and versions in order
    codes = list(dict.fromkeys(r["referral_code"] for r in by_code_version))
    versions = list(dict.fromkeys(r["version"] for r in by_code_version))

    # Build lookup: (code, version) -> row
    lookup = {(r["referral_code"], r["version"]): r for r in by_code_version}

    code_header = "".join(f"<th colspan='2'>{v}</th>" for v in versions)
    sub_header = "".join("<th>세션</th><th>전환율</th>" for _ in versions)

    code_rows = ""
    for code in codes:
        cells = ""
        for v in versions:
            row = lookup.get((code, v))
            if row:
                sessions = row.get("sessions") or "—"
                rate = row.get("phone_rate")
                rate_disp = f"{float(rate):.2f}%" if rate is not None else "—"
            else:
                sessions, rate_disp = "—", "—"
            cells += f"<td>{sessions}</td><td>{rate_disp}</td>"
        code_rows += f"<tr><td>@{code}</td>{cells}</tr>"

    code_table = f"""
<table class="funnel-table">
  <thead>
    <tr><th>계정</th>{code_header}</tr>
    <tr><th></th>{sub_header}</tr>
  </thead>
  <tbody>
    {code_rows}
  </tbody>
</table>"""

    # ── Version metadata badges ────────────────────────────────────
    version_badges = ""
    for v in funnel.get("versions", []):
        start = v.get("start_kst") or "서비스 시작"
        end = v.get("end_kst") or "현재"
        # Display KST times stored in config directly (already KST)
        # The stored values in versions dict are UTC; label stays original
        version_badges += f'<span class="ver-badge">{v["version"]}: {v["label"]}</span> '

    return f"""
<div class="section">
  <div class="section-label">채팅 버전별 전환율 비교</div>
  <div class="funnel-note">
    {version_badges}
    <span class="funnel-hint">※ 기점: 2026-03-15 16:20 KST (채팅 콘텐츠 업데이트 #1)</span>
  </div>
  <div style="margin-top:16px">
    <div class="funnel-subtitle">전체 퍼널 (버전별)</div>
    {overview_table}
  </div>
  <div style="margin-top:20px">
    <div class="funnel-subtitle">계정별 세션 수 · 전환율 (버전별)</div>
    {code_table}
  </div>
</div>"""


def generate_html_dashboard(
    latest_metrics: list[dict],
    history: dict[str, list[dict]],
    output_path: str,
    history_days: int = 30,
    funnel: dict | None = None,
) -> str:
    generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # Sort by views descending for ranking
    valid = [m for m in latest_metrics if not m.get("error") and m.get("views")]
    ranked = sorted(valid, key=lambda m: m.get("views") or 0, reverse=True)
    # Add any errored ones at end
    ranked += [m for m in latest_metrics if m.get("error") or not m.get("views")]

    insight_html = _insight_text(latest_metrics)
    summary_html = _build_summary_bar(ranked)
    cards_html = _build_cards(ranked, history)
    ts_data = _build_timeseries(history, ranked)
    comp_data = _build_comparison(ranked)
    funnel_html = _build_funnel_section(funnel or {})

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>광고 릴스 성과 대시보드</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root {{
  --bg: #0a0f1e;
  --surface: #111827;
  --surface2: #1f2937;
  --border: #1f2937;
  --text: #f1f5f9;
  --muted: #64748b;
  --accent: #6366f1;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, 'Segoe UI', sans-serif; background: var(--bg);
        color: var(--text); padding: 28px 32px; max-width: 1300px; margin: 0 auto; }}
a {{ color: inherit; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}

/* Header */
.header {{ margin-bottom: 28px; }}
.header h1 {{ font-size: 1.4rem; font-weight: 700; letter-spacing: -0.02em; }}
.header .meta {{ color: var(--muted); font-size: 0.8rem; margin-top: 4px; }}

/* Insight box */
.insight {{ background: #0f172a; border: 1px solid #1e3a5f; border-left: 3px solid var(--accent);
            border-radius: 10px; padding: 14px 18px; margin-bottom: 28px;
            font-size: 0.85rem; line-height: 1.8; color: #cbd5e1; }}

/* Summary bar */
.summary {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: 32px; }}
.sum-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
             padding: 14px 16px; cursor: default; transition: border-color .2s; }}
.sum-card:hover {{ border-color: #374151; }}
.sum-rank {{ font-size: 1.1rem; margin-bottom: 6px; }}
.sum-name {{ font-size: 0.75rem; font-weight: 600; color: #e2e8f0; margin-bottom: 2px;
             white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.sum-handle {{ font-size: 0.68rem; color: var(--muted); margin-bottom: 10px; }}
.sum-views {{ font-size: 1.3rem; font-weight: 800; letter-spacing: -0.03em; }}
.sum-views span {{ font-size: 0.65rem; font-weight: 400; color: var(--muted); margin-left: 3px; }}
.bar-wrap {{ margin-top: 8px; height: 4px; background: var(--surface2); border-radius: 2px; overflow: hidden; }}
.bar-fill {{ height: 100%; border-radius: 2px; }}

/* Section */
.section {{ margin-bottom: 36px; }}
.section-label {{ font-size: 0.7rem; font-weight: 600; text-transform: uppercase;
                  letter-spacing: 0.1em; color: var(--muted); margin-bottom: 14px; }}

/* Metric cards */
.cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 14px; }}
.card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
         padding: 18px 20px; position: relative; overflow: hidden; }}
.card::before {{ content: attr(data-rank); position: absolute; top: 12px; right: 16px;
                 font-size: 1.3rem; opacity: .35; }}
.card-top {{ display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }}
.card-avatar {{ width: 38px; height: 38px; border-radius: 50%; display: flex; align-items: center;
                justify-content: center; font-size: 1rem; font-weight: 700; flex-shrink: 0; }}
.card-who {{ min-width: 0; }}
.card-name {{ font-size: 0.9rem; font-weight: 700; white-space: nowrap;
              overflow: hidden; text-overflow: ellipsis; }}
.card-handle {{ font-size: 0.72rem; color: var(--muted); }}
.card-url {{ font-size: 0.68rem; color: #818cf8; }}

/* Metrics table inside card */
.metrics {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; margin-top: 2px; }}
.metric {{ background: var(--bg); border-radius: 8px; padding: 9px 11px; }}
.metric-label {{ font-size: 0.62rem; text-transform: uppercase; letter-spacing: .06em;
                 color: var(--muted); margin-bottom: 4px; }}
.metric-val {{ font-size: 1.05rem; font-weight: 700; }}
.metric-sub {{ font-size: 0.65rem; color: var(--muted); margin-top: 2px; }}
.dup {{ color: #34d399; font-size: 0.65rem; margin-left: 4px; }}
.ddn {{ color: #f87171; font-size: 0.65rem; margin-left: 4px; }}
.d0  {{ color: var(--muted); font-size: 0.65rem; margin-left: 4px; }}

/* Engagement badge */
.eng-badge {{ display: inline-block; padding: 2px 8px; border-radius: 9999px;
              font-size: 0.68rem; font-weight: 700; margin-left: 6px; }}
.eng-high {{ background: #064e3b; color: #34d399; }}
.eng-mid  {{ background: #1c1917; color: #fbbf24; }}
.eng-low  {{ background: #1f1212; color: #f87171; }}

/* Charts */
.charts-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
@media (max-width: 860px) {{ .charts-grid {{ grid-template-columns: 1fr; }} }}
.chart-card {{ background: var(--surface); border: 1px solid var(--border);
               border-radius: 12px; padding: 20px; }}
.chart-card h3 {{ font-size: 0.78rem; font-weight: 600; color: var(--muted);
                  text-transform: uppercase; letter-spacing: .07em; margin-bottom: 16px; }}
.chart-wrap {{ position: relative; height: 230px; }}

.collected {{ font-size: 0.65rem; color: #334155; margin-top: 12px; text-align: right; }}
footer {{ text-align: center; font-size: 0.7rem; color: #1e293b; margin-top: 40px; }}

/* Funnel version section */
.funnel-note {{ font-size: 0.78rem; color: var(--muted); margin-bottom: 10px; }}
.funnel-hint {{ font-size: 0.72rem; color: #334155; }}
.funnel-subtitle {{ font-size: 0.72rem; font-weight: 600; color: var(--muted); text-transform: uppercase;
                    letter-spacing: .06em; margin-bottom: 8px; }}
.ver-badge {{ display: inline-block; background: #1e1b4b; color: #818cf8;
              border: 1px solid #312e81; border-radius: 9999px; padding: 2px 10px;
              font-size: 0.72rem; font-weight: 600; margin-right: 6px; }}
.funnel-table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; }}
.funnel-table th {{ background: var(--surface2); color: var(--muted); padding: 8px 12px;
                    text-align: left; font-weight: 600; border-bottom: 1px solid var(--border); }}
.funnel-table td {{ padding: 8px 12px; border-bottom: 1px solid #111827; }}
.funnel-table td.metric-label {{ color: #94a3b8; font-size: 0.78rem; }}
.funnel-table tr:last-child td {{ border-bottom: none; }}
.funnel-table tr:hover td {{ background: #111827; }}
</style>
</head>
<body>

<div class="header">
  <h1>📊 광고 릴스 성과 대시보드</h1>
  <div class="meta">수집: {generated_at} &nbsp;·&nbsp; 최근 {history_days}일 데이터</div>
</div>

<div class="insight">{insight_html}</div>

<div class="section">
  <div class="section-label">조회수 순위</div>
  <div class="summary">{summary_html}</div>
</div>

<div class="section">
  <div class="section-label">릴스별 상세 지표</div>
  <div class="cards">{cards_html}</div>
</div>

<div class="section">
  <div class="section-label">성과 비교</div>
  <div class="charts-grid">
    <div class="chart-card">
      <h3>조회수 비교 (Views)</h3>
      <div class="chart-wrap"><canvas id="cViews"></canvas></div>
    </div>
    <div class="chart-card">
      <h3>좋아요 · 댓글 비교</h3>
      <div class="chart-wrap"><canvas id="cEng"></canvas></div>
    </div>
    <div class="chart-card">
      <h3>참여율 비교 (Engagement Rate %)</h3>
      <div class="chart-wrap"><canvas id="cEngRate"></canvas></div>
    </div>
    <div class="chart-card">
      <h3>재생수 비교 (Plays — 반복 포함)</h3>
      <div class="chart-wrap"><canvas id="cPlays"></canvas></div>
    </div>
  </div>
</div>

{funnel_html}

<div class="section">
  <div class="section-label">시간별 추이</div>
  <div class="charts-grid">
    <div class="chart-card">
      <h3>Views 추이</h3>
      <div class="chart-wrap"><canvas id="tViews"></canvas></div>
    </div>
    <div class="chart-card">
      <h3>참여율 추이</h3>
      <div class="chart-wrap"><canvas id="tEng"></canvas></div>
    </div>
  </div>
</div>

<footer>Instagram Ad Reel Tracker · Apify</footer>

<script>
const C = {json.dumps(COLORS)};
const comp = {json.dumps(comp_data)};
const ts   = {json.dumps(ts_data)};

const baseOpts = (title) => ({{
  responsive: true, maintainAspectRatio: false,
  plugins: {{
    legend: {{ display: false }},
    tooltip: {{ callbacks: {{ label: ctx => ` ${{ctx.dataset.label}}: ${{ctx.parsed.y?.toLocaleString() ?? ctx.parsed.x?.toLocaleString()}}` }} }}
  }},
  scales: {{
    x: {{ ticks: {{ color:'#64748b', font:{{size:11}} }}, grid:{{ color:'#111827' }} }},
    y: {{ ticks: {{ color:'#64748b', font:{{size:11}} }}, grid:{{ color:'#1f2937' }} }}
  }}
}});

function hBar(id, labels, data, colors, fmt) {{
  new Chart(document.getElementById(id), {{
    type: 'bar',
    data: {{
      labels,
      datasets: [{{ data, backgroundColor: colors.map(c=>c+'bb'),
                    borderColor: colors, borderWidth: 1, borderRadius: 6 }}]
    }},
    options: {{ ...baseOpts(), indexAxis: 'y',
      plugins: {{ ...baseOpts().plugins,
        tooltip: {{ callbacks: {{ label: ctx => ` ${{ctx.parsed.x?.toLocaleString()}}` }} }} }} }}
  }});
}}

function vBar(id, labels, datasets) {{
  new Chart(document.getElementById(id), {{
    type: 'bar',
    data: {{ labels, datasets: datasets.map((d,i) => ({{
      label: d.label, data: d.data,
      backgroundColor: C[i%C.length]+'99', borderColor: C[i%C.length],
      borderWidth: 1, borderRadius: 4
    }})) }},
    options: baseOpts()
  }});
}}

function line(id, datasets) {{
  new Chart(document.getElementById(id), {{
    type: 'line',
    data: {{ datasets: datasets.map((d,i) => ({{
      label: d.label, data: d.data,
      borderColor: C[i%C.length], backgroundColor: C[i%C.length]+'22',
      tension: 0.3, fill: false, pointRadius: 4, pointHoverRadius: 6
    }})) }},
    options: {{ ...baseOpts(), scales: {{ ...baseOpts().scales, x: {{ ...baseOpts().scales.x, type:'category' }} }} }}
  }});
}}

// Comparison charts
const labels = comp.map(d => d.name);
const colors = comp.map((_,i) => C[i%C.length]);

hBar('cViews', labels, comp.map(d=>d.views), colors);
hBar('cPlays', labels, comp.map(d=>d.plays), colors);
hBar('cEngRate', labels, comp.map(d=>d.er), colors);
vBar('cEng', labels, [
  {{ label:'좋아요', data: comp.map(d=>d.likes) }},
  {{ label:'댓글',   data: comp.map(d=>d.comments) }},
]);

// Time-series charts
line('tViews', ts.map((r,i) => ({{ label: r.name, data: r.ts.map(p=>p.v) }})));
line('tEng',   ts.map((r,i) => ({{ label: r.name, data: r.ts.map(p=>p.er) }})));
</script>
</body>
</html>
"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    logger.info(f"Dashboard written to: {output_path}")
    return str(output_path)


def _eng_badge(er) -> str:
    if er is None:
        return ""
    if er >= 3.0:
        return f'<span class="eng-badge eng-high">{er:.2f}%</span>'
    if er >= 1.5:
        return f'<span class="eng-badge eng-mid">{er:.2f}%</span>'
    return f'<span class="eng-badge eng-low">{er:.2f}%</span>'


def _build_summary_bar(ranked: list[dict]) -> str:
    max_views = max((m.get("views") or 0 for m in ranked), default=1) or 1
    parts = []
    for i, m in enumerate(ranked[:5]):
        views = m.get("views") or 0
        pct = views / max_views * 100
        color = COLORS[i % len(COLORS)]
        name = m.get("owner_name") or m["label"]
        handle = f'@{m["owner_username"]}' if m.get("owner_username") else ""
        parts.append(f"""
  <div class="sum-card">
    <div class="sum-rank">{RANK_MEDALS[i]}</div>
    <div class="sum-name" title="{name}">{name}</div>
    <div class="sum-handle">{handle}</div>
    <div class="sum-views">{_fmt(views)}<span>views</span></div>
    <div class="bar-wrap"><div class="bar-fill" style="width:{pct:.1f}%;background:{color}"></div></div>
  </div>""")
    return "\n".join(parts)


def _build_cards(ranked: list[dict], history: dict[str, list[dict]]) -> str:
    cards = []
    for i, m in enumerate(ranked):
        sc = m["shortcode"]
        hist = history.get(sc, [])
        prev = hist[-2] if len(hist) >= 2 else None
        color = COLORS[i % len(COLORS)]
        medal = RANK_MEDALS[i] if i < len(RANK_MEDALS) else ""

        name = m.get("owner_name") or m["label"]
        handle = m.get("owner_username") or ""
        handle_display = f"@{handle}" if handle else ""
        profile_url = f"https://www.instagram.com/{handle}/" if handle else "#"
        initial = (name[0] if name else "?").upper()

        er = m.get("engagement_rate")
        er_badge = _eng_badge(er)
        replay = _replay_rate(m.get("views"), m.get("plays"))
        collected = (m.get("collected_at") or "")[:16].replace("T", " ")

        views_d = _delta(m, prev, "views")
        likes_d = _delta(m, prev, "likes")
        comments_d = _delta(m, prev, "comments")

        error_html = f'<div style="color:#f87171;font-size:.8rem;margin-top:8px">⚠ {m["error"]}</div>' if m.get("error") else ""

        cards.append(f"""
<div class="card" data-rank="{medal}">
  <div class="card-top">
    <div class="card-avatar" style="background:{color}22;color:{color}">{initial}</div>
    <div class="card-who">
      <div class="card-name"><a href="{profile_url}" target="_blank">{name}</a></div>
      <div class="card-handle"><a href="{profile_url}" target="_blank">{handle_display}</a></div>
      <div class="card-url"><a href="{m['url']}" target="_blank">릴스 바로가기 →</a></div>
    </div>
  </div>
  <div class="metrics">
    <div class="metric">
      <div class="metric-label">Views</div>
      <div class="metric-val">{_fmt(m.get('views'))}{views_d}</div>
      <div class="metric-sub">순수 조회</div>
    </div>
    <div class="metric">
      <div class="metric-label">Plays</div>
      <div class="metric-val">{_fmt(m.get('plays'))}</div>
      <div class="metric-sub">재생 {replay} 반복률</div>
    </div>
    <div class="metric">
      <div class="metric-label">참여율</div>
      <div class="metric-val">{er_badge if er else '—'}</div>
      <div class="metric-sub">likes+comments/views</div>
    </div>
    <div class="metric">
      <div class="metric-label">Likes</div>
      <div class="metric-val">{_fmt(m.get('likes'))}{likes_d}</div>
    </div>
    <div class="metric">
      <div class="metric-label">Comments</div>
      <div class="metric-val">{_fmt(m.get('comments'))}{comments_d}</div>
    </div>
    <div class="metric">
      <div class="metric-label">Shares / Saves</div>
      <div class="metric-val">{_fmt(m.get('shares'))} / {_fmt(m.get('saves'))}</div>
    </div>
  </div>
  {error_html}
  <div class="collected">수집: {collected} UTC</div>
</div>""")
    return "\n".join(cards)


def _build_comparison(ranked: list[dict]) -> list[dict]:
    out = []
    for m in ranked:
        name = m.get("owner_name") or m["label"]
        out.append({
            "name": name,
            "views": m.get("views") or 0,
            "plays": m.get("plays") or 0,
            "likes": m.get("likes") or 0,
            "comments": m.get("comments") or 0,
            "er": round(m.get("engagement_rate") or 0, 2),
        })
    return out


def _build_timeseries(history: dict[str, list[dict]], ranked: list[dict]) -> list[dict]:
    out = []
    sc_order = [m["shortcode"] for m in ranked]
    for sc in sc_order:
        records = history.get(sc, [])
        if not records:
            continue
        name = records[0].get("owner_name") or records[0].get("label", sc)
        out.append({
            "name": name,
            "ts": [
                {
                    "t": r["collected_at"][:16].replace("T", " "),
                    "v": r.get("views") or 0,
                    "er": round(r.get("engagement_rate") or 0, 2),
                }
                for r in records
            ],
        })
    return out
