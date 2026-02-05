/**
 * API client for MiniApp backend.
 * Set VITE_API_URL in .env (e.g. https://your-api.com) when backend REST API is ready.
 */

const API_BASE = import.meta.env.VITE_API_URL || ''

function getInitData(): string {
  const tg = (window as unknown as { Telegram?: { WebApp?: { initData: string } } }).Telegram
  return tg?.WebApp?.initData || ''
}

/** Для проверки на localhost без Telegram: передаём dev user id в заголовке */
function getDevUserId(): string | null {
  if (getInitData()) return null
  const dev = import.meta.env.VITE_DEV_USER_ID
  if (typeof dev === 'string' && dev) return dev
  const isLocalhost = typeof window !== 'undefined' && /^localhost$|^127\.0\.0\.1$/.test(window.location.hostname)
  if (isLocalhost && API_BASE) return '1'
  return null
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${path}`
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }
  const initData = getInitData()
  if (initData) {
    (headers as Record<string, string>)['X-Telegram-Init-Data'] = initData
  } else {
    const devUserId = getDevUserId()
    if (devUserId) {
      (headers as Record<string, string>)['X-Dev-User-Id'] = devUserId
    }
  }
  const res = await fetch(url, { ...options, headers })
  if (!res.ok) {
    const err = await res.json().catch(() => ({})) as { detail?: string | { msg?: string }[] }
    const detail = err.detail
    let message = res.statusText
    if (typeof detail === 'string') {
      message = detail
    } else if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0]
      message = typeof first?.msg === 'string' ? first.msg : res.statusText
    }
    throw new Error(message)
  }
  return res.json() as Promise<T>
}

export const api = {
  getUser: () => request<{ user: import('../types').User | null }>('/api/user'),
  getUserProfile: (userId: number) =>
    request<{ user: import('../types').User }>(`/api/users/${userId}`),
  register: (data: {
    name: string
    age: number
    gender: string
    city: string
    relationship_status: string
    photo?: string
    purpose?: string
    referred_by?: number
  }) => request<{ user: import('../types').User }>('/api/register', { method: 'POST', body: JSON.stringify(data) }),
  updateProfile: (data: Partial<import('../types').User>) =>
    request<{ user: import('../types').User }>('/api/profile', { method: 'PUT', body: JSON.stringify(data) }),

  getEvents: (filter?: string, limit = 10) =>
    request<{ events: import('../types').Event[] }>(`/api/events?filter=${filter || 'new'}&limit=${limit}`),
  getEvent: (id: number) => request<{ event: import('../types').Event }>(`/api/events/${id}`),
  createEvent: (data: {
    title: string
    description: string
    event_date: string
    target_gender: string
    city: string
    category?: string
  }) => request<{ event: import('../types').Event }>('/api/events', { method: 'POST', body: JSON.stringify(data) }),
  updateEvent: (id: number, data: Partial<import('../types').Event>) =>
    request<{ event: import('../types').Event }>(`/api/events/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteEvent: (id: number) => request<{ ok: boolean }>(`/api/events/${id}`, { method: 'DELETE' }),
  getMyEvents: () => request<{ events: import('../types').Event[] }>('/api/events/mine'),

  likeEvent: (eventId: number) =>
    request<{ like_id?: number; mutual?: boolean }>(`/api/events/${eventId}/like`, { method: 'POST' }),
  skipEvent: (eventId: number) => request<{ ok: boolean }>(`/api/events/${eventId}/skip`, { method: 'POST' }),

  getAchievements: () => request<{ achievements: import('../types').Achievement[]; points: number }>('/api/achievements'),
  getReferral: () => request<{ referral_code: string; referrals_count: number }>('/api/referral'),
}

/** Check if backend API is configured */
export function isApiConfigured(): boolean {
  return Boolean(API_BASE)
}
