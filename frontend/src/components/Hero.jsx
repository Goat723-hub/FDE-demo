export default function Hero({ onStart, error }) {
  return (
    <main className="hero">
      <div className="hero-copy">
        <p className="eyebrow">FORWARD DEPLOYED ENGINEER · DEMO 01</p>
        <h1>
          一张询价单，
          <br />
          <em>从 40 分钟到 40 秒。</em>
        </h1>
        <p className="lede">
          客户在微信发来一张照片，业务员要照着敲进 Excel、翻历史价、算材料费和加工费。
          这里让 LLM 负责看懂，Python 负责算准，人只负责点头。
        </p>

        <div className="hero-notes">
          <div className="hero-note">
            <span>01</span>
            <b>LLM 看单据</b>
            <small>只做抽取，不做决定</small>
          </div>
          <div className="hero-note">
            <span>02</span>
            <b>人确认字段</b>
            <small>错了当场改</small>
          </div>
          <div className="hero-note">
            <span>03</span>
            <b>Python 算价</b>
            <small>同输入同输出</small>
          </div>
        </div>
      </div>

      <div className="upload-stage">
        <div className="paper-preview" aria-hidden="true">
          <img src="/static/inquiry.png" alt="" />
          <div className="paper-fade" />
        </div>

        <button className="upload-card" onClick={onStart} type="button">
          <span className="upload-plus" aria-hidden="true">
            +
          </span>
          <span className="upload-title">开始识别这张询价单</span>
          <span className="upload-sub">
            演示使用内置样例 HD-2026-1020 · 点击即上传
          </span>
          <span className="upload-cta">
            开始识别 <i>→</i>
          </span>
        </button>

        {error && <p className="inline-error">{error}</p>}
      </div>
    </main>
  )
}
