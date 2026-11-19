export const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ||
  'http://127.0.0.1:8001'

export type AuthRole = 'requester' | 'approver' | 'admin' | 'internal'

export function getToken(): string {
  return localStorage.getItem('breakglass_token') || ''
}

export function setToken(token: string) {
  if (token) localStorage.setItem('breakglass_token', token)
  else localStorage.removeItem('breakglass_token')
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers = new Headers(options.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (options.body) headers.set('Content-Type', 'application/json')

  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers })
  const text = await response.text()
  let data: T | undefined
  if (text) {
    try {
      data = JSON.parse(text) as T
    } catch {
      throw new Error(text)
    }
  }
  if (!response.ok) {
    const detail =
      typeof data === 'object' && data !== null && 'detail' in data
        ? String((data as { detail: unknown }).detail)
        : `Request failed with status ${response.status}`
    throw new Error(detail)
  }
  return data as T
}

export const api = {
  health: () => request<{ status: string; checks: Record<string, string> }>('/health'),
  createDevelopmentToken: (email: string, roles: AuthRole[]) =>
    request<{ access_token: string; token_type: string; expires_at: string }>(
      '/api/auth/dev-token',
      { method: 'POST', body: JSON.stringify({ email, roles }) },
    ),
  getRequests: (page = 1, pageSize = 50) =>
    request<RequestList>(`/api/requests/?page=${page}&page_size=${pageSize}`),
  submitRequest: (body: AccessRequestInput) =>
    request<AccessRequestFull>('/api/requests/', { method: 'POST', body: JSON.stringify(body) }),
  getPendingApprovals: () =>
    request<PendingApprovals>('/api/approvals/pending'),
  decideApproval: (approvalId: string, body: ApprovalDecision) =>
    request<Approval>(`/api/approvals/${approvalId}/decide`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  getSessions: () =>
    request<SessionList>('/api/sessions/'),
  revokeSession: (sessionId: string, body: SessionRevocation) =>
    request<AccessSession>(`/api/sessions/${sessionId}/revoke`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  getAuditEvents: (limit = 100) =>
    request<AuditLog>(`/api/audit/events?limit=${limit}`),
  getAuditAlerts: () =>
    request<SecurityAlert[]>('/api/audit/alerts'),
  getAuditStatistics: () =>
    request<AuditStatistics>('/api/audit/statistics'),
}

export interface AccessRequestInput {
  requester_email: string
  requester_name: string
  emergency_description: string
  resource_type: 'ec2' | 's3' | 'lambda' | 'dynamodb' | 'rds'
  resource_id: string
  resource_region: string
  requested_action: string
  requested_permissions?: string[]
  duration_minutes: number
  business_justification: string
}

export interface AccessRequestFull {
  request: AccessRequest & {
    status: string
    created_at?: string
  }
  agent_analysis?: AgentAnalysis
  backend_validation?: BackendValidation
  approval_id?: string
  session_id?: string
}

export interface AccessRequest extends AccessRequestInput {
  request_id: string
  status: string
  created_at?: string
  updated_at?: string
}

export interface AgentAnalysis {
  risk_classification: string
  risk_score: number
  risk_explanation: string
  requested_permissions: string[]
  recommended_permissions: string[]
  recommended_template?: string
  affected_resources: string[]
  potential_impact: string
  approval_required: boolean
  suspicious_indicators: string[]
  agent_decision: string
  agent_explanation: string
}

export interface BackendValidation {
  validation_passed: boolean
  violations: string[]
  warnings: string[]
  final_risk_level: string
  backend_risk_score: number
}

export interface RequestList {
  requests: AccessRequestFull[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export interface Approval {
  approval_id: string
  request_id: string
  requester_email: string
  requester_name: string
  emergency_description: string
  resource_type: string
  resource_id: string
  requested_action: string
  duration_minutes: number
  business_justification: string
  risk_classification: string
  risk_score: number
  recommended_permissions: string[]
  agent_recommendation: string
  risk_explanation: string
  status: 'pending' | 'approved' | 'rejected' | 'expired'
  expires_at: string
  approver_email?: string
  approver_name?: string
  approval_decision?: string
  approval_reason?: string
  used: boolean
}

export interface PendingApprovals {
  approvals: Approval[]
  total: number
}

export interface ApprovalDecision {
  approval_id: string
  approver_email: string
  approver_name: string
  decision: 'APPROVED' | 'REJECTED'
  reason: string
  mfa_verified: boolean
}

export interface AccessSession {
  session_id: string
  request_id: string
  approval_id: string
  requester_email: string
  requester_name: string
  resource_type: string
  resource_id: string
  resource_region: string
  aws_account_id: string
  granted_permissions: string[]
  iam_role_arn?: string
  status: 'creating' | 'active' | 'expired' | 'revoked' | 'failed'
  created_at: string
  expires_at: string
  duration_minutes: number
  sts_session_name?: string
  revoked_at?: string
  revoked_by?: string
  revocation_reason?: string
}

export interface SessionList {
  sessions: AccessSession[]
  total: number
  active_count: number
  expiring_soon_count: number
}

export interface SessionRevocation {
  session_id: string
  revoked_by_email: string
  revoked_by_name: string
  revocation_reason: string
}

export interface AuditEvent {
  event_id: string
  event_type: string
  severity: string
  timestamp: string
  actor_email?: string
  request_id?: string
  approval_id?: string
  session_id?: string
  resource_type?: string
  resource_id?: string
  event_description: string
  outcome: string
  outcome_reason?: string
}

export interface AuditLog {
  events: AuditEvent[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export interface SecurityAlert {
  alert_id: string
  alert_type: string
  severity: string
  title: string
  description: string
  resolved: boolean
  auto_blocked: boolean
  manual_review_required: boolean
}

export interface AuditStatistics {
  total_events: number
  events_by_type: Record<string, number>
  events_by_severity: Record<string, number>
  security_alerts: number
  blocked_attempts: number
  events_last_24h: number
  events_last_7d: number
  events_last_30d: number
  most_active_users: { email: string; event_count: number }[]
}
