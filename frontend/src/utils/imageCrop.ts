/**
 * Возвращает data URL обрезанного квадратного фрагмента изображения.
 * @param imageSrc — data URL или URL изображения
 * @param crop — область в координатах исходного изображения (пиксели): x, y, size (квадрат)
 * @param outputSize — размер стороны выходного квадрата в пикселях (качество)
 */
export function getCroppedImageDataUrl(
  imageSrc: string,
  crop: { x: number; y: number; size: number },
  outputSize: number = 800
): Promise<string> {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onerror = () => reject(new Error('Не удалось загрузить изображение'))
    img.onload = () => {
      try {
        const { x, y, size } = crop
        const canvas = document.createElement('canvas')
        canvas.width = outputSize
        canvas.height = outputSize
        const ctx = canvas.getContext('2d')
        if (!ctx) {
          reject(new Error('Canvas не поддерживается'))
          return
        }
        ctx.drawImage(img, x, y, size, size, 0, 0, outputSize, outputSize)
        resolve(canvas.toDataURL('image/jpeg', 0.9))
      } catch (e) {
        reject(e instanceof Error ? e : new Error('Ошибка кадрирования'))
      }
    }
    img.src = imageSrc
  })
}
