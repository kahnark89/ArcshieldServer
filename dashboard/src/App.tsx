import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import EventList from './views/EventList'
import EventDetail from './views/EventDetail'
import ThresholdDashboard from './views/ThresholdDashboard'
import './App.css'

const queryClient = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter basename="/dashboard">
        <nav className="nav">
          <span className="nav-brand">ArcShield Corpus</span>
          <NavLink to="/events" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>Events</NavLink>
          <NavLink to="/thresholds" className={({ isActive }) => isActive ? 'nav-link active' : 'nav-link'}>Thresholds</NavLink>
        </nav>
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Navigate to="/events" replace />} />
            <Route path="/events" element={<EventList />} />
            <Route path="/events/:id" element={<EventDetail />} />
            <Route path="/thresholds" element={<ThresholdDashboard />} />
          </Routes>
        </main>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
