const API = typeof API_BASE !== 'undefined' ? API_BASE : 'http://localhost:5000';
let SESSION = null;   // current logged-in RBAC user
let allUsers = [];
let rolesCache = {};

// ── API ───────────────────────────────────────────────────────────────────────
async function api(path, opts = {}) {
  const res = await fetch(API + path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts
  });
  return res.json();
}

// ── Auth ──────────────────────────────────────────────────────────────────────
document.getElementById('login-form').addEventListener('submit', async e => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const result = await api('/rbac/login', {
    method: 'POST',
    body: JSON.stringify({ username: fd.get('username'), password: fd.get('password') })
  });
  if (result.error) {
    document.getElementById('login-error').classList.remove('hidden');
    return;
  }
  SESSION = result;
  document.getElementById('login-error').classList.add('hidden');
  document.getElementById('login-overlay').classList.add('hidden');
  renderSessionBar();
  init();
});

function logout() {
  SESSION = null;
  document.getElementById('session-bar').classList.add('hidden');
  document.getElementById('login-overlay').classList.remove('hidden');
  document.getElementById('login-form').reset();
}

function renderSessionBar() {
  const bar = document.getElementById('session-bar');
  bar.classList.remove('hidden');
  document.getElementById('session-avatar').textContent = SESSION.name.charAt(0);
  document.getElementById('session-name').textContent = SESSION.name;
  const rb = document.getElementById('session-role-badge');
  rb.textContent = SESSION.role_label;
  rb.style.color = SESSION.role_color;
  rb.style.borderColor = SESSION.role_color;
  rb.style.background = SESSION.role_color + '18';
  document.getElementById('session-perms').innerHTML =
    SESSION.permissions.map(p => `<span class="perm-tag">${p}</span>`).join('');
}

function can(permission) {
  return SESSION && (SESSION.permissions.includes('approve_any') || SESSION.permissions.includes(permission));
}

// ── Tabs ──────────────────────────────────────────────────────────────────────
const TAB_TITLES = {
  dashboard: 'Dashboard', joiner: 'New Joiner', mover: 'Role Change',
  leaver: 'Offboard Employee', approvals: 'Pending Approvals',
  users: 'Employee Directory', audit: 'Audit Log', rbac: 'RBAC Users'
};

document.querySelectorAll('.nav-item').forEach(btn => {
  btn.addEventListener('click', () => switchTab(btn.dataset.tab));
});

function switchTab(name) {
  document.querySelectorAll('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.tab === name));
  document.querySelectorAll('.tab-content').forEach(s => s.classList.toggle('active', s.id === `tab-${name}`));
  document.getElementById('topbar-title').textContent = TAB_TITLES[name] || name;
  if (name === 'dashboard') loadDashboard();
  if (name === 'approvals') loadApprovals();
  if (name === 'users')     loadUsers();
  if (name === 'audit')     loadAudit();
  if (name === 'rbac')      loadRbac();
}

// ── Modal ─────────────────────────────────────────────────────────────────────
document.getElementById('modal-close').addEventListener('click', closeModal);
document.getElementById('modal-backdrop').addEventListener('click', closeModal);
function openModal(html) {
  document.getElementById('modal-content').innerHTML = html;
  document.getElementById('modal').classList.remove('hidden');
}
function closeModal() { document.getElementById('modal').classList.add('hidden'); }

// ── Chips ─────────────────────────────────────────────────────────────────────
function typeChip(type, requestId, employeeName) {
  const colors = { JOINER: 'chip-JOINER', MOVER: 'chip-MOVER', LEAVER: 'chip-LEAVER' };
  return `<span class="type-chip ${colors[type]}" onclick="showIdDocument('${requestId}','${type}','${(employeeName||'').replace(/'/g,"\\'")}'); event.stopPropagation()" title="View identity document">${type} 🪪</span>`;
}
function statusChip(status) {
  return `<span class="status-chip s-${status}">${status.replace(/_/g,' ')}</span>`;
}
function riskBadge(risk) {
  if (!risk) return '';
  return `<span class="risk-badge risk-${risk.level}">${risk.level}</span>`;
}
function timeAgo(iso) {
  const diff = Date.now() - new Date(iso + 'Z').getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function showToast(elId, data, isError) {
  const el = document.getElementById(elId);
  el.classList.remove('hidden', 'toast-success', 'toast-error');
  el.classList.add(isError ? 'toast-error' : 'toast-success');
  const msg = isError ? data.error || 'Request failed' : `Status: ${(data.status || '').replace(/_/g,' ')}`;
  el.innerHTML = `<div class="toast-header">${isError ? '✕' : '✓'} ${msg}</div>
    <div class="toast-body"><pre>${JSON.stringify(data, null, 2)}</pre></div>`;
  el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ── Roles & employees ─────────────────────────────────────────────────────────
async function loadRoles() {
  rolesCache = await api('/roles');
  const names = Object.keys(rolesCache);
  ['joiner-role', 'mover-role'].forEach(id => {
    const sel = document.getElementById(id);
    sel.innerHTML = '<option value="">Select a role…</option>';
    names.forEach(r => {
      const opt = document.createElement('option');
      opt.value = r; opt.textContent = r; sel.appendChild(opt);
    });
  });
}

async function loadEmployeeDropdowns() {
  allUsers = await api('/users');
  const active = allUsers.filter(u => u.status === 'active');
  ['mover-employee', 'leaver-employee'].forEach(id => {
    const sel = document.getElementById(id);
    sel.innerHTML = '<option value="">Select employee…</option>';
    active.forEach(u => {
      const opt = document.createElement('option');
      opt.value = u.id; opt.textContent = `${u.name} (${u.id})`; sel.appendChild(opt);
    });
  });
}

// Role preview
document.getElementById('joiner-role').addEventListener('change', e => {
  const cfg = rolesCache[e.target.value];
  const el  = document.getElementById('role-preview');
  if (!cfg) { el.classList.add('hidden'); return; }
  const needsApproval = new Set(cfg.requires_approval || []);
  el.classList.remove('hidden');
  el.innerHTML = `<div class="rp-title">Systems to be provisioned</div>
    <div class="rp-systems">${cfg.systems.map(s =>
      `<span class="rp-tag ${needsApproval.has(s) ? 'needs-approval' : ''}">${s}${needsApproval.has(s) ? ' ⚠' : ''}</span>`
    ).join('')}</div>
    ${needsApproval.size ? `<div class="rp-note">⚠ Highlighted systems require multi-level approval (L1 Manager → L2 IT Security → L3 IT Compliance for critical systems like AWS_Prod, Okta, AD).</div>` : ''}`;
});

// Mover diff
function updateMoverDiff() {
  const empId   = document.getElementById('mover-employee').value;
  const newRole = document.getElementById('mover-role').value;
  const el      = document.getElementById('mover-diff');
  if (!empId || !newRole) { el.classList.add('hidden'); return; }
  const emp    = allUsers.find(u => u.id === empId);
  if (!emp) { el.classList.add('hidden'); return; }
  const oldSys = new Set((rolesCache[emp.role] || {}).systems || []);
  const newSys = new Set((rolesCache[newRole]  || {}).systems || []);
  el.classList.remove('hidden');
  el.innerHTML = `
    <div class="diff-col">
      <div class="diff-label">Current (${emp.role})</div>
      <div class="diff-tags">
        ${[...oldSys].filter(s => newSys.has(s)).map(s => `<span class="diff-tag keep">${s}</span>`).join('')}
        ${[...oldSys].filter(s => !newSys.has(s)).map(s => `<span class="diff-tag remove">− ${s}</span>`).join('')}
      </div>
    </div>
    <div class="diff-arrow">→</div>
    <div class="diff-col">
      <div class="diff-label">New (${newRole})</div>
      <div class="diff-tags">
        ${[...newSys].filter(s => oldSys.has(s)).map(s => `<span class="diff-tag keep">${s}</span>`).join('')}
        ${[...newSys].filter(s => !oldSys.has(s)).map(s => `<span class="diff-tag add">+ ${s}</span>`).join('')}
      </div>
    </div>`;
}
document.getElementById('mover-employee').addEventListener('change', updateMoverDiff);
document.getElementById('mover-role').addEventListener('change', updateMoverDiff);

// Leaver preview
document.getElementById('leaver-employee').addEventListener('change', e => {
  const emp = allUsers.find(u => u.id === e.target.value);
  const el  = document.getElementById('leaver-preview');
  if (!emp) { el.classList.add('hidden'); return; }
  el.classList.remove('hidden');
  el.innerHTML = `<div class="lp-name">${emp.name}</div>
    <div class="lp-role">${emp.role} · ${emp.department}</div>
    <div class="lp-systems">${(emp.systems || []).map(s => `<span class="lp-sys">${s}</span>`).join('')}</div>`;
});

// ── Dashboard ─────────────────────────────────────────────────────────────────
let activityChart = null;
let chartMode = 'activity';

async function loadDashboard() {
  const [users, requests, analytics, orphans] = await Promise.all([
    api('/users'), api('/requests'), api('/analytics'), api('/orphans')
  ]);
  allUsers = users;

  const active    = users.filter(u => u.status === 'active').length;
  const inactive  = users.filter(u => u.status === 'inactive').length;
  const pending   = requests.filter(r => r.status === 'PENDING_APPROVAL').length;
  const completed = requests.filter(r => r.status === 'COMPLETED').length;

  const badge = document.getElementById('approval-count');
  badge.textContent = pending || '';
  badge.style.display = pending > 0 ? 'inline-block' : 'none';

  document.getElementById('stats').innerHTML = `
    <div class="stat-card" style="--card-accent:linear-gradient(90deg,#10b981,#059669)">
      <span class="stat-icon">👥</span><div class="num">${active}</div>
      <div class="label">Active Employees</div><span class="trend trend-up">Active</span>
    </div>
    <div class="stat-card" style="--card-accent:linear-gradient(90deg,#f59e0b,#d97706)">
      <span class="stat-icon">⏳</span><div class="num">${pending}</div>
      <div class="label">Pending Approvals</div>
      <span class="trend ${pending > 0 ? 'trend-warn' : 'trend-up'}">${pending > 0 ? 'Needs action' : 'All clear'}</span>
    </div>
    <div class="stat-card" style="--card-accent:linear-gradient(90deg,#5b8dee,#8b5cf6)">
      <span class="stat-icon">✓</span><div class="num">${completed}</div>
      <div class="label">Completed</div><span class="trend trend-up">This cycle</span>
    </div>
    <div class="stat-card" style="--card-accent:linear-gradient(90deg,#ef4444,#dc2626)">
      <span class="stat-icon">🔒</span><div class="num">${inactive}</div>
      <div class="label">Deprovisioned</div>
      <span class="trend ${inactive > 0 ? 'trend-red' : 'trend-up'}">${inactive > 0 ? 'Offboarded' : 'None'}</span>
    </div>`;

  // Orphan alert
  const orphanEl = document.getElementById('orphan-alert');
  if (orphans.length) {
    orphanEl.classList.remove('hidden');
    orphanEl.innerHTML = `<span style="font-size:1.1rem">⚠</span>
      <div><div class="alert-title">${orphans.length} Orphaned Account${orphans.length>1?'s':''} Detected</div>
      <div style="font-size:0.8rem;opacity:0.8">Accounts with mismatched access status require review.</div>
      <div class="alert-items">${orphans.map(o=>`<span class="alert-item" onclick="switchTab('users')">${o.name}</span>`).join('')}</div></div>`;
  } else orphanEl.classList.add('hidden');

  // SLA alert
  const breached = analytics.sla.filter(s => s.breached);
  const slaEl = document.getElementById('sla-alert');
  if (breached.length) {
    slaEl.classList.remove('hidden');
    slaEl.innerHTML = `<span style="font-size:1.1rem">🔴</span>
      <div><div class="alert-title">${breached.length} SLA Breach${breached.length>1?'es':''} — Approval overdue (&gt;24h)</div>
      <div class="alert-items">${breached.map(b=>`<span class="alert-item" onclick="showRequestDetail('${b.id}')">${b.title} (${b.hours_pending}h)</span>`).join('')}</div></div>`;
  } else slaEl.classList.add('hidden');

  // Chart
  renderActivityChart(analytics);

  // SLA panel
  renderSlaPanel(analytics.sla);

  // Recent requests
  const recent = [...requests].sort((a,b) => b.created_at.localeCompare(a.created_at)).slice(0,6);
  renderRequestRows('recent-requests', recent);

  // System coverage
  const sysCounts = {};
  users.filter(u => u.status === 'active').forEach(u =>
    (u.systems||[]).forEach(s => { sysCounts[s] = (sysCounts[s]||0)+1; })
  );
  const max = Math.max(...Object.values(sysCounts), 1);
  document.getElementById('system-coverage').innerHTML =
    Object.entries(sysCounts).sort((a,b)=>b[1]-a[1]).map(([sys,cnt])=>`
      <div class="sys-coverage-item">
        <div class="sys-name">${sys}</div>
        <div class="sys-bar-wrap"><div class="sys-bar" style="width:${(cnt/max)*100}%"></div></div>
        <div class="sys-count">${cnt}</div>
      </div>`).join('') || '<div class="empty-state">No data</div>';
}

function renderActivityChart(analytics) {
  const ctx = document.getElementById('activity-chart').getContext('2d');
  if (activityChart) activityChart.destroy();

  if (chartMode === 'activity') {
    const days = Object.keys(analytics.by_day).sort().slice(-10);
    activityChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: days.map(d => d.slice(5)),
        datasets: [
          { label:'Joiners', data: days.map(d=>analytics.by_day[d]?.JOINER||0), backgroundColor:'rgba(16,185,129,0.7)', borderRadius:4 },
          { label:'Movers',  data: days.map(d=>analytics.by_day[d]?.MOVER||0),  backgroundColor:'rgba(91,141,238,0.7)',  borderRadius:4 },
          { label:'Leavers', data: days.map(d=>analytics.by_day[d]?.LEAVER||0), backgroundColor:'rgba(239,68,68,0.7)',   borderRadius:4 },
        ]
      },
      options: { responsive:true, plugins:{legend:{labels:{color:'#94a3b8',font:{size:11}}}},
        scales:{ x:{ticks:{color:'#475569'},grid:{color:'rgba(255,255,255,0.04)'}}, y:{ticks:{color:'#475569',stepSize:1},grid:{color:'rgba(255,255,255,0.04)'}} } }
    });
  } else {
    const rc = analytics.risk_counts;
    activityChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Low','Medium','High','Critical'],
        datasets: [{ data:[rc.LOW,rc.MEDIUM,rc.HIGH,rc.CRITICAL],
          backgroundColor:['rgba(16,185,129,0.8)','rgba(245,158,11,0.8)','rgba(239,68,68,0.8)','rgba(220,38,38,0.9)'],
          borderWidth:0 }]
      },
      options: { responsive:true, cutout:'65%',
        plugins:{legend:{position:'right',labels:{color:'#94a3b8',font:{size:11},padding:12}}} }
    });
  }
}

function toggleChart() {
  chartMode = chartMode === 'activity' ? 'risk' : 'activity';
  document.getElementById('chart-toggle').textContent =
    chartMode === 'activity' ? 'Switch to Risk View' : 'Switch to Activity View';
  loadDashboard();
}

function renderSlaPanel(slaData) {
  const el = document.getElementById('sla-panel');
  const breachEl = document.getElementById('sla-breach-count');
  const breached = slaData.filter(s => s.breached);
  breachEl.textContent = breached.length ? `${breached.length} breached` : '';
  breachEl.style.display = breached.length ? 'inline-block' : 'none';

  if (!slaData.length) {
    el.innerHTML = '<div class="empty-state">No pending requests.</div>';
    return;
  }
  el.innerHTML = slaData.map(s => `
    <div class="sla-row" onclick="showRequestDetail('${s.id}')">
      ${typeChip(s.type)}
      <div style="flex:1;font-size:0.82rem">${s.title}</div>
      <span class="sla-timer ${s.breached ? 'sla-breached' : 'sla-ok'}">${s.hours_pending}h ${s.breached ? '⚠ BREACHED' : '✓'}</span>
    </div>`).join('');
}

// ── Request rows ──────────────────────────────────────────────────────────────
function renderRequestRows(containerId, requests) {
  const el = document.getElementById(containerId);
  if (!requests.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">📋</div>No requests yet.</div>';
    return;
  }
  el.innerHTML = requests.map(r => {
    const p = r.payload;
    const title = r.type === 'JOINER' ? `Onboard ${p.name || p.employee_id}`
                : r.type === 'MOVER'  ? `${p.employee_id} → ${p.new_role}`
                : `Offboard ${p.employee_id}`;
    const empName = p.name || p.employee_id || '';
    return `<div class="request-row" onclick="showRequestDetail('${r.id}')">
      ${typeChip(r.type, r.id, empName)}
      <div class="req-meta">
        <div class="req-title">${title}</div>
        <div class="req-sub">${r.requester} · ${timeAgo(r.created_at)}</div>
      </div>
      ${riskBadge(r.risk)}
      ${statusChip(r.status)}
    </div>`;
  }).join('');
}

// ── Request detail modal ──────────────────────────────────────────────────────
async function showRequestDetail(id) {
  const r = await api(`/requests/${id}`);
  const chain = r.approval_chain || [];

  // Build approval chain UI
  const chainHtml = chain.length ? `
    <div class="modal-section">
      <div class="modal-section-label">Approval Chain</div>
      <div class="approval-chain">
        ${chain.map(step => {
          const icon = step.status === 'APPROVED'  ? '✓' :
                       step.status === 'BYPASSED'  ? '⚡' :
                       step.status === 'PENDING'   ? '⏳' : '○';
          const cls  = step.status.toLowerCase();
          return `<div class="chain-step ${cls}">
            <span class="chain-level level-${step.level}">${step.level}</span>
            <div style="flex:1">
              <div class="chain-label">${step.label}</div>
              <div class="chain-role">${step.approver_role}</div>
            </div>
            ${step.approver ? `<span class="chain-approver">${step.approver}</span>` : ''}
            <span class="chain-status-icon">${icon}</span>
          </div>`;
        }).join('')}
      </div>
    </div>` : '';

  // IAM results
  const iamHtml = r.iam_results && r.iam_results.length
    ? r.iam_results.map(x => `
        <div class="iam-card">
          <div class="iam-sys">${x.system}</div>
          <span class="iam-action-badge action-${x.action}">${x.action}</span>
          <div class="iam-txn">${x.transaction_id.slice(0,8)}…</div>
        </div>`).join('')
    : '<div class="empty-state" style="padding:12px">No IAM actions yet.</div>';

  // Approval buttons — only show levels the current user can approve
  let approvalBtns = '';
  if (r.status === 'PENDING_APPROVAL') {
    const pendingSteps = chain.filter(s => s.status === 'PENDING');
    const btns = pendingSteps
      .filter(s => can(`approve_${s.level}`))
      .map(s => `<button class="btn btn-success btn-sm" onclick="doApprove('${r.id}','${s.level}')">
        Approve ${s.level} — ${s.label}
      </button>`).join('');

    const rejectBtn = can('reject_any')
      ? `<button class="btn btn-danger btn-sm" onclick="doReject('${r.id}')">Reject</button>` : '';

    const overrideBtn = can('override')
      ? `<button class="btn-override" onclick="doOverride('${r.id}')">⚡ Emergency Override</button>` : '';

    if (btns || rejectBtn || overrideBtn) {
      approvalBtns = `<div class="approval-actions">${btns}${rejectBtn}${overrideBtn}</div>`;
    }
  }

  // Override badge
  const overrideBadge = r.override_by
    ? `<div class="override-badge" style="margin-top:8px">⚡ Overridden by ${r.override_by} — ${r.override_reason}</div>` : '';

  const riskHtml = r.risk ? `
    <div class="modal-section">
      <div class="modal-section-label">Risk Assessment</div>
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px">
        <span class="risk-badge risk-${r.risk.level}" style="font-size:0.8rem;padding:5px 12px">${r.risk.level} RISK</span>
        <span style="font-size:0.82rem;color:var(--text2)">Score: ${r.risk.score}/100</span>
        ${r.risk.sod_violation ? '<span style="color:var(--red);font-size:0.78rem;font-weight:600">⚠ SoD Violation</span>' : ''}
      </div>
      ${r.risk.factors.map(f=>`<div style="font-size:0.78rem;color:var(--text2);padding:3px 0;border-bottom:1px solid var(--border)">• ${f}</div>`).join('')}
    </div>` : '';

  openModal(`
    <div class="modal-title">${typeChip(r.type, r.id, r.payload?.name || r.payload?.employee_id)} ${statusChip(r.status)} ${riskBadge(r.risk)}</div>
    <div class="modal-section">
      <div class="modal-section-label">Details</div>
      <div class="modal-field"><span class="mf-key">Request ID</span><span class="mf-val" style="font-family:monospace;font-size:0.75rem">${r.id}</span></div>
      <div class="modal-field"><span class="mf-key">Requester</span><span class="mf-val">${r.requester}</span></div>
      <div class="modal-field"><span class="mf-key">Created</span><span class="mf-val">${new Date(r.created_at + 'Z').toLocaleString()}</span></div>
      ${r.rejection_reason ? `<div class="modal-field"><span class="mf-key">Rejected by</span><span class="mf-val" style="color:var(--red)">${r.rejected_by} — ${r.rejection_reason}</span></div>` : ''}
      ${overrideBadge}
    </div>
    ${riskHtml}
    ${chainHtml}
    <div class="modal-section">
      <div class="modal-section-label">IAM Actions (${r.iam_results?.length || 0})</div>
      ${iamHtml}
    </div>
    ${approvalBtns}
  `);
}

async function doApprove(requestId, level) {
  if (!SESSION) return;
  const result = await api(`/requests/${requestId}/approve`, {
    method: 'POST',
    body: JSON.stringify({ approver: SESSION.username, level })
  });
  if (result.error) { alert(result.error); return; }
  closeModal();
  await showRequestDetail(requestId);
  loadDashboard(); loadApprovals();
}

async function doReject(requestId) {
  if (!SESSION) return;
  const reason = prompt('Rejection reason:');
  if (reason === null) return;
  const result = await api(`/requests/${requestId}/reject`, {
    method: 'POST',
    body: JSON.stringify({ approver: SESSION.username, reason: reason || 'No reason given' })
  });
  if (result.error) { alert(result.error); return; }
  closeModal(); loadApprovals(); loadDashboard();
}

async function doOverride(requestId) {
  if (!SESSION) return;
  const justification = prompt('⚡ Emergency Override — Enter justification (this is fully audited):');
  if (!justification) return;
  const result = await api(`/requests/${requestId}/override`, {
    method: 'POST',
    body: JSON.stringify({ actor: SESSION.username, justification })
  });
  if (result.error) { alert(result.error); return; }
  closeModal();
  await showRequestDetail(requestId);
  loadDashboard(); loadApprovals(); loadAudit();
}

// ── Approvals tab ─────────────────────────────────────────────────────────────
async function loadApprovals() {
  const requests = await api('/requests?status=PENDING_APPROVAL');
  const label = document.getElementById('pending-count-label');
  if (label) { label.textContent = requests.length ? `${requests.length} pending` : ''; }
  renderRequestRows('approvals-list', requests);
}

// ── Directory ─────────────────────────────────────────────────────────────────
let activeDeptFilter = null;

async function loadUsers() {
  allUsers = await api('/users');
  buildDeptFilters();
  renderUsers(allUsers);
}

function buildDeptFilters() {
  const depts = [...new Set(allUsers.map(u => u.department))].sort();
  const el = document.getElementById('dept-filters');
  el.innerHTML = `<span class="filter-pill active" data-dept="all">All</span>` +
    depts.map(d => `<span class="filter-pill" data-dept="${d}">${d}</span>`).join('');
  el.querySelectorAll('.filter-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      el.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      activeDeptFilter = pill.dataset.dept === 'all' ? null : pill.dataset.dept;
      applyUserFilters();
    });
  });
}

function applyUserFilters() {
  const q = document.getElementById('user-search').value.toLowerCase();
  let filtered = allUsers;
  if (activeDeptFilter) filtered = filtered.filter(u => u.department === activeDeptFilter);
  if (q) filtered = filtered.filter(u =>
    u.name.toLowerCase().includes(q) || u.role.toLowerCase().includes(q) || u.department.toLowerCase().includes(q)
  );
  renderUsers(filtered);
}
document.getElementById('user-search').addEventListener('input', applyUserFilters);

function renderUsers(users) {
  const el = document.getElementById('users-list');
  if (!users.length) { el.innerHTML = '<div class="empty-state" style="grid-column:1/-1"><div class="empty-icon">🔍</div>No employees found.</div>'; return; }
  el.innerHTML = users.map(u => `
    <div class="user-card">
      <div class="user-card-top">
        <div class="user-avatar ${u.status}">${u.name.charAt(0)}</div>
        <div class="user-info"><div class="u-name">${u.name}</div><div class="u-email">${u.email || u.id}</div></div>
      </div>
      <div class="u-status ${u.status}"><span class="status-dot"></span>${u.status}</div>
      <div class="u-role">${u.role}</div>
      <div class="u-dept">${u.department}</div>
      <div class="u-systems">
        ${(u.systems || []).map(s => `<span class="u-sys-tag">${s}</span>`).join('')}
        ${!u.systems?.length ? '<span style="font-size:0.75rem;color:var(--text3)">No active access</span>' : ''}
      </div>
    </div>`).join('');
}

// ── Audit Log ─────────────────────────────────────────────────────────────────
let auditSevFilter = 'ALL';

async function loadAudit() {
  const logs = await api('/audit');
  renderAudit(logs);
}

function renderAudit(logs) {
  const q   = (document.getElementById('audit-search')?.value || '').toLowerCase();
  let filtered = logs;
  if (auditSevFilter !== 'ALL') filtered = filtered.filter(l => l.severity === auditSevFilter);
  if (q) filtered = filtered.filter(l =>
    l.action.toLowerCase().includes(q) || l.actor.toLowerCase().includes(q)
  );

  const el = document.getElementById('audit-table');
  if (!filtered.length) { el.innerHTML = '<div class="empty-state">No audit entries found.</div>'; return; }

  el.innerHTML = `
    <div class="audit-row audit-header">
      <div>Timestamp</div><div>Severity</div><div>Actor</div><div>Action</div><div>Request ID</div>
    </div>` +
    filtered.map(l => `
      <div class="audit-row">
        <div class="audit-ts">${new Date(l.timestamp + 'Z').toLocaleString()}</div>
        <div><span class="sev-badge sev-${l.severity}">${l.severity}</span></div>
        <div class="audit-actor">${l.actor}</div>
        <div class="audit-action">${l.action}</div>
        <div class="audit-detail">${l.request_id ? l.request_id.slice(0,8) + '…' : '—'}</div>
      </div>`).join('');
}

document.getElementById('audit-search')?.addEventListener('input', async () => {
  const logs = await api('/audit');
  renderAudit(logs);
});

document.querySelectorAll('[data-sev]').forEach(pill => {
  pill.addEventListener('click', async () => {
    document.querySelectorAll('[data-sev]').forEach(p => p.classList.remove('active'));
    pill.classList.add('active');
    auditSevFilter = pill.dataset.sev;
    const logs = await api('/audit');
    renderAudit(logs);
  });
});

// ── RBAC Users ────────────────────────────────────────────────────────────────
async function loadRbac() {
  const data = await api('/rbac/users');
  const el = document.getElementById('rbac-table');
  const highlightPerms = ['approve_any', 'override', 'approve_L1', 'approve_L2', 'approve_L3'];
  el.innerHTML = `
    <div class="rbac-row rbac-header">
      <div>Username</div><div>Name</div><div>Role</div><div>Permissions</div>
    </div>` +
    data.users.map(u => {
      const def = data.role_definitions[u.role] || {};
      return `<div class="rbac-row">
        <div style="font-family:monospace;font-size:0.8rem">${u.username}</div>
        <div style="font-weight:600">${u.name}</div>
        <div><span class="session-role" style="color:${def.color};border-color:${def.color};background:${def.color}18;font-size:0.72rem;padding:3px 9px;border-radius:20px;border:1px solid">${def.label || u.role}</span></div>
        <div class="rbac-perms">${u.permissions.map(p =>
          `<span class="rbac-perm ${highlightPerms.includes(p) ? 'highlight' : ''}">${p}</span>`
        ).join('')}</div>
      </div>`;
    }).join('');
}

// ── JML Forms ─────────────────────────────────────────────────────────────────
document.getElementById('joiner-form').addEventListener('submit', async e => {
  e.preventDefault();
  const body = { ...Object.fromEntries(new FormData(e.target)), actor: SESSION?.username || 'HR_Portal' };
  const result = await api('/joiner', { method: 'POST', body: JSON.stringify(body) });
  showToast('joiner-result', result, !!result.error);
  if (!result.error) { await loadEmployeeDropdowns(); loadDashboard(); }
});

document.getElementById('mover-form').addEventListener('submit', async e => {
  e.preventDefault();
  const body = { ...Object.fromEntries(new FormData(e.target)), actor: SESSION?.username || 'HR_Portal' };
  const result = await api('/mover', { method: 'POST', body: JSON.stringify(body) });
  showToast('mover-result', result, !!result.error);
  if (!result.error) { await loadEmployeeDropdowns(); loadDashboard(); }
});

document.getElementById('leaver-form').addEventListener('submit', async e => {
  e.preventDefault();
  const body = { ...Object.fromEntries(new FormData(e.target)), actor: SESSION?.username || 'HR_Portal' };
  const emp = allUsers.find(u => u.id === body.employee_id);
  if (!confirm(`Offboard ${emp?.name || body.employee_id}? All access will be revoked.`)) return;
  const result = await api('/leaver', { method: 'POST', body: JSON.stringify(body) });
  showToast('leaver-result', result, !!result.error);
  if (!result.error) { await loadEmployeeDropdowns(); loadDashboard(); }
});

// ── Identity Document Viewer ──────────────────────────────────────────────────
async function showIdDocument(requestId, type, employeeName) {
  const r = await api(`/requests/${requestId}`);
  const p = r.payload;

  const name      = p.name || employeeName || p.employee_id || 'Unknown';
  const empId     = p.employee_id || '—';
  const role      = p.role || p.new_role || '—';
  const dept      = p.department || '—';
  const email     = p.email || `${empId.toLowerCase()}@techcorp.io`;
  const issued    = new Date(r.created_at + 'Z').toLocaleDateString('en-GB');
  const initials  = name.split(' ').map(w => w[0]).join('').slice(0,2).toUpperCase();

  // Deterministic avatar colour from name
  const hue = [...name].reduce((acc, c) => acc + c.charCodeAt(0), 0) % 360;

  const typeConfig = {
    JOINER: { label: 'ONBOARDING',    color: '#10b981', bg: 'rgba(16,185,129,0.08)',  border: 'rgba(16,185,129,0.3)',  icon: '＋' },
    MOVER:  { label: 'ROLE TRANSFER', color: '#5b8dee', bg: 'rgba(91,141,238,0.08)',  border: 'rgba(91,141,238,0.3)',  icon: '⇄' },
    LEAVER: { label: 'OFFBOARDING',   color: '#ef4444', bg: 'rgba(239,68,68,0.08)',   border: 'rgba(239,68,68,0.3)',   icon: '✕' },
  };
  const cfg = typeConfig[type];

  const verifiedStamp = r.status === 'COMPLETED' || r.status === 'OVERRIDE'
    ? `<div class="id-stamp verified">✓ VERIFIED</div>`
    : r.status === 'REJECTED'
    ? `<div class="id-stamp rejected">✕ REJECTED</div>`
    : `<div class="id-stamp pending">⏳ PENDING</div>`;

  // Build a fake but realistic document number
  const docNum = 'TC-' + empId + '-' + requestId.slice(0,6).toUpperCase();

  openModal(`
    <div class="id-doc" style="--id-color:${cfg.color};--id-bg:${cfg.bg};--id-border:${cfg.border}">
      <div class="id-doc-header">
        <div class="id-doc-brand">
          <span class="id-brand-icon">⚕</span>
          <div>
            <div class="id-brand-name">TechCorp</div>
            <div class="id-brand-sub">Identity & Access Management</div>
          </div>
        </div>
        <div class="id-type-label" style="background:${cfg.bg};color:${cfg.color};border:1px solid ${cfg.border}">
          ${cfg.icon} ${cfg.label}
        </div>
      </div>

      <div class="id-doc-body">
        <div class="id-photo" style="background:linear-gradient(135deg,hsl(${hue},60%,35%),hsl(${hue+40},60%,25%))">
          <div class="id-initials">${initials}</div>
          <div class="id-photo-label">EMPLOYEE PHOTO</div>
        </div>

        <div class="id-fields">
          <div class="id-field-row">
            <div class="id-field">
              <div class="id-field-label">Full Name</div>
              <div class="id-field-value">${name}</div>
            </div>
            <div class="id-field">
              <div class="id-field-label">Employee ID</div>
              <div class="id-field-value mono">${empId}</div>
            </div>
          </div>
          <div class="id-field-row">
            <div class="id-field">
              <div class="id-field-label">Role</div>
              <div class="id-field-value">${role}</div>
            </div>
            <div class="id-field">
              <div class="id-field-label">Department</div>
              <div class="id-field-value">${dept}</div>
            </div>
          </div>
          <div class="id-field-row">
            <div class="id-field">
              <div class="id-field-label">Corporate Email</div>
              <div class="id-field-value mono">${email}</div>
            </div>
            <div class="id-field">
              <div class="id-field-label">Issue Date</div>
              <div class="id-field-value">${issued}</div>
            </div>
          </div>
          <div class="id-field-row">
            <div class="id-field">
              <div class="id-field-label">Document Reference</div>
              <div class="id-field-value mono" style="font-size:0.75rem">${docNum}</div>
            </div>
            <div class="id-field">
              <div class="id-field-label">Authorised By</div>
              <div class="id-field-value">${r.requester}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="id-doc-footer">
        <div class="id-barcode">
          ${generateBarcode(docNum)}
        </div>
        <div style="flex:1"></div>
        ${verifiedStamp}
      </div>

      <div class="id-disclaimer">
        This document is auto-generated by TechCorp IAM and is valid only for internal identity verification purposes.
        Document ID: ${docNum}
      </div>
    </div>
  `);
}

function generateBarcode(text) {
  // Visual-only SVG barcode from text chars
  const bars = [...text].map(c => c.charCodeAt(0));
  const width = 180;
  const height = 36;
  let rects = '';
  let x = 0;
  const unit = width / (bars.length * 4);
  bars.forEach(b => {
    const w1 = unit * (1 + (b % 3));
    const w2 = unit * (1 + ((b >> 2) % 2));
    rects += `<rect x="${x.toFixed(1)}" y="0" width="${w1.toFixed(1)}" height="${height}" fill="#e2e8f0"/>`;
    x += w1 + unit;
    rects += `<rect x="${x.toFixed(1)}" y="0" width="${w2.toFixed(1)}" height="${height}" fill="#e2e8f0"/>`;
    x += w2 + unit;
  });
  return `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg">${rects}</svg>`;
}

// ── Chatbot ───────────────────────────────────────────────────────────────────
let pendingChatPayload = null;

document.getElementById('chat-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') sendChat();
});

async function sendChat() {
  const input = document.getElementById('chat-input');
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';

  appendChatMsg(msg, 'user');
  appendTyping();

  const result = await api('/chat', {
    method: 'POST',
    body: JSON.stringify({ message: msg, actor: SESSION?.username || 'guest' })
  });

  removeTyping();

  // Format markdown-lite: **bold**, _italic_
  const formatted = (result.reply || '')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/_(.*?)_/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');

  if (result.action === 'SUBMIT_JOINER' || result.action === 'SUBMIT_MOVER' || result.action === 'SUBMIT_LEAVER') {
    pendingChatPayload = { action: result.action, payload: result.payload };
    appendChatMsg(formatted + `
      <div class="chat-confirm">
        <button class="btn btn-success btn-sm" onclick="confirmChat()">Confirm</button>
        <button class="btn btn-ghost btn-sm" onclick="cancelChat()">Cancel</button>
      </div>`, 'bot', true);
  } else if (result.action === 'SHOW_APPROVALS') {
    appendChatMsg(formatted, 'bot', true);
    setTimeout(() => switchTab('approvals'), 600);
  } else if (result.action === 'SHOW_DIRECTORY') {
    appendChatMsg(formatted, 'bot', true);
    setTimeout(() => switchTab('users'), 600);
  } else if (result.action === 'SHOW_AUDIT') {
    appendChatMsg(formatted, 'bot', true);
    setTimeout(() => switchTab('audit'), 600);
  } else {
    appendChatMsg(formatted, 'bot', true);
  }
}

async function confirmChat() {
  if (!pendingChatPayload) return;
  const { action, payload } = pendingChatPayload;
  pendingChatPayload = null;

  const endpoint = action === 'SUBMIT_JOINER' ? '/joiner'
                 : action === 'SUBMIT_MOVER'  ? '/mover'
                 : '/leaver';

  appendTyping();
  const result = await api(endpoint, { method: 'POST', body: JSON.stringify(payload) });
  removeTyping();

  if (result.error) {
    appendChatMsg(`Failed: <strong>${result.error}</strong>`, 'bot', true);
  } else {
    const status = result.status?.replace(/_/g,' ') || 'submitted';
    appendChatMsg(`Request submitted successfully. Status: <strong>${status}</strong>${result.risk ? ` · Risk: <strong>${result.risk.level}</strong>` : ''}`, 'bot', true);
    loadDashboard();
    loadEmployeeDropdowns();
  }
}

function cancelChat() {
  pendingChatPayload = null;
  appendChatMsg('Request cancelled.', 'bot', true);
}

function appendChatMsg(html, side, isHtml = false) {
  const el = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = `chat-msg ${side}`;
  const bubble = document.createElement('div');
  bubble.className = 'chat-bubble';
  if (isHtml) bubble.innerHTML = html;
  else bubble.textContent = html;
  div.appendChild(bubble);
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
}

function appendTyping() {
  const el = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'chat-msg bot';
  div.id = 'chat-typing';
  div.innerHTML = '<div class="chat-bubble"><div class="chat-typing"><span></span><span></span><span></span></div></div>';
  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
}

function removeTyping() {
  document.getElementById('chat-typing')?.remove();
}

// ── Init ──────────────────────────────────────────────────────────────────────
async function init() {
  await loadRoles();
  await loadEmployeeDropdowns();
  loadDashboard();
}
