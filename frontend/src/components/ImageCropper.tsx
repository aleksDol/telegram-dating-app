import { useState, useRef, useCallback, useEffect } from 'react'
import { getCroppedImageDataUrl } from '../utils/imageCrop'

export interface ImageCropperProps {
  imageSrc: string
  onCrop: (dataUrl: string) => void
  onCancel: () => void
  outputSize?: number
  /** Встроенное кадрирование в форме (фото сразу в интерфейсе, без полноэкранного оверлея) */
  inline?: boolean
}

const CONTAINER_MIN = 280
const MIN_CROP_SIZE = 80

type DragMode = 'move' | 'nw' | 'ne' | 'sw' | 'se' | null

/**
 * Кадрирование как в Telegram: фото целиком, рамку можно двигать и менять размер (углы).
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
  const [containerSize, setContainerSize] = useState({ w: CONTAINER_MIN, h: 360 })
  const [cropBox, setCropBox] = useState({ x: 0, y: 0, size: 200 })
  const [dragMode, setDragMode] = useState<DragMode>(null)
  const dragStartRef = useRef({ clientX: 0, clientY: 0, x: 0, y: 0, size: 0 })
  const containerRef = useRef<HTMLDivElement>(null)

  const scale =
    imgSize.w && imgSize.h
      ? Math.min(containerSize.w / imgSize.w, containerSize.h / imgSize.h)
      : 1
  const imgDisplayW = imgSize.w * scale
  const imgDisplayH = imgSize.h * scale
  const imgLeft = (containerSize.w - imgDisplayW) / 2
  const imgTop = (containerSize.h - imgDisplayH) / 2

  const clampCrop = useCallback(
    (x: number, y: number, size: number) => {
      const maxSize = Math.min(imgDisplayW, imgDisplayH)
      const s = Math.max(MIN_CROP_SIZE, Math.min(maxSize, size))
      const rx = Math.max(imgLeft, Math.min(imgLeft + imgDisplayW - s, x))
      const ry = Math.max(imgTop, Math.min(imgTop + imgDisplayH - s, y))
      return { x: rx, y: ry, size: s }
    },
    [imgLeft, imgTop, imgDisplayW, imgDisplayH]
  )

  useEffect(() => {
    if (inline) return
    const prevOverflow = document.body.style.overflow
    const prevTouchAction = document.body.style.touchAction
    const prevOverscrollBehavior = document.body.style.overscrollBehavior
    document.body.style.overflow = 'hidden'
    document.body.style.touchAction = 'none'
    document.body.style.overscrollBehavior = 'none'
    return () => {
      document.body.style.overflow = prevOverflow
      document.body.style.touchAction = prevTouchAction
      document.body.style.overscrollBehavior = prevOverscrollBehavior
    }
  }, [inline])

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
    const el = containerRef.current
    if (!el) return
    const ro = new ResizeObserver(() => {
      setContainerSize({ w: el.clientWidth || CONTAINER_MIN, h: el.clientHeight || 360 })
    })
    ro.observe(el)
    setContainerSize({ w: el.clientWidth || CONTAINER_MIN, h: el.clientHeight || 360 })
    return () => ro.disconnect()
  }, [loaded])

  useEffect(() => {
    if (!loaded || !imgDisplayW || !imgDisplayH) return
    const maxSize = Math.min(imgDisplayW, imgDisplayH)
    const size = Math.max(MIN_CROP_SIZE, Math.min(maxSize, maxSize * 0.85))
    const x = imgLeft + (imgDisplayW - size) / 2
    const y = imgTop + (imgDisplayH - size) / 2
    setCropBox(clampCrop(x, y, size))
  }, [loaded, imgDisplayW, imgDisplayH, imgLeft, imgTop, clampCrop])

  const handlePointerDown = useCallback(
    (e: React.PointerEvent, mode: DragMode) => {
      e.preventDefault()
      if (mode === null) return
      setDragMode(mode)
      dragStartRef.current = {
        clientX: e.clientX,
        clientY: e.clientY,
        x: cropBox.x,
        y: cropBox.y,
        size: cropBox.size,
      }
    },
    [cropBox]
  )

  const getContainerRect = useCallback(() => {
    return containerRef.current?.getBoundingClientRect() ?? { left: 0, top: 0 }
  }, [])

  useEffect(() => {
    if (dragMode === null) return
    const onUp = () => setDragMode(null)
    const onMove = (e: PointerEvent) => {
      const rect = getContainerRect()
      const relX = e.clientX - rect.left
      const relY = e.clientY - rect.top
      const { clientX, clientY, x, y, size } = dragStartRef.current
      const startRelX = clientX - rect.left
      const startRelY = clientY - rect.top
      const dx = relX - startRelX
      const dy = relY - startRelY

      if (dragMode === 'move') {
        setCropBox((prev) => clampCrop(x + dx, y + dy, prev.size))
        return
      }
      if (dragMode === 'se') {
        const newSize = Math.max(
          MIN_CROP_SIZE,
          Math.min(
            Math.min(relX - x, relY - y),
            imgLeft + imgDisplayW - x,
            imgTop + imgDisplayH - y
          )
        )
        setCropBox(clampCrop(x, y, newSize))
        return
      }
      if (dragMode === 'nw') {
        const newSize = Math.max(
          MIN_CROP_SIZE,
          Math.min(Math.min(x + size - relX, y + size - relY), x - imgLeft + size, y - imgTop + size)
        )
        setCropBox(clampCrop(x + size - newSize, y + size - newSize, newSize))
        return
      }
      if (dragMode === 'ne') {
        const newSize = Math.max(
          MIN_CROP_SIZE,
          Math.min(Math.min(relX - x, (y + size) - relY), x + size - imgLeft, imgTop + imgDisplayH - y)
        )
        setCropBox(clampCrop(x + size - newSize, y, newSize))
        return
      }
      if (dragMode === 'sw') {
        const newSize = Math.max(
          MIN_CROP_SIZE,
          Math.min(Math.min((x + size) - relX, relY - y), imgLeft + imgDisplayW - x, y + size - imgTop)
        )
        setCropBox(clampCrop(x, y + size - newSize, newSize))
      }
    }
    window.addEventListener('pointerup', onUp)
    window.addEventListener('pointermove', onMove)
    return () => {
      window.removeEventListener('pointerup', onUp)
      window.removeEventListener('pointermove', onMove)
    }
  }, [dragMode, clampCrop, imgLeft, imgTop, imgDisplayW, imgDisplayH, getContainerRect])

  const handlePointerUp = useCallback(() => setDragMode(null), [])

  const handleCrop = useCallback(() => {
    if (!loaded || !imgSize.w || !imgSize.h) return
    const sx = (cropBox.x - imgLeft) / scale
    const sy = (cropBox.y - imgTop) / scale
    const size = cropBox.size / scale
    getCroppedImageDataUrl(imageSrc, { x: sx, y: sy, size }, outputSize)
      .then(onCrop)
      .catch(() => {})
  }, [imageSrc, loaded, imgSize.w, imgSize.h, cropBox, imgLeft, imgTop, scale, outputSize, onCrop])

  const stopScroll = useCallback((e: React.PointerEvent | React.TouchEvent) => {
    e.preventDefault()
  }, [])

  if (!loaded && imgSize.w === 0) {
    return (
      <div className="image-cropper-overlay" role="dialog" aria-modal="true" aria-label="Кадрирование">
        <div className="image-cropper-loading">Загрузка…</div>
        <button type="button" className="btn btn-ghost image-cropper-cancel" onClick={onCancel}>
          Отмена
        </button>
      </div>
    )
  }

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
        ref={containerRef}
        className="image-cropper-viewport image-cropper-viewport-contain"
        style={{ minHeight: 320 }}
        onPointerUp={handlePointerUp}
        onPointerLeave={handlePointerUp}
      >
        <img
          src={imageSrc}
          alt=""
          draggable={false}
          className="image-cropper-image image-cropper-image-contain"
        />
        <div
          className="image-cropper-frame"
          style={{
            left: cropBox.x,
            top: cropBox.y,
            width: cropBox.size,
            height: cropBox.size,
          }}
          onPointerDown={(e) => handlePointerDown(e, 'move')}
          aria-hidden
        >
          <span
            className="image-cropper-handle image-cropper-handle-nw"
            onPointerDown={(e) => {
              e.stopPropagation()
              handlePointerDown(e, 'nw')
            }}
          />
          <span
            className="image-cropper-handle image-cropper-handle-ne"
            onPointerDown={(e) => {
              e.stopPropagation()
              handlePointerDown(e, 'ne')
            }}
          />
          <span
            className="image-cropper-handle image-cropper-handle-sw"
            onPointerDown={(e) => {
              e.stopPropagation()
              handlePointerDown(e, 'sw')
            }}
          />
          <span
            className="image-cropper-handle image-cropper-handle-se"
            onPointerDown={(e) => {
              e.stopPropagation()
              handlePointerDown(e, 'se')
            }}
          />
        </div>
      </div>
      <p className="image-cropper-hint">Сдвиньте рамку или потяните за углы</p>
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
