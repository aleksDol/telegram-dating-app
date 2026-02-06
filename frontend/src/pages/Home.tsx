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

function WaveSvg() {
  return (
    <svg className="home-hero-wave" viewBox="0 0 400 32" preserveAspectRatio="none" aria-hidden>
      <path d="M0 32V0h400v32c-66.5-8-133-8-200 0S66.5 32 0 32z" />
    </svg>
  )
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
      {/* Градиентный хедер с волной */}
      <header className="home-hero">
        <WaveSvg />
        <div className="home-hero-inner">
          <Logo size="md" showText link />
        </div>
      </header>

      {/* Быстрые действия — 2 кнопки */}
      <div className="home-quick-actions animate-in stagger-1">
        <Link to="/events" className="home-quick-btn">
          <span>🔍</span>
          <span>Найти встречу</span>
        </Link>
        <Link to="/create" className="home-quick-btn home-quick-btn-secondary">
          <span>🎯</span>
          <span>Создать встречу</span>
        </Link>
      </div>

      {/* Статистика — 3 колонки с подписями */}
      <div className="home-stats-cols animate-in stagger-2">
        <Link to="/my-events" className="home-stat-col">
          <span className="home-stat-num">17</span>
          <span className="home-stat-emoji">💫</span>
          <span className="home-stat-label">Мои встречи</span>
        </Link>
        <div className="home-stat-col">
          <span className="home-stat-num">{user.points}</span>
          <span className="home-stat-emoji">⭐</span>
          <span className="home-stat-label">Рейтинг</span>
        </div>
        <Link to="/referral" className="home-stat-col">
          <span className="home-stat-num">{user.referrals_count}</span>
          <span className="home-stat-emoji">👥</span>
          <span className="home-stat-label">Рефералов</span>
        </Link>
      </div>

      {/* Призыв к действию с иллюстрацией */}
      <section className="home-cta animate-in stagger-3">
        <div className="home-cta-card">
          <h2 className="home-cta-title">🎯 Не знаешь, с чего начать?</h2>
          <div className="home-cta-illus">✨</div>
          <ul className="home-cta-steps">
            <li data-step="1.">Создай встречу</li>
            <li data-step="2.">Пригласи людей</li>
            <li data-step="3.">Знакомься!</li>
          </ul>
        </div>
      </section>

      {/* Рекомендации */}
      <section className="home-recommendations animate-in stagger-4">
        <h2 className="home-recommendations-title">🔥 Популярные рядом с тобой</h2>
        <div className="home-recommendations-grid">
          <Link to="/events/sport" className="home-rec-card">
            <span className="home-rec-emoji">🏀</span>
            <span className="home-rec-label">Спорт</span>
          </Link>
          <Link to="/events/culture" className="home-rec-card">
            <span className="home-rec-emoji">🎭</span>
            <span className="home-rec-label">Культура</span>
          </Link>
          <Link to="/events/party" className="home-rec-card">
            <span className="home-rec-emoji">🍸</span>
            <span className="home-rec-label">Вечеринки</span>
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
