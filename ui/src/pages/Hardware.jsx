import { useState, useEffect } from 'react'
import { api } from '../api'

const PROTO_LABEL = { mavlink: 'Serial (MAVLink)', msp: 'Serial (MSP)', ssh: 'SSH' }

const DEFAULT_FORM = {
  board_type: 'pixhawk',
  port: '',
  baudrate: '',
  host: '',
  username: 'jetson',
  password: '',
  key_path: '',
  ssh_port: '22',
}

export default function Hardware({ status }) {
  const [boards,   setBoards]   = useState([])
  const [ports,    setPorts]    = useState([])
  const [hwStatus, setHwStatus] = useState(null)
  const [form,     setForm]     = useState(DEFAULT_FORM)
  const [profiles, setProfiles] = useState([])
  const [saveName, setSaveName] = useState('')
  const [busy,     setBusy]     = useState('')   // 'connect'|'read'|'apply'|'save'|''
  const [msg,      setMsg]      = useState(null) // {ok, text}

  const proto = boards.find(b => b.id === form.board_type)?.proto ?? 'mavlink'
  const isSSH = proto === 'ssh'

  useEffect(() => {
    api.hwBoardTypes().then(r => setBoards(r.boards ?? []))
    api.hwPorts().then(r => setPorts(r.ports ?? []))
    refreshStatus()
    refreshProfiles()
  }, [])

  function refreshStatus() {
    api.hwStatus().then(setHwStatus).catch(() => {})
  }

  function refreshProfiles() {
    api.hwListProfiles().then(r => setProfiles(r.profiles ?? []))
  }

  function notice(ok, text) {
    setMsg({ ok, text })
    setTimeout(() => setMsg(null), 4000)
  }

  function field(key, value) {
    if (key === 'board_type') {
      const board = boards.find(b => b.id === value)
      setForm(f => ({
        ...f,
        board_type: value,
        baudrate: board?.default_baud ? String(board.default_baud) : f.baudrate,
      }))
    } else {
      setForm(f => ({ ...f, [key]: value }))
    }
  }

  async function connect() {
    setBusy('connect')
    try {
      const payload = { board_type: form.board_type }
      if (!isSSH) {
        payload.port     = form.port
        payload.baudrate = form.baudrate ? parseInt(form.baudrate) : undefined
      } else {
        payload.host     = form.host
        payload.username = form.username
        payload.password = form.password || undefined
        payload.key_path = form.key_path || undefined
        payload.ssh_port = form.ssh_port ? parseInt(form.ssh_port) : 22
      }
      const r = await api.hwConnect(payload)
      notice(r.ok, r.ok ? `Connected to ${form.board_type}` : r.error)
      refreshStatus()
    } finally { setBusy('') }
  }

  async function disconnect() {
    setBusy('connect')
    try {
      const r = await api.hwDisconnect()
      notice(r.ok, r.ok ? 'Disconnected' : r.error)
      refreshStatus()
    } finally { setBusy('') }
  }

  async function readParams() {
    setBusy('read')
    try {
      const r = await api.hwRead()
      notice(r.ok, r.ok ? 'Parameters read successfully' : r.error)
      refreshStatus()
    } finally { setBusy('') }
  }

  async function applyParams() {
    setBusy('apply')
    try {
      const r = await api.hwApply()
      if (r.ok) {
        notice(true, 'Configs updated: AirSim + EKF + VIO')
      } else {
        const failed = Object.entries(r.results ?? {})
          .filter(([, v]) => !v.ok)
          .map(([k]) => k).join(', ')
        notice(false, `Failed: ${failed || r.error}`)
      }
    } finally { setBusy('') }
  }

  async function saveProfile() {
    if (!saveName.trim()) return
    setBusy('save')
    try {
      const r = await api.hwSaveProfile(saveName.trim())
      notice(r.ok, r.ok ? `Saved: ${r.name}` : r.error)
      setSaveName('')
      refreshProfiles()
    } finally { setBusy('') }
  }

  async function loadProfile(name) {
    const r = await api.hwLoadProfile(name)
    notice(r.ok, r.ok ? `Loaded: ${name}` : r.error)
    refreshStatus()
  }

  async function deleteProfile(name) {
    if (!confirm(`Delete profile "${name}"?`)) return
    const r = await api.hwDeleteProfile(name)
    notice(r.ok, r.ok ? `Deleted: ${name}` : r.error)
    refreshProfiles()
  }

  const connected = hwStatus?.status === 'connected' || hwStatus?.status === 'ready'

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <h1 className="text-xl font-semibold text-slate-100">Hardware Profile</h1>
      <p className="text-sm text-slate-400">
        Connect a real drone board, read its parameters, then apply them to AirSim,
        EKF, and VIO configs before running the simulation or ML training.
      </p>

      {/* Notification */}
      {msg && (
        <div className={`px-4 py-2 rounded text-sm font-medium ${
          msg.ok ? 'bg-emerald-900/60 text-emerald-300' : 'bg-red-900/60 text-red-300'
        }`}>
          {msg.text}
        </div>
      )}

      {/* Connection form */}
      <div className="bg-slate-800 rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
          Board Connection
        </h2>

        <div className="grid grid-cols-2 gap-4">
          <label className="block">
            <span className="text-xs text-slate-400 block mb-1">Board type</span>
            <select
              className="w-full bg-slate-700 text-slate-200 text-sm rounded px-3 py-2 border border-slate-600 focus:outline-none focus:border-cyan-500"
              value={form.board_type}
              onChange={e => field('board_type', e.target.value)}
              disabled={connected}
            >
              {boards.map(b => (
                <option key={b.id} value={b.id}>{b.label}</option>
              ))}
            </select>
          </label>
          <div className="flex items-end pb-0.5">
            <span className="text-xs text-slate-500 px-2 py-1.5 rounded bg-slate-700 border border-slate-600">
              {PROTO_LABEL[proto] ?? proto}
            </span>
          </div>
        </div>

        {/* Serial fields */}
        {!isSSH && (
          <div className="grid grid-cols-2 gap-4">
            <label className="block">
              <span className="text-xs text-slate-400 block mb-1">Serial port</span>
              <div className="flex gap-2">
                <select
                  className="flex-1 bg-slate-700 text-slate-200 text-sm rounded px-3 py-2 border border-slate-600 focus:outline-none focus:border-cyan-500"
                  value={form.port}
                  onChange={e => field('port', e.target.value)}
                  disabled={connected}
                >
                  <option value="">— select —</option>
                  {ports.map(p => (
                    <option key={p.port} value={p.port}>
                      {p.port}{p.description ? ` (${p.description})` : ''}
                    </option>
                  ))}
                </select>
                <button
                  className="text-xs px-2 py-1 rounded bg-slate-600 hover:bg-slate-500 text-slate-300"
                  onClick={() => api.hwPorts().then(r => setPorts(r.ports ?? []))}
                  title="Refresh ports"
                >↺</button>
              </div>
            </label>
            <label className="block">
              <span className="text-xs text-slate-400 block mb-1">Baud rate</span>
              <input
                type="number"
                className="w-full bg-slate-700 text-slate-200 text-sm rounded px-3 py-2 border border-slate-600 focus:outline-none focus:border-cyan-500"
                value={form.baudrate}
                onChange={e => field('baudrate', e.target.value)}
                placeholder="57600"
                disabled={connected}
              />
            </label>
          </div>
        )}

        {/* SSH fields */}
        {isSSH && (
          <div className="grid grid-cols-2 gap-4">
            <label className="block">
              <span className="text-xs text-slate-400 block mb-1">Host / IP</span>
              <input
                className="w-full bg-slate-700 text-slate-200 text-sm rounded px-3 py-2 border border-slate-600 focus:outline-none focus:border-cyan-500"
                value={form.host}
                onChange={e => field('host', e.target.value)}
                placeholder="192.168.1.100"
                disabled={connected}
              />
            </label>
            <label className="block">
              <span className="text-xs text-slate-400 block mb-1">Username</span>
              <input
                className="w-full bg-slate-700 text-slate-200 text-sm rounded px-3 py-2 border border-slate-600 focus:outline-none focus:border-cyan-500"
                value={form.username}
                onChange={e => field('username', e.target.value)}
                placeholder="jetson"
                disabled={connected}
              />
            </label>
            <label className="block">
              <span className="text-xs text-slate-400 block mb-1">Password (optional)</span>
              <input
                type="password"
                className="w-full bg-slate-700 text-slate-200 text-sm rounded px-3 py-2 border border-slate-600 focus:outline-none focus:border-cyan-500"
                value={form.password}
                onChange={e => field('password', e.target.value)}
                placeholder="leave blank for key auth"
                disabled={connected}
              />
            </label>
            <label className="block">
              <span className="text-xs text-slate-400 block mb-1">SSH port</span>
              <input
                type="number"
                className="w-full bg-slate-700 text-slate-200 text-sm rounded px-3 py-2 border border-slate-600 focus:outline-none focus:border-cyan-500"
                value={form.ssh_port}
                onChange={e => field('ssh_port', e.target.value)}
                placeholder="22"
                disabled={connected}
              />
            </label>
          </div>
        )}

        {/* Connect / Disconnect */}
        <div className="flex gap-3 pt-1">
          {!connected ? (
            <button
              className="px-5 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-medium disabled:opacity-50"
              onClick={connect}
              disabled={!!busy}
            >
              {busy === 'connect' ? 'Connecting…' : 'Connect'}
            </button>
          ) : (
            <button
              className="px-5 py-2 rounded-lg bg-slate-600 hover:bg-slate-500 text-slate-200 text-sm font-medium disabled:opacity-50"
              onClick={disconnect}
              disabled={!!busy}
            >
              Disconnect
            </button>
          )}
          <span className={`self-center text-xs font-medium px-2 py-1 rounded ${
            connected
              ? 'bg-emerald-900/50 text-emerald-400'
              : 'bg-slate-700 text-slate-500'
          }`}>
            {hwStatus?.status ?? 'disconnected'}
          </span>
        </div>
      </div>

      {/* Read & Apply */}
      <div className="bg-slate-800 rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
          Parameters
        </h2>

        <div className="flex gap-3 flex-wrap">
          <button
            className="px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium disabled:opacity-40"
            onClick={readParams}
            disabled={!connected || !!busy}
          >
            {busy === 'read' ? 'Reading…' : 'Read from Board'}
          </button>
          <button
            className="px-5 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-white text-sm font-medium disabled:opacity-40"
            onClick={applyParams}
            disabled={!hwStatus?.imu_sensor || !!busy}
          >
            {busy === 'apply' ? 'Applying…' : 'Apply to Configs'}
          </button>
        </div>

        {hwStatus?.imu_sensor && (
          <ProfileSummary hwStatus={hwStatus} />
        )}
      </div>

      {/* Save / Load profiles */}
      <div className="bg-slate-800 rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
          Saved Profiles
        </h2>

        <div className="flex gap-2">
          <input
            className="flex-1 bg-slate-700 text-slate-200 text-sm rounded px-3 py-2 border border-slate-600 focus:outline-none focus:border-cyan-500"
            placeholder="Profile name…"
            value={saveName}
            onChange={e => setSaveName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && saveProfile()}
          />
          <button
            className="px-4 py-2 rounded-lg bg-slate-600 hover:bg-slate-500 text-slate-200 text-sm font-medium disabled:opacity-40"
            onClick={saveProfile}
            disabled={!saveName.trim() || !hwStatus?.imu_sensor || !!busy}
          >
            {busy === 'save' ? 'Saving…' : 'Save'}
          </button>
        </div>

        {profiles.length === 0 ? (
          <p className="text-xs text-slate-500">No saved profiles yet.</p>
        ) : (
          <div className="space-y-1">
            {profiles.map(p => (
              <div
                key={p.name}
                className="flex items-center justify-between px-3 py-2 rounded bg-slate-700/60 hover:bg-slate-700"
              >
                <span className="text-sm text-slate-300">{p.name}</span>
                <div className="flex gap-2">
                  <button
                    className="text-xs px-3 py-1 rounded bg-cyan-800 hover:bg-cyan-700 text-cyan-200"
                    onClick={() => loadProfile(p.name)}
                  >Load</button>
                  <button
                    className="text-xs px-3 py-1 rounded bg-red-900/60 hover:bg-red-800 text-red-300"
                    onClick={() => deleteProfile(p.name)}
                  >Delete</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function ProfileSummary({ hwStatus }) {
  const fw = hwStatus.firmware ?? {}
  const vh = hwStatus.vehicle  ?? {}

  const rows = [
    ['IMU sensor',  hwStatus.imu_sensor],
    ['Board',       hwStatus.board_type],
    ['Firmware',    fw.firmware ?? fw.model],
    ['Frame type',  vh.frame_type],
    ['Motors',      vh.motor_count],
  ].filter(([, v]) => v !== undefined && v !== null && v !== '')

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-1">
      {rows.map(([label, value]) => (
        <div key={label} className="bg-slate-700/50 rounded px-3 py-2">
          <div className="text-xs text-slate-500">{label}</div>
          <div className="text-sm text-slate-200 font-medium mt-0.5">{String(value)}</div>
        </div>
      ))}
    </div>
  )
}
