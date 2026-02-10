import { useState, useRef, useCallback, useEffect } from 'react'
import { getCroppedImageDataUrl } from '../utils/imageCrop'

export interface ImageCropperProps {
  imageSrc: string
  onCrop: (dataUrl: string) => void
  onCancel: () => void
  outputSize?: number
  /** Встроенное кадрирование в форме */
  inline?: boolean
}

const VIEWPORT_SIZE = 300
const MIN_ZOOM = 0.5
const MAX_ZOOM = 4

/**
 * Фиксированный квадрат кадрирования. Пользователь двигает и масштабирует фото внутри квадрата.
 */
export default function ImageCropper({
  imageSrc,
  onCrop,
  onCancel,
  outputSize = 800,
  inline = false,
}: ImageCropperProps) {
  const [loaded, setLoaded] = useState(false)
  const [imgSize, setImgSize] = useState({ w: 0, h: 0 })
  const [viewportSize, setViewportSize] = useState(VIEWPORT_SIZE)
  const [scale, setScale] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const dragStart = useRef({ clientX: 0, clientY: 0, panX: 0, panY: 0 })
  const viewportRef = useRef<HTMLDivElement>(null)
  const scrollLockRef = useRef<{
    active: boolean
    scrollY: number
    prevOverflow: string
    prevTouchAction: string
    prevPosition: string
    prevTop: string
    prevLeft: string
    prevRight: string
    prevWidth: string
    prevOverscrollBody: string
    prevOverscrollHtml: string
  }>({
    active: false,
    scrollY: 0,
    prevOverflow: '',
    prevTouchAction: '',
    prevPosition: '',
    prevTop: '',
    prevLeft: '',
    prevRight: '',
    prevWidth: '',
    prevOverscrollBody: '',
    prevOverscrollHtml: '',
  })
  const panX = pan.x
  const panY = pan.y

  // Блокировка прокрутки страницы только в полноэкранном режиме
  useEffect(() => {
    if (inline) return
    const prevOverflow = document.body.style.overflow
    const prevTouchAction = document.body.style.touchAction
    document.body.style.overflow = 'hidden'
    document.body.style.touchAction = 'none'
    return () => {
      document.body.style.overflow = prevOverflow
      document.body.style.touchAction = prevTouchAction
    }
  }, [inline])

  const lockBodyScroll = useCallback(() => {
    const st = scrollLockRef.current
    if (st.active) return
    const scrollY = window.scrollY || document.documentElement.scrollTop || 0
    const html = document.documentElement
    scrollLockRef.current = {
      active: true,
      scrollY,
      prevOverflow: document.body.style.overflow,
      prevTouchAction: document.body.style.touchAction,
      prevPosition: document.body.style.position,
      prevTop: document.body.style.top,
      prevLeft: document.body.style.left,
      prevRight: document.body.style.right,
      prevWidth: document.body.style.width,
      prevOverscrollBody: document.body.style.overscrollBehavior,
      prevOverscrollHtml: html.style.overscrollBehavior,
    }
    // На iOS overflow:hidden может не блокировать скролл — фиксируем body
    document.body.style.overflow = 'hidden'
    document.body.style.touchAction = 'none'
    document.body.style.position = 'fixed'
    document.body.style.top = `-${scrollY}px`
    document.body.style.left = '0'
    document.body.style.right = '0'
    document.body.style.width = '100%'
    // Убираем «резинку» при тяге вниз/вверх
    document.body.style.overscrollBehavior = 'none'
    html.style.overscrollBehavior = 'none'
  }, [])

  const unlockBodyScroll = useCallback(() => {
    const st = scrollLockRef.current
    if (!st.active) return
    document.body.style.overflow = st.prevOverflow
    document.body.style.touchAction = st.prevTouchAction
    document.body.style.position = st.prevPosition
    document.body.style.top = st.prevTop
    document.body.style.left = st.prevLeft
    document.body.style.right = st.prevRight
    document.body.style.width = st.prevWidth
    document.body.style.overscrollBehavior = st.prevOverscrollBody
    document.documentElement.style.overscrollBehavior = st.prevOverscrollHtml
    scrollLockRef.current.active = false
    window.scrollTo(0, st.scrollY)
  }, [])

  // На всякий случай снимаем блокировку при размонтировании
  useEffect(() => {
    return () => unlockBodyScroll()
  }, [unlockBodyScroll])

  // Тач: блокируем скролл на viewport нативным touchmove с passive: false, иначе preventDefault не сработает
  useEffect(() => {
    const el = viewportRef.current
    if (!el || !inline) return
    const onTouchStart = () => lockBodyScroll()
    const onTouchMove = (e: TouchEvent) => e.preventDefault()
    const onTouchEnd = () => unlockBodyScroll()
    el.addEventListener('touchstart', onTouchStart, { passive: true })
    el.addEventListener('touchmove', onTouchMove, { passive: false })
    el.addEventListener('touchend', onTouchEnd, { passive: true })
    el.addEventListener('touchcancel', onTouchEnd, { passive: true })
    return () => {
      el.removeEventListener('touchstart', onTouchStart)
      el.removeEventListener('touchmove', onTouchMove)
      el.removeEventListener('touchend', onTouchEnd)
      el.removeEventListener('touchcancel', onTouchEnd)
    }
  }, [inline, lockBodyScroll, unlockBodyScroll])

  useEffect(() => {
    const img = new Image()
    img.onload = () => {
      setImgSize({ w: img.naturalWidth, h: img.naturalHeight })
      setLoaded(true)
    }
    img.onerror = () => setLoaded(false)
    img.src = imageSrc
  }, [imageSrc])

  useEffect(() => {
    const el = viewportRef.current
    if (!el) return
    const updateSize = () => {
      const w = el.clientWidth || 0
      const h = el.clientHeight || 0
      const size = Math.max(280, Math.min(w || VIEWPORT_SIZE, h || VIEWPORT_SIZE, VIEWPORT_SIZE))
      setViewportSize(size)
    }
    const ro = new ResizeObserver(updateSize)
    ro.observe(el)
    updateSize()
    return () => ro.disconnect()
  }, [loaded])

  // Начальный масштаб: фото заполняет квадрат. Начальная позиция по центру.
  useEffect(() => {
    if (!loaded || !imgSize.w || !imgSize.h || !viewportSize) return
    const Smin = viewportSize / Math.min(imgSize.w, imgSize.h)
    setScale(Smin)
    setPan({ x: 0, y: 0 })
  }, [loaded, imgSize.w, imgSize.h, viewportSize])

  const Smin = imgSize.w && imgSize.h && viewportSize
    ? viewportSize / Math.min(imgSize.w, imgSize.h)
    : 1
  const SminClamp = Math.max(Smin * MIN_ZOOM, 0.1)
  const Smax = Math.max(Smin * MAX_ZOOM, Smin + 0.5)

  const clampPan = useCallback(
    (s: number, px: number, py: number) => {
      const imgW = imgSize.w * s
      const imgH = imgSize.h * s
      const maxPanX = Math.max(0, (imgW - viewportSize) / 2)
      const maxPanY = Math.max(0, (imgH - viewportSize) / 2)
      return {
        panX: Math.max(-maxPanX, Math.min(maxPanX, px)),
        panY: Math.max(-maxPanY, Math.min(maxPanY, py)),
      }
    },
    [viewportSize, imgSize.w, imgSize.h]
  )

  const handlePointerDown = useCallback(
    (e: React.PointerEvent) => {
      e.preventDefault()
      e.stopPropagation()
      if (inline) lockBodyScroll()
      setIsDragging(true)
      dragStart.current = { clientX: e.clientX, clientY: e.clientY, panX, panY }
      // Захват указателя — все pointermove идут в viewport, браузер не начинает скролл/overscroll
      const el = e.currentTarget as HTMLElement
      if (el.setPointerCapture) el.setPointerCapture(e.pointerId)
    },
    [panX, panY, inline, lockBodyScroll]
  )

  const handlePointerMove = useCallback(
    (e: PointerEvent) => {
      if (!isDragging) return
      const dx = e.clientX - dragStart.current.clientX
      const dy = e.clientY - dragStart.current.clientY
      const { panX: panX0, panY: panY0 } = dragStart.current
      const { panX: px, panY: py } = clampPan(scale, panX0 + dx, panY0 + dy)
      setPan({ x: px, y: py })
    },
    [isDragging, scale, clampPan]
  )

  const handlePointerUp = useCallback(
    (e?: PointerEvent) => {
      if (viewportRef.current && e && viewportRef.current.releasePointerCapture) {
        try {
          viewportRef.current.releasePointerCapture(e.pointerId)
        } catch (_) {}
      }
      setIsDragging(false)
      if (inline) unlockBodyScroll()
    },
    [inline, unlockBodyScroll]
  )

  useEffect(() => {
    if (!isDragging) return
    const onPointerUp = (e: PointerEvent) => handlePointerUp(e)
    const onPointerMove = (e: PointerEvent) => {
      e.preventDefault()
      handlePointerMove(e)
    }
    window.addEventListener('pointermove', onPointerMove, { passive: false })
    window.addEventListener('pointerup', onPointerUp)
    window.addEventListener('pointercancel', onPointerUp)
    return () => {
      window.removeEventListener('pointermove', onPointerMove)
      window.removeEventListener('pointerup', onPointerUp)
      window.removeEventListener('pointercancel', onPointerUp)
    }
  }, [isDragging, handlePointerMove, handlePointerUp])

  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      e.preventDefault()
      const delta = e.deltaY > 0 ? -0.1 : 0.1
      setScale((s) => Math.max(SminClamp, Math.min(Smax, s * (1 + delta))))
    },
    [SminClamp, Smax]
  )

  // При изменении scale ограничиваем pan, чтобы не было пустых краёв
  useEffect(() => {
    setPan((prev) => {
      const c = clampPan(scale, prev.x, prev.y)
      return { x: c.panX, y: c.panY }
    })
  }, [scale, clampPan])

  const zoomIn = useCallback(() => {
    setScale((s) => Math.min(Smax, s * 1.2))
  }, [Smax])

  const zoomOut = useCallback(() => {
    setScale((s) => Math.max(SminClamp, s / 1.2))
  }, [SminClamp])

  const handleCrop = useCallback(() => {
    if (!loaded || !imgSize.w || !imgSize.h || !viewportSize) return
    const cropSizePx = viewportSize / scale
    const cropX = imgSize.w / 2 - viewportSize / (2 * scale) - panX / scale
    const cropY = imgSize.h / 2 - viewportSize / (2 * scale) - panY / scale
    const x = Math.max(0, Math.min(imgSize.w - cropSizePx, cropX))
    const y = Math.max(0, Math.min(imgSize.h - cropSizePx, cropY))
    const size = Math.min(cropSizePx, imgSize.w - x, imgSize.h - y)
    if (size <= 0) return
    getCroppedImageDataUrl(imageSrc, { x, y, size }, outputSize)
      .then(onCrop)
      .catch(() => {})
  }, [imageSrc, loaded, imgSize, viewportSize, scale, panX, panY, outputSize, onCrop])

  const stopScroll = useCallback((e: React.PointerEvent | React.TouchEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])

  if (!loaded && imgSize.w === 0) {
    return (
      <div className={`image-cropper-overlay ${inline ? 'image-cropper-inline' : ''}`} role="dialog" aria-label="Кадрирование">
        <div className="image-cropper-loading">Загрузка…</div>
        <button type="button" className="btn btn-ghost image-cropper-cancel" onClick={onCancel}>
          Отмена
        </button>
      </div>
    )
  }

  const imgW = imgSize.w * scale
  const imgH = imgSize.h * scale
  const left = viewportSize / 2 - imgW / 2 + panX
  const top = viewportSize / 2 - imgH / 2 + panY

  return (
    <div
      className={`image-cropper-overlay ${inline ? 'image-cropper-inline' : ''}`}
      role="dialog"
      aria-modal={!inline}
      aria-label="Кадрирование фото"
      onPointerDown={inline ? undefined : stopScroll}
      onTouchStart={inline ? undefined : stopScroll}
      onTouchMove={inline ? undefined : stopScroll}
    >
      <div className="image-cropper-header">
        <span className="image-cropper-title">Кадрирование</span>
        <button type="button" className="image-cropper-close" onClick={onCancel} aria-label="Закрыть">
          ✕
        </button>
      </div>
      <div
        ref={viewportRef}
        className="image-cropper-viewport image-cropper-viewport-fixed"
        style={{
          width: '100%',
          maxWidth: VIEWPORT_SIZE,
          aspectRatio: '1',
          height: 'auto',
        }}
        onPointerDown={handlePointerDown}
        onTouchStart={stopScroll}
        onTouchMove={stopScroll}
        onWheel={handleWheel}
      >
        <div
          className="image-cropper-image-wrap"
          style={{
            width: imgW,
            height: imgH,
            left,
            top,
          }}
        >
          <img
            src={imageSrc}
            alt=""
            draggable={false}
            className="image-cropper-image"
            style={{ width: imgW, height: imgH }}
          />
        </div>
      </div>
      <div className="image-cropper-zoom-row">
        <button type="button" className="btn btn-ghost image-cropper-zoom-btn" onClick={zoomOut} aria-label="Уменьшить">
          −
        </button>
        <span className="image-cropper-hint">Двигайте фото и масштабируйте</span>
        <button type="button" className="btn btn-ghost image-cropper-zoom-btn" onClick={zoomIn} aria-label="Увеличить">
          +
        </button>
      </div>
      <div className="image-cropper-actions">
        <button type="button" className="btn btn-ghost" onClick={onCancel}>
          Отмена
        </button>
        <button type="button" className="btn btn-primary" onClick={handleCrop}>
          Готово
        </button>
      </div>
    </div>
  )
}
