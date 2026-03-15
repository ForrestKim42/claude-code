interface VerData {
  sessions: number;
  chatted: number;
  cta: number;
  phone: number;
  chatRate: number;
  ctaRate: number;
  convRate: number;
  phoneRate: number;
}

interface Versions {
  v1: VerData | null;
  v2: VerData | null;
  cutoffKst: string;
  minSamplesForComparison: number;
}

function RateCell({
  v1, v2, label, unit = '%',
}: { v1: number; v2: number; label: string; unit?: string }) {
  const diff = v2 - v1;
  const improved = diff > 0;
  const neutral = Math.abs(diff) < 0.5;
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-gray-500">{label}</span>
      <div className="flex items-baseline gap-2">
        <span className="text-base font-semibold text-white tabular-nums">
          {v2.toLocaleString('ko-KR')}{unit}
        </span>
        {!neutral && (
          <span className={`text-xs font-medium tabular-nums ${improved ? 'text-emerald-400' : 'text-red-400'}`}>
            {improved ? '▲' : '▼'} {Math.abs(diff).toFixed(1)}{unit}
          </span>
        )}
      </div>
      <span className="text-xs text-gray-600">v1: {v1.toLocaleString('ko-KR')}{unit}</span>
    </div>
  );
}

function InsufficientData({ sessions, min }: { sessions: number; min: number }) {
  const pct = Math.min(100, Math.round(sessions / min * 100));
  return (
    <div className="flex flex-col gap-2">
      <div className="text-sm text-gray-400">
        아직 비교 불가 — 최소 {min}세션 필요
      </div>
      <div className="flex items-center gap-3">
        <div className="flex-1 bg-gray-800 rounded-full h-2">
          <div
            className="h-2 rounded-full bg-purple-500 transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="text-xs text-gray-400 tabular-nums whitespace-nowrap">
          {sessions} / {min}건
        </span>
      </div>
      <p className="text-xs text-gray-600">
        {min - sessions}건 더 수집되면 v1과 전환율을 비교합니다
      </p>
    </div>
  );
}

export default function VersionComparison({ versions }: { versions: Versions }) {
  const { v1, v2, cutoffKst, minSamplesForComparison } = versions;
  const canCompare = (v2?.sessions ?? 0) >= minSamplesForComparison;

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 p-5">
      <div className="flex items-start justify-between mb-4 flex-wrap gap-2">
        <div>
          <h3 className="text-sm font-semibold text-white">콘텐츠 버전 비교</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            v2 시작: {cutoffKst} KST · 퍼널 DB 기준
          </p>
        </div>
        <div className="flex gap-2 text-xs">
          <span className="px-2 py-0.5 rounded-full bg-gray-800 text-gray-400">
            v1: {v1?.sessions.toLocaleString('ko-KR') ?? 0}세션
          </span>
          <span className="px-2 py-0.5 rounded-full bg-purple-900/50 text-purple-300">
            v2: {v2?.sessions.toLocaleString('ko-KR') ?? 0}세션
          </span>
        </div>
      </div>

      {!canCompare ? (
        <InsufficientData
          sessions={v2?.sessions ?? 0}
          min={minSamplesForComparison}
        />
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <RateCell
            v1={v1?.chatRate ?? 0}
            v2={v2?.chatRate ?? 0}
            label="채팅 시작율"
          />
          <RateCell
            v1={v1?.ctaRate ?? 0}
            v2={v2?.ctaRate ?? 0}
            label="채팅→CTA율"
          />
          <RateCell
            v1={v1?.convRate ?? 0}
            v2={v2?.convRate ?? 0}
            label="CTA→전화율"
          />
          <RateCell
            v1={v1?.phoneRate ?? 0}
            v2={v2?.phoneRate ?? 0}
            label="전체 전환율"
          />
        </div>
      )}
    </div>
  );
}
