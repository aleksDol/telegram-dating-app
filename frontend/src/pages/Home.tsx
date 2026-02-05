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
  const { user, loading, fetchUser, setUser, setUseDemoEvents } = useApp()

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
        <div className="hero-content">
          <Logo size="lg" showText link={false} />
          <h1 className="hero-title hero-title-sub">Найди компанию для встречи</h1>
          <p className="hero-subtitle">
            Хочешь куда-то сходить, но не знаешь с кем — создай встречу. Бот покажет её людям рядом. Откликнутся — идите.
          </p>
          <div className="hero-actions">
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
        <h1 className="page-title">Привет, {user.name} 👋</h1>
        <p className="page-subtitle">
          Хочешь куда-то сходить — создай встречу или найдите события рядом.
        </p>
      </div>

      <div className="card-grid">
        <Link to="/events" className="card card-action">
          <span className="card-icon">🔍</span>
          <span className="card-title">Найти события</span>
          <span className="card-desc">Популярные, рядом, сегодня</span>
        </Link>
        <Link to="/create" className="card card-action">
          <span className="card-icon">🎉</span>
          <span className="card-title">Создать событие</span>
          <span className="card-desc">Кино, кафе, прогулка</span>
        </Link>
        <Link to="/my-events" className="card card-action">
          <span className="card-icon">📅</span>
          <span className="card-title">Мои события</span>
          <span className="card-desc">Управление встречами</span>
        </Link>
      </div>

      <section className="section">
        <h2 className="section-title">Аккаунт</h2>
        <button
          type="button"
          className="card card-row card-action"
          onClick={() => {
            setUseDemoEvents(true)
            navigate('/events')
          }}
        >
          <span className="card-icon">👀</span>
          <div>
            <span className="card-title">Посмотреть примеры событий</span>
            <span className="card-meta">Демо-карточки без бэкенда</span>
          </div>
          <span className="card-arrow">→</span>
        </button>
        <Link to="/achievements" className="card card-row">
          <span className="card-icon">🏆</span>
          <div>
            <span className="card-title">Достижения</span>
            <span className="card-meta">Очков: {user.points}</span>
          </div>
          <span className="card-arrow">→</span>
        </Link>
        <Link to="/referral" className="card card-row">
          <span className="card-icon">👥</span>
          <div>
            <span className="card-title">Реферальная программа</span>
            <span className="card-meta">Приглашай друзей</span>
          </div>
          <span className="card-arrow">→</span>
        </Link>
        <Link to="/about" className="card card-row">
          <span className="card-icon">ℹ️</span>
          <div>
            <span className="card-title">О боте</span>
          </div>
          <span className="card-arrow">→</span>
        </Link>
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
