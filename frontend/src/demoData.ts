/**
 * Демо-данные для просмотра интерфейса без бэкенда.
 * События и «организаторы» (имя, возраст, город) для списков и карточек.
 */

import type { Event } from './types'
import { DEMO_USER_ID } from './context/AppContext'

const now = new Date()
const in1d = new Date(now.getTime() + 86400000)
const in2d = new Date(now.getTime() + 2 * 86400000)
const in3d = new Date(now.getTime() + 3 * 86400000)
const in5d = new Date(now.getTime() + 5 * 86400000)
const in7d = new Date(now.getTime() + 7 * 86400000)

const fmt = (d: Date) => d.toISOString().slice(0, 19)

/** Все демо-события (чужие + «мои» для демо-пользователя) */
export const MOCK_EVENTS_ALL: Event[] = [
  {
    id: 1,
    user_id: 101,
    title: 'Кофе в центре',
    description: 'Ищу компанию на чашку кофе в субботу. Люблю латте и спокойные разговоры. Можем обсудить что угодно — книги, путешествия, планы на выходные.',
    event_date: fmt(in1d),
    target_gender: 'Все',
    city: 'Москва',
    category: '🍽️ Рестораны и бары',
    name: 'Анна',
    age: 28,
    gender: 'Женский',
    purpose: 'куда-то сходить',
    relationship_status: 'Не в отношениях',
    likes_count: 12,
  },
  {
    id: 2,
    user_id: 102,
    title: 'Кино: премьера',
    description: 'Хочу сходить на новый фильм в пятницу вечером. Кинотеатр у метро. После — можно обсудить за соком или кофе.',
    event_date: fmt(in2d),
    target_gender: 'Все',
    city: 'Москва',
    category: '🎬 Кино и театр',
    name: 'Максим',
    age: 30,
    gender: 'Мужской',
    purpose: 'куда-то сходить',
    relationship_status: 'Не в отношениях',
    likes_count: 8,
  },
  {
    id: 3,
    user_id: 103,
    title: 'Прогулка по парку',
    description: 'Субботнее утро — парк Горького, спокойная прогулка, возможно завтрак на веранде. Кто со мной?',
    event_date: fmt(in2d),
    target_gender: 'Все',
    city: 'Москва',
    category: '🌳 Природа',
    name: 'Дарья',
    age: 26,
    gender: 'Женский',
    purpose: 'куда-то сходить',
    relationship_status: 'Не в отношениях',
    likes_count: 15,
  },
  {
    id: 4,
    user_id: 104,
    title: 'Настолки в антикафе',
    description: 'Играем в настольные игры в антикафе в воскресенье. Опыт не нужен — научим. Компания на 4–6 человек.',
    event_date: fmt(in3d),
    target_gender: 'Все',
    city: 'Москва',
    category: '🎮 Развлечения',
    name: 'Илья',
    age: 24,
    gender: 'Мужской',
    purpose: 'куда-то сходить',
    relationship_status: 'Не в отношениях',
    likes_count: 6,
  },
  {
    id: 5,
    user_id: 105,
    title: 'Выставка современного искусства',
    description: 'Еду в галерею на выставку. Хочу обсудить впечатления с кем-то после — за чаем или кофе рядом.',
    event_date: fmt(in5d),
    target_gender: 'Все',
    city: 'Москва',
    category: '🎨 Искусство и культура',
    name: 'София',
    age: 29,
    gender: 'Женский',
    purpose: 'куда-то сходить',
    relationship_status: 'Не в отношениях',
    likes_count: 9,
  },
  {
    id: 6,
    user_id: 106,
    title: 'Йога в парке',
    description: 'Утренняя йога в парке в воскресенье. Уровень любой. Потом можно позавтракать вместе.',
    event_date: fmt(in7d),
    target_gender: 'Все',
    city: 'Москва',
    category: '🏃‍♀️ Активный отдых',
    name: 'Артём',
    age: 27,
    gender: 'Мужской',
    purpose: 'куда-то сходить',
    relationship_status: 'Не в отношениях',
    likes_count: 11,
  },
  // «Мои» события для демо-пользователя (user_id === DEMO_USER_ID)
  {
    id: 7,
    user_id: DEMO_USER_ID,
    title: 'Вечер в баре',
    description: 'Хочу провести пятничный вечер в баре с живой музыкой. Ищу компанию — один-два человека. Бар в центре.',
    event_date: fmt(in2d),
    target_gender: 'Все',
    city: 'Москва',
    category: '🍽️ Рестораны и бары',
    name: 'Гость',
    age: 25,
    gender: 'Мужской',
    purpose: 'куда-то сходить',
    relationship_status: 'Не в отношениях',
    likes_count: 3,
  },
  {
    id: 8,
    user_id: DEMO_USER_ID,
    title: 'Квест-комната',
    description: 'Собираю команду на квест в субботу. Рассчитан на 2–4 человека. Уже двое — нужен ещё один или два.',
    event_date: fmt(in3d),
    target_gender: 'Все',
    city: 'Москва',
    category: '🎮 Развлечения',
    name: 'Гость',
    age: 25,
    gender: 'Мужской',
    purpose: 'куда-то сходить',
    relationship_status: 'Не в отношениях',
    likes_count: 5,
  },
]

/** События других пользователей (для страницы «События») */
export function getDemoEventsForFeed(currentUserId: number): Event[] {
  return MOCK_EVENTS_ALL.filter((e) => e.user_id !== currentUserId)
}

/** События текущего пользователя (для страницы «Мои события») */
export function getDemoMyEvents(currentUserId: number): Event[] {
  return MOCK_EVENTS_ALL.filter((e) => e.user_id === currentUserId)
}

/** Одно событие по id (для карточки события) */
export function getDemoEventById(id: string | undefined): Event | null {
  if (!id) return null
  const num = parseInt(id, 10)
  if (Number.isNaN(num)) return null
  return MOCK_EVENTS_ALL.find((e) => e.id === num) ?? null
}

/** Демо: публичный профиль пользователя по user_id (для страницы профиля автора) */
export function getDemoUserByUserId(userId: number): import('./types').User | null {
  const ev = MOCK_EVENTS_ALL.find((e) => e.user_id === userId)
  if (!ev) return null
  return {
    user_id: ev.user_id,
    name: ev.name ?? 'Пользователь',
    age: ev.age ?? 0,
    gender: ev.gender ?? '',
    city: ev.city ?? '',
    relationship_status: ev.relationship_status,
    purpose: ev.purpose ?? 'куда-то сходить',
    points: 0,
    referrals_count: 0,
    photo: ev.photo,
  }
}

/** Демо: ID разблокированных достижений для режима просмотра */
export const MOCK_ACHIEVEMENT_IDS = ['first_event', 'five_likes', 'mutual_match', 'week_streak']
/** Демо: очки рейтинга */
export const MOCK_POINTS = 420
