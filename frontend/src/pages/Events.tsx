import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { api, isApiConfigured } from '../api/client'
import { FILTER_LABELS } from '../constants'
import { getDemoEventsForFeed } from '../demoData'
import Logo from '../components/Logo'
import type { Event as EventType } from '../types'

const FILTERS = ['new', 'popular', 'nearby', 'today', 'tomorrow', 'for_me', 'random', 'interest'] as const
const SWIPE_THRESHOLD = 80

export default function Events() {
  const { filter = 'new' } = useParams<{ filter?: string }>()
  const navigate = useNavigate()
  const { user, loading: userLoading, fetchUser, isDemo, useDemoEvents, setUseDemoEvents } = useApp()
  const [events, setEvents] = useState<EventType[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [currentIndex, setCurrentIndex] = useState(0)
  const [swipeOffset, setSwipeOffset] = useState(0)
  const [actionBusy, setActionBusy] = useState(false)
  const [touchStartX, setTouchStartX] = useState<number | null>(null)

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
      setCurrentIndex(0)
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
      .then(({ events: list }) => {
        setEvents(list)
        setCurrentIndex(0)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Ошибка'))
      .finally(() => setLoading(false))
  }, [user, userLoading, filter, isDemo, useDemoEvents, navigate])

  const goNext = useCallback(() => {
    setCurrentIndex((i) => Math.min(i + 1, events.length))
    setSwipeOffset(0)
  }, [events.length])

  const performLike = useCallback(async () => {
    const ev = events[currentIndex]
    if (!ev || actionBusy) return
    setActionBusy(true)
    if (isApiConfigured() && !isDemo && !useDemoEvents) {
      try {
        const res = await api.likeEvent(ev.id)
        if (res.mutual) {
          alert('💞 Взаимная симпатия! Можете обменяться контактами.')
        } else {
          alert('❤️ Лайк отправлен!')
        }
      } catch (e) {
        alert(e instanceof Error ? e.message : 'Ошибка')
        setActionBusy(false)
        return
      }
    }
    goNext()
    setActionBusy(false)
  }, [events, currentIndex, actionBusy, isDemo, useDemoEvents, goNext])

  const performSkip = useCallback(async () => {
    const ev = events[currentIndex]
    if (!ev || actionBusy) return
    setActionBusy(true)
    if (isApiConfigured() && !isDemo && !useDemoEvents) {
      try {
        await api.skipEvent(ev.id)
      } catch (_) {}
    }
    goNext()
    setActionBusy(false)
  }, [events, currentIndex, actionBusy, isDemo, useDemoEvents, goNext])

  const handleSwipeEnd = useCallback(() => {
    if (swipeOffset > SWIPE_THRESHOLD) {
      performLike()
      return
    }
    if (swipeOffset < -SWIPE_THRESHOLD) {
      performSkip()
      return
    }
    setSwipeOffset(0)
    setTouchStartX(null)
  }, [swipeOffset, performLike, performSkip])

  const handleTouchStart = (e: React.TouchEvent) => {
    setTouchStartX(e.touches[0].clientX)
  }
  const handleTouchMove = (e: React.TouchEvent) => {
    if (touchStartX === null) return
    const dx = e.touches[0].clientX - touchStartX
    setSwipeOffset(Math.max(-200, Math.min(200, dx)))
  }
  const handleTouchEnd = () => {
    handleSwipeEnd()
    setTouchStartX(null)
  }

  const handleMouseDown = (e: React.MouseEvent) => {
    setTouchStartX(e.clientX)
  }
  const handleMouseMove = (e: React.MouseEvent) => {
    if (touchStartX === null) return
    const dx = e.clientX - touchStartX
    setSwipeOffset(Math.max(-200, Math.min(200, dx)))
  }
  const handleMouseUp = () => {
    handleSwipeEnd()
    setTouchStartX(null)
  }
  const handleMouseLeave = () => {
    if (touchStartX !== null) setSwipeOffset(0)
    setTouchStartX(null)
  }

  if (!user) return null

  const currentEvent = events[currentIndex]
  const hasCards = events.length > 0 && currentIndex < events.length
  const showEmpty = !loading && !error && (events.length === 0 || currentIndex >= events.length)

  return (
    <>
      <DemoBanner />
      <div className="page-header page-header-with-logo">
        <Logo size="sm" showText link />
        <h1 className="page-title animate-in">Найти встречу</h1>
        <p className="page-subtitle animate-in stagger-1">Свайп влево — пропустить, вправо — лайк</p>
      </div>
      <div className="filter-chips animate-in stagger-2">
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
          <p>Нет встреч по выбранному фильтру</p>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => setUseDemoEvents(true)}
          >
            Показать примеры встреч
          </button>
        </div>
      )}
      {showEmpty && events.length > 0 && currentIndex >= events.length && (
        <div className="empty-state">
          <span className="empty-icon">✨</span>
          <p>Встречи закончились</p>
          <p className="text-muted" style={{ fontSize: '0.9rem', marginTop: 8 }}>Смените фильтр или зайдите позже</p>
          <button
            type="button"
            className="btn btn-ghost"
            style={{ marginTop: 16 }}
            onClick={() => setCurrentIndex(0)}
          >
            Смотреть заново
          </button>
        </div>
      )}
      {!loading && hasCards && currentEvent && (
        <div className="events-tinder">
          <div
            className="events-tinder-card-wrap"
            onTouchStart={handleTouchStart}
            onTouchMove={handleTouchMove}
            onTouchEnd={handleTouchEnd}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseLeave}
            style={{
              transform: `translateX(${swipeOffset}px) rotate(${swipeOffset * 0.06}deg)`,
              transition: touchStartX === null ? 'transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)' : 'none',
            }}
          >
            {swipeOffset > 40 && (
              <span className="events-tinder-badge events-tinder-badge-like">❤️ Лайк</span>
            )}
            {swipeOffset < -40 && (
              <span className="events-tinder-badge events-tinder-badge-skip">Пропустить</span>
            )}
            <div className="card event-card">
              <div
                className="event-card-image-wrap"
                role="button"
                tabIndex={0}
                onClick={() => navigate(`/event/${currentEvent.id}`)}
                onKeyDown={(e) => e.key === 'Enter' && navigate(`/event/${currentEvent.id}`)}
              >
                {currentEvent.photo ? (
                  <img src={currentEvent.photo} alt="" />
                ) : (
                  <div className="event-card-image-placeholder">
                    {currentEvent.category?.slice(0, 2) || '🎉'}
                  </div>
                )}
                {currentEvent.category && (
                  <span className="event-card-cat-badge">{currentEvent.category}</span>
                )}
              </div>
              <div className="event-card-footer">
                <div
                  className="event-card-author"
                  role="button"
                  tabIndex={0}
                  onClick={(e) => {
                    e.stopPropagation()
                    navigate(`/profile/${currentEvent.user_id}`, { state: { fromEventId: currentEvent.id } })
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.stopPropagation()
                      navigate(`/profile/${currentEvent.user_id}`, { state: { fromEventId: currentEvent.id } })
                    }
                  }}
                >
                  <div className="event-author-avatar-placeholder">
                    {(currentEvent.name ?? '?').slice(0, 1)}
                  </div>
                  <div className="event-author-info">
                    <span className="event-author-name">{currentEvent.name ?? 'Пользователь'}</span>
                    <span className="event-author-meta">{currentEvent.age} · {currentEvent.city}</span>
                    <span className="event-card-author-hint">Нажать — открыть профиль</span>
                  </div>
                  <span className="event-author-arrow">→</span>
                </div>
                <div
                  role="button"
                  tabIndex={0}
                  className="event-card-body"
                  onClick={() => navigate(`/event/${currentEvent.id}`)}
                  onKeyDown={(e) => e.key === 'Enter' && navigate(`/event/${currentEvent.id}`)}
                >
                  <div className="event-card-header">
                    <h3 className="event-card-title">{currentEvent.title}</h3>
                    {currentEvent.category && <span className="event-card-cat">{currentEvent.category}</span>}
                  </div>
                  <p className="event-card-meta">{currentEvent.city} · {currentEvent.event_date?.slice(0, 16)}</p>
                  <p className="event-card-desc">{currentEvent.description?.slice(0, 120)}{(currentEvent.description?.length ?? 0) > 120 ? '…' : ''}</p>
                </div>
              </div>
            </div>
          </div>
          <div className="events-tinder-actions">
            <button
              type="button"
              className="btn events-tinder-btn events-tinder-btn-skip"
              onClick={performSkip}
              disabled={actionBusy}
              aria-label="Пропустить"
            >
              ✕
            </button>
            <button
              type="button"
              className="btn events-tinder-btn events-tinder-btn-like"
              onClick={performLike}
              disabled={actionBusy}
              aria-label="Лайк"
            >
              ❤️
            </button>
          </div>
          <p className="events-tinder-hint">
            {currentIndex + 1} из {events.length}
          </p>
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
