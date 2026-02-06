import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { api, isApiConfigured } from '../api/client'
import { CATEGORY_KEYS, TARGET_GENDERS } from '../constants'

export default function CreateEvent() {
  const navigate = useNavigate()
  const { user, fetchUser } = useApp()
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [eventDate, setEventDate] = useState('')
  const [targetGender, setTargetGender] = useState('Все')
  const [category, setCategory] = useState('')
  const [city, setCity] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  useEffect(() => {
    if (user) setCity(user.city || '')
  }, [user])

  useEffect(() => {
    if (!user) navigate('/', { replace: true })
  }, [user, navigate])

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
      await api.createEvent({
        title: title.trim(),
        description: description.trim(),
        event_date: eventDate,
        target_gender: targetGender,
        city,
        category: category || undefined,
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
    <>
      <DemoBanner />
      <div className="page-header">
        <h1 className="page-title">Создать встречу</h1>
        <p className="page-subtitle">Опишите встречу — её увидят люди рядом</p>
      </div>
      <form className="form" onSubmit={handleSubmit}>
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

        <label className="label">Дата и время</label>
        <input
          className="input"
          type="datetime-local"
          value={eventDate}
          onChange={(e) => setEventDate(e.target.value)}
          required
        />

        <label className="label">Для кого</label>
        <select
          className="input"
          value={targetGender}
          onChange={(e) => setTargetGender(e.target.value)}
        >
          {TARGET_GENDERS.map((g) => (
            <option key={g} value={g}>{g}</option>
          ))}
        </select>

        <label className="label">Город</label>
        <input
          className="input"
          value={city}
          onChange={(e) => setCity(e.target.value)}
          placeholder="Город"
          required
        />

        <label className="label">Категория (необязательно)</label>
        <select
          className="input"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        >
          <option value="">—</option>
          {CATEGORY_KEYS.map((k) => (
            <option key={k} value={k}>{k}</option>
          ))}
        </select>

        {error && <p className="text-error">{error}</p>}
        <button type="submit" className="btn btn-primary btn-lg" disabled={loading}>
          {loading ? 'Создание...' : '🎉 Создать встречу'}
        </button>
      </form>
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
