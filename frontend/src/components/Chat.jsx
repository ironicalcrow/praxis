import { useState, useEffect, useRef } from 'react'
import { chat as chatApi, jobs as jobsApi } from '../api'
import { Card, Btn, Input, Alert, Badge, Row, SectionTitle, Spinner } from './ui'
import { JobDetailModal } from './Jobs'

const TOOL_STATUS_COLORS = {
  handled: '#22c55e',
  confirmation_required: '#f59e0b',
  failed: '#ef4444',
  unsupported: '#64748b',
}

// ── Payload Renderers ──────────────────────────────────────────────────────────

function FitScorePayload({ data }) {
  const score = data.fit_score
  const color = score >= 70 ? '#22c55e' : score >= 50 ? '#f59e0b' : '#ef4444'
  return (
    <div style={{ background: '#0f0f1a', borderRadius: 8, padding: '10px 14px', marginTop: 8 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
        <span style={{ fontSize: 28, fontWeight: 800, color, lineHeight: 1 }}>{Math.round(score)}%</span>
        <span style={{ color: '#94a3b8', fontSize: 13 }}>{data.verdict}</span>
      </div>
      {data.strengths?.length > 0 && (
        <p style={{ margin: '3px 0', fontSize: 12 }}>
          <span style={{ color: '#22c55e', fontWeight: 600 }}>✓ Matched: </span>
          <span style={{ color: '#94a3b8' }}>{data.strengths.slice(0, 7).join(', ')}</span>
        </p>
      )}
      {data.weaknesses?.length > 0 && (
        <p style={{ margin: '3px 0', fontSize: 12 }}>
          <span style={{ color: '#ef4444', fontWeight: 600 }}>✗ Missing: </span>
          <span style={{ color: '#94a3b8' }}>{data.weaknesses.slice(0, 7).join(', ')}</span>
        </p>
      )}
    </div>
  )
}

function JobSearchPayload({ data, onSelectJob }) {
  const [selected, setSelected] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const jobList = data.jobs || []

  async function open(job) {
    setSelected(job)
    setDetailLoading(true)
    try { setSelected(await jobsApi.detail(job.id)) } catch {}
    finally { setDetailLoading(false) }
  }

  return (
    <div style={{ marginTop: 8 }}>
      {jobList.length === 0 && (
        <p style={{ fontSize: 12, color: '#64748b', margin: 0 }}>No jobs found.</p>
      )}
      {jobList.slice(0, 10).map(j => (
        <div key={j.id} onClick={() => open(j)}
          style={{
            cursor: 'pointer', background: '#0f0f1a', borderRadius: 6,
            padding: '7px 10px', marginBottom: 5, border: '1px solid #2d2d4e',
            display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
          }}>
          <div style={{ flex: 1 }}>
            <strong style={{ color: '#e2e8f0', fontSize: 13 }}>{j.title}</strong>
            <div style={{ color: '#94a3b8', fontSize: 11 }}>
              {j.company_name} · {j.location || 'Remote'}
            </div>
            {j.salary && <div style={{ color: '#22c55e', fontSize: 11 }}>{j.salary}</div>}
            {j.skills_and_technologies?.length > 0 && (
              <div style={{ marginTop: 3, display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                {j.skills_and_technologies.slice(0, 4).map(s => (
                  <span key={s} style={{ fontSize: 10, background: '#1e1e3a', border: '1px solid #2d2d4e', borderRadius: 3, padding: '1px 5px', color: '#64748b' }}>{s}</span>
                ))}
              </div>
            )}
          </div>
          {j.fit_score && (
            <Badge color={j.fit_score.fit_score >= 70 ? '#22c55e' : j.fit_score.fit_score >= 50 ? '#f59e0b' : '#ef4444'}>
              {Math.round(j.fit_score.fit_score)}%
            </Badge>
          )}
        </div>
      ))}
      {selected && (
        <JobDetailModal
          job={selected}
          loading={detailLoading}
          onClose={() => setSelected(null)}
          onSelectJob={onSelectJob}
        />
      )}
    </div>
  )
}

function RoadmapPayload({ data }) {
  return (
    <div style={{ background: '#0f0f1a', borderRadius: 8, padding: '10px 14px', marginTop: 8 }}>
      <p style={{ color: '#a5b4fc', fontWeight: 700, margin: '0 0 4px', fontSize: 14 }}>{data.title}</p>
      {data.description && (
        <p style={{ color: '#64748b', fontSize: 12, margin: '0 0 10px' }}>{data.description}</p>
      )}
      {(data.phases || []).map((phase, pi) => (
        <div key={pi} style={{ marginBottom: 10 }}>
          <p style={{ color: '#a5b4fc', fontSize: 13, fontWeight: 600, margin: '0 0 4px' }}>
            Phase {pi + 1}: {phase.title}
          </p>
          <div style={{ marginLeft: 8 }}>
            {(phase.milestones || []).map((m, mi) => (
              <div key={mi} style={{ borderLeft: '2px solid #4f46e5', paddingLeft: 8, marginBottom: 4 }}>
                <span style={{ fontSize: 12, color: '#cbd5e1' }}>{m.title}</span>
                {m.description && (
                  <div style={{ fontSize: 11, color: '#475569' }}>{m.description}</div>
                )}
                {m.estimated_days && (
                  <div style={{ fontSize: 10, color: '#374151' }}>{m.estimated_days}d</div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function RoadmapsPayload({ data }) {
  const list = data.roadmaps || []
  if (!list.length) return <p style={{ fontSize: 12, color: '#64748b', marginTop: 6 }}>No roadmaps yet.</p>
  return (
    <div style={{ marginTop: 8 }}>
      {list.map(r => (
        <div key={r.id} style={{
          background: '#0f0f1a', borderRadius: 6, padding: '7px 10px',
          marginBottom: 5, border: '1px solid #2d2d4e',
        }}>
          <strong style={{ color: '#e2e8f0', fontSize: 13 }}>{r.title}</strong>
          <div style={{ color: '#64748b', fontSize: 11, marginTop: 2 }}>
            {r.phase_count} phase{r.phase_count !== 1 ? 's' : ''} · {r.milestone_count} milestone{r.milestone_count !== 1 ? 's' : ''} · {new Date(r.created_at).toLocaleDateString()}
          </div>
          {r.description && <div style={{ color: '#475569', fontSize: 11, marginTop: 2 }}>{r.description.slice(0, 100)}</div>}
        </div>
      ))}
    </div>
  )
}

function GoalsPayload({ data }) {
  const list = data.goals || []
  const STATUS_COLORS = { not_started: '#94a3b8', in_progress: '#3b82f6', completed: '#22c55e', paused: '#f59e0b' }
  if (!list.length) return <p style={{ fontSize: 12, color: '#64748b', marginTop: 6 }}>No goals yet.</p>
  return (
    <div style={{ marginTop: 8 }}>
      {list.map(g => (
        <div key={g.id} style={{
          background: '#0f0f1a', borderRadius: 6, padding: '6px 10px', marginBottom: 5,
          border: '1px solid #2d2d4e', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div>
            <span style={{ fontSize: 13, color: '#e2e8f0' }}>{g.title}</span>
            {g.target_date && (
              <span style={{ fontSize: 11, color: '#64748b', marginLeft: 8 }}>
                due {new Date(g.target_date).toLocaleDateString()}
              </span>
            )}
          </div>
          <Badge color={STATUS_COLORS[g.status] || '#94a3b8'}>{g.status?.replace('_', ' ')}</Badge>
        </div>
      ))}
    </div>
  )
}

function ApplicationKanbanPayload({ data }) {
  const STATUS_COLORS = { saved: '#6366f1', applied: '#3b82f6', interviewing: '#f59e0b', offer: '#22c55e', rejected: '#ef4444' }
  const statuses = ['saved', 'applied', 'interviewing', 'offer', 'rejected']
  const active = statuses.filter(s => (data[s] || []).length > 0)
  if (!active.length) return <p style={{ fontSize: 12, color: '#64748b', marginTop: 6 }}>No applications yet.</p>
  return (
    <div style={{ marginTop: 8, overflowX: 'auto' }}>
      <div style={{ display: 'flex', gap: 8, minWidth: Math.max(300, active.length * 110) }}>
        {active.map(s => (
          <div key={s} style={{ flex: 1, minWidth: 90 }}>
            <div style={{ fontSize: 11, color: STATUS_COLORS[s], fontWeight: 700, marginBottom: 5, textTransform: 'uppercase', letterSpacing: 0.5 }}>
              {s} ({(data[s] || []).length})
            </div>
            {(data[s] || []).slice(0, 4).map(a => (
              <div key={a.id} style={{
                background: '#0f0f1a', borderRadius: 4, padding: '4px 7px', marginBottom: 4,
                fontSize: 11, border: '1px solid #2d2d4e',
              }}>
                <div style={{ color: '#cbd5e1', fontWeight: 600 }}>{a.job_title}</div>
                <div style={{ color: '#475569' }}>{a.company}</div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

function ApplicationPayload({ data }) {
  const STATUS_COLORS = { saved: '#6366f1', applied: '#3b82f6', interviewing: '#f59e0b', offer: '#22c55e', rejected: '#ef4444' }
  return (
    <div style={{
      background: '#0f0f1a', borderRadius: 8, padding: '10px 14px', marginTop: 8,
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    }}>
      <div>
        <p style={{ color: '#e2e8f0', fontWeight: 600, fontSize: 13, margin: 0 }}>{data.job_title}</p>
        <p style={{ color: '#64748b', fontSize: 12, margin: '2px 0 0' }}>
          {[data.company, data.location].filter(Boolean).join(' · ')}
        </p>
      </div>
      <Badge color={STATUS_COLORS[data.status] || '#94a3b8'}>{data.status}</Badge>
    </div>
  )
}

function CoverLetterPayload({ data }) {
  const [copied, setCopied] = useState(false)
  function copy() {
    navigator.clipboard.writeText(data.content || '').catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <div style={{ background: '#0f0f1a', borderRadius: 8, padding: '10px 14px', marginTop: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontSize: 12, color: '#94a3b8', fontWeight: 600 }}>
          Cover Letter{data.tone ? ` · ${data.tone}` : ''}
        </span>
        <button onClick={copy}
          style={{ fontSize: 11, color: copied ? '#22c55e' : '#6366f1', background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
          {copied ? '✓ Copied' : 'Copy'}
        </button>
      </div>
      <pre style={{
        fontSize: 12, color: '#cbd5e1', whiteSpace: 'pre-wrap', maxHeight: 240,
        overflow: 'auto', margin: 0, fontFamily: 'inherit', lineHeight: 1.65,
      }}>
        {data.content}
      </pre>
    </div>
  )
}

function PayloadRenderer({ type, data, onSelectJob }) {
  if (!type || !data) return null
  switch (type) {
    case 'job_search_results': return <JobSearchPayload data={data} onSelectJob={onSelectJob} />
    case 'fit_score': return <FitScorePayload data={data} />
    case 'roadmap': return <RoadmapPayload data={data} />
    case 'roadmaps': return <RoadmapsPayload data={data} />
    case 'goals': return <GoalsPayload data={data} />
    case 'application_kanban': return <ApplicationKanbanPayload data={data} />
    case 'application':
    case 'application_status': return <ApplicationPayload data={data} />
    case 'cover_letter': return <CoverLetterPayload data={data} />
    default: return null
  }
}

// ── Message ────────────────────────────────────────────────────────────────────

function Message({ m, onSelectJob }) {
  const isUser = m.role === 'user'
  return (
    <div style={{
      display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start',
      marginBottom: 10, padding: '0 8px',
    }}>
      <div className="animate-slide-up" style={{
        background: isUser ? 'var(--gradient-primary)' : 'rgba(0, 0, 0, 0.4)',
        border: isUser ? 'none' : '1px solid var(--border-subtle)',
        color: isUser ? '#fff' : 'var(--text-main)',
        padding: '14px 18px', borderRadius: 16,
        borderBottomRightRadius: isUser ? 4 : 16, borderBottomLeftRadius: !isUser ? 4 : 16,
        maxWidth: '85%', fontSize: 14, lineHeight: 1.6,
        boxShadow: isUser ? '0 4px 14px rgba(14, 165, 233, 0.2)' : 'none'
      }}>
        <div style={{ whiteSpace: 'pre-wrap' }}>{m.content}</div>

        {!isUser && m.ui_payload && (
          <PayloadRenderer type={m.ui_payload.type} data={m.ui_payload.data} onSelectJob={onSelectJob} />
        )}

        {m.tool_status && m.tool_status !== 'handled' && (
          <div style={{ marginTop: 6 }}>
            <Badge color={TOOL_STATUS_COLORS[m.tool_status] || '#64748b'}>{m.tool_status}</Badge>
          </div>
        )}

        {m.notification?.created && (
          <div style={{ fontSize: 11, color: '#22c55e', marginTop: 4 }}>✓ notification sent</div>
        )}

        {m.created_at && (
          <div style={{ fontSize: 10, color: isUser ? '#a5b4fc' : '#475569', marginTop: 4 }}>
            {new Date(m.created_at).toLocaleTimeString()}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Chat ───────────────────────────────────────────────────────────────────────

export default function Chat({ preselectedJob }) {
  const [mode, setMode] = useState(preselectedJob ? 'job' : 'general')
  const [jobId, setJobId] = useState(preselectedJob?.id || '')
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')
  const [sessions, setSessions] = useState([])
  const scrollRef = useRef(null)

  useEffect(() => {
    if (preselectedJob) {
      setMode('job')
      setJobId(preselectedJob.id || preselectedJob.external_id || '')
    }
  }, [preselectedJob])

  useEffect(() => { loadHistory() }, [mode, jobId])

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function loadHistory() {
    setErr('')
    try {
      let hist
      if (mode === 'job' && jobId) hist = await chatApi.historyJob(jobId, 30)
      else if (mode === 'general') hist = await chatApi.history(30)
      if (hist) setMessages((hist.messages || hist || []).reverse())
    } catch (e) { setErr(e.message) }
  }

  async function loadSessions() {
    try {
      const s = mode === 'job' && jobId
        ? await chatApi.sessionsJob(jobId)
        : await chatApi.sessions()
      setSessions(s.sessions || s || [])
    } catch {}
  }

  async function send(e) {
    e?.preventDefault()
    if (!input.trim() || loading) return
    const userMsg = { role: 'user', content: input, created_at: new Date().toISOString() }
    setMessages(m => [...m, userMsg])
    const text = input
    setInput(''); setLoading(true); setErr('')
    try {
      const res = mode === 'job' && jobId
        ? await chatApi.sendJob(jobId, { content: text })
        : await chatApi.send({ content: text })
      setMessages(m => [...m, {
        role: 'assistant',
        content: res.content,
        created_at: res.created_at,
        tool_status: res.tool_status,
        ui_payload: res.ui_payload,
        notification: res.notification,
      }])
    } catch (e) {
      setErr(e.message)
      setMessages(m => m.slice(0, -1))
    } finally { setLoading(false) }
  }

  function switchToJobChat(job) {
    setMode('job')
    setJobId(job.id || job.external_id || '')
    setMessages([])
  }

  const SUGGESTIONS = ['Find me backend jobs', 'Show my applications', 'What are my goals?', 'Show my roadmaps']

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <SectionTitle>Chat</SectionTitle>

      <Card>
        <Row style={{ flexWrap: 'nowrap', gap: 8 }}>
          <div>
            <label style={{ fontSize: 12, color: '#94a3b8', display: 'block', marginBottom: 3 }}>Mode</label>
            <div style={{ display: 'flex', gap: 4 }}>
              {['general', 'job'].map(m => (
                <button key={m} onClick={() => { setMode(m); setMessages([]) }}
                  style={{
                    padding: '4px 10px', borderRadius: 4, border: 'none', cursor: 'pointer', fontSize: 12,
                    background: mode === m ? '#6366f1' : '#1e1e3a',
                    color: mode === m ? '#fff' : '#94a3b8', fontWeight: mode === m ? 700 : 400,
                  }}>
                  {m}
                </button>
              ))}
            </div>
          </div>
          {mode === 'job' && (
            <Input label="Job ID" value={jobId} onChange={setJobId} placeholder="paste job ID"
              style={{ flex: 1, marginBottom: 0 }} />
          )}
          <Btn size="sm" variant="ghost" onClick={loadHistory} disabled={loading} style={{ alignSelf: 'flex-end' }}>
            Reload
          </Btn>
          <Btn size="sm" variant="ghost" onClick={loadSessions} style={{ alignSelf: 'flex-end' }}>
            Sessions
          </Btn>
        </Row>
        {sessions.length > 0 && (
          <div style={{ marginTop: 8, maxHeight: 80, overflowY: 'auto' }}>
            {sessions.map(s => (
              <div key={s.id} style={{ fontSize: 11, color: '#64748b', padding: '1px 0' }}>
                {s.id.slice(0, 16)} — {new Date(s.created_at).toLocaleString()}
                {s.session_summary && (
                  <span style={{ color: '#475569' }}> · {s.session_summary.slice(0, 60)}…</span>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      {err && <Alert type="error">{err}</Alert>}

      <div style={{
        flex: 1, overflowY: 'auto', minHeight: 300, maxHeight: 500, padding: '8px 0',
        border: '1px solid #2d2d4e', borderRadius: 8, background: '#0f0f1a',
        marginBottom: 10,
      }}>
        {messages.length === 0 && (
          <div style={{ color: '#475569', fontSize: 13, textAlign: 'center', padding: 40 }}>
            {mode === 'general' ? 'Ask about your career, jobs, goals…' : `Chatting about job ${jobId}`}
          </div>
        )}
        {messages.map((m, i) => (
          <Message key={i} m={m} onSelectJob={switchToJobChat} />
        ))}
        {loading && (
          <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 10, padding: '0 8px' }}>
            <div style={{ padding: '9px 13px', background: '#1e1e3a', borderRadius: 10 }}>
              <Spinner />
            </div>
          </div>
        )}
        <div ref={scrollRef} />
      </div>

      <div className="glass-panel" style={{
        marginTop: 16, padding: 12, display: 'flex', gap: 10,
        position: 'sticky', bottom: 20
      }}>
        <textarea
          value={input} onChange={e => setInput(e.target.value)}
          placeholder="Ask me anything..."
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
          style={{
            flex: 1, background: 'rgba(0, 0, 0, 0.2)', border: '1px solid var(--border-strong)', borderRadius: 8,
            color: 'var(--text-main)', padding: '12px 16px', fontSize: 14, outline: 'none', resize: 'none',
            height: 48, transition: 'all 0.2s', fontFamily: 'inherit'
          }}
        />
        <Btn onClick={send} disabled={!input.trim() || loading} style={{ height: 48, borderRadius: 8 }}>
          {loading ? <Spinner /> : 'Send'}
        </Btn>
      </div>

      <div style={{ marginTop: 8, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {SUGGESTIONS.map(s => (
          <button key={s} onClick={() => setInput(s)}
            style={{
              fontSize: 11, padding: '3px 8px', background: '#1e1e3a', border: '1px solid #2d2d4e',
              borderRadius: 4, color: '#64748b', cursor: 'pointer',
            }}>
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}
