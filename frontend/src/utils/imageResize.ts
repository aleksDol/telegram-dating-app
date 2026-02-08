/** Максимальная сторона после ресайза (пиксели). */
const MAX_SIDE = 1200
/** Качество JPEG (0–1). Меньше — меньше размер. */
const JPEG_QUALITY = 0.82
/** Порог размера файла (байт): если меньше — ресайз не делаем. */
const SKIP_RESIZE_BELOW_BYTES = 400_000

/**
 * Сжимает изображение для отправки на сервер: уменьшает размер и конвертирует в JPEG.
 * Устраняет ошибку "Request Entity Too Large" при загрузке больших фото с телефона.
 */
export function compressImageForUpload(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    if (!file.type.startsWith('image/')) {
      const r = new FileReader()
      r.onload = () => resolve(r.result as string)
      r.onerror = () => reject(new Error('Не удалось прочитать файл'))
      r.readAsDataURL(file)
      return
    }
    if (file.size <= SKIP_RESIZE_BELOW_BYTES) {
      const r = new FileReader()
      r.onload = () => resolve(r.result as string)
      r.onerror = () => reject(new Error('Не удалось прочитать файл'))
      r.readAsDataURL(file)
      return
    }
    const img = new Image()
    const objectUrl = URL.createObjectURL(file)
    img.src = objectUrl
    img.onerror = () => {
      URL.revokeObjectURL(objectUrl)
      reject(new Error('Не удалось загрузить изображение'))
    }
    img.onload = () => {
      URL.revokeObjectURL(objectUrl)
      try {
        let { width, height } = img
        if (width <= MAX_SIDE && height <= MAX_SIDE && file.size <= SKIP_RESIZE_BELOW_BYTES * 2) {
          const r = new FileReader()
          r.onload = () => resolve(r.result as string)
          r.onerror = () => reject(new Error('Не удалось прочитать файл'))
          r.readAsDataURL(file)
          return
        }
        if (width > MAX_SIDE || height > MAX_SIDE) {
          if (width >= height) {
            height = Math.round((height * MAX_SIDE) / width)
            width = MAX_SIDE
          } else {
            width = Math.round((width * MAX_SIDE) / height)
            height = MAX_SIDE
          }
        }
        const canvas = document.createElement('canvas')
        canvas.width = width
        canvas.height = height
        const ctx = canvas.getContext('2d')
        if (!ctx) {
          const r = new FileReader()
          r.onload = () => resolve(r.result as string)
          r.onerror = () => reject(new Error('Не удалось прочитать файл'))
          r.readAsDataURL(file)
          return
        }
        ctx.drawImage(img, 0, 0, width, height)
        const dataUrl = canvas.toDataURL('image/jpeg', JPEG_QUALITY)
        resolve(dataUrl)
      } catch (e) {
        reject(e instanceof Error ? e : new Error('Ошибка сжатия'))
      }
    }
  })
}
