'use client';

import useSWR from 'swr';
import Header from '@/components/Header';
import SummaryCards from '@/components/SummaryCards';
import CostTable from '@/components/CostTable';
import FunnelCards from '@/components/FunnelCards';

const REFRESH_INTERVAL = 30_000; // 30초

interface DashboardData {
  rows: {
    code: string; name: string;
    views: number; plays: number; likes: number;
    sessions: number; chatted: number; cta: number; phone: number;
    ctr: number;
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
  fetchedAt: string;
}

const fetcher = (url: string) => fetch(url).then(r => r.json());

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

      <main className="flex-1 px-4 md:px-6 py-6 space-y-6 max-w-screen-2xl mx-auto w-full">
        {error && (
          <div className="rounded-lg bg-red-900/30 border border-red-800 px-4 py-3 text-sm text-red-400">
            데이터를 불러오지 못했습니다. 잠시 후 자동으로 재시도합니다.
          </div>
        )}

        {!data && isLoading && (
          <div className="flex items-center justify-center h-64 text-gray-500 text-sm">
            데이터 불러오는 중…
          </div>
        )}

        {data && (
          <>
            {/* Summary */}
            <section>
              <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
                전체 요약
              </h2>
              <SummaryCards total={data.total} />
            </section>

            {/* Cost table */}
            <section>
              <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
                단계별 비용 효율 — 릴스당 40,000원
                <span className="ml-2 text-gray-600 normal-case">
                  초록 = 최저비용 · 빨강 = 최고비용
                </span>
              </h2>
              <CostTable rows={data.rows} total={data.total} />
            </section>

            {/* Funnel cards */}
            <section>
              <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
                계정별 퍼널
              </h2>
              <FunnelCards rows={data.rows} />
            </section>
          </>
        )}
      </main>
    </div>
  );
}
