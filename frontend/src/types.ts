export interface User {
  user_id: number
  username?: string
  name: string
  age: number
  gender: string
  city?: string
  relationship_status?: string
  photo?: string
  photos?: string[]
  purpose: string
  points: number
  reg_date?: string
  last_active?: string
  favorite_categories?: string[]
  referral_code?: string
  referred_by?: number
  referrals_count: number
  is_banned?: boolean
  ban_reason?: string
  banned_date?: string
}

export interface Event {
  id: number
  user_id: number
  title: string
  description: string
  event_date: string
  target_gender: string
  city: string
  category?: string
  created?: string
  is_hidden?: boolean
  name?: string
  age?: number
  gender?: string
  photo?: string
  purpose?: string
  relationship_status?: string
  likes_count?: number
}

export interface Achievement {
  id: string
  name: string
  description: string
  emoji: string
  points: number
  unlocked_date?: string
}

export type FilterType =
  | 'interest'
  | 'popular'
  | 'nearby'
  | 'new'
  | 'today'
  | 'tomorrow'
  | 'for_me'
  | 'random'

/** Лайк, на который ещё не ответили (вкладка «Лайки»). */
export interface PendingLike {
  like_id: number
  liker: (Pick<User, 'user_id' | 'name' | 'age' | 'gender' | 'city' | 'relationship_status' | 'photo' | 'purpose'>) & { username?: string }
  event: Event | null
}

/** Взаимная симпатия (матчинг). */
export interface LikeMatch {
  user_id: number
  user: (Pick<User, 'user_id' | 'name' | 'age' | 'gender' | 'city' | 'relationship_status' | 'photo' | 'purpose'>) & { username?: string }
  event: Event | null
}
