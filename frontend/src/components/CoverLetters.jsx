import { useState, useEffect } from 'react'
import { coverLetters as clApi } from '../api'
import { Card, Btn, Input, Select, Textarea, Alert, Pre, Badge, Row, SectionTitle, Spinner } from './ui'

const TONES = ['professional', 'friendly', 'concise', 'enthusiastic', 'formal']

export default function CoverLetters({ preselectedJob }) {
  const [list, setList] = useState([])
  const [selected, setSelected] = useState(null)
  const [editing, setEditing] = useState(false)
  const [editContent, setEditContent] = useState('')
  const [genForm, setGenForm] = useState({ job_id: preselectedJob?.id || '', tone: 'professional' })
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')
  const [msg, setMsg] = useState('')

  useEffect(() => { load() }, [])
  useEffect(() => {
    if (preselectedJob) setGenForm(f => ({ ...f, job_id: preselectedJob.id || preselectedJob.external_id || '' }))
  }, [preselectedJob])

  async function load() {
    try { setList(await clApi.list()) } catch {}
  }

  async function generate(e) {
    e.preventDefault(); setErr(''); setLoading(true)
    try {
      const res = await clApi.generate({ job_id: genForm.job_id, tone: genForm.tone })
      setMsg(`Generated! ID: ${res.id}`)
      load(); setSelected(res)
    } catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }

  async function open(id) {
    setLoading(true); setErr('')
    try {
      const d = await clApi.get(id)
      setSelected(d); setEditContent(d.content || ''); setEditing(false)
    } catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }

  async function save() {
    if (!selected) return; setLoading(true)
    try {
      const res = await clApi.update(selected.id, { content: editContent })
      setSelected(res); setEditing(false); setMsg('Saved!')
      load()
    } catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }

  async function del(id) {
    if (!confirm('Delete this cover letter?')) return
    try {
      await clApi.delete(id); setMsg('Deleted!'); load()
      if (selected?.id === id) setSelected(null)
    } catch (e) { setErr(e.message) }
  }

  return (
    <div>
      <SectionTitle>Cover Letters</SectionTitle>

      <Card>
        <h4 style={{ marginBottom: 12, color: '#e2e8f0' }}>Generate</h4>
        <form onSubmit={generate} style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <Input label="Job ID *" value={genForm.job_id} onChange={v => setGenForm(f => ({ ...f, job_id: v }))}
            placeholder="job UUID" style={{ flex: 2, minWidth: 180, marginBottom: 0 }} />
          <Select label="Tone" value={genForm.tone} onChange={v => setGenForm(f => ({ ...f, tone: v }))}
            options={TONES} style={{ flex: 1, minWidth: 130, marginBottom: 0 }} />
          <Btn disabled={loading || !genForm.job_id}>
            {loading ? <Spinner /> : 'Generate'}
          </Btn>
        </form>
        {err && <Alert type="error" style={{ marginTop: 8 }}>{err}</Alert>}
        {msg && <Alert type="success" style={{ marginTop: 8 }}>{msg}</Alert>}
      </Card>

      <div style={{ display: 'flex', gap: 12 }}>
        <div style={{ flex: 1 }}>
          <h5 style={{ color: '#94a3b8', fontSize: 12, marginBottom: 8 }}>All Cover Letters ({list.length})</h5>
          {list.length === 0 && <p style={{ color: '#475569', fontSize: 13 }}>None yet. Generate one above.</p>}
          {(Array.isArray(list) ? list : []).map(cl => (
            <Card key={cl.id} style={{ cursor: 'pointer', border: selected?.id === cl.id ? '1px solid #6366f1' : undefined }}
              onClick={() => open(cl.id)}>
              <Row>
                <div style={{ flex: 1 }}>
                  <div style={{ color: '#e2e8f0', fontSize: 13, fontWeight: 600 }}>
                    {cl.job?.title || cl.job_id?.slice(0, 16) || 'Unknown Job'}
                  </div>
                  <div style={{ color: '#64748b', fontSize: 11 }}>
                    {cl.job?.company_name} · {cl.tone} · {new Date(cl.created_at).toLocaleDateString()}
                  </div>
                </div>
                <Btn size="sm" variant="danger" onClick={e => { e.stopPropagation(); del(cl.id) }}>✕</Btn>
              </Row>
            </Card>
          ))}
        </div>

        {selected && (
          <div style={{ flex: 2, minWidth: 280 }}>
            <Card style={{ border: '1px solid #4f46e5' }}>
              <Row style={{ marginBottom: 8 }}>
                <h4 style={{ color: '#a5b4fc', flex: 1 }}>Cover Letter</h4>
                <Badge color="#6366f1">{selected.tone}</Badge>
                <Btn size="sm" variant="ghost" onClick={() => { setEditing(e => !e); setEditContent(selected.content) }}>
                  {editing ? 'Cancel' : 'Edit'}
                </Btn>
              </Row>
              {editing ? (
                <>
                  <Textarea value={editContent} onChange={setEditContent} rows={16} />
                  <Btn size="sm" onClick={save} disabled={loading}>Save</Btn>
                </>
              ) : (
                <pre style={{
                  whiteSpace: 'pre-wrap', fontSize: 13, color: '#cbd5e1', fontFamily: 'inherit',
                  lineHeight: 1.6, maxHeight: 500, overflowY: 'auto', margin: 0
                }}>
                  {selected.content}
                </pre>
              )}
              <details style={{ marginTop: 10 }}>
                <summary style={{ cursor: 'pointer', fontSize: 11, color: '#475569' }}>Raw JSON</summary>
                <Pre>{selected}</Pre>
              </details>
            </Card>
          </div>
        )}
      </div>
    </div>
  )
}
