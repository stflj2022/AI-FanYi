// 验证后端 /ws 原生 WebSocket 协议：发 ping 应收到 pong
const url = 'ws://127.0.0.1:8000/ws'
const ws = new WebSocket(url)
const timeout = setTimeout(() => { console.log('TIMEOUT: no pong'); process.exit(1) }, 5000)

ws.onopen = () => {
  console.log('open, sending ping')
  ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }))
}

ws.onmessage = (e) => {
  const msg = String(e.data)
  console.log('got:', msg)
  try {
    const d = JSON.parse(msg)
    if (d.type === 'pong') {
      console.log('PONG RECEIVED — WS 协议对接成功')
      clearTimeout(timeout)
      ws.close()
      process.exit(0)
    }
  } catch {}
}

ws.onerror = (e) => { console.log('ws error', String(e?.message || e)); process.exit(1) }
ws.onclose = () => { console.log('closed') }
