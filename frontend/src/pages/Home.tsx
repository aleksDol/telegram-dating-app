import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { DEMO_USER_ID } from '../context/AppContext'
import { isApiConfigured, api } from '../api/client'
import Logo from '../components/Logo'
import type { User } from '../types'

import firstPageImg from '../img/first-page.jpeg'

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
      {/* Шапка с градиентом: логотип + SponTime */}
      <header className="home-header-bar animate-in stagger-1">
        <div className="home-header-bar-inner">
          <div className="home-header-logo-circle">
            <img src="/images/Spon.png" alt="" className="home-header-logo-img" />
          </div>
          <span className="home-header-app-name">SponTime</span>
        </div>
      </header>

      {/* Фон: неоновое фото first-page */}
      <div className="home-first-page-bg" style={{ backgroundImage: `url(${firstPageImg})` }} aria-hidden />

      {/* Центральная карточка */}
      <section className="home-main-card-wrap animate-in stagger-2">
        <div className="home-main-card">
          <h1 className="home-main-card-title">Знакомься по-новому</h1>
          <p className="home-main-card-text">
            Привет, ты можешь создать встречу, например «Пойти в клуб» и те кто захочет составить компанию откликнутся.
          </p>
          <p className="home-main-card-text">
            Или можешь найти встречу, к которой хочешь присоединиться и если тебе ответят симпатией, то встреча состоится.
          </p>
          <Link to="/create" className="home-main-card-btn">
            Создать встречу
          </Link>
        </div>
      </section>

      {/* Нижние блоки: Мои встречи, Рейтинг, Рефералов */}
      <div className="home-stats-cols home-stats-cosmic animate-in stagger-3">
        <Link to="/my-events" className="home-stat-col home-stat-cosmic">
          <span className="home-stat-num">{myEventsCount}</span>
          <span className="home-stat-icon home-stat-icon-meetings" aria-hidden>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
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
