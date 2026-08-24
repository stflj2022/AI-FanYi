import { useEffect, useState } from 'react'

interface HealthStatus {
  status: string
  version: string
  service: string
}

export function HealthCheck() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/health`)
      .then((res) => res.json())
      .then((data) => {
        setHealth(data)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  if (loading) return <div>Loading...</div>
  if (error) return <div>Error: {error}</div>

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Health Check</h1>
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <pre className="text-sm">{JSON.stringify(health, null, 2)}</pre>
      </div>
    </div>
  )
}
