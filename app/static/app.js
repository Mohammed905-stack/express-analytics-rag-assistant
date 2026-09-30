const el = id => document.getElementById(id);
let keyConfigured = false;
let documentCount = 0;
let busy = false;
let lastResult = null;
let lastQuestion = '';

function notice(text = '') { el('notice').textContent = text; el('notice').hidden = !text; }
function working(value, text = '') {
  busy = value; el('busy').hidden = !value; el('busy-text').textContent = text;
  document.querySelectorAll('button').forEach(button => { button.disabled = value; });
}
async function api(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
  return data;
}
async function refresh() {
  const [health, data] = await Promise.all([api('/health'), api('/documents')]);
  keyConfigured = health.key_configured;
  documentCount = data.documents.length;
  el('health').textContent = keyConfigured ? '● Connected · key configured' : '● Connected · key needed';
  el('count').textContent = documentCount;
  el('documents').replaceChildren();
  for (const doc of data.documents) {
    const item = document.createElement('li');
    const title = document.createElement('div'); title.textContent = doc.title;
    const meta = document.createElement('div'); meta.className = 'document-meta'; meta.textContent = `${doc.chunks} searchable passages`;
    item.append(title, meta); el('documents').append(item);
  }
  if (!keyConfigured) notice('Close the app server, run SETUP_KEY.cmd to save your key, then start START.cmd again.');
}
function needKey() {
  if (keyConfigured) return true;
  notice('Save your Gemini key using SETUP_KEY.cmd and restart the app.'); return false;
}
function render(result, question) {
  lastResult = result; lastQuestion = question;
  el('result').hidden = false;
  el('answer').textContent = result.answer;
  const checked = result.trace.some(step => step.node === 'grounding_check' && step.supported);
  el('status').textContent = result.status !== 'answered' ? 'INSUFFICIENT CONTEXT' : checked ? 'SUPPORT CHECK PASSED' : 'CITATIONS VALIDATED';
  el('sources').replaceChildren();
  for (const source of result.sources) {
    const detail = document.createElement('details');
    const summary = document.createElement('summary'); summary.textContent = `[${source.citation}] ${source.title}`;
    const label = document.createElement('div'); label.className = 'source-label'; label.textContent = source.source;
    const excerpt = document.createElement('pre'); excerpt.className = 'excerpt'; excerpt.textContent = source.excerpt;
    detail.append(summary, label, excerpt); el('sources').append(detail);
  }
  el('retries').textContent = `· ${result.retries} corrective ${result.retries === 1 ? 'retry' : 'retries'}`;
  el('trace').replaceChildren();
  const names = {query_analysis:'Analyse the question',retrieval:'Search the documents',document_grading:'Grade passage relevance',query_rewrite:'Rewrite and retry',generation:'Generate a cited answer',grounding_check:'Check answer support',fallback:'Return insufficient information'};
  result.trace.forEach((step, i) => {
    const row = document.createElement('div'); row.className = 'trace-step';
    const heading = document.createElement('strong'); heading.textContent = `${i + 1}. ${names[step.node] || step.node}`;
    const data = document.createElement('pre'); data.className = 'trace-data';
    const {node, ...details} = step; data.textContent = JSON.stringify(details, null, 2);
    row.append(heading, data); el('trace').append(row);
  });
  el('comment').value = ''; el('feedback-state').textContent = '';
  el('result').scrollIntoView({behavior:'smooth',block:'start'});
}
el('index').addEventListener('click', async () => {
  if (busy || !needKey()) return;
  notice(); working(true, 'Creating real embeddings for five guides. The first run can take a few minutes…');
  try { const result = await api('/ingest-corpus', {method:'POST'}); await refresh(); notice(`Ready: ${result.documents.length} guides processed. Ask a question below.`); }
  catch (error) { await refresh().catch(() => {}); notice(error.message + ' Completed guides stay saved; retry after fixing the issue.'); }
  finally { working(false); }
});
el('query-form').addEventListener('submit', async event => {
  event.preventDefault(); if (busy || !needKey()) return;
  if (!documentCount) { notice('Index the five guides or upload a document first.'); return; }
  const question = el('question').value.trim();
  if (!question) { notice('Enter a question first.'); return; }
  notice(); working(true, 'Searching passages, grading relevance and checking answer support…');
  try { render(await api('/query', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question})}),question); }
  catch (error) { notice(error.message); }
  finally { working(false); }
});
el('upload-form').addEventListener('submit', async event => {
  event.preventDefault(); if (busy || !needKey()) return;
  const file = el('file').files[0]; if (!file) return;
  if (file.size > 2 * 1024 * 1024) { notice('Choose a document no larger than 2 MiB.'); return; }
  const data = new FormData(); data.append('file',file);
  if (el('source').value.trim()) data.append('source',el('source').value.trim());
  notice(); working(true,'Splitting your document and creating embeddings…');
  try { await api('/ingest',{method:'POST',body:data}); await refresh(); el('upload-form').reset(); notice('Document indexed. You can now ask questions about it.'); }
  catch (error) { notice(error.message); }
  finally { working(false); }
});
document.querySelectorAll('[data-question]').forEach(button => button.addEventListener('click', () => { el('question').value = button.dataset.question; el('question').focus(); }));
async function feedback(rating) {
  if (!lastResult || busy) return;
  try { await api('/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query_id:lastResult.query_id,rating,comment:el('comment').value.trim() || null})}); el('feedback-state').textContent = 'Feedback saved.'; }
  catch (error) { notice(error.message); }
}
el('up').addEventListener('click', () => feedback('up'));
el('down').addEventListener('click', () => feedback('down'));
el('download').addEventListener('click', () => {
  if (!lastResult) return;
  const blob = new Blob([JSON.stringify({captured_at:new Date().toISOString(),mode:'api_response',question:lastQuestion,response:lastResult},null,2)],{type:'application/json'});
  const url = URL.createObjectURL(blob), link = document.createElement('a');
  link.href = url; link.download = `response-${lastResult.query_id}.json`; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
});
refresh().catch(error => { el('health').textContent = '● Connection unavailable'; notice(error.message); });
