import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { DEMO_USER_ID } from '../context/AppContext'
import { api, isApiConfigured } from '../api/client'
import { ACHIEVEMENTS } from '../constants'
import { MOCK_ACHIEVEMENT_IDS, MOCK_POINTS } from '../demoData'
import type { Achievement } from '../types'

export default function Achievements() {
  const navigate = useNavigate()
  const { user, fetchUser } = useApp()
  const [achievements, setAchievements] = useState<Achievement[]>([])
  const [points, setPoints] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  useEffect(() => {
    if (!user) {
      navigate('/', { replace: true })
      return
    }
    if (!isApiConfigured()) {
      const isDemoMode = user.user_id === DEMO_USER_ID
      if (isDemoMode) {
        setPoints(MOCK_POINTS)
        setAchievements(
          MOCK_ACHIEVEMENT_IDS.map((id) => {
            const d = ACHIEVEMENTS[id as keyof typeof ACHIEVEMENTS]
            return d ? { id, name: d.name, description: d.description, emoji: d.emoji, points: d.points } : null
          }).filter((a): a is Achievement => a !== null)
        )
      } else {
        setPoints(user.points ?? 0)
        setAchievements([])
      }
      setLoading(false)
      return
    }
    setLoading(true)
    api
      .getAchievements()
      .then(({ achievements: list, points: p }) => {
        setAchievements(list)
        setPoints(p)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [user, navigate])

  if (!user) return null

  return (
    <>
      <DemoBanner />
      <div className="page-header">
        <h1 className="page-title">Достижения</h1>
        <p className="page-subtitle">Зарабатывайте очки за активность</p>
      </div>
      <div className="card card-points">
        <span className="card-points-emoji">🏆</span>
        <span className="card-points-value">{points}</span>
        <span className="card-points-label">очков рейтинга</span>
      </div>
      {loading && <div className="screen-center"><div className="loader" /><p className="text-muted">Загрузка...</p></div>}
      {!loading && (
        <section className="section">
          <h2 className="section-title">Все достижения</h2>
          <div className="achievement-list">
            {Object.entries(ACHIEVEMENTS).map(([id, data]) => {
              const unlocked = achievements.some((a) => a.id === id)
              return (
                <div key={id} className={`card achievement-card ${unlocked ? 'achievement-unlocked' : ''}`}>
                  <span className="achievement-emoji">{unlocked ? data.emoji : '🔒'}</span>
                  <div className="achievement-body">
                    <h3 className="achievement-name">{data.name}</h3>
                    <p className="achievement-desc">{data.description}</p>
                    <span className="achievement-points">+{data.points} очков</span>
                  </div>
                </div>
              )
            })}
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
