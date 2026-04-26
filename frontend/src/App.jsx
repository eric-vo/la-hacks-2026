import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { GestureProvider } from './GestureContext'
import Home from './Home'
import Live from './Live'

export default function App() {
  return (
    <BrowserRouter>
      <GestureProvider>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/live" element={<Live />} />
        </Routes>
      </GestureProvider>
    </BrowserRouter>
  )
}
