import { NextResponse } from 'next/server';
import path from 'path';

const COST_PER_REEL = 40_000;

const ACCOUNTS: Record<string, string> = {
  'xeo.yuunny': '서윤',
  'ha_n_a0.6': '하나',
  'esther_ffff': '에스더',
  'thinxoyoon': '신소윤',
  'caiime_pretty': '지여닝',
};

// ── SQLite ──────────────────────────────────────────────────────────
function getReelMetrics() {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const Database = require('better-sqlite3');
  const dbPath = path.join(process.cwd(), '..', 'data', 'reels.db');
  const db = new Database(dbPath, { readonly: true });

  const rows = db.prepare(`
    SELECT owner_username, owner_name, label, views, plays, likes, comments,
           collected_at, error
    FROM reel_metrics
    WHERE id IN (
      SELECT MAX(id) FROM reel_metrics
      WHERE error IS NULL
      GROUP BY shortcode
    )
    ORDER BY views DESC
  `).all() as {
    owner_username: string; owner_name: string; label: string;
    views: number; plays: number; likes: number; comments: number;
    collected_at: string; error: string | null;
  }[];

  db.close();
  return rows;
}

// ── Neon HTTP ───────────────────────────────────────────────────────
async function queryNeon(sql: string): Promise<Record<string, unknown>[]> {
  const connStr = process.env.NEON_CONNECTION_STRING;
  if (!connStr) return [];
  const host = connStr.split('@')[1].split('/')[0];
  const res = await fetch(`https://${host}/sql`, {
    method: 'POST',
    headers: { 'Neon-Connection-String': connStr, 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: sql, params: [] }),
    cache: 'no-store',
  });
  const data = await res.json() as { rows: Record<string, unknown>[] };
  return data.rows ?? [];
}

// ── Cost calculation ────────────────────────────────────────────────
function cpx(cost: number, n: number): number | null {
  return n > 0 ? Math.round(cost / n) : null;
}

// ── Main handler ────────────────────────────────────────────────────
export async function GET() {
  const codes = Object.keys(ACCOUNTS);
  const codesIn = codes.map(c => `'${c}'`).join(',');

  // Run SQLite + Neon in parallel
  const [reelRows, funnelRows] = await Promise.all([
    Promise.resolve().then(() => {
      try { return getReelMetrics(); }
      catch { return []; }
    }),
    queryNeon(`
      SELECT referral_code,
        COUNT(*)                                            AS sessions,
        COUNT(*) FILTER (WHERE chat_count > 0)             AS chatted,
        COUNT(*) FILTER (WHERE chat_count = 3)             AS reached_cta,
        COUNT(*) FILTER (WHERE phone_submitted)            AS phone_sub,
        MAX(created_at)                                    AS latest_session_at
      FROM landing_page_sessions
      WHERE referral_code IN (${codesIn})
      GROUP BY referral_code
    `),
  ]);

  // Index reel metrics by username
  const reelByCode = Object.fromEntries(
    reelRows.map(r => [r.owner_username, r])
  );

  // Index funnel by referral_code
  const funnelByCode = Object.fromEntries(
    funnelRows.map(r => [r.referral_code as string, r])
  );

  // Build unified rows
  const rows = codes.map(code => {
    const reel = reelByCode[code];
    const f = funnelByCode[code];
    const views = reel?.views ?? 0;
    const sessions = Number(f?.sessions ?? 0);
    const chatted  = Number(f?.chatted ?? 0);
    const cta      = Number(f?.reached_cta ?? 0);
    const phone    = Number(f?.phone_sub ?? 0);
    return {
      code,
      name: reel?.owner_name ?? ACCOUNTS[code],
      views,
      plays: reel?.plays ?? 0,
      likes: reel?.likes ?? 0,
      sessions,
      chatted,
      cta,
      phone,
      ctr: views > 0 ? Math.round(sessions / views * 10000) / 100 : 0,
      cpv:  cpx(COST_PER_REEL, views),
      cps:  cpx(COST_PER_REEL, sessions),
      cpc:  cpx(COST_PER_REEL, chatted),
      cpca: cpx(COST_PER_REEL, cta),
      cpph: cpx(COST_PER_REEL, phone),
      reelCollectedAt: reel?.collected_at ?? null,
      latestSessionAt: f?.latest_session_at ?? null,
    };
  });

  // Totals
  const totalCost = COST_PER_REEL * rows.length;
  const tv = rows.reduce((s, r) => s + r.views, 0);
  const ts = rows.reduce((s, r) => s + r.sessions, 0);
  const tc = rows.reduce((s, r) => s + r.chatted, 0);
  const tt = rows.reduce((s, r) => s + r.cta, 0);
  const tp = rows.reduce((s, r) => s + r.phone, 0);

  const total = {
    cost: totalCost,
    views: tv, sessions: ts, chatted: tc, cta: tt, phone: tp,
    cpv:  cpx(totalCost, tv),
    cps:  cpx(totalCost, ts),
    cpc:  cpx(totalCost, tc),
    cpca: cpx(totalCost, tt),
    cpph: cpx(totalCost, tp),
  };

  return NextResponse.json({ rows, total, fetchedAt: new Date().toISOString() });
}
