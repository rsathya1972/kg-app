interface StatusBadgeProps {
  status: "connected" | "unreachable" | "loading";
  responseTimeMs?: number;
}

export default function StatusBadge({ status, responseTimeMs }: StatusBadgeProps) {
  const config = {
    connected: {
      dot: "bg-emerald-400 animate-pulse",
      text: "text-emerald-400",
      label: "Connected",
      bg: "bg-emerald-900/30 border-emerald-800",
    },
    unreachable: {
      dot: "bg-red-400",
      text: "text-red-400",
      label: "Unreachable",
      bg: "bg-red-900/30 border-red-800",
    },
    loading: {
      dot: "bg-slate-500 animate-pulse",
      text: "text-slate-400",
      label: "Checking…",
      bg: "bg-slate-800 border-slate-700",
    },
  }[status];

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm font-medium ${config.bg} ${config.text}`}>
      <span className={`w-2 h-2 rounded-full shrink-0 ${config.dot}`} />
      <span>Backend: {config.label}</span>
      {status === "connected" && responseTimeMs !== undefined && (
        <span className="text-slate-500 font-normal">{responseTimeMs}ms</span>
      )}
    </div>
  );
}
