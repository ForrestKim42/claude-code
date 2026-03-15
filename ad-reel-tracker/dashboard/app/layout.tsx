import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: '광고 릴스 대시보드',
  description: '인스타그램 광고 릴스 퍼포먼스 실시간 모니터링',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
