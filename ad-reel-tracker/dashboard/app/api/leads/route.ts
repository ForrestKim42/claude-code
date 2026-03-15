import { NextResponse } from 'next/server';

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

export async function GET() {
  // 1) 테이블 컬럼 목록 조회
  const columns = await queryNeon(`
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'landing_page_sessions'
    ORDER BY ordinal_position
  `);

  // 2) phone_submitted = true 인 세션 전체 조회 (최신순)
  const sessions = await queryNeon(`
    SELECT *
    FROM landing_page_sessions
    WHERE phone_submitted = true
    ORDER BY created_at DESC
  `);

  return NextResponse.json({ columns, sessions });
}
