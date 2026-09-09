/**
 * static/js/app.js
 * AI Digital Memory Guardian — Frontend Logic
 *
 * Professional UI state management and REST API client.
 * Pure modern vanilla JS — no emojis, clean SVG icons, responsive feedback.
 */

// ── Icons (Inline SVGs) ────────────────────────────────────────────────────
const ICONS = {
  check: `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5"/></svg>`,
  error: `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>`,
  info:  `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z"/></svg>`,
  file:  `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"/></svg>`,
  copy:  `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125H4.125A1.125 1.125 0 013 20.625V7.875c0-.621.504-1.125 1.125-1.125H6.75m3.75 0h8.625c.621 0 1.125.504 1.125 1.125v10.125c0 .621-.504 1.125-1.125 1.125H10.5a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125z"/></svg>`,
  sparkle: `<svg class="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"/></svg>`,
  target: `<svg class="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>`,
  type:  `<svg class="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M7.5 12h9m-6.75 5.25h4.5"/></svg>`,
  network: `<svg class="w-4 h-4 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><circle cx="6" cy="6" r="3"/><circle cx="18" cy="18" r="3"/><path d="M8.5 8.5l7 7"/></svg>`,
  trash: `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"/></svg>`,
};

// ── State ──────────────────────────────────────────────────────────────────
const state = {
  activeTab: 'ingest',
  apiKey: localStorage.getItem('mg_api_key') || '',
  model: localStorage.getItem('mg_model') || 'claude-3-5-haiku-20241022',
  engine: localStorage.getItem('mg_engine') || 'auto',
  stats: { chunks: 0, sources: [] },
};

// ── API base ───────────────────────────────────────────────────────────────
const API = {
  async post(url, body, isFormData = false) {
    const opts = {
      method: 'POST',
      body: isFormData ? body : JSON.stringify(body),
    };
    if (!isFormData) opts.headers = { 'Content-Type': 'application/json' };
    const res = await fetch(url, opts);
    return res.json();
  },
  async get(url) {
    const res = await fetch(url);
    return res.json();
  },
  async delete(url) {
    const res = await fetch(url, { method: 'DELETE' });
    return res.json();
  },
};

// ── Navigation ─────────────────────────────────────────────────────────────
function setTab(tab) {
  state.activeTab = tab;
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tab);
  });
  document.querySelectorAll('.tab-panel').forEach(panel => {
    panel.classList.toggle('hidden', panel.id !== `panel-${tab}`);
  });
  if (tab === 'library') loadLibrary();
}

// ── Sidebar Config Persistence ─────────────────────────────────────────────
function saveApiKey() {
  const val = document.getElementById('sidebar-api-key').value.trim();
  state.apiKey = val;
  localStorage.setItem('mg_api_key', val);
  showToast('Credentials updated successfully', 'success');
}

function saveModel() {
  const val = document.getElementById('sidebar-model').value;
  state.model = val;
  localStorage.setItem('mg_model', val);
}

function saveEngine() {
  const val = document.getElementById('sidebar-engine').value;
  state.engine = val;
  localStorage.setItem('mg_engine', val);
  showToast(`Synthesis engine set to: ${val}`, 'info');
}

// ── Toast Notifications ────────────────────────────────────────────────────
function showToast(msg, type = 'info') {
  const toast = document.getElementById('toast');
  toast.innerHTML = `<span class="toast-icon toast-${type}">${ICONS[type] || ICONS.info}</span><span>${msg}</span>`;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 3500);
}

// ── Copy Snippet Helper ────────────────────────────────────────────────────
function copyMemoryText(btn, text) {
  navigator.clipboard.writeText(text).then(() => {
    const orig = btn.innerHTML;
    btn.innerHTML = `${ICONS.check} Copied`;
    btn.style.color = '#10b981';
    btn.style.borderColor = '#10b981';
    setTimeout(() => {
      btn.innerHTML = orig;
      btn.style.color = '';
      btn.style.borderColor = '';
    }, 1800);
  }).catch(() => {
    showToast('Failed to copy to clipboard', 'error');
  });
}

// ── Quick Prompts ──────────────────────────────────────────────────────────
function fillQuery(text) {
  const input = document.getElementById('query-input');
  input.value = text;
  input.focus();
  runQuery();
}

// ── Stats update & Source Filter Population ────────────────────────────────
async function refreshStats() {
  try {
    const data = await API.get('/api/library/');
    state.stats.chunks = data.total_chunks;
    state.stats.sources = data.sources || [];
    document.getElementById('stat-chunks').textContent = data.total_chunks;
    document.getElementById('stat-docs').textContent   = (data.sources || []).length;

    // Populate source dropdown in Query tab
    const select = document.getElementById('query-source-filter');
    if (select) {
      const currentVal = select.value;
      let opts = `<option value="">All Documents (Entire Library)</option>`;
      (data.sources || []).forEach(s => {
        const sel = s.source === currentVal ? 'selected' : '';
        opts += `<option value="${escHtml(s.source)}" ${sel}>${escHtml(s.source)} (${s.chunk_count} chunks)</option>`;
      });
      select.innerHTML = opts;
    }
  } catch (_) {}
}

// ── Score Color ────────────────────────────────────────────────────────────
function scoreColor(score) {
  if (score >= 0.75) return '#10b981'; // green
  if (score >= 0.50) return '#8b5cf6'; // violet
  if (score >= 0.25) return '#f59e0b'; // amber
  return '#64748b';                    // slate
}

// ── Render Memory Card ─────────────────────────────────────────────────────
function renderMemoryCard(r, type = 'semantic') {
  const score      = type === 'semantic' ? r.final_score : r.kw_score;
  const scoreLabel = type === 'semantic' ? 'Relevance' : 'Score';
  const color      = scoreColor(score);

  const extra = type === 'semantic'
    ? `<span class="chip chip-dim">Similarity: ${(r.similarity * 100).toFixed(1)}%</span>
       <span class="chip chip-dim">Retrieved: ×${r.retrieved_n ?? 0}</span>`
    : `<span class="chip chip-dim">Matched: ${(r.matched_terms || []).join(', ') || 'none'}</span>`;

  // Safe string serialization for the copy function
  const rawText = r.text || '';
  const escapedAttrText = rawText.replace(/"/g, '&quot;').replace(/'/g, '&#39;');

  return `
    <div class="memory-card" style="--accent: ${color}">
      <div class="card-header">
        <div class="card-badges">
          <span class="chip chip-score" style="color:${color}; border-color:${color}44">
            ${scoreLabel}: ${(score * 100).toFixed(1)}%
          </span>
          <span class="chip chip-source">${ICONS.file} ${escHtml(r.source)}</span>
          ${extra}
        </div>
        <div class="card-actions">
          <button class="btn-icon-action" onclick="copyMemoryText(this, \`${escapedAttrText}\`)">
            ${ICONS.copy} Copy
          </button>
        </div>
      </div>
      <p class="card-text">${escHtml(rawText)}</p>
    </div>`;
}

function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function loadingHTML(text) {
  return `
    <div class="loading-state">
      <div class="spinner"></div>
      <span>${text}</span>
    </div>`;
}

// ══════════════════════════════════════════════════════════════════════════
// INGEST
// ══════════════════════════════════════════════════════════════════════════
function initDropzone() {
  const dz = document.getElementById('dropzone');
  if (!dz) return;

  dz.addEventListener('dragover', e => {
    e.preventDefault();
    dz.classList.add('dragover');
  });
  dz.addEventListener('dragleave', () => dz.classList.remove('dragover'));
  dz.addEventListener('drop', e => {
    e.preventDefault();
    dz.classList.remove('dragover');
    const files = [...e.dataTransfer.files].filter(f => f.name.match(/\.(txt|md)$/i));
    if (files.length) handleFiles(files);
    else showToast('Only .txt and .md files are accepted', 'error');
  });
}

document.getElementById('file-input')?.addEventListener('change', e => {
  handleFiles([...e.target.files]);
});

function handleFiles(files) {
  const list = document.getElementById('file-list');
  list.innerHTML = '';
  list._files = [];

  files.forEach(f => {
    const item = document.createElement('div');
    item.className = 'file-item';
    item.innerHTML = `
      <span class="flex items-center gap-2">${ICONS.file} ${escHtml(f.name)}</span>
      <span class="file-size">${(f.size / 1024).toFixed(1)} KB</span>
    `;
    item.dataset.file = f.name;
    list._files.push(f);
    list.appendChild(item);
  });
}

async function ingestFiles() {
  const list  = document.getElementById('file-list');
  const files = list?._files;
  const text  = document.getElementById('paste-text').value.trim();
  const name  = document.getElementById('paste-name').value.trim() || 'pasted_document';
  const btn   = document.getElementById('btn-ingest');

  if (!files?.length && !text) {
    showToast('Select a file or enter text to ingest', 'error');
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Processing…';
  const progress = document.getElementById('ingest-progress');
  progress.classList.remove('hidden');

  try {
    // Ingest uploaded files
    if (files?.length) {
      for (let i = 0; i < files.length; i++) {
        const fd = new FormData();
        fd.append('file', files[i]);
        document.getElementById('progress-label').textContent =
          `Embedding ${files[i].name} (${i + 1}/${files.length})…`;
        const data = await API.post('/api/ingest/', fd, true);
        if (data.error) { showToast(data.error, 'error'); continue; }
        showToast(`${data.source}: ${data.chunks_added} chunks indexed`, 'success');
      }
    }

    // Ingest pasted text
    if (text) {
      document.getElementById('progress-label').textContent = `Embedding "${name}"…`;
      const data = await API.post('/api/ingest/', { text, name });
      if (data.error) showToast(data.error, 'error');
      else showToast(`${data.source}: ${data.chunks_added} chunks indexed`, 'success');
    }

    // Reset UI
    if (list) { list.innerHTML = ''; list._files = null; }
    document.getElementById('paste-text').value = '';
    document.getElementById('paste-name').value = '';
    document.getElementById('progress-label').textContent = 'Indexing Complete!';
    await refreshStats();
    setTimeout(() => progress.classList.add('hidden'), 1500);
  } catch (e) {
    showToast('Ingest failed: ' + e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z"/>
      </svg>
      Embed &amp; Store
    `;
  }
}

// ══════════════════════════════════════════════════════════════════════════
// QUERY
// ══════════════════════════════════════════════════════════════════════════
async function runQuery() {
  const query = document.getElementById('query-input').value.trim();
  const top_k = parseInt(document.getElementById('query-topk').value);
  const sourceFilter = document.getElementById('query-source-filter')?.value || '';
  const btn   = document.getElementById('btn-query');

  if (!query) { showToast('Please enter a query', 'error'); return; }

  btn.disabled    = true;
  btn.textContent = 'Retrieving…';
  document.getElementById('query-results').innerHTML = loadingHTML('Searching vector embeddings…');

  try {
    const data = await API.post('/api/query/', {
      query,
      top_k,
      api_key:       state.apiKey,
      model:         state.model,
      engine:        state.engine,
      source_filter: sourceFilter,
    });

    if (data.error) { showToast(data.error, 'error'); return; }

    const scopeLabel = sourceFilter ? ` in [${escHtml(sourceFilter)}]` : '';
    let html = `
      <h3 class="results-title">
        ${ICONS.target}
        <span>Retrieved ${data.results.length} Memory Passages${scopeLabel}</span>
      </h3>`;

    html += data.results.map(r => renderMemoryCard(r, 'semantic')).join('');

    if (data.answer) {
      const modelName = data.usage?.model || 'AI Assistant';
      const tokenInfo = data.usage && (data.usage.input_tokens > 0 || data.usage.output_tokens > 0)
        ? `<span class="token-count">${data.usage.input_tokens}↑ ${data.usage.output_tokens}↓ tokens</span>`
        : `<span class="token-count">Local Offline</span>`;

      html = `
        <div class="answer-box">
          <div class="answer-header">
            ${ICONS.sparkle}
            <span>Synthesized Answer <span class="answer-model">(${escHtml(modelName)})</span></span>
            ${tokenInfo}
          </div>
          <div class="answer-text">${escHtml(data.answer)}</div>
        </div>` + html;
    }

    document.getElementById('query-results').innerHTML = html;
    await refreshStats();
  } catch (e) {
    showToast('Query failed: ' + e.message, 'error');
  } finally {
    btn.disabled    = false;
    btn.innerHTML   = `
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"/>
      </svg>
      Search Memory
    `;
  }
}

// ══════════════════════════════════════════════════════════════════════════
// COMPARE
// ══════════════════════════════════════════════════════════════════════════
async function runCompare() {
  const query = document.getElementById('compare-input').value.trim();
  const top_k = parseInt(document.getElementById('compare-topk').value);
  const btn   = document.getElementById('btn-compare');

  if (!query) { showToast('Please enter a query to compare', 'error'); return; }

  btn.disabled    = true;
  btn.textContent = 'Comparing…';
  document.getElementById('col-keyword').innerHTML  = loadingHTML('Running keyword matching…');
  document.getElementById('col-semantic').innerHTML = loadingHTML('Running semantic embedding search…');

  try {
    const data = await API.post('/api/compare/', {
      query, top_k,
      api_key: state.apiKey,
      model:   state.model,
    });

    // Keyword Column
    const kwHtml = data.keyword.length
      ? data.keyword.map(r => renderMemoryCard(r, 'keyword')).join('')
      : `<div class="empty-state">No keyword matches found.<br><span class="hint-text">The exact search tokens do not exist in stored documents.</span></div>`;

    document.getElementById('col-keyword').innerHTML = `
      <h4 class="col-title col-title-kw">
        ${ICONS.type}
        <span>Keyword Matching</span>
        <span class="count-badge">${data.keyword.length}</span>
      </h4>${kwHtml}`;

    // Semantic Column
    const semHtml = data.semantic.length
      ? data.semantic.map(r => renderMemoryCard(r, 'semantic')).join('')
      : `<div class="empty-state">No semantic matches found.</div>`;

    let semExtra = '';
    if (data.answer) {
      semExtra = `
        <div class="answer-box" style="margin-top:16px">
          <div class="answer-header">${ICONS.sparkle} <span>Synthesized Answer</span></div>
          <div class="answer-text">${escHtml(data.answer)}</div>
        </div>`;
    }

    document.getElementById('col-semantic').innerHTML = `
      <h4 class="col-title col-title-sem">
        ${ICONS.network}
        <span>Semantic Vector Search</span>
        <span class="count-badge">${data.semantic.length}</span>
      </h4>${semHtml}${semExtra}`;

    await refreshStats();
  } catch (e) {
    showToast('Comparison failed: ' + e.message, 'error');
  } finally {
    btn.disabled    = false;
    btn.innerHTML   = `
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M7.5 21L3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5"/>
      </svg>
      Run Comparison
    `;
  }
}

// ══════════════════════════════════════════════════════════════════════════
// LIBRARY
// ══════════════════════════════════════════════════════════════════════════
async function loadLibrary() {
  const container = document.getElementById('library-content');
  container.innerHTML = loadingHTML('Reading vector collection…');

  try {
    const data = await API.get('/api/library/');
    if (!data.sources.length) {
      container.innerHTML = `
        <div class="empty-state">
          No documents currently indexed.<br>
          <span class="hint-text">Go to the Ingest tab to add your first notes or files.</span>
        </div>`;
      return;
    }

    const rows = data.sources.map(s => `
      <div class="library-row">
        <div class="lib-info">
          <span class="lib-name">${ICONS.file} ${escHtml(s.source)}</span>
          <span class="lib-meta">${s.chunk_count} chunks indexed · accessed ${s.total_retrieved}× · uploaded ${s.upload_date}</span>
        </div>
        <button class="btn btn-danger btn-sm" onclick="deleteSource('${encodeURIComponent(s.source)}')">
          ${ICONS.trash} Delete
        </button>
      </div>`).join('');

    container.innerHTML = `
      <div class="lib-stats">
        <span><strong>${data.sources.length}</strong> documents</span>
        <span><strong>${data.total_chunks}</strong> vector chunks</span>
        <span class="lib-db-path">Storage: ChromaDB SQLite (data/chroma_db)</span>
      </div>
      <div class="library-list">${rows}</div>`;

    await refreshStats();
  } catch (e) {
    container.innerHTML = `<div class="empty-state error-text">Failed to load library: ${e.message}</div>`;
  }
}

async function deleteSource(sourceEncoded) {
  const source = decodeURIComponent(sourceEncoded);
  if (!confirm(`Delete all vector chunks from "${source}"?`)) return;

  try {
    const res = await API.delete(`/api/library/${encodeURIComponent(source)}/`);
    showToast(`Deleted ${res.deleted} chunks from ${source}`, 'info');
    await loadLibrary();
    await refreshStats();
  } catch (e) {
    showToast('Delete failed: ' + e.message, 'error');
  }
}

// ── Initialization ─────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initDropzone();

  // Restore saved configurations
  const keyInput = document.getElementById('sidebar-api-key');
  if (keyInput && state.apiKey) keyInput.value = state.apiKey;

  const modelSelect = document.getElementById('sidebar-model');
  if (modelSelect && state.model) modelSelect.value = state.model;

  const engineSelect = document.getElementById('sidebar-engine');
  if (engineSelect && state.engine) engineSelect.value = state.engine;

  refreshStats();
});
