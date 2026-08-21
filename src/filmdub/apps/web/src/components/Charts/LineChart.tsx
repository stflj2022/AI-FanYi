import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface LineChartProps {
  data: any[]
  xKey: string
  yKey: string
  title?: string
  color?: string
}

export default function LineChartComponent({ data, xKey, yKey, title, color = '#1890ff' }: LineChartProps) {
  return (
    <div>
      {title && <h3 style={{ marginBottom: 16 }}>{title}</h3>}
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={xKey} />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey={yKey} stroke={color} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
