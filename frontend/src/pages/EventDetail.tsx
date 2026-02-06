import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { api, isApiConfigured } from '../api/client'
import { getDemoEventById } from '../demoData'
import type { Event as EventType } from '../types'

export default function EventDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user, fetchUser, isDemo, useDemoEvents } = useApp()
  const [event, setEvent] = useState<EventType | null>(null)
  const [loading, setLoading] = useState(true)
  const [liking, setLiking] = useState(false)

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  useEffect(() => {
    if (!user) {
      navigate('/', { replace: true })
      return
    }
    if (!id) {
      setLoading(false)
      return
    }
    if (isDemo || useDemoEvents) {
      setEvent(getDemoEventById(id) ?? null)
      setLoading(false)
      return
    }
    if (!isApiConfigured()) {
      setEvent(null)
      setLoading(false)
      return
    }
    setLoading(true)
    api
      .getEvent(Number(id))
      .then(({ event: e }) => setEvent(e))
      .catch(() => setEvent(null))
      .finally(() => setLoading(false))
  }, [id, user, isDemo, useDemoEvents, navigate])

  const handleLike = async () => {
    if (!event || !isApiConfigured() || liking) return
    setLiking(true)
    try {
      const res = await api.likeEvent(event.id)
      if (res.mutual) {
        alert('💞 Взаимная симпатия! Можете обменяться контактами.')
      } else {
        alert('❤️ Лайк отправлен!')
      }
      navigate('/events')
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Ошибка')
    } finally {
      setLiking(false)
    }
  }

  const handleSkip = async () => {
    if (!event || !isApiConfigured()) {
      navigate('/events')
      return
    }
    try {
      await api.skipEvent(event.id)
    } catch (_) {}
    navigate('/events')
  }

  const handleDelete = async () => {
    if (!event || !isApiConfigured()) return
    if (!window.confirm('Удалить встречу «' + event.title + '»? Это действие нельзя отменить.')) return
    try {
      await api.deleteEvent(event.id)
      navigate('/my-events', { replace: true })
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Ошибка удаления')
    }
  }

  if (!user) return null
  if (loading) return <div className="screen-center"><div className="loader" /><p className="text-muted">Загрузка...</p></div>
  if (!event) return <div className="empty-state"><span className="empty-icon">📅</span><p>Встреча не найдена</p><button type="button" className="btn btn-ghost" onClick={() => navigate('/events')}>К встречам</button></div>

  const showDemoActions = (isDemo || useDemoEvents) && !isApiConfigured()
  const isOwnEvent = event.user_id === user.user_id
  const canEditDelete = isOwnEvent && isApiConfigured() && !showDemoActions

  return (
    <>
      <div className="page-header">
        {event.category && <span className="page-badge">{event.category}</span>}
        <h1 className="page-title">{event.title}</h1>
      </div>
      <div
        className="event-detail-author card"
        role="button"
        tabIndex={0}
        onClick={() => navigate(`/profile/${event.user_id}`)}
        onKeyDown={(e) => e.key === 'Enter' && navigate(`/profile/${event.user_id}`)}
      >
        {event.photo ? (
          <img src={event.photo} alt="" className="event-detail-author-avatar" />
        ) : (
          <div className="event-detail-author-avatar-placeholder">
            {(event.name ?? '?').slice(0, 1)}
          </div>
        )}
        <div className="event-detail-author-info">
          <span className="event-detail-author-name">{event.name ?? 'Пользователь'}</span>
          <p className="event-detail-author-meta">{event.age} лет · {event.gender} · {event.city}</p>
          <span className="event-detail-author-link">Перейти в профиль</span>
        </div>
        <span className="event-detail-author-arrow">→</span>
      </div>
      <div className="card event-detail-card">
        <p className="event-card-meta">📅 {event.event_date?.slice(0, 16).replace('T', ' ')}</p>
        <p className="event-card-meta">Для кого: {event.target_gender}</p>
        <p className="event-detail-desc">{event.description}</p>
      </div>
      <div className="event-detail-actions">
        {canEditDelete ? (
          <>
            <button type="button" className="btn btn-primary" style={{ flex: 1 }} onClick={() => navigate(`/event/${event.id}/edit`)}>
              ✏️ Редактировать
            </button>
            <button type="button" className="btn btn-secondary" style={{ flex: 1, borderColor: 'rgba(248, 113, 113, 0.4)', color: 'var(--error)' }} onClick={handleDelete}>
              🗑 Удалить
            </button>
          </>
        ) : showDemoActions ? (
          <>
            <button type="button" className="btn btn-primary" style={{ flex: 1 }} onClick={() => navigate('/events')}>
              ❤️ Лайк (демо)
            </button>
            <button type="button" className="btn btn-secondary" style={{ flex: 1 }} onClick={() => navigate('/events')}>
              Пропустить
            </button>
          </>
        ) : (
          <>
            <button type="button" className="btn btn-primary" style={{ flex: 1 }} onClick={handleLike} disabled={liking}>
              ❤️ Лайк
            </button>
            <button type="button" className="btn btn-secondary" style={{ flex: 1 }} onClick={handleSkip}>
              Пропустить
            </button>
          </>
        )}
      </div>
    </>
  )
}
