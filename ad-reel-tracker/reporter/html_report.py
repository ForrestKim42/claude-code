"""
HTML dashboard report generator for Instagram reel metrics.
Uses Chart.js for time-series and comparison charts.
Outputs a self-contained single HTML file (no external dependencies at runtime).
"""

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Chart colors for up to 5 reels
COLORS = [
    "#4F46E5",  # indigo
    "#7C3AED",  # violet
    "#EC4899",  # pink
    "#F59E0B",  # amber
    "#10B981",  # emerald
]


def _fmt(value, suffix="") -> str:
    """Format large numbers with K/M suffixes."""
    if value is None:
        return "—"
    if value >= 1_000_000:
        return f"{value/1_000_000:.1f}M{suffix}"
    if value >= 1_000:
        return f"{value/1_000:.1f}K{suffix}"
    return f"{value:,}{suffix}"


def _delta_html(current, previous, key: str) -> str:
    """Return HTML span showing change from previous snapshot."""
    if previous is None or current is None:
        return ""
    curr_val = current.get(key) or 0
    prev_val = previous.get(key) or 0
    diff = curr_val - prev_val
    if diff == 0:
        return '<span class="delta neutral">±0</span>'
    sign = "+" if diff > 0 else ""
    cls = "up" if diff > 0 else "down"
    return f'<span class="delta {cls}">{sign}{_fmt(diff)}</span>'


def generate_html_dashboard(
    latest_metrics: list[dict],
    history: dict[str, list[dict]],
    output_path: str,
    history_days: int = 30,
) -> str:
    """
    Generate a self-contained HTML dashboard.

    Args:
        latest_metrics: List of most recent metric dicts per reel
        history: Dict mapping shortcode -> list of historical metric dicts
        output_path: Path to write the HTML file
        history_days: Number of days shown in time-series chart

    Returns:
        Path to the generated file
    """
    generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # Build metric cards HTML
    cards_html = _build_metric_cards(latest_metrics, history)

    # Build Chart.js datasets
    timeseries_data = _build_timeseries_data(history)
    comparison_data = _build_comparison_data(latest_metrics)

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Instagram Ad Reel Performance Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #0f172a; color: #e2e8f0; min-height: 100vh; padding: 24px; }}
  h1 {{ font-size: 1.5rem; font-weight: 700; margin-bottom: 4px; }}
  .subtitle {{ color: #94a3b8; font-size: 0.875rem; margin-bottom: 28px; }}
  .section-title {{ font-size: 1rem; font-weight: 600; color: #94a3b8;
                    text-transform: uppercase; letter-spacing: 0.05em;
                    margin: 32px 0 16px; }}
  /* Cards */
  .cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }}
  .card {{ background: #1e293b; border-radius: 12px; padding: 20px;
           border: 1px solid #334155; }}
  .card-header {{ display: flex; justify-content: space-between; align-items: flex-start;
                  margin-bottom: 16px; }}
  .card-label {{ font-weight: 600; font-size: 0.95rem; }}
  .card-source {{ font-size: 0.7rem; color: #64748b; background: #0f172a;
                  padding: 2px 8px; border-radius: 9999px; }}
  .card-url {{ font-size: 0.72rem; color: #4F46E5; margin-bottom: 14px;
               white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .card-url a {{ color: #818cf8; text-decoration: none; }}
  .card-url a:hover {{ text-decoration: underline; }}
  .metrics-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
  .metric {{ background: #0f172a; border-radius: 8px; padding: 10px 12px; }}
  .metric-name {{ font-size: 0.7rem; color: #64748b; text-transform: uppercase;
                  letter-spacing: 0.05em; margin-bottom: 4px; }}
  .metric-value {{ font-size: 1.25rem; font-weight: 700; }}
  .delta {{ font-size: 0.7rem; margin-left: 6px; font-weight: 500; }}
  .delta.up {{ color: #34d399; }}
  .delta.down {{ color: #f87171; }}
  .delta.neutral {{ color: #64748b; }}
  .card-error {{ color: #f87171; font-size: 0.8rem; margin-top: 8px; }}
  .card-collected {{ font-size: 0.7rem; color: #475569; margin-top: 12px; }}
  /* Charts */
  .charts-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
  @media (max-width: 900px) {{ .charts-grid {{ grid-template-columns: 1fr; }} }}
  .chart-card {{ background: #1e293b; border-radius: 12px; padding: 20px;
                 border: 1px solid #334155; }}
  .chart-card h3 {{ font-size: 0.875rem; font-weight: 600; color: #94a3b8; margin-bottom: 16px; }}
  .chart-wrap {{ position: relative; height: 260px; }}
  /* No data */
  .no-data {{ color: #475569; font-size: 0.875rem; padding: 40px 0; text-align: center; }}
  footer {{ margin-top: 40px; text-align: center; font-size: 0.75rem; color: #334155; }}
</style>
</head>
<body>
<h1>📊 Instagram Ad Reel Dashboard</h1>
<p class="subtitle">Generated: {generated_at} &nbsp;·&nbsp; Last {history_days} days</p>

<p class="section-title">Latest Metrics</p>
<div class="cards">
{cards_html}
</div>

<p class="section-title">Performance Over Time</p>
<div class="charts-grid">
  <div class="chart-card">
    <h3>Views 추이</h3>
    <div class="chart-wrap"><canvas id="viewsChart"></canvas></div>
  </div>
  <div class="chart-card">
    <h3>Likes 추이</h3>
    <div class="chart-wrap"><canvas id="likesChart"></canvas></div>
  </div>
  <div class="chart-card">
    <h3>Comments 추이</h3>
    <div class="chart-wrap"><canvas id="commentsChart"></canvas></div>
  </div>
  <div class="chart-card">
    <h3>Engagement Rate (%) 추이</h3>
    <div class="chart-wrap"><canvas id="engChart"></canvas></div>
  </div>
</div>

<p class="section-title">Comparison (Latest Snapshot)</p>
<div class="charts-grid">
  <div class="chart-card">
    <h3>Views 비교</h3>
    <div class="chart-wrap"><canvas id="compViewsChart"></canvas></div>
  </div>
  <div class="chart-card">
    <h3>Likes / Comments 비교</h3>
    <div class="chart-wrap"><canvas id="compEngChart"></canvas></div>
  </div>
</div>

<footer>Instagram Ad Reel Tracker — 데이터 수집: Instaloader / Apify</footer>

<script>
const COLORS = {json.dumps(COLORS)};
const tsData = {json.dumps(timeseries_data)};
const compData = {json.dumps(comparison_data)};

function makeChartOptions(yLabel) {{
  return {{
    responsive: true,
    maintainAspectRatio: false,
    interaction: {{ mode: 'index', intersect: false }},
    plugins: {{ legend: {{ labels: {{ color: '#94a3b8', font: {{ size: 11 }} }} }} }},
    scales: {{
      x: {{ ticks: {{ color: '#64748b', maxRotation: 30, font: {{ size: 10 }} }},
            grid: {{ color: '#1e293b' }} }},
      y: {{ ticks: {{ color: '#64748b', font: {{ size: 11 }} }},
            grid: {{ color: '#334155' }},
            title: {{ display: !!yLabel, text: yLabel, color: '#64748b' }} }}
    }}
  }};
}}

function makeBarOptions(stacked) {{
  const opts = makeChartOptions(null);
  opts.scales.x.stacked = stacked;
  opts.scales.y.stacked = stacked;
  return opts;
}}

function buildTimeseriesChart(canvasId, metric, label, yLabel) {{
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  const datasets = tsData.reels.map((r, i) => ({{
    label: r.label,
    data: r.timestamps.map((t, j) => ({{ x: t, y: r[metric][j] }})),
    borderColor: COLORS[i % COLORS.length],
    backgroundColor: COLORS[i % COLORS.length] + '33',
    tension: 0.3,
    fill: false,
    pointRadius: 3,
  }}));
  new Chart(ctx, {{
    type: 'line',
    data: {{ datasets }},
    options: {{
      ...makeChartOptions(yLabel),
      scales: {{
        ...makeChartOptions(yLabel).scales,
        x: {{ ...makeChartOptions(yLabel).scales.x, type: 'category' }}
      }}
    }}
  }});
}}

function buildComparisonChart(canvasId, metrics, labels, stacked) {{
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  const datasets = metrics.map((m, i) => ({{
    label: m.label,
    data: compData.labels.map(l => {{
      const r = compData.data.find(d => d.shortcode === compData.shortcodes[compData.labels.indexOf(l)] || d.label === l);
      return r ? (r[m.key] ?? 0) : 0;
    }}),
    backgroundColor: COLORS[i % COLORS.length] + 'cc',
    borderColor: COLORS[i % COLORS.length],
    borderWidth: 1,
  }}));
  // Simpler: one dataset per metric, one bar per reel
  const ds2 = metrics.map((m, i) => ({{
    label: m.label,
    data: compData.data.map(d => d[m.key] ?? 0),
    backgroundColor: COLORS[i % COLORS.length] + 'cc',
    borderColor: COLORS[i % COLORS.length],
    borderWidth: 1,
  }}));
  new Chart(ctx, {{
    type: 'bar',
    data: {{ labels: compData.data.map(d => d.label), datasets: ds2 }},
    options: makeBarOptions(stacked),
  }});
}}

// Build time-series charts
buildTimeseriesChart('viewsChart', 'views', 'Views', 'Views');
buildTimeseriesChart('likesChart', 'likes', 'Likes', 'Likes');
buildTimeseriesChart('commentsChart', 'comments', 'Comments', 'Comments');
buildTimeseriesChart('engChart', 'engagement_rate', 'Engagement Rate', '%');

// Build comparison charts
buildComparisonChart('compViewsChart', [{{label: 'Views', key: 'views'}}], [], false);
buildComparisonChart('compEngChart', [
  {{label: 'Likes', key: 'likes'}},
  {{label: 'Comments', key: 'comments'}},
], [], false);
</script>
</body>
</html>
"""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
    logger.info(f"Dashboard written to: {output_path}")
    return str(output_path)


def _build_metric_cards(latest_metrics: list[dict], history: dict[str, list[dict]]) -> str:
    if not latest_metrics:
        return '<p class="no-data">아직 수집된 데이터가 없습니다. python main.py --collect 를 실행하세요.</p>'

    cards = []
    for m in latest_metrics:
        sc = m["shortcode"]
        hist = history.get(sc, [])
        prev = hist[-2] if len(hist) >= 2 else None

        views_delta = _delta_html(m, prev, "views")
        likes_delta = _delta_html(m, prev, "likes")
        comments_delta = _delta_html(m, prev, "comments")
        shares_delta = _delta_html(m, prev, "shares")

        er = m.get("engagement_rate")
        er_str = f"{er:.2f}%" if er is not None else "—"

        error_html = f'<p class="card-error">⚠ 오류: {m["error"]}</p>' if m.get("error") else ""
        collected = m.get("collected_at", "")[:16].replace("T", " ")

        cards.append(f"""
  <div class="card">
    <div class="card-header">
      <span class="card-label">{m['label']}</span>
      <span class="card-source">{m.get('source', '?')}</span>
    </div>
    <div class="card-url"><a href="{m['url']}" target="_blank">{m['url']}</a></div>
    <div class="metrics-grid">
      <div class="metric">
        <div class="metric-name">Views</div>
        <div class="metric-value">{_fmt(m.get('views'))}{views_delta}</div>
      </div>
      <div class="metric">
        <div class="metric-name">Likes</div>
        <div class="metric-value">{_fmt(m.get('likes'))}{likes_delta}</div>
      </div>
      <div class="metric">
        <div class="metric-name">Comments</div>
        <div class="metric-value">{_fmt(m.get('comments'))}{comments_delta}</div>
      </div>
      <div class="metric">
        <div class="metric-name">Engagement</div>
        <div class="metric-value">{er_str}</div>
      </div>
      <div class="metric">
        <div class="metric-name">Shares</div>
        <div class="metric-value">{_fmt(m.get('shares'))}{shares_delta}</div>
      </div>
      <div class="metric">
        <div class="metric-name">Saves</div>
        <div class="metric-value">{_fmt(m.get('saves'))}</div>
      </div>
    </div>
    {error_html}
    <p class="card-collected">수집: {collected} UTC</p>
  </div>""")

    return "\n".join(cards)


def _build_timeseries_data(history: dict[str, list[dict]]) -> dict:
    """Build Chart.js-ready time series data."""
    reels = []
    for sc, records in history.items():
        if not records:
            continue
        label = records[0].get("label", sc)
        timestamps = [r["collected_at"][:16].replace("T", " ") for r in records]
        reels.append({
            "shortcode": sc,
            "label": label,
            "timestamps": timestamps,
            "views": [r.get("views") for r in records],
            "likes": [r.get("likes") for r in records],
            "comments": [r.get("comments") for r in records],
            "engagement_rate": [r.get("engagement_rate") for r in records],
        })
    return {"reels": reels}


def _build_comparison_data(latest_metrics: list[dict]) -> dict:
    """Build comparison bar chart data."""
    return {
        "labels": [m["label"] for m in latest_metrics],
        "shortcodes": [m["shortcode"] for m in latest_metrics],
        "data": [
            {
                "shortcode": m["shortcode"],
                "label": m["label"],
                "views": m.get("views") or 0,
                "likes": m.get("likes") or 0,
                "comments": m.get("comments") or 0,
                "shares": m.get("shares") or 0,
                "engagement_rate": m.get("engagement_rate") or 0,
            }
            for m in latest_metrics
        ],
    }
