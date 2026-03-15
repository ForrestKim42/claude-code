import { fmtCost } from '@/lib/fmt';

interface Row {
  code: string; name: string;
  views: number; sessions: number; ctr: number;
  chatted: number; cta: number; phone: number;
  cpv: number | null; cps: number | null;
  cpc: number | null; cpca: number | null; cpph: number | null;
}

interface Total {
  views: number; sessions: number; chatted: number; cta: number; phone: number;
  cpv: number | null; cps: number | null; cpc: number | null;
  cpca: number | null; cpph: number | null;
}

// Color: green (best) → yellow → red (worst) relative to column min/max
function costColor(val: number | null, min: number | null, max: number | null): string {
  if (val === null || min === null || max === null || min === max) return 'text-gray-300';
  const ratio = (val - min) / (max - min); // 0 = best, 1 = worst
  if (ratio < 0.25) return 'text-emerald-400 font-semibold';
  if (ratio < 0.6)  return 'text-yellow-400';
  return 'text-red-400';
}

function CostCell({ val, min, max }: { val: number | null; min: number | null; max: number | null }) {
  if (val === null) return <td className="px-3 py-3 text-center text-red-400">∞</td>;
  const cls = costColor(val, min, max);
  return (
    <td className={`px-3 py-3 text-right tabular-nums ${cls}`}>
      {fmtCost(val)}
    </td>
  );
}

export default function CostTable({ rows, total }: { rows: Row[]; total: Total }) {
  const cols = ['cpv', 'cps', 'cpc', 'cpca', 'cpph'] as const;
  type ColKey = typeof cols[number];

  const mins: Record<ColKey, number | null> = {} as never;
  const maxs: Record<ColKey, number | null> = {} as never;
  for (const col of cols) {
    const vals = rows.map(r => r[col]).filter((v): v is number => v !== null);
    mins[col] = vals.length ? Math.min(...vals) : null;
    maxs[col] = vals.length ? Math.max(...vals) : null;
  }

  const fmt = (n: number) => n.toLocaleString('ko-KR');

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-800">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-800 bg-gray-900/60 text-xs text-gray-400 uppercase tracking-wide">
            <th className="px-4 py-3 text-left">계정</th>
            <th className="px-3 py-3 text-right">Views</th>
            <th className="px-3 py-3 text-right">세션</th>
            <th className="px-3 py-3 text-right">CTR</th>
            <th className="px-3 py-3 text-right">CPV<br /><span className="text-gray-600 normal-case">뷰당</span></th>
            <th className="px-3 py-3 text-right">CPS<br /><span className="text-gray-600 normal-case">세션당</span></th>
            <th className="px-3 py-3 text-right">CP-Chat<br /><span className="text-gray-600 normal-case">채팅당</span></th>
            <th className="px-3 py-3 text-right">CP-CTA<br /><span className="text-gray-600 normal-case">CTA당</span></th>
            <th className="px-3 py-3 text-right">CP-Lead<br /><span className="text-gray-600 normal-case">전화당</span></th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.code} className="border-b border-gray-800/60 hover:bg-gray-800/30 transition-colors">
              <td className="px-4 py-3">
                <div className="font-medium text-white">{r.name}</div>
                <div className="text-xs text-gray-500">@{r.code}</div>
              </td>
              <td className="px-3 py-3 text-right text-gray-300 tabular-nums">{fmt(r.views)}</td>
              <td className="px-3 py-3 text-right text-gray-300 tabular-nums">{fmt(r.sessions)}</td>
              <td className="px-3 py-3 text-right text-gray-300 tabular-nums">{r.ctr}%</td>
              <CostCell val={r.cpv}  min={mins.cpv}  max={maxs.cpv}  />
              <CostCell val={r.cps}  min={mins.cps}  max={maxs.cps}  />
              <CostCell val={r.cpc}  min={mins.cpc}  max={maxs.cpc}  />
              <CostCell val={r.cpca} min={mins.cpca} max={maxs.cpca} />
              <CostCell val={r.cpph} min={mins.cpph} max={maxs.cpph} />
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="bg-gray-900/80 text-xs border-t-2 border-gray-700">
            <td className="px-4 py-3 font-semibold text-gray-300">전체 합계</td>
            <td className="px-3 py-3 text-right text-gray-300 tabular-nums">{fmt(total.views)}</td>
            <td className="px-3 py-3 text-right text-gray-300 tabular-nums">{fmt(total.sessions)}</td>
            <td className="px-3 py-3 text-right text-gray-500">—</td>
            <CostCell val={total.cpv}  min={null} max={null} />
            <CostCell val={total.cps}  min={null} max={null} />
            <CostCell val={total.cpc}  min={null} max={null} />
            <CostCell val={total.cpca} min={null} max={null} />
            <CostCell val={total.cpph} min={null} max={null} />
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
