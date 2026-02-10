import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { api, isApiConfigured } from '../api/client'
import { CATEGORY_KEYS, TARGET_GENDERS } from '../constants'
import { compressImageForUpload } from '../utils/imageResize'

export default function CreateEvent() {
  const navigate = useNavigate()
  const { user, fetchUser } = useApp()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [eventDate, setEventDate] = useState('')
  const [targetGender, setTargetGender] = useState('Все')
  const [category, setCategory] = useState('')
  const [city, setCity] = useState('')
  const [photoFile, setPhotoFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [targetGenderOpen, setTargetGenderOpen] = useState(false)
  const [categoryOpen, setCategoryOpen] = useState(false)
  const targetGenderRef = useRef<HTMLDivElement>(null)
  const categoryRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  useEffect(() => {
    if (user) setCity(user.city || '')
  }, [user])

  useEffect(() => {
    if (!user) navigate('/', { replace: true })
  }, [user, navigate])

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (targetGenderRef.current && !targetGenderRef.current.contains(e.target as Node)) setTargetGenderOpen(false)
      if (categoryRef.current && !categoryRef.current.contains(e.target as Node)) setCategoryOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim() || !description.trim() || !eventDate || !city) {
      setError('Заполните название, описание, дату и город')
      return
    }
    if (!isApiConfigured()) {
      setError('API не подключен. Настройте VITE_API_URL.')
      return
    }
    setLoading(true)
    setError('')
    try {
      let photoDataUrl: string | undefined
      if (photoFile) {
        photoDataUrl = await compressImageForUpload(photoFile)
      }
      await api.createEvent({
        title: title.trim(),
        description: description.trim(),
        event_date: eventDate,
        target_gender: targetGender,
        city,
        category: category || undefined,
        photo: photoDataUrl,
      })
      navigate('/my-events')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка создания')
    } finally {
      setLoading(false)
    }
  }

  if (!user) return null

  return (
    <div className="create-event-page">
      <DemoBanner />
      <div className="create-event-hero">
        <h1 className="create-event-hero-title">Создать встречу</h1>
        <p className="create-event-hero-subtitle">Опишите встречу — её увидят люди рядом</p>
        <svg className="create-event-hero-wave" viewBox="0 0 400 32" preserveAspectRatio="none" aria-hidden>
          <path d="M0 32V0h400v32c-66.5-8-133-8-200 0S66.5 32 0 32z" />
        </svg>
      </div>
      <form className="form form-create" onSubmit={handleSubmit}>
        <label className="label">Название</label>
        <input
          className="input"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Например: Кофе в центре"
          required
        />

        <label className="label">Описание</label>
        <textarea
          className="input"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Опишите встречу..."
          rows={3}
          required
        />

        <label className="label">Фото (необязательно)</label>
        <label className="input-photo-placeholder">
          <input
            type="file"
            accept="image/*"
            className="input-photo-input"
            onChange={(e) => setPhotoFile(e.target.files?.[0] ?? null)}
          />
          <span className="input-photo-text">
            {photoFile ? photoFile.name : 'Например фото заведения'}
          </span>
        </label>

        <label className="label">Дата</label>
        <div className="input-date-wrap">
          <input
            className="input input-date"
            type="date"
            value={eventDate}
            onChange={(e) => setEventDate(e.target.value)}
            min={new Date().toISOString().slice(0, 10)}
            required
          />
        </div>

        <label className="label">Для кого</label>
        <div className="form-select-wrap" ref={targetGenderRef}>
          <button
            type="button"
            className="form-select-trigger"
            onClick={() => { setTargetGenderOpen((o) => !o); setCategoryOpen(false); }}
            aria-expanded={targetGenderOpen}
            aria-haspopup="listbox"
          >
            <span>{targetGender}</span>
            <span className="form-select-arrow">{targetGenderOpen ? '▲' : '▼'}</span>
          </button>
          {targetGenderOpen && (
            <div className="form-select-panel" role="listbox">
              {TARGET_GENDERS.map((g) => (
                <button
                  key={g}
                  type="button"
                  role="option"
                  aria-selected={targetGender === g}
                  className={`form-select-item ${targetGender === g ? 'form-select-item-active' : ''}`}
                  onClick={() => { setTargetGender(g); setTargetGenderOpen(false); }}
                >
                  {g}
                </button>
              ))}
            </div>
          )}
        </div>

        <label className="label">Город</label>
        <input
          className="input"
          value={city}
          onChange={(e) => setCity(e.target.value)}
          placeholder="Город"
          required
        />

        <label className="label">Категория (необязательно)</label>
        <div className="form-select-wrap" ref={categoryRef}>
          <button
            type="button"
            className="form-select-trigger"
            onClick={() => { setCategoryOpen((o) => !o); setTargetGenderOpen(false); }}
            aria-expanded={categoryOpen}
            aria-haspopup="listbox"
          >
            <span>{category || '—'}</span>
            <span className="form-select-arrow">{categoryOpen ? '▲' : '▼'}</span>
          </button>
          {categoryOpen && (
            <div className="form-select-panel" role="listbox">
              <button
                type="button"
                role="option"
                aria-selected={!category}
                className={`form-select-item ${!category ? 'form-select-item-active' : ''}`}
                onClick={() => { setCategory(''); setCategoryOpen(false); }}
              >
                —
              </button>
              {CATEGORY_KEYS.map((k) => (
                <button
                  key={k}
                  type="button"
                  role="option"
                  aria-selected={category === k}
                  className={`form-select-item ${category === k ? 'form-select-item-active' : ''}`}
                  onClick={() => { setCategory(k); setCategoryOpen(false); }}
                >
                  {k}
                </button>
              ))}
            </div>
          )}
        </div>

        {error && <p className="text-error">{error}</p>}
        <button type="submit" className="btn btn-primary btn-lg btn-create-event" disabled={loading}>
          {loading ? 'Создание...' : '🎉 Создать встречу'}
        </button>
      </form>
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
