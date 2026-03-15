'use client';

import useSWR from 'swr';
import Header from '@/components/Header';
import AlertBanner from '@/components/AlertBanner';
import SummaryCards from '@/components/SummaryCards';
import CostTable from '@/components/CostTable';
import FunnelCards from '@/components/FunnelCards';
import TrendChart from '@/components/TrendChart';
import VersionComparison from '@/components/VersionComparison';

const REFRESH_INTERVAL = 30_000;

interface VerData {
  sessions: number; chatted: number; cta: number; phone: number;
  chatRate: number; ctaRate: number; convRate: number; phoneRate: number;
}

interface DashboardData {
  rows: {
    code: string; name: string;
    views: number; plays: number; likes: number;
    sessions: number; chatted: number; cta: number; phone: number;
    ctr: number; sessionToChat: number; chatToCta: number; ctaToPhone: number;
    cpv: number | null; cps: number | null;
    cpc: number | null; cpca: number | null; cpph: number | null;
    reelCollectedAt: string | null;
    latestSessionAt: string | null;
  }[];
  total: {
    cost: number; views: number; sessions: number;
    chatted: number; cta: number; phone: number;
    cpv: number | null; cps: number | null; cpc: number | null;
    cpca: number | null; cpph: number | null;
  };
  today: {
    sessions: number; phone: number;
    sessionsYesterday: number; phoneYesterday: number;
  };
  trend: {
    dates: string[];
    total: { sessions: number[]; phone: number[] };
    byAccount: Record<string, { sessions: number[]; phone: number[] }>;
    v2StartKst: string;
  };
  versions: {
    v1: VerData | null; v2: VerData | null;
    cutoffKst: string; minSamplesForComparison: number;
  };
  alerts: { type: 'error' | 'warning'; message: string }[];
  reelCollectedAt: string | null;
  fetchedAt: string;
}

const fetcher = (url: string) => fetch(url).then(r => r.json());

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
      {children}
    </h2>
  );
}

export default function Dashboard() {
  const { data, error, isLoading, mutate } = useSWR<DashboardData>(
    '/api/dashboard',
    fetcher,
    { refreshInterval: REFRESH_INTERVAL, revalidateOnFocus: false }
  );

  return (
    <div className="min-h-screen flex flex-col">
      <Header
        fetchedAt={data?.fetchedAt ?? null}
        isLoading={isLoading}
        onRefresh={() => mutate()}
        refreshInterval={REFRESH_INTERVAL}
      />

      <main className="flex-1 px-4 md:px-6 py-6 space-y-8 max-w-screen-2xl mx-auto w-full">

        {/* 에러 */}
        {error && (
          <div className="rounded-lg bg-red-900/30 border border-red-800 px-4 py-3 text-sm text-red-400">
            데이터를 불러오지 못했습니다. 잠시 후 자동으로 재시도합니다.
          </div>
        )}

        {/* 로딩 */}
        {!data && isLoading && (
          <div className="flex items-center justify-center h-64 text-gray-500 text-sm">
            데이터 불러오는 중…
          </div>
        )}

        {data && (
          <>
            {/* Zone 1 — 이상 감지 + 요약 */}
            <section className="space-y-4">
              <AlertBanner alerts={data.alerts} />
              <SummaryCards
                total={data.total}
                today={data.today}
                reelCollectedAt={data.reelCollectedAt}
              />
            </section>

            {/* Zone 2 — 비용 효율 + 퍼널 */}
            <section>
              <SectionLabel>
                비용 효율 — 릴스당 40,000원
                <span className="ml-2 text-gray-600 normal-case font-normal">
                  초록 = 최저비용 · 빨강 = 최고비용
                </span>
              </SectionLabel>
              <CostTable rows={data.rows} total={data.total} />
            </section>

            <section>
              <SectionLabel>계정별 퍼널</SectionLabel>
              <FunnelCards rows={data.rows} />
            </section>

            {/* Zone 3 & 4 — 트렌드 + 버전 비교 */}
            <section className="grid grid-cols-1 xl:grid-cols-2 gap-4">
              <div>
                <SectionLabel>캠페인 트렌드</SectionLabel>
                <TrendChart trend={data.trend} />
              </div>
              <div>
                <SectionLabel>v1 vs v2 콘텐츠 비교</SectionLabel>
                <VersionComparison versions={data.versions} />
              </div>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
