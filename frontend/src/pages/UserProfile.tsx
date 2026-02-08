import { useEffect, useState, useMemo } from 'react'
import { useParams, useNavigate, Link, useLocation } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { api, isApiConfigured, API_BASE } from '../api/client'
import { getDemoUserByUserId } from '../demoData'
import PhotoViewer from '../components/PhotoViewer'
import type { User } from '../types'

function resolvePhotoUrl(url: string): string {
  if (!url) return ''
  if (url.startsWith('data:') || url.startsWith('http')) return url
  return API_BASE + url
}

type LocationState = { fromEventId?: number; fromLikes?: boolean } | null

export default function UserProfile() {
  const { userId } = useParams<{ userId: string }>()
  const navigate = useNavigate()
  const location = useLocation()
  const locationState = location.state as LocationState
  const fromEventId = locationState?.fromEventId
  const fromLikes = locationState?.fromLikes
  const { user: currentUser, fetchUser, loading: userLoading, isDemo, useDemoEvents } = useApp()
  const [profile, setProfile] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [photoViewerOpen, setPhotoViewerOpen] = useState(false)

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  useEffect(() => {
    if (!userId) return
    setProfile(null)
    setError('')
    setLoading(true)
    const id = parseInt(userId, 10)
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
    setError('')
    api
      .getUserProfile(id)
      .then(({ user }) => setProfile(user))
      .catch((e) => {
        setError(e instanceof Error ? e.message : 'Ошибка')
        setProfile(null)
      })
      .finally(() => setLoading(false))
  }, [userId, isDemo, useDemoEvents])

  if (userId && currentUser && String(currentUser.user_id) === userId) {
    navigate('/profile', { replace: true })
    return (
      <div className="screen-center">
        <div className="loader" />
        <p className="text-muted">Переход в профиль...</p>
      </div>
    )
  }
  if (userLoading && !profile) {
    return (
      <div className="screen-center">
        <div className="loader" />
        <p className="text-muted">Загрузка...</p>
      </div>
    )
  }
  if (!currentUser && !profile && !loading) {
    navigate('/', { replace: true })
    return (
      <div className="screen-center">
        <div className="loader" />
        <p className="text-muted">Перенаправление...</p>
      </div>
    )
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

  const isMyProfile = Boolean(currentUser && currentUser.user_id === profile.user_id)

  const profilePhotos = useMemo(() => {
    const list = profile.photos?.length ? profile.photos : (profile.photo ? [profile.photo] : [])
    return list.map(resolvePhotoUrl).filter(Boolean)
  }, [profile?.photo, profile?.photos])

  return (
    <>
      <DemoBanner />
      {(fromEventId != null || fromLikes) && (
        <div className="page-header" style={{ marginBottom: 8 }}>
          {fromEventId != null && (
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => navigate(`/event/${fromEventId}`)}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
            >
              ← Вернуться к встрече
            </button>
          )}
          {fromLikes && (
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={() => navigate('/likes')}
              style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
            >
              ← Назад к лайкам
            </button>
          )}
        </div>
      )}
      <div className="page-header">
        <h1 className="page-title">{isMyProfile ? 'Мой профиль' : 'Профиль'}</h1>
      </div>
      <div className="card profile-card">
        {profile.photo ? (
          <button
            type="button"
            className="profile-avatar-btn"
            onClick={() => profilePhotos.length > 0 && setPhotoViewerOpen(true)}
            aria-label="Увеличить фото"
          >
            <img src={resolvePhotoUrl(profile.photo)} alt="" className="profile-avatar" />
          </button>
        ) : (
          <div className="profile-avatar-placeholder">{(profile.name || '?').slice(0, 1)}</div>
        )}
        {photoViewerOpen && profilePhotos.length > 0 && (
          <PhotoViewer photos={profilePhotos} onClose={() => setPhotoViewerOpen(false)} />
        )}
        <h2 className="profile-name">{profile.name || 'Пользователь'}</h2>
        <p className="profile-meta">{profile.age ?? '—'} лет · {profile.gender || '—'} · {profile.city || '—'}</p>
        {profile.relationship_status && (
          <p className="profile-meta">{profile.relationship_status}</p>
        )}
        <p className="profile-purpose">Цель: {profile.purpose || '—'}</p>
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
