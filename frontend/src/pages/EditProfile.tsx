import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { api, isApiConfigured } from '../api/client'
import { CITIES, GENDERS, RELATIONSHIP_STATUSES } from '../constants'

export default function EditProfile() {
  const navigate = useNavigate()
  const { user, loading: userLoading, fetchUser, setUser } = useApp()
  const [name, setName] = useState('')
  const [age, setAge] = useState('')
  const [gender, setGender] = useState('')
  const [city, setCity] = useState('')
  const [relationshipStatus, setRelationshipStatus] = useState('')
  const [purpose, setPurpose] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  useEffect(() => {
    if (user) {
      setName(user.name || '')
      setAge(String(user.age ?? ''))
      setGender(user.gender || '')
      setCity(user.city || '')
      setRelationshipStatus(user.relationship_status || '')
      setPurpose(user.purpose || 'куда-то сходить')
    }
  }, [user])

  useEffect(() => {
    if (!userLoading && !user) navigate('/', { replace: true })
  }, [userLoading, user, navigate])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const ageNum = parseInt(age, 10)
    if (!name.trim()) {
      setError('Введите имя')
      return
    }
    if (isNaN(ageNum) || ageNum < 18 || ageNum > 100) {
      setError('Возраст от 18 до 100')
      return
    }
    if (!gender || !city) {
      setError('Заполните пол и город')
      return
    }
    setSaving(true)
    setError('')
    try {
      if (isApiConfigured()) {
        const { user: updated } = await api.updateProfile({
          name: name.trim(),
          age: ageNum,
          gender,
          city,
          relationship_status: relationshipStatus || 'Не в отношениях',
          purpose: purpose.trim() || 'куда-то сходить',
        })
        setUser(updated)
      } else {
        setUser({
          ...user!,
          name: name.trim(),
          age: ageNum,
          gender,
          city,
          relationship_status: relationshipStatus || 'Не в отношениях',
          purpose: purpose.trim() || 'куда-то сходить',
        })
      }
      navigate('/profile', { replace: true })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }

  if (userLoading || !user) return null

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Редактировать профиль</h1>
        <p className="page-subtitle">Измените данные и нажмите «Сохранить»</p>
      </div>
      <form className="form" onSubmit={handleSubmit}>
        <label className="label">Имя</label>
        <input
          className="input"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Ваше имя"
          required
        />

        <label className="label">Возраст</label>
        <input
          className="input"
          type="number"
          min={18}
          max={100}
          value={age}
          onChange={(e) => setAge(e.target.value)}
          placeholder="18–100"
          required
        />

        <label className="label">Пол</label>
        <select
          className="input"
          value={gender}
          onChange={(e) => setGender(e.target.value)}
          required
        >
          <option value="">—</option>
          {GENDERS.map((g) => (
            <option key={g} value={g}>{g}</option>
          ))}
        </select>

        <label className="label">Город</label>
        <select
          className="input"
          value={city}
          onChange={(e) => setCity(e.target.value)}
          required
        >
          <option value="">—</option>
          {CITIES.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>

        <label className="label">Статус отношений</label>
        <select
          className="input"
          value={relationshipStatus}
          onChange={(e) => setRelationshipStatus(e.target.value)}
        >
          {RELATIONSHIP_STATUSES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        <label className="label">Цель знакомств</label>
        <input
          className="input"
          value={purpose}
          onChange={(e) => setPurpose(e.target.value)}
          placeholder="Например: куда-то сходить"
        />

        {error && <p className="text-error">{error}</p>}
        <div className="form-actions">
          <button type="button" className="btn btn-secondary" onClick={() => navigate('/profile')}>
            Отмена
          </button>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Сохранение...' : 'Сохранить'}
          </button>
        </div>
      </form>
    </>
  )
}
