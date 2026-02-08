import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { api, isApiConfigured, API_BASE } from '../api/client'
import { getDemoEventById } from '../demoData'
import { CATEGORY_KEYS, TARGET_GENDERS } from '../constants'
import type { Event as EventType } from '../types'
import { compressImageForUpload } from '../utils/imageResize'

function eventPhotoSrc(url: string | undefined): string {
  if (!url) return ''
  if (url.startsWith('data:') || url.startsWith('http')) return url
  return API_BASE + url
}

export default function EditEvent() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user, fetchUser, isDemo, useDemoEvents } = useApp()
  const [event, setEvent] = useState<EventType | null>(null)
  const [loading, setLoading] = useState(true)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [eventDate, setEventDate] = useState('')
  const [targetGender, setTargetGender] = useState('Все')
  const [category, setCategory] = useState('')
  const [city, setCity] = useState('')
  const [photoFile, setPhotoFile] = useState<File | null>(null)
  const [photoDataUrl, setPhotoDataUrl] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  useEffect(() => {
    if (!user) {
      navigate('/', { replace: true })
      return
    }
    const eventId = id ? parseInt(id, 10) : NaN
    if (Number.isNaN(eventId)) {
      setLoading(false)
      setError('Неверный адрес')
      return
    }
    if (isDemo || useDemoEvents) {
      const ev = getDemoEventById(id ?? '')
      setEvent(ev ?? null)
      if (ev) {
        setTitle(ev.title || '')
        setDescription(ev.description || '')
        setCity(ev.city || '')
        setTargetGender(ev.target_gender || 'Все')
        setCategory(ev.category || '')
        if (ev.event_date) {
          const d = ev.event_date.replace(' ', 'T').slice(0, 16)
          setEventDate(d)
        }
      }
      setLoading(false)
      return
    }
    if (!isApiConfigured()) {
      setLoading(false)
      setError('API не подключен')
      return
    }
    setLoading(true)
    setError('')
    api
      .getEvent(eventId)
      .then(({ event: ev }) => {
        setEvent(ev)
        setTitle(ev.title || '')
        setDescription(ev.description || '')
        setCity(ev.city || '')
        setTargetGender(ev.target_gender || 'Все')
        setCategory(ev.category || '')
        if (ev.event_date) {
          const d = ev.event_date.replace(' ', 'T').slice(0, 16)
          setEventDate(d)
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Ошибка загрузки'))
      .finally(() => setLoading(false))
  }, [id, user, isDemo, useDemoEvents, navigate])

  useEffect(() => {
    if (event && user && event.user_id !== user.user_id) {
      navigate('/my-events', { replace: true })
    }
  }, [event, user, navigate])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!event) return
    if (!title.trim() || !description.trim() || !eventDate || !city) {
      setError('Заполните название, описание, дату и город')
      return
    }
    if (isDemo || useDemoEvents || !isApiConfigured()) {
      setError('В демо-режиме изменения не сохраняются')
      return
    }
    setSaving(true)
    setError('')
    try {
      let photoToSend: string | undefined
      if (photoFile) {
        photoToSend = await compressImageForUpload(photoFile)
      }
      await api.updateEvent(event.id, {
        title: title.trim(),
        description: description.trim(),
        event_date: eventDate,
        target_gender: targetGender,
        city,
        category: category || undefined,
        photo: photoToSend,
      })
      navigate(`/event/${event.id}`, { replace: true })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!event) return
    if (!window.confirm('Удалить встречу «' + event.title + '»? Это действие нельзя отменить.')) return
    if (isDemo || useDemoEvents || !isApiConfigured()) {
      setError('В демо-режиме удаление недоступно')
      return
    }
    setDeleting(true)
    setError('')
    try {
      await api.deleteEvent(event.id)
      navigate('/my-events', { replace: true })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка удаления')
    } finally {
      setDeleting(false)
    }
  }

  if (!user) return null
  if (loading) return <div className="screen-center"><div className="loader" /><p className="text-muted">Загрузка...</p></div>
  if (error && !event) return <div className="empty-state"><p className="text-error">{error}</p><button type="button" className="btn btn-ghost" onClick={() => navigate('/my-events')}>К моим встречам</button></div>
  if (!event) return null
  if (event.user_id !== user.user_id) return null

  const isDemoMode = isDemo || useDemoEvents || !isApiConfigured()

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Редактировать встречу</h1>
        <p className="page-subtitle">{event.title}</p>
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

        <label className="label">Фото события</label>
        <label className="input-photo-placeholder create-event-photo">
          <input
            type="file"
            accept="image/*"
            className="input-photo-input"
            onChange={(e) => {
              const file = e.target.files?.[0]
              setPhotoFile(file ?? null)
              if (file) {
                const r = new FileReader()
                r.onload = () => setPhotoDataUrl(r.result as string)
                r.readAsDataURL(file)
              } else {
                setPhotoDataUrl(null)
              }
            }}
          />
          {photoDataUrl ? (
            <span className="input-photo-preview-wrap">
              <img src={photoDataUrl} alt="" className="input-photo-preview" />
              <span className="input-photo-text">Изменить фото</span>
            </span>
          ) : event.photo ? (
            <span className="input-photo-preview-wrap">
              <img src={eventPhotoSrc(event.photo)} alt="" className="input-photo-preview" />
              <span className="input-photo-text">Изменить фото</span>
            </span>
          ) : (
            <span className="input-photo-text">
              {photoFile ? photoFile.name : 'Выбрать фото встречи'}
            </span>
          )}
        </label>

        {error && <p className="text-error">{error}</p>}
        <div className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={() => navigate(`/event/${event.id}`)}>
            Отмена
          </button>
          <button type="submit" className="btn btn-primary" disabled={saving || isDemoMode}>
            {saving ? 'Сохранение...' : 'Сохранить'}
          </button>
        </div>
        {isDemoMode && <p className="text-muted" style={{ marginTop: 8 }}>В демо-режиме редактирование и удаление недоступны.</p>}
        {!isDemoMode && (
          <button
            type="button"
            className="btn btn-secondary block-btn"
            style={{ marginTop: 16, borderColor: 'rgba(248, 113, 113, 0.4)', color: 'var(--error)' }}
            onClick={handleDelete}
            disabled={deleting}
          >
            {deleting ? 'Удаление...' : '🗑 Удалить встречу'}
          </button>
        )}
      </form>
    </>
  )
}
