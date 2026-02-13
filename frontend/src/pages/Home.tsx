import { useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { DEMO_USER_ID } from '../context/AppContext'
import { isApiConfigured } from '../api/client'
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

      {/* Центральная карточка — по центру экрана */}
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
