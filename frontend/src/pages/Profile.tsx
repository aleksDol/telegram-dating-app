import { useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'

export default function Profile() {
  const navigate = useNavigate()
  const { user, loading, fetchUser } = useApp()

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  useEffect(() => {
    if (!loading && !user) navigate('/', { replace: true })
  }, [loading, user, navigate])

  if (loading) return <div className="screen-center"><div className="loader" /><p className="text-muted">Загрузка...</p></div>
  if (!user) return null

  return (
    <>
      <DemoBanner />
      <div className="page-header">
        <h1 className="page-title animate-in">Мой профиль</h1>
      </div>

      {/* Верх: фото слева в квадрате со скруглёнными углами */}
      <div className="profile-top animate-in stagger-1">
        <div className="profile-photo-wrap">
          {user.photo ? (
            <img src={user.photo} alt="" className="profile-photo" />
          ) : (
            <div className="profile-photo-placeholder">{user.name.slice(0, 1)}</div>
          )}
        </div>
        <Link to="/profile/edit" className="btn btn-ghost btn-sm profile-edit-btn">
          ✏️ Редактировать
        </Link>
      </div>

      {/* Обо мне */}
      <section className="profile-about card animate-in stagger-2">
        <h2 className="profile-about-title">Обо мне</h2>
        <h3 className="profile-name">{user.name}</h3>
        <p className="profile-meta">{user.age} лет · {user.gender}{user.city ? ` · ${user.city}` : ''}</p>
        {user.relationship_status && <p className="profile-meta">{user.relationship_status}</p>}
        <p className="profile-purpose">Цель: {user.purpose}</p>
        <div className="profile-points">🏆 {user.points} очков</div>
      </section>

      {/* Блок с фото */}
      <section className="profile-photo-block card animate-in stagger-3">
        <h2 className="profile-block-title">Фото</h2>
        <div className="profile-photo-main">
          {user.photo ? (
            <img src={user.photo} alt="" className="profile-photo-main-img" />
          ) : (
            <div className="profile-photo-main-placeholder">
              <span className="profile-photo-main-emoji">📷</span>
              <span>Фото можно добавить в редактировании профиля</span>
            </div>
          )}
        </div>
      </section>

      {/* Реферальная программа и Достижения — в один ряд: слева и справа */}
      <div className="profile-actions-row animate-in stagger-4">
        <Link to="/referral" className="card profile-action-card profile-action-referral">
          <span className="profile-action-icon">👥</span>
          <span className="profile-action-title">Реферальная программа</span>
          <span className="profile-action-meta">Приглашай друзей</span>
          <span className="profile-action-arrow">→</span>
        </Link>
        <Link to="/achievements" className="card profile-action-card profile-action-achievements">
          <span className="profile-action-icon">🏆</span>
          <span className="profile-action-title">Достижения</span>
          <span className="profile-action-meta">{user.points} очков</span>
          <span className="profile-action-arrow">→</span>
        </Link>
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
