import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { DEMO_USER_ID } from '../context/AppContext'
import { isApiConfigured, api } from '../api/client'
import Logo from '../components/Logo'
import type { User } from '../types'

import heroPageImg from '../img/hero-page.jpeg'

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
  const [myEventsCount, setMyEventsCount] = useState(0)

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  useEffect(() => {
    if (!user || !isApiConfigured()) {
      setMyEventsCount(0)
      return
    }
    api
      .getMyEvents()
      .then((res) => setMyEventsCount(res.events?.length ?? 0))
      .catch(() => setMyEventsCount(0))
  }, [user])

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
    <div className="home-cosmic">
      <DemoBanner />
      <div className="home-cosmic-bg" aria-hidden />
      {/* Логотип и слоган */}
      <header className="home-cosmic-hero animate-in stagger-1">
        <div className="home-cosmic-logo-wrap">
          <div className="home-cosmic-logo-circle">
            <span className="home-cosmic-logo-text">SponTime</span>
          </div>
        </div>
        <p className="home-cosmic-tagline">
          <span className="home-cosmic-tagline-line home-cosmic-tagline-line-left" aria-hidden />
          Знакомься по-новому
          <span className="home-cosmic-tagline-line home-cosmic-tagline-line-right" aria-hidden />
        </p>
      </header>

      {/* Две кнопки с градиентами */}
      <div className="home-quick-actions home-quick-actions-cosmic animate-in stagger-2">
        <Link to="/events" className="home-quick-btn home-quick-btn-find">
          <span className="home-quick-btn-icon" aria-hidden>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
          </span>
          <span>Найти встречу</span>
        </Link>
        <Link to="/create" className="home-quick-btn home-quick-btn-create">
          <span className="home-quick-btn-icon" aria-hidden>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>
          </span>
          <span>Создать встречу</span>
        </Link>
      </div>

      {/* Статистика — 3 карточки в космическом стиле */}
      <div className="home-stats-cols home-stats-cosmic animate-in stagger-3">
        <Link to="/my-events" className="home-stat-col home-stat-cosmic">
          <span className="home-stat-num">{myEventsCount}</span>
          <span className="home-stat-icon home-stat-icon-meetings" aria-hidden>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83M12 8a4 4 0 1 1 0 8 4 4 0 0 1 0-8z"/></svg>
          </span>
          <span className="home-stat-label">Мои встречи</span>
        </Link>
        <div className="home-stat-col home-stat-cosmic">
          <span className="home-stat-num">{user.points}</span>
          <span className="home-stat-icon home-stat-icon-rating" aria-hidden>
            <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
          </span>
          <span className="home-stat-label">Рейтинг</span>
        </div>
        <Link to="/referral" className="home-stat-col home-stat-cosmic">
          <span className="home-stat-num">{user.referrals_count}</span>
          <span className="home-stat-icon home-stat-icon-referrals" aria-hidden>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          </span>
          <span className="home-stat-label">Рефералов</span>
        </Link>
      </div>

      {/* Призыв к действию — в тёмном стиле */}
      <section className="home-cta home-cta-cosmic animate-in stagger-4">
        <div className="home-cta-card home-cta-card-cosmic">
          <h2 className="home-cta-title">Не знаешь, с чего начать?</h2>
          <div className="home-cta-illus home-cta-illus-cosmic">
            <img src={heroPageImg} alt="" className="home-cta-illus-img" />
          </div>
          <ul className="home-cta-steps">
            <li data-step="1.">Создай встречу</li>
            <li data-step="2.">Пригласи людей</li>
            <li data-step="3.">Знакомься!</li>
          </ul>
        </div>
      </section>

      {/* Рекомендации — в тёмном стиле */}
      <section className="home-recommendations home-recommendations-cosmic animate-in stagger-5">
        <h2 className="home-recommendations-title">Популярные рядом с тобой</h2>
        <div className="home-recommendations-grid">
          <Link to="/events/sport" className="home-rec-card home-rec-card-cosmic">
            <span className="home-rec-emoji">🏀</span>
            <span className="home-rec-label">Спорт</span>
          </Link>
          <Link to="/events/culture" className="home-rec-card home-rec-card-cosmic">
            <span className="home-rec-emoji">🎭</span>
            <span className="home-rec-label">Культура</span>
          </Link>
          <Link to="/events/party" className="home-rec-card home-rec-card-cosmic">
            <span className="home-rec-emoji">🍸</span>
            <span className="home-rec-label">Вечеринки</span>
          </Link>
        </div>
      </section>
    </div>
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
