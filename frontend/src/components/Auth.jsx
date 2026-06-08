import { useState } from 'react'
import { useAuth } from '../AuthContext'
import { Card, Btn, Input, Alert } from './ui'

export default function Auth() {
  const { login, register } = useAuth()
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ name: '', username: '', email: '', password: '' })
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)

  const set = (k) => (v) => setForm(f => ({ ...f, [k]: v }))

  async function submit(e) {
    e.preventDefault()
    setErr(''); setLoading(true)
    try {
      if (mode === 'login') {
        await login(form.email, form.password)
      } else {
        await register(form.name, form.username, form.email, form.password)
      }
    } catch (e) {
      setErr(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="animate-fade-in" style={{ 
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', 
      background: 'radial-gradient(circle at top right, rgba(14, 165, 233, 0.15), transparent 40%), radial-gradient(circle at bottom left, rgba(59, 130, 246, 0.15), transparent 40%)',
      position: 'relative'
    }}>
      <div style={{ width: 400, zIndex: 10 }}>
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <div style={{ width: 48, height: 48, margin: '0 auto 16px', borderRadius: 12, background: 'var(--gradient-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 800, fontSize: 24, boxShadow: '0 8px 24px rgba(14, 165, 233, 0.3)' }}>P</div>
          <h1 style={{ fontSize: 32, fontWeight: 800, color: 'var(--text-main)', letterSpacing: -0.5 }}>Praxis</h1>
          <p style={{ color: 'var(--primary)', fontSize: 14, marginTop: 6, fontWeight: 600, letterSpacing: 0.5, textTransform: 'uppercase' }}>AI Career Platform</p>
        </div>
        <Card style={{ padding: '30px', border: '1px solid var(--border-strong)', background: 'rgba(5, 10, 21, 0.7)' }}>
          <div style={{ display: 'flex', marginBottom: 24, background: 'rgba(0,0,0,0.3)', borderRadius: 8, padding: 4 }}>
            {['login', 'register'].map(m => (
              <button key={m} onClick={() => { setMode(m); setErr('') }}
                style={{
                  flex: 1, padding: '10px 0', background: mode === m ? 'var(--gradient-primary)' : 'transparent', border: 'none',
                  color: mode === m ? '#fff' : 'var(--text-muted)', fontWeight: mode === m ? 600 : 500,
                  borderRadius: 6, cursor: 'pointer', textTransform: 'capitalize', fontSize: 14,
                  transition: 'all 0.2s', boxShadow: mode === m ? '0 4px 14px rgba(14, 165, 233, 0.2)' : 'none'
                }}>
                {m}
              </button>
            ))}
          </div>
          <form onSubmit={submit}>
            {mode === 'register' && (
              <>
                <Input label="Full Name" value={form.name} onChange={set('name')} placeholder="John Doe" />
                <Input label="Username" value={form.username} onChange={set('username')} placeholder="johndoe" />
              </>
            )}
            <Input label="Email" type="email" value={form.email} onChange={set('email')} placeholder="you@example.com" />
            <Input label="Password" type="password" value={form.password} onChange={set('password')} placeholder="••••••••" />
            {err && <Alert type="error">{err}</Alert>}
            <Btn size="lg" disabled={loading} style={{ width: '100%', marginTop: 8 }}>
              {loading ? 'Please wait…' : mode === 'login' ? 'Sign In' : 'Create Account'}
            </Btn>
          </form>
        </Card>
      </div>
    </div>
  )
}
