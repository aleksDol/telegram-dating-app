import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { api, isApiConfigured } from '../api/client'

export default function Referral() {
  const navigate = useNavigate()
  const { user, fetchUser } = useApp()
  const [referralCode, setReferralCode] = useState('')
  const [referralsCount, setReferralsCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  useEffect(() => {
    if (!user) {
      navigate('/', { replace: true })
      return
    }
    if (!isApiConfigured()) {
      setReferralCode('REF_DEMO')
      setReferralsCount(user.referrals_count ?? 0)
      setLoading(false)
      return
    }
    setLoading(true)
    api
      .getReferral()
      .then(({ referral_code, referrals_count }) => {
        setReferralCode(referral_code)
        setReferralsCount(referrals_count)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [user, navigate])

  if (!user) return null

  const botUsername = import.meta.env.VITE_BOT_USERNAME || (window as unknown as { __BOT_USERNAME?: string }).__BOT_USERNAME || 'Spontime_bot'
  const link = `https://t.me/${botUsername}?start=${referralCode}`

  const copyLink = () => {
    if (!link) return
    navigator.clipboard.writeText(link).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <>
      <DemoBanner />
      <div className="page-header">
        <h1 className="page-title">Реферальная программа</h1>
        <p className="page-subtitle">Приглашайте друзей и получайте очки</p>
      </div>
      {loading && <div className="screen-center"><div className="loader" /><p className="text-muted">Загрузка...</p></div>}
      {!loading && (
        <div className="card referral-code-card">
          <h2 className="section-title">Ваш реферальный код</h2>
          <p className="referral-code-value">{referralCode}</p>
          <div className="referral-stats">
            <span>Приглашено: <strong>{referralsCount}</strong></span>
            <span>Очков: <strong>{referralsCount * 100}</strong></span>
          </div>
        </div>
      )}
      <div className="card">
        <h2 className="section-title">Как приглашать</h2>
        <p className="card-desc">Отправьте друзьям ссылку. После регистрации по ссылке вы оба получите бонусные очки.</p>
        {referralCode && (
          <button
            type="button"
            className="referral-link referral-link-btn"
            onClick={copyLink}
            title="Нажмите, чтобы скопировать"
          >
            {link}
            {copied && <span className="referral-copied">Скопировано!</span>}
          </button>
        )}
      </div>
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
