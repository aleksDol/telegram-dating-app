import { useState, useRef, useCallback, useEffect } from 'react'
import { getCroppedImageDataUrl } from '../utils/imageCrop'

export interface ImageCropperProps {
  imageSrc: string
  onCrop: (dataUrl: string) => void
  onCancel: () => void
  aspectRatio?: number
  outputSize?: number
}

/**
 * Кадрирование изображения: квадратная область, перетаскивание для выбора кадра.
 * Не меняет формат данных — на выходе data URL, как и без кадрирования.
 */
export default function ImageCropper({
  imageSrc,
  onCrop,
  onCancel,
  aspectRatio = 1,
  outputSize = 800,
}: ImageCropperProps) {
  const [loaded, setLoaded] = useState(false)
  const [imgSize, setImgSize] = useState({ w: 0, h: 0 })
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [dragStart, setDragStart] = useState<{ x: number; y: number } | null>(null)
  const [panStart, setPanStart] = useState({ x: 0, y: 0 })
  const containerRef = useRef<HTMLDivElement>(null)
  const imgRef = useRef<HTMLImageElement>(null)

  const CROP_SIZE = 280
  const scaleRef = useRef(1)

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
    if (!loaded || !imgSize.w || !imgSize.h) return
    const scale = Math.max(CROP_SIZE / imgSize.w, CROP_SIZE / imgSize.h)
    scaleRef.current = scale
    const scaledW = imgSize.w * scale
    const scaledH = imgSize.h * scale
    const maxX = Math.max(0, scaledW - CROP_SIZE)
    const maxY = Math.max(0, scaledH - CROP_SIZE)
    setPan({
      x: Math.max(0, Math.min(maxX, (scaledW - CROP_SIZE) / 2)),
      y: Math.max(0, Math.min(maxY, (scaledH - CROP_SIZE) / 2)),
    })
  }, [loaded, imgSize.w, imgSize.h])

  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    setDragStart({ x: e.clientX, y: e.clientY })
    setPanStart(pan)
  }, [pan])

  const handlePointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (dragStart === null || !loaded) return
      const dx = e.clientX - dragStart.x
      const dy = e.clientY - dragStart.y
      const scale = scaleRef.current
      const scaledW = imgSize.w * scale
      const scaledH = imgSize.h * scale
      const maxX = Math.max(0, scaledW - CROP_SIZE)
      const maxY = Math.max(0, scaledH - CROP_SIZE)
      setPan({
        x: Math.max(0, Math.min(maxX, panStart.x + dx)),
        y: Math.max(0, Math.min(maxY, panStart.y + dy)),
      })
    },
    [dragStart, loaded, imgSize.w, imgSize.h, panStart]
  )

  const handlePointerUp = useCallback(() => setDragStart(null), [])
  const handlePointerLeave = useCallback(() => setDragStart(null), [])

  const handleCrop = useCallback(() => {
    if (!loaded || !imgSize.w || !imgSize.h) return
    const scale = scaleRef.current
    const sx = pan.x / scale
    const sy = pan.y / scale
    const size = CROP_SIZE / scale
    getCroppedImageDataUrl(imageSrc, { x: sx, y: sy, size }, outputSize)
      .then(onCrop)
      .catch(() => {})
  }, [imageSrc, loaded, imgSize.w, imgSize.h, pan, outputSize, onCrop])

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

  const scale = Math.max(CROP_SIZE / imgSize.w, CROP_SIZE / imgSize.h)
  const scaledW = imgSize.w * scale
  const scaledH = imgSize.h * scale

  return (
    <div className="image-cropper-overlay" role="dialog" aria-modal="true" aria-label="Кадрирование фото">
      <div className="image-cropper-header">
        <span className="image-cropper-title">Кадрирование</span>
        <button type="button" className="image-cropper-close" onClick={onCancel} aria-label="Закрыть">
          ✕
        </button>
      </div>
      <div
        ref={containerRef}
        className="image-cropper-viewport"
        style={{ width: CROP_SIZE, height: CROP_SIZE }}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerLeave={handlePointerLeave}
        onPointerCancel={handlePointerUp}
      >
        <div
          className="image-cropper-image-wrap"
          style={{
            width: scaledW,
            height: scaledH,
            left: (CROP_SIZE - scaledW) / 2 - pan.x,
            top: (CROP_SIZE - scaledH) / 2 - pan.y,
          }}
        >
          <img ref={imgRef} src={imageSrc} alt="" draggable={false} className="image-cropper-image" />
        </div>
        <div className="image-cropper-frame" aria-hidden />
      </div>
      <p className="image-cropper-hint">Перетащите фото, чтобы выбрать кадр</p>
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
