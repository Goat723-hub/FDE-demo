import { useEffect, useState } from 'react'

export const fmt = (n) =>
  new Intl.NumberFormat('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(n || 0))

export const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

export function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = reject
    reader.readAsDataURL(blob)
  })
}

/** 数字滚动：总价从 0 提到目标值 */
export function useCountUp(target, duration = 900) {
  const [value, setValue] = useState(0)

  useEffect(() => {
    const end = Number(target || 0)
    if (!end) {
      setValue(0)
      return
    }
    let frame
    let start
    const tick = (ts) => {
      if (!start) start = ts
      const progress = Math.min(1, (ts - start) / duration)
      const eased = 1 - Math.pow(1 - progress, 3)
      setValue(end * eased)
      if (progress < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [target, duration])

  return value
}

/** 摘要逐字出现 */
export function useTypewriter(text, speed = 24) {
  const [out, setOut] = useState('')

  useEffect(() => {
    setOut('')
    if (!text) return
    let index = 0
    const timer = setInterval(() => {
      index += 2
      setOut(text.slice(0, index))
      if (index >= text.length) clearInterval(timer)
    }, speed)
    return () => clearInterval(timer)
  }, [text, speed])

  return out
}
