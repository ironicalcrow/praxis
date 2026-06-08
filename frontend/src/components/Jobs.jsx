import { useState, useEffect } from 'react'
import { jobs as jobsApi, apps } from '../api'
import { useAuth } from '../AuthContext'
import { Card, Btn, Input, Alert, Badge, Row, SectionTitle, Spinner } from './ui'

// ── Shared Job Detail Modal (exported for Chat.jsx) ───────────────────────────
export function JobDetailModal({ job, loading, onClose, onSelectJob, jobStatus, onAddToApply, onRemove }) {
  if (!job) return null
  const score = job.fit_score?.fit_score
  const scoreColor = score >= 70 ? '#22c55e' : score >= 50 ? '#f59e0b' : '#ef4444'

  return (
    <div
      style={{ position: 'fixed', inset: 0, background: '#000000bb', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}
      onClick={onClose}
    >
      <div
        style={{ background: '#1a1a2e', border: '1px solid #4f46e5', borderRadius: 12, padding: 24, maxWidth: 660, width: '100%', maxHeight: '90vh', overflowY: 'auto' }}
        onClick={e => e.stopPropagation()}
      >
        {/* ── Header ── */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, marginBottom: 10 }}>
          <div style={{ flex: 1 }}>
            <h3 style={{ color: '#e2e8f0', margin: '0 0 4px', fontSize: 18 }}>{job.title}</h3>
            <p style={{ color: '#94a3b8', fontSize: 14, margin: 0 }}>
              {[job.company_name, job.location, job.experience_level].filter(Boolean).join(' · ')}
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
            {loading && <Spinner />}
            <Btn size="sm" variant="ghost" onClick={onClose}>✕</Btn>
          </div>
        </div>

        {/* ── Tracker / CV / Chat badges ── */}
        {jobStatus && (
          <div style={{ display: 'flex', gap: 6, marginBottom: 10, flexWrap: 'wrap' }}>
            {jobStatus.in_tracker && <Badge color="#22c55e">✓ In Tracker</Badge>}
            {jobStatus.has_cover_letter && <Badge color="#6366f1">Cover Letter</Badge>}
            {jobStatus.has_chat && <Badge color="#a78bfa">Has Chat</Badge>}
          </div>
        )}

        {/* ── Salary + Job types ── */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {job.salary && <Badge color="#22c55e">{job.salary}</Badge>}
          {job.is_remote && <Badge color="#3b82f6">Remote</Badge>}
          {(job.job_types || []).map(t => <Badge key={t} color="#6366f1">{t}</Badge>)}
          {job.publisher && <Badge color="#475569">{job.publisher}</Badge>}
        </div>

        {/* ── Dates ── */}
        {(job.posted_at || job.deadline) && (
          <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: 12, color: '#64748b' }}>
            {job.posted_at && <span>Posted: {new Date(job.posted_at).toLocaleDateString()}</span>}
            {job.deadline && <span style={{ color: '#f59e0b' }}>⚠ Deadline: {new Date(job.deadline).toLocaleDateString()}</span>}
          </div>
        )}

        {/* ── Fit Score ── */}
        {job.fit_score && (
          <div style={{ background: '#0f0f1a', borderRadius: 8, padding: '12px 16px', marginTop: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 8 }}>
              <span style={{ fontSize: 32, fontWeight: 800, color: scoreColor, lineHeight: 1 }}>
                {Math.round(score)}%
              </span>
              <span style={{ color: '#94a3b8', fontSize: 14 }}>{job.fit_score.verdict}</span>
            </div>
            {job.fit_score.strengths?.length > 0 && (
              <p style={{ margin: '3px 0', fontSize: 12 }}>
                <span style={{ color: '#22c55e', fontWeight: 600 }}>✓ Matched: </span>
                <span style={{ color: '#94a3b8' }}>{job.fit_score.strengths.slice(0, 7).join(', ')}</span>
              </p>
            )}
            {job.fit_score.weaknesses?.length > 0 && (
              <p style={{ margin: '3px 0', fontSize: 12 }}>
                <span style={{ color: '#ef4444', fontWeight: 600 }}>✗ Missing: </span>
                <span style={{ color: '#94a3b8' }}>{job.fit_score.weaknesses.slice(0, 7).join(', ')}</span>
              </p>
            )}
          </div>
        )}

        {/* ── Skills ── */}
        {job.skills_and_technologies?.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <p style={{ fontSize: 12, color: '#94a3b8', fontWeight: 600, marginBottom: 7, textTransform: 'uppercase', letterSpacing: 0.5 }}>Skills & Technologies</p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {job.skills_and_technologies.map(s => (
                <span key={s} style={{ background: '#1e1e3a', border: '1px solid #2d2d4e', borderRadius: 4, padding: '3px 9px', fontSize: 11, color: '#a5b4fc' }}>{s}</span>
              ))}
            </div>
          </div>
        )}

        {/* ── Description ── */}
        {job.description && (
          <div style={{ marginTop: 16 }}>
            <p style={{ fontSize: 12, color: '#94a3b8', fontWeight: 600, marginBottom: 6, textTransform: 'uppercase', letterSpacing: 0.5 }}>About the Role</p>
            <p style={{ fontSize: 13, color: '#cbd5e1', lineHeight: 1.7, margin: 0 }}>
              {job.description.slice(0, 700)}{job.description.length > 700 ? '…' : ''}
            </p>
          </div>
        )}

        {/* ── Responsibilities ── */}
        {job.responsibilities?.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <p style={{ fontSize: 12, color: '#94a3b8', fontWeight: 600, marginBottom: 6, textTransform: 'uppercase', letterSpacing: 0.5 }}>Responsibilities</p>
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {job.responsibilities.slice(0, 7).map((r, i) => (
                <li key={i} style={{ fontSize: 13, color: '#cbd5e1', marginBottom: 4, lineHeight: 1.5 }}>{r}</li>
              ))}
            </ul>
          </div>
        )}

        {/* ── Qualifications ── */}
        {job.qualifications?.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <p style={{ fontSize: 12, color: '#94a3b8', fontWeight: 600, marginBottom: 6, textTransform: 'uppercase', letterSpacing: 0.5 }}>Qualifications</p>
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {job.qualifications.slice(0, 7).map((q, i) => (
                <li key={i} style={{ fontSize: 13, color: '#cbd5e1', marginBottom: 4, lineHeight: 1.5 }}>{q}</li>
              ))}
            </ul>
          </div>
        )}

        {/* ── Benefits ── */}
        {job.benefits?.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <p style={{ fontSize: 12, color: '#94a3b8', fontWeight: 600, marginBottom: 6, textTransform: 'uppercase', letterSpacing: 0.5 }}>Benefits</p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {job.benefits.map((b, i) => (
                <span key={i} style={{ background: '#22c55e1a', border: '1px solid #22c55e33', borderRadius: 4, padding: '3px 9px', fontSize: 11, color: '#22c55e' }}>{b}</span>
              ))}
            </div>
          </div>
        )}

        {/* ── Apply URLs ── */}
        {job.apply_urls?.length > 0 && (
          <div style={{ marginTop: 18, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {job.apply_urls.slice(0, 3).map((url, i) => (
              <a key={i} href={url} target="_blank" rel="noreferrer"
                style={{ background: '#6366f1', color: '#fff', borderRadius: 6, padding: '8px 18px', fontSize: 13, textDecoration: 'none', fontWeight: 600 }}>
                Apply{job.apply_urls.length > 1 ? ` (${i + 1})` : ''} ↗
              </a>
            ))}
          </div>
        )}

        {/* ── Action ── */}
        {(onSelectJob || onAddToApply || onRemove) && (
          <div style={{ marginTop: 16, paddingTop: 14, borderTop: '1px solid #2d2d4e', display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            {onSelectJob && (
              <Btn size="sm" onClick={() => { onSelectJob(job); onClose() }}>
                Chat / Cover Letter →
              </Btn>
            )}
            {(onAddToApply || onRemove) && (
              jobStatus?.in_tracker ? (
                <>
                  <Badge color="#22c55e">✓ In Applications Board</Badge>
                  {onRemove && jobStatus.application_id && (
                    <Btn size="sm" variant="ghost"
                      onClick={() => { onRemove(jobStatus.application_id, job.id); onClose() }}>
                      Remove
                    </Btn>
                  )}
                </>
              ) : (
                onAddToApply && (
                  <Btn size="sm" onClick={() => { onAddToApply(job); onClose() }}>
                    + Add to Apply
                  </Btn>
                )
              )
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Jobs Tab ──────────────────────────────────────────────────────────────────
export default function Jobs({ onSelectJob }) {
  const { user } = useAuth()
  const [tab, setTab] = useState('search')
  const [query, setQuery] = useState('')
  const [location, setLocation] = useState('')
  const [results, setResults] = useState([])
  const [suggestions, setSuggestions] = useState([])
  const [selected, setSelected] = useState(null)
  const [jobStatus, setJobStatus] = useState(null)
  const [prefs, setPrefs] = useState(null)
  const [prefTypes, setPrefTypes] = useState([])
  const [savedMap, setSavedMap] = useState(new Map())
  const [savedList, setSavedList] = useState([])
  const [savingId, setSavingId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [detailLoading, setDetailLoading] = useState(false)
  const [err, setErr] = useState('')
  const [msg, setMsg] = useState('')

  useEffect(() => {
    if (tab === 'suggest') loadSuggestions()
    if (tab === 'prefs') loadPrefs()
    if (tab === 'saved') loadSaved()
  }, [tab])

  useEffect(() => { if (user) loadSavedMap() }, [user])

  async function search(e) {
    e?.preventDefault(); setErr('')
    if (!query.trim()) return
    setLoading(true)
    try {
      const res = await jobsApi.search({ query, location, page: 1, num_pages: 1 })
      setResults(res.jobs || res || [])
    } catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }

  async function loadSuggestions() {
    setLoading(true)
    try { setSuggestions((await jobsApi.suggest()).jobs || []) }
    catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }

  async function nextSuggestions() {
    setLoading(true)
    try { setSuggestions((await jobsApi.suggestNext()).jobs || []) }
    catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }

  async function openDetail(job) {
    setSelected(job)
    setJobStatus(null)
    setDetailLoading(true)
    setErr('')
    const id = job.id || job.external_id
    try {
      const d = await jobsApi.detail(id)
      setSelected(d)
      try { setJobStatus(await jobsApi.status(d.id || id)) } catch {}
    } catch (e) { setErr(e.message) }
    finally { setDetailLoading(false) }
  }

  async function loadPrefs() {
    try {
      const p = await jobsApi.prefs()
      setPrefs(p)
      setPrefTypes(p.job_types || [])
    } catch {}
  }

  async function savePrefs() {
    setLoading(true)
    try { await jobsApi.updatePrefs({ job_types: prefTypes }); setErr('') }
    catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }

  async function loadSavedMap() {
    if (!user) return
    try {
      const d = await apps.list(user.id)
      const list = d.applications || d || []
      setSavedMap(new Map(list.filter(a => a.job_id).map(a => [a.job_id, a.id])))
    } catch {}
  }

  async function loadSaved() {
    if (!user) return
    setLoading(true)
    try {
      const d = await apps.list(user.id)
      const list = d.applications || d || []
      setSavedList(list)
      setSavedMap(new Map(list.filter(a => a.job_id).map(a => [a.job_id, a.id])))
    } catch (e) { setErr(e.message) }
    finally { setLoading(false) }
  }

  async function addToApply(job) {
    if (!user) return
    const jobId = job.id
    setSavingId(jobId)
    try {
      const app = await apps.fromJob({ user_id: user.id, job })
      const resolvedJobId = app.job_id || jobId
      const appId = app.application_id || app.id
      setSavedMap(m => new Map(m).set(resolvedJobId, appId))
      setMsg('Added to your Applications! Manage status from the Applications board.')
      setTimeout(() => setMsg(''), 4000)
    } catch (e) {
      if (e.message?.includes('409') || e.message?.toLowerCase().includes('already exists')) {
        setMsg('Already in your Applications board.')
        setTimeout(() => setMsg(''), 3000)
      } else {
        setErr(e.message)
      }
    }
    finally { setSavingId(null) }
  }

  async function removeFromSaved(appId, jobId) {
    setSavingId(jobId)
    try {
      await apps.delete(appId, user.id)
      setSavedMap(m => { const n = new Map(m); n.delete(jobId); return n })
      setSavedList(l => l.filter(a => a.id !== appId))
    } catch (e) { setErr(e.message) }
    finally { setSavingId(null) }
  }

  const tabs = ['search', 'suggest', 'saved', 'prefs']
  const jobList = tab === 'search' ? results : suggestions

  return (
    <div>
      <SectionTitle>Jobs</SectionTitle>
      <div style={{ display: 'flex', gap: 4, marginBottom: 16, borderBottom: '1px solid #2d2d4e' }}>
        {tabs.map(t => (
          <button key={t} onClick={() => { setTab(t); setErr(''); setSelected(null) }}
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

      {tab === 'search' && (
        <Card>
          <form onSubmit={search} style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 0 }}>
            <Input label="Query" value={query} onChange={setQuery} placeholder="Backend developer" style={{ flex: 2, minWidth: 180, marginBottom: 0 }} />
            <Input label="Location" value={location} onChange={setLocation} placeholder="Dhaka" style={{ flex: 1, minWidth: 120, marginBottom: 0 }} />
            <Btn size="md" disabled={loading} style={{ alignSelf: 'flex-end' }}>
              {loading ? <Spinner /> : 'Search'}
            </Btn>
          </form>
        </Card>
      )}

      {tab === 'suggest' && (
        <Row style={{ marginBottom: 12 }}>
          <Btn onClick={loadSuggestions} disabled={loading}>Refresh</Btn>
          <Btn onClick={nextSuggestions} variant="ghost" disabled={loading}>Next Window →</Btn>
        </Row>
      )}

      {tab === 'prefs' && prefs && (
        <Card>
          <h4 style={{ marginBottom: 10, color: '#e2e8f0' }}>Job Type Preferences</h4>
          {['Full-time', 'Part-time', 'Contract', 'Internship', 'Remote', 'Hybrid', 'On-site', 'Freelance'].map(t => (
            <label key={t} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, cursor: 'pointer', fontSize: 14 }}>
              <input type="checkbox" checked={prefTypes.includes(t)}
                onChange={e => setPrefTypes(p => e.target.checked ? [...p, t] : p.filter(x => x !== t))} />
              {t}
            </label>
          ))}
          <Btn onClick={savePrefs} disabled={loading}>Save Preferences</Btn>
        </Card>
      )}

      {tab === 'saved' && (
        <div style={{ marginTop: 8 }}>
          {loading && <div style={{ textAlign: 'center', padding: 20 }}><Spinner /></div>}
          {!loading && savedList.length === 0 && (
            <p style={{ color: '#475569', fontSize: 13 }}>No jobs added yet. Browse suggestions and click "+ Add to Apply".</p>
          )}
          {savedList.map(a => (
            <Card key={a.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ flex: 1 }}>
                <strong style={{ color: '#e2e8f0' }}>{a.job_title}</strong>
                <div style={{ color: '#94a3b8', fontSize: 13 }}>
                  {a.company}{a.location ? ` · ${a.location}` : ''}
                </div>
                {a.salary && <div style={{ color: '#22c55e', fontSize: 12 }}>{a.salary}</div>}
                <div style={{ fontSize: 11, color: '#475569', marginTop: 2 }}>
                  Manage status from the Applications board
                </div>
              </div>
              <Btn size="sm" variant="ghost"
                onClick={() => removeFromSaved(a.id, a.job_id)}
                disabled={savingId === a.job_id}>
                {savingId === a.job_id ? '…' : 'Remove'}
              </Btn>
            </Card>
          ))}
        </div>
      )}

      {(tab === 'search' || tab === 'suggest') && (
        <div style={{ marginTop: 8 }}>
          {loading && <div style={{ textAlign: 'center', padding: 20 }}><Spinner /></div>}
          {!loading && jobList.length === 0 && (tab === 'search' ? null : (
            <p style={{ color: '#475569', fontSize: 13 }}>No suggestions yet. Upload a CV first.</p>
          ))}
          {jobList.length > 0 && (
            <>
              <p style={{ fontSize: 12, color: '#64748b', marginBottom: 8 }}>{jobList.length} jobs — click any to view details</p>
              {jobList.map(j => (
                <Card key={j.id || j.external_id || j.title}
                  style={{ cursor: 'pointer', border: selected?.id === j.id ? '1px solid #6366f1' : undefined }}
                  onClick={() => openDetail(j)}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ flex: 1 }}>
                      <strong style={{ color: '#e2e8f0' }}>{j.title}</strong>
                      <div style={{ color: '#94a3b8', fontSize: 13 }}>
                        {j.company_name} · {j.location || 'Remote'}
                        {j.experience_level && <span style={{ color: '#475569' }}> · {j.experience_level}</span>}
                      </div>
                      {j.salary && <div style={{ color: '#22c55e', fontSize: 12, marginTop: 2 }}>{j.salary}</div>}
                      {j.skills_and_technologies?.length > 0 && (
                        <div style={{ marginTop: 5, display: 'flex', flexWrap: 'wrap', gap: 3 }}>
                          {j.skills_and_technologies.slice(0, 5).map(s => (
                            <span key={s} style={{ fontSize: 10, background: '#1e1e3a', border: '1px solid #2d2d4e', borderRadius: 3, padding: '1px 5px', color: '#64748b' }}>{s}</span>
                          ))}
                        </div>
                      )}
                    </div>
                    <div style={{ textAlign: 'right', flexShrink: 0, marginLeft: 8, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
                      {j.fit_score && (
                        <Badge color={j.fit_score.fit_score >= 70 ? '#22c55e' : j.fit_score.fit_score >= 50 ? '#f59e0b' : '#ef4444'}>
                          {Math.round(j.fit_score.fit_score)}% match
                        </Badge>
                      )}
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3, justifyContent: 'flex-end' }}>
                        {(j.job_types || []).slice(0, 2).map(t => <Badge key={t} color="#6366f1">{t}</Badge>)}
                      </div>
                      <button
                        disabled={savingId === j.id || savedMap.has(j.id)}
                        onClick={e => { e.stopPropagation(); addToApply(j) }}
                        style={{
                          fontSize: 11, padding: '3px 8px', borderRadius: 4, cursor: savedMap.has(j.id) ? 'default' : 'pointer',
                          background: savedMap.has(j.id) ? '#22c55e22' : '#1e1e3a',
                          color: savedMap.has(j.id) ? '#22c55e' : '#94a3b8',
                          border: `1px solid ${savedMap.has(j.id) ? '#22c55e55' : '#2d2d4e'}`,
                        }}>
                        {savingId === j.id ? '…' : savedMap.has(j.id) ? '✓ In Board' : '+ Add to Apply'}
                      </button>
                    </div>
                  </div>
                </Card>
              ))}
            </>
          )}
        </div>
      )}

      {/* Detail as overlay modal — over the list */}
      <JobDetailModal
        job={selected}
        loading={detailLoading}
        onClose={() => { setSelected(null); setJobStatus(null) }}
        onSelectJob={onSelectJob}
        jobStatus={jobStatus}
        onAddToApply={addToApply}
        onRemove={removeFromSaved}
      />
    </div>
  )
}
