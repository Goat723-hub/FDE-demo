const HIGHLIGHT_FIELDS = ['part_name', 'material', 'weight', 'quantity']

const FIELDS = [
  ['part_name', '零件名称'],
  ['material', '材质'],
  ['weight_kg', '单件重量 (kg)', 'number'],
  ['quantity', '数量', 'number'],
  ['unit', '单位'],
  ['process', '工艺要求', 'text', true],
  ['delivery_days', '交期 (天)', 'number'],
]

function DocPanel({ extraction, visibleItems, scanning }) {
  return (
    <section className="doc-panel">
      <div className="panel-head">
        <span>原始单据</span>
        <span className="mono">{extraction?.order?.inquiry_no || 'HD-2026-1020'}</span>
      </div>

      <div className="doc-frame">
        <div className="doc-wrap">
          <img src="/static/inquiry.png" alt="客户询价单" />
          {scanning && <div className="scanline" />}

          {extraction &&
            extraction.items.map((_, itemIndex) =>
              itemIndex < visibleItems
                ? HIGHLIGHT_FIELDS.map((field) => {
                    const box = extraction.boxes?.[`item_${itemIndex + 1}`]?.[field]
                    if (!box) return null
                    return (
                      <span
                        key={`${itemIndex}-${field}`}
                        className={`hl hl-${field}`}
                        style={{
                          left: `${box.x * 100}%`,
                          top: `${box.y * 100}%`,
                          width: `${box.w * 100}%`,
                          height: `${box.h * 100}%`,
                          animationDelay: `${HIGHLIGHT_FIELDS.indexOf(field) * 70}ms`,
                        }}
                      />
                    )
                  })
                : null,
            )}
        </div>
      </div>

      <div className="doc-legend">
        <span className="legend-dot" />
        AI 定位到的字段 · 右侧可逐项修改
      </div>
    </section>
  )
}

function ItemCard({ item, index, onChange, disabled }) {
  return (
    <article className="item-card" style={{ animationDelay: `${index * 90}ms` }}>
      <header>
        <span className="item-no">0{index + 1}</span>
        <h3>{item.part_name || '未识别'}</h3>
        <span className="tag">{disabled ? '已确认' : '待确认'}</span>
      </header>

      <div className="field-grid">
        {FIELDS.map(([key, label, type, wide]) => (
          <label className={`field ${wide ? 'wide' : ''}`} key={key}>
            <span>{label}</span>
            <input
              type={type || 'text'}
              value={item[key] ?? ''}
              disabled={disabled}
              onChange={(event) => onChange(index, key, event.target.value)}
              inputMode={type === 'number' ? 'decimal' : undefined}
            />
          </label>
        ))}
      </div>
    </article>
  )
}

function SkeletonCard({ index }) {
  return (
    <div className="item-card skeleton" style={{ animationDelay: `${index * 90}ms` }}>
      <div className="sk-head">
        <span className="sk-block w10" />
        <span className="sk-block w40" />
      </div>
      <div className="sk-grid">
        {Array.from({ length: 6 }).map((_, i) => (
          <span className="sk-block" key={i} />
        ))}
      </div>
    </div>
  )
}

export default function Workspace({
  step,
  extraction,
  items,
  visibleItems,
  onUpdate,
  onConfirm,
  onReset,
  error,
}) {
  const scanning = step === 'scanning'
  const quoting = step === 'quoting'
  const ready = items.length > 0 && visibleItems >= items.length

  return (
    <main className="workspace">
      <DocPanel
        extraction={extraction}
        visibleItems={scanning ? 0 : visibleItems}
        scanning={scanning}
      />

      <section className="fields-panel">
        <div className="panel-head">
          <span>识别结果 · 请确认</span>
          <span className="mono">
            {scanning ? 'READING…' : `${items.length} ITEMS / HUMAN REVIEW`}
          </span>
        </div>

        {scanning &&
          [0, 1, 2].map((index) => <SkeletonCard index={index} key={index} />)}

        {!scanning &&
          items.map((item, index) =>
            index < visibleItems ? (
              <ItemCard
                key={index}
                item={item}
                index={index}
                onChange={onUpdate}
                disabled={quoting}
              />
            ) : null,
          )}

        {error && <p className="inline-error">{error}</p>}

        <div className="actions">
          <button className="btn ghost" onClick={onReset} type="button">
            ← 重新识别
          </button>
          <button
            className="btn primary"
            onClick={onConfirm}
            disabled={scanning || quoting || !ready}
            type="button"
          >
            {quoting ? '正在计价…' : '确认并计价 →'}
          </button>
        </div>

        <p className="fineprint">
          单价 = 单件重量 × 材料单价 + 工序费；合计由后端计算，不经过模型。
        </p>
      </section>
    </main>
  )
}
