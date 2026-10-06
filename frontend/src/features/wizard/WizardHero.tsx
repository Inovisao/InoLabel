/** Cabeçalho de cada etapa do wizard: título, subtítulo e ilustração. */
export default function HeroSection({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div
      style={{
        background: "var(--color-hero-bg)",
        borderRadius: "var(--radius-xl)",
        padding: "28px 32px",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div style={{ maxWidth: 520, position: "relative", zIndex: 1 }}>
        <h1 className="text-display" style={{ marginBottom: 8 }}>{title}</h1>
        <p className="text-page-subtitle">{subtitle}</p>
      </div>
      <div
        style={{
          position: "absolute",
          right: 0,
          top: "50%",
          transform: "translateY(-50%)",
          pointerEvents: "none",
          opacity: 0.85,
        }}
      >
        <HeroIllustration />
      </div>
    </div>
  );
}

function HeroIllustration() {
  return (
    <svg width="240" height="190" viewBox="0 0 240 190" fill="none" xmlns="http://www.w3.org/2000/svg">
      <polygon points="80,50 130,28 200,28 150,50" fill="var(--color-illustration-soft)" stroke="var(--color-illustration-stroke)" strokeWidth="1.5" strokeLinejoin="round" />
      <polygon points="150,50 200,28 200,110 150,132" fill="var(--color-illustration-softer)" stroke="var(--color-illustration-stroke)" strokeWidth="1.5" strokeLinejoin="round" />
      <polygon points="80,50 150,50 150,132 80,132" fill="var(--color-illustration-softest)" stroke="var(--color-illustration-stroke)" strokeWidth="1.5" strokeLinejoin="round" />
      {([
        [80, 50], [150, 50], [80, 132], [150, 132],
        [130, 28], [200, 28], [200, 110],
      ] as [number, number][]).map(([cx, cy], i) => (
        <circle key={i} cx={cx} cy={cy} r="3.5" fill="var(--color-illustration-stroke)" />
      ))}
      <rect x="148" y="124" width="78" height="54" rx="10" fill="var(--color-illustration-panel)" filter="var(--shadow-illustration)" />
      <rect x="156" y="132" width="22" height="16" rx="4" fill="var(--color-primary-light)" />
      <circle cx="159.5" cy="135.5" r="2.5" fill="var(--color-illustration-stroke)" />
      <path d="M156 147l5-5 4 4 3-3 6 6" stroke="var(--color-illustration-stroke)" strokeWidth="1.2" fill="none" strokeLinecap="round" />
      <rect x="182" y="133" width="36" height="3" rx="1.5" fill="var(--color-border)" />
      <rect x="182" y="140" width="26" height="3" rx="1.5" fill="var(--color-border)" />
      <rect x="186" y="38" width="46" height="26" rx="13" fill="var(--color-neutral-active)" />
      <text x="209" y="55" textAnchor="middle" fontSize="11" fill="var(--color-muted)" fontFamily="monospace" fontWeight="600">{"</>"}</text>
      <circle cx="52" cy="48" r="2.5" fill="var(--color-illustration-dot)" opacity="0.8" />
      <circle cx="44" cy="60" r="1.8" fill="var(--color-illustration-dot)" opacity="0.5" />
      <circle cx="58" cy="70" r="1.5" fill="var(--color-illustration-dot)" opacity="0.4" />
    </svg>
  );
}
