import { NextResponse } from 'next/server';
import path from 'path';

const COST_PER_REEL = 40_000;

// v2 시작: config.yaml chat_versions v2 start_kst "2026-03-15 16:20:00" → UTC
const V2_START_UTC = '2026-03-15 07:20:00+00';
const V2_START_KST = '2026-03-15 16:20';

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

function cpx(cost: number, n: number): number | null {
  return n > 0 ? Math.round(cost / n) : null;
}

function pct(a: number, b: number): number {
  return b > 0 ? Math.round(a / b * 1000) / 10 : 0;
}

// ── Main handler ────────────────────────────────────────────────────
export async function GET() {
  const codes = Object.keys(ACCOUNTS);
  const codesIn = codes.map(c => `'${c}'`).join(',');

  const [reelRows, funnelRows, todayRows, trendRows, versionRows, chatDistRows] =
    await Promise.all([
      // SQLite
      Promise.resolve().then(() => { try { return getReelMetrics(); } catch { return []; } }),

      // 계정별 누적 퍼널
      queryNeon(`
        SELECT referral_code,
          COUNT(*)                                        AS sessions,
          COUNT(*) FILTER (WHERE chat_count > 0)         AS chatted,
          COUNT(*) FILTER (WHERE chat_count = 3)         AS reached_cta,
          COUNT(*) FILTER (WHERE phone_submitted)        AS phone_sub,
          MAX(created_at)                                AS latest_session_at
        FROM landing_page_sessions
        WHERE referral_code IN (${codesIn})
        GROUP BY referral_code
      `),

      // 오늘 / 어제 (KST 기준)
      queryNeon(`
        SELECT
          COUNT(*) FILTER (
            WHERE (created_at AT TIME ZONE 'Asia/Seoul')::date
                = (NOW() AT TIME ZONE 'Asia/Seoul')::date
          )                                              AS today_sessions,
          COUNT(*) FILTER (
            WHERE (created_at AT TIME ZONE 'Asia/Seoul')::date
                = (NOW() AT TIME ZONE 'Asia/Seoul')::date - 1
          )                                              AS yesterday_sessions,
          COUNT(*) FILTER (
            WHERE phone_submitted
              AND (created_at AT TIME ZONE 'Asia/Seoul')::date
                = (NOW() AT TIME ZONE 'Asia/Seoul')::date
          )                                              AS today_phone,
          COUNT(*) FILTER (
            WHERE phone_submitted
              AND (created_at AT TIME ZONE 'Asia/Seoul')::date
                = (NOW() AT TIME ZONE 'Asia/Seoul')::date - 1
          )                                              AS yesterday_phone
        FROM landing_page_sessions
        WHERE referral_code IN (${codesIn})
      `),

      // 일별 추이 — 최근 14일, KST 날짜
      queryNeon(`
        SELECT
          (created_at AT TIME ZONE 'Asia/Seoul')::date   AS kst_date,
          referral_code,
          COUNT(*)                                        AS sessions,
          COUNT(*) FILTER (WHERE phone_submitted)        AS phone_sub
        FROM landing_page_sessions
        WHERE referral_code IN (${codesIn})
          AND created_at >= NOW() - INTERVAL '14 days'
        GROUP BY kst_date, referral_code
        ORDER BY kst_date
      `),

      // v1 vs v2
      queryNeon(`
        SELECT
          CASE WHEN created_at < '${V2_START_UTC}' THEN 'v1' ELSE 'v2' END AS version,
          COUNT(*)                                        AS sessions,
          COUNT(*) FILTER (WHERE chat_count > 0)         AS chatted,
          COUNT(*) FILTER (WHERE chat_count = 3)         AS cta,
          COUNT(*) FILTER (WHERE phone_submitted)        AS phone_sub
        FROM landing_page_sessions
        WHERE referral_code IN (${codesIn})
        GROUP BY version
        ORDER BY version
      `),

      // chat_count 분포 (0/1/2/3 단계별)
      queryNeon(`
        SELECT referral_code, chat_count, COUNT(*) AS cnt
        FROM landing_page_sessions
        WHERE referral_code IN (${codesIn})
        GROUP BY referral_code, chat_count
        ORDER BY referral_code, chat_count
      `),
    ]);

  // ── 계정별 누적 퍼널 ──────────────────────────────────────────────
  const reelByCode = Object.fromEntries(reelRows.map(r => [r.owner_username, r]));
  const funnelByCode = Object.fromEntries(funnelRows.map(r => [r.referral_code as string, r]));

  const rows = codes.map(code => {
    const reel = reelByCode[code];
    const f = funnelByCode[code];
    const views    = reel?.views ?? 0;
    const sessions = Number(f?.sessions ?? 0);
    const chatted  = Number(f?.chatted ?? 0);
    const cta      = Number(f?.reached_cta ?? 0);
    const phone    = Number(f?.phone_sub ?? 0);
    return {
      code,
      name: reel?.owner_name ?? ACCOUNTS[code],
      views, plays: reel?.plays ?? 0, likes: reel?.likes ?? 0,
      sessions, chatted, cta, phone,
      ctr: views > 0 ? Math.round(sessions / views * 10000) / 100 : 0,
      // 퍼널 전환율
      sessionToChat: pct(chatted, sessions),
      chatToCta:     pct(cta, chatted),
      ctaToPhone:    pct(phone, cta),
      // 비용
      cpv:  cpx(COST_PER_REEL, views),
      cps:  cpx(COST_PER_REEL, sessions),
      cpc:  cpx(COST_PER_REEL, chatted),
      cpca: cpx(COST_PER_REEL, cta),
      cpph: cpx(COST_PER_REEL, phone),
      reelCollectedAt: reel?.collected_at ?? null,
      latestSessionAt: f?.latest_session_at ?? null,
    };
  });

  const totalCost = COST_PER_REEL * rows.length;
  const tv = rows.reduce((s, r) => s + r.views, 0);
  const ts = rows.reduce((s, r) => s + r.sessions, 0);
  const tc = rows.reduce((s, r) => s + r.chatted, 0);
  const tt = rows.reduce((s, r) => s + r.cta, 0);
  const tp = rows.reduce((s, r) => s + r.phone, 0);
  const total = {
    cost: totalCost, views: tv, sessions: ts, chatted: tc, cta: tt, phone: tp,
    cpv:  cpx(totalCost, tv),
    cps:  cpx(totalCost, ts),
    cpc:  cpx(totalCost, tc),
    cpca: cpx(totalCost, tt),
    cpph: cpx(totalCost, tp),
  };

  // ── 오늘/어제 ─────────────────────────────────────────────────────
  const t = todayRows[0] ?? {};
  const today = {
    sessions:          Number(t.today_sessions ?? 0),
    phone:             Number(t.today_phone ?? 0),
    sessionsYesterday: Number(t.yesterday_sessions ?? 0),
    phoneYesterday:    Number(t.yesterday_phone ?? 0),
  };

  // ── 일별 추이 ─────────────────────────────────────────────────────
  // 최근 14일 날짜 배열 생성 (KST 오늘 기준)
  const todayKst = new Date(
    new Date().toLocaleString('en-US', { timeZone: 'Asia/Seoul' })
  );
  const dates: string[] = [];
  for (let i = 13; i >= 0; i--) {
    const d = new Date(todayKst);
    d.setDate(d.getDate() - i);
    dates.push(d.toISOString().slice(0, 10));
  }

  // trendRows를 { date → code → {sessions, phone} } 로 인덱싱
  const trendIndex: Record<string, Record<string, { sessions: number; phone: number }>> = {};
  for (const r of trendRows) {
    const date = String(r.kst_date).slice(0, 10);
    const code = r.referral_code as string;
    if (!trendIndex[date]) trendIndex[date] = {};
    trendIndex[date][code] = {
      sessions: Number(r.sessions),
      phone: Number(r.phone_sub),
    };
  }

  // 날짜 × 계정 행렬로 변환
  const trendByAccount: Record<string, { sessions: number[]; phone: number[] }> = {};
  for (const code of codes) {
    trendByAccount[code] = { sessions: [], phone: [] };
  }
  const trendTotal = { sessions: [] as number[], phone: [] as number[] };

  for (const date of dates) {
    let totalS = 0, totalP = 0;
    for (const code of codes) {
      const v = trendIndex[date]?.[code] ?? { sessions: 0, phone: 0 };
      trendByAccount[code].sessions.push(v.sessions);
      trendByAccount[code].phone.push(v.phone);
      totalS += v.sessions;
      totalP += v.phone;
    }
    trendTotal.sessions.push(totalS);
    trendTotal.phone.push(totalP);
  }

  const trend = { dates, total: trendTotal, byAccount: trendByAccount, v2StartKst: V2_START_KST };

  // ── v1 vs v2 ─────────────────────────────────────────────────────
  const vMap: Record<string, Record<string, unknown>> = {};
  for (const r of versionRows) vMap[r.version as string] = r;

  const buildVer = (r: Record<string, unknown> | undefined) => {
    if (!r) return null;
    const s = Number(r.sessions ?? 0);
    const c = Number(r.chatted ?? 0);
    const a = Number(r.cta ?? 0);
    const p = Number(r.phone_sub ?? 0);
    return { sessions: s, chatted: c, cta: a, phone: p,
      chatRate: pct(c, s), ctaRate: pct(a, c), convRate: pct(p, a), phoneRate: pct(p, s) };
  };

  const versions = {
    v1: buildVer(vMap['v1']),
    v2: buildVer(vMap['v2']),
    cutoffKst: V2_START_KST,
    minSamplesForComparison: 50,
  };

  // ── chat_count 분포 ───────────────────────────────────────────────
  const chatDist: Record<string, number[]> = {};
  for (const code of codes) chatDist[code] = [0, 0, 0, 0]; // index = chat_count 0~3
  for (const r of chatDistRows) {
    const code = r.referral_code as string;
    const step = Math.min(Number(r.chat_count), 3);
    if (chatDist[code]) chatDist[code][step] = Number(r.cnt);
  }

  // ── 이상 감지 알림 ─────────────────────────────────────────────────
  type Alert = { type: 'error' | 'warning'; message: string };
  const alerts: Alert[] = [];

  // 릴스 데이터 오래됨
  const reelCollectedAt = reelRows[0]?.collected_at ?? null;
  if (reelCollectedAt) {
    const ageMs = Date.now() - new Date(reelCollectedAt).getTime();
    const ageH = Math.floor(ageMs / 3_600_000);
    if (ageH >= 12) {
      alerts.push({ type: 'warning', message: `릴스 지표가 ${ageH}시간 전 수집 데이터입니다 (Instagram 수집 차단 중)` });
    }
  }

  // CTA 도달 후 전화 0건
  for (const row of rows) {
    if (row.cta >= 5 && row.phone === 0) {
      alerts.push({ type: 'error', message: `@${row.code} — CTA 도달 ${row.cta}건이지만 전화 제출 0건: UI 버그 의심` });
    }
  }

  // 오늘 전화 급감
  if (today.phoneYesterday >= 3 && today.phone === 0) {
    alerts.push({ type: 'warning', message: `오늘 전화 제출 0건 (어제 ${today.phoneYesterday}건 대비 급감)` });
  }

  return NextResponse.json({
    rows, total, today, trend, versions, chatDist, alerts,
    reelCollectedAt,
    fetchedAt: new Date().toISOString(),
  });
}
