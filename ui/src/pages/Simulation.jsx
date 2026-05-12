import { useState, useEffect } from 'react'
import { api } from '../api'

export default function Simulation({ status, refreshStatus }) {
  const [settings, setSettings] = useState('')
  const [settingsDirty, setSettingsDirty] = useState(false)
  const [savingSettings, setSavingSettings] = useState(false)
  const [simMsg, setSimMsg] = useState('')

  const simRunning = status?.simulation === 'running'

  useEffect(() => {
    api.getSettings().then(r => r.ok && setSettings(r.content))
  }, [])

  async function handleStart() {
    const r = await api.startSim()
    setSimMsg(r.ok ? 'Simulation started' : r.error)
    refreshStatus()
  }

  async function handleStop() {
    const r = await api.stopSim()
    setSimMsg(r.ok ? 'Simulation stopped' : r.error)
    refreshStatus()
  }

  async function handleSaveSettings() {
    setSavingSettings(true)
    const r = await api.saveSettings(settings)
    setSavingSettings(false)
    setSettingsDirty(false)
    setSimMsg(r.ok ? 'Settings saved' : r.error)
  }

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      <h1 className="text-xl font-semibold text-slate-100">Simulation</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Control panel */}
        <div className="card space-y-4">
          <div className="label">Unreal + AirSim</div>

          <div className="flex items-center gap-3">
            <span className={`w-3 h-3 rounded-full ${simRunning ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'}`} />
            <span className="text-slate-300">
              {simRunning ? 'Simulation running' : 'Simulation offline'}
            </span>
          </div>

          <div className="flex gap-3">
            <button className="btn-primary flex-1" onClick={handleStart} disabled={simRunning}>
              Start Simulation
            </button>
            <button className="btn-danger flex-1" onClick={handleStop} disabled={!simRunning}>
              Stop
            </button>
          </div>

          {simMsg && (
            <div className="text-xs text-slate-400 bg-slate-900 rounded px-3 py-2">{simMsg}</div>
          )}

          <div className="text-xs text-slate-500 border-t border-slate-700 pt-3">
            <p>Requires <code className="text-cyan-400">scripts/run_unreal_sim.bat</code></p>
            <p className="mt-1">Make sure Unreal Engine is installed and the AirSim plugin is configured.</p>
          </div>
        </div>

        {/* Camera feed */}
        <div className="card">
          <div className="label mb-3">Camera Feed</div>
          <div className="bg-slate-900 rounded-lg aspect-video flex items-center justify-center border border-slate-700">
            {simRunning ? (
              <div className="text-center text-slate-500 text-sm">
                <div className="text-slate-400 mb-1">AirSim Camera</div>
                <div className="text-xs">Stream via airsim_bridge ROS2 node</div>
                <div className="text-xs mt-1 text-cyan-500">/airsim/camera/front_left/image_raw</div>
              </div>
            ) : (
              <div className="text-center text-slate-600 text-sm">
                <div className="text-3xl mb-2">📷</div>
                <div>Start simulation to view camera feed</div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* AirSim settings editor */}
      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <div className="label">AirSim Settings (airsim_settings.json)</div>
          <div className="flex gap-2">
            <button
              className="btn-ghost text-xs py-1"
              onClick={() => api.getSettings().then(r => { setSettings(r.content); setSettingsDirty(false) })}
            >
              Reload
            </button>
            <button
              className="btn-primary text-xs py-1"
              onClick={handleSaveSettings}
              disabled={!settingsDirty || savingSettings}
            >
              {savingSettings ? 'Saving…' : 'Save'}
            </button>
          </div>
        </div>
        <textarea
          className="input font-mono text-xs h-64 resize-none"
          value={settings}
          onChange={e => { setSettings(e.target.value); setSettingsDirty(true) }}
          placeholder="Loading AirSim settings…"
          spellCheck={false}
        />
        {settingsDirty && (
          <div className="text-xs text-amber-400 mt-1">Unsaved changes</div>
        )}
      </div>
    </div>
  )
}
