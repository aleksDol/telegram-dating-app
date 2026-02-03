import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { api, isApiConfigured } from '../api/client'
import { FILTER_LABELS } from '../constants'
import { getDemoEventsForFeed } from '../demoData'
import Logo from '../components/Logo'
import type { Event as EventType } from '../types'

const FILTERS = ['new', 'popular', 'nearby', 'today', 'tomorrow', 'for_me', 'random', 'interest'] as const

export default function Events() {
  const { filter = 'new' } = useParams<{ filter?: string }>()
  const navigate = useNavigate()
  const { user, loading: userLoading, fetchUser, isDemo, useDemoEvents, setUseDemoEvents } = useApp()
  const [events, setEvents] = useState<EventType[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  useEffect(() => {
    if (!user && !userLoading) {
      navigate('/', { replace: true })
      return
    }
    if (!user) return

    if (isDemo || useDemoEvents) {
      setEvents(getDemoEventsForFeed(user.user_id))
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
      .getEvents(filter, 20)
      .then(({ events: list }) => setEvents(list))
      .catch((e) => setError(e instanceof Error ? e.message : 'Ошибка'))
      .finally(() => setLoading(false))
  }, [user, userLoading, filter, isDemo, useDemoEvents, navigate])

  if (!user) return null

  return (
    <>
      <DemoBanner />
      <div className="page-header page-header-with-logo">
        <Logo size="sm" showText link />
        <h1 className="page-title">Найти события</h1>
        <p className="page-subtitle">Выберите фильтр и смотрите карточки</p>
      </div>
      <div className="filter-chips">
        {FILTERS.map((f) => (
          <button
            key={f}
            type="button"
            className={`chip ${filter === f ? 'chip-active' : ''}`}
            onClick={() => navigate(`/events/${f}`)}
          >
            {FILTER_LABELS[f] ?? f}
          </button>
        ))}
      </div>
      {loading && <div className="screen-center"><div className="loader" /><p className="text-muted">Загрузка...</p></div>}
      {error && <p className="text-error">{error}</p>}
      {!loading && !error && events.length === 0 && (
        <div className="empty-state">
          <span className="empty-icon">📅</span>
          <p>Нет событий по выбранному фильтру</p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setUseDemoEvents(true)}
          >
            Показать примеры событий
          </button>
        </div>
      )}
      {!loading && events.length > 0 && (
        <div className="event-list">
          {events.map((ev) => (
            <div key={ev.id} className="card event-card">
              <div
                className="event-card-image-wrap"
                role="button"
                tabIndex={0}
                onClick={() => navigate(`/event/${ev.id}`)}
                onKeyDown={(e) => e.key === 'Enter' && navigate(`/event/${ev.id}`)}
              >
                {ev.photo ? (
                  <img src={ev.photo} alt="" />
                ) : (
                  <div className="event-card-image-placeholder">
                    {ev.category?.slice(0, 2) || '🎉'}
                  </div>
                )}
                {ev.category && (
                  <span className="event-card-cat-badge">{ev.category}</span>
                )}
              </div>
              <div className="event-card-footer">
                <div
                  className="event-card-author"
                  role="button"
                  tabIndex={0}
                  onClick={(e) => {
                    e.stopPropagation()
                    navigate(`/profile/${ev.user_id}`)
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.stopPropagation()
                      navigate(`/profile/${ev.user_id}`)
                    }
                  }}
                >
                  {ev.photo ? (
                    <img src={ev.photo} alt="" className="event-author-avatar" />
                  ) : (
                    <div className="event-author-avatar-placeholder">
                      {(ev.name ?? '?').slice(0, 1)}
                    </div>
                  )}
                  <div className="event-author-info">
                    <span className="event-author-name">{ev.name ?? 'Пользователь'}</span>
                    <span className="event-author-meta">{ev.age} · {ev.city}</span>
                  </div>
                  <span className="event-author-arrow">→</span>
                </div>
                <div
                  role="button"
                  tabIndex={0}
                  className="event-card-body"
                  onClick={() => navigate(`/event/${ev.id}`)}
                  onKeyDown={(e) => e.key === 'Enter' && navigate(`/event/${ev.id}`)}
                >
                  <div className="event-card-header">
                    <h3 className="event-card-title">{ev.title}</h3>
                    {ev.category && <span className="event-card-cat">{ev.category}</span>}
                  </div>
                  <p className="event-card-meta">{ev.city} · {ev.event_date?.slice(0, 16)}</p>
                  <p className="event-card-desc">{ev.description?.slice(0, 120)}{(ev.description?.length ?? 0) > 120 ? '…' : ''}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
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
