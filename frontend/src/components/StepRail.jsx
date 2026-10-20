const STEPS = [
  { no: '01', title: '上传询价单' },
  { no: '02', title: 'AI 识别' },
  { no: '03', title: '人工确认' },
  { no: '04', title: '报价单' },
]

export default function StepRail({ current = 0 }) {
  return (
    <nav className="steps" aria-label="演示流程">
      {STEPS.map((step, index) => (
        <div
          key={step.no}
          className={`step ${index < current ? 'done' : ''} ${
            index === current ? 'current' : ''
          }`}
        >
          <span className="step-no">{step.no}</span>
          <span className="step-title">{step.title}</span>
          {index < STEPS.length - 1 && <span className="step-line" />}
        </div>
      ))}
    </nav>
  )
}
