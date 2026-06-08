import { useState, useEffect } from 'react'
import { roadmaps as rmApi, goals as goalsApi } from '../api'
import { Card, Btn, Input, Textarea, Alert, Pre, Badge, Row, SectionTitle, Spinner } from './ui'

export default function Roadmaps() {
  const [list, setList] = useState([])
  const [selected, setSelected] = useState(null)
  const [tab, setTab] = useState('list')
  const [form, setForm] = useState({ title: '', conversation_id: '', job_id: '' })
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')
  const [msg, setMsg] = useState('')

  useEffect(() => { load() }, [])

  async function load() {
    try { setList(await rmApi.list()) } catch {}
  }

  async function open(id) {
    setLoading(true); setErr('')
    try { setSelected(await rmApi.get(id)) }
    catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }

  async function fromConversation(e) {
    e.preventDefault(); setLoading(true); setErr('')
    try {
      const res = await rmApi.fromConversation({
        conversation_id: form.conversation_id || undefined,
        title: form.title || undefined
      })
      setMsg(`Roadmap created: ${res.title}`)
      load(); setSelected(res); setTab('list')
    } catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }

  async function fromJob(e) {
    e.preventDefault(); setLoading(true); setErr('')
    try {
      const res = await rmApi.fromJob({ job_id: form.job_id, title: form.title || undefined })
      setMsg(`Roadmap created: ${res.title}`)
      load(); setSelected(res); setTab('list')
    } catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }

  async function createGoalsFromRoadmap(id) {
    setLoading(true)
    try {
      const res = await goalsApi.fromRoadmap(id)
      setMsg(`Created ${res.goals?.length || 0} goals from roadmap!`)
    } catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }

  async function del(id) {
    if (!confirm('Delete this roadmap?')) return
    try {
      await rmApi.delete(id); setMsg('Deleted!'); load()
      if (selected?.id === id) setSelected(null)
    } catch (e) { setErr(e.message) }
  }

  const set = (k) => (v) => setForm(f => ({ ...f, [k]: v }))
  const tabs = ['list', 'from-conversation', 'from-job']

  return (
    <div>
      <SectionTitle>Roadmaps</SectionTitle>
      <div style={{ display: 'flex', gap: 4, marginBottom: 16, borderBottom: '1px solid #2d2d4e' }}>
        {tabs.map(t => (
          <button key={t} onClick={() => { setTab(t); setErr(''); setMsg('') }}
            style={{
              padding: '7px 14px', background: 'none', border: 'none', cursor: 'pointer',
              color: tab === t ? '#a5b4fc' : '#64748b', borderBottom: tab === t ? '2px solid #6366f1' : '2px solid transparent',
              fontSize: 13, fontWeight: tab === t ? 700 : 400
            }}>
            {t}
          </button>
        ))}
      </div>

      {err && <Alert type="error">{err}</Alert>}
      {msg && <Alert type="success">{msg}</Alert>}

      {tab === 'from-conversation' && (
        <Card>
          <h4 style={{ marginBottom: 12, color: '#e2e8f0' }}>Generate from Conversation</h4>
          <form onSubmit={fromConversation}>
            <Input label="Conversation ID (optional)" value={form.conversation_id} onChange={set('conversation_id')} placeholder="leave blank for latest" />
            <Input label="Title (optional)" value={form.title} onChange={set('title')} placeholder="My Learning Path" />
            <Btn disabled={loading}>{loading ? <Spinner /> : 'Generate Roadmap'}</Btn>
          </form>
        </Card>
      )}

      {tab === 'from-job' && (
        <Card>
          <h4 style={{ marginBottom: 12, color: '#e2e8f0' }}>Generate from Job</h4>
          <form onSubmit={fromJob}>
            <Input label="Job ID *" value={form.job_id} onChange={set('job_id')} placeholder="job UUID" />
            <Input label="Title (optional)" value={form.title} onChange={set('title')} placeholder="Backend Engineer Path" />
            <Btn disabled={loading || !form.job_id}>{loading ? <Spinner /> : 'Generate Roadmap'}</Btn>
          </form>
        </Card>
      )}

      {tab === 'list' && (
        <div style={{ display: 'flex', gap: 12 }}>
          <div style={{ flex: 1 }}>
            {list.length === 0 && <p style={{ color: '#475569', fontSize: 13 }}>No roadmaps yet. Generate one first.</p>}
            {(Array.isArray(list) ? list : []).map(r => (
              <Card key={r.id} style={{ cursor: 'pointer', border: selected?.id === r.id ? '1px solid #6366f1' : undefined }}
                onClick={() => open(r.id)}>
                <Row>
                  <div style={{ flex: 1 }}>
                    <strong style={{ color: '#e2e8f0' }}>{r.title}</strong>
                    <div style={{ color: '#64748b', fontSize: 12 }}>
                      {r.phases?.length || 0} phases · {new Date(r.created_at).toLocaleDateString()}
                    </div>
                  </div>
                  <Btn size="sm" variant="danger" onClick={e => { e.stopPropagation(); del(r.id) }}>✕</Btn>
                </Row>
              </Card>
            ))}
          </div>

          {selected && (
            <div style={{ flex: 2, minWidth: 260 }}>
              <Card style={{ border: '1px solid #4f46e5' }}>
                <Row style={{ marginBottom: 8 }}>
                  <h4 style={{ color: '#a5b4fc', flex: 1 }}>{selected.title}</h4>
                  <Btn size="sm" variant="ghost" onClick={() => setSelected(null)}>✕</Btn>
                </Row>
                {selected.description && (
                  <p style={{ color: '#64748b', fontSize: 13, marginBottom: 10 }}>{selected.description}</p>
                )}
                <Btn size="sm" variant="success" onClick={() => createGoalsFromRoadmap(selected.id)} disabled={loading}>
                  Create Goals from Roadmap
                </Btn>

                {(selected.phases || []).map((phase, pi) => (
                  <div key={pi} style={{ marginTop: 14 }}>
                    <h5 style={{ color: '#a5b4fc', marginBottom: 6 }}>Phase {pi + 1}: {phase.title}</h5>
                    {phase.description && <p style={{ color: '#64748b', fontSize: 12 }}>{phase.description}</p>}
                    <div style={{ marginLeft: 12 }}>
                      {(phase.milestones || []).map((m, mi) => (
                        <div key={mi} style={{
                          padding: '4px 8px', marginBottom: 4,
                          borderLeft: '2px solid #4f46e5', fontSize: 12, color: '#cbd5e1'
                        }}>
                          <strong>{m.title}</strong>
                          {m.description && <div style={{ color: '#64748b' }}>{m.description}</div>}
                          {m.resource_url && (
                            <a href={m.resource_url} target="_blank" rel="noreferrer"
                              style={{ color: '#6366f1', fontSize: 11 }}>
                              Resource ↗
                            </a>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
                <details style={{ marginTop: 10 }}>
                  <summary style={{ cursor: 'pointer', fontSize: 11, color: '#475569' }}>Raw JSON</summary>
                  <Pre>{selected}</Pre>
                </details>
              </Card>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
