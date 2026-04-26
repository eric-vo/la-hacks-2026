import { createContext, useContext, useEffect, useState } from 'react'

const GestureContext = createContext(null)

const DEFAULT_STATE = {
  cursor_active: false,
  pinch_ratio: null,
  mouse_down: false,
  double_click: false,
  triple_click: false,
  thumb_up: false,
  media_gesture: false,
  media_triggered: false,
  asl_candidate: null,
  asl_typed: '',
  gemma_prediction: '',
  gemma_thinking: false,
  gemma_error: '',
}

export function GestureProvider({ children }) {
  const [state, setState] = useState(DEFAULT_STATE)
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    let ws
    let retryTimer

    function connect() {
      ws = new WebSocket(`ws://${location.host}/ws`)
      ws.onopen = () => setConnected(true)
      ws.onmessage = e => setState(JSON.parse(e.data))
      ws.onclose = () => {
        setConnected(false)
        retryTimer = setTimeout(connect, 1500)
      }
      ws.onerror = () => ws.close()
    }

    connect()
    return () => {
      clearTimeout(retryTimer)
      ws?.close()
    }
  }, [])

  return (
    <GestureContext.Provider value={{ state, connected }}>
      {children}
    </GestureContext.Provider>
  )
}

export const useGesture = () => useContext(GestureContext)
