interface Today {
  sessions: number;
  phone: number;
  sessionsYesterday: number;
  phoneYesterday: number;
}

interface Total {
  cost: number;
  views: number;
  sessions: number;
  phone: number;
  cpph: number | null;
}

function delta(today: number, yesterday: number) {
  if (yesterday === 0) return null;
  const diff = today - yesterday;
  const sign = diff >= 0 ? '+' : '';
  const color = diff >= 0 ? 'text-emerald-400' : 'text-red-400';
  return <span className={`text-xs ml-1 ${color}`}>{sign}{diff} 어제 대비</span>;
}

function ReelCard({ views, collectedAt }: { views: number; collectedAt: string | null }) {
  const ageH = collectedAt
    ? Math.floor((Date.now() - new Date(collectedAt).getTime()) / 3_600_000)
    : null;
  const isStale = ageH !== null && ageH >= 6;

  return (
    <div className={`rounded-xl border px-5 py-4 ${isStale ? 'border-amber-800/60 bg-amber-950/20' : 'border-gray-800 bg-gray-900'}`}>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-gray-500">총 뷰 (릴스)</span>
        {isStale && (
          <span className="text-xs text-amber-500 flex items-center gap-1">
            ⚠ {ageH}h 전 수집
          </span>
        )}
      </div>
      <div className="text-2xl font-bold text-white">{views.toLocaleString('ko-KR')}</div>
      <div className="text-xs text-gray-600 mt-0.5">
        {collectedAt
          ? `수집: ${new Date(collectedAt).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })} KST`
          : '수집 정보 없음'}
      </div>
    </div>
  );
}

function MetricCard({
  label, value, sub, today, yesterday,
}: {
  label: string; value: string; sub?: string;
  today?: number; yesterday?: number;
}) {
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 px-5 py-4">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-2xl font-bold text-white">{value}</div>
      {(today !== undefined && yesterday !== undefined) && (
        <div className="text-xs text-gray-400 mt-0.5">
          오늘 +{today}건{delta(today, yesterday)}
        </div>
      )}
      {sub && !today && <div className="text-xs text-gray-500 mt-0.5">{sub}</div>}
    </div>
  );
}

export default function SummaryCards({
  total, today, reelCollectedAt,
}: {
  total: Total;
  today: Today;
  reelCollectedAt: string | null;
}) {
  return (
    <div className="space-y-2">
      {/* 구분 레이블 */}
      <div className="flex items-center gap-6">
        <span className="text-xs text-amber-600/80 font-medium tracking-wider uppercase">
          릴스 지표 — 스냅샷
        </span>
        <div className="flex-1 border-t border-gray-800/60" />
        <span className="text-xs text-emerald-600/80 font-medium tracking-wider uppercase">
          퍼널 지표 — 실시간
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* 릴스 (스냅샷) */}
        <ReelCard views={total.views} collectedAt={reelCollectedAt} />

        {/* 퍼널 (실시간) */}
        <MetricCard
          label="오늘 세션"
          value={`+${today.sessions}건`}
          today={today.sessions}
          yesterday={today.sessionsYesterday}
        />
        <MetricCard
          label="오늘 전화 제출"
          value={`+${today.phone}건`}
          today={today.phone}
          yesterday={today.phoneYesterday}
        />
        <MetricCard
          label="누적 세션"
          value={total.sessions.toLocaleString('ko-KR')}
          sub="캠페인 전체"
        />
        <MetricCard
          label="누적 전화 제출"
          value={`${total.phone}건`}
          sub="캠페인 전체"
        />
        <MetricCard
          label="평균 CP-Lead"
          value={total.cpph != null ? `${total.cpph.toLocaleString('ko-KR')}원` : '—'}
          sub="전화 제출 1건당"
        />
      </div>
    </div>
  );
}
