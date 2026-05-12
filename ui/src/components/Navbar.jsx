import { NavLink } from 'react-router-dom'

const DOT_COLOR = {
  running: 'bg-emerald-400',
  stopped: 'bg-slate-600',
  idle:    'bg-slate-600',
  null:    'bg-slate-600',
}

function StatusDot({ s }) {
  return (
    <span className={`inline-block w-2 h-2 rounded-full ${DOT_COLOR[s] ?? 'bg-slate-600'} shrink-0`} />
  )
}

const NAV = [
  { to: '/',           label: 'Dashboard',   icon: IconDash },
  { to: '/simulation', label: 'Simulation',  icon: IconSim  },
  { to: '/mission',    label: 'Mission',     icon: IconMission },
  { to: '/ml',         label: 'ML Training', icon: IconML  },
  { to: '/logs',       label: 'Logs',        icon: IconLogs },
  { to: '/hardware',   label: 'Hardware',    icon: IconHardware },
]

export default function Navbar({ status }) {
  return (
    <nav className="w-52 shrink-0 bg-slate-900 border-r border-slate-800 flex flex-col py-4">
      {/* Logo */}
      <div className="px-4 mb-6">
        <div className="flex items-center gap-2">
          <span className="text-cyan-400 text-lg font-semibold tracking-wider">PEREGRINE</span>
        </div>
        <div className="text-slate-500 text-xs mt-0.5">Control Center</div>
      </div>

      {/* Links */}
      <div className="flex flex-col gap-1 px-2 flex-1">
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-slate-700 text-cyan-400'
                  : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
              }`
            }
          >
            <Icon />
            <span>{label}</span>
          </NavLink>
        ))}
      </div>

       {/* Status footer */}
       {status && (
         <div className="px-4 pt-4 border-t border-slate-800 mt-4 space-y-1.5">
           {[
             ['ROS2',  status.ros2],
             ['Sim',   status.simulation],
             ['ML',    status.ml],
             ['Hardware', status.hardware],
           ].map(([name, s]) => (
             <div key={name} className="flex items-center gap-2 text-xs text-slate-400">
               <StatusDot s={s} />
               <span>{name}</span>
               <span className="ml-auto text-slate-500">{s}</span>
             </div>
           ))}
         </div>
       )}
    </nav>
  )
}

function IconDash() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <rect x="3" y="3" width="7" height="7" rx="1" strokeWidth="2"/>
      <rect x="14" y="3" width="7" height="7" rx="1" strokeWidth="2"/>
      <rect x="3" y="14" width="7" height="7" rx="1" strokeWidth="2"/>
      <rect x="14" y="14" width="7" height="7" rx="1" strokeWidth="2"/>
    </svg>
  )
}

function IconSim() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
        d="M15 10l4.553-2.277A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z"/>
    </svg>
  )
}

function IconMission() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
        d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-1.447-.894L15 9m0 8V9m0 0L9 7"/>
    </svg>
  )
}

function IconML() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <circle cx="12" cy="5" r="2" strokeWidth="2"/>
      <circle cx="5"  cy="19" r="2" strokeWidth="2"/>
      <circle cx="19" cy="19" r="2" strokeWidth="2"/>
      <path strokeLinecap="round" strokeWidth="2" d="M12 7v4M12 11l-5 6M12 11l5 6"/>
    </svg>
  )
}

function IconLogs() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
        d="M4 6h16M4 10h16M4 14h10M4 18h8"/>
    </svg>
  )
}

function IconHardware() {
  return (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
        d="M9 12h6m2 0a2 2 0 110-4h-1a1 1 0 00-1 1v2h-2v-2a1 1 0 00-1-1h-1a2 2 0 110 4zM3 8a2 2 0 012-2h1a1 1 0 000-2H3a2 2 0 01-2 2v4a2 2 0 002 2h1a1 1 0 000-2H3z"/>
    </svg>
  )
}
