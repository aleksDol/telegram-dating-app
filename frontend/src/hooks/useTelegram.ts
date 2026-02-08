import { useEffect, useState } from 'react'

declare global {
  interface Window {
    Telegram?: {
      WebApp: {
        ready: () => void
        expand: () => void
        close: () => void
        MainButton: {
          show: () => void
          hide: () => void
          setText: (text: string) => void
          onClick: (cb: () => void) => void
          offClick: (cb: () => void) => void
        }
        BackButton: {
          show: () => void
          hide: () => void
          onClick: (cb: () => void) => void
          offClick: (cb: () => void) => void
        }
        initData: string
        initDataUnsafe: {
          user?: {
            id: number
            first_name: string
            last_name?: string
            username?: string
            language_code?: string
          }
        }
        themeParams: Record<string, string>
        colorScheme: 'light' | 'dark'
        /** Открыть ссылку во внешнем браузере / в Telegram, не заменяя текущую страницу */
        openLink: (url: string) => void
        /** Открыть t.me/... в нативном Telegram */
        openTelegramLink: (url: string) => void
      }
    }
  }
}

export function useTelegram() {
  const [tg] = useState(() => window.Telegram?.WebApp)
  const [user] = useState(() => tg?.initDataUnsafe?.user)

  useEffect(() => {
    if (tg) {
      tg.ready()
      tg.expand()
    }
  }, [tg])

  return {
    tg,
    user,
    userId: user?.id,
    initData: tg?.initData ?? '',
    theme: tg?.colorScheme ?? 'light',
    themeParams: tg?.themeParams ?? {},
    mainButton: tg?.MainButton,
    backButton: tg?.BackButton,
    close: () => tg?.close(),
    /** Открыть ссылку (t.me или tg://) через WebApp — не заменяет страницу, нет белого экрана */
    openExternalLink: (url: string) => {
      if (tg?.openTelegramLink && url.startsWith('https://t.me/')) {
        tg.openTelegramLink(url)
      } else if (tg?.openLink) {
        tg.openLink(url)
      } else {
        window.open(url, '_blank', 'noopener,noreferrer')
      }
    },
  }
}
