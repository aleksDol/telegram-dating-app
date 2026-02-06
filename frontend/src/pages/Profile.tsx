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
      <div className="card profile-card animate-in stagger-1">
        {user.photo && (
          <img src={user.photo} alt="" className="profile-avatar" />
        )}
        {!user.photo && <div className="profile-avatar-placeholder">{user.name.slice(0, 1)}</div>}
        <h2 className="profile-name">{user.name}</h2>
        <p className="profile-meta">{user.age} лет · {user.gender} · {user.city}</p>
        {user.relationship_status && <p className="profile-meta">{user.relationship_status}</p>}
        <p className="profile-purpose">Цель: {user.purpose}</p>
        <div className="profile-points">🏆 {user.points} очков</div>
        <Link to="/profile/edit" className="btn btn-primary" style={{ marginTop: 16 }}>
          ✏️ Редактировать профиль
        </Link>
      </div>
      <section className="section">
        <Link to="/achievements" className="card card-row">
          <span className="card-icon">🏆</span>
          <div><span className="card-title">Достижения</span></div>
          <span className="card-arrow">→</span>
        </Link>
        <Link to="/referral" className="card card-row">
          <span className="card-icon">👥</span>
          <div><span className="card-title">Реферальная программа</span></div>
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
      <button type="button" className="demo-banner-btn" onClick={() => navigate('/register')}>Зарегистрироваться</button>
    </div>
  )
}
