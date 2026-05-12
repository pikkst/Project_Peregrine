import { useState, useEffect, useRef } from 'react'
import { api } from '../api'
import LogStream from '../components/LogStream'

function StepCard({ number, title, desc, action, status, onRun, onStop, disabled }) {
  const running = status === action
  return (
    <div className={`bg-slate-800 rounded-xl p-4 border-l-4 ${
      running ? 'border-l-amber-500' : 'border-l-slate-700'
    }`}>
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className={`text-lg font-bold ${running ? 'text-amber-400' : 'text-slate-500'}`}>
              {number}
            </span>
            <span className="font-medium text-slate-200">{title}</span>
            {running && (
              <span className="text-xs bg-amber-900 text-amber-300 px-2 py-0.5 rounded-full animate-pulse">
                running
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-1 ml-7">{desc}</p>
        </div>
        <div className="flex gap-2">
          {running && (
            <button className="px-3 py-1 text-xs rounded bg-red-800 hover:bg-red-700 text-red-200"
              onClick={onStop}>Stop</button>
          )}
          <button
            className="px-3 py-1 text-xs rounded bg-cyan-700 hover:bg-cyan-600 text-white disabled:opacity-40"
            onClick={onRun}
            disabled={disabled || running}
          >
            {running ? 'Running…' : 'Run'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Checkpoint section ──────────────────────────────────────────────────────

function CheckpointTrainer({ mlRunning, mlStep, onStop, logs }) {
  const [checkpoints, setCheckpoints] = useState({ classes: [], total_images: 0, model_exists: false, labels: [] })
  const [label,     setLabel]     = useState('')
  const [uploading, setUploading] = useState(false)
  const [msg,       setMsg]       = useState(null)
  const fileRef = useRef()

  const ckptRunning = mlStep === 'checkpoint_train'

  useEffect(() => {
    refresh()
  }, [])

  function refresh() {
    api.getCheckpoints().then(r => r.ok && setCheckpoints(r)).catch(() => {})
  }

  function notice(ok, text) {
    setMsg({ ok, text })
    setTimeout(() => setMsg(null), 4000)
  }

  async function upload(files) {
    if (!label.trim()) { notice(false, 'Enter a label name first'); return }
    if (!files?.length) return
    setUploading(true)
    try {
      const r = await api.uploadCheckpointImages(label.trim(), Array.from(files))
      notice(r.ok, r.ok ? `Uploaded ${r.saved} images for "${r.label}"` : r.error)
      refresh()
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  async function deleteLabelImages(lbl) {
    if (!confirm(`Delete all images for "${lbl}"?`)) return
    const r = await api.deleteCheckpointLabel(lbl)
    notice(r.ok, r.ok ? `Deleted "${lbl}"` : r.error)
    refresh()
  }

  async function trainCkpt() {
    const r = await api.trainCheckpoint()
    notice(r.ok, r.ok ? 'Training started — check logs below' : r.error)
  }

  const ckptLogs = logs.filter(l => l.source === 'checkpoint')

  return (
    <div className="bg-slate-800 rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-slate-200">
            Checkpoint Object Recognition
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Upload labelled photos of real-world checkpoints → fine-tune ResNet-18 to recognise them
          </p>
        </div>
        {checkpoints.model_exists && (
          <span className="text-xs bg-emerald-900/60 text-emerald-400 px-2 py-1 rounded">
            model trained
          </span>
        )}
      </div>

      {msg && (
        <div className={`px-3 py-2 rounded text-xs font-medium ${
          msg.ok ? 'bg-emerald-900/60 text-emerald-300' : 'bg-red-900/60 text-red-300'
        }`}>{msg.text}</div>
      )}

      {/* Upload area */}
      <div className="space-y-2">
        <div className="flex gap-2">
          <input
            className="flex-1 bg-slate-700 text-slate-200 text-sm rounded px-3 py-2 border border-slate-600 focus:outline-none focus:border-cyan-500"
            placeholder="Label name (e.g. tower_A, building_north)…"
            value={label}
            onChange={e => setLabel(e.target.value)}
          />
          <label className={`px-4 py-2 rounded-lg text-sm font-medium cursor-pointer ${
            uploading
              ? 'bg-slate-600 text-slate-400'
              : 'bg-indigo-700 hover:bg-indigo-600 text-white'
          }`}>
            {uploading ? 'Uploading…' : '+ Upload Images'}
            <input
              ref={fileRef}
              type="file"
              multiple
              accept="image/*"
              className="hidden"
              disabled={uploading}
              onChange={e => upload(e.target.files)}
            />
          </label>
        </div>
        <p className="text-xs text-slate-600">
          Accepts JPG, PNG, WEBP. Minimum 4 images total across all labels.
        </p>
      </div>

      {/* Classes table */}
      {checkpoints.classes.length > 0 ? (
        <div className="space-y-1">
          <div className="text-xs text-slate-500 mb-1">
            {checkpoints.classes.length} classes · {checkpoints.total_images} images total
            {checkpoints.labels.length > 0 &&
              ` · trained on: ${checkpoints.labels.join(', ')}`}
          </div>
          {checkpoints.classes.map(c => (
            <div key={c.label}
              className="flex items-center justify-between px-3 py-2 rounded bg-slate-700/50">
              <div className="flex items-center gap-3">
                <span className="text-sm text-slate-200 font-medium">{c.label}</span>
                <span className="text-xs text-slate-500">{c.count} images</span>
                {c.count < 2 && (
                  <span className="text-xs text-amber-500">need more images</span>
                )}
              </div>
              <button
                className="text-xs px-2 py-0.5 rounded bg-red-900/50 hover:bg-red-800 text-red-400"
                onClick={() => deleteLabelImages(c.label)}
              >Delete</button>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-xs text-slate-600 italic">
          No checkpoint images uploaded yet. Add a label and upload photos above.
        </p>
      )}

      {/* Train button */}
      <div className="flex gap-3 pt-1">
        <button
          className="px-5 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-white text-sm font-medium disabled:opacity-40"
          onClick={trainCkpt}
          disabled={mlRunning || checkpoints.total_images < 4}
          title={checkpoints.total_images < 4 ? 'Need at least 4 images' : ''}
        >
          {ckptRunning ? 'Training…' : 'Train Checkpoint Classifier'}
        </button>
        {ckptRunning && (
          <button className="px-3 py-2 text-sm rounded bg-red-800 hover:bg-red-700 text-red-200"
            onClick={onStop}>Stop</button>
        )}
        {ckptRunning && (
          <span className="self-center text-xs text-amber-400 animate-pulse">training…</span>
        )}
      </div>

      {/* Checkpoint logs */}
      {ckptLogs.length > 0 && (
        <div className="bg-slate-900 rounded p-3 max-h-36 overflow-y-auto font-mono text-xs text-slate-300 space-y-0.5">
          {ckptLogs.slice(-30).map((l, i) => (
            <div key={i} className={
              l.text.startsWith('PROGRESS') ? 'text-cyan-400' :
              l.text.startsWith('ERROR') ? 'text-red-400' : ''
            }>{l.text}</div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Main page ───────────────────────────────────────────────────────────────

export default function MLTraining({ status, logs }) {
  const [mlInfo, setMlInfo] = useState(null)
  const mlRunning = status?.ml === 'running'
  const mlStep    = status?.ml_step

  useEffect(() => {
    const fetch = () => api.mlStatus().then(setMlInfo).catch(() => {})
    fetch()
    const id = setInterval(fetch, 3000)
    return () => clearInterval(id)
  }, [])

  const mlLogs = logs.filter(l =>
    ['collect', 'build_db', 'train', 'ml'].includes(l.source)
  )

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">ML Training Pipeline</h1>
        <p className="text-slate-500 text-sm mt-1">
          Simulation pipeline (AirSim data) + checkpoint object recognition (your own images)
        </p>
      </div>

      {/* Dataset info */}
      <div className="bg-slate-800 rounded-xl p-4">
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
          AirSim Dataset
        </div>
        <div className="flex gap-6 text-sm">
          <div>
            <span className="text-slate-400">RGB images: </span>
            <span className="text-cyan-300 font-mono">{mlInfo?.dataset_count ?? '—'}</span>
          </div>
          <div>
            <span className="text-slate-400">Output dir: </span>
            <code className="text-slate-300 text-xs">ros2_ws/src/sim/data_collection/output/</code>
          </div>
        </div>
      </div>

      {/* AirSim pipeline */}
      <div className="space-y-3">
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-1">
          AirSim Simulation Pipeline
        </div>
        <StepCard
          number="01"
          title="Collect Data"
          action="collect"
          desc="Fly preset route in AirSim and capture RGB/depth/segmentation images"
          status={mlRunning ? mlStep : null}
          onRun={() => api.collectData()}
          onStop={() => api.stopMl()}
          disabled={mlRunning && mlStep !== 'collect'}
        />
        <StepCard
          number="02"
          title="Build Savepoint Database"
          action="build_db"
          desc="Index captured images into savepoints.json for VPR lookup"
          status={mlRunning ? mlStep : null}
          onRun={() => api.buildDb()}
          onStop={() => api.stopMl()}
          disabled={mlRunning && mlStep !== 'build_db'}
        />
        <StepCard
          number="03"
          title="Train VPR Model"
          action="train"
          desc="Train visual place recognition model on collected AirSim data"
          status={mlRunning ? mlStep : null}
          onRun={() => api.trainModel()}
          onStop={() => api.stopMl()}
          disabled={mlRunning && mlStep !== 'train'}
        />
      </div>

      {/* Checkpoint object recognition */}
      <CheckpointTrainer
        mlRunning={mlRunning}
        mlStep={mlStep}
        onStop={() => api.stopMl()}
        logs={logs}
      />

      {/* ML log stream */}
      <div className="bg-slate-800 rounded-xl p-4">
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
          ML Output Log
        </div>
        <LogStream
          logs={mlLogs.length > 0 ? mlLogs : logs.slice(-50)}
          filter="all"
          className="h-48"
        />
      </div>
    </div>
  )
}
