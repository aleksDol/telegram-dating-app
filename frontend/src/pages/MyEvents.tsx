import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { DEMO_USER_ID } from '../context/AppContext'
import { api, isApiConfigured } from '../api/client'
import { getDemoMyEvents } from '../demoData'
import type { Event as EventType } from '../types'

export default function MyEvents() {
  const navigate = useNavigate()
  const { user, fetchUser, isDemo, useDemoEvents, setUseDemoEvents } = useApp()
  const [events, setEvents] = useState<EventType[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [deletingId, setDeletingId] = useState<number | null>(null)

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  useEffect(() => {
    if (!user) {
      navigate('/', { replace: true })
      return
    }
    if (isDemo || useDemoEvents) {
      setEvents(getDemoMyEvents(useDemoEvents ? DEMO_USER_ID : user.user_id))
      setLoading(false)
      setError('')
      return
    }
    if (!isApiConfigured()) {
      setEvents([])
      setLoading(false)
      return
    }
    setLoading(true)
    setError('')
    api
      .getMyEvents()
      .then(({ events: list }) => setEvents(list))
      .catch((e) => setError(e instanceof Error ? e.message : 'Ошибка'))
      .finally(() => setLoading(false))
  }, [user, isDemo, useDemoEvents, navigate])

  const handleDelete = async (ev: EventType) => {
    if (isDemo || useDemoEvents || !isApiConfigured()) {
      setError('В демо-режиме удаление недоступно')
      return
    }
    if (!window.confirm('Удалить событие «' + ev.title + '»? Это действие нельзя отменить.')) return
    setDeletingId(ev.id)
    setError('')
    try {
      await api.deleteEvent(ev.id)
      setEvents((prev) => prev.filter((e) => e.id !== ev.id))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка удаления')
    } finally {
      setDeletingId(null)
    }
  }

  if (!user) return null

  return (
    <>
      <DemoBanner />
      <div className="page-header">
        <h1 className="page-title">Мои события</h1>
        <p className="page-subtitle">Управляйте своими встречами</p>
      </div>
      <button type="button" className="btn btn-primary btn-lg block-btn" onClick={() => navigate('/create')}>
        🎉 Создать событие
      </button>
      {loading && <div className="screen-center"><div className="loader" /><p className="text-muted">Загрузка...</p></div>}
      {error && <div className="card card-error"><p className="text-error">{error}</p></div>}
      {!loading && !error && events.length === 0 && (
        <div className="empty-state">
          <span className="empty-icon">📅</span>
          <p>У вас пока нет событий</p>
          <p className="text-muted" style={{ marginTop: 8 }}>Создайте первое — кнопка выше</p>
          <button type="button" className="btn btn-ghost" style={{ marginTop: 16 }} onClick={() => navigate('/create')}>Создать событие</button>
          <button
            type="button"
            className="btn btn-primary"
            style={{ marginTop: 12 }}
            onClick={() => setUseDemoEvents(true)}
          >
            Показать примеры событий
          </button>
        </div>
      )}
      {!loading && events.length > 0 && (
        <section className="section">
          <h2 className="section-title">Ваши встречи</h2>
          <div className="event-list">
            {events.map((ev) => (
              <div key={ev.id} className="card my-event-card">
                <div
                  className="my-event-card-body"
                  role="button"
                  tabIndex={0}
                  onClick={() => navigate(`/event/${ev.id}`)}
                  onKeyDown={(e) => e.key === 'Enter' && navigate(`/event/${ev.id}`)}
                >
                  <div className="event-card-header">
                    <h3 className="event-card-title">{ev.title}</h3>
                    {ev.category && <span className="event-card-cat">{ev.category}</span>}
                  </div>
                  <p className="event-card-meta">{ev.city} · {ev.event_date?.slice(0, 16).replace('T', ' ')}</p>
                </div>
                <div className="my-event-card-actions">
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={(e) => { e.stopPropagation(); navigate(`/event/${ev.id}/edit`) }}
                  >
                    ✏️ Редактировать
                  </button>
                  {isApiConfigured() && !isDemo && !useDemoEvents && (
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm btn-danger"
                      onClick={(e) => { e.stopPropagation(); handleDelete(ev) }}
                      disabled={deletingId === ev.id}
                    >
                      {deletingId === ev.id ? '…' : '🗑 Удалить'}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
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
      <button type="button" className="demo-banner-btn" onClick={() => navigate('/register')}>Зарегистрироваться</button>
    </div>
  )
}
