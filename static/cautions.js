/* Report content is treated as untrusted text. Links are validated again. */
let cautionData = null;
let cautionFailed = false;
function renderCautions() {
  const status = document.getElementById('caution-status');
  const container = document.getElementById('caution-items');
  container.replaceChildren();
  if (cautionFailed) { status.textContent = t('caution_failed'); return; }
  if (!cautionData) { status.textContent = t('caution_loading'); return; }
  if (!cautionData.updated_at) { status.textContent = t('caution_waiting'); return; }
  const date = new Date(cautionData.updated_at);
  if (Number.isNaN(date.getTime())) { status.textContent = t('caution_failed'); return; }
  const stale = Date.now() - date.getTime() > 48 * 60 * 60 * 1000;
  status.textContent = t('caution_updated') + ' ' + date.toLocaleString(locale === 'hi' ? 'hi-IN' : locale === 'te' ? 'te-IN' : 'en-IN')
    + (stale ? ' · ' + t('caution_stale') : '')
    + (cautionData.sources_unavailable?.length ? ' · ' + t('caution_partial') : '');
  const items = Array.isArray(cautionData.articles) ? cautionData.articles : [];
  if (!items.length) { const p = document.createElement('p'); p.textContent = t('caution_empty'); container.append(p); return; }
  for (const item of items.slice(0, 6)) {
    let url;
    try { url = new URL(item.url); } catch { continue; }
    if (url.protocol !== 'https:' || !['www.bleepingcomputer.com', 'thehackernews.com'].includes(url.hostname) || url.username || url.password) continue;
    const article = document.createElement('article');
    const link = document.createElement('a');
    link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.textContent = item.title;
    const meta = document.createElement('p'); meta.className = 'hint';
    const published = new Date(item.published_at);
    meta.textContent = item.publisher + (Number.isNaN(published.getTime()) ? '' : ' · ' + published.toLocaleDateString(locale === 'hi' ? 'hi-IN' : locale === 'te' ? 'te-IN' : 'en-IN'));
    const summary = document.createElement('p'); summary.textContent = item.summary;
    article.append(link, meta, summary); container.append(article);
  }
}
(async () => {
  try {
    const response = await fetch('/static/cautions.json', {cache: 'no-store'});
    if (!response.ok) throw new Error('Unavailable');
    cautionData = await response.json();
  } catch { cautionFailed = true; }
  renderCautions();
})();
