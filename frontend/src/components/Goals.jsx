import { useState, useEffect } from 'react'
import { goals as goalsApi } from '../api'
import { Card, Btn, Input, Select, Textarea, Alert, Pre, Badge, Row, SectionTitle, Spinner } from './ui'

const STATUS_COLORS = {
  not_started: '#94a3b8', in_progress: '#3b82f6', completed: '#22c55e', paused: '#f59e0b'
}
const STATUSES = ['not_started', 'in_progress', 'completed', 'paused']

export default function Goals() {
  const [list, setList] = useState([])
  const [selected, setSelected] = useState(null)
  const [tab, setTab] = useState('list')
  const [filterStatus, setFilterStatus] = useState('')
  const [form, setForm] = useState({ title: '', description: '', target_date: '' })
  const [editStatus, setEditStatus] = useState('')
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')
  const [msg, setMsg] = useState('')

  useEffect(() => { load() }, [filterStatus])

  async function load() {
    try { setList(await goalsApi.list(filterStatus)) }
    catch (e) { setErr(e.message) }
  }

  async function open(id) {
    setLoading(true); setErr('')
    try {
      const d = await goalsApi.get(id)
      setSelected(d); setEditStatus(d.status)
    } catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }

  async function create(e) {
    e.preventDefault(); setLoading(true); setErr('')
    try {
      await goalsApi.create(form)
      setMsg('Goal created!'); load()
      setForm({ title: '', description: '', target_date: '', priority: 'medium' })
      setTab('list')
    } catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }

  async function updateStatus() {
    if (!selected || !editStatus) return; setLoading(true)
    try {
      const res = await goalsApi.update(selected.id, { status: editStatus })
      setSelected(res); setMsg('Updated!'); load()
    } catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }

  async function del(id) {
    if (!confirm('Delete this goal?')) return
    try {
      await goalsApi.delete(id); setMsg('Deleted!'); load()
      if (selected?.id === id) setSelected(null)
    } catch (e) { setErr(e.message) }
  }

  const set = (k) => (v) => setForm(f => ({ ...f, [k]: v }))
  const tabs = ['list', 'create']

  return (
    <div>
      <SectionTitle>Goals</SectionTitle>
      <div style={{ display: 'flex', gap: 4, marginBottom: 16, borderBottom: '1px solid #2d2d4e' }}>
        {tabs.map(t => (
          <button key={t} onClick={() => { setTab(t); setErr(''); setMsg('') }}
            style={{
              padding: '7px 14px', background: 'none', border: 'none', cursor: 'pointer',
              color: tab === t ? '#a5b4fc' : '#64748b', borderBottom: tab === t ? '2px solid #6366f1' : '2px solid transparent',
              fontSize: 13, fontWeight: tab === t ? 700 : 400, textTransform: 'capitalize'
            }}>
            {t}
          </button>
        ))}
      </div>

      {err && <Alert type="error">{err}</Alert>}
      {msg && <Alert type="success">{msg}</Alert>}

      {tab === 'create' && (
        <Card>
          <h4 style={{ marginBottom: 12, color: '#e2e8f0' }}>New Goal</h4>
          <form onSubmit={create}>
            <Input label="Title *" value={form.title} onChange={set('title')} placeholder="Learn GraphQL" />
            <Textarea label="Description" value={form.description} onChange={set('description')} rows={2} />
            <Input label="Target Date" type="date" value={form.target_date} onChange={set('target_date')} />
            <Btn disabled={loading || !form.title}>{loading ? <Spinner /> : 'Create Goal'}</Btn>
          </form>
        </Card>
      )}

      {tab === 'list' && (
        <>
          <Row style={{ marginBottom: 12 }}>
            <Select label="" value={filterStatus} onChange={setFilterStatus}
              options={[{ value: '', label: 'All' }, ...STATUSES.map(s => ({ value: s, label: s }))]}
              style={{ width: 160, marginBottom: 0 }} />
            <Btn size="sm" variant="ghost" onClick={load}>Refresh</Btn>
          </Row>
          <div style={{ display: 'flex', gap: 12 }}>
            <div style={{ flex: 1 }}>
              {list.length === 0 && <p style={{ color: '#475569', fontSize: 13 }}>No goals. Create one or use the chat to generate them.</p>}
              {(Array.isArray(list) ? list : []).map(g => (
                <Card key={g.id} style={{ cursor: 'pointer', border: selected?.id === g.id ? '1px solid #6366f1' : undefined }}
                  onClick={() => open(g.id)}>
                  <Row>
                    <div style={{ flex: 1 }}>
                      <strong style={{ color: '#e2e8f0' }}>{g.title}</strong>
                      {g.target_date && (
                        <span style={{ fontSize: 11, color: '#64748b', marginLeft: 8 }}>
                          due {new Date(g.target_date).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                    <Badge color={STATUS_COLORS[g.status] || '#64748b'}>{g.status?.replace('_', ' ')}</Badge>
                    <Btn size="sm" variant="danger" onClick={e => { e.stopPropagation(); del(g.id) }}>✕</Btn>
                  </Row>
                  {g.description && <p style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>{g.description}</p>}
                </Card>
              ))}
            </div>

            {selected && (
              <div style={{ flex: 1, minWidth: 220 }}>
                <Card style={{ border: '1px solid #4f46e5' }}>
                  <Row style={{ marginBottom: 8 }}>
                    <h4 style={{ color: '#a5b4fc', flex: 1 }}>{selected.title}</h4>
                    <Btn size="sm" variant="ghost" onClick={() => setSelected(null)}>✕</Btn>
                  </Row>
                  {selected.description && (
                    <p style={{ color: '#64748b', fontSize: 13, marginBottom: 10 }}>{selected.description}</p>
                  )}
                  <div style={{ marginBottom: 10 }}>
                    <Badge color={STATUS_COLORS[selected.status] || '#64748b'}>{selected.status?.replace('_', ' ')}</Badge>
                  </div>
                  {selected.target_date && (
                    <p style={{ fontSize: 12, color: '#64748b' }}>Due: {new Date(selected.target_date).toLocaleDateString()}</p>
                  )}
                  <h5 style={{ color: '#94a3b8', fontSize: 12, marginTop: 12, marginBottom: 6 }}>Update Status</h5>
                  <Select label="" value={editStatus} onChange={setEditStatus} options={STATUSES}
                    style={{ marginBottom: 8 }} />
                  <Btn size="sm" onClick={updateStatus} disabled={loading}>Update</Btn>
                  <details style={{ marginTop: 10 }}>
                    <summary style={{ cursor: 'pointer', fontSize: 11, color: '#475569' }}>Raw JSON</summary>
                    <Pre>{selected}</Pre>
                  </details>
                </Card>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
