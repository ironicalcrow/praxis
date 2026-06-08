import { useState, useEffect } from 'react'
import { useAuth } from './AuthContext'
import Auth from './components/Auth'
import CVSection from './components/CV'
import Jobs from './components/Jobs'
import Applications from './components/Applications'
import Chat from './components/Chat'
import CoverLetters from './components/CoverLetters'
import Roadmaps from './components/Roadmaps'
import Goals from './components/Goals'
import Notifications from './components/Notifications'
import { health, createNotificationWS } from './api'
import { Spinner } from './components/ui'

const TABS = [
  { id: 'chat',         label: 'Chat',           emoji: '💬' },
  { id: 'jobs',         label: 'Jobs',           emoji: '🔍' },
  { id: 'applications', label: 'Applications',   emoji: '📋' },
  { id: 'cv',           label: 'CV',             emoji: '📄' },
  { id: 'cover-letters',label: 'Cover Letters',  emoji: '✉️' },
  { id: 'roadmaps',     label: 'Roadmaps',       emoji: '🗺️' },
  { id: 'goals',        label: 'Goals',          emoji: '🎯' },
  { id: 'notifications',label: 'Notifications',  emoji: '🔔' },
]

export default function App() {
  const { user, loading, logout } = useAuth()
  const [tab, setTab] = useState('chat')
  const [selectedJob, setSelectedJob] = useState(null)
  const [apiOk, setApiOk] = useState(null)
  const [wsStatus, setWsStatus] = useState('disconnected')
  const [live, setLive] = useState([])

  useEffect(() => {
    health().then(() => setApiOk(true)).catch(() => setApiOk(false))
  }, [])

  useEffect(() => {
    if (!user) return
    setWsStatus('connecting')
    const ws = createNotificationWS(
      (msg) => {
        setLive(l => [{ ...msg, _ts: Date.now() }, ...l.slice(0, 19)])
      },
      () => setWsStatus('connected'),
      () => setWsStatus('disconnected')
    )
    return () => {
      ws.close()
      setWsStatus('disconnected')
    }
  }, [user])

  if (loading) {
    return (
      <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Spinner />
      </div>
    )
  }

  if (!user) return <Auth />

  function handleSelectJob(job) {
    setSelectedJob(job)
    setTab('chat')
  }

  return (
    <div className="animate-fade-in">

      {/* Header */}
      <div className="glass-header" style={{
        position: 'sticky', top: 0, zIndex: 50, padding: '0 20px',
        boxShadow: '0 4px 30px rgba(0,0,0,0.2)'
      }}>
        <div style={{ maxWidth: 1200, margin: '0 auto', display: 'flex', alignItems: 'center', height: 60 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 32, height: 32, borderRadius: 8, background: 'var(--gradient-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 800, fontSize: 18 }}>P</div>
            <h1 style={{ fontSize: 20, fontWeight: 800, color: 'var(--text-main)', letterSpacing: -0.5 }}>Praxis</h1>
          </div>
          {apiOk !== null && (
            <span style={{ fontSize: 12, marginLeft: 16, color: apiOk ? 'var(--success)' : 'var(--danger)', background: `color-mix(in srgb, ${apiOk ? 'var(--success)' : 'var(--danger)'} 15%, transparent)`, padding: '4px 10px', borderRadius: 20, fontWeight: 600 }}>
              ● backend {apiOk ? 'online' : 'offline'}
            </span>
          )}
          <div style={{ flex: 1 }} />
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span style={{ fontSize: 14, color: 'var(--text-muted)', fontWeight: 500 }}>{user.email}</span>
            <button onClick={logout} style={{
              fontSize: 13, padding: '6px 14px', background: 'rgba(255,255,255,0.05)',
              border: '1px solid var(--border-strong)', borderRadius: 8, color: 'var(--text-muted)', cursor: 'pointer',
              transition: 'all 0.2s', fontWeight: 600
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.1)'; e.currentTarget.style.color = 'var(--text-main)' }}
            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; e.currentTarget.style.color = 'var(--text-muted)' }}
            >
              Sign out
            </button>
          </div>
        </div>

        {/* Nav tabs */}
        <div style={{ maxWidth: 1200, margin: '0 auto', display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 10 }}>
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              style={{
                padding: '8px 16px', border: 'none', cursor: 'pointer', borderRadius: 8,
                color: tab === t.id ? '#fff' : 'var(--text-muted)',
                background: tab === t.id ? 'var(--gradient-primary)' : 'transparent',
                boxShadow: tab === t.id ? '0 4px 14px rgba(14, 165, 233, 0.25)' : 'none',
                fontSize: 14, fontWeight: tab === t.id ? 600 : 500, whiteSpace: 'nowrap',
                transition: 'all 0.2s', display: 'flex', alignItems: 'center', gap: 6
              }}
              onMouseEnter={e => { if(tab !== t.id) e.currentTarget.style.background = 'rgba(255,255,255,0.05)' }}
              onMouseLeave={e => { if(tab !== t.id) e.currentTarget.style.background = 'transparent' }}
              >
              <span>{t.emoji}</span> {t.label}
              {t.id === 'notifications' && live.length > 0 && (
                <span style={{ marginLeft: 4, width: 8, height: 8, background: 'var(--warning)', borderRadius: '50%', boxShadow: '0 0 8px var(--warning)' }} />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Context bar: selected job */}
      {selectedJob && tab !== 'jobs' && (
        <div className="animate-slide-up" style={{ background: 'rgba(14, 165, 233, 0.1)', borderBottom: '1px solid var(--border-subtle)', padding: '8px 20px', backdropFilter: 'blur(8px)' }}>
          <div style={{ maxWidth: 1200, margin: '0 auto', display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>Selected job:</span>
            <span style={{ fontSize: 14, color: 'var(--primary)', fontWeight: 600 }}>
              {selectedJob.title} @ {selectedJob.company_name}
            </span>
            <button onClick={() => setSelectedJob(null)}
              style={{ fontSize: 12, color: 'var(--text-muted)', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-strong)', borderRadius: 12, padding: '2px 8px', cursor: 'pointer', transition: 'all 0.2s' }}
              onMouseEnter={e => e.currentTarget.style.background = 'rgba(0,0,0,0.4)'}
              onMouseLeave={e => e.currentTarget.style.background = 'rgba(0,0,0,0.2)'}
            >
              ✕ clear
            </button>
          </div>
        </div>
      )}

      {/* Main content */}
      <div className="animate-slide-up" style={{ maxWidth: 1200, margin: '0 auto', padding: '30px 20px 60px' }}>
        {tab === 'cv' && <CVSection />}
        {tab === 'jobs' && <Jobs onSelectJob={handleSelectJob} />}
        {tab === 'applications' && <Applications />}
        {tab === 'chat' && <Chat preselectedJob={selectedJob} />}
        {tab === 'cover-letters' && <CoverLetters preselectedJob={selectedJob} />}
        {tab === 'roadmaps' && <Roadmaps />}
        {tab === 'goals' && <Goals />}
        {tab === 'notifications' && <Notifications live={live} wsStatus={wsStatus} />}
      </div>
    </div>
  )
}
