import { useEffect, useState, useCallback, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { api, isApiConfigured, API_BASE } from '../api/client'
import { FILTER_LABELS } from '../constants'
import { getDemoEventsForFeed } from '../demoData'
import PhotoViewer from '../components/PhotoViewer'
import type { Event as EventType } from '../types'

const FILTERS = ['new', 'nearby', 'today', 'tomorrow', 'random', 'interest'] as const

function eventPhotoSrc(url: string | undefined): string {
  if (!url) return ''
  if (url.startsWith('data:') || url.startsWith('http')) return url
  return API_BASE + url
}
const SWIPE_THRESHOLD = 80
const CARD_EXIT_DURATION_MS = 580

function FilterSliderIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <line x1="4" y1="6" x2="20" y2="6" />
      <line x1="4" y1="12" x2="14" y2="12" />
      <line x1="4" y1="18" x2="10" y2="18" />
      <circle cx="17" cy="6" r="2" fill="currentColor" />
      <circle cx="17" cy="12" r="2" fill="currentColor" />
      <circle cx="17" cy="18" r="2" fill="currentColor" />
    </svg>
  )
}

export default function Events() {
  const { filter = 'new' } = useParams<{ filter?: string }>()
  const navigate = useNavigate()
  const filterDropdownRef = useRef<HTMLDivElement>(null)
  const cardWrapRef = useRef<HTMLDivElement>(null)
  const { user, loading: userLoading, fetchUser, isDemo, useDemoEvents, setUseDemoEvents } = useApp()
  const [events, setEvents] = useState<EventType[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [currentIndex, setCurrentIndex] = useState(0)
  const [swipeOffset, setSwipeOffset] = useState(0)
  const [actionBusy, setActionBusy] = useState(false)
  const [touchStartX, setTouchStartX] = useState<number | null>(null)
  const [touchStartY, setTouchStartY] = useState<number | null>(null)
  const [filterDropdownOpen, setFilterDropdownOpen] = useState(false)
  const [exitDirection, setExitDirection] = useState<'left' | 'right' | null>(null)
  const [exitStartOffset, setExitStartOffset] = useState(0)
  const [exitAnimateToEnd, setExitAnimateToEnd] = useState(false)
  const [photoViewerPhotos, setPhotoViewerPhotos] = useState<string[] | null>(null)

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  useEffect(() => {
    if (!filterDropdownOpen) return
    const close = (e: MouseEvent) => {
      if (filterDropdownRef.current && !filterDropdownRef.current.contains(e.target as Node)) {
        setFilterDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [filterDropdownOpen])

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

  const performLike = useCallback((startOffset = 0) => {
    const ev = events[currentIndex]
    if (!ev || actionBusy || currentIndex >= events.length) return
    setActionBusy(true)
    setExitStartOffset(startOffset)
    setExitAnimateToEnd(false)
    setExitDirection('right')
    if (!startOffset) setSwipeOffset(0)
    if (isApiConfigured() && !isDemo && !useDemoEvents) {
      api.likeEvent(ev.id).then((res) => {
        if (res.mutual) alert('💞 Взаимная симпатия! Можете обменяться контактами.')
        else alert('❤️ Лайк отправлен!')
      }).catch((e) => alert(e instanceof Error ? e.message : 'Ошибка'))
    }
    setTimeout(() => {
      setCurrentIndex((i) => Math.min(i + 1, events.length))
      setExitDirection(null)
      setExitAnimateToEnd(false)
      setSwipeOffset(0)
      setActionBusy(false)
    }, CARD_EXIT_DURATION_MS)
  }, [events, currentIndex, actionBusy, isDemo, useDemoEvents])

  const performSkip = useCallback((startOffset = 0) => {
    const ev = events[currentIndex]
    if (!ev || actionBusy || currentIndex >= events.length) return
    setActionBusy(true)
    setExitStartOffset(startOffset)
    setExitAnimateToEnd(false)
    setExitDirection('left')
    if (!startOffset) setSwipeOffset(0)
    if (isApiConfigured() && !isDemo && !useDemoEvents) {
      api.skipEvent(ev.id).catch(() => {})
    }
    setTimeout(() => {
      setCurrentIndex((i) => Math.min(i + 1, events.length))
      setExitDirection(null)
      setExitAnimateToEnd(false)
      setSwipeOffset(0)
      setActionBusy(false)
    }, CARD_EXIT_DURATION_MS)
  }, [events, currentIndex, actionBusy, isDemo, useDemoEvents])

  useEffect(() => {
    if (!exitDirection) return
    const id = requestAnimationFrame(() => setExitAnimateToEnd(true))
    return () => cancelAnimationFrame(id)
  }, [exitDirection])

  useEffect(() => {
    const el = cardWrapRef.current
    if (!el) return
    const onTouchMove = (e: TouchEvent) => {
      if (touchStartX === null || touchStartY === null) return
      const dx = e.touches[0].clientX - touchStartX
      const dy = e.touches[0].clientY - touchStartY
      if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 8) {
        e.preventDefault()
      }
    }
    el.addEventListener('touchmove', onTouchMove, { passive: false })
    return () => el.removeEventListener('touchmove', onTouchMove)
  }, [touchStartX, touchStartY])

  const handleSwipeEnd = useCallback(() => {
    if (swipeOffset > SWIPE_THRESHOLD) {
      performLike(swipeOffset)
      setTouchStartX(null)
      setTouchStartY(null)
      return
    }
    if (swipeOffset < -SWIPE_THRESHOLD) {
      performSkip(swipeOffset)
      setTouchStartX(null)
      setTouchStartY(null)
      return
    }
    setSwipeOffset(0)
    setTouchStartX(null)
    setTouchStartY(null)
  }, [swipeOffset, performLike, performSkip])

  const handleTouchStart = (e: React.TouchEvent) => {
    setTouchStartX(e.touches[0].clientX)
    setTouchStartY(e.touches[0].clientY)
  }
  const handleTouchMove = (e: React.TouchEvent) => {
    if (touchStartX === null || touchStartY === null) return
    const dx = e.touches[0].clientX - touchStartX
    const dy = e.touches[0].clientY - touchStartY
    if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 8) {
      e.preventDefault()
    }
    setSwipeOffset(Math.max(-280, Math.min(280, dx)))
  }
  const handleTouchEnd = () => {
    handleSwipeEnd()
    setTouchStartX(null)
    setTouchStartY(null)
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
      <div className="page-header page-header-events-compact">
        <h1 className="page-title page-title-events animate-in">Найти встречу</h1>
        <p className="page-subtitle page-subtitle-events animate-in stagger-1">Свайп влево — пропустить, вправо — лайк</p>
      </div>
      <div className="filter-dropdown-wrap animate-in stagger-2" ref={filterDropdownRef}>
        <button
          type="button"
          className="filter-dropdown-btn"
          onClick={() => setFilterDropdownOpen((o) => !o)}
          aria-expanded={filterDropdownOpen}
          aria-haspopup="listbox"
          aria-label="Выбрать фильтр"
        >
          <span className="filter-dropdown-icon">
            <FilterSliderIcon />
          </span>
          <span className="filter-dropdown-label">Фильтры</span>
          <span className="filter-dropdown-arrow">{filterDropdownOpen ? '▲' : '▼'}</span>
        </button>
        {filterDropdownOpen && (
          <div className="filter-dropdown-panel" role="listbox">
            {FILTERS.map((f) => (
              <button
                key={f}
                type="button"
                role="option"
                aria-selected={filter === f}
                className={`filter-dropdown-item ${filter === f ? 'filter-dropdown-item-active' : ''}`}
                onClick={() => {
                  navigate(`/events/${f}`)
                  setFilterDropdownOpen(false)
                }}
              >
                {FILTER_LABELS[f] ?? f}
              </button>
            ))}
          </div>
        )}
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
      {!loading && hasCards && (currentEvent || (exitDirection && events[currentIndex + 1])) && (
        <div className="events-tinder">
          <div className="events-tinder-cards">
            {exitDirection ? (
              <>
                {events[currentIndex + 1] && (
                  <div className="events-tinder-card-wrap events-tinder-card-enter" key={`enter-${events[currentIndex + 1].id}`}>
                    <EventCard event={events[currentIndex + 1]} navigate={navigate} onAvatarClick={setPhotoViewerPhotos} />
                  </div>
                )}
                <div
                  className="events-tinder-card-wrap events-tinder-card-exit"
                  key={`exit-${currentEvent?.id}`}
                  style={{
                    transform: exitAnimateToEnd
                      ? (exitDirection === 'right' ? 'translateX(120vw) rotate(22deg)' : 'translateX(-120vw) rotate(-22deg)')
                      : `translateX(${exitStartOffset}px) rotate(${exitStartOffset * 0.06}deg)`,
                    opacity: exitAnimateToEnd ? 0 : 1,
                    transition: `transform 0.55s cubic-bezier(0.32, 0.72, 0.38, 1), opacity 0.5s cubic-bezier(0.33, 0, 0.2, 1)`,
                  }}
                >
                  {currentEvent && <EventCard event={currentEvent} navigate={navigate} onAvatarClick={setPhotoViewerPhotos} />}
                </div>
              </>
            ) : (
              <div
                ref={cardWrapRef}
                className="events-tinder-card-wrap"
                onTouchStart={handleTouchStart}
                onTouchMove={handleTouchMove}
                onTouchEnd={handleTouchEnd}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseLeave}
                style={{
                  transform: `translateX(${swipeOffset}px) rotate(${swipeOffset * 0.07}deg)`,
                  transition: touchStartX === null ? 'transform 0.35s cubic-bezier(0.34, 1.2, 0.64, 1)' : 'none',
                }}
              >
                {swipeOffset > 40 && (
                  <span className="events-tinder-badge events-tinder-badge-like">❤️ Лайк</span>
                )}
                {swipeOffset < -40 && (
                  <span className="events-tinder-badge events-tinder-badge-skip">Пропустить</span>
                )}
                {currentEvent && <EventCard event={currentEvent} navigate={navigate} onAvatarClick={setPhotoViewerPhotos} />}
              </div>
            )}
          </div>
          <div className="events-tinder-actions">
            <button
              type="button"
              className="btn events-tinder-btn events-tinder-btn-skip"
              onClick={() => performSkip(0)}
              disabled={actionBusy}
              aria-label="Пропустить"
            >
              ✕
            </button>
            <button
              type="button"
              className="btn events-tinder-btn events-tinder-btn-like"
              onClick={() => performLike(0)}
              disabled={actionBusy}
              aria-label="Лайк"
            >
              ❤️
            </button>
          </div>
        </div>
      )}
      {photoViewerPhotos && photoViewerPhotos.length > 0 && (
        <PhotoViewer photos={photoViewerPhotos} onClose={() => setPhotoViewerPhotos(null)} />
      )}
    </>
  )
}

function EventCard({
  event: ev,
  navigate,
  onAvatarClick,
}: {
  event: EventType
  navigate: (to: string, opts?: { state?: { fromEventId: number } }) => void
  onAvatarClick?: (photos: string[]) => void
}) {
  return (
    <div className="card event-card">
      <div
        className="event-card-image-wrap"
        role="button"
        tabIndex={0}
        onClick={() => navigate(`/event/${ev.id}`)}
        onKeyDown={(e) => e.key === 'Enter' && navigate(`/event/${ev.id}`)}
      >
        {ev.photo ? (
          <img src={eventPhotoSrc(ev.photo)} alt="" />
        ) : (
          <div className="event-card-image-placeholder">
            {ev.category?.slice(0, 2) || '🎉'}
          </div>
        )}
        {ev.category && <span className="event-card-cat-badge">{ev.category}</span>}
      </div>
      <div className="event-card-footer">
        <div
          className="event-card-author"
          role="button"
          tabIndex={0}
          onClick={(e) => {
            e.stopPropagation()
            navigate(`/profile/${ev.user_id}`, { state: { fromEventId: ev.id } })
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.stopPropagation()
              navigate(`/profile/${ev.user_id}`, { state: { fromEventId: ev.id } })
            }
          }}
        >
          <button
            type="button"
            className="event-author-avatar-wrap event-author-avatar-btn"
            onClick={(e) => {
              e.stopPropagation()
              if (ev.organizer_photo || ev.user_id) {
                onAvatarClick?.([eventPhotoSrc(ev.organizer_photo || `/api/photo/user/${ev.user_id}`)])
              }
            }}
            aria-label="Увеличить фото"
          >
            {(ev.organizer_photo || ev.user_id) ? (
              <img
                src={eventPhotoSrc(ev.organizer_photo || `/api/photo/user/${ev.user_id}`)}
                alt=""
                className="event-author-avatar"
                onError={(e) => {
                  e.currentTarget.style.display = 'none'
                  const wrap = e.currentTarget.closest('.event-author-avatar-wrap')
                  const placeholder = wrap?.querySelector('.event-author-avatar-placeholder') as HTMLElement
                  if (placeholder) placeholder.style.display = 'flex'
                }}
              />
            ) : null}
            <div
              className="event-author-avatar-placeholder"
              style={{ display: (ev.organizer_photo || ev.user_id) ? 'none' : 'flex' }}
              aria-hidden
            >
              {(ev.name ?? '?').slice(0, 1)}
            </div>
          </button>
          <div className="event-author-info">
            <span className="event-author-name">{ev.name ?? 'Пользователь'}</span>
            <span className="event-author-meta">{ev.age} · {ev.city}</span>
            <span className="event-card-author-hint">Нажать — открыть профиль</span>
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
