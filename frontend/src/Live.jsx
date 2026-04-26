import { useGesture } from './GestureContext'
import './Live.css'

function StatusBadge({ on, labelOn, labelOff }) {
  return (
    <span className={`status-badge ${on ? 'badge-on' : 'badge-off'}`}>
      <span className="badge-dot" />
      {on ? labelOn : labelOff}
    </span>
  )
}

function Panel({ title, children }) {
  return (
    <div className="live-panel-card">
      <h3 className="panel-title">{title}</h3>
      {children}
    </div>
  )
}

function PinchBar({ ratio }) {
  const pct = ratio != null ? Math.min(Math.max((1 - ratio) * 100, 0), 100) : 0
  const color = ratio != null && ratio < 0.25 ? '#f85149' : ratio != null && ratio < 0.45 ? '#d29922' : '#3fb950'
  return (
    <div className="pinch-bar-wrap">
      <div className="pinch-bar-track">
        <div className="pinch-bar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="pinch-bar-label">
        {ratio != null ? ratio.toFixed(2) : '—'}
      </span>
    </div>
  )
}

export default function Live() {
  const { state, connected } = useGesture()

  const clickLabel = state.double_click
    ? '⚡ Double Click'
    : state.mouse_down
      ? '🔴 Holding'
      : '—'

  return (
    <div className="live-page">
      {/* ── Connection badge ── */}
      <div className="live-topbar">
        <h1 className="live-title">Live Dashboard</h1>
        <span className={`conn-badge ${connected ? 'conn-on' : 'conn-off'}`}>
          <span className="conn-dot" />
          {connected ? 'Connected' : 'Offline — start server.py'}
        </span>
      </div>

      <div className="live-body">
        {/* ── Camera feed ── */}
        <div className="live-camera-wrap">
          {connected
            ? <img className="live-camera" src="http://localhost:8000/video" alt="live hand tracking feed" />
            : <div className="live-camera-placeholder">
              <span>📷</span>
              <p>Waiting for server…</p>
            </div>
          }
        </div>

        {/* ── Sidebar: mode indicator + status panels ── */}
        <div className="live-sidebar">
          <div className="mode-indicator" style={{
            textAlign: 'center',
            padding: '12px',
            backgroundColor: state.active_mode === 'typing' ? 'rgba(220, 120, 0, 0.1)' : 'rgba(40, 220, 40, 0.1)',
            border: `2px solid ${state.active_mode === 'typing' ? '#dc7800' : '#28dc28'}`,
            borderRadius: '8px',
            fontWeight: 'bold',
          }}>
            <span style={{ fontSize: '18px', color: state.active_mode === 'typing' ? '#dc7800' : '#28dc28' }}>
              Mode: {state.active_mode === 'typing' ? '⌨️ TYPING' : '🖱️ CONTROL'}
            </span>
            <p style={{ margin: '8px 0 0 0', fontSize: '12px', color: '#888' }}>
              Thumbs down to switch
            </p>
          </div>

          {/* ── Status panels ── */}
          <div className="live-panels">
            {state.active_mode === 'control' ? (
              <>
                <Panel title="Cursor Mode">
                  <StatusBadge on={state.cursor_active} labelOn="Active" labelOff="Inactive" />
                  <p className="panel-hint">
                    {state.cursor_active ? 'C-claw grip active — move hand to steer' : 'Raise index finger to activate'}
                  </p>
                </Panel>

                <Panel title="Pinch">
                  <PinchBar ratio={state.pinch_ratio} />
                  <p className="panel-hint">Quick tap = single click · ×2 = double · hold = drag</p>
                </Panel>

                <Panel title="Click State">
                  <span className={`click-label ${(state.mouse_down || state.double_click || state.triple_click) ? 'click-active' : ''}`}>
                    {clickLabel}
                  </span>
                </Panel>

                <Panel title="Media">
                  <StatusBadge
                    on={state.media_triggered}
                    labelOn="▶︎ Play / Pause fired"
                    labelOff={state.media_gesture ? 'Holding open palm…' : 'Ready'}
                  />
                </Panel>
              </>
            ) : (
              <>
                <Panel title="ASL Input">
                  <div className="asl-row">
                    <span className="asl-candidate">{state.asl_candidate ?? '—'}</span>
                    <span className="asl-typed">{state.asl_typed || <em>nothing typed yet</em>}</span>
                  </div>
                </Panel>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
