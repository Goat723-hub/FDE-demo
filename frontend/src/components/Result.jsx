import { fmt, useCountUp, useTypewriter } from '../lib'

function Change({ pct }) {
  if (pct == null) return <span className="muted">无历史</span>
  const up = pct > 0
  return (
    <span className={`change ${up ? 'up' : 'down'}`}>
      {up ? '↑' : '↓'} {Math.abs(pct).toFixed(1)}%
    </span>
  )
}

export default function Result({ quote, summary, order, onDownload, onReset }) {
  const total = useCountUp(quote.total)
  const typed = useTypewriter(summary)
  const lineSubtotal = quote.line_items.reduce((sum, row) => sum + row.line_total, 0)

  return (
    <main className="result">
      <div className="result-top">
        <div className="result-title">
          <p className="eyebrow">QUOTATION READY · {order.inquiry_no || 'DEMO'}</p>
          <div className="total">
            <span className="cny">¥</span>
            {fmt(total)}
          </div>
          <p className="total-meta">
            {quote.item_count} 个零件 · {quote.total_quantity} 件 · 含开机费 ¥{fmt(quote.setup_fee)}
            {quote.expedite ? ` · 急单系数 ${quote.expedite_multiplier}` : ''}
          </p>
        </div>

        <div className="output-block">
          <span className="output-label">OUTPUT · 报价单已生成</span>
          <div className="result-actions">
            <button className="btn primary" onClick={onDownload} type="button">
              下载 PDF 报价单 <span className="btn-arrow">↓</span>
            </button>
            <button className="btn ghost" onClick={onReset} type="button">
              重新演示
            </button>
          </div>
          <span className="output-note">后端 fpdf2 生成 · A4 · 可直接发客户</span>
        </div>
      </div>

      <div className="result-grid">
        <section className="quote-sheet">
          <div className="panel-head">
            <span>报价明细</span>
            <span className="mono">DETERMINISTIC / PYTHON</span>
          </div>

          <table>
            <thead>
              <tr>
                <th>零件</th>
                <th>材质</th>
                <th className="num">数量</th>
                <th className="num">单件价</th>
                <th className="num">小计</th>
                <th className="num">较上次</th>
              </tr>
            </thead>
            <tbody>
              {quote.line_items.map((row) => (
                <tr key={row.part_name}>
                  <td>
                    <b>{row.part_name}</b>
                    <small>{row.process}</small>
                  </td>
                  <td>{row.material}</td>
                  <td className="num">
                    {row.quantity} {row.unit}
                  </td>
                  <td className="num">¥{fmt(row.unit_price)}</td>
                  <td className="num">¥{fmt(row.line_total)}</td>
                  <td className="num">
                    <Change pct={row.change_pct} />
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan="4">零件合计</td>
                <td className="num">¥{fmt(lineSubtotal)}</td>
                <td />
              </tr>
              <tr>
                <td colSpan="4">开机费</td>
                <td className="num">¥{fmt(quote.setup_fee)}</td>
                <td />
              </tr>
              <tr className="grand">
                <td colSpan="4">合计</td>
                <td className="num">¥{fmt(quote.total)}</td>
                <td />
              </tr>
            </tfoot>
          </table>
        </section>

        <section className="summary-card">
          <div className="panel-head">
            <span>报价摘要</span>
            <span className="mono">FACTS → LLM</span>
          </div>

          <p className="summary-text">
            {typed}
            <span className="caret">▌</span>
          </p>

          <div className="summary-foot">数字由 Python 计算 · 文字由 deepseek-flash 组织</div>

          <div className="source-facts">
            <div>
              <span>历史对比</span>
              <b>
                {quote.biggest_change
                  ? `${quote.biggest_change.part_name} ${
                      quote.biggest_change.change_pct > 0 ? '+' : ''
                    }${quote.biggest_change.change_pct}%`
                  : '无历史同材料报价'}
              </b>
            </div>
            <div>
              <span>计价方式</span>
              <b>材料费 + 工序费</b>
            </div>
            <div>
              <span>报价单</span>
              <b>后端 fpdf2 生成</b>
            </div>
          </div>
        </section>
      </div>
    </main>
  )
}
