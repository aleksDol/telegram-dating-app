import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { useEffect } from 'react'

export default function About() {
  const navigate = useNavigate()
  const { user, fetchUser } = useApp()

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  useEffect(() => {
    if (!user) navigate('/', { replace: true })
  }, [user, navigate])

  if (!user) return null

  return (
    <>
      <DemoBanner />
      <div className="page-header">
        <h1 className="page-title">О боте</h1>
        <p className="page-subtitle">Знакомства через встречи</p>
      </div>
      <div className="card about-block">
        <h2 className="section-title">🎯 Главная идея</h2>
        <p className="card-desc">Знакомства через совместные мероприятия. Хочешь куда-то сходить, но не знаешь с кем — создай встречу. Бот покажет её людям рядом. Откликнутся — идите.</p>
      </div>
      <div className="card about-block">
        <h2 className="section-title">✨ Что можно делать</h2>
        <ul className="about-list">
          <li>Создавать свои события (кино, кафе, прогулки)</li>
          <li>Просматривать события других</li>
          <li>Лайкать и знакомиться с организаторами</li>
          <li>Получать рекомендации и достижения</li>
          <li>Приглашать друзей и получать бонусы</li>
        </ul>
      </div>
      <div className="card about-block">
        <h2 className="section-title">💡 Как начать</h2>
        <ol className="about-steps">
          <li>Заполните профиль</li>
          <li>Создайте событие или найдите чужие</li>
          <li>Лайкайте понравившееся</li>
          <li>Знакомьтесь и встречайтесь!</li>
        </ol>
      </div>
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
      <button type="button" className="demo-banner-btn" onClick={() => navigate('/register')}>Зарегистрироваться</button>
    </div>
  )
}
