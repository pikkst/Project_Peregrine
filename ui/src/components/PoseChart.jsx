import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

const TOOLTIP_STYLE = {
  backgroundColor: '#1e293b',
  border: '1px solid #475569',
  borderRadius: '6px',
  color: '#f1f5f9',
  fontSize: '11px',
  fontFamily: 'monospace',
}

export default function PoseChart({ data, height = 180 }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis
          dataKey="t"
          stroke="#475569"
          tick={{ fontSize: 10, fill: '#64748b' }}
          tickFormatter={v => `${v}s`}
        />
        <YAxis
          stroke="#475569"
          tick={{ fontSize: 10, fill: '#64748b' }}
          domain={['auto', 'auto']}
        />
        <Tooltip
          contentStyle={TOOLTIP_STYLE}
          labelFormatter={v => `t=${v}s`}
          formatter={(v, name) => [v.toFixed(3), name]}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} />
        <Line type="monotone" dataKey="x" stroke="#06b6d4" dot={false} strokeWidth={1.5} isAnimationActive={false} />
        <Line type="monotone" dataKey="y" stroke="#a78bfa" dot={false} strokeWidth={1.5} isAnimationActive={false} />
        <Line type="monotone" dataKey="z" stroke="#34d399" dot={false} strokeWidth={1.5} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  )
}
