
const API = '';
let TOKEN = localStorage.getItem('ec_token');
let currentInvoiceId = null;
let allInvoices = [];
let allClients = [];
let allProperties = [];

// ── AUTH ──────────────────────────────────
async function checkAuth() {
  if (!TOKEN) { window.location.href = '/login'; return; }
  try {
    const res = await apiFetch('/auth/me');
    if (!res.ok) {
      if (res.status === 401) {
        localStorage.removeItem('ec_token');
        window.location.href = '/login';
        return;
      }
      throw new Error('Auth fetch failed');
    }
    const admin = await res.json();
    currentUserRole = admin.role;
    document.getElementById('adminName').textContent = admin.full_name;
    document.getElementById('adminRole').textContent = admin.role === 'admin' ? '⭐ Admin' : 'Staff';
    document.getElementById('adminInitials').textContent = admin.full_name.split(' ').map(n=>n[0]).join('').slice(0,2).toUpperCase();

    // Show admin-only nav items
    if (admin.role === 'admin') {
      document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'flex');
    }
  } catch (e) {
    console.error('Auth check error:', e);
    localStorage.removeItem('ec_token');
    window.location.href = '/login';
  }
}

function logout() {
  localStorage.removeItem('ec_token');
  window.location.href = '/login';
}

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
}

async function apiFetch(path, options = {}) {
  return fetch(API + path, {
    ...options,
    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + TOKEN, ...options.headers }
  });
}

// ── NAVIGATION ────────────────────────────
function showSection(name) {
  if (['team', 'analytics-revenue', 'reports', 'sales-reps'].includes(name) && currentUserRole !== 'admin') {
    toast('Access restricted to administrators', 'error'); return;
  }
  ['dashboard','invoices','clients','properties','team','profile','verifications','analytics-revenue','reports','sales-reps'].forEach(s => {
    const el = document.getElementById('section-' + s);
    if (el) el.style.display = s === name ? '' : 'none';
  });
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  document.getElementById('nav-' + name)?.classList?.add('active');
  
  const titles = { 
    dashboard:'Overview', 
    invoices:'Invoices', 
    clients:'Clients', 
    properties:'Properties', 
    team:'Team Members', 
    profile:'My Profile', 
    verifications:'Pending Verifications',
    'analytics-revenue':'Revenue Analytics',
    'reports':'Reports & Exports',
    'sales-reps':'Sales Representatives'
  };
  document.getElementById('pageTitle').textContent = titles[name] || name;
  
  if (window.innerWidth <= 1024) {
    document.getElementById('sidebar').classList.remove('open');
  }

  if (name === 'dashboard') loadDashboard();
  if (name === 'invoices') loadInvoices();
  if (name === 'clients') loadClients();
  if (name === 'properties') loadProperties();
  if (name === 'team') loadTeam();
  if (name === 'profile') loadProfile();
  if (name === 'verifications') loadVerifications();
  if (name === 'sales-reps') loadSalesReps();
  if (name === 'analytics-revenue') loadAnalyticsRevenue();
}
let currentUserRole = 'staff';
let currentTimeframe = '30d';
let charts = {};

// ── DASHBOARD ANALYTICS ──────────────────
function getDates(tf) {
  const end = new Date();
  const start = new Date();
  if (tf === '7d') start.setDate(end.getDate() - 7);
  else if (tf === '30d') start.setDate(end.getDate() - 30);
  else if (tf === '90d') start.setDate(end.getDate() - 90);
  else if (tf === '12m') start.setMonth(end.getMonth() - 12);
  else if (tf === 'all') start.setFullYear(2000); // effectively all
  return { start: start.toISOString().split('T')[0], end: end.toISOString().split('T')[0] };
}

async function setTimeframe(tf) {
  currentTimeframe = tf;
  document.querySelectorAll('.tf-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tf-btn').forEach(b => b.style.background = 'transparent');
  document.querySelectorAll('.tf-btn').forEach(b => b.style.color = 'var(--dark)');
  
  const btn = document.getElementById('tf-' + tf);
  btn.classList.add('active');
  btn.style.background = 'var(--gold)';
  
  loadDashboard();
}

async function loadDashboard() {
  const { start, end } = getDates(currentTimeframe);
  const query = `?start=${start}&end=${end}`;

  try {
    const [kpiRes, trendRes, estateRes, statusRes, referralRes, activityRes, leaderboardRes] = await Promise.all([
      apiFetch('/api/analytics/kpis' + query).then(r => r.json()),
      apiFetch('/api/analytics/revenue-trend' + query).then(r => r.json()),
      apiFetch('/api/analytics/estates' + query).then(r => r.json()),
      apiFetch('/api/analytics/payment-status' + query).then(r => r.json()),
      apiFetch('/api/analytics/referral-sources' + query).then(r => r.json()),
      apiFetch('/api/analytics/activity?limit=15').then(r => r.json()),
      apiFetch('/api/analytics/rep-leaderboard' + query).then(r => r.json())
    ]);

    updateKPIs(kpiRes);
    renderRevenueChart(trendRes);
    renderStatusChart(statusRes);
    renderEstateChart(estateRes);
    renderReferralChart(referralRes);
    renderActivityFeed(activityRes);
    renderRepLeaderboard(leaderboardRes);

  } catch (e) {
    console.error('Dashboard load error:', e);
    toast('Error loading analytics data', 'error');
  }
}

// ── SALES REPS ────────────────────────────
async function loadSalesReps() {
  const container = document.getElementById('salesRepsTable');
  container.innerHTML = '<div class="loading"><span class="spinner"></span>Loading reps...</div>';
  try {
    const data = await apiFetch('/api/sales-reps/').then(r => r.json());
    container.innerHTML = data.length ? `
      <div class="table-responsive">
        <table class="data-table">
          <thead><tr><th>Rep Name</th><th>Email</th><th>Phone</th><th>Commission</th><th>Deals</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody>
            ${data.map(r => `
              <tr>
                <td style="font-weight:600;">${r.name}</td>
                <td style="font-size:12px;color:var(--gray);">${r.email || '—'}</td>
                <td>${r.phone || '—'}</td>
                <td>${r.commission_rate}%</td>
                <td style="font-weight:700;">${r.total_deals || 0}</td>
                <td><span class="status ${r.is_active ? 'paid' : 'unpaid'}"><span class="status-dot"></span>${r.is_active ? 'Active' : 'Inactive'}</span></td>
                <td><button class="action-btn" onclick="openEditRepModal('${r.id}')">Edit</button></td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>` : `<div class="empty-state"><p>No sales representatives found.</p></div>`;
  } catch(e) { container.innerHTML = '<div class="empty-state"><p>Error loading reps.</p></div>'; }
}

async function openAddRepModal() {
    ['sr-name','sr-email','sr-phone','sr-comm'].forEach(id => {
        const el = document.getElementById(id);
        if (id === 'sr-comm') el.value = '5.0';
        else el.value = '';
    });
    openModal('addRepModal');
}

async function submitAddRep() {
    const body = {
        name: document.getElementById('sr-name').value.trim(),
        email: document.getElementById('sr-email').value.trim() || null,
        phone: document.getElementById('sr-phone').value.trim() || null,
        commission_rate: parseFloat(document.getElementById('sr-comm').value)
    };
    if (!body.name) return toast('Name is required', 'error');
    try {
        const res = await apiFetch('/api/sales-reps/', { method: 'POST', body: JSON.stringify(body) });
        if (!res.ok) throw new Error('Failed to add rep');
        toast('Sales representative added successfully', 'success');
        closeModal('addRepModal');
        loadSalesReps();
    } catch(e) { toast(e.message, 'error'); }
}

async function openEditRepModal(id) {
    try {
        const res = await apiFetch(`/api/sales-reps/`).then(r => r.json());
        const rep = res.find(r => r.id === id);
        if (!rep) throw new Error('Representative not found');

        document.getElementById('edit-sr-id').value = rep.id;
        document.getElementById('edit-sr-name').value = rep.name;
        document.getElementById('edit-sr-email').value = rep.email || '';
        document.getElementById('edit-sr-phone').value = rep.phone || '';
        document.getElementById('edit-sr-comm').value = rep.commission_rate;
        
        // Handle radio buttons for status
        if (rep.is_active) {
            document.getElementById('edit-sr-active').checked = true;
        } else {
            document.getElementById('edit-sr-inactive').checked = true;
        }

        openModal('editRepModal');
    } catch(e) { toast(e.message, 'error'); }
}

async function submitEditRep() {
    const id = document.getElementById('edit-sr-id').value;
    const body = {
        name: document.getElementById('edit-sr-name').value.trim(),
        email: document.getElementById('edit-sr-email').value.trim() || null,
        phone: document.getElementById('edit-sr-phone').value.trim() || null,
        commission_rate: parseFloat(document.getElementById('edit-sr-comm').value),
        is_active: document.getElementById('edit-sr-active').checked
    };

    if (!body.name) return toast('Name is required', 'error');

    try {
        const res = await apiFetch(`/api/sales-reps/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(body)
        });
        if (!res.ok) throw new Error('Failed to update representative');
        toast('Sales representative updated successfully', 'success');
        closeModal('editRepModal');
        loadSalesReps();
    } catch(e) { toast(e.message, 'error'); }
}

async function openResolveModal(id, name) {
    document.getElementById('unmatched-id').value = id;
    document.getElementById('unmatched-name-display').textContent = name;
    document.getElementById('resolve-target-id').value = '';
    document.querySelector('#resolve-rep-search input[type="text"]').value = '';
    openModal('resolveRepModal');
}

async function submitResolve() {
    const body = {
        unmatched_id: document.getElementById('unmatched-id').value,
        target_rep_id: document.getElementById('resolve-target-id').value
    };
    if (!body.target_rep_id) return toast('Please select a target representative', 'error');
    try {
        const res = await apiFetch('/api/sales-reps/resolve', { method: 'POST', body: JSON.stringify(body) });
        if (!res.ok) throw new Error('Failed to resolve name');
        toast('Name resolved successfully', 'success');
        closeModal('resolveRepModal');
        loadSalesReps();
    } catch(e) { toast(e.message, 'error'); }
}

// ── REPORTS ───────────────────────────────
async function downloadReport(event) {
  const type = document.getElementById('report-type').value;
  const start = document.getElementById('report-start').value;
  const end = document.getElementById('report-end').value;
  const format = document.querySelector('input[name="report-format"]:checked').value;

  if (!start || !end) return toast('Please select date range', 'error');

  const btn = event ? event.currentTarget : document.querySelector('button[onclick="downloadReport(event)"]');
  const originalHtml = btn ? btn.innerHTML : 'Generate & Download';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Generating...';
  }

  try {
    const query = `?report_type=${type}&start_date=${start}&end_date=${end}&format=${format}`;
    const res = await apiFetch('/api/reports/download' + query);
    if (!res.ok) throw new Error('Report generation failed');
    
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${type}_${start}_to_${end}.${format === 'excel' ? 'xlsx' : 'pdf'}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    toast('Report downloaded successfully', 'success');
  } catch(e) { toast(e.message, 'error'); }
  finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    }
  }
}

function openScheduleModal() {
  openModal('scheduleModal');
  document.getElementById('sched-type').value = 'sales_summary';
  document.getElementById('sched-format').value = 'pdf';
  document.getElementById('sched-freq').value = 'weekly';
  document.getElementById('sched-day-weekly').value = '1';
  document.getElementById('sched-day-monthly').value = '1';
  document.getElementById('sched-time').value = '08:00';
  document.getElementById('sched-recipients').value = currentUserRole === 'admin' ? '' : localStorage.getItem('ec_email') || '';
  toggleScheduleOptions();
}

function toggleScheduleOptions() {
  const freq = document.getElementById('sched-freq').value;
  document.getElementById('sched-day-weekly-group').style.display = freq === 'weekly' ? 'block' : 'none';
  document.getElementById('sched-day-monthly-group').style.display = freq === 'monthly' ? 'block' : 'none';
}

async function submitSchedule() {
  const freq = document.getElementById('sched-freq').value;
  const recipsStr = document.getElementById('sched-recipients').value;
  
  if (!recipsStr.trim()) return toast('Please enter at least one recipient email', 'error');

  const emails = recipsStr.split(',').map(s => s.trim()).filter(Boolean);

  const body = {
    report_type: document.getElementById('sched-type').value,
    frequency: freq,
    format: document.getElementById('sched-format').value,
    recipients: emails
  };

  try {
    const res = await apiFetch('/api/reports/schedules', {
      method: 'POST',
      body: JSON.stringify(body)
    });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || 'Failed to create schedule');
    }
    toast('Report schedule created successfully', 'success');
    closeModal('scheduleModal');
    loadSchedules(); // to refresh the list, though currently just stubbed functionality
  } catch(e) { toast(e.message, 'error'); }
}

async function loadSchedules() {
  const container = document.getElementById('scheduledReportsList');
  try {
    const res = await apiFetch('/api/reports/schedules');
    if (!res.ok) throw new Error('Fetch failed');
    const data = await res.json();
    
    if (!data.length) {
      container.innerHTML = `
        <div style="background:#f8fafc; border:1px dashed #e2e8f0; border-radius:8px; padding:24px; text-align:center;">
          <div style="font-size:13px; color:var(--gray);">No scheduled reports yet.</div>
          <button class="btn btn-ghost" style="margin-top:12px; font-size:11px;" onclick="openScheduleModal()">+ Setup Schedule</button>
        </div>
      `;
      return;
    }
    
    container.innerHTML = `
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th>Report</th>
              <th>Frequency</th>
              <th>Format</th>
              <th>Recipients</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${data.map(s => `
              <tr>
                <td style="font-weight:600; text-transform:capitalize;">${s.report_type.replace('_', ' ')}</td>
                <td style="text-transform:capitalize;">${s.frequency}</td>
                <td style="text-transform:uppercase;">${s.format}</td>
                <td style="max-width:150px; overflow:hidden; text-overflow:ellipsis;" title="${s.recipients.join(', ')}">${s.recipients.length} Recipient(s)</td>
                <td>${s.is_active ? '<span style="color:var(--green)">Active</span>' : '<span style="color:var(--gray)">Paused</span>'}</td>
                <td>
                  <button class="action-btn" style="color:var(--red); border-color:#feb2b2;" onclick="deleteSchedule('${s.id}')">Delete</button>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
        <div style="margin-top:16px;">
          <button class="btn btn-ghost" style="font-size:12px;" onclick="openScheduleModal()">+ Setup Additional Schedule</button>
        </div>
      </div>
    `;
  } catch(e) {
    console.error(e);
  }
}

async function deleteSchedule(id) {
  if (!confirm('Are you sure you want to delete this schedule?')) return;
  try {
    const res = await apiFetch(`/api/reports/schedules/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete');
    loadSchedules();
  } catch(e) { toast(e.message, 'error'); }
}

// ── ANALYTICS REVENUE SECTION ────

async function loadAnalyticsRevenue() {
    const startInput = document.getElementById('ana-start');
    const endInput = document.getElementById('ana-end');
    
    // Set default dates if empty
    if (!startInput.value || !endInput.value) {
        const { start, end } = getDates('30d');
        startInput.value = start;
        endInput.value = end;
    }

    const query = `?start=${startInput.value}&end=${endInput.value}`;
    
    try {
        const [trendRes, estateRes, statusRes, leaderboardRes] = await Promise.all([
          apiFetch('/api/analytics/revenue-trend' + query).then(r => r.json()),
          apiFetch('/api/analytics/estates' + query).then(r => r.json()),
          apiFetch('/api/analytics/payment-status' + query).then(r => r.json()),
          apiFetch('/api/analytics/rep-leaderboard' + query).then(r => r.json())
        ]);

        renderAnaRevenueChart(trendRes);
        renderAnaEstateChart(estateRes);
        renderAnaStatusChart(statusRes);
        renderAnaRepLeaderboard(leaderboardRes);

    } catch (e) {
        console.error('Analytics load error:', e);
        toast('Error loading analytics data', 'error');
    }
}

function renderAnaRevenueChart(data) {
  const container = document.getElementById('anaRevenueChart').parentElement;
  if (!data.labels || data.labels.length === 0 || (data.invoiced.every(v => v === 0) && data.collected.every(v => v === 0))) {
    container.innerHTML = '<div class="empty-state" style="height:100%; display:flex; align-items:center; justify-content:center; color:var(--gray); font-size:13px;">No revenue data for this period</div>';
    return;
  }
  container.innerHTML = '<canvas id="anaRevenueChart"></canvas>';
  if (charts.anaRevenue) charts.anaRevenue.destroy();
  const ctx = document.getElementById('anaRevenueChart').getContext('2d');
  charts.anaRevenue = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.labels,
      datasets: [
        { label: 'Invoiced', data: data.invoiced, borderColor: '#F5A623', backgroundColor: 'rgba(245,170,35,0.1)', fill: true, tension: 0.4 },
        { label: 'Collected', data: data.collected, borderColor: '#2ecc71', backgroundColor: 'transparent', borderDash: [5, 5], tension: 0.4 }
      ]
    },
    options: { responsive: true, maintainAspectRatio: false }
  });
}

function renderAnaEstateChart(data) {
  const container = document.getElementById('anaEstateChart').parentElement;
  if (!data.length) {
    container.innerHTML = '<div class="empty-state" style="height:100%; display:flex; align-items:center; justify-content:center; color:var(--gray); font-size:13px;">No estate sales data for this period</div>';
    return;
  }
  container.innerHTML = '<canvas id="anaEstateChart"></canvas>';
  if (charts.anaEstate) charts.anaEstate.destroy();
  const ctx = document.getElementById('anaEstateChart').getContext('2d');
  charts.anaEstate = new Chart(ctx, {
    type: 'pie',
    data: {
      labels: data.map(d => d.name),
      datasets: [{
        data: data.map(d => d.revenue),
        backgroundColor: ['#F5A623', '#2ecc71', '#3498db', '#e74c3c', '#9b59b6', '#f1c40f'],
        borderWidth: 0
      }]
    },
    options: { responsive: true, maintainAspectRatio: false }
  });
}

function renderAnaStatusChart(data) {
  const container = document.getElementById('anaStatusChart').parentElement;
  if (data.paid === 0 && data.partial === 0 && data.unpaid === 0) {
    container.innerHTML = '<div class="empty-state" style="height:100%; display:flex; align-items:center; justify-content:center; color:var(--gray); font-size:13px;">No payment status data</div>';
    return;
  }
  container.innerHTML = '<canvas id="anaStatusChart"></canvas>';
  if (charts.anaStatus) charts.anaStatus.destroy();
  const ctx = document.getElementById('anaStatusChart').getContext('2d');
  charts.anaStatus = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['Paid', 'Partial', 'Unpaid'],
      datasets: [{
        label: 'Invoices',
        data: [data.paid, data.partial, data.unpaid],
        backgroundColor: ['#2ecc71', '#f39c12', '#e74c3c'],
        borderRadius: 4
      }]
    },
    options: { responsive: true, maintainAspectRatio: false }
  });
}

function renderAnaRepLeaderboard(data) {
  const container = document.getElementById('anaRepLeaderboard');
  if (!data.length) {
    container.innerHTML = '<div class="empty-state"><p>No sales data for this period.</p></div>';
    return;
  }
  container.innerHTML = `
    <div class="table-responsive">
      <table class="data-table">
        <thead><tr><th>Rep Name</th><th>Deals</th><th>Revenue</th><th>Col. Rate</th></tr></thead>
        <tbody>
          ${data.map(r => `
            <tr>
              <td style="font-weight:600;">${r.rep_name}</td>
              <td>${r.deals}</td>
              <td style="font-weight:600;">${fmtNGN(r.total_value)}</td>
              <td>
                <div style="display:flex; align-items:center; gap:8px;">
                  <div style="flex:1; height:6px; background:#f0f0f0; border-radius:3px; overflow:hidden;">
                    <div style="width:${r.collection_rate}%; height:100%; background:var(--green);"></div>
                  </div>
                  <span style="font-size:11px; font-weight:600; color:var(--green);">${r.collection_rate.toFixed(0)}%</span>
                </div>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

// ── KPI UPDATES ───────────────────────────
function updateKPIs(data) {
  document.getElementById('stat-invoiced').textContent = fmtNGN(data.total_revenue);
  document.getElementById('stat-collected').textContent = fmtNGN(data.amount_collected);
  document.getElementById('stat-clients').textContent = data.new_clients;
  document.getElementById('stat-pending').textContent = data.pending_verifications;

  const fmtDelta = (val) => {
    if (val === null) return '--';
    const color = val >= 0 ? 'var(--green)' : 'var(--red)';
    const sign = val >= 0 ? '+' : '';
    return `<span style="color:${color}">${sign}${val.toFixed(1)}%</span> vs prev`;
  };

  if (data.delta) {
    document.getElementById('stat-rev-delta').innerHTML = fmtDelta(data.delta.total_revenue);
    document.getElementById('stat-col-delta').innerHTML = fmtDelta(data.delta.amount_collected);
    document.getElementById('stat-cli-delta').innerHTML = fmtDelta(data.delta.new_clients);
  }
}

function renderRevenueChart(data) {
  const container = document.getElementById('revenueChart').parentElement;
  if (!data.labels || data.labels.length === 0 || (data.invoiced.every(v => v === 0) && data.collected.every(v => v === 0))) {
    container.innerHTML = '<div class="empty-state" style="height:100%; display:flex; align-items:center; justify-content:center; color:var(--gray); font-size:13px;">No revenue data for this period</div>';
    return;
  }
  container.innerHTML = '<canvas id="revenueChart"></canvas>';
  if (charts.revenue) charts.revenue.destroy();
  const ctx = document.getElementById('revenueChart').getContext('2d');
  charts.revenue = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.labels,
      datasets: [
        { label: 'Invoiced', data: data.invoiced, borderColor: '#F5A623', backgroundColor: 'rgba(245,170,35,0.1)', fill: true, tension: 0.4 },
        { label: 'Collected', data: data.collected, borderColor: '#2ecc71', backgroundColor: 'transparent', borderDash: [5, 5], tension: 0.4 }
      ]
    },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'top' } } }
  });
}

function renderStatusChart(data) {
  const container = document.getElementById('statusChart').parentElement;
  if (data.paid === 0 && data.partial === 0 && data.unpaid === 0) {
    container.innerHTML = '<div class="empty-state" style="height:100%; display:flex; align-items:center; justify-content:center; color:var(--gray); font-size:13px;">No payment status data</div>';
    return;
  }
  container.innerHTML = '<canvas id="statusChart"></canvas>';
  if (charts.status) charts.status.destroy();
  const ctx = document.getElementById('statusChart').getContext('2d');
  charts.status = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Paid', 'Partial', 'Unpaid'],
      datasets: [{
        data: [data.paid, data.partial, data.unpaid],
        backgroundColor: ['#2ecc71', '#f39c12', '#e74c3c'],
        borderWidth: 0
      }]
    },
    options: { responsive: true, maintainAspectRatio: false, cutout: '70%' }
  });
}

function renderEstateChart(data) {
  const container = document.getElementById('estateChart').parentElement;
  if (!data.length) {
    container.innerHTML = '<div class="empty-state" style="height:100%; display:flex; align-items:center; justify-content:center; color:var(--gray); font-size:13px;">No estate data available</div>';
    return;
  }
  container.innerHTML = '<canvas id="estateChart"></canvas>';
  if (charts.estate) charts.estate.destroy();
  const ctx = document.getElementById('estateChart').getContext('2d');
  charts.estate = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.map(d => d.name),
      datasets: [{
        label: 'Revenue',
        data: data.map(d => d.revenue),
        backgroundColor: '#F5A623',
        borderRadius: 4
      }]
    },
    options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y' }
  });
}

function renderReferralChart(data) {
  if (charts.referral) charts.referral.destroy();
  const ctx = document.getElementById('referralChart').getContext('2d');
  charts.referral = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.map(d => d.source),
      datasets: [{
        label: 'Clients',
        data: data.map(d => d.count),
        backgroundColor: '#3498db',
        borderRadius: 4
      }]
    },
    options: { responsive: true, maintainAspectRatio: false }
  });
}

function renderActivityFeed(data) {
  const container = document.getElementById('activityFeed');
  if (!data.length) {
    container.innerHTML = '<div style="padding:40px; text-align:center; color:#999; font-size:13px;">No recent activity</div>';
    return;
  }
  container.innerHTML = data.map(a => `
    <div style="padding:12px 20px; border-bottom:1px solid #f8f8f8; display:flex; gap:12px; align-items:flex-start;">
      <div style="width:8px; height:8px; border-radius:50%; background:var(--gold); margin-top:6px; flex-shrink:0;"></div>
      <div>
        <div style="font-size:13px; color:var(--dark); line-height:1.4;">
          <strong>${a.performed_by_name}</strong> ${a.description}
        </div>
        <div style="font-size:11px; color:var(--gray); margin-top:4px;">
          ${new Date(a.created_at).toLocaleString()}
        </div>
      </div>
    </div>
  `).join('');
}

function renderRepLeaderboard(data) {
  const container = document.getElementById('repLeaderboard');
  if (!data.length) {
    container.innerHTML = '<div class="empty-state"><p>No sales data for this period.</p></div>';
    return;
  }
  container.innerHTML = `
    <div class="table-responsive">
      <table class="data-table">
        <thead><tr><th>Rep Name</th><th>Deals</th><th>Revenue</th><th>Col. Rate</th></tr></thead>
        <tbody>
          ${data.map(r => `
            <tr>
              <td style="font-weight:600;">${r.rep_name}</td>
              <td>${r.deals}</td>
              <td style="font-weight:600;">${fmtNGN(r.total_value)}</td>
              <td>
                <div style="display:flex; align-items:center; gap:8px;">
                  <div style="flex:1; height:6px; background:#f0f0f0; border-radius:3px; overflow:hidden;">
                    <div style="width:${r.collection_rate}%; height:100%; background:var(--green);"></div>
                  </div>
                  <span style="font-size:11px; font-weight:600; color:var(--green);">${r.collection_rate.toFixed(0)}%</span>
                </div>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

// ── INVOICES TABLE ────────────────────────
let originalDueDate = null;

async function loadInvoices() {
  document.getElementById('invoicesTable').innerHTML = '<div class="loading"><span class="spinner"></span>Loading...</div>';
  const data = await apiFetch('/api/invoices/').then(r => r.json());
  allInvoices = data;
  document.getElementById('invoicesTable').innerHTML = data.length ? `
    <div class="table-responsive">
      <table class="data-table">
        <thead><tr><th>Invoice No</th><th>Client</th><th>Property</th><th>Amount</th><th>Paid</th><th>Balance</th><th>Status</th><th>Actions</th></tr></thead>
        <tbody>
          ${data.map(inv => `
            <tr>
              <td style="font-weight:700;color:var(--gold-dark);font-size:12px;">${inv.invoice_number}</td>
              <td><div class="client-name">${inv.clients?.full_name || '—'}</div><div class="client-email">${inv.invoice_date}</div></td>
              <td style="font-size:12px;color:var(--gray);">${inv.property_name || '—'}</td>
              <td style="font-weight:600;">${fmtNGN(inv.amount)}</td>
              <td style="color:var(--green);font-weight:600;">${fmtNGN(inv.amount_paid)}</td>
              <td style="font-weight:600;">${fmtNGN(inv.balance_due)}</td>
              <td><span class="status ${inv.status}"><span class="status-dot"></span>${inv.status}</span></td>
              <td style="display:flex;gap:4px;flex-wrap:wrap;">
                <button class="action-btn" onclick="openEditInvoiceModal('${inv.id}')">Edit</button>
                <button class="action-btn" onclick="openViewPaymentsModal('${inv.id}')">Payments</button>
                <button class="action-btn gold" onclick="openSendModal('${inv.id}', '${inv.invoice_number}', '${inv.clients?.full_name}', '${inv.clients?.email}')">Send</button>
                <a href="/api/invoices/${inv.id}/pdf/invoice" target="_blank" class="action-btn" style="text-decoration:none;display:inline-block;">Invoice</a>
                ${inv.amount_paid > 0 ? `<a href="/api/invoices/${inv.id}/pdf/receipt" target="_blank" class="action-btn" style="text-decoration:none;display:inline-block;">Receipt</a>` : ''}
                <a href="/api/invoices/${inv.id}/pdf/statement" target="_blank" class="action-btn" style="text-decoration:none;display:inline-block;">Statement</a>
                ${currentUserRole === 'admin' ? `<button class="action-btn" style="color:var(--red);border-color:#feb2b2;" onclick="openVoidModal('${inv.id}')">Void</button>` : ''}
              </td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>` : `<div class="empty-state"><p>No invoices yet. Create your first invoice.</p></div>`;
}

async function openEditInvoiceModal(id) {
  try {
    const res = await apiFetch(`/api/invoices/${id}`);
    if (!res.ok) throw new Error('Invoice not found');
    const inv = await res.json();
    
    if (inv.status === 'paid' && currentUserRole !== 'admin') {
      return toast('Fully paid invoices cannot be edited by staff.', 'error');
    }
    
    document.getElementById('edit-inv-id').value = inv.id;
    document.getElementById('edit-inv-terms').value = inv.payment_terms || '';
    document.getElementById('edit-inv-due').value = inv.due_date || '';
    document.getElementById('edit-inv-rep').value = inv.sales_rep_name || '';
    document.getElementById('edit-inv-prop').value = inv.property_name || '';
    document.getElementById('edit-inv-notes').value = inv.notes || '';
    
    originalDueDate = inv.due_date;
    document.getElementById('edit-inv-due-reason').value = '';
    document.getElementById('edit-inv-due-reason-group').style.display = 'none';
    
    // Add event listener to show reason input if due date changes
    const dueInput = document.getElementById('edit-inv-due');
    dueInput.onchange = function() {
      if (this.value !== originalDueDate) {
        document.getElementById('edit-inv-due-reason-group').style.display = 'block';
      } else {
        document.getElementById('edit-inv-due-reason-group').style.display = 'none';
      }
    };
    
    const isStaff = currentUserRole === 'staff';
    const termsInput = document.getElementById('edit-inv-terms');
    const repInput = document.getElementById('edit-inv-rep');
    const propInput = document.getElementById('edit-inv-prop');
    
    if (isStaff) {
      termsInput.classList.add('locked-field'); termsInput.disabled = true;
      repInput.classList.add('locked-field'); repInput.readOnly = true;
      propInput.classList.add('locked-field'); propInput.readOnly = true;
      document.querySelectorAll('.edit-inv-admin-lock').forEach(el => el.style.display = 'block');
    } else {
      termsInput.classList.remove('locked-field'); termsInput.disabled = false;
      repInput.classList.remove('locked-field'); repInput.readOnly = false;
      propInput.classList.remove('locked-field'); propInput.readOnly = false;
      document.querySelectorAll('.edit-inv-admin-lock').forEach(el => el.style.display = 'none');
    }
    
    openModal('editInvoiceModal');
  } catch(e) { toast(e.message, 'error'); }
}

async function submitEditInvoice() {
  const id = document.getElementById('edit-inv-id').value;
  const newDue = document.getElementById('edit-inv-due').value;
  
  const body = {
    due_date: newDue,
    notes: document.getElementById('edit-inv-notes').value
  };
  
  if (currentUserRole === 'admin') {
    body.payment_terms = document.getElementById('edit-inv-terms').value;
    body.sales_rep_name = document.getElementById('edit-inv-rep').value || null;
    body.property_name = document.getElementById('edit-inv-prop').value || null;
  }
  
  if (newDue !== originalDueDate) {
    const reason = document.getElementById('edit-inv-due-reason').value.trim();
    if (!reason) return toast('Reason is required when changing due date', 'error');
    body.reason_for_change = reason;
  }
  
  try {
    const res = await apiFetch(`/api/invoices/${id}/edit`, { method: 'PATCH', body: JSON.stringify(body) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to update invoice');
    toast('Invoice updated successfully', 'success');
    closeModal('editInvoiceModal');
    loadInvoices();
  } catch(e) { toast(e.message, 'error'); }
}

async function openViewPaymentsModal(invoiceId) {
  openModal('viewPaymentsModal');
  const container = document.getElementById('invoicePaymentsList');
  container.innerHTML = '<div class="loading" style="padding: 24px;"><span class="spinner"></span>Loading payments...</div>';
  
  try {
    const res = await apiFetch(`/api/invoices/${invoiceId}`);
    if (!res.ok) throw new Error('Failed to fetch payments');
    const inv = await res.json();
    
    if (!inv.payments || !inv.payments.length) {
      container.innerHTML = '<div class="empty-state" style="padding: 40px;"><p>No payments recorded for this invoice.</p></div>';
      return;
    }
    
    container.innerHTML = `
      <div class="table-responsive">
        <table class="data-table" style="margin: 0; border: none;">
          <thead>
            <tr style="background: #f8fafc;">
              <th style="padding-left: 24px;">Date</th>
              <th>Reference</th>
              <th>Method</th>
              <th>Amount</th>
              <th style="padding-right: 24px;">Actions</th>
            </tr>
          </thead>
          <tbody>
            ${inv.payments.map(p => `
              <tr>
                <td style="padding-left: 24px;">${p.payment_date}</td>
                <td style="font-weight: 600;">${p.reference}</td>
                <td>${p.payment_method}</td>
                <td style="color: var(--green); font-weight: 600;">${fmtNGN(p.amount)}</td>
                <td style="padding-right: 24px;">
                  ${currentUserRole === 'admin' ? `<button class="action-btn" onclick='openEditPaymentModal(${JSON.stringify(p).replace(/'/g, "&#39;")})'>Edit</button>` : '<span style="color:var(--gray);font-size:11px;">Admin Only</span>'}
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  } catch(e) { container.innerHTML = `<div class="empty-state" style="padding: 40px;"><p>${e.message}</p></div>`; }
}

function openEditPaymentModal(payment) {
  document.getElementById('edit-pay-id').value = payment.id;
  document.getElementById('edit-pay-ref').value = payment.reference;
  document.getElementById('edit-pay-amount').value = payment.amount;
  document.getElementById('edit-pay-date').value = payment.payment_date;
  document.getElementById('edit-pay-method').value = payment.payment_method;
  document.getElementById('edit-pay-notes').value = payment.notes || '';
  
  // Close view payments to not overlay weirdly, or just keep it open underneath?
  // Let's hide viewPaymentsModal while editing
  closeModal('viewPaymentsModal');
  openModal('editPaymentModal');
}

async function submitEditPayment() {
  const id = document.getElementById('edit-pay-id').value;
  const body = {
    reference: document.getElementById('edit-pay-ref').value,
    amount: parseFloat(document.getElementById('edit-pay-amount').value),
    payment_date: document.getElementById('edit-pay-date').value,
    payment_method: document.getElementById('edit-pay-method').value,
    notes: document.getElementById('edit-pay-notes').value
  };
  
  if (!body.reference || !body.amount || !body.payment_date) return toast('Reference, amount, and date are required', 'error');
  
  try {
    const res = await apiFetch(`/api/payments/${id}`, { method: 'PATCH', body: JSON.stringify(body) });
    if (!res.ok) throw new Error('Failed to update payment');
    toast('Payment updated successfully', 'success');
    closeModal('editPaymentModal');
    loadInvoices(); // Refresh invoices list to reflect new totals
    if (document.getElementById('section-dashboard').style.display === '') loadDashboard();
  } catch(e) { toast(e.message, 'error'); }
}

// ── CLIENTS TABLE ─────────────────────────
async function loadClients() {
  const data = await apiFetch('/api/clients/').then(r => r.json());
  allClients = data;
  document.getElementById('clientsTable').innerHTML = data.length ? `
    <div class="table-responsive">
      <table class="data-table">
        <thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Location</th><th>Added</th></tr></thead>
        <tbody>
          ${data.map(c => `
            <tr>
              <td><div class="client-name">${c.full_name}</div></td>
              <td>${c.email}</td>
              <td>${c.phone || '—'}</td>
              <td style="font-size:12px;color:var(--gray);">${[c.city, c.state].filter(Boolean).join(', ') || '—'}</td>
              <td style="font-size:12px;color:var(--gray);">${new Date(c.created_at).toLocaleDateString()}</td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>` : `<div class="empty-state"><p>No clients yet.</p></div>`;
}

// ── PROPERTIES TABLE ──────────────────────
// ── PROPERTIES TABLE ──────────────────────
let activePropTab = 'active';

function setPropTab(tab) {
  activePropTab = tab;
  document.getElementById('prop-tab-active').classList.toggle('active', tab === 'active');
  document.getElementById('prop-tab-active').style.color = tab === 'active' ? 'var(--dark)' : 'var(--gray)';
  document.getElementById('prop-tab-archived').classList.toggle('active', tab === 'archived');
  document.getElementById('prop-tab-archived').style.color = tab === 'archived' ? 'var(--dark)' : 'var(--gray)';
  loadProperties();
}

async function loadProperties() {
  document.getElementById('propertiesTable').innerHTML = '<div class="loading"><span class="spinner"></span>Loading properties...</div>';
  const data = await apiFetch(`/api/properties/${activePropTab === 'archived' ? 'archived' : ''}`).then(r => r.json());
  if (activePropTab === 'active') allProperties = data;
  document.getElementById('propertiesTable').innerHTML = data.length ? `
    <div class="table-responsive">
      <table class="data-table">
        <thead><tr><th>Property Name</th><th>Location</th><th>Plot Size</th><th>Price</th><th>Actions</th></tr></thead>
        <tbody>
          ${data.map(p => `
            <tr>
              <td><div class="client-name">${p.name}</div><div class="client-email">${p.estate_name || ''}</div></td>
              <td>${p.location}</td>
              <td>${p.plot_size_sqm ? p.plot_size_sqm + ' sqm' : '—'}</td>
              <td style="font-weight:600;">${fmtNGN(p.starting_price || p.total_price)}</td>
              <td>
                <button class="action-btn" onclick="openEditPropertyModal('${p.id}')">Edit</button>
                ${activePropTab === 'active' ? 
                  `<button class="action-btn" style="color:var(--gray);border-color:#ccc;" onclick="togglePropertyArchive('${p.id}', true)">Archive</button>` : 
                  `<button class="action-btn gold" onclick="togglePropertyArchive('${p.id}', false)">Restore</button>`}
              </td>
            </tr>`).join('')}
        </tbody>
      </table>
    </div>` : `<div class="empty-state"><p>No ${activePropTab} properties found.</p></div>`;
}

async function togglePropertyArchive(id, archive) {
  try {
    const res = await apiFetch(`/api/properties/${id}/${archive ? 'archive' : 'restore'}`, { method: 'PATCH' });
    if (!res.ok) throw new Error('Failed to update property status');
    toast(`Property ${archive ? 'archived' : 'restored'}`, 'success');
    loadProperties();
  } catch(e) { toast(e.message, 'error'); }
}

function openAddPropertyModal() { openModal('addPropertyModal'); }

async function submitProperty() {
  const body = {
    name: document.getElementById('prop-name').value,
    estate_name: document.getElementById('prop-estate').value,
    location: document.getElementById('prop-location').value,
    plot_size_sqm: document.getElementById('prop-size').value ? parseFloat(document.getElementById('prop-size').value) : null,
    total_price: parseFloat(document.getElementById('prop-price').value),
    description: document.getElementById('prop-desc').value,
  };
  if (!body.name || !body.location || isNaN(body.total_price)) return toast('Name, location, and price are required', 'error');
  try {
    const res = await apiFetch('/api/properties/', { method: 'POST', body: JSON.stringify(body) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed');
    toast(`Property ${data.property.name} added`, 'success');
    closeModal('addPropertyModal');
    allProperties = [];
    loadProperties();
  } catch(e) { toast(e.message, 'error'); }
}

async function openEditPropertyModal(id) {
  try {
    const res = await apiFetch(`/api/properties/${id}`);
    if (!res.ok) throw new Error('Property not found');
    const p = await res.json();
    document.getElementById('edit-prop-id').value = p.id;
    document.getElementById('edit-prop-name').value = p.name;
    document.getElementById('edit-prop-estate').value = p.estate_name || '';
    document.getElementById('edit-prop-location').value = p.location;
    document.getElementById('edit-prop-size').value = p.plot_size_sqm || '';
    document.getElementById('edit-prop-price').value = p.starting_price || p.total_price || '';
    document.getElementById('edit-prop-desc').value = p.description || '';
    openModal('editPropertyModal');
  } catch(e) { toast(e.message, 'error'); }
}

async function submitEditProperty() {
  const id = document.getElementById('edit-prop-id').value;
  const body = {
    name: document.getElementById('edit-prop-name').value,
    estate_name: document.getElementById('edit-prop-estate').value,
    location: document.getElementById('edit-prop-location').value,
    plot_size_sqm: document.getElementById('edit-prop-size').value ? parseFloat(document.getElementById('edit-prop-size').value) : null,
    starting_price: parseFloat(document.getElementById('edit-prop-price').value),
    description: document.getElementById('edit-prop-desc').value,
  };
  if (!body.name || !body.location || isNaN(body.starting_price)) return toast('Name, location, and price are required', 'error');
  try {
    const res = await apiFetch(`/api/properties/${id}`, { method: 'PUT', body: JSON.stringify(body) });
    if (!res.ok) throw new Error('Failed to update property');
    toast('Property updated successfully', 'success');
    closeModal('editPropertyModal');
    loadProperties();
  } catch(e) { toast(e.message, 'error'); }
}

// ── MODALS ────────────────────────────────
function openModal(id) { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

async function openNewInvoiceModal() {
  if (!allClients.length) allClients = await apiFetch('/api/clients/').then(r => r.json());
  if (!allProperties.length) allProperties = await apiFetch('/api/properties/').then(r => r.json());
  
  // Clear search fields
  document.querySelector('#inv-client-search input[type="text"]').value = '';
  document.getElementById('inv-client').value = '';
  document.querySelector('#inv-property-search input[type="text"]').value = '';
  document.getElementById('inv-property').value = '';
  document.getElementById('inv-property-name').value = '';
  document.getElementById('inv-location').value = '';
  document.getElementById('inv-size').value = '';
  document.getElementById('inv-amount').value = '';
  document.getElementById('inv-notes').value = '';

  const today = new Date().toISOString().split('T')[0];
  document.getElementById('inv-date').value = today;
  document.getElementById('inv-due').value = today;
  openModal('newInvoiceModal');
}

async function submitInvoice() {
  const body = {
    client_id: document.getElementById('inv-client').value,
    property_id: document.getElementById('inv-property').value || null,
    property_name: document.getElementById('inv-property-name').value,
    property_location: document.getElementById('inv-location').value,
    plot_size_sqm: document.getElementById('inv-size').value ? parseFloat(document.getElementById('inv-size').value) : null,
    amount: parseFloat(document.getElementById('inv-amount').value),
    payment_terms: document.getElementById('inv-terms').value,
    invoice_date: document.getElementById('inv-date').value,
    due_date: document.getElementById('inv-due').value,
    notes: document.getElementById('inv-notes').value,
  };

  if (!body.client_id || !body.amount || !body.invoice_date) {
    return toast('Please fill in all required fields', 'error');
  }

  try {
    const res = await apiFetch('/api/invoices/', { method: 'POST', body: JSON.stringify(body) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed');

    const sendNow = document.getElementById('inv-send-now').checked;
    if (sendNow) {
      await apiFetch('/api/invoices/send', {
        method: 'POST',
        body: JSON.stringify({ invoice_id: data.invoice.id, document_types: ['invoice'] })
      });
      toast('Invoice created and sent to client!', 'success');
    } else {
      toast(`Invoice ${data.invoice.invoice_number} created successfully`, 'success');
    }

    closeModal('newInvoiceModal');
    allInvoices = [];
    loadDashboard();
  } catch(e) { toast(e.message, 'error'); }
}

async function openRecordPaymentModal() {
  if (!allInvoices.length) allInvoices = await apiFetch('/api/invoices/').then(r => r.json());
  
  // Clear fields
  document.querySelector('#pay-invoice-search input[type="text"]').value = '';
  document.getElementById('pay-invoice').value = '';
  document.getElementById('pay-client-display').value = '';
  document.getElementById('pay-client-id').value = '';
  document.getElementById('pay-amount').value = '';
  document.getElementById('pay-ref').value = '';
  document.getElementById('pay-notes').value = '';

  document.getElementById('pay-date').value = new Date().toISOString().split('T')[0];
  openModal('recordPaymentModal');
}

async function submitPayment() {
  const body = {
    invoice_id: document.getElementById('pay-invoice').value,
    client_id: document.getElementById('pay-client-id').value,
    reference: document.getElementById('pay-ref').value,
    amount: parseFloat(document.getElementById('pay-amount').value),
    payment_method: document.getElementById('pay-method').value,
    payment_date: document.getElementById('pay-date').value,
    notes: document.getElementById('pay-notes').value,
  };
  if (!body.invoice_id || !body.reference || !body.amount) return toast('Fill all required fields', 'error');

  try {
    const res = await apiFetch('/api/payments/', { method: 'POST', body: JSON.stringify(body) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed');

    if (document.getElementById('pay-send-receipt').checked) {
      await apiFetch('/api/invoices/send', {
        method: 'POST',
        body: JSON.stringify({ invoice_id: body.invoice_id, document_types: ['receipt'] })
      });
      toast('Payment recorded and receipt sent!', 'success');
    } else {
      toast('Payment recorded successfully', 'success');
    }
    closeModal('recordPaymentModal');
    allInvoices = [];
    loadDashboard();
  } catch(e) { toast(e.message, 'error'); }
}

function openAddClientModal() { openModal('addClientModal'); }

async function submitClient() {
  const body = {
    full_name: document.getElementById('cl-name').value,
    email: document.getElementById('cl-email').value,
    phone: document.getElementById('cl-phone').value,
    address: document.getElementById('cl-address').value,
    city: document.getElementById('cl-city').value,
    state: document.getElementById('cl-state').value,
  };
  if (!body.full_name || !body.email) return toast('Name and email are required', 'error');
  try {
    const res = await apiFetch('/api/clients/', { method: 'POST', body: JSON.stringify(body) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed');
    toast(`Client ${data.client.full_name} added`, 'success');
    closeModal('addClientModal');
    allClients = [];
    loadDashboard();
  } catch(e) { toast(e.message, 'error'); }
}

function openSendModal(invoiceId, invNum, clientName, clientEmail) {
  currentInvoiceId = invoiceId;
  document.getElementById('sendDocsInvoiceInfo').innerHTML = `
    <strong>${invNum}</strong> → ${clientName} &lt;${clientEmail}&gt;`;
  openModal('sendDocsModal');
}

async function submitSendDocs() {
  const types = [...document.querySelectorAll('#sendDocsModal input[type=checkbox]:checked')].map(el => el.value);
  if (!types.length) return toast('Select at least one document', 'error');
  try {
    const res = await apiFetch('/api/invoices/send', {
      method: 'POST',
      body: JSON.stringify({ invoice_id: currentInvoiceId, document_types: types })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed');
    toast(`Sent: ${data.sent.join(', ')}`, 'success');
    closeModal('sendDocsModal');
  } catch(e) { toast(e.message, 'error'); }
}

// ── HELPERS ───────────────────────────────
function fmtNGN(amount) {
  if (!amount && amount !== 0) return 'NGN 0.00';
  return 'NGN ' + parseFloat(amount).toLocaleString('en-NG', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function toast(msg, type = 'info') {
  const div = document.createElement('div');
  div.className = `toast ${type}`;
  div.textContent = msg;
  document.getElementById('toastContainer').appendChild(div);
  setTimeout(() => div.remove(), 4000);
}

// Close modal on overlay click
document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', e => { if (e.target === overlay) overlay.classList.remove('open'); });
});

// ── PROFILE ───────────────────────────────
async function loadProfile() {
  const res = await apiFetch('/auth/me');
  const admin = await res.json();

  const initials = admin.full_name.split(' ').map(n=>n[0]).join('').slice(0,2).toUpperCase();
  document.getElementById('profile-avatar').textContent = initials;
  document.getElementById('profile-name-display').textContent = admin.full_name;
  document.getElementById('profile-email-display').textContent = admin.email;
  document.getElementById('profile-since').textContent = `Member since ${new Date(admin.created_at).toLocaleDateString('en-NG', {year:'numeric',month:'long'})}`;
  document.getElementById('profile-name-input').value = admin.full_name;
  document.getElementById('profile-role-badge').textContent = admin.role === 'admin' ? '⭐ Admin' : 'Staff';
  document.getElementById('profile-role-badge').style.background = admin.role === 'admin' ? 'var(--gold-light)' : '#ebf5fb';
  document.getElementById('profile-role-badge').style.color = admin.role === 'admin' ? 'var(--gold-dark)' : '#2471a3';
}

async function saveProfileName() {
  const name = document.getElementById('profile-name-input').value.trim();
  if (!name) return toast('Name cannot be empty', 'error');
  try {
    const res = await apiFetch('/auth/me/profile', { method: 'PATCH', body: JSON.stringify({ full_name: name }) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed');
    // Update sidebar
    document.getElementById('adminName').textContent = name;
    document.getElementById('adminInitials').textContent = name.split(' ').map(n=>n[0]).join('').slice(0,2).toUpperCase();
    document.getElementById('profile-name-display').textContent = name;
    document.getElementById('profile-avatar').textContent = name.split(' ').map(n=>n[0]).join('').slice(0,2).toUpperCase();
    toast('Name updated successfully', 'success');
  } catch(e) { toast(e.message, 'error'); }
}

function checkPasswordStrength(pwd) {
  const el = document.getElementById('cp-strength');
  if (!pwd) { el.textContent = ''; return; }
  let score = 0;
  if (pwd.length >= 8) score++;
  if (pwd.length >= 12) score++;
  if (/[A-Z]/.test(pwd)) score++;
  if (/[0-9]/.test(pwd)) score++;
  if (/[^A-Za-z0-9]/.test(pwd)) score++;
  const levels = ['','Weak — add numbers or symbols','Fair — try adding uppercase','Good','Strong'];
  const colors = ['','var(--red)','var(--amber)','#2980b9','var(--green)'];
  el.textContent = levels[score] || '';
  el.style.color = colors[score] || '';
}

async function submitChangePassword() {
  const current = document.getElementById('cp-current').value;
  const newPwd = document.getElementById('cp-new').value;
  const confirm = document.getElementById('cp-confirm').value;

  if (!current || !newPwd || !confirm) return toast('Please fill in all fields', 'error');
  if (newPwd !== confirm) return toast('New passwords do not match', 'error');
  if (newPwd.length < 8) return toast('Password must be at least 8 characters', 'error');

  try {
    const res = await apiFetch('/auth/me/password', {
      method: 'PATCH',
      body: JSON.stringify({ current_password: current, new_password: newPwd })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed');
    document.getElementById('cp-current').value = '';
    document.getElementById('cp-new').value = '';
    document.getElementById('cp-confirm').value = '';
    document.getElementById('cp-strength').textContent = '';
    toast('Password updated successfully', 'success');
  } catch(e) { toast(e.message, 'error'); }
}

// ── TEAM MANAGEMENT ───────────────────────
function renderMemberRow(a, archived = false) {
  const initials = a.full_name.split(' ').map(n=>n[0]).join('').slice(0,2).toUpperCase();
  const avatarBg = a.role === 'admin' ? 'var(--gold-light)' : '#ebf5fb';
  const avatarColor = a.role === 'admin' ? 'var(--gold-dark)' : '#2980b9';

  let actions = '';
  if (archived) {
    actions = `<button class="action-btn gold" onclick="reactivateAdmin('${a.id}','${a.full_name}')">Restore</button>`;
  } else {
    actions = `
      <button class="action-btn" style="color:#2980b9;border-color:#aed6f1;" onclick="openResetPasswordModal('${a.id}','${a.full_name}')">Reset PW</button>
      <button class="action-btn" onclick="openDeactivateModal('${a.id}','${a.full_name}')">${a.is_active ? 'Deactivate' : 'Reactivate'}</button>
      <button class="action-btn" style="color:#636e72;border-color:#dfe6e9;" onclick="openArchiveModal('${a.id}','${a.full_name}')">Archive</button>`;
  }

  return `<tr style="${archived ? 'opacity:0.6;' : ''}">
    <td>
      <div style="display:flex;align-items:center;gap:10px;">
        <div style="width:32px;height:32px;background:${avatarBg};border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:${avatarColor};flex-shrink:0;">${initials}</div>
        <div class="client-name">${a.full_name}</div>
      </div>
    </td>
    <td style="font-size:12px;color:var(--gray);">${a.email}</td>
    <td><span class="status ${a.role === 'admin' ? 'paid' : 'partial'}" style="${a.role==='admin'?'background:#fffbf0;color:#7d5a0a;':'background:#ebf5fb;color:#2471a3;'}"><span class="status-dot"></span>${a.role}</span></td>
    <td><span class="status ${a.is_active ? 'paid' : 'unpaid'}"><span class="status-dot"></span>${a.is_active ? 'Active' : 'Inactive'}</span></td>
    <td style="font-size:12px;color:var(--gray);">${new Date(a.created_at).toLocaleDateString()}</td>
    <td style="display:flex;gap:4px;flex-wrap:wrap;">${actions}</td>
  </tr>`;
}

const TABLE_HEAD = `<table class="data-table"><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Added</th><th>Actions</th></tr></thead><tbody>`;

async function loadTeam() {
  document.getElementById('teamTable').innerHTML = '<div class="loading"><span class="spinner"></span>Loading team...</div>';
  const data = await apiFetch('/auth/admins').then(r => r.json());

  const active = data.filter(a => !a.is_archived);
  const archived = data.filter(a => a.is_archived);

  document.getElementById('teamTable').innerHTML = active.length
    ? '<div class="table-responsive">' + TABLE_HEAD + active.map(a => renderMemberRow(a)).join('') + '</tbody></table></div>'
    : '<div class="empty-state"><p>No active team members.</p></div>';

  document.getElementById('archived-count').textContent = archived.length;
  document.getElementById('archivedTable').innerHTML = archived.length
    ? '<div class="table-responsive">' + TABLE_HEAD + archived.map(a => renderMemberRow(a, true)).join('') + '</tbody></table></div>'
    : '<div class="empty-state" style="padding:20px;"><p>No archived members.</p></div>';
}

function toggleArchived() {
  const el = document.getElementById('archivedTable');
  const chevron = document.getElementById('archived-chevron');
  const open = el.style.display === 'none';
  el.style.display = open ? '' : 'none';
  chevron.style.transform = open ? 'rotate(180deg)' : '';
}

function openAddAdminModal() {
  ['am-name','am-email','am-password','am-password2'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('am-role').value = 'staff';
  openModal('addAdminModal');
}

async function submitAddAdmin() {
  const name = document.getElementById('am-name').value.trim();
  const email = document.getElementById('am-email').value.trim();
  const role = document.getElementById('am-role').value;
  const pass = document.getElementById('am-password').value;
  const pass2 = document.getElementById('am-password2').value;

  if (!name || !email || !pass) return toast('Please fill in all required fields', 'error');
  if (pass !== pass2) return toast('Passwords do not match', 'error');
  if (pass.length < 8) return toast('Password must be at least 8 characters', 'error');

  try {
    const res = await apiFetch('/auth/register', {
      method: 'POST', body: JSON.stringify({ full_name: name, email, password: pass, role })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to create account');
    toast(`${role === 'admin' ? 'Admin' : 'Staff'} account created for ${name}`, 'success');
    closeModal('addAdminModal');
    loadTeam();
  } catch(e) { toast(e.message, 'error'); }
}

function openDeactivateModal(adminId, adminName) {
  document.getElementById('deactivateAdminId').value = adminId;
  document.getElementById('deactivateName').textContent = adminName;
  openModal('deactivateModal');
}

async function confirmDeactivate() {
  const id = document.getElementById('deactivateAdminId').value;
  try {
    const res = await apiFetch(`/auth/admins/${id}/deactivate`, { method: 'PATCH' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed');
    toast('Account deactivated', 'info');
    closeModal('deactivateModal');
    loadTeam();
  } catch(e) { toast(e.message, 'error'); }
}

async function reactivateAdmin(id, name) {
  try {
    const res = await apiFetch(`/auth/admins/${id}/reactivate`, { method: 'PATCH' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed');
    toast(`${name}'s account restored`, 'success');
    loadTeam();
  } catch(e) { toast(e.message, 'error'); }
}

function openArchiveModal(adminId, adminName) {
  document.getElementById('archiveAdminId').value = adminId;
  document.getElementById('archiveName').textContent = adminName;
  openModal('archiveModal');
}

async function confirmArchive() {
  const id = document.getElementById('archiveAdminId').value;
  try {
    const res = await apiFetch(`/auth/admins/${id}/archive`, { method: 'PATCH' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed');
    toast(data.message, 'info');
    closeModal('archiveModal');
    loadTeam();
  } catch(e) { toast(e.message, 'error'); }
}

function openResetPasswordModal(adminId, adminName) {
  document.getElementById('resetPasswordAdminId').value = adminId;
  document.getElementById('resetPasswordName').textContent = adminName;
  document.getElementById('rp-new').value = '';
  document.getElementById('rp-confirm').value = '';
  openModal('resetPasswordModal');
}

async function confirmResetPassword() {
  const id = document.getElementById('resetPasswordAdminId').value;
  const newPwd = document.getElementById('rp-new').value;
  const confirm = document.getElementById('rp-confirm').value;

  if (!newPwd || !confirm) return toast('Please fill in both fields', 'error');
  if (newPwd !== confirm) return toast('Passwords do not match', 'error');
  if (newPwd.length < 8) return toast('Password must be at least 8 characters', 'error');

  try {
    const res = await apiFetch(`/auth/admins/${id}/reset-password`, {
      method: 'PATCH', body: JSON.stringify({ new_password: newPwd })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed');
    toast(data.message, 'success');
    closeModal('resetPasswordModal');
  } catch(e) { toast(e.message, 'error'); }
}

// ── SEARCH-SELECT LOGIC ──────────────────
function openSearch(cid, type) {
  const container = document.getElementById(cid);
  const results = container.querySelector('.search-select-results');
  results.classList.add('open');
  if (!results.querySelector('.search-item')) {
    filterSearch(cid, type); // Initial load
  }
}

async function filterSearch(cid, type) {
  const container = document.getElementById(cid);
  const input = container.querySelector('input[type="text"]');
  const results = container.querySelector('.search-select-results');
  const query = input.value.toLowerCase();
  
  let items = [];
  if (type === 'clients') items = allClients;
  else if (type === 'properties') items = allProperties;
  else if (type === 'invoices') items = allInvoices;
  else if (type === 'reps') {
      // Inline fetch for reps as they are fewer
      allReps = await apiFetch('/api/sales-reps/').then(r => r.json());
      items = allReps;
  }

  const filtered = items.filter(item => {
    if (type === 'clients') return item.full_name.toLowerCase().includes(query) || (item.email && item.email.toLowerCase().includes(query));
    if (type === 'properties') return item.name.toLowerCase().includes(query) || (item.estate_name && item.estate_name.toLowerCase().includes(query));
    if (type === 'invoices') return (item.invoice_number && item.invoice_number.toLowerCase().includes(query)) || (item.clients?.full_name && item.clients.full_name.toLowerCase().includes(query));
    if (type === 'reps') return item.name.toLowerCase().includes(query);
    return false;
  });

  if (filtered.length === 0) {
    results.innerHTML = `<div class="search-empty">No ${type} found matching "${input.value}"</div>`;
  } else {
    results.innerHTML = filtered.map(item => {
      let title = '', meta = '', id = item.id;
      let itemData = encodeURIComponent(JSON.stringify(item));
      if (type === 'clients') {
        title = item.full_name;
        meta = `<span>${item.email || 'No email'}</span> <span>${item.phone || ''}</span>`;
      } else if (type === 'properties') {
        title = item.name;
        meta = `<span>${item.estate_name || ''}</span> <span>${item.location}</span>`;
      } else if (type === 'invoices') {
        title = item.invoice_number || 'INV-???';
        const balance = parseFloat(item.balance_due || 0);
        const statusClass = balance > 0 ? (item.amount_paid > 0 ? 'partial' : 'unpaid') : '';
        const statusLabel = balance > 0 ? (item.amount_paid > 0 ? 'Part Paid' : 'Unpaid') : 'Paid';
        meta = `<span>${item.clients?.full_name || 'Unknown'}</span> <span class="badge-small badge-${statusClass}">${statusLabel}: ${fmtNGN(balance)}</span>`;
      }
      
      return `
        <div class="search-item" onclick="selectSearchItem('${cid}', '${type}', '${id}', '${title.replace(/'/g, "\\'")}', '${itemData}')">
          <div class="search-item-title">${title}</div>
          <div class="search-item-meta">${meta}</div>
        </div>`;
    }).join('');
  }
}

function selectSearchItem(cid, type, id, title, itemDataEncoded) {
  const item = JSON.parse(decodeURIComponent(itemDataEncoded));
  const container = document.getElementById(cid);
  container.querySelector('input[type="text"]').value = title;
  container.querySelector('input[type="hidden"]').value = id;
  container.querySelector('.search-select-results').classList.remove('open');
  
  // Specific auto-fill logic
  if (cid === 'inv-property-search') {
    document.getElementById('inv-property-name').value = item.name;
    document.getElementById('inv-location').value = item.location;
    document.getElementById('inv-size').value = item.plot_size_sqm || '';
    document.getElementById('inv-amount').value = item.total_price || '';
  } else if (cid === 'pay-invoice-search') {
    document.getElementById('pay-client-id').value = item.client_id;
    document.getElementById('pay-client-display').value = item.clients?.full_name || '—';
    document.getElementById('pay-amount').value = item.balance_due || '';
  }
}

// Global click handler to close search boxes
document.addEventListener('click', (e) => {
  if (!e.target.closest('.search-select-container')) {
    document.querySelectorAll('.search-select-results').forEach(r => r.classList.remove('open'));
  }
});

// ── VERIFICATIONS ─────────────────────────
async function updateVerificationsBadge() {
  try {
    const res = await apiFetch('/api/verifications/count');
    const data = await res.json();
    const badge = document.getElementById('verifications-badge');
    if (data.count > 0) {
      badge.textContent = data.count;
      badge.style.display = 'block';
    } else {
      badge.style.display = 'none';
    }
  } catch(e) { console.error('Badge update failed', e); }
}

async function loadVerifications() {
  const container = document.getElementById('verificationsTable');
  container.innerHTML = '<div class="loading"><span class="spinner"></span>Loading submissions...</div>';
  try {
    const data = await apiFetch('/api/verifications/').then(r => r.json());
    const pending = data.filter(v => v.status === 'pending');
    
    if (!pending.length) {
      container.innerHTML = '<div class="empty-state"><p>No pending verifications at the moment.</p></div>';
      return;
    }
    
    container.innerHTML = `
      <div class="table-responsive">
        <table class="data-table">
          <thead>
            <tr>
              <th>Submitted</th>
              <th>Client</th>
              <th>Property</th>
              <th>Deposit</th>
              <th>Status</th>
              <th>Proof</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            ${pending.map(v => `
              <tr>
                <td style="font-size:12px;color:var(--gray);">${new Date(v.created_at).toLocaleString()}</td>
                <td>
                  <div class="client-name">${v.clients?.full_name || '—'}</div>
                  <div class="client-email">${v.clients?.email || ''}</div>
                </td>
                <td style="font-size:12px;">
                   <strong>${v.invoices?.invoice_number || '—'}</strong><br>
                   ${v.invoices?.property_name || '—'}
                </td>
                <td style="font-weight:600;color:var(--gold-dark);">${fmtNGN(v.deposit_amount)}</td>
                <td><span class="status unpaid"><span class="status-dot"></span>${v.status}</span></td>
                <td>
                  <a href="${v.payment_proof_url}" target="_blank" class="action-btn" style="text-decoration:none;display:inline-block;border-color:#ccc;">View Proof</a>
                </td>
                <td>
                  <div style="display:flex;gap:4px;">
                    <button class="action-btn" onclick="openEditVerification('${v.id}')">Edit</button>
                    <button class="action-btn gold" onclick="openConfirmVerification('${v.id}')">Confirm</button>
                    <button class="action-btn" style="color:var(--red);border-color:#feb2b2;" onclick="openRejectVerification('${v.id}')">Reject</button>
                  </div>
                </td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
    updateVerificationsBadge();
  } catch(e) { container.innerHTML = '<div class="empty-state"><p>Error loading data.</p></div>'; }
}

async function openEditVerification(id) {
  try {
    const res = await apiFetch(`/api/verifications/`);
    const all = await res.json();
    const ver = all.find(v => v.id === id);
    if (!ver) throw new Error('Verification not found');
    
    document.getElementById('edit-ver-id').value = ver.id;
    document.getElementById('edit-ver-deposit').value = ver.deposit_amount;
    document.getElementById('edit-ver-date').value = ver.payment_date;
    document.getElementById('edit-ver-proof').value = ver.payment_proof_url || '';
    
    const isStaff = currentUserRole === 'staff';
    const depInput = document.getElementById('edit-ver-deposit');
    const dateInput = document.getElementById('edit-ver-date');
    
    if (isStaff) {
      depInput.classList.add('locked-field'); depInput.readOnly = true;
      dateInput.classList.add('locked-field'); dateInput.readOnly = true;
      document.querySelectorAll('.edit-ver-admin-lock').forEach(el => el.style.display = 'block');
    } else {
      depInput.classList.remove('locked-field'); depInput.readOnly = false;
      dateInput.classList.remove('locked-field'); dateInput.readOnly = false;
      document.querySelectorAll('.edit-ver-admin-lock').forEach(el => el.style.display = 'none');
    }
    
    openModal('editVerificationModal');
  } catch(e) { toast(e.message, 'error'); }
}

async function submitEditVerification() {
  const id = document.getElementById('edit-ver-id').value;
  const body = { payment_proof_url: document.getElementById('edit-ver-proof').value };
  
  if (currentUserRole === 'admin') {
    body.deposit_amount = parseFloat(document.getElementById('edit-ver-deposit').value);
    body.payment_date = document.getElementById('edit-ver-date').value;
  }
  
  try {
    const res = await apiFetch(`/api/verifications/${id}/edit`, { method: 'PATCH', body: JSON.stringify(body) });
    if (!res.ok) throw new Error('Failed to update verification');
    toast('Verification updated successfully', 'success');
    closeModal('editVerificationModal');
    loadVerifications();
  } catch(e) { toast(e.message, 'error'); }
}

function openConfirmVerification(id) {
  document.getElementById('verify-confirm-id').value = id;
  openModal('verifyConfirmModal');
}

async function processConfirmVerification() {
  const id = document.getElementById('verify-confirm-id').value;
  try {
    const res = await apiFetch(`/api/verifications/${id}/confirm`, { method: 'PATCH' });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed');
    toast('Payment confirmed and documents sent!', 'success');
    closeModal('verifyConfirmModal');
    loadVerifications();
    if (document.getElementById('section-dashboard').style.display === '') loadDashboard(); 
  } catch(e) { toast(e.message, 'error'); }
}

function openRejectVerification(id) {
  document.getElementById('verify-reject-id').value = id;
  document.getElementById('verify-reject-reason').value = '';
  openModal('verifyRejectModal');
}

async function processRejectVerification() {
  const id = document.getElementById('verify-reject-id').value;
  const reason = document.getElementById('verify-reject-reason').value.trim();
  if (!reason) return toast('Please provide a reason', 'error');
  
  try {
    const res = await apiFetch(`/api/verifications/${id}/reject`, { 
      method: 'PATCH', 
      body: JSON.stringify({ reason }) 
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed');
    toast('Submission rejected and client notified', 'info');
    closeModal('verifyRejectModal');
    loadVerifications();
  } catch(e) { toast(e.message, 'error'); }
}

// ── VOID LOGIC ────────────────────────────
function openVoidModal(invoiceId) {
  document.getElementById('void-invoice-id').value = invoiceId;
  document.getElementById('void-reason').value = '';
  document.getElementById('void-notify-client').checked = true;
  openModal('voidReceiptModal');
}

async function processVoidInvoice() {
  const id = document.getElementById('void-invoice-id').value;
  const reason = document.getElementById('void-reason').value.trim();
  const notify = document.getElementById('void-notify-client').checked;
  if (!reason) return toast('Please provide a reason', 'error');
  
  try {
    const res = await apiFetch(`/api/invoices/${id}/void`, {
      method: 'POST',
      body: JSON.stringify({ reason, notify_client: notify })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed');
    toast('Receipt voided and payment reversed', 'info');
    closeModal('voidReceiptModal');
    loadInvoices();
    if (document.getElementById('section-dashboard').style.display === '') loadDashboard();
  } catch(e) { toast(e.message, 'error'); }
}

// ── INIT ──────────────────────────────────
checkAuth().then(() => {
  loadDashboard();
  updateVerificationsBadge();
});
