import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { useTelegram } from '../hooks/useTelegram'
import { CITIES, GENDERS, RELATIONSHIP_STATUSES } from '../constants'
import { isApiConfigured, api } from '../api/client'
import type { User } from '../types'

const STEPS = ['name', 'age', 'gender', 'city', 'relationship', 'purpose', 'photo'] as const

export default function Register() {
  const navigate = useNavigate()
  const { setUser } = useApp()
  const { user: tgUser } = useTelegram()
  const [stepIndex, setStepIndex] = useState(0)
  const step = STEPS[stepIndex]

  const [name, setName] = useState('')
  const [age, setAge] = useState('')
  const [gender, setGender] = useState('')
  const [city, setCity] = useState('')
  const [relationship, setRelationship] = useState('')
  const [purpose, setPurpose] = useState('куда-то сходить')
  const [photo, setPhoto] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const next = () => setStepIndex((i) => Math.min(i + 1, STEPS.length - 1))
  const canNext = () => {
    if (step === 'name') return name.trim().length > 0
    if (step === 'age') {
      const n = parseInt(age, 10)
      return !isNaN(n) && n >= 18 && n <= 100
    }
    if (step === 'gender') return gender.length > 0
    if (step === 'city') return CITIES.includes(city)
    if (step === 'relationship') return relationship.length > 0
    return true
  }

  const enterDemoWithForm = () => {
    const ageNum = parseInt(age, 10) || 25
    const mockUser: User = {
      user_id: 0,
      name: name.trim() || 'Гость',
      age: isNaN(ageNum) ? 25 : Math.min(100, Math.max(18, ageNum)),
      gender: gender || 'Мужской',
      city: city || 'Москва',
      relationship_status: relationship || 'Не в отношениях',
      purpose: purpose.trim() || 'куда-то сходить',
      photo: photo || undefined,
      points: 0,
      referrals_count: 0,
    }
    setUser(mockUser)
    navigate('/', { replace: true })
  }

  const handleRegister = async () => {
    const ageNum = parseInt(age, 10)
    setLoading(true)
    setError('')
    try {
      if (isApiConfigured()) {
        const { user } = await api.register({
          name: name.trim(),
          age: ageNum,
          gender,
          city,
          relationship_status: relationship,
          purpose: purpose.trim() || 'куда-то сходить',
          photo: photo || undefined,
        })
        setUser(user)
        navigate('/', { replace: true })
      } else {
        enterDemoWithForm()
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Ошибка регистрации')
      // Показать возможность войти в режим просмотра с введёнными данными
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <div className="register-demo-bar">
        <span>Нет бэкенда или не работает?</span>
        <button type="button" className="btn-demo-inline" onClick={enterDemoWithForm}>
          Посмотреть приложение →
        </button>
      </div>
      <h1 className="page-title">Регистрация</h1>

      {step === 'name' && (
        <>
          <label className="label">Как тебя зовут?</label>
          <input
            className="input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Имя"
            autoFocus
          />
          <button className="btn btn-primary" onClick={next} disabled={!name.trim()}>
            Далее
          </button>
        </>
      )}

      {step === 'age' && (
        <>
          <label className="label">Возраст</label>
          <input
            className="input"
            type="number"
            min={18}
            max={100}
            value={age}
            onChange={(e) => setAge(e.target.value)}
            placeholder="18"
          />
          <button
            className="btn btn-primary"
            onClick={next}
            disabled={!age || parseInt(age, 10) < 18 || parseInt(age, 10) > 100}
          >
            Далее
          </button>
        </>
      )}

      {step === 'gender' && (
        <>
          <label className="label">Пол</label>
          {GENDERS.map((g) => (
            <button
              key={g}
              className="btn btn-secondary"
              style={{ display: 'block', width: '100%', marginBottom: 8 }}
              onClick={() => { setGender(g); next() }}
            >
              {g}
            </button>
          ))}
        </>
      )}

      {step === 'city' && (
        <>
          <label className="label">Город</label>
          <input
            className="input"
            list="cities"
            value={city}
            onChange={(e) => setCity(e.target.value)}
            placeholder="Начните вводить город"
          />
          <datalist id="cities">
            {CITIES.map((c) => (
              <option key={c} value={c} />
            ))}
          </datalist>
          {city && !CITIES.includes(city) && (
            <p className="text-muted" style={{ marginBottom: 8 }}>
              Выберите город из выпадающего списка при вводе
            </p>
          )}
          <button
            className="btn btn-primary"
            onClick={next}
            disabled={!CITIES.includes(city)}
          >
            Далее
          </button>
        </>
      )}

      {step === 'relationship' && (
        <>
          <label className="label">Статус отношений</label>
          {RELATIONSHIP_STATUSES.map((s) => (
            <button
              key={s}
              className="btn btn-secondary"
              style={{ display: 'block', width: '100%', marginBottom: 8 }}
              onClick={() => { setRelationship(s); next() }}
            >
              {s}
            </button>
          ))}
        </>
      )}

      {step === 'purpose' && (
        <>
          <label className="label">Цель (необязательно)</label>
          <input
            className="input"
            value={purpose}
            onChange={(e) => setPurpose(e.target.value)}
            placeholder="например: куда-то сходить"
          />
          <button className="btn btn-primary" onClick={next}>
            Далее
          </button>
        </>
      )}

      {step === 'photo' && (
        <>
          <label className="label">Фото (URL, необязательно)</label>
          <input
            className="input"
            value={photo}
            onChange={(e) => setPhoto(e.target.value)}
            placeholder="https://..."
          />
          <button className="btn btn-primary btn-lg block-btn" onClick={handleRegister} disabled={loading}>
            {loading ? 'Регистрация...' : 'Готово'}
          </button>
          {error && (
            <div className="card card-error" style={{ marginTop: 12 }}>
              <p className="text-error">{error}</p>
              <button type="button" className="btn btn-ghost" style={{ marginTop: 8 }} onClick={enterDemoWithForm}>
                Войти в режиме просмотра с моими данными
              </button>
            </div>
          )}
        </>
      )}
    </>
  )
}
