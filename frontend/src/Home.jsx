import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import './Home.css'

gsap.registerPlugin(ScrollTrigger)

/* MediaPipe landmark indices grouped by finger */
const CONNECTIONS = [
  [0,1],[1,2],[2,3],[3,4],           // thumb
  [0,5],[5,6],[6,7],[7,8],           // index
  [0,9],[9,10],[10,11],[11,12],      // middle
  [0,13],[13,14],[14,15],[15,16],    // ring
  [0,17],[17,18],[18,19],[19,20],    // pinky
  [5,9],[9,13],[13,17],              // palm
]

const LANDMARKS = [
  { x: 50, y: 88 },   // 0  wrist
  { x: 38, y: 78 },   // 1  thumb cmc
  { x: 28, y: 68 },   // 2  thumb mcp
  { x: 20, y: 58 },   // 3  thumb ip
  { x: 14, y: 48 },   // 4  thumb tip
  { x: 42, y: 62 },   // 5  index mcp
  { x: 40, y: 47 },   // 6  index pip
  { x: 39, y: 35 },   // 7  index dip
  { x: 38, y: 24 },   // 8  index tip
  { x: 51, y: 60 },   // 9  middle mcp
  { x: 51, y: 44 },   // 10 middle pip
  { x: 51, y: 31 },   // 11 middle dip
  { x: 51, y: 19 },   // 12 middle tip
  { x: 61, y: 62 },   // 13 ring mcp
  { x: 62, y: 47 },   // 14 ring pip
  { x: 62, y: 35 },   // 15 ring dip
  { x: 62, y: 25 },   // 16 ring tip
  { x: 70, y: 66 },   // 17 pinky mcp
  { x: 73, y: 53 },   // 18 pinky pip
  { x: 75, y: 43 },   // 19 pinky dip
  { x: 76, y: 34 },   // 20 pinky tip
]

const LANDMARK_COLORS = [
  '#94a3b8', // wrist — slate
  '#f97316','#f97316','#f97316','#f97316', // thumb — orange
  '#facc15','#facc15','#facc15','#facc15', // index — yellow
  '#34d399','#34d399','#34d399','#34d399', // middle — emerald
  '#60a5fa','#60a5fa','#60a5fa','#60a5fa', // ring — blue
  '#e879f9','#e879f9','#e879f9','#e879f9', // pinky — fuchsia
]

function HandSVG() {
  return (
    <svg className="hand-svg" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
      {/* Glow filter */}
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

      {/* Connections */}
      {CONNECTIONS.map(([a, b], i) => (
        <line
          key={i}
          className="hand-bone"
          x1={LANDMARKS[a].x} y1={LANDMARKS[a].y}
          x2={LANDMARKS[b].x} y2={LANDMARKS[b].y}
          filter="url(#glow)"
        />
      ))}

      {/* Radar pulse on fingertips */}
      {[4, 8, 12, 16, 20].map(idx => (
        <circle
          key={`pulse-${idx}`}
          className="fingertip-pulse"
          cx={LANDMARKS[idx].x}
          cy={LANDMARKS[idx].y}
          r="0"
          style={{ '--tip-color': LANDMARK_COLORS[idx] }}
        />
      ))}

      {/* Landmark dots */}
      {LANDMARKS.map((pt, i) => (
        <circle
          key={i}
          className="landmark-dot"
          cx={pt.x}
          cy={pt.y}
          r={i === 0 ? 2.2 : 1.5}
          fill={LANDMARK_COLORS[i]}
          filter="url(#glowStrong)"
        />
      ))}
    </svg>
  )
}

const FEATURES = [
  {
    icon: '🤙',
    title: 'Natural Gestures',
    desc: 'Works with gestures already familiar to ASL users. No new vocabulary to learn.',
    color: '#6366f1',
  },
  {
    icon: '🖱️',
    title: 'Full Cursor Control',
    desc: 'Point with your index finger to move the cursor. Pinch to click — single, double, or hold to drag.',
    color: '#a78bfa',
  },
  {
    icon: '⏯️',
    title: 'Media Controls',
    desc: 'The universal "stop" hand gesture plays and pauses media without touching a keyboard.',
    color: '#60a5fa',
  },
  {
    icon: '👍',
    title: 'AI Autocorrect',
    desc: 'Hold a thumbs-up after fingerspelling to send your letters to Gemma 4 — it corrects and completes your words on-device.',
    color: '#34d399',
  },
  {
    icon: '⚡',
    title: 'Real-Time at 30 FPS',
    desc: 'MediaPipe landmark detection runs entirely on-device with sub-33 ms latency per frame.',
    color: '#f59e0b',
  },
  {
    icon: '🔒',
    title: '100% Local',
    desc: 'No data ever leaves your machine. Your camera feed and gestures stay private.',
    color: '#f43f5e',
  },
]

const STEPS = [
  {
    num: '01',
    title: 'Open the dashboard',
    desc: 'Click Get Started and allow camera access. SignPC begins landmark detection immediately in your browser.',
  },
  {
    num: '02',
    title: 'Raise your index finger',
    desc: 'Extend your index finger upward. The cursor activates and follows your hand in real time.',
  },
  {
    num: '03',
    title: 'Pinch to interact',
    desc: 'Bring index finger to thumb to click. Do it twice for double-click, or hold to drag.',
  },
]

export default function Home() {
  const heroRef = useRef(null)
  const handRef = useRef(null)

  useEffect(() => {
    const ctx = gsap.context(() => {
      /* ── Hero entrance timeline ─────────────────────────── */
      const tl = gsap.timeline({ defaults: { ease: 'power3.out' } })
      tl.from('.hero-tag',      { y: 20, opacity: 0, duration: 0.6 })
        .from('.hero-headline', { y: 30, opacity: 0, duration: 0.7 }, '-=0.3')
        .from('.hero-sub',      { y: 20, opacity: 0, duration: 0.6 }, '-=0.4')
        .from('.hero-cta',      { y: 16, opacity: 0, duration: 0.5, stagger: 0.12 }, '-=0.3')
        .from('.hero-visual',   { scale: 0.85, opacity: 0, duration: 0.9, ease: 'back.out(1.4)' }, '-=0.6')

      /* ── Hand floating ──────────────────────────────────── */
      gsap.to('.hero-visual', {
        y: -18,
        duration: 3.5,
        yoyo: true,
        repeat: -1,
        ease: 'sine.inOut',
      })

      /* ── Fingertip pulse ────────────────────────────────── */
      gsap.to('.fingertip-pulse', {
        attr: { r: 5 },
        opacity: 0,
        duration: 1.2,
        stagger: { each: 0.25, repeat: -1 },
        ease: 'power2.out',
      })

      /* ── Stats bar ──────────────────────────────────────── */
      gsap.from('.stat-item', {
        scrollTrigger: { trigger: '.stats-bar', start: 'top 85%' },
        y: 24, opacity: 0, duration: 0.5, stagger: 0.12, ease: 'power2.out',
      })

      /* ── Feature cards ──────────────────────────────────── */
      gsap.from('.feature-card', {
        scrollTrigger: { trigger: '.features-grid', start: 'top 80%' },
        y: 50, opacity: 0, duration: 0.55, stagger: 0.1, ease: 'power2.out',
      })

      /* ── How-it-works steps ─────────────────────────────── */
      gsap.from('.step-card', {
        scrollTrigger: { trigger: '.steps-row', start: 'top 82%' },
        x: -50, opacity: 0, duration: 0.6, stagger: 0.15, ease: 'power2.out',
      })

      /* ── CTA section ────────────────────────────────────── */
      gsap.from('.cta-section', {
        scrollTrigger: { trigger: '.cta-section', start: 'top 88%' },
        y: 30, opacity: 0, duration: 0.7, ease: 'power2.out',
      })
    }, heroRef)

    return () => ctx.revert()
  }, [])

  return (
    <div className="home-page" ref={heroRef}>
      {/* ── Blob background ──────────────────────────────── */}
      <div className="bg-blobs" aria-hidden="true">
        <div className="blob blob-1" />
        <div className="blob blob-2" />
        <div className="blob blob-3" />
      </div>

      {/* ── Hero ─────────────────────────────────────────── */}
      <section className="hero-section">
        <div className="hero-text">
          <span className="hero-tag">Gesture-Powered Computing</span>
          <h1 className="hero-headline">
            Your hands.<br />
            <span className="hero-headline-accent">Your interface.</span>
          </h1>
          <p className="hero-sub">
            SignPC translates natural hand gestures into keyboard and mouse actions —
            designed for ASL users, those with motor impairments, and anyone who thinks
            with their hands.
          </p>
          <div className="hero-cta">
            <Link className="btn-primary" to="/live">
              Get Started
            </Link>
          </div>
        </div>

        <div className="hero-visual" ref={handRef}>
          <div className="hand-glow-ring" />
          <HandSVG />
        </div>
      </section>

      {/* ── Stats bar ────────────────────────────────────── */}
      <div className="stats-bar">
        <div className="stat-item">
          <span className="stat-num">21</span>
          <span className="stat-label">Hand Landmarks</span>
        </div>
        <div className="stat-divider" />
        <div className="stat-item">
          <span className="stat-num">30 FPS</span>
          <span className="stat-label">Real-Time Detection</span>
        </div>
        <div className="stat-divider" />
        <div className="stat-item">
          <span className="stat-num">0 ms</span>
          <span className="stat-label">Server Latency</span>
        </div>
        <div className="stat-divider" />
        <div className="stat-item">
          <span className="stat-num">100%</span>
          <span className="stat-label">On-Device & Private</span>
        </div>
      </div>

      {/* ── Features ─────────────────────────────────────── */}
      <section className="features-section">
        <div className="section-header">
          <span className="section-tag">Capabilities</span>
          <h2 className="section-title">Everything you need to control your computer</h2>
          <p className="section-sub">A complete input system built on gestures you already know.</p>
        </div>
        <div className="features-grid">
          {FEATURES.map(f => (
            <div className="feature-card" key={f.title} style={{ '--fc': f.color }}>
              <span className="feature-icon" style={{ background: `color-mix(in srgb, ${f.color} 14%, transparent)` }}>
                {f.icon}
              </span>
              <h3 className="feature-title">{f.title}</h3>
              <p className="feature-desc">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────── */}
      <section className="how-section">
        <div className="section-header">
          <span className="section-tag">How It Works</span>
          <h2 className="section-title">Up and running in seconds</h2>
        </div>
        <div className="steps-row">
          {STEPS.map((s, i) => (
            <div className="step-card" key={s.num}>
              <span className="step-num">{s.num}</span>
              {i < STEPS.length - 1 && <div className="step-connector" aria-hidden="true" />}
              <h3 className="step-title">{s.title}</h3>
              <p className="step-desc">{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────────── */}
      <section className="cta-section">
        <div className="cta-glow" aria-hidden="true" />
        <h2 className="cta-headline">Ready to go hands-free?</h2>
        <p className="cta-sub">
          Open source. No cloud. No account. Just your hands.
        </p>
        <a className="btn-primary btn-large" href="https://github.com" target="_blank" rel="noreferrer">
          View on GitHub
        </a>
      </section>
    </div>
  )
}
