const COLOR = {
  running: { dot: 'bg-emerald-400', text: 'text-emerald-400', ring: 'border-emerald-900' },
  stopped: { dot: 'bg-slate-500',   text: 'text-slate-400',   ring: 'border-slate-700'  },
  idle:    { dot: 'bg-slate-500',   text: 'text-slate-400',   ring: 'border-slate-700'  },
  error:   { dot: 'bg-red-500',     text: 'text-red-400',     ring: 'border-red-900'    },
  ok:      { dot: 'bg-emerald-400', text: 'text-emerald-400', ring: 'border-emerald-900'},
}

export default function StatusCard({ title, status, value, sub }) {
  const c = COLOR[status] ?? COLOR.idle
  return (
    <div className={`card border ${c.ring}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="label">{title}</span>
        <span className={`flex items-center gap-1.5 text-xs ${c.text}`}>
          <span className={`w-2 h-2 rounded-full ${c.dot} ${status === 'running' ? 'animate-pulse' : ''}`} />
          {status}
        </span>
      </div>
      {value !== undefined && (
        <div className="text-2xl font-semibold text-slate-100 font-mono">{value}</div>
      )}
      {sub && <div className="text-xs text-slate-500 mt-1">{sub}</div>}
    </div>
  )
}
