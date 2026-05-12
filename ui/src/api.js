const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const API_KEY = import.meta.env.VITE_API_KEY || ''
const WS = BASE.replace(/^http/, 'ws')

function authHeaders() {
  return API_KEY ? { Authorization: `Bearer ${API_KEY}` } : {}
}

export const WS_LOGS_URL      = `${WS}/ws/logs`
export const WS_TELEMETRY_URL = `${WS}/ws/telemetry`

async function request(method, path, body) {
  const headers = {
    ...authHeaders(),
    ...(body ? { 'Content-Type': 'application/json' } : {}),
  }

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: Object.keys(headers).length ? headers : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`${method} ${path} → ${res.status}`)
  return res.json()
}

export const api = {
  // System
  getStatus:    () => request('GET',  '/api/system/status'),
  buildRos2:    () => request('POST', '/api/system/build'),
  launchRos2:   (sim) => request('POST', `/api/system/launch?use_sim_time=${!!sim}`),
  stopRos2:     () => request('POST', '/api/system/stop'),

  // Simulation
  simStatus:    () => request('GET',  '/api/simulation/status'),
  startSim:     () => request('POST', '/api/simulation/start'),
  stopSim:      () => request('POST', '/api/simulation/stop'),
  getSettings:  () => request('GET',  '/api/simulation/settings'),
  saveSettings: (content) => request('POST', '/api/simulation/settings', { content }),

  // Mission
  missionStatus:  () => request('GET',  '/api/mission/status'),
  setWaypoints:   (wps) => request('POST', '/api/mission/waypoints', wps),
  startMission:   () => request('POST', '/api/mission/start'),
  stopMission:    () => request('POST', '/api/mission/stop'),

  // ML
  mlStatus:   () => request('GET',  '/api/ml/status'),
  collectData:() => request('POST', '/api/ml/collect'),
  buildDb:    () => request('POST', '/api/ml/build-db'),
  trainModel: () => request('POST', '/api/ml/train'),
  stopMl:     () => request('POST', '/api/ml/stop'),

  // ML — checkpoint object recognition
  getCheckpoints:        () => request('GET',    '/api/ml/checkpoints'),
  deleteCheckpointLabel: (label) => request('DELETE', `/api/ml/checkpoints/${encodeURIComponent(label)}`),
  trainCheckpoint:       () => request('POST',   '/api/ml/checkpoints/train'),
  uploadCheckpointImages: (label, files) => {
    const fd = new FormData()
    fd.append('label', label)
    for (const f of files) fd.append('files', f)
    return fetch(`${BASE}/api/ml/checkpoints/upload`, {
      method: 'POST',
      headers: Object.keys(authHeaders()).length ? authHeaders() : undefined,
      body: fd,
    }).then(r => r.json())
  },

  // Hardware — board connection
  hwBoardTypes:   () => request('GET',  '/api/hardware/board-types'),
  hwPorts:        () => request('GET',  '/api/hardware/ports'),
  hwStatus:       () => request('GET',  '/api/hardware/status'),
  hwConnect:      (payload) => request('POST', '/api/hardware/connect', payload),
  hwDisconnect:   () => request('POST', '/api/hardware/disconnect'),
  hwRead:         () => request('POST', '/api/hardware/read'),
  hwApply:        () => request('POST', '/api/hardware/apply'),
  // Hardware — saved profiles
  hwListProfiles:  () => request('GET',    '/api/hardware/profiles'),
  hwSaveProfile:   (name) => request('POST',   '/api/hardware/profiles', { name }),
  hwLoadProfile:   (name) => request('POST',   `/api/hardware/profiles/${encodeURIComponent(name)}/load`),
  hwDeleteProfile: (name) => request('DELETE', `/api/hardware/profiles/${encodeURIComponent(name)}`),
}
