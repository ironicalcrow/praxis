import { useState, useEffect } from 'react'
import { notifications as notiApi } from '../api'
import { Card, Btn, Alert, Badge, Row, SectionTitle, Spinner } from './ui'

export default function Notifications({ live = [], wsStatus = 'disconnected' }) {
  const [list, setList] = useState([])
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => { load() }, [unreadOnly])

  async function load() {
    setLoading(true)
    try { setList(await notiApi.list(unreadOnly)) }
    catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }



  async function markRead(id) {
    try { await notiApi.markRead(id); load() } catch {}
  }

  async function markAll() {
    try { await notiApi.markAllRead(); load(); setErr('') } catch (e) { setErr(e.message) }
  }

  async function del(id) {
    try { await notiApi.delete(id); load() } catch {}
  }

  const wsColor = { connected: '#22c55e', connecting: '#f59e0b', disconnected: '#ef4444' }

  return (
    <div>
      <SectionTitle>Notifications</SectionTitle>

      <Card>
        <Row style={{ marginBottom: 8 }}>
          <span style={{ fontSize: 13, color: '#94a3b8' }}>WebSocket</span>
          <span style={{ fontSize: 12, color: wsColor[wsStatus] || '#ef4444', fontWeight: 700 }}>● {wsStatus}</span>
        </Row>
        {live.length > 0 && (
          <div>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1 }}>Live feed (last 20)</p>
            {live.map((n, i) => (
              <div key={i} className="animate-slide-up" style={{
                background: 'rgba(34, 197, 94, 0.05)', border: '1px solid rgba(34, 197, 94, 0.2)', borderRadius: 8,
                padding: '10px 14px', marginBottom: 6, fontSize: 13,
                boxShadow: '0 4px 10px rgba(0,0,0,0.1)'
              }}>
                <Row>
                  <Badge color="var(--success)">{n.type || n.event_type || 'event'}</Badge>
                  <span style={{ color: 'var(--text-main)', flex: 1, fontWeight: 500 }}>{n.title || n.message || JSON.stringify(n).slice(0, 60)}</span>
                </Row>
                {n.message && n.title && <p style={{ color: 'var(--text-muted)', marginTop: 4 }}>{n.message}</p>}
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card>
        <Row style={{ marginBottom: 16 }}>
          <label style={{ fontSize: 14, color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8, fontWeight: 500 }}>
            <input type="checkbox" checked={unreadOnly} onChange={e => setUnreadOnly(e.target.checked)} style={{ width: 16, height: 16, accentColor: 'var(--primary)' }} />
            Unread only
          </label>
          <Btn size="sm" onClick={load} disabled={loading} variant="ghost">Refresh</Btn>
          <Btn size="sm" variant="ghost" onClick={markAll}>Mark All Read</Btn>
        </Row>
        {err && <Alert type="error">{err}</Alert>}
        {loading && <div style={{ padding: 20, textAlign: 'center' }}><Spinner /></div>}
        {list.length === 0 && !loading && (
          <p style={{ color: 'var(--text-muted)', fontSize: 14, textAlign: 'center', padding: 20 }}>No notifications.</p>
        )}
        {(Array.isArray(list) ? list : []).map(n => (
          <div key={n.id} className="animate-slide-up" style={{
            display: 'flex', alignItems: 'flex-start', gap: 12,
            padding: '16px', borderBottom: '1px solid var(--border-subtle)',
            background: n.is_read ? 'transparent' : 'rgba(14, 165, 233, 0.05)',
            opacity: n.is_read ? 0.6 : 1,
            borderRadius: n.is_read ? 0 : 8,
            marginBottom: 4, transition: 'background 0.2s'
          }}>
            <div style={{ flex: 1 }}>
              <Row>
                <Badge color="var(--primary)">{n.type}</Badge>
                {!n.is_read && <Badge color="var(--warning)">new</Badge>}
                <span style={{ color: 'var(--text-main)', fontSize: 14, fontWeight: 600 }}>{n.title}</span>
              </Row>
              {n.message && <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 6, lineHeight: 1.5 }}>{n.message}</p>}
              <p style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 8, fontWeight: 500 }}>{new Date(n.created_at).toLocaleString()}</p>
            </div>
            <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
              {!n.is_read && (
                <Btn size="sm" variant="ghost" onClick={() => markRead(n.id)}>Read</Btn>
              )}
              <Btn size="sm" variant="danger" onClick={() => del(n.id)}>✕</Btn>
            </div>
          </div>
        ))}
      </Card>
    </div>
  )
}
