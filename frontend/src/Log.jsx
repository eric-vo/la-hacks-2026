import { useState, useEffect } from 'react'
import './Log.css'

const EVENT_CONFIG = {
  single_click:     { label: 'Single Click',    icon: '👆', color: '#f85149' },
  double_click:     { label: 'Double Click',    icon: '👆', color: '#58a6ff', badge: '×2' },
  triple_click:     { label: 'Triple Click',    icon: '👆', color: '#3fb950', badge: '×3' },
  thumbs_up:        { label: 'Thumbs Up',       icon: '👍', color: '#d29922' },
  thumbs_down:      { label: 'Thumbs Down',     icon: '👎', color: '#e3702a' },
  media_play_pause: { label: 'Play / Pause',    icon: '⏯️',  color: '#39d2f1' },
  cursor_on:        { label: 'Cursor Mode ON',  icon: '🖱️', color: '#bc8cff' },
  cursor_off:       { label: 'Cursor Mode OFF', icon: '🖱️', color: '#6e7681' },
}

function formatTime(iso) {
  const t = iso.split('T')[1] ?? iso
  return t.slice(0, 12)
}

function EventCard({ event }) {
  const cfg = EVENT_CONFIG[event.type] ?? { label: event.label, icon: '●', color: '#7d8590' }
  return (
    <div className="event-card" style={{ '--accent': cfg.color }}>
      <span className="event-icon">{cfg.icon}</span>
      <span className="event-label">
        {cfg.label}
        {cfg.badge && <span className="event-badge">{cfg.badge}</span>}
      </span>
      <span className="event-type-pill">{event.type}</span>
      <span className="event-time">{formatTime(event.timestamp)}</span>
    </div>
  )
}

export default function Log() {
  const [events, setEvents] = useState([])
  const [isLive, setIsLive] = useState(false)

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await fetch(`/events.json?t=${Date.now()}`)
        if (res.ok) {
          setEvents(await res.json())
          setIsLive(true)
        }
      } catch {
        setIsLive(false)
      }
    }
    poll()
    const id = setInterval(poll, 1000)
    return () => clearInterval(id)
  }, [])

  const reversed = [...events].reverse()

  return (
    <div className="log-page">
      <header className="log-header">
        <div className="log-header-left">
          <h1 className="log-title">Gesture Log</h1>
          <span className={`live-dot ${isLive ? 'live' : 'offline'}`} />
          <span className="live-label">{isLive ? 'Live' : 'Offline'}</span>
        </div>
        <span className="event-count">{events.length} event{events.length !== 1 ? 's' : ''}</span>
      </header>

      <main className="log-content">
        {reversed.length === 0 ? (
          <div className="empty-state">
            <span className="empty-icon">🤚</span>
            <p>No gestures recorded yet.</p>
            <p className="empty-hint">Start <code>python main.py</code> and make a gesture.</p>
          </div>
        ) : (
          <div className="event-list">
            {reversed.map(event => (
              <EventCard key={event.id} event={event} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
