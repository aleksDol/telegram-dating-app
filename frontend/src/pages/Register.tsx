import { useState, useRef, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { useTelegram } from '../hooks/useTelegram'
import { CITIES, GENDERS, RELATIONSHIP_STATUSES } from '../constants'
import { isApiConfigured, api } from '../api/client'
import type { User } from '../types'

const STEPS = ['name', 'age', 'gender', 'city', 'relationship', 'purpose', 'photo'] as const
const MAX_SUGGESTIONS = 12

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
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [cityNotInList, setCityNotInList] = useState(false)
  const [cityDropdownOpen, setCityDropdownOpen] = useState(false)
  const cityWrapRef = useRef<HTMLDivElement>(null)
  const cityInputRef = useRef<HTMLInputElement>(null)

  const citySuggestions = useMemo(() => {
    const q = city.trim().toLowerCase()
    if (!q) return CITIES.slice(0, MAX_SUGGESTIONS)
    return CITIES.filter((c) => c.toLowerCase().includes(q)).slice(0, MAX_SUGGESTIONS)
  }, [city])

  useEffect(() => {
    if (step !== 'city') return
    const handleClickOutside = (e: MouseEvent) => {
      if (cityWrapRef.current && !cityWrapRef.current.contains(e.target as Node)) {
        setCityDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [step])

  const next = () => setStepIndex((i) => Math.min(i + 1, STEPS.length - 1))

  const handleCityNext = () => {
    const trimmed = city.trim()
    if (!trimmed) return
    if (!CITIES.includes(trimmed)) {
      setCityNotInList(true)
      return
    }
    setCityNotInList(false)
    next()
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
    <div className="register-page">
      {isApiConfigured() ? null : (
        <div className="register-demo-bar">
          <span>Нет бэкенда или не работает?</span>
          <button type="button" className="btn-demo-inline" onClick={enterDemoWithForm}>
            Посмотреть приложение →
          </button>
        </div>
      )}
      <header className="register-hero">
        <h1 className="register-hero-title">Регистрация</h1>
      </header>

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
          <div className="register-option-buttons">
            {GENDERS.map((g) => (
              <button
                key={g}
                type="button"
                className="btn register-btn-option"
                onClick={() => { setGender(g); next() }}
              >
                {g}
              </button>
            ))}
          </div>
        </>
      )}

      {step === 'city' && (
        <>
          <label className="label">Город</label>
          <div className="register-city-wrap" ref={cityWrapRef}>
            <input
              ref={cityInputRef}
              className="input register-city-input"
              type="text"
              value={city}
              onChange={(e) => {
                setCity(e.target.value)
                setCityNotInList(false)
                setCityDropdownOpen(true)
              }}
              onFocus={() => setCityDropdownOpen(true)}
              placeholder="Начните вводить город"
              autoComplete="off"
              aria-autocomplete="list"
              aria-expanded={cityDropdownOpen && citySuggestions.length > 0}
            />
            {cityDropdownOpen && citySuggestions.length > 0 && (
              <ul
                className="register-city-dropdown"
                role="listbox"
                aria-hidden={false}
              >
                {citySuggestions.map((c) => (
                  <li
                    key={c}
                    role="option"
                    className="register-city-option"
                    onClick={() => {
                      setCity(c)
                      setCityNotInList(false)
                      setCityDropdownOpen(false)
                      cityInputRef.current?.blur()
                    }}
                  >
                    {c}
                  </li>
                ))}
              </ul>
            )}
          </div>
          {cityNotInList && (
            <p className="register-city-error" role="alert">
              К сожалению, данного города нет в списке. Выберите город из вариантов ниже.
            </p>
          )}
          {city && !CITIES.includes(city.trim()) && !cityNotInList && (
            <p className="text-muted" style={{ marginBottom: 8 }}>
              Выберите город из списка ниже или введите другой
            </p>
          )}
          <button
            className="btn btn-primary"
            onClick={handleCityNext}
            disabled={!city.trim()}
          >
            Далее
          </button>
        </>
      )}

      {step === 'relationship' && (
        <>
          <label className="label">Статус отношений</label>
          <div className="register-option-buttons">
            {RELATIONSHIP_STATUSES.map((s) => (
              <button
                key={s}
                type="button"
                className="btn register-btn-option"
                onClick={() => { setRelationship(s); next() }}
              >
                {s}
              </button>
            ))}
          </div>
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
          <p className="text-muted register-photo-hint">
            Загрузите своё фото. Без фото регистрация невозможна.
          </p>
          <label className="register-photo-picker">
            <input
              type="file"
              accept="image/*"
              capture="user"
              className="register-photo-input"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) {
                  const reader = new FileReader()
                  reader.onload = () => {
                    const dataUrl = reader.result as string
                    setPhoto(dataUrl)
                  }
                  reader.readAsDataURL(file)
                }
              }}
            />
            {photo ? (
              <span className="register-photo-preview-wrap">
                <img
                  src={photo}
                  alt="Ваше фото"
                  className="register-photo-preview"
                  onError={() => setPhoto('')}
                />
                <span className="register-photo-change">Изменить фото</span>
              </span>
            ) : (
              <span className="register-photo-placeholder">
                <span className="register-photo-icon" aria-hidden>📷</span>
                <span className="register-photo-text">Выбрать фото</span>
                <span className="register-photo-sub">С телефона откроется камера</span>
              </span>
            )}
          </label>
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
                  Откройте приложение из Telegram (кнопка «Открыть» в боте). Если открываете из бота и ошибка остаётся — на бэкенде (VPS: в .env) переменная BOT_TOKEN должна быть от того же бота, в настройках которого указан URL Mini App. Для локальной проверки без Telegram: ALLOW_DEV_USER_ID=1 на бэкенде и при необходимости VITE_DEV_USER_ID на фронте.
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
    </div>
  )
}
