import { useState, useEffect, useRef, useCallback, lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import { api, WS_LOGS_URL, WS_TELEMETRY_URL } from './api'

const Dashboard   = lazy(() => import('./pages/Dashboard'))
const Simulation  = lazy(() => import('./pages/Simulation'))
const Mission     = lazy(() => import('./pages/Mission'))
const MLTraining  = lazy(() => import('./pages/MLTraining'))
const Logs        = lazy(() => import('./pages/Logs'))
const Hardware    = lazy(() => import('./pages/Hardware'))

const MAX_TELEMETRY_HISTORY = 120  // ~24 seconds at 5 Hz

export default function App() {
  const [status, setStatus]   = useState(null)
  const [telemetry, setTelemetry] = useState(null)
  const [telHistory, setTelHistory] = useState([])
  const [logs, setLogs]       = useState([])

  // Fetch system status every 2 seconds
  useEffect(() => {
    const fetchStatus = () =>
      api.getStatus().then(setStatus).catch(() => setStatus(null))
    fetchStatus()
    const id = setInterval(fetchStatus, 2000)
    return () => clearInterval(id)
  }, [])

  // WebSocket: telemetry
  useEffect(() => {
    let ws, retry
    let active = true
    const connect = () => {
      if (!active) return
      ws = new WebSocket(WS_TELEMETRY_URL)
      ws.onmessage = (e) => {
        const data = JSON.parse(e.data)
        setTelemetry(data)
        setTelHistory(prev => {
          const next = [...prev, data]
          return next.length > MAX_TELEMETRY_HISTORY
            ? next.slice(next.length - MAX_TELEMETRY_HISTORY)
            : next
        })
      }
      ws.onclose = () => { if (active) retry = setTimeout(connect, 2000) }
      ws.onerror = () => ws.close()
    }
    connect()
    return () => { active = false; clearTimeout(retry); ws?.close() }
  }, [])

  // WebSocket: logs
  useEffect(() => {
    let ws, retry
    let active = true
    const connect = () => {
      if (!active) return
      ws = new WebSocket(WS_LOGS_URL)
      ws.onmessage = (e) => {
        const entry = JSON.parse(e.data)
        setLogs(prev => {
          const next = [...prev, entry]
          return next.length > 2000 ? next.slice(next.length - 2000) : next
        })
      }
      ws.onclose = () => { if (active) retry = setTimeout(connect, 2000) }
      ws.onerror = () => ws.close()
    }
    connect()
    return () => { active = false; clearTimeout(retry); ws?.close() }
  }, [])

  const refreshStatus = useCallback(() =>
    api.getStatus().then(setStatus).catch(() => {}), [])

  const sharedProps = { status, telemetry, telHistory, logs, refreshStatus }

  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden bg-slate-900">
        <Navbar status={status} />
        <main className="flex-1 overflow-y-auto">
           <Suspense fallback={
             <div className="flex items-center justify-center h-full text-slate-500 text-sm">
               Loading…
             </div>
           }>
             <Routes>
               <Route path="/"           element={<Dashboard {...sharedProps} />} />
               <Route path="/simulation" element={<Simulation {...sharedProps} />} />
               <Route path="/mission"    element={<Mission    {...sharedProps} />} />
               <Route path="/ml"         element={<MLTraining {...sharedProps} />} />
               <Route path="/logs"       element={<Logs       {...sharedProps} />} />
               <Route path="/hardware"   element={<Hardware   {...sharedProps} />} />
               <Route path="*"           element={<Navigate to="/" replace />} />
             </Routes>
           </Suspense>
        </main>
      </div>
    </BrowserRouter>
  )
}
