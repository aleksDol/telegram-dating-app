import { useState, useCallback, useRef, useEffect } from 'react'

export interface PhotoViewerProps {
  /** Список URL фото (уже полные, с API_BASE если нужно). */
  photos: string[]
  /** Индекс фото для старта (0 по умолчанию). */
  initialIndex?: number
  onClose: () => void
}

const SWIPE_THRESHOLD = 50

export default function PhotoViewer({ photos, initialIndex = 0, onClose }: PhotoViewerProps) {
  const [index, setIndex] = useState(Math.min(initialIndex, Math.max(0, photos.length - 1)))
  const touchStartX = useRef(0)
  const touchStartY = useRef(0)
  const mouseDown = useRef(false)

  const goPrev = useCallback(() => {
    setIndex((i) => (i <= 0 ? i : i - 1))
  }, [])
  const goNext = useCallback(() => {
    setIndex((i) => (i >= photos.length - 1 ? i : i + 1))
  }, [photos.length])

  const onTouchStart = useCallback((e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX
    touchStartY.current = e.touches[0].clientY
  }, [])
  const onTouchEnd = useCallback(
    (e: React.TouchEvent) => {
      const endX = e.changedTouches[0].clientX
      const endY = e.changedTouches[0].clientY
      const dx = endX - touchStartX.current
      const dy = endY - touchStartY.current
      if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > SWIPE_THRESHOLD) {
        if (dx > 0) goPrev()
        else goNext()
      }
    },
    [goPrev, goNext]
  )

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    mouseDown.current = true
    touchStartX.current = e.clientX
    touchStartY.current = e.clientY
  }, [])
  const onMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!mouseDown.current) return
      const dx = e.clientX - touchStartX.current
      const dy = e.clientY - touchStartY.current
      if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > SWIPE_THRESHOLD) {
        if (dx > 0) goPrev()
        else goNext()
        mouseDown.current = false
        touchStartX.current = e.clientX
        touchStartY.current = e.clientY
      }
    },
    [goPrev, goNext]
  )
  const onMouseUp = useCallback(() => {
    mouseDown.current = false
  }, [])
  const onMouseLeave = useCallback(() => {
    mouseDown.current = false
  }, [])

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowLeft') goPrev()
      if (e.key === 'ArrowRight') goNext()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose, goPrev, goNext])

  if (photos.length === 0) return null

  const currentPhoto = photos[index]

  return (
    <div
      className="photo-viewer-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Просмотр фото"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <button
        type="button"
        className="photo-viewer-close"
        onClick={onClose}
        aria-label="Закрыть"
      >
        ✕
      </button>

      <div
        className="photo-viewer-content"
        onTouchStart={onTouchStart}
        onTouchEnd={onTouchEnd}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseLeave}
        onClick={(e) => e.stopPropagation()}
      >
        {photos.length > 1 && index > 0 && (
          <button
            type="button"
            className="photo-viewer-arrow photo-viewer-arrow-left"
            onClick={goPrev}
            aria-label="Предыдущее фото"
          >
            ‹
          </button>
        )}
        <img src={currentPhoto} alt="" className="photo-viewer-img" draggable={false} />
        {photos.length > 1 && index < photos.length - 1 && (
          <button
            type="button"
            className="photo-viewer-arrow photo-viewer-arrow-right"
            onClick={goNext}
            aria-label="Следующее фото"
          >
            ›
          </button>
        )}
      </div>

      {photos.length > 1 && (
        <div className="photo-viewer-dots">
          {photos.map((_, i) => (
            <button
              key={i}
              type="button"
              className={`photo-viewer-dot ${i === index ? 'active' : ''}`}
              onClick={() => setIndex(i)}
              aria-label={`Фото ${i + 1} из ${photos.length}`}
              aria-current={i === index ? 'true' : undefined}
            />
          ))}
        </div>
      )}
    </div>
  )
}
