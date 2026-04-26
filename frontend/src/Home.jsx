import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { gsap } from 'gsap'
import './Home.css'

const CONNECTIONS = [
  [0,1],[1,2],[2,3],[3,4],
  [0,5],[5,6],[6,7],[7,8],
  [0,9],[9,10],[10,11],[11,12],
  [0,13],[13,14],[14,15],[15,16],
  [0,17],[17,18],[18,19],[19,20],
  [5,9],[9,13],[13,17],
]

const LANDMARKS = [
  { x: 50, y: 88 }, { x: 38, y: 78 }, { x: 28, y: 68 }, { x: 20, y: 58 }, { x: 14, y: 48 },
  { x: 42, y: 62 }, { x: 40, y: 47 }, { x: 39, y: 35 }, { x: 38, y: 24 },
  { x: 51, y: 60 }, { x: 51, y: 44 }, { x: 51, y: 31 }, { x: 51, y: 19 },
  { x: 61, y: 62 }, { x: 62, y: 47 }, { x: 62, y: 35 }, { x: 62, y: 25 },
  { x: 70, y: 66 }, { x: 73, y: 53 }, { x: 75, y: 43 }, { x: 76, y: 34 },
]

const LANDMARK_COLORS = [
  '#94a3b8',
  '#22d3ee','#22d3ee','#22d3ee','#22d3ee',
  '#facc15','#facc15','#facc15','#facc15',
  '#34d399','#34d399','#34d399','#34d399',
  '#60a5fa','#60a5fa','#60a5fa','#60a5fa',
  '#e879f9','#e879f9','#e879f9','#e879f9',
]

function HandSVG() {
  return (
    <svg className="hand-svg" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <filter id="glow">
          <feGaussianBlur stdDeviation="1.2" result="blur" />
          <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
        <filter id="glowStrong">
          <feGaussianBlur stdDeviation="2" result="blur" />
          <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>
      {CONNECTIONS.map(([a, b], i) => (
        <line
          key={i}
          className="hand-bone"
          x1={LANDMARKS[a].x} y1={LANDMARKS[a].y}
          x2={LANDMARKS[b].x} y2={LANDMARKS[b].y}
          filter="url(#glow)"
        />
      ))}
      {[4, 8, 12, 16, 20].map(idx => (
        <circle
          key={`pulse-${idx}`}
          className="fingertip-pulse"
          cx={LANDMARKS[idx].x} cy={LANDMARKS[idx].y}
          r="0"
          style={{ '--tip-color': LANDMARK_COLORS[idx] }}
        />
      ))}
      {LANDMARKS.map((pt, i) => (
        <circle
          key={i}
          className="landmark-dot"
          cx={pt.x} cy={pt.y}
          r={i === 0 ? 2.2 : 1.5}
          fill={LANDMARK_COLORS[i]}
          filter="url(#glowStrong)"
        />
      ))}
    </svg>
  )
}

const GESTURES = [
  { label: 'Raise index finger to move the cursor' },
  { label: 'Pinch thumb to index to click or drag' },
  { label: 'Fingerspell ASL letters to type text' },
  { label: 'Open palm to play or pause media' },
]

export default function Home() {
  const pageRef = useRef(null)

  useEffect(() => {
    const ctx = gsap.context(() => {
      const tl = gsap.timeline({ defaults: { ease: 'power3.out' } })
      tl.from('.hero-eyebrow',  { y: 20, opacity: 0, duration: 0.5 })
        .from('.hero-headline', { y: 30, opacity: 0, duration: 0.7 }, '-=0.3')
        .from('.hero-sub',      { y: 20, opacity: 0, duration: 0.6 }, '-=0.4')
        .from('.gesture-item',  { y: 16, opacity: 0, duration: 0.4, stagger: 0.08 }, '-=0.3')
        .from('.hero-cta',      { y: 16, opacity: 0, duration: 0.4 }, '-=0.2')
        .from('.hero-visual',   { scale: 0.88, opacity: 0, duration: 0.9, ease: 'back.out(1.4)' }, '-=0.6')

      gsap.to('.hero-visual', {
        y: -16, duration: 3.5, yoyo: true, repeat: -1, ease: 'sine.inOut',
      })

      gsap.to('.fingertip-pulse', {
        attr: { r: 5 }, opacity: 0, duration: 1.2,
        stagger: { each: 0.25, repeat: -1 }, ease: 'power2.out',
      })
    }, pageRef)

    return () => ctx.revert()
  }, [])

  return (
    <div className="home-page" ref={pageRef}>
      <div className="bg-blobs" aria-hidden="true">
        <div className="blob blob-1" />
        <div className="blob blob-2" />
      </div>

      <nav className="home-nav">
        <span className="brand">SignPC</span>
      </nav>

      <div className="hero-grid">
        <div className="hero-left">
          <p className="hero-eyebrow">Gesture-Powered Computing</p>
          <h1 className="hero-headline">
            Your hands.<br />
            <span className="hero-accent">Your interface.</span>
          </h1>
          <p className="hero-sub">
            SignPC translates natural hand gestures into cursor control
            and ASL fingerspelling into text — 100% on-device, zero cloud latency.
          </p>

          <div className="gesture-strip">
            {GESTURES.map((g, i) => (
              <div key={i} className="gesture-item">
                <span className="gesture-dot" />
                <span>{g.label}</span>
              </div>
            ))}
          </div>

          <div className="hero-cta">
            <Link to="/live" className="btn-primary">Get Started</Link>
          </div>
        </div>

        <div className="hero-visual">
          <div className="hand-glow-ring" />
          <HandSVG />
        </div>
      </div>
    </div>
  )
}
