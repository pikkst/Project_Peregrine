import { useEffect, useRef } from 'react'

const SRC_COLOR = {
  ros2:     'text-cyan-400',
  sim:      'text-purple-400',
  mission:  'text-emerald-400',
  collect:  'text-amber-400',
  build_db: 'text-amber-400',
  train:    'text-orange-400',
  build:    'text-blue-400',
  system:   'text-slate-400',
  ml:       'text-amber-400',
}

export default function LogStream({ logs, filter = 'all', className = '' }) {
  const endRef = useRef(null)
  const containerRef = useRef(null)
  const autoScroll = useRef(true)

  const filtered = filter === 'all'
    ? logs
    : logs.filter(l => l.source === filter)

  useEffect(() => {
    if (autoScroll.current) {
      endRef.current?.scrollIntoView({ behavior: 'auto' })
    }
  }, [filtered.length])

  const onScroll = () => {
    const el = containerRef.current
    if (!el) return
    autoScroll.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40
  }

  return (
    <div
      ref={containerRef}
      onScroll={onScroll}
      className={`bg-slate-950 rounded-lg p-3 overflow-y-auto font-mono text-xs leading-5 ${className}`}
    >
      {filtered.length === 0 && (
        <div className="text-slate-600 italic">No log entries yet…</div>
      )}
      {filtered.map((log, i) => (
        <div key={i} className="flex gap-2 py-px hover:bg-slate-900 rounded px-1">
          <span className={`shrink-0 ${SRC_COLOR[log.source] ?? 'text-slate-500'}`}>
            [{log.source}]
          </span>
          <span className="text-slate-300 break-all">{log.text}</span>
        </div>
      ))}
      <div ref={endRef} />
    </div>
  )
}
