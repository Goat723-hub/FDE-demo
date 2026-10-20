import { useCallback, useEffect, useRef, useState } from 'react'
import Hero from './components/Hero'
import Workspace from './components/Workspace'
import Result from './components/Result'
import StepRail from './components/StepRail'
import { blobToDataUrl, sleep } from './lib'

const NUMERIC_FIELDS = ['weight_kg', 'quantity', 'delivery_days']

const STEP_INDEX = { idle: 0, scanning: 1, review: 2, quoting: 2, done: 3 }

function normalizeItems(items) {
  return items.map((item) => ({
    part_name: item.part_name ?? '',
    material: item.material ?? '',
    weight_kg: Number(item.weight_kg) || 0,
    quantity: Number(item.quantity) || 0,
    unit: item.unit ?? '件',
    process: item.process ?? '',
    delivery_days: Number(item.delivery_days) || 0,
  }))
}

async function postJson(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    let detail = `请求失败（${res.status}）`
    try {
      const data = await res.json()
      if (data.detail) detail = data.detail
    } catch {
      /* 非 JSON 错误体，保留默认提示 */
    }
    throw new Error(detail)
  }
  return res.json()
}

export default function App() {
  const [step, setStep] = useState('idle')
  const [mode, setMode] = useState(null)
  const [extraction, setExtraction] = useState(null)
  const [items, setItems] = useState([])
  const [visibleItems, setVisibleItems] = useState(0)
  const [quote, setQuote] = useState(null)
  const [summary, setSummary] = useState('')
  const [error, setError] = useState('')
  const timers = useRef([])

  useEffect(() => {
    fetch('/api/health')
      .then((res) => res.json())
      .then((data) => setMode(data))
      .catch(() => setMode(null))
  }, [])

  useEffect(
    () => () => {
      timers.current.forEach(clearTimeout)
    },
    [],
  )

  const reset = useCallback(() => {
    timers.current.forEach(clearTimeout)
    timers.current = []
    setStep('idle')
    setExtraction(null)
    setItems([])
    setVisibleItems(0)
    setQuote(null)
    setSummary('')
    setError('')
  }, [])

  const start = useCallback(async () => {
    setError('')
    setStep('scanning')

    try {
      const imageBlob = await (await fetch('/static/inquiry.png')).blob()
      const imageBase64 = await blobToDataUrl(imageBlob)

      const [data] = await Promise.all([
        postJson('/api/extract', { image_base64: imageBase64 }),
        sleep(1500),
      ])

      const nextItems = normalizeItems(data.items || [])
      setExtraction(data)
      setItems(nextItems)
      setVisibleItems(0)
      setStep('review')

      nextItems.forEach((_, index) => {
        const timer = setTimeout(() => setVisibleItems(index + 1), 260 * (index + 1))
        timers.current.push(timer)
      })
    } catch (err) {
      setError(err.message)
      setStep('idle')
    }
  }, [])

  const update = useCallback((index, key, raw) => {
    setItems((prev) =>
      prev.map((item, i) => {
        if (i !== index) return item
        const value = NUMERIC_FIELDS.includes(key) ? Number(raw) : raw
        return { ...item, [key]: Number.isNaN(value) ? 0 : value }
      }),
    )
  }, [])

  const confirm = useCallback(async () => {
    setError('')
    setStep('quoting')

    try {
      const [result] = await Promise.all([
        postJson('/api/quote', { order: extraction.order, items }),
        sleep(600),
      ])
      setQuote(result)

      const { summary: text } = await postJson('/api/summary', { facts: result.facts })
      setSummary(text)
      setStep('done')
    } catch (err) {
      setError(err.message)
      setStep('review')
    }
  }, [extraction, items])

  const download = useCallback(async () => {
    try {
      const res = await fetch('/api/pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order: extraction.order, items }),
      })
      if (!res.ok) throw new Error('PDF 生成失败')

      const url = URL.createObjectURL(await res.blob())
      const link = document.createElement('a')
      link.href = url
      link.download = `报价单_${extraction.order.inquiry_no || 'quotation'}.pdf`
      link.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err.message)
    }
  }, [extraction, items])

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">精工</span>
          <span className="brand-text">
            宁波精工制造有限公司
            <small>QUOTATION WORKBENCH</small>
          </span>
        </div>

        <div className="topbar-right">
          <span className="rule-label">询价 → 报价 · 内部工具</span>
          <span className={`mode-dot ${mode?.mode === 'live' ? 'live' : ''}`}>
            {mode ? (mode.mode === 'live' ? `LIVE · ${mode.model}` : 'DEMO · 固定样例') : 'OFFLINE'}
          </span>
        </div>
      </header>

      <StepRail current={STEP_INDEX[step]} />

      {step === 'idle' && <Hero onStart={start} error={error} />}

      {(step === 'scanning' || step === 'review' || step === 'quoting') && (
        <Workspace
          step={step}
          extraction={extraction}
          items={items}
          visibleItems={step === 'quoting' ? items.length : visibleItems}
          onUpdate={update}
          onConfirm={confirm}
          onReset={reset}
          error={error}
        />
      )}

      {step === 'done' && (
        <Result
          quote={quote}
          summary={summary}
          order={extraction.order}
          onDownload={download}
          onReset={reset}
        />
      )}

      <footer className="footer">
        <span>FDE DEMO 01 · 询价单自动报价</span>
        <span className="footer-note">
          LLM 有建议权 · 人有确认权 · 程序只有执行权
        </span>
      </footer>
    </div>
  )
}
