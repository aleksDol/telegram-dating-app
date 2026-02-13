import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { api, isApiConfigured } from '../api/client'

const MAX_PHOTOS = 6
const API_BASE = import.meta.env.VITE_API_URL || ''

function photoSrc(url: string): string {
  if (!url) return ''
  if (url.startsWith('data:') || url.startsWith('http')) return url
  return API_BASE + url
}

export default function Profile() {
  const navigate = useNavigate()
  const { user, loading, fetchUser, setUser } = useApp()
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const photosRef = useRef<string[]>([])

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  useEffect(() => {
    if (!loading && !user) navigate('/', { replace: true })
  }, [loading, user, navigate])

  const photos: string[] = user?.photos?.length
    ? user.photos
    : user?.photo
      ? [user.photo]
      : []
  photosRef.current = photos

  const handleAddPhoto = () => {
    if (photos.length >= MAX_PHOTOS || uploading) return
    fileInputRef.current?.click()
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file || !user || !file.type.startsWith('image/')) return
    if (uploading) return
    setUploading(true)
    let dataUrl: string
    try {
      dataUrl = await new Promise<string>((resolve, reject) => {
        const r = new FileReader()
        r.onload = () => resolve(r.result as string)
        r.onerror = reject
        r.readAsDataURL(file)
      })
    } catch {
      setUploading(false)
      return
    }
    const currentPhotos = photosRef.current
    const newPhotos = [...currentPhotos, dataUrl].slice(0, MAX_PHOTOS)
    photosRef.current = newPhotos
    try {
      if (isApiConfigured()) {
        const { user: updated } = await api.updateProfile({ photos: newPhotos })
        setUser(updated)
        photosRef.current = updated.photos ?? (updated.photo ? [updated.photo] : [])
        await fetchUser()
      } else {
        setUser({ ...user, photo: dataUrl, photos: newPhotos })
      }
    } catch {
      photosRef.current = currentPhotos
    } finally {
      setUploading(false)
    }
  }

  if (loading) return <div className="screen-center"><div className="loader" /><p className="text-muted">Загрузка...</p></div>
  if (!user) return null

  const meetingsCount = 0

  return (
    <div className="profile-page">
      <DemoBanner />
      {/* Верхняя панель: назад + меню */}
      <header className="profile-top-bar">
        <button type="button" className="profile-top-bar-btn" onClick={() => navigate(-1)} aria-label="Назад">
          <span className="profile-top-bar-icon profile-top-bar-icon-back">←</span>
        </button>
        <button type="button" className="profile-top-bar-btn" aria-label="Меню">
          <span className="profile-top-bar-icon profile-top-bar-icon-menu">☰</span>
        </button>
      </header>

      {/* Карточка профиля: аватар, имя, описание, кнопка Редактировать */}
      <section className="profile-card animate-in stagger-1">
        <div className="profile-card-avatar" aria-hidden>
          {user.photo ? (
            <img src={photoSrc(user.photo)} alt="" className="profile-card-avatar-img" />
          ) : (
            <div className="profile-card-avatar-placeholder">{user.name.slice(0, 1)}</div>
          )}
        </div>
        <h1 className="profile-card-name">{user.name}</h1>
        <p className="profile-card-bio">
          {user.purpose && `Цель: ${user.purpose}. `}
          {user.age} лет · {user.gender}{user.city ? ` · ${user.city}` : ''}
          {user.relationship_status ? ` · ${user.relationship_status}` : ''}
        </p>
        <Link to="/profile/edit" className="profile-card-edit-btn">
          Редактировать
        </Link>
      </section>

      {/* Два столбца: статистика слева, Мои фото справа */}
      <div className="profile-bottom-row animate-in stagger-2">
        {/* Статистика */}
        <aside className="profile-stats-card">
          <Link to="/my-events" className="profile-stats-row">
            <span className="profile-stats-num">{meetingsCount}</span>
            <span className="profile-stats-label">Мои встречи</span>
          </Link>
          <div className="profile-stats-divider" />
          <div className="profile-stats-row">
            <span className="profile-stats-num">{user.points}</span>
            <span className="profile-stats-label">Рейтинг</span>
          </div>
          <div className="profile-stats-divider" />
          <Link to="/referral" className="profile-stats-row">
            <span className="profile-stats-num">{user.referrals_count ?? 0}</span>
            <span className="profile-stats-label">Рефералы</span>
          </Link>
        </aside>

        {/* Мои фото: 6 слотов, пустые — рамка со знаком + */}
        <section className="profile-photo-block animate-in stagger-3">
          <h2 className="profile-block-title">МОИ ФОТО</h2>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            className="profile-photo-input-hidden"
            aria-hidden
            onChange={handleFileChange}
          />
          <div className="profile-photos-grid profile-photos-grid-six">
            {[0, 1, 2, 3, 4, 5].map((i) => (
              <div
                key={i}
                className={`profile-photo-slot ${photos[i] ? '' : 'profile-photo-slot-empty-wrap'}`}
              >
                {photos[i] ? (
                  <img src={photoSrc(photos[i])} alt="" className="profile-photo-slot-img" />
                ) : (
                  <button
                    type="button"
                    className="profile-photo-slot-empty profile-photo-slot-add"
                    onClick={handleAddPhoto}
                    disabled={uploading || photos.length >= MAX_PHOTOS}
                    title="Добавить фото"
                    aria-label="Добавить фото"
                  >
                    <span className="profile-photo-slot-emoji">+</span>
                  </button>
                )}
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Реферальная программа и Достижения */}
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
      <button type="button" className="demo-banner-btn" onClick={() => navigate('/register')}>Зарегистрироваться</button>
    </div>
  )
}
