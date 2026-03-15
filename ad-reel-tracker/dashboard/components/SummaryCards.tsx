interface Total {
  cost: number;
  views: number;
  sessions: number;
  chatted: number;
  cta: number;
  phone: number;
  cpph: number | null;
}

function Card({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-gray-900 rounded-xl border border-gray-800 px-5 py-4">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-2xl font-bold text-white">{value}</div>
      {sub && <div className="text-xs text-gray-500 mt-0.5">{sub}</div>}
    </div>
  );
}

export default function SummaryCards({ total }: { total: Total }) {
  const fmt = (n: number) => n.toLocaleString('ko-KR');
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      <Card label="총 집행 비용" value={`${fmt(total.cost)}원`} />
      <Card label="총 뷰" value={fmt(total.views)} />
      <Card label="총 세션" value={fmt(total.sessions)} />
      <Card label="총 채팅" value={fmt(total.chatted)} />
      <Card label="총 전화 제출" value={`${fmt(total.phone)}건`} />
      <Card
        label="평균 CP-Lead"
        value={total.cpph != null ? `${fmt(total.cpph)}원` : '—'}
        sub="전화 제출 1건당"
      />
    </div>
  );
}
