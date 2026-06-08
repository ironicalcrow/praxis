// Shared micro-components

export function Card({ children, style, onClick, className = '' }) {
  return (
    <div onClick={onClick} className={`glass-panel animate-fade-in ${className}`} style={{
      padding: 20, marginBottom: 16, ...style
    }}>
      {children}
    </div>
  )
}

export function Btn({ children, onClick, variant = 'primary', size = 'md', disabled, style }) {
  const isPrimary = variant === 'primary'
  
  const pad = size === 'sm' ? '6px 14px' : size === 'lg' ? '12px 28px' : '8px 20px'
  const fs = size === 'sm' ? 13 : size === 'lg' ? 16 : 14

  let baseStyle = {
    padding: pad, fontSize: fs, borderRadius: 8, fontWeight: 600,
    cursor: disabled ? 'not-allowed' : 'pointer', border: 'none',
    transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 8,
    opacity: disabled ? 0.6 : 1,
    ...style
  }

  if (isPrimary) {
    baseStyle.background = 'var(--gradient-primary)'
    baseStyle.color = '#fff'
    baseStyle.boxShadow = '0 4px 14px rgba(14, 165, 233, 0.25)'
    if (!disabled) baseStyle.transform = 'translateY(0)'
  } else if (variant === 'ghost') {
    baseStyle.background = 'rgba(255, 255, 255, 0.05)'
    baseStyle.color = 'var(--text-main)'
    baseStyle.border = '1px solid rgba(255, 255, 255, 0.1)'
  } else if (variant === 'danger') {
    baseStyle.background = 'rgba(244, 63, 94, 0.1)'
    baseStyle.color = 'var(--danger)'
    baseStyle.border = '1px solid rgba(244, 63, 94, 0.3)'
  } else if (variant === 'success') {
    baseStyle.background = 'rgba(16, 185, 129, 0.1)'
    baseStyle.color = 'var(--success)'
    baseStyle.border = '1px solid rgba(16, 185, 129, 0.3)'
  }

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={baseStyle}
      onMouseEnter={e => {
        if (!disabled && isPrimary) {
          e.currentTarget.style.background = 'var(--gradient-primary-hover)'
          e.currentTarget.style.transform = 'translateY(-1px)'
          e.currentTarget.style.boxShadow = '0 6px 20px rgba(14, 165, 233, 0.4)'
        } else if (!disabled) {
          e.currentTarget.style.background = variant === 'ghost' ? 'rgba(255,255,255,0.1)' : baseStyle.background
        }
      }}
      onMouseLeave={e => {
        if (!disabled && isPrimary) {
          e.currentTarget.style.background = 'var(--gradient-primary)'
          e.currentTarget.style.transform = 'translateY(0)'
          e.currentTarget.style.boxShadow = '0 4px 14px rgba(14, 165, 233, 0.25)'
        } else if (!disabled) {
          e.currentTarget.style.background = baseStyle.background
        }
      }}
      onMouseDown={e => { if (!disabled) e.currentTarget.style.transform = 'scale(0.96)' }}
      onMouseUp={e => { if (!disabled) e.currentTarget.style.transform = isPrimary ? 'translateY(-1px)' : 'scale(1)' }}
    >
      {children}
    </button>
  )
}

export function Input({ label, value, onChange, placeholder, type = 'text', style }) {
  return (
    <div style={{ marginBottom: 14 }}>
      {label && <label style={{ display: 'block', fontSize: 13, color: 'var(--text-muted)', marginBottom: 6, fontWeight: 500 }}>{label}</label>}
      <input
        type={type} value={value} onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        style={{
          width: '100%', background: 'rgba(0, 0, 0, 0.2)', border: '1px solid var(--border-strong)', borderRadius: 8,
          color: 'var(--text-main)', padding: '10px 14px', fontSize: 14, outline: 'none',
          transition: 'all 0.2s', ...style
        }}
      />
    </div>
  )
}

export function Textarea({ label, value, onChange, placeholder, rows = 4, style }) {
  return (
    <div style={{ marginBottom: 14 }}>
      {label && <label style={{ display: 'block', fontSize: 13, color: 'var(--text-muted)', marginBottom: 6, fontWeight: 500 }}>{label}</label>}
      <textarea
        value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} rows={rows}
        style={{
          width: '100%', background: 'rgba(0, 0, 0, 0.2)', border: '1px solid var(--border-strong)', borderRadius: 8,
          color: 'var(--text-main)', padding: '10px 14px', fontSize: 14, outline: 'none', resize: 'vertical',
          transition: 'all 0.2s', ...style
        }}
      />
    </div>
  )
}

export function Select({ label, value, onChange, options, style }) {
  return (
    <div style={{ marginBottom: 14 }}>
      {label && <label style={{ display: 'block', fontSize: 13, color: 'var(--text-muted)', marginBottom: 6, fontWeight: 500 }}>{label}</label>}
      <select
        value={value} onChange={e => onChange(e.target.value)}
        style={{
          width: '100%', background: 'rgba(0, 0, 0, 0.2)', border: '1px solid var(--border-strong)', borderRadius: 8,
          color: 'var(--text-main)', padding: '10px 14px', fontSize: 14, outline: 'none',
          transition: 'all 0.2s', appearance: 'none', ...style
        }}
      >
        {options.map(o => (
          <option key={o.value ?? o} value={o.value ?? o} style={{ background: 'var(--bg-dark)' }}>{o.label ?? o}</option>
        ))}
      </select>
    </div>
  )
}

export function Badge({ children, color = 'var(--primary)' }) {
  return (
    <span style={{
      background: `color-mix(in srgb, ${color} 15%, transparent)`, color, border: `1px solid color-mix(in srgb, ${color} 30%, transparent)`,
      borderRadius: 20, padding: '3px 10px', fontSize: 12, fontWeight: 600, letterSpacing: 0.3
    }}>
      {children}
    </span>
  )
}

export function Alert({ children, type = 'error' }) {
  const colors = { error: 'var(--danger)', success: 'var(--success)', info: 'var(--primary)', warning: 'var(--warning)' }
  const c = colors[type] || colors.error
  return (
    <div className="animate-slide-up" style={{
      background: `color-mix(in srgb, ${c} 10%, transparent)`, border: `1px solid color-mix(in srgb, ${c} 40%, transparent)`, borderRadius: 8,
      padding: '12px 16px', marginBottom: 16, color: c, fontSize: 14, display: 'flex', alignItems: 'center', gap: 10,
      backdropFilter: 'blur(8px)'
    }}>
      {children}
    </div>
  )
}

export function Spinner() {
  return (
    <span style={{
      display: 'inline-block', width: 20, height: 20,
      border: '3px solid color-mix(in srgb, var(--primary) 20%, transparent)', borderTop: '3px solid var(--primary)',
      borderRadius: '50%', animation: 'spin 0.8s linear infinite',
    }} />
  )
}

export function Pre({ children }) {
  return (
    <pre style={{
      background: 'rgba(0, 0, 0, 0.3)', border: '1px solid var(--border-strong)', borderRadius: 8,
      padding: 16, fontSize: 12, color: 'var(--text-muted)', overflow: 'auto',
      maxHeight: 350, whiteSpace: 'pre-wrap', wordBreak: 'break-all',
      fontFamily: "'Fira Code', monospace"
    }}>
      {typeof children === 'string' ? children : JSON.stringify(children, null, 2)}
    </pre>
  )
}

export function Row({ children, gap = 8, style }) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap, alignItems: 'center', ...style }}>
      {children}
    </div>
  )
}

export function SectionTitle({ children }) {
  return <h3 style={{ 
    fontSize: 16, fontWeight: 800, color: 'var(--text-main)', marginBottom: 20, 
    textTransform: 'uppercase', letterSpacing: 1.5,
    borderLeft: '4px solid var(--primary)', paddingLeft: 12
  }}>{children}</h3>
}
