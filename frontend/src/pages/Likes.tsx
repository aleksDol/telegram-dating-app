import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { useTelegram } from '../hooks/useTelegram'
import { api, isApiConfigured, API_BASE } from '../api/client'
import Logo from '../components/Logo'
import PhotoViewer from '../components/PhotoViewer'
import type { PendingLike as PendingLikeType, LikeMatch as LikeMatchType } from '../types'

function photoSrc(url: string | undefined): string {
  if (!url) return ''
  if (url.startsWith('data:') || url.startsWith('http')) return url
  return API_BASE + url
}

/** Ссылка на чат с пользователем в Telegram (по username или tg://user?id=). */
function telegramChatLink(userId: number, username?: string | null): string {
  if (username && username.trim()) return `https://t.me/${username.trim()}`
  return `tg://user?id=${userId}`
}

/** Список URL фото пользователя для просмотра (все фото или одно). */
function userPhotosForViewer(
  photo: string | undefined,
  photos: string[] | undefined
): string[] {
  const list = photos?.length ? photos : photo ? [photo] : []
  return list.map((u) => photoSrc(u)).filter(Boolean)
}

export default function Likes() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, loading: userLoading, fetchUser } = useApp()
  const { openExternalLink } = useTelegram()
  const [likes, setLikes] = useState<PendingLikeType[]>([])
  const [matches, setMatches] = useState<LikeMatchType[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [respondingId, setRespondingId] = useState<number | null>(null)
  const [photoViewerPhotos, setPhotoViewerPhotos] = useState<string[] | null>(null)

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  const loadLikesAndMatches = () => {
    if (!user || !isApiConfigured()) {
      setLikes([])
      setMatches([])
      setLoading(false)
      return
    }
    setLoading(true)
    setError('')
    Promise.all([api.getPendingLikes(), api.getLikesMatches()])
      .then(([pendingRes, matchesRes]) => {
        setLikes(pendingRes.likes)
        setMatches(matchesRes.matches)
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Ошибка'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    if (!user && !userLoading) {
      navigate('/', { replace: true })
      return
    }
    if (!user) return
    if (location.pathname !== '/likes') return
    if (!isApiConfigured()) {
      setLikes([])
      setMatches([])
      setLoading(false)
      return
    }
    loadLikesAndMatches()
  }, [user, userLoading, navigate, location.pathname])

  const handleRespond = async (likeId: number, action: 'mutual' | 'ignore') => {
    setRespondingId(likeId)
    try {
      await api.respondToLike(likeId, action)
      setLikes((prev) => prev.filter((l) => l.like_id !== likeId))
      if (action === 'mutual') loadLikesAndMatches()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка')
    } finally {
      setRespondingId(null)
    }
  }

  if (!user) return null

  return (
    <>
      <div className="page-header page-header-with-logo">
        <Logo size="sm" showText link />
        <h1 className="page-title">Лайки</h1>
        <p className="page-subtitle" style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          Ответьте взаимностью или пропустите
          <button
            type="button"
            className="btn btn-secondary"
            style={{ fontSize: 13 }}
            disabled={loading}
            onClick={() => loadLikesAndMatches()}
          >
            {loading ? '...' : '🔄 Обновить'}
          </button>
        </p>
      </div>
      {loading && (
        <div className="screen-center">
          <div className="loader" />
          <p className="text-muted">Загрузка...</p>
        </div>
      )}
      {error && <p className="text-error">{error}</p>}
      {!loading && !error && likes.length === 0 && matches.length === 0 && (
        <div className="empty-state">
          <span className="empty-icon">💌</span>
          <p>Нет новых лайков</p>
          <p className="text-muted" style={{ fontSize: 14, marginTop: 8 }}>
            Когда кто-то лайкнет вашу встречу, он появится здесь
          </p>
        </div>
      )}

      {!loading && matches.length > 0 && (
        <section style={{ marginBottom: 24 }}>
          <h2 className="page-subtitle" style={{ marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
            💞 Взаимные симпатии
            <span className="chip chip-active" style={{ fontSize: 12 }}>МАТЧИНГ</span>
          </h2>
          <div className="event-list">
            {matches.map((item) => (
              <div key={item.user_id} className="card event-card">
                <div className="event-card-footer" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
                  <div style={{ marginBottom: 8 }}>
                    <span className="chip chip-active" style={{ fontSize: 11 }}>МАТЧИНГ</span>
                  </div>
                  {item.event && (
                    <div style={{ marginBottom: 12 }}>
                      <h3 className="event-card-title">{item.event.title}</h3>
                      <p className="event-card-meta">
                        {item.event.city} · {item.event.event_date?.slice(0, 16)}
                      </p>
                    </div>
                  )}
                  <div className="event-card-author" style={{ marginBottom: 8 }}>
                    <button
                      type="button"
                      className="event-author-avatar-wrap event-author-avatar-btn"
                      onClick={(e) => {
                        e.stopPropagation()
                        const urls = userPhotosForViewer(item.user?.photo, item.user?.photos)
                        if (urls.length) setPhotoViewerPhotos(urls)
                      }}
                      aria-label="Увеличить фото"
                    >
                      {item.user?.photo ? (
                        <img src={photoSrc(item.user.photo)} alt="" className="event-author-avatar" />
                      ) : (
                        <div className="event-author-avatar-placeholder">
                          {(item.user?.name ?? '?').slice(0, 1)}
                        </div>
                      )}
                    </button>
                    <div
                      className="event-author-info event-author-info-clickable"
                      role="button"
                      tabIndex={0}
                      onClick={() => item.user && navigate(`/profile/${item.user.user_id}`, { state: { fromLikes: true } })}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault()
                          item.user && navigate(`/profile/${item.user.user_id}`, { state: { fromLikes: true } })
                        }
                      }}
                      aria-label="Открыть профиль"
                    >
                      <span className="event-author-name">{item.user?.name ?? 'Пользователь'}</span>
                      <span className="event-author-meta">
                        {item.user?.age} · {item.user?.city ?? '—'}
                        {item.user?.username ? ` · @${item.user.username}` : ''}
                      </span>
                      <span className="event-author-arrow">→</span>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ marginTop: 8, width: '100%' }}
                    onClick={() => item.user && navigate(`/profile/${item.user.user_id}`, { state: { fromLikes: true } })}
                  >
                    Открыть профиль
                  </button>
                  <a
                    href={telegramChatLink(item.user_id, item.user?.username)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-primary"
                    style={{ marginTop: 12, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8, textDecoration: 'none' }}
                    onClick={(e) => {
                      e.preventDefault()
                      openExternalLink(telegramChatLink(item.user_id, item.user?.username))
                    }}
                  >
                    ✉️ Написать в Telegram
                  </a>
                  <p className="text-muted" style={{ marginTop: 8, fontSize: 12 }}>
                    Сообщите, что вы из SponTime, чтобы не вводить в заблуждение
                  </p>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {!loading && (() => {
        const matchUserIds = new Set(matches.map((m) => m.user_id))
        const pendingOnly = likes.filter((item) => !item.liker?.user_id || !matchUserIds.has(item.liker.user_id))
        if (pendingOnly.length === 0) return null
        return (
        <section>
          <h2 className="page-subtitle" style={{ marginBottom: 12 }}>Новые лайки</h2>
          <div className="event-list">
            {pendingOnly.map((item) => (
              <div key={item.like_id} className="card event-card">
                <div className="event-card-footer" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
                  <div
                    className="event-card-body"
                    style={{ cursor: 'default', marginBottom: 12 }}
                  >
                    <p className="text-muted" style={{ marginBottom: 8, fontSize: 14 }}>
                      Лайкнул вашу встречу
                    </p>
                    {item.event && (
                      <div style={{ marginBottom: 12 }}>
                        <h3 className="event-card-title">{item.event.title}</h3>
                        <p className="event-card-meta">
                          {item.event.city} · {item.event.event_date?.slice(0, 16)}
                        </p>
                      </div>
                    )}
                  </div>
                  <div className="event-card-author" style={{ marginBottom: 12 }}>
                    <button
                      type="button"
                      className="event-author-avatar-wrap event-author-avatar-btn"
                      onClick={(e) => {
                        e.stopPropagation()
                        const urls = userPhotosForViewer(item.liker?.photo, item.liker?.photos)
                        if (urls.length) setPhotoViewerPhotos(urls)
                      }}
                      aria-label="Увеличить фото"
                    >
                      {item.liker?.photo ? (
                        <img src={photoSrc(item.liker.photo)} alt="" className="event-author-avatar" />
                      ) : (
                        <div className="event-author-avatar-placeholder">
                          {(item.liker?.name ?? '?').slice(0, 1)}
                        </div>
                      )}
                    </button>
                    <div
                      className="event-author-info event-author-info-clickable"
                      role="button"
                      tabIndex={0}
                      onClick={() => item.liker && navigate(`/profile/${item.liker.user_id}`, { state: { fromLikes: true } })}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault()
                          item.liker && navigate(`/profile/${item.liker.user_id}`, { state: { fromLikes: true } })
                        }
                      }}
                      aria-label="Открыть профиль"
                    >
                      <span className="event-author-name">{item.liker?.name ?? 'Пользователь'}</span>
                      <span className="event-author-meta">
                        {item.liker?.age} · {item.liker?.city ?? '—'}
                      </span>
                      <p className="text-muted" style={{ margin: '4px 0 0', fontSize: 12 }}>
                        Контакт (ник) виден после взаимности
                      </p>
                      <span className="event-author-arrow">→</span>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ marginTop: 8, width: '100%' }}
                    onClick={() => item.liker && navigate(`/profile/${item.liker.user_id}`, { state: { fromLikes: true } })}
                  >
                    Открыть профиль
                  </button>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <button
                      type="button"
                      className="btn btn-primary"
                      disabled={respondingId === item.like_id}
                      onClick={() => handleRespond(item.like_id, 'mutual')}
                    >
                      {respondingId === item.like_id ? '...' : '❤️ Ответить взаимностью'}
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      disabled={respondingId === item.like_id}
                      onClick={() => handleRespond(item.like_id, 'ignore')}
                    >
                      ➡️ Пропустить
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
        )
      })()}
      {photoViewerPhotos && photoViewerPhotos.length > 0 && (
        <PhotoViewer photos={photoViewerPhotos} onClose={() => setPhotoViewerPhotos(null)} />
      )}
    </>
  )
}
