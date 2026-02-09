import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { useTelegram } from './hooks/useTelegram'
import { AppProvider } from './context/AppContext'
import ErrorBoundary from './components/ErrorBoundary'
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

import navHome from './img/hom-page.png'
import navMeets from './img/metts.png'
import navCreate from './img/create.png'
import navLikes from './img/likes.png'
import navProfile from './img/user.png'
import bgImage from './img/bg.jpeg'

function Nav() {
  const location = useLocation()
  const path = location.pathname
  const isRegister = path.startsWith('/register')
  const isEventDetail = path.startsWith('/event/')

  if (isRegister || isEventDetail) return null

  return (
    <nav className="nav-bottom">
      <NavLink to="/" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
        <img src={navHome} alt="" className="nav-item-icon" />
        <span>Главная</span>
      </NavLink>
      <NavLink to="/events" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
        <img src={navMeets} alt="" className="nav-item-icon" />
        <span>Встречи</span>
      </NavLink>
      <NavLink to="/create" className={({ isActive }) => `nav-item nav-item-center ${isActive ? 'active' : ''}`}>
        <img src={navCreate} alt="" className="nav-item-icon" />
        <span>Создать</span>
      </NavLink>
      <NavLink to="/likes" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
        <img src={navLikes} alt="" className="nav-item-icon" />
        <span>Отклики</span>
      </NavLink>
      <NavLink to="/profile" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
        <img src={navProfile} alt="" className="nav-item-icon" />
        <span>Профиль</span>
      </NavLink>
    </nav>
  )
}

export default function App() {
  useTelegram()

  return (
    <AppProvider>
    <ErrorBoundary>
    <BrowserRouter>
      <div className="app-bg" style={{ backgroundImage: `url(${bgImage})` }} aria-hidden />
      <div className="app">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/register" element={<Register />} />
          <Route path="/profile/edit" element={<EditProfile />} />
          <Route path="/profile/:userId" element={<UserProfile />} />
          <Route path="/profile" element={<Profile />} />
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
    </ErrorBoundary>
    </AppProvider>
  )
}
