interface Alert {
  type: 'error' | 'warning';
  message: string;
}

export default function AlertBanner({ alerts }: { alerts: Alert[] }) {
  if (!alerts.length) return null;

  const errors   = alerts.filter(a => a.type === 'error');
  const warnings = alerts.filter(a => a.type === 'warning');

  return (
    <div className="space-y-2">
      {errors.map((a, i) => (
        <div
          key={i}
          className="flex items-start gap-2.5 px-4 py-3 rounded-lg bg-red-950/40 border border-red-800/60 text-sm text-red-300"
        >
          <span className="text-red-400 mt-0.5 shrink-0">●</span>
          {a.message}
        </div>
      ))}
      {warnings.map((a, i) => (
        <div
          key={i}
          className="flex items-start gap-2.5 px-4 py-3 rounded-lg bg-amber-950/30 border border-amber-800/50 text-sm text-amber-300"
        >
          <span className="text-amber-400 mt-0.5 shrink-0">▲</span>
          {a.message}
        </div>
      ))}
    </div>
  );
}
