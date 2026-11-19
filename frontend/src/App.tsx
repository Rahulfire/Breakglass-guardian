import { useEffect, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { NavLink, Route, Routes } from 'react-router-dom'
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  CircleUserRound,
  Clock3,
  KeyRound,
  LayoutDashboard,
  LockKeyhole,
  LogOut,
  Menu,
  ShieldCheck,
  ShieldX,
  TerminalSquare,
  XCircle,
} from 'lucide-react'
import {
  api,
  getToken,
  setToken,
} from './api'
import type {
  Approval,
  AccessRequestInput,
  AccessSession,
  AuditEvent,
  AuditStatistics,
  SecurityAlert,
  AuthRole,
} from './api'

type LoadState = 'loading' | 'ready' | 'error'

function StatusBadge({ status }: { status: string }) {
  const value = status.toLowerCase()
  const tone =
    value.includes('approved') || value.includes('active') || value.includes('success')
      ? 'success'
      : value.includes('reject') || value.includes('blocked') || value.includes('critical') || value.includes('failed')
        ? 'danger'
        : value.includes('pending') || value.includes('creating') || value.includes('medium') || value.includes('warning')
          ? 'warning'
          : 'neutral'
  return <span className={`status-badge ${tone}`}><i />{status.replaceAll('_', ' ')}</span>
}

function Sidebar({ open, setOpen }: { open: boolean; setOpen: (open: boolean) => void }) {
  const items = [
    { to: '/', label: 'Overview', icon: LayoutDashboard },
    { to: '/requests', label: 'Emergency requests', icon: TerminalSquare },
    { to: '/approvals', label: 'Approvals', icon: ShieldCheck },
    { to: '/sessions', label: 'Active sessions', icon: KeyRound },
    { to: '/audit', label: 'Security audit', icon: Activity },
  ]
  return (
    <>
      {open && <button className="sidebar-backdrop" aria-label="Close menu" onClick={() => setOpen(false)} />}
      <aside className={open ? 'sidebar open' : 'sidebar'}>
        <div className="brand">
          <div className="brand-mark"><ShieldCheck size={21} /></div>
          <div><strong>BreakGlass</strong><span>Guardian</span></div>
        </div>
        <nav>
          <span className="nav-label">Control plane</span>
          {items.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === '/'} onClick={() => setOpen(false)}>
              <Icon size={18} /><span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-status">
          <div className="status-row"><span className="pulse" /><span>Systems operational</span></div>
          <small>Regional control plane</small>
        </div>
      </aside>
    </>
  )
}

function Header({ onMenu }: { onMenu: () => void }) {
  return (
    <header className="topbar">
      <button className="menu-button" onClick={onMenu} aria-label="Open menu"><Menu size={20} /></button>
      <div className="environment">
        <span className="env-dot" />
        <div><small>Environment</small><strong>AWS production sandbox</strong></div>
      </div>
      <div className="top-actions">
        <div className="account-chip"><CircleUserRound size={18} /><div><small>Signed identity</small><strong>Admin session</strong></div></div>
      </div>
    </header>
  )
}

function TokenGate({ onReady }: { onReady: () => void }) {
  const [token, setTokenValue] = useState(getToken())
  const [message, setMessage] = useState('')
  const [identity, setIdentity] = useState('engineer@company.com')
  const [role, setRole] = useState<AuthRole>('requester')

  async function createLocalToken() {
    try {
      const result = await api.createDevelopmentToken(identity, [role, 'internal'])
      setTokenValue(result.access_token)
      setToken(result.access_token)
      setMessage(`Local ${role} identity ready.`)
      onReady()
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : 'Local login failed')
    }
  }

  async function saveToken(event: FormEvent) {
    event.preventDefault()
    setToken(token.trim())
    setMessage(token.trim() ? 'Development identity token saved.' : 'Token cleared.')
    onReady()
  }
  return (
    <form className="token-gate" onSubmit={saveToken}>
      <LockKeyhole size={16} />
      <input
        type="email"
        value={identity}
        onChange={(event) => setIdentity(event.target.value)}
        placeholder="Development identity"
        aria-label="Development identity"
      />
      <select value={role} onChange={(event) => setRole(event.target.value as AuthRole)} aria-label="Development role">
        <option value="requester">Requester</option>
        <option value="approver">Approver</option>
        <option value="admin">Admin</option>
      </select>
      <button type="button" onClick={() => void createLocalToken()}>Create local token</button>
      <input
        type="password"
        value={token}
        onChange={(event) => setTokenValue(event.target.value)}
        placeholder="Bearer JWT"
        aria-label="Bearer JWT"
      />
      <button type="submit">Apply</button>
      {message && <span>{message}</span>}
    </form>
  )
}

function PageHeading({ eyebrow, title, description, action }: {
  eyebrow: string
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <div className="page-heading">
      <div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>
      {action}
    </div>
  )
}

function MetricCard({ label, value, detail, icon: Icon, tone = 'blue' }: {
  label: string
  value: number | string
  detail: string
  icon: typeof Activity
  tone?: 'blue' | 'green' | 'amber' | 'red'
}) {
  return (
    <article className={`metric-card ${tone}`}>
      <div className="metric-icon"><Icon size={20} /></div>
      <div><span>{label}</span><strong>{value}</strong><small>{detail}</small></div>
    </article>
  )
}

function Overview() {
  const [stats, setStats] = useState<AuditStatistics>()
  const [pending, setPending] = useState<Approval[]>([])
  const [sessions, setSessions] = useState<AccessSession[]>([])
  const [alerts, setAlerts] = useState<SecurityAlert[]>([])
  const [state, setState] = useState<LoadState>('loading')
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      api.getAuditStatistics(),
      api.getPendingApprovals(),
      api.getSessions(),
      api.getAuditAlerts(),
    ]).then(([audit, approval, sessionList, alertList]) => {
      setStats(audit)
      setPending(approval.approvals)
      setSessions(sessionList.sessions)
      setAlerts(alertList)
      setState('ready')
    }).catch((caught) => {
      setError(caught instanceof Error ? caught.message : 'Unable to load dashboard')
      setState('error')
    })
  }, [])

  return (
    <>
      <PageHeading eyebrow="Security operations" title="Control overview"
        description="Emergency access posture across requests, approvals, sessions and audit events." />
      {state === 'error' && <div className="error-banner"><AlertTriangle size={18} />{error}</div>}
      {state === 'loading' && <div className="loading-grid">{[1,2,3,4].map((n) => <div key={n} className="skeleton" />)}</div>}
      {state === 'ready' && <>
        <div className="metric-grid">
          <MetricCard label="Total requests" value={stats?.total_events || 0} detail="All tracked events" icon={TerminalSquare} />
          <MetricCard label="Pending approvals" value={pending.length} detail="Requires human review" icon={Clock3} tone="amber" />
          <MetricCard label="Active sessions" value={sessions.filter((item) => item.status === 'active').length} detail="Temporary AWS access" icon={KeyRound} tone="green" />
          <MetricCard label="Security alerts" value={stats?.security_alerts || alerts.length} detail={`${stats?.blocked_attempts || 0} blocked attempts`} icon={ShieldX} tone="red" />
        </div>
        <div className="dashboard-grid">
          <section className="panel approval-panel">
            <div className="panel-heading"><div><span>Review queue</span><h2>Pending approvals</h2></div><span className="count-chip">{pending.length}</span></div>
            {pending.length === 0 ? <div className="empty-state"><CheckCircle2 size={28} /><strong>No pending approvals</strong><span>The review queue is clear.</span></div> :
              pending.slice(0, 5).map((approval) => (
                <div className="approval-row" key={approval.approval_id}>
                  <div className="resource-icon"><TerminalSquare size={18} /></div>
                  <div className="approval-copy"><strong>{approval.resource_type.toUpperCase()} · {approval.resource_id}</strong><span>{approval.requester_email}</span></div>
                  <StatusBadge status={approval.risk_classification} />
                  <ChevronRight size={18} />
                </div>
              ))}
          </section>
          <section className="panel posture-panel">
            <div className="panel-heading"><div><span>Security posture</span><h2>Last 24 hours</h2></div></div>
            <div className="posture-ring">
              <div className="ring"><strong>{stats?.events_last_24h || 0}</strong><span>events</span></div>
              <div className="posture-list">
                <div><span className="legend blue" /><span>Informational</span><strong>{stats?.events_by_severity?.info || 0}</strong></div>
                <div><span className="legend amber" /><span>Warnings</span><strong>{stats?.events_by_severity?.warning || 0}</strong></div>
                <div><span className="legend red" /><span>Critical</span><strong>{stats?.events_by_severity?.critical || 0}</strong></div>
              </div>
            </div>
          </section>
        </div>
      </>}
    </>
  )
}

function RequestsPage() {
  const [items, setItems] = useState<Awaited<ReturnType<typeof api.getRequests>>['requests']>([])
  const [state, setState] = useState<LoadState>('loading')
  const [error, setError] = useState('')
  const [open, setOpen] = useState(false)

  async function load() {
    setState('loading')
    try {
      const data = await api.getRequests()
      setItems(data.requests)
      setState('ready')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to load requests')
      setState('error')
    }
  }
  useEffect(() => { void load() }, [])
  return (
    <>
      <PageHeading eyebrow="Emergency access" title="Access requests"
        description="Submit and investigate narrowly scoped AWS emergency access requests."
        action={<button className="primary-button" onClick={() => setOpen(true)}>New request</button>} />
      {error && <div className="error-banner"><AlertTriangle size={18} />{error}</div>}
      {open && <RequestModal onClose={() => setOpen(false)} onCreated={load} />}
      {state === 'loading' ? <div className="table-skeleton" /> :
        <section className="panel table-panel">
          <div className="table-wrap">
            <table><thead><tr><th>Request</th><th>Requester</th><th>Resource</th><th>Risk</th><th>Status</th><th>Submitted</th></tr></thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.request.request_id}>
                    <td><strong>{item.request.request_id}</strong><span>{item.request.requested_action}</span></td>
                    <td>{item.request.requester_email}</td>
                    <td><strong>{item.request.resource_type.toUpperCase()}</strong><span>{item.request.resource_id}</span></td>
                    <td><StatusBadge status={item.agent_analysis?.risk_classification || 'pending'} /></td>
                    <td><StatusBadge status={item.request.status} /></td>
                    <td>{item.request.created_at ? new Date(item.request.created_at).toLocaleString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {items.length === 0 && <div className="empty-state"><TerminalSquare size={28} /><strong>No requests found</strong><span>Create the first emergency request.</span></div>}
          </div>
        </section>}
    </>
  )
}

function RequestModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<Awaited<ReturnType<typeof api.submitRequest>>>()
  const [form, setForm] = useState<AccessRequestInput>({
    requester_email: 'engineer@company.com',
    requester_name: 'John Engineer',
    emergency_description: '',
    resource_type: 'dynamodb',
    resource_id: 'breakglass-audit-dev',
    resource_region: 'us-east-1',
    requested_action: 'read_table',
    duration_minutes: 30,
    business_justification: '',
  })

  function update<K extends keyof AccessRequestInput>(key: K, value: AccessRequestInput[K]) {
    setForm((current) => ({ ...current, [key]: value }))
  }
  async function submit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      const created = await api.submitRequest(form)
      setResult(created)
      onCreated()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Request submission failed')
    } finally {
      setSubmitting(false)
    }
  }
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal request-modal">
        <div className="modal-heading"><div><span>Emergency access</span><h2>New access request</h2></div><button onClick={onClose} aria-label="Close"><XCircle size={22} /></button></div>
        {result ? (
          <div className="created-result">
            <CheckCircle2 size={34} />
            <h3>Request submitted</h3>
            <p>{result.request.request_id}</p>
            <StatusBadge status={result.request.status} />
            <button className="primary-button" onClick={onClose}>Done</button>
          </div>
        ) : (
          <form onSubmit={submit} className="form-grid">
            {error && <div className="error-banner"><AlertTriangle size={18} />{error}</div>}
            <label>Requester email<input type="email" required value={form.requester_email} onChange={(event) => update('requester_email', event.target.value)} /></label>
            <label>Requester name<input required value={form.requester_name} onChange={(event) => update('requester_name', event.target.value)} /></label>
            <label>Resource type<select value={form.resource_type} onChange={(event) => update('resource_type', event.target.value as AccessRequestInput['resource_type'])}><option value="ec2">EC2</option><option value="s3">S3</option><option value="lambda">Lambda</option><option value="dynamodb">DynamoDB</option><option value="rds">RDS</option></select></label>
            <label>Resource identifier<input required value={form.resource_id} onChange={(event) => update('resource_id', event.target.value)} /></label>
            <label>Region<input required value={form.resource_region} onChange={(event) => update('resource_region', event.target.value)} /></label>
            <label>Requested action<input required value={form.requested_action} onChange={(event) => update('requested_action', event.target.value)} /></label>
            <label>Duration (minutes)<input type="number" min="5" max="120" required value={form.duration_minutes} onChange={(event) => update('duration_minutes', Number(event.target.value))} /></label>
            <label className="span-two">Emergency description<textarea required minLength={10} value={form.emergency_description} onChange={(event) => update('emergency_description', event.target.value)} /></label>
            <label className="span-two">Business justification<textarea required minLength={10} value={form.business_justification} onChange={(event) => update('business_justification', event.target.value)} /></label>
            <div className="form-actions span-two"><button type="button" className="secondary-button" onClick={onClose}>Cancel</button><button className="primary-button" type="submit" disabled={submitting}>{submitting ? 'Submitting...' : 'Submit request'}</button></div>
          </form>
        )}
      </div>
    </div>
  )
}

function ApprovalsPage() {
  const [items, setItems] = useState<Approval[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')

  async function load() {
    try { setItems((await api.getPendingApprovals()).approvals); setError('') }
    catch (caught) { setError(caught instanceof Error ? caught.message : 'Unable to load approvals') }
  }
  useEffect(() => { void load() }, [])

  async function decide(item: Approval, decision: 'APPROVED' | 'REJECTED') {
    setBusy(item.approval_id)
    setError('')
    try {
      await api.decideApproval(item.approval_id, {
        approval_id: item.approval_id,
        approver_email: 'admin@company.com',
        approver_name: 'Admin User',
        decision,
        reason: decision === 'APPROVED'
          ? 'Emergency access is justified, narrowly scoped and suitable for approval.'
          : 'Request rejected after security review.',
        mfa_verified: true,
      })
      await load()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Approval decision failed')
    } finally {
      setBusy('')
    }
  }

  return (
    <>
      <PageHeading eyebrow="Human oversight" title="Approval management"
        description="Independent review for privileged temporary access." />
      {error && <div className="error-banner"><AlertTriangle size={18} />{error}</div>}
      <section className="approval-cards">
        {items.map((item) => (
          <article className="approval-card" key={item.approval_id}>
            <div className="approval-card-head"><div className="resource-icon"><TerminalSquare size={20} /></div><div><strong>{item.resource_type.toUpperCase()} · {item.resource_id}</strong><span>{item.requester_name} · {item.requester_email}</span></div><StatusBadge status={item.risk_classification} /></div>
            <p>{item.emergency_description}</p>
            <div className="approval-meta"><div><small>Requested action</small><strong>{item.requested_action}</strong></div><div><small>Duration</small><strong>{item.duration_minutes} minutes</strong></div><div><small>Expires</small><strong>{new Date(item.expires_at).toLocaleString()}</strong></div></div>
            <div className="permission-list"><small>Recommended permissions</small>{item.recommended_permissions.map((permission) => <span key={permission}>{permission}</span>)}</div>
            <div className="approval-actions"><button className="reject-button" disabled={busy === item.approval_id} onClick={() => decide(item, 'REJECTED')}><ShieldX size={16} />Reject</button><button className="approve-button" disabled={busy === item.approval_id} onClick={() => decide(item, 'APPROVED')}><ShieldCheck size={16} />Approve</button></div>
          </article>
        ))}
        {items.length === 0 && <div className="panel empty-state wide"><CheckCircle2 size={34} /><strong>No approvals awaiting review</strong><span>Submitted requests will appear here.</span></div>}
      </section>
    </>
  )
}

function SessionsPage() {
  const [sessions, setSessions] = useState<AccessSession[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')

  async function load() {
    try { setSessions((await api.getSessions()).sessions); setError('') }
    catch (caught) { setError(caught instanceof Error ? caught.message : 'Unable to load sessions') }
  }
  useEffect(() => { void load() }, [])

  async function revoke(session: AccessSession) {
    setBusy(session.session_id)
    setError('')
    try {
      await api.revokeSession(session.session_id, {
        session_id: session.session_id,
        revoked_by_email: 'admin@company.com',
        revoked_by_name: 'Admin User',
        revocation_reason: 'Emergency access no longer required.',
      })
      await load()
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Session revocation failed')
    } finally { setBusy('') }
  }

  return (
    <>
      <PageHeading eyebrow="Temporary access" title="Active sessions"
        description="Monitor and revoke approved time-limited AWS access." />
      {error && <div className="error-banner"><AlertTriangle size={18} />{error}</div>}
      <section className="panel table-panel">
        <div className="table-wrap"><table><thead><tr><th>Session</th><th>User</th><th>Resource</th><th>Permissions</th><th>Expires</th><th>Status</th><th /></tr></thead>
          <tbody>{sessions.map((session) => (
            <tr key={session.session_id}>
              <td><strong>{session.session_id}</strong><span>{session.approval_id}</span></td>
              <td>{session.requester_email}</td>
              <td><strong>{session.resource_type.toUpperCase()}</strong><span>{session.resource_id}</span></td>
              <td><div className="permission-table">{session.granted_permissions.slice(0, 3).map((permission) => <span key={permission}>{permission}</span>)}</div></td>
              <td>{new Date(session.expires_at).toLocaleString()}</td>
              <td><StatusBadge status={session.status} /></td>
              <td>{session.status === 'active' && <button className="icon-revoke" disabled={busy === session.session_id} onClick={() => revoke(session)} title="Revoke session"><LogOut size={17} /></button>}</td>
            </tr>
          ))}</tbody></table>
          {sessions.length === 0 && <div className="empty-state"><KeyRound size={28} /><strong>No temporary sessions</strong><span>Approved sessions will appear here.</span></div>}
        </div>
      </section>
    </>
  )
}

function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [alerts, setAlerts] = useState<SecurityAlert[]>([])
  const [error, setError] = useState('')
  useEffect(() => {
    Promise.all([api.getAuditEvents(), api.getAuditAlerts()])
      .then(([log, securityAlerts]) => { setEvents(log.events); setAlerts(securityAlerts) })
      .catch((caught) => setError(caught instanceof Error ? caught.message : 'Unable to load audit trail'))
  }, [])
  return (
    <>
      <PageHeading eyebrow="Forensic trail" title="Security audit"
        description="Review requests, decisions, refusals and access lifecycle events." />
      {error && <div className="error-banner"><AlertTriangle size={18} />{error}</div>}
      <div className="audit-layout">
        <section className="panel table-panel audit-table"><div className="panel-heading"><div><span>Audit ledger</span><h2>Recent events</h2></div></div>
          <div className="event-list">{events.map((event) => (
            <div className="event-row" key={event.event_id}>
              <div className={`event-icon ${event.outcome === 'BLOCKED' ? 'blocked' : ''}`}>{event.outcome === 'BLOCKED' ? <ShieldX size={17} /> : <Activity size={17} />}</div>
              <div><strong>{event.event_description}</strong><span>{event.event_type.replaceAll('_', ' ')}</span></div>
              <StatusBadge status={event.severity} />
              <time>{new Date(event.timestamp).toLocaleString()}</time>
            </div>
          ))}{events.length === 0 && <div className="empty-state"><Activity size={28} /><strong>No audit events</strong></div>}</div>
        </section>
        <aside className="panel alert-panel"><div className="panel-heading"><div><span>Threat monitor</span><h2>Security alerts</h2></div></div>
          {alerts.map((alert) => <div className="alert-row" key={alert.alert_id}><AlertTriangle size={18} /><div><strong>{alert.title}</strong><span>{alert.description}</span></div></div>)}
          {alerts.length === 0 && <div className="empty-state"><ShieldCheck size={28} /><strong>No active alerts</strong><span>No unresolved security alerts.</span></div>}
        </aside>
      </div>
    </>
  )
}

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [tokenVersion, setTokenVersion] = useState(0)
  return (
    <div className="app-shell">
      <Sidebar open={sidebarOpen} setOpen={setSidebarOpen} />
      <div className="main-shell">
        <Header onMenu={() => setSidebarOpen(true)} />
        <TokenGate onReady={() => setTokenVersion((version) => version + 1)} />
        <main className="content" key={tokenVersion}>
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/requests" element={<RequestsPage />} />
            <Route path="/approvals" element={<ApprovalsPage />} />
            <Route path="/sessions" element={<SessionsPage />} />
            <Route path="/audit" element={<AuditPage />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
