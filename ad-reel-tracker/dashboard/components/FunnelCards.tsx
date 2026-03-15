interface Row {
  code: string; name: string;
  views: number; sessions: number; chatted: number; cta: number; phone: number;
  ctr: number; cpph: number | null;
  latestSessionAt: string | null;
}

function Bar({ ratio, color }: { ratio: number; color: string }) {
  return (
    <div className="w-full bg-gray-800 rounded-full h-1.5 mt-1">
      <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${Math.min(100, ratio * 100)}%` }} />
    </div>
  );
}

function Stage({
  label, value, base, color, cost,
}: { label: string; value: number; base: number; color: string; cost?: number | null }) {
  const ratio = base > 0 ? value / base : 0;
  const pct = (ratio * 100).toFixed(1);
  return (
    <div className="mb-3">
      <div className="flex justify-between items-baseline mb-0.5">
        <span className="text-xs text-gray-400">{label}</span>
        <div className="text-right">
          <span className="text-sm font-semibold text-white tabular-nums">
            {value.toLocaleString('ko-KR')}
          </span>
          {base > 0 && value !== base && (
            <span className="text-xs text-gray-500 ml-1">({pct}%)</span>
          )}
        </div>
      </div>
      <Bar ratio={ratio} color={color} />
      {cost != null && (
        <div className="text-right text-xs text-indigo-400 mt-0.5">
          {cost.toLocaleString('ko-KR')}원/건
        </div>
      )}
    </div>
  );
}

export default function FunnelCards({ rows }: { rows: Row[] }) {
  const maxViews = Math.max(...rows.map(r => r.views), 1);

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
      {rows.map(r => {
        const isPhoneBug = r.cta > 0 && r.phone === 0;
        return (
          <div
            key={r.code}
            className="bg-gray-900 rounded-xl border border-gray-800 p-4 flex flex-col gap-1"
          >
            {/* Header */}
            <div className="mb-3">
              <div className="font-semibold text-white">{r.name}</div>
              <div className="text-xs text-gray-500">@{r.code}</div>
              {r.latestSessionAt && (
                <div className="text-xs text-gray-600 mt-0.5">
                  최신 세션:{' '}
                  {new Date(r.latestSessionAt).toLocaleString('ko-KR', {
                    timeZone: 'Asia/Seoul',
                    month: 'numeric', day: 'numeric',
                    hour: '2-digit', minute: '2-digit',
                  })}
                </div>
              )}
            </div>

            {/* Funnel stages */}
            <Stage label="뷰" value={r.views} base={maxViews} color="bg-blue-500" />
            <Stage label="세션 (CTR)" value={r.sessions} base={r.views} color="bg-indigo-500" />
            <Stage label="채팅 시작" value={r.chatted} base={r.sessions} color="bg-violet-500" />
            <Stage label="CTA 도달" value={r.cta} base={r.chatted} color="bg-purple-500" />
            <Stage
              label="전화 제출"
              value={r.phone}
              base={r.cta}
              color={isPhoneBug ? 'bg-red-500' : 'bg-rose-500'}
              cost={r.cpph}
            />

            {/* Badge */}
            <div className="mt-2 pt-2 border-t border-gray-800 flex items-center justify-between">
              <span className="text-xs text-gray-500">CTR</span>
              <span className="text-xs font-medium text-gray-300">{r.ctr}%</span>
            </div>

            {isPhoneBug && (
              <div className="text-xs bg-red-900/40 text-red-400 rounded px-2 py-1 mt-1">
                ⚠ CTA 도달 후 전화 제출 0건 — UI 버그 의심
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
