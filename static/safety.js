/* Verification and recovery stay in the browser. No complaint fields are sent. */
let evidenceTime = null;
let completedActions = new Set();
let fingerprintStatus = null;

function renderSafetyLanguage() {
  if (fingerprintStatus) $('fingerprint-result').textContent = t(fingerprintStatus);
  if (!$('complaint-error').hidden) $('complaint-error').textContent = t('secret_detected');
}
const demoMessages = {
  family: "Hi mom this is my new number. My phone broke. Send money to my friend's account urgently and don't call.",
  college: 'I am the college finance officer. Pay examination charges into my private account today.',
  genuine: 'The placement cell says no employer should ask you for a joining deposit.'
};

function resetSafety() {
  evidenceTime = null;
  completedActions.clear();
  $('verification').value = 'pending';
  $('exposure').value = 'none';
  $('feedback').value = 'none';
  $('complaint').reset();
  $('draft').value = '';
  $('handoff').hidden = true;
  $('complaint-error').hidden = true;
  $('copied').textContent = '';
}

function planKeys() {
  if ($('exposure').value === 'money') return ['plan_bank', 'plan_1930', 'plan_preserve', 'plan_report'];
  if ($('exposure').value === 'access') return ['plan_access', 'plan_bank', 'plan_preserve', 'plan_report'];
  if ($('verification').value === 'denied') return ['plan_stop', 'plan_preserve', 'plan_report'];
  if ($('verification').value === 'confirmed') return ['plan_destination', 'plan_secrets'];
  return ['plan_verify', 'plan_secrets', 'plan_preserve'];
}

function renderSafety(result) {
  if (!evidenceTime) evidenceTime = new Date().toISOString();
  const assessment = result.scam;
  const score = assessment?.score;
  const hasScore = typeof score === 'number' && Number.isFinite(score);
  let level = assessment?.level || 'unknown';
  if ($('exposure').value !== 'none') level = 'urgent';
  else if ($('verification').value === 'denied') level = 'high';
  $('risk-label').textContent = t('risk_' + level);
  $('risk-label').className = 'risk-label risk-' + level;
  $('risk-meter').hidden = !hasScore;
  $('risk-meter').dataset.level = assessment?.level || 'unknown';
  if (hasScore) $('risk-meter').value = score;
  $('risk-meter').setAttribute('aria-label', t('warning_score'));
  $('score-caption').textContent = hasScore
    ? t('warning_score') + ' ' + Math.round(score * 100) + '/100 · ' + t('score_limit')
    : t('no_message_score');
  $('risk-reason').textContent = t(result.scam ? 'risk_reason_text' : 'risk_reason_media');
  $('learned-terms').textContent = assessment?.terms?.length
    ? t('learned_terms') + ' “' + assessment.terms.join('”, “') + '”.'
    : t('terms_unavailable');
  $('verification-note').textContent = t('verification_' + $('verification').value);
  const plan = $('action-plan');
  plan.replaceChildren();
  for (const key of planKeys()) {
    const item = document.createElement('li');
    const wrapper = document.createElement('div');
    wrapper.className = 'action-check';
    const check = document.createElement('input');
    check.type = 'checkbox';
    check.id = key;
    check.checked = completedActions.has(key);
    check.addEventListener('change', () => {
      if (check.checked) completedActions.add(key);
      else completedActions.delete(key);
    });
    const label = document.createElement('label');
    label.htmlFor = key;
    label.textContent = t(key);
    wrapper.append(check, label);
    item.append(wrapper);
    plan.append(item);
  }
}

function downloadLocal(name, content, mime) {
  const url = URL.createObjectURL(new Blob([content], {type: mime}));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = name;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function evidenceSummary() {
  const result = lastResult;
  return {
    format: 'physiocheck-evidence-v1',
    created_at: evidenceTime,
    exported_at: new Date().toISOString(),
    input: {kind: result.kind, sha256: result.input_sha256, source: result.input_source, encoding: result.input_source === 'pasted_text' ? 'UTF-8 of trimmed submitted text' : 'original uploaded bytes'},
    assessment: {
      model: result.model || null,
      ai_generation_estimate: result.is_ai ?? null,
      media_assessment: result.assessment || result.verdict || null,
      message_model: result.scam || {status: 'not_assessed'},
      provenance_limit: t(result.notice_key),
      message_limit: t('scam_model_limit')
    },
    user_reported: {
      independent_contact: $('verification').value,
      exposure: $('exposure').value,
      correction: $('feedback').value,
      completed_steps: [...completedActions]
    },
    action_plan: planKeys().map(key => ({step: key, instruction: t(key), done: completedActions.has(key)})),
    limitations: [t('evidence_integrity'), t('score_limit')],
    official_sources: ['https://cybercrime.gov.in/', 'https://cybercrime.gov.in/webform/FAQ.aspx'],
    complaint_submitted: false
  };
}

$('verification').addEventListener('change', () => { if (lastResult) renderSafety(lastResult); });
$('exposure').addEventListener('change', () => { if (lastResult) renderSafety(lastResult); });
$('evidence').addEventListener('click', () => {
  if (lastResult) downloadLocal('physiocheck-evidence.json', JSON.stringify(evidenceSummary(), null, 2), 'application/json');
});

function openComplaint() {
  $('complaint-dialog').showModal();
  $('incident').focus();
}
$('help-open').addEventListener('click', openComplaint);
$('report-open').addEventListener('click', openComplaint);
$('help-close').addEventListener('click', () => $('complaint-dialog').close());

function hasSecret(text) {
  return /\b(?:otp|pin|password|passcode|verification code)\s*(?:is|:|=)?\s*\d{4,8}\b/i.test(text)
    || /(?<!\d)(?:\d[ -]?){15}\d(?!\d)/.test(text)
    || /(?<!\d)\d{4}[ -]\d{4}[ -]\d{4}(?!\d)/.test(text);
}
function validateDraft(text) {
  const invalid = hasSecret(text);
  $('complaint-error').hidden = !invalid;
  $('complaint-error').textContent = invalid ? t('secret_detected') : '';
  return !invalid;
}
$('complaint').addEventListener('input', () => {
  $('handoff').hidden = true;
  $('draft').value = '';
  $('copied').textContent = '';
});
$('draft').addEventListener('input', () => { $('copied').textContent = ''; });
$('complaint').addEventListener('submit', event => {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  const fields = [['incident', 'incident_label'], ['date', 'date_label'], ['contact', 'contact_label'], ['payment', 'payment_label']];
  const text = fields.filter(([key]) => data.get(key).trim())
    .map(([key, label]) => t(label) + '\n' + data.get(key).trim()).join('\n\n');
  if (!validateDraft(text)) return;
  $('draft').value = text;
  $('handoff').hidden = false;
  $('draft').focus();
});
$('copy').addEventListener('click', async () => {
  if (!validateDraft($('draft').value)) return;
  try {
    await navigator.clipboard.writeText($('draft').value);
    $('copied').textContent = t('copied');
  } catch {
    $('draft').select();
    $('copied').textContent = t('copy_manual');
  }
});
$('save-draft').addEventListener('click', () => {
  if (validateDraft($('draft').value)) downloadLocal('complaint-draft.txt', $('draft').value, 'text/plain;charset=utf-8');
});
document.querySelectorAll('[data-demo]').forEach(button => {
  button.addEventListener('click', () => {
    if (busy) return;
    removeFile();
    $('input').value = demoMessages[button.dataset.demo];
    $('input').focus();
  });
});

$('verify-fingerprint').addEventListener('click', async () => {
  const summary = $('summary-file').files[0];
  const original = $('original-file').files[0];
  const showFingerprint = key => { fingerprintStatus = key; renderSafetyLanguage(); };
  if (!summary || !original) { showFingerprint('fingerprint_choose'); return; }
  if (summary.size > 1024 * 1024 || original.size > 50 * 1024 * 1024) {
    showFingerprint('file_large'); return;
  }
  try {
    const record = JSON.parse(await summary.text());
    if (record.format !== 'physiocheck-evidence-v1' || !/^[a-f0-9]{64}$/.test(record.input?.sha256)
      || !['file_bytes', 'pasted_text'].includes(record.input.source)) throw new Error('Invalid summary');
    let bytes = await original.arrayBuffer();
    if (record.input.source === 'pasted_text') {
      const text = new TextDecoder('utf-8', {fatal: true}).decode(bytes).trim();
      bytes = new TextEncoder().encode(text);
    }
    const digest = await crypto.subtle.digest('SHA-256', bytes);
    const hex = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
    showFingerprint(hex === record.input.sha256 ? 'fingerprint_match' : 'fingerprint_mismatch');
  } catch { showFingerprint('fingerprint_invalid'); }
});
