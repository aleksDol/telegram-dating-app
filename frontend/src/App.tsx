import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { useTelegram } from './hooks/useTelegram'
import { AppProvider } from './context/AppContext'
import Home from './pages/Home'
import Register from './pages/Register'
import Profile from './pages/Profile'
import Events from './pages/Events'
import CreateEvent from './pages/CreateEvent'
import MyEvents from './pages/MyEvents'
import Achievements from './pages/Achievements'
import Referral from './pages/Referral'
import About from './pages/About'
import EventDetail from './pages/EventDetail'
import UserProfile from './pages/UserProfile'
import EditProfile from './pages/EditProfile'
import EditEvent from './pages/EditEvent'
import Likes from './pages/Likes'

function Nav() {
  const location = useLocation()
  const path = location.pathname
  const isRegister = path.startsWith('/register')
  const isEventDetail = path.startsWith('/event/')

  if (isRegister || isEventDetail) return null

  return (
    <nav className="nav-bottom">
      <NavLink to="/" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
        <span>🏠</span>
        <span>Главная</span>
      </NavLink>
      <NavLink to="/events" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
        <span>🔍</span>
        <span>События</span>
      </NavLink>
      <NavLink to="/likes" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
        <span>💌</span>
        <span>Лайки</span>
      </NavLink>
      <NavLink to="/create" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
        <span>🎉</span>
        <span>Создать</span>
      </NavLink>
      <NavLink to="/my-events" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
        <span>📅</span>
        <span>Мои</span>
      </NavLink>
      <NavLink to="/profile" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
        <span>👤</span>
        <span>Профиль</span>
      </NavLink>
    </nav>
  )
}

export default function App() {
  useTelegram()

  return (
    <AppProvider>
    <BrowserRouter>
      <div className="app">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/register" element={<Register />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/profile/edit" element={<EditProfile />} />
          <Route path="/profile/:userId" element={<UserProfile />} />
          <Route path="/events" element={<Events />} />
          <Route path="/events/:filter" element={<Events />} />
          <Route path="/likes" element={<Likes />} />
          <Route path="/event/:id" element={<EventDetail />} />
          <Route path="/event/:id/edit" element={<EditEvent />} />
          <Route path="/create" element={<CreateEvent />} />
          <Route path="/my-events" element={<MyEvents />} />
          <Route path="/achievements" element={<Achievements />} />
          <Route path="/referral" element={<Referral />} />
          <Route path="/about" element={<About />} />
        </Routes>
      </div>
      <Nav />
    </BrowserRouter>
    </AppProvider>
  )
}
