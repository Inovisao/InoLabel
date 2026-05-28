import { useEffect, useRef, useCallback } from 'react'
import { useAnnotationStore } from '@/stores/annotationStore'
import type { AnnotationState } from '@/lib/types'

const WS_URL = `ws://${window.location.hostname}:${
  window.location.hostname === 'localhost' ? '7432' : window.location.port
}/ws`

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const setState = useAnnotationStore(s => s.setState)

  const send = useCallback((action: string, payload?: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action, ...payload }))
    }
  }, [])

  useEffect(() => {
    let retryTimeout: ReturnType<typeof setTimeout>

    const connect = () => {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data) as AnnotationState
          if (data.active !== undefined) setState(data)
        } catch { /* ignore malformed */ }
      }

      ws.onclose = () => {
        retryTimeout = setTimeout(connect, 2000)
      }

      ws.onerror = () => ws.close()
    }

    connect()
    return () => {
      clearTimeout(retryTimeout)
      wsRef.current?.close()
    }
  }, [setState])

  return { send }
}
