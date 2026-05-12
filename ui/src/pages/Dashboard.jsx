import { api } from '../api'
import StatusCard from '../components/StatusCard'
import PoseChart from '../components/PoseChart'

function TelNum({ label, value, unit = '' }) {
  return (
    <div className="bg-slate-900 rounded p-3 text-center">
      <div className="label">{label}</div>
      <div className="text-xl font-semibold text-cyan-300 font-mono">
        {value !== undefined ? value.toFixed(3) : '—'}
        {unit && <span className="text-sm text-slate-500 ml-1">{unit}</span>}
      </div>
    </div>
  )
}

export default function Dashboard({ status, telemetry, telHistory, refreshStatus }) {
  const ros2     = status?.ros2       ?? 'stopped'
  const sim      = status?.simulation ?? 'stopped'
  const mission  = status?.mission    ?? 'idle'
  const mlStatus = status?.ml         ?? 'idle'
  const built    = status?.build_exists ? 'ok' : 'stopped'

  async function handleLaunch() {
    await api.launchRos2(false)
    refreshStatus()
  }
  async function handleStop() {
    await api.stopRos2()
    refreshStatus()
  }
  async function handleBuild() {
    await api.buildRos2()
  }

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-semibold text-slate-100">Peregrine Control Center</h1>
        <p className="text-slate-500 text-sm mt-1">GNSS-denied autonomous drone navigation stack</p>
      </div>

      {/* Status cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatusCard title="ROS2 Stack"  status={ros2}    sub={ros2 === 'running' ? 'nodes active' : 'not launched'} />
        <StatusCard title="Simulation"  status={sim}     sub={sim  === 'running' ? 'AirSim live'  : 'Unreal offline'} />
        <StatusCard title="Mission"     status={mission} sub={mission === 'running' ? `wp ${telemetry?.wp_idx ?? 0}` : 'idle'} />
        <StatusCard title="Workspace"   status={built}   sub={status?.build_exists ? 'built' : 'not built'} />
      </div>

      {/* Quick actions */}
      <div className="card flex flex-wrap gap-3 items-center">
        <span className="label mr-2">Quick Actions</span>
        <button className="btn-primary" onClick={handleLaunch} disabled={ros2 === 'running'}>
          Launch ROS2
        </button>
        <button className="btn-danger"  onClick={handleStop}   disabled={ros2 !== 'running'}>
          Stop ROS2
        </button>
        <button className="btn-ghost"   onClick={handleBuild}  disabled={ros2 === 'running'}>
          Build Workspace
        </button>
        <span className="text-slate-600 text-xs ml-auto">
          {ros2 === 'running' ? '● ROS2 is running' : '○ ROS2 offline'}
        </span>
      </div>

      {/* Telemetry numbers + chart */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card lg:col-span-1 space-y-3">
          <div className="label">Live Telemetry</div>
          <div className="grid grid-cols-3 gap-2">
            <TelNum label="X" value={telemetry?.x} unit="m" />
            <TelNum label="Y" value={telemetry?.y} unit="m" />
            <TelNum label="Z" value={telemetry?.z} unit="m" />
          </div>
          <div className="grid grid-cols-3 gap-2">
            <TelNum label="Vx"  value={telemetry?.vx}  unit="m/s" />
            <TelNum label="Vy"  value={telemetry?.vy}  unit="m/s" />
            <TelNum label="Yaw" value={telemetry?.yaw} unit="°" />
          </div>
          {ros2 !== 'running' && (
            <div className="text-xs text-slate-600 text-center italic">
              Launch ROS2 for live data
            </div>
          )}
        </div>

        <div className="card lg:col-span-2">
          <div className="label mb-3">Position History (X / Y / Z)</div>
          {telHistory.length > 1
            ? <PoseChart data={telHistory} height={200} />
            : <div className="flex items-center justify-center h-48 text-slate-600 text-sm">
                No data — launch ROS2 to stream telemetry
              </div>
          }
        </div>
      </div>

      {/* ML status row */}
      <div className="card">
        <div className="label mb-2">ML Pipeline</div>
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${mlStatus === 'running' ? 'bg-amber-400 animate-pulse' : 'bg-slate-600'}`} />
            <span className="text-slate-300">
              {mlStatus === 'running'
                ? `Running: ${status?.ml_step ?? '…'}`
                : 'Idle'}
            </span>
          </div>
          <span className="text-slate-600">→ navigate to ML Training to trigger pipeline</span>
        </div>
      </div>
    </div>
  )
}
