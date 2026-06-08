import { useState, useEffect } from 'react'
import { cv as cvApi } from '../api'
import { Card, Btn, Alert, Pre, Badge, Row, SectionTitle, Spinner } from './ui'

export default function CVSection() {
  const [parsed, setParsed] = useState(null)
  const [uploads, setUploads] = useState([])
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState(null)

  useEffect(() => { load() }, [])

  async function load() {
    try { setParsed(await cvApi.get()) } catch {}
    try { setUploads(await cvApi.uploads()) } catch {}
  }

  async function upload(e) {
    const file = e.target.files[0]; if (!file) return
    setLoading(true); setMsg(null)
    try {
      const res = await cvApi.upload(file)
      setMsg({ type: 'success', text: `CV uploaded! Resume ID: ${res.resume_id}` })
      await load()
    } catch (err) {
      setMsg({ type: 'error', text: err.message })
    } finally { setLoading(false) }
  }

  async function activate(id) {
    try {
      await cvApi.activate(id)
      setMsg({ type: 'success', text: 'CV version activated!' })
      await load()
    } catch (err) {
      setMsg({ type: 'error', text: err.message })
    }
  }

  return (
    <div>
      <SectionTitle>CV / Resume</SectionTitle>

      <Card>
        <h4 style={{ marginBottom: 10, color: '#e2e8f0' }}>Upload CV</h4>
        <p style={{ color: '#64748b', fontSize: 13, marginBottom: 12 }}>PDF, DOCX, PNG, JPG, JPEG accepted</p>
        <label style={{
          display: 'inline-block', padding: '8px 18px', background: '#6366f1', color: '#fff',
          borderRadius: 6, cursor: 'pointer', fontSize: 14, fontWeight: 500
        }}>
          {loading ? <><Spinner /> Uploading…</> : 'Choose File & Upload'}
          <input type="file" accept=".pdf,.docx,.png,.jpg,.jpeg" onChange={upload} style={{ display: 'none' }} />
        </label>
        {msg && <Alert type={msg.type} style={{ marginTop: 10 }}>{msg.text}</Alert>}
      </Card>

      {parsed && (
        <Card>
          <h4 style={{ marginBottom: 12, color: '#e2e8f0' }}>Parsed CV</h4>
          <Row style={{ marginBottom: 10 }}>
            <span style={{ fontSize: 18, fontWeight: 700 }}>{parsed.name || '—'}</span>
            {parsed.years_of_experience && <Badge color="#22c55e">{parsed.years_of_experience} yrs exp</Badge>}
            {parsed.location && <span style={{ color: '#64748b', fontSize: 13 }}>📍 {parsed.location}</span>}
          </Row>
          {parsed.skills?.length > 0 && (
            <div style={{ marginBottom: 10 }}>
              <strong style={{ fontSize: 12, color: '#94a3b8' }}>Skills:</strong>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 6 }}>
                {parsed.skills.map(s => <Badge key={s} color="#6366f1">{s}</Badge>)}
              </div>
            </div>
          )}
          {parsed.experience?.length > 0 && (
            <div style={{ marginBottom: 10 }}>
              <strong style={{ fontSize: 12, color: '#94a3b8' }}>Experience:</strong>
              {parsed.experience.map((e, i) => (
                <div key={i} style={{ margin: '6px 0', fontSize: 13, color: '#cbd5e1' }}>
                  <strong>{e.role}</strong> @ {e.organization}
                  {e.description && <p style={{ color: '#64748b', marginTop: 2 }}>{e.description.slice(0, 120)}…</p>}
                </div>
              ))}
            </div>
          )}
          {parsed.education?.length > 0 && (
            <div style={{ marginBottom: 10 }}>
              <strong style={{ fontSize: 12, color: '#94a3b8' }}>Education:</strong>
              {parsed.education.map((e, i) => (
                <div key={i} style={{ fontSize: 13, color: '#cbd5e1', margin: '4px 0' }}>
                  {e.degree} — {e.institution} {e.year && `(${e.year})`}
                </div>
              ))}
            </div>
          )}
          {parsed.projects?.length > 0 && (
            <div style={{ marginBottom: 10 }}>
              <strong style={{ fontSize: 12, color: '#94a3b8' }}>Projects:</strong>
              {parsed.projects.map((p, i) => (
                <div key={i} style={{ fontSize: 13, color: '#cbd5e1', margin: '4px 0' }}>
                  <strong>{p.name}</strong>{p.technology && ` (${p.technology})`}
                </div>
              ))}
            </div>
          )}
          <details style={{ marginTop: 10 }}>
            <summary style={{ cursor: 'pointer', fontSize: 12, color: '#64748b' }}>Raw JSON</summary>
            <Pre>{parsed}</Pre>
          </details>
        </Card>
      )}

      {uploads.length > 0 && (
        <Card>
          <h4 style={{ marginBottom: 12, color: '#e2e8f0' }}>Upload History</h4>
          {uploads.map(u => (
            <div key={u.id} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '8px 0', borderBottom: '1px solid #1e1e3a'
            }}>
              <div>
                <span style={{ fontSize: 13, color: '#e2e8f0' }}>{u.original_filename || u.id.slice(0,8)}</span>
                {u.is_active && <Badge color="#22c55e" style={{ marginLeft: 8 }}>Active</Badge>}
                <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>{u.uploaded_at}</div>
              </div>
              {!u.is_active && (
                <Btn size="sm" variant="ghost" onClick={() => activate(u.id)}>Activate</Btn>
              )}
            </div>
          ))}
        </Card>
      )}
    </div>
  )
}
