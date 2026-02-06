import { useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { DEMO_USER_ID } from '../context/AppContext'
import { isApiConfigured } from '../api/client'
import Logo from '../components/Logo'
import type { User } from '../types'

const MOCK_USER: User = {
  user_id: DEMO_USER_ID,
  name: 'Гость',
  age: 25,
  gender: 'Мужской',
  city: 'Москва',
  relationship_status: 'Не в отношениях',
  purpose: 'куда-то сходить',
  points: 120,
  referrals_count: 0,
}

export default function Home() {
  const navigate = useNavigate()
  const { user, loading, fetchUser, setUser } = useApp()

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  if (loading) {
    return (
      <div className="screen-center">
        <div className="loader" />
        <p className="text-muted">Загрузка...</p>
      </div>
    )
  }

  // Не залогинен: при подключённом API — сразу на регистрацию, иначе — приветствие и выбор
  if (!user) {
    if (isApiConfigured()) {
      navigate('/register', { replace: true })
      return (
        <div className="screen-center">
          <div className="loader" />
          <p className="text-muted">Переход к регистрации...</p>
        </div>
      )
    }
    return (
      <div className="hero">
        <div className="hero-bg" />
        <div className="hero-orb hero-orb-1" aria-hidden />
        <div className="hero-orb hero-orb-2" aria-hidden />
        <div className="hero-orb hero-orb-3" aria-hidden />
        <div className="hero-content">
          <div className="animate-in stagger-1">
            <Logo size="lg" showText link={false} />
          </div>
          <h1 className="hero-title hero-title-sub animate-in stagger-2">Найди компанию для встречи</h1>
          <p className="hero-subtitle animate-in stagger-3">
            Хочешь куда-то сходить, но не знаешь с кем — создай встречу. Бот покажет её людям рядом. Откликнутся — идите.
          </p>
          <div className="hero-actions animate-in stagger-4">
            <button
              type="button"
              className="btn btn-primary btn-lg"
              onClick={() => {
                setUser(MOCK_USER)
                navigate('/')
              }}
            >
              Посмотреть все страницы
            </button>
            <p className="hero-hint">Откроются главная, события, профиль, достижения и остальные разделы без сервера</p>
            <button
              type="button"
              className="btn btn-ghost btn-lg"
              onClick={() => navigate('/register')}
            >
              Зарегистрироваться (нужен бэкенд)
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <>
      <DemoBanner />
      <div className="page-header page-header-with-logo">
        <Logo size="sm" showText link />
        <h1 className="page-title animate-in">Привет, {user.name} 👋</h1>
        <p className="page-subtitle animate-in stagger-1">
          Хочешь куда-то сходить — создай встречу или найдите события рядом.
        </p>
      </div>

      <section className="section home-stats-section">
        <div className="home-stats-row animate-in stagger-1">
          <Link to="/my-events" className="card home-stat-card home-stat-events">
            <span className="home-stat-icon">📅</span>
            <span className="home-stat-value">Мои события</span>
            <span className="home-stat-label">Управление встречами</span>
          </Link>
          <Link to="/referral" className="card home-stat-card home-stat-referrals">
            <span className="home-stat-icon">👥</span>
            <span className="home-stat-value">{user.referrals_count}</span>
            <span className="home-stat-label">Рефералов</span>
          </Link>
        </div>
        <div className="home-stats-row animate-in stagger-2">
          <div className="card home-stat-card home-stat-rating">
            <span className="home-stat-icon">⭐</span>
            <span className="home-stat-value">{user.points}</span>
            <span className="home-stat-label">Рейтинг</span>
          </div>
          <Link to="/about" className="card home-stat-card home-stat-about">
            <span className="home-stat-icon">ℹ️</span>
            <span className="home-stat-value">О боте</span>
            <span className="home-stat-label">Как это работает</span>
          </Link>
        </div>
      </section>
    </>
  )
}

function DemoBanner() {
  const { isDemo } = useApp()
  const navigate = useNavigate()
  if (!isDemo) return null
  return (
    <div className="demo-banner">
      <span>Режим просмотра</span>
      <button type="button" className="demo-banner-btn" onClick={() => navigate('/register')}>
        Зарегистрироваться
      </button>
    </div>
  )
}
