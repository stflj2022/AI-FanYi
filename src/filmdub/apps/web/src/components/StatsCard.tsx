import { Card, Statistic } from 'antd'
import { ReactNode } from 'react'

interface StatsCardProps {
  title: string
  value: number | string
  prefix?: ReactNode
  suffix?: ReactNode
  valueStyle?: React.CSSProperties
  loading?: boolean
}

function StatsCard({ title, value, prefix, suffix, valueStyle, loading }: StatsCardProps) {
  return (
    <Card>
      <Statistic
        title={title}
        value={value}
        prefix={prefix}
        suffix={suffix}
        valueStyle={valueStyle}
        loading={loading}
      />
    </Card>
  )
}

export default StatsCard
