import { useState, useEffect } from 'react'
import { apps } from '../api'
import { useAuth } from '../AuthContext'
import { Card, Btn, Input, Textarea, Select, Alert, Pre, Badge, Row, SectionTitle, Spinner } from './ui'

const STATUS_COLORS = {
  saved: '#6366f1', applied: '#3b82f6', interviewing: '#f59e0b',
  offer: '#22c55e', rejected: '#ef4444', archived: '#64748b'
}

const STATUSES = ['saved', 'applied', 'interviewing', 'offer', 'rejected']

export default function Applications() {
  const { user } = useAuth()
  const [view, setView] = useState('kanban')
  const [kanban, setKanban] = useState({})
  const [list, setList] = useState([])
  const [selected, setSelected] = useState(null)
  const [filterStatus, setFilterStatus] = useState('')
  const [newNote, setNewNote] = useState('')
  const [newStatus, setNewStatus] = useState('')
  const [statusNote, setStatusNote] = useState('')
  const [manualForm, setManualForm] = useState({ job_title: '', company: '', location: '', apply_url: '', notes: '' })
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')
  const [msg, setMsg] = useState('')

  useEffect(() => { load() }, [view, filterStatus])

  async function load() {
    if (!user) return
    setLoading(true); setErr('')
    try {
      if (view === 'kanban') {
        const d = await apps.kanban(user.id)
        setKanban(d.kanban || d || {})
      } else {
        const d = await apps.list(user.id, filterStatus)
        setList(d.applications || d || [])
      }
    } catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }

  async function openApp(app) {
    setSelected(app); setNewStatus(app.status); setNewNote(''); setStatusNote(''); setErr('')
  }

  async function updateStatus() {
    if (!selected || !newStatus) return
    setLoading(true)
    try {
      await apps.updateStatus(selected.id, { user_id: user.id, status: newStatus, reason: statusNote })
      setMsg('Status updated!')
      setSelected(s => ({ ...s, status: newStatus }))
      load()
    } catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }

  async function addNote() {
    if (!selected || !newNote.trim()) return
    setLoading(true)
    try {
      await apps.addNote(selected.id, { content: newNote })
      setNewNote('')
      setMsg('Note added!')
    } catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }

  async function archive(id) {
    try {
      await apps.archive(id, user.id)
      setMsg('Archived!'); load()
      if (selected?.id === id) setSelected(null)
    } catch (e) { setErr(e.message) }
  }

  async function del(id) {
    if (!confirm('Delete this application?')) return
    try {
      await apps.delete(id, user.id)
      setMsg('Deleted!'); load()
      if (selected?.id === id) setSelected(null)
    } catch (e) { setErr(e.message) }
  }

  const set = (k) => (v) => setManualForm(f => ({ ...f, [k]: v }))

  async function createManual(e) {
    e.preventDefault(); setLoading(true); setErr('')
    try {
      await apps.manual({ ...manualForm, user_id: user.id })
      setMsg('Application created!'); setManualForm({ job_title: '', company: '', location: '', apply_url: '', notes: '' })
      load()
    } catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }

  const views = ['kanban', 'list', 'add']

  return (
    <div>
      <SectionTitle>Applications</SectionTitle>
      <div style={{ display: 'flex', gap: 4, marginBottom: 16, borderBottom: '1px solid #2d2d4e' }}>
        {views.map(v => (
          <button key={v} onClick={() => { setView(v); setErr(''); setMsg(''); setSelected(null) }}
            style={{
              padding: '7px 14px', background: 'none', border: 'none', cursor: 'pointer',
              color: view === v ? '#a5b4fc' : '#64748b', borderBottom: view === v ? '2px solid #6366f1' : '2px solid transparent',
              fontSize: 13, fontWeight: view === v ? 700 : 400, textTransform: 'capitalize'
            }}>
            {v}
          </button>
        ))}
      </div>

      {err && <Alert type="error">{err}</Alert>}
      {msg && <Alert type="success">{msg}</Alert>}

      {view === 'kanban' && (
        <div style={{ overflowX: 'auto' }}>
          {loading && <Spinner />}
          <div style={{ display: 'flex', gap: 12, minWidth: 800, paddingBottom: 8 }}>
            {STATUSES.map(s => {
              const col = kanban[s] || []
              return (
                <div key={s} style={{ flex: 1, minWidth: 160 }}>
                  <div style={{
                    padding: '4px 8px', background: STATUS_COLORS[s] + '22',
                    borderBottom: `2px solid ${STATUS_COLORS[s]}`, marginBottom: 8,
                    borderRadius: '6px 6px 0 0', fontSize: 12, fontWeight: 700,
                    color: STATUS_COLORS[s], textTransform: 'uppercase', letterSpacing: 0.5
                  }}>
                    {s} ({col.length})
                  </div>
                  {col.map(a => (
                    <div key={a.id} onClick={() => openApp(a)}
                      style={{
                        background: '#1a1a2e', border: '1px solid #2d2d4e', borderRadius: 6,
                        padding: '8px 10px', marginBottom: 6, cursor: 'pointer', fontSize: 13
                      }}>
                      <div style={{ color: '#e2e8f0', fontWeight: 600 }}>{a.job_title}</div>
                      <div style={{ color: '#94a3b8', fontSize: 11 }}>{a.company}</div>
                      {a.location && <div style={{ color: '#475569', fontSize: 11 }}>{a.location}</div>}
                    </div>
                  ))}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {view === 'list' && (
        <>
          <Row style={{ marginBottom: 12 }}>
            <Select label="" value={filterStatus} onChange={setFilterStatus}
              options={[{ value: '', label: 'All statuses' }, ...STATUSES.map(s => ({ value: s, label: s }))]}
              style={{ width: 160, marginBottom: 0 }} />
            <Btn size="sm" onClick={load} disabled={loading}>Refresh</Btn>
          </Row>
          {list.map(a => (
            <Card key={a.id} style={{ cursor: 'pointer' }} onClick={() => openApp(a)}>
              <Row>
                <div style={{ flex: 1 }}>
                  <strong style={{ color: '#e2e8f0' }}>{a.job_title}</strong>
                  <span style={{ color: '#94a3b8', fontSize: 13 }}> · {a.company}</span>
                  {a.location && <span style={{ color: '#64748b', fontSize: 12 }}> · {a.location}</span>}
                </div>
                <Badge color={STATUS_COLORS[a.status] || '#64748b'}>{a.status}</Badge>
              </Row>
            </Card>
          ))}
        </>
      )}

      {view === 'add' && (
        <Card>
          <h4 style={{ marginBottom: 12, color: '#e2e8f0' }}>Add Manual Application</h4>
          <form onSubmit={createManual}>
            <Input label="Job Title *" value={manualForm.job_title} onChange={set('job_title')} placeholder="Senior Backend Engineer" />
            <Input label="Company *" value={manualForm.company} onChange={set('company')} placeholder="Acme Corp" />
            <Input label="Location" value={manualForm.location} onChange={set('location')} placeholder="Dhaka, Bangladesh" />
            <Input label="Apply URL" value={manualForm.apply_url} onChange={set('apply_url')} placeholder="https://..." />
            <Textarea label="Notes" value={manualForm.notes} onChange={set('notes')} rows={3} />
            <Btn disabled={loading}>{loading ? <Spinner /> : 'Add Application'}</Btn>
          </form>
        </Card>
      )}

      {selected && (
        <div style={{ position: 'fixed', inset: 0, background: '#000000aa', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          onClick={() => setSelected(null)}>
          <div style={{ background: '#1a1a2e', border: '1px solid #4f46e5', borderRadius: 12, padding: 24, maxWidth: 520, width: '90%', maxHeight: '85vh', overflowY: 'auto' }}
            onClick={e => e.stopPropagation()}>
            <Row style={{ marginBottom: 12 }}>
              <h3 style={{ color: '#a5b4fc', flex: 1 }}>{selected.job_title}</h3>
              <Btn size="sm" variant="ghost" onClick={() => setSelected(null)}>✕</Btn>
            </Row>
            <p style={{ color: '#94a3b8', fontSize: 13, marginBottom: 12 }}>{selected.company} · {selected.location}</p>
            <Badge color={STATUS_COLORS[selected.status] || '#64748b'}>{selected.status}</Badge>

            <h5 style={{ color: '#94a3b8', marginTop: 16, marginBottom: 8 }}>Update Status</h5>
            <Row style={{ marginBottom: 8 }}>
              <Select label="" value={newStatus} onChange={setNewStatus}
                options={STATUSES.map(s => ({ value: s, label: s }))}
                style={{ flex: 1, marginBottom: 0 }} />
            </Row>
            <Input label="Reason / note (optional)" value={statusNote} onChange={setStatusNote} placeholder="Got interview invite" />
            <Btn size="sm" onClick={updateStatus} disabled={loading}>Update Status</Btn>

            <h5 style={{ color: '#94a3b8', marginTop: 16, marginBottom: 8 }}>Add Note</h5>
            <Textarea value={newNote} onChange={setNewNote} rows={2} placeholder="Wrote thank-you email..." />
            <Btn size="sm" variant="ghost" onClick={addNote} disabled={loading || !newNote.trim()}>Add Note</Btn>

            <Row style={{ marginTop: 16 }}>
              <Btn size="sm" variant="warning" onClick={() => archive(selected.id)}>Archive</Btn>
              <Btn size="sm" variant="danger" onClick={() => del(selected.id)}>Delete</Btn>
            </Row>

            <details style={{ marginTop: 12 }}>
              <summary style={{ cursor: 'pointer', fontSize: 12, color: '#64748b' }}>Full JSON</summary>
              <Pre>{selected}</Pre>
            </details>
          </div>
        </div>
      )}
    </div>
  )
}
