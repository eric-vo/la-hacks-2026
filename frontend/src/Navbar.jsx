import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import './Navbar.css'

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <nav className={`navbar ${scrolled ? 'scrolled' : ''}`}>
      <NavLink to="/" className="nav-logo">
        <span className="nav-logo-icon">✋</span>
        <span className="nav-logo-text">HandBridge</span>
      </NavLink>

      <div className="nav-links">
        <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          Home
        </NavLink>
        <NavLink to="/live" className={({ isActive }) => `nav-link nav-link-live ${isActive ? 'active' : ''}`}>
          <span className="nav-live-dot" />
          Live
        </NavLink>
        <NavLink to="/log" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
          Log
        </NavLink>
      </div>
    </nav>
  )
}
