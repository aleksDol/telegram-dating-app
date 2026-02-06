import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { api, isApiConfigured } from '../api/client'
import Logo from '../components/Logo'
import type { PendingLike as PendingLikeType } from '../types'

export default function Likes() {
  const navigate = useNavigate()
  const { user, loading: userLoading, fetchUser } = useApp()
  const [likes, setLikes] = useState<PendingLikeType[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [respondingId, setRespondingId] = useState<number | null>(null)

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  useEffect(() => {
    if (!user && !userLoading) {
      navigate('/', { replace: true })
      return
    }
    if (!user) return
    if (!isApiConfigured()) {
      setLikes([])
      setLoading(false)
      return
    }
    setLoading(true)
    setError('')
    api
      .getPendingLikes()
      .then(({ likes: list }) => setLikes(list))
      .catch((e) => setError(e instanceof Error ? e.message : 'Ошибка'))
      .finally(() => setLoading(false))
  }, [user, userLoading, navigate])

  const handleRespond = async (likeId: number, action: 'mutual' | 'ignore') => {
    setRespondingId(likeId)
    try {
      await api.respondToLike(likeId, action)
      setLikes((prev) => prev.filter((l) => l.like_id !== likeId))
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
        <p className="page-subtitle">Ответьте взаимностью или пропустите</p>
      </div>
      {loading && (
        <div className="screen-center">
          <div className="loader" />
          <p className="text-muted">Загрузка...</p>
        </div>
      )}
      {error && <p className="text-error">{error}</p>}
      {!loading && !error && likes.length === 0 && (
        <div className="empty-state">
          <span className="empty-icon">💌</span>
          <p>Нет новых лайков</p>
          <p className="text-muted" style={{ fontSize: 14, marginTop: 8 }}>
            Когда кто-то лайкнет ваше событие, он появится здесь
          </p>
        </div>
      )}
      {!loading && likes.length > 0 && (
        <div className="event-list">
          {likes.map((item) => (
            <div key={item.like_id} className="card event-card">
              <div className="event-card-footer" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
                <div
                  className="event-card-body"
                  style={{ cursor: 'default', marginBottom: 12 }}
                >
                  <p className="text-muted" style={{ marginBottom: 8, fontSize: 14 }}>
                    Лайкнул ваше событие
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
                <div
                  className="event-card-author"
                  role="button"
                  tabIndex={0}
                  onClick={() => item.liker && navigate(`/profile/${item.liker.user_id}`)}
                  onKeyDown={(e) =>
                    e.key === 'Enter' && item.liker && navigate(`/profile/${item.liker.user_id}`)
                  }
                  style={{ marginBottom: 12 }}
                >
                  {item.liker?.photo ? (
                    <img src={item.liker.photo} alt="" className="event-author-avatar" />
                  ) : (
                    <div className="event-author-avatar-placeholder">
                      {(item.liker?.name ?? '?').slice(0, 1)}
                    </div>
                  )}
                  <div className="event-author-info">
                    <span className="event-author-name">{item.liker?.name ?? 'Пользователь'}</span>
                    <span className="event-author-meta">
                      {item.liker?.age} · {item.liker?.city ?? '—'}
                      {item.liker?.username ? ` · @${item.liker.username}` : ''}
                    </span>
                  </div>
                  <span className="event-author-arrow">→</span>
                </div>
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
      )}
    </>
  )
}
