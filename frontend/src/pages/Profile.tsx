import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { api, isApiConfigured } from '../api/client'

const MAX_PHOTOS = 3
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

  return (
    <div className="profile-page">
      <DemoBanner />
      <div className="page-header">
        <h1 className="page-title animate-in">Мой профиль</h1>
      </div>

      {/* Обо мне */}
      <section className="profile-about card animate-in stagger-1">
        <h2 className="profile-about-title">Обо мне</h2>
        <div className="profile-about-avatar" aria-hidden>
          {user.photo ? (
            <img src={photoSrc(user.photo)} alt="" className="profile-about-avatar-img" />
          ) : (
            <div className="profile-about-avatar-placeholder">{user.name.slice(0, 1)}</div>
          )}
        </div>
        <h3 className="profile-name">{user.name}</h3>
        <p className="profile-meta">{user.age} лет · {user.gender}{user.city ? ` · ${user.city}` : ''}</p>
        {user.relationship_status && <p className="profile-meta">{user.relationship_status}</p>}
        <p className="profile-purpose">Цель: {user.purpose}</p>
        <div className="profile-points">🏆 {user.points} очков</div>
      </section>

      <div className="profile-main-actions animate-in stagger-2">
        <Link to="/my-events" className="btn btn-secondary btn-lg">
          📅 Мои встречи
        </Link>
        <Link to="/profile/edit" className="btn btn-ghost btn-lg">
          ✏️ Изменить
        </Link>
      </div>

      {/* Блок с фото */}
      <section className="profile-photo-block card animate-in stagger-3">
        <h2 className="profile-block-title">Мои фото</h2>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          className="profile-photo-input-hidden"
          aria-hidden
          onChange={handleFileChange}
        />
        <div className="profile-photos-grid">
          {[0, 1, 2].map((i) => (
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
                  <span className="profile-photo-slot-emoji">＋</span>
                </button>
              )}
            </div>
          ))}
        </div>
        {photos.length < MAX_PHOTOS && (
          <p className="text-muted profile-photo-hint">
            Нажмите ＋, чтобы добавить фото (максимум {MAX_PHOTOS})
          </p>
        )}
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
