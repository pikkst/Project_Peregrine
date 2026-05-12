import { useState } from 'react'
import LogStream from '../components/LogStream'

const SOURCES = ['all', 'ros2', 'sim', 'mission', 'collect', 'build_db', 'train', 'build', 'system']

export default function Logs({ logs }) {
  const [filter, setFilter] = useState('all')

  const counts = SOURCES.reduce((acc, s) => {
    acc[s] = s === 'all'
      ? logs.length
      : logs.filter(l => l.source === s).length
    return acc
  }, {})

  return (
    <div className="p-6 flex flex-col h-full space-y-4" style={{ height: 'calc(100vh - 0px)' }}>
      <div className="flex items-center justify-between shrink-0">
        <h1 className="text-xl font-semibold text-slate-100">System Logs</h1>
        <span className="text-slate-500 text-xs">{logs.length} entries</span>
      </div>

      {/* Source filter */}
      <div className="flex flex-wrap gap-2 shrink-0">
        {SOURCES.map(s => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`text-xs px-3 py-1 rounded-full border transition-colors ${
              filter === s
                ? 'bg-cyan-700 border-cyan-600 text-white'
                : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-500'
            }`}
          >
            {s}
            {counts[s] > 0 && (
              <span className="ml-1.5 text-slate-500">{counts[s]}</span>
            )}
          </button>
        ))}
      </div>

      {/* Log stream fills rest of height */}
      <LogStream
        logs={logs}
        filter={filter}
        className="flex-1 min-h-0"
      />
    </div>
  )
}
