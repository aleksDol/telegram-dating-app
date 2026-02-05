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
  useTelegram()
  const [stepIndex, setStepIndex] = useState(0)
  const step = STEPS[stepIndex]

  const [name, setName] = useState('')
  const [age, setAge] = useState('')
  const [gender, setGender] = useState('')
  const [city, setCity] = useState('')
  const [relationship, setRelationship] = useState('')
  const [purpose, setPurpose] = useState('куда-то сходить')
  const [photo, setPhoto] = useState('')
  const [photoFile, setPhotoFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const next = () => setStepIndex((i) => Math.min(i + 1, STEPS.length - 1))

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
    if (!name.trim()) {
      setError('Введите имя')
      return
    }
    if (!age || isNaN(ageNum) || ageNum < 18 || ageNum > 100) {
      setError('Укажите возраст от 18 до 100')
      return
    }
    if (!gender) {
      setError('Выберите пол')
      return
    }
    if (!city || !CITIES.includes(city)) {
      setError('Выберите город из списка')
      return
    }
    if (!relationship) {
      setError('Укажите статус отношений')
      return
    }
    if (!photo.trim()) {
      setError('Добавьте фото для регистрации')
      return
    }

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
          photo: photo.trim(),
        })
        setUser(user)
        navigate('/', { replace: true })
      } else {
        enterDemoWithForm()
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Ошибка регистрации'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      {isApiConfigured() ? null : (
        <div className="register-demo-bar">
          <span>Нет бэкенда или не работает?</span>
          <button type="button" className="btn-demo-inline" onClick={enterDemoWithForm}>
            Посмотреть приложение →
          </button>
        </div>
      )}
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
          <label className="label">Фото (обязательно)</label>
          <p className="text-muted" style={{ marginBottom: 8, fontSize: 14 }}>
            Загрузите фото или вставьте ссылку на изображение. Без фото регистрация невозможна.
          </p>
          <input
            className="input"
            type="file"
            accept="image/*"
            capture="user"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) {
                setPhotoFile(file)
                const reader = new FileReader()
                reader.onload = () => {
                  const dataUrl = reader.result as string
                  setPhoto(dataUrl)
                }
                reader.readAsDataURL(file)
              }
            }}
            style={{ marginBottom: 8 }}
          />
          <input
            className="input"
            value={photo.startsWith('data:') ? '' : photo}
            onChange={(e) => {
              setPhotoFile(null)
              setPhoto(e.target.value.trim())
            }}
            placeholder="Или вставьте URL фото"
            style={{ marginBottom: 8 }}
          />
          {photo && (
            <div style={{ marginBottom: 12, textAlign: 'center' }}>
              <img
                src={photo}
                alt="Ваше фото"
                style={{ maxWidth: '100%', maxHeight: 160, objectFit: 'cover', borderRadius: 8 }}
                onError={() => setPhoto('')}
              />
            </div>
          )}
          <button
            className="btn btn-primary btn-lg block-btn"
            onClick={handleRegister}
            disabled={loading || !photo.trim()}
          >
            {loading ? 'Регистрация...' : 'Готово'}
          </button>
          {error && (
            <div className="card card-error" style={{ marginTop: 12 }}>
              <p className="text-error">{error}</p>
              {isApiConfigured() ? (
                <p className="text-muted" style={{ marginTop: 8, fontSize: 14 }}>
                  Откройте приложение из Telegram (кнопка «Открыть» в боте). Если открываете из бота и ошибка остаётся — на бэкенде (Render) в Environment переменная BOT_TOKEN должна быть от того же бота, в настройках которого указан URL Mini App. Для локальной проверки без Telegram: ALLOW_DEV_USER_ID=1 на бэкенде и при необходимости VITE_DEV_USER_ID на фронте.
                </p>
              ) : (
                <button type="button" className="btn btn-ghost" style={{ marginTop: 8 }} onClick={enterDemoWithForm}>
                  Войти в режиме просмотра с моими данными
                </button>
              )}
            </div>
          )}
        </>
      )}
    </>
  )
}
