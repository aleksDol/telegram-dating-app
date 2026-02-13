import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { api, isApiConfigured, API_BASE } from '../api/client'
import { CITIES, GENDERS, RELATIONSHIP_STATUSES } from '../constants'

const MAX_PHOTOS = 6

/** Каждое фото имеет стабильный id — удаление всегда по id, без путаницы с индексами */
type PhotoItem = { id: string; url: string }

function photoSrc(url: string): string {
  if (!url) return ''
  if (url.startsWith('data:') || url.startsWith('http')) return url
  return API_BASE + url
}

function photosFromUser(user: { user_id: number; photos?: string[]; photo?: string }): PhotoItem[] {
  const list = user.photos?.length ? user.photos : user.photo ? [user.photo] : []
  return list.map((url, i) => ({
    id: `u-${user.user_id}-${i}-${String(url).replace(/^.*\//, '').slice(0, 20)}`,
    url,
  }))
}

export default function EditProfile() {
  const navigate = useNavigate()
  const { user, loading: userLoading, fetchUser, setUser } = useApp()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [name, setName] = useState('')
  const [age, setAge] = useState('')
  const [gender, setGender] = useState('')
  const [city, setCity] = useState('')
  const [relationshipStatus, setRelationshipStatus] = useState('')
  const [purpose, setPurpose] = useState('')
  const [photos, setPhotos] = useState<PhotoItem[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const photosSyncedForUserIdRef = useRef<number | null>(null)

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  useEffect(() => {
    if (!user) return
    setName(user.name || '')
    setAge(String(user.age ?? ''))
    setGender(user.gender || '')
    setCity(user.city || '')
    setRelationshipStatus(user.relationship_status || '')
    setPurpose(user.purpose || 'куда-то сходить')
    if (photosSyncedForUserIdRef.current !== user.user_id) {
      photosSyncedForUserIdRef.current = user.user_id
      setPhotos(photosFromUser(user))
    }
  }, [user])

  useEffect(() => {
    if (!userLoading && !user) navigate('/', { replace: true })
  }, [userLoading, user, navigate])

  const handleAddPhoto = () => {
    if (photos.length >= MAX_PHOTOS) return
    fileInputRef.current?.click()
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file || !file.type.startsWith('image/')) return
    const dataUrl = await new Promise<string>((resolve, reject) => {
      const r = new FileReader()
      r.onload = () => resolve(r.result as string)
      r.onerror = reject
      r.readAsDataURL(file)
    })
    const newItem: PhotoItem = { id: `add-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`, url: dataUrl }
    setPhotos((prev) => [...prev, newItem].slice(0, MAX_PHOTOS))
  }

  const handleRemovePhoto = (id: string) => {
    if (!id) return
    setPhotos((prev) => prev.filter((p) => p.id !== id))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const ageNum = parseInt(age, 10)
    if (!name.trim()) {
      setError('Введите имя')
      return
    }
    if (isNaN(ageNum) || ageNum < 18 || ageNum > 100) {
      setError('Возраст от 18 до 100')
      return
    }
    if (!gender || !city) {
      setError('Заполните пол и город')
      return
    }
    setSaving(true)
    setError('')
    try {
      const photoUrls = photos.map((p) => p.url)
      if (isApiConfigured()) {
        const { user: updated } = await api.updateProfile({
          name: name.trim(),
          age: ageNum,
          gender,
          city,
          relationship_status: relationshipStatus || 'Не в отношениях',
          purpose: purpose.trim() || 'куда-то сходить',
          photos: photoUrls,
        })
        setUser(updated)
        await fetchUser()
      } else {
        setUser({
          ...user!,
          name: name.trim(),
          age: ageNum,
          gender,
          city,
          relationship_status: relationshipStatus || 'Не в отношениях',
          purpose: purpose.trim() || 'куда-то сходить',
          photo: photoUrls[0],
          photos: photoUrls,
        })
      }
      navigate('/profile', { replace: true })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }

  if (userLoading || !user) return null

  return (
    <div className="edit-profile-page">
      <div className="page-header">
        <h1 className="page-title">Редактировать профиль</h1>
        <p className="page-subtitle">Измените данные и нажмите «Сохранить»</p>
      </div>
      <form className="form" onSubmit={handleSubmit}>
        <label className="label">Имя</label>
        <input
          className="input"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Ваше имя"
          required
        />

        <label className="label">Возраст</label>
        <input
          className="input"
          type="number"
          min={18}
          max={100}
          value={age}
          onChange={(e) => setAge(e.target.value)}
          placeholder="18–100"
          required
        />

        <label className="label">Пол</label>
        <select
          className="input"
          value={gender}
          onChange={(e) => setGender(e.target.value)}
          required
        >
          <option value="">—</option>
          {GENDERS.map((g) => (
            <option key={g} value={g}>{g}</option>
          ))}
        </select>

        <label className="label">Город</label>
        <select
          className="input"
          value={city}
          onChange={(e) => setCity(e.target.value)}
          required
        >
          <option value="">—</option>
          {CITIES.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>

        <label className="label">Статус отношений</label>
        <select
          className="input"
          value={relationshipStatus}
          onChange={(e) => setRelationshipStatus(e.target.value)}
        >
          {RELATIONSHIP_STATUSES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        <label className="label">Цель знакомств</label>
        <input
          className="input"
          value={purpose}
          onChange={(e) => setPurpose(e.target.value)}
          placeholder="Например: куда-то сходить"
        />

        <label className="label">Мои фото</label>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          className="profile-photo-input-hidden"
          aria-hidden
          onChange={handleFileChange}
        />
        <div className="profile-photos-grid profile-photos-grid-six edit-profile-photos">
          {[0, 1, 2, 3, 4, 5].map((i) => {
            const item = photos[i]
            return (
              <div
                key={item ? item.id : `empty-${i}`}
                className={`profile-photo-slot ${item ? '' : 'profile-photo-slot-empty-wrap'}`}
              >
                {item ? (
                  <div className="profile-photo-slot-edit-wrap">
                    <img src={photoSrc(item.url)} alt="" className="profile-photo-slot-img" />
                    <button
                      type="button"
                      className="profile-photo-slot-remove"
                      onClick={(e) => {
                        e.preventDefault()
                        e.stopPropagation()
                        handleRemovePhoto(item.id)
                      }}
                      title="Удалить фото"
                      aria-label={`Удалить фото ${i + 1}`}
                    >
                      ×
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    className="profile-photo-slot-empty profile-photo-slot-add"
                    onClick={handleAddPhoto}
                    disabled={photos.length >= MAX_PHOTOS}
                    title="Добавить фото"
                    aria-label="Добавить фото"
                  >
                    <span className="profile-photo-slot-emoji">＋</span>
                  </button>
                )}
              </div>
            )
          })}
        </div>
        {photos.length < MAX_PHOTOS && (
          <p className="text-muted profile-photo-hint">
            Нажмите ＋, чтобы добавить фото (максимум {MAX_PHOTOS})
          </p>
        )}

        {error && <p className="text-error">{error}</p>}
        <div className="form-actions">
          <button type="button" className="btn btn-secondary" onClick={() => navigate('/profile')}>
            Отмена
          </button>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Сохранение...' : 'Сохранить'}
          </button>
        </div>
      </form>
    </div>
  )
}
