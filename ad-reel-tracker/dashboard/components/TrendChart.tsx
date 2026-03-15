'use client';

import { useState, useMemo } from 'react';
import {
  ResponsiveContainer, ComposedChart, Bar, Line,
  XAxis, YAxis, Tooltip, Legend, ReferenceLine, CartesianGrid,
} from 'recharts';

const ACCOUNT_COLORS: Record<string, string> = {
  'xeo.yuunny':    '#818cf8',
  'ha_n_a0.6':     '#34d399',
  'esther_ffff':   '#fb923c',
  'thinxoyoon':    '#f472b6',
  'caiime_pretty': '#facc15',
};

const ACCOUNT_NAMES: Record<string, string> = {
  'xeo.yuunny':    '서윤',
  'ha_n_a0.6':     '하나',
  'esther_ffff':   '에스더',
  'thinxoyoon':    '신소윤',
  'caiime_pretty': '지여닝',
};

interface Trend {
  dates: string[];
  total: { sessions: number[]; phone: number[] };
  byAccount: Record<string, { sessions: number[]; phone: number[] }>;
  v2StartKst: string; // 'YYYY-MM-DD HH:MM'
}

function fmtDate(iso: string) {
  const d = new Date(iso + 'T00:00:00');
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-xs shadow-xl">
      <div className="text-gray-400 mb-1 font-medium">{label}</div>
      {payload.map((p: { name: string; value: number; color: string }, i: number) => (
        <div key={i} className="flex items-center gap-2 py-0.5">
          <span style={{ color: p.color }} className="font-semibold">{p.name}</span>
          <span className="text-white tabular-nums">{p.value.toLocaleString('ko-KR')}</span>
        </div>
      ))}
    </div>
  );
}

export default function TrendChart({ trend }: { trend: Trend }) {
  const codes = Object.keys(ACCOUNT_NAMES);
  const [mode, setMode] = useState<'total' | string>('total');

  // v2 기준선 날짜 ('YYYY-MM-DD')
  const v2Date = trend.v2StartKst.slice(0, 10);

  const chartData = useMemo(() => {
    return trend.dates.map((date, i) => {
      const row: Record<string, string | number> = { date: fmtDate(date), rawDate: date };
      if (mode === 'total') {
        row['세션'] = trend.total.sessions[i];
        row['전화 제출'] = trend.total.phone[i];
      } else {
        const acc = trend.byAccount[mode];
        row['세션'] = acc?.sessions[i] ?? 0;
        row['전화 제출'] = acc?.phone[i] ?? 0;
      }
      return row;
    });
  }, [trend, mode]);

  // v2 기준선이 현재 날짜 범위 안에 있는지
  const v2InRange = trend.dates.includes(v2Date);
  const v2Label = fmtDate(v2Date);

  const hasAnyData = chartData.some(d => (d['세션'] as number) > 0);

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 p-5">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div>
          <h3 className="text-sm font-semibold text-white">일별 캠페인 트렌드</h3>
          <p className="text-xs text-gray-500 mt-0.5">최근 14일 · 퍼널 DB 기준</p>
        </div>

        {/* 계정 토글 */}
        <div className="flex flex-wrap gap-1.5">
          <button
            onClick={() => setMode('total')}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              mode === 'total'
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:text-white'
            }`}
          >
            전체
          </button>
          {codes.map(code => (
            <button
              key={code}
              onClick={() => setMode(code)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                mode === code
                  ? 'text-white'
                  : 'bg-gray-800 text-gray-400 hover:text-white'
              }`}
              style={mode === code ? { backgroundColor: ACCOUNT_COLORS[code] } : {}}
            >
              {ACCOUNT_NAMES[code]}
            </button>
          ))}
        </div>
      </div>

      {/* 차트 */}
      {!hasAnyData ? (
        <div className="flex items-center justify-center h-40 text-gray-600 text-sm">
          해당 기간 데이터 없음
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <ComposedChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -10 }}>
            <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="date"
              tick={{ fill: '#6b7280', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              yAxisId="left"
              tick={{ fill: '#6b7280', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={{ fill: '#6b7280', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={30}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
            <Legend
              wrapperStyle={{ fontSize: '11px', color: '#9ca3af', paddingTop: '8px' }}
            />

            {/* v2 기준선 */}
            {v2InRange && (
              <ReferenceLine
                yAxisId="left"
                x={v2Label}
                stroke="#a78bfa"
                strokeDasharray="4 3"
                label={{ value: 'v2 시작', position: 'insideTopRight', fill: '#a78bfa', fontSize: 10 }}
              />
            )}

            <Bar
              yAxisId="left"
              dataKey="세션"
              fill={mode === 'total' ? '#3b82f6' : ACCOUNT_COLORS[mode] ?? '#3b82f6'}
              opacity={0.7}
              radius={[2, 2, 0, 0]}
              maxBarSize={32}
            />
            <Line
              yAxisId="right"
              dataKey="전화 제출"
              stroke="#f43f5e"
              strokeWidth={2}
              dot={{ fill: '#f43f5e', r: 3 }}
              activeDot={{ r: 5 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      )}

      {/* v2 기준선 레전드 */}
      {v2InRange && (
        <div className="mt-2 flex items-center gap-1.5 text-xs text-purple-400/70">
          <span className="inline-block w-4 border-t border-dashed border-purple-400/70" />
          v2 콘텐츠 업데이트 ({trend.v2StartKst} KST)
        </div>
      )}
    </div>
  );
}
