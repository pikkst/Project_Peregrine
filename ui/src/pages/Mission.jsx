import { useState, useEffect } from 'react'
import { api } from '../api'

const CANVAS = 280
const MARGIN = 28

function toSvg(pts, drone) {
  const all = [...pts, drone].filter(Boolean)
  if (all.length === 0) return { toSvg: (x, y) => ({ sx: CANVAS / 2, sy: CANVAS / 2 }), scale: 1 }
  const xs = all.map(p => p.x), ys = all.map(p => p.y)
  const minX = Math.min(...xs), maxX = Math.max(...xs)
  const minY = Math.min(...ys), maxY = Math.max(...ys)
  const rangeX = maxX - minX || 2
  const rangeY = maxY - minY || 2
  const scale = Math.min((CANVAS - 2 * MARGIN) / rangeX, (CANVAS - 2 * MARGIN) / rangeY)
  const offX = (CANVAS - rangeX * scale) / 2 - minX * scale
  const offY = (CANVAS - rangeY * scale) / 2 + maxY * scale
  return {
    toSvg: (x, y) => ({ sx: x * scale + offX, sy: -y * scale + offY }),
    scale,
  }
}

export default function Mission({ status, telemetry }) {
  const [waypoints, setWaypoints] = useState([
    { x: 1.0, y: 0.0, z: -2.0 },
    { x: 1.0, y: 1.0, z: -2.0 },
    { x: 0.0, y: 1.0, z: -2.0 },
  ])
  const [msg, setMsg] = useState('')

  const missionRunning = status?.mission === 'running'
  const ros2Running    = status?.ros2    === 'running'

  // Load initial waypoints from backend
  useEffect(() => {
    api.missionStatus().then(r => {
      if (r.waypoints?.length) setWaypoints(r.waypoints)
    }).catch(() => {})
  }, [])

  function updateWp(i, field, val) {
    setWaypoints(prev => prev.map((wp, idx) =>
      idx === i ? { ...wp, [field]: parseFloat(val) || 0 } : wp
    ))
  }

  function addWp() {
    const last = waypoints[waypoints.length - 1] ?? { x: 0, y: 0, z: -2.0 }
    setWaypoints(prev => [...prev, { x: last.x + 1, y: last.y, z: last.z }])
  }

  function removeWp(i) {
    setWaypoints(prev => prev.filter((_, idx) => idx !== i))
  }

  async function handleSave() {
    const r = await api.setWaypoints(waypoints)
    setMsg(r.ok ? `Saved ${r.count} waypoints` : r.error)
  }

  async function handleStart() {
    await api.setWaypoints(waypoints)
    const r = await api.startMission()
    setMsg(r.ok ? 'Mission started' : r.error)
  }

  async function handleStop() {
    const r = await api.stopMission()
    setMsg(r.ok ? 'Mission stopped' : r.error)
  }

  const drone = telemetry ? { x: telemetry.x, y: telemetry.y } : { x: 0, y: 0 }
  const { toSvg: project } = toSvg(waypoints, drone)

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      <h1 className="text-xl font-semibold text-slate-100">Mission Planner</h1>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Waypoint editor */}
        <div className="card lg:col-span-3 space-y-3">
          <div className="flex items-center justify-between">
            <div className="label">Waypoints</div>
            <button className="btn-ghost text-xs py-1" onClick={addWp}>+ Add</button>
          </div>

          <table className="w-full text-sm">
            <thead>
              <tr className="text-slate-500 text-xs border-b border-slate-700">
                <th className="pb-2 text-left">#</th>
                <th className="pb-2 text-left">X (m)</th>
                <th className="pb-2 text-left">Y (m)</th>
                <th className="pb-2 text-left">Z (m)</th>
                <th className="pb-2"></th>
              </tr>
            </thead>
            <tbody>
              {waypoints.map((wp, i) => (
                <tr key={i} className={`border-b border-slate-800 ${
                  telemetry?.wp_idx === i && missionRunning ? 'bg-cyan-950' : ''
                }`}>
                  <td className="py-1.5 pr-2 text-slate-400 text-xs">{i + 1}</td>
                  {['x', 'y', 'z'].map(f => (
                    <td key={f} className="py-1.5 pr-2">
                      <input
                        type="number"
                        step="0.1"
                        className="input w-20 py-0.5 text-xs"
                        value={wp[f]}
                        onChange={e => updateWp(i, f, e.target.value)}
                        disabled={missionRunning}
                      />
                    </td>
                  ))}
                  <td className="py-1.5">
                    <button
                      className="text-slate-600 hover:text-red-400 transition-colors text-xs"
                      onClick={() => removeWp(i)}
                      disabled={missionRunning}
                    >✕</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="flex gap-2 pt-1">
            <button className="btn-ghost text-xs py-1.5 flex-1" onClick={handleSave}>
              Save
            </button>
            <button
              className="btn-primary flex-1"
              onClick={handleStart}
              disabled={missionRunning || !ros2Running || waypoints.length === 0}
            >
              {missionRunning ? '● Running…' : '▶ Start Mission'}
            </button>
            <button
              className="btn-danger flex-1"
              onClick={handleStop}
              disabled={!missionRunning}
            >
              ■ Stop
            </button>
          </div>

          {!ros2Running && (
            <div className="text-xs text-amber-400">Launch ROS2 before starting a mission</div>
          )}
          {msg && <div className="text-xs text-slate-400">{msg}</div>}

          {missionRunning && (
            <div className="bg-slate-900 rounded p-3">
              <div className="label mb-1">Progress</div>
              <div className="w-full bg-slate-700 rounded-full h-2">
                <div
                  className="bg-cyan-500 h-2 rounded-full transition-all"
                  style={{ width: `${waypoints.length > 0 ? ((telemetry?.wp_idx ?? 0) / waypoints.length) * 100 : 0}%` }}
                />
              </div>
              <div className="text-xs text-slate-400 mt-1">
                Waypoint {(telemetry?.wp_idx ?? 0) + 1} / {waypoints.length}
              </div>
            </div>
          )}
        </div>

        {/* Top-down map */}
        <div className="card lg:col-span-2">
          <div className="label mb-3">Top-down View (XY plane)</div>
          <svg
            width={CANVAS} height={CANVAS}
            className="bg-slate-900 rounded border border-slate-700"
          >
            {/* Grid */}
            {[-4,-2,0,2,4].map(v => {
              const { sx: gx } = project(v, 0)
              const { sy: gy } = project(0, v)
              return (
                <g key={v}>
                  <line x1={gx} y1={0} x2={gx} y2={CANVAS} stroke="#1e293b" strokeWidth="1"/>
                  <line x1={0} y1={gy} x2={CANVAS} y2={gy} stroke="#1e293b" strokeWidth="1"/>
                </g>
              )
            })}

            {/* Waypoint path */}
            {waypoints.length > 1 && (
              <polyline
                points={waypoints.map(wp => {
                  const { sx, sy } = project(wp.x, wp.y)
                  return `${sx},${sy}`
                }).join(' ')}
                fill="none"
                stroke="#334155"
                strokeWidth="1.5"
                strokeDasharray="4 3"
              />
            )}

            {/* Waypoints */}
            {waypoints.map((wp, i) => {
              const { sx, sy } = project(wp.x, wp.y)
              const active = missionRunning && telemetry?.wp_idx === i
              return (
                <g key={i}>
                  <circle
                    cx={sx} cy={sy} r={active ? 8 : 6}
                    fill={active ? '#06b6d4' : '#334155'}
                    stroke={active ? '#67e8f9' : '#475569'}
                    strokeWidth="1.5"
                  />
                  <text x={sx} y={sy + 1} textAnchor="middle" dominantBaseline="middle"
                    fill={active ? '#0f172a' : '#94a3b8'} fontSize="8" fontFamily="monospace">
                    {i + 1}
                  </text>
                </g>
              )
            })}

            {/* Drone */}
            {(() => {
              const { sx, sy } = project(drone.x, drone.y)
              const yaw = telemetry?.yaw ?? 0
              const rad = (yaw * Math.PI) / 180
              const pts = [
                [sx + 10 * Math.cos(rad - Math.PI / 2), sy + 10 * Math.sin(rad - Math.PI / 2)],
                [sx + 6 * Math.cos(rad + 2.3), sy + 6 * Math.sin(rad + 2.3)],
                [sx + 6 * Math.cos(rad - 2.3), sy + 6 * Math.sin(rad - 2.3)],
              ]
              return (
                <polygon
                  points={pts.map(p => p.join(',')).join(' ')}
                  fill="#06b6d4"
                  stroke="#67e8f9"
                  strokeWidth="1"
                />
              )
            })()}

            {/* Axis labels */}
            <text x={CANVAS - 4} y={CANVAS / 2 + 12} fill="#475569" fontSize="9" textAnchor="end">X+</text>
            <text x={CANVAS / 2 + 4} y={12} fill="#475569" fontSize="9">Y+</text>
          </svg>
          <div className="text-xs text-slate-600 mt-2 flex gap-4">
            <span>● cyan = drone</span>
            <span>○ = waypoint</span>
          </div>
        </div>
      </div>
    </div>
  )
}
