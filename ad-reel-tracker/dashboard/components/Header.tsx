'use client';

import { useEffect, useState } from 'react';

interface HeaderProps {
  fetchedAt: string | null;
  isLoading: boolean;
  onRefresh: () => void;
  refreshInterval: number; // ms
}

export default function Header({ fetchedAt, isLoading, onRefresh, refreshInterval }: HeaderProps) {
  const [countdown, setCountdown] = useState(refreshInterval / 1000);

  useEffect(() => {
    if (!fetchedAt) return;
    setCountdown(refreshInterval / 1000);
    const id = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) { return refreshInterval / 1000; }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [fetchedAt, refreshInterval]);

  const fmtKst = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleString('ko-KR', {
      timeZone: 'Asia/Seoul',
      month: 'numeric', day: 'numeric',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    }) + ' KST';
  };

  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
      <div>
        <h1 className="text-xl font-bold text-white">광고 릴스 대시보드</h1>
        <p className="text-xs text-gray-500 mt-0.5">인스타그램 릴스 5개 × 40,000원 = 총 200,000원</p>
      </div>

      <div className="flex items-center gap-4">
        {fetchedAt && (
          <div className="text-right text-xs text-gray-500">
            <div>업데이트: {fmtKst(fetchedAt)}</div>
            <div className="text-gray-600">다음 갱신까지 {countdown}초</div>
          </div>
        )}

        <a
          href="/leads"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-emerald-700 hover:bg-emerald-600 text-sm font-medium transition-colors text-white"
        >
          전화 채팅 보기
        </a>

        <button
          onClick={onRefresh}
          disabled={isLoading}
          className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-sm font-medium transition-colors"
        >
          <span
            className={`inline-block w-2 h-2 rounded-full bg-white ${isLoading ? 'animate-ping' : ''}`}
          />
          {isLoading ? '갱신 중…' : '지금 갱신'}
        </button>
      </div>
    </header>
  );
}
