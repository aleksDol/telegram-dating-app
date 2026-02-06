import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link, useLocation } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { api, isApiConfigured } from '../api/client'
import { getDemoUserByUserId } from '../demoData'
import type { User } from '../types'

type LocationState = { fromEventId?: number } | null

export default function UserProfile() {
  const { userId } = useParams<{ userId: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const fromEventId = (location.state as LocationState)?.fromEventId
  const { user: currentUser, fetchUser, isDemo, useDemoEvents } = useApp()
  const [profile, setProfile] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  useEffect(() => {
    if (!currentUser && !userId) return
    const id = userId ? parseInt(userId, 10) : NaN
    if (Number.isNaN(id)) {
      setLoading(false)
      setError('Неверный профиль')
      return
    }
    if (isDemo || useDemoEvents) {
      const u = getDemoUserByUserId(id)
      setProfile(u ?? null)
      setError(u ? '' : 'Пользователь не найден')
      setLoading(false)
      return
    }
    if (!isApiConfigured()) {
      setProfile(getDemoUserByUserId(id) ?? null)
      setLoading(false)
      return
    }
    setLoading(true)
    setError('')
    api
      .getUserProfile(id)
      .then(({ user }) => setProfile(user))
      .catch((e) => {
        setError(e instanceof Error ? e.message : 'Ошибка')
        setProfile(null)
      })
      .finally(() => setLoading(false))
  }, [userId, isDemo, useDemoEvents, currentUser])

  if (!currentUser) {
    navigate('/', { replace: true })
    return null
  }
  if (userId && String(currentUser.user_id) === userId) {
    navigate('/profile', { replace: true })
    return null
  }

  if (loading) {
    return (
      <div className="screen-center">
        <div className="loader" />
        <p className="text-muted">Загрузка...</p>
      </div>
    )
  }

  if (error || !profile) {
    return (
      <div className="empty-state">
        <span className="empty-icon">👤</span>
        <p>{error || 'Пользователь не найден'}</p>
        <button type="button" className="btn btn-ghost" onClick={() => navigate(-1)}>
          Назад
        </button>
      </div>
    )
  }

  const isMyProfile = currentUser.user_id === profile.user_id

  return (
    <>
      <DemoBanner />
      {fromEventId != null && (
        <div className="page-header" style={{ marginBottom: 8 }}>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            onClick={() => navigate(`/event/${fromEventId}`)}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
          >
            ← Вернуться к встрече
          </button>
        </div>
      )}
      <div className="page-header">
        <h1 className="page-title">{isMyProfile ? 'Мой профиль' : 'Профиль'}</h1>
      </div>
      <div className="card profile-card">
        {profile.photo ? (
          <img src={profile.photo} alt="" className="profile-avatar" />
        ) : (
          <div className="profile-avatar-placeholder">{profile.name.slice(0, 1)}</div>
        )}
        <h2 className="profile-name">{profile.name}</h2>
        <p className="profile-meta">{profile.age} лет · {profile.gender} · {profile.city}</p>
        {profile.relationship_status && (
          <p className="profile-meta">{profile.relationship_status}</p>
        )}
        <p className="profile-purpose">Цель: {profile.purpose}</p>
        {isMyProfile && (
          <>
            <div className="profile-points">🏆 {profile.points ?? 0} очков</div>
            <Link to="/profile" className="btn btn-primary" style={{ marginTop: 12 }}>
              Редактировать профиль
            </Link>
          </>
        )}
      </div>
      {isMyProfile && (
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
      )}
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
