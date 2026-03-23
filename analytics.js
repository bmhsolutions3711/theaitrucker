/* ── LoadCalc Analytics Tracker ──
   Lightweight, privacy-first event tracking.
   Events are sent to a Google Apps Script endpoint
   that writes to a Google Sheet. No cookies, no PII.
*/
(function() {
  // ⚠️ Replace this URL after deploying the Google Apps Script
  var ENDPOINT = 'https://script.google.com/macros/s/AKfycbypBXf9HXzcJzvhzZWmYkYhFrrwIKSe2HOAii2F7fXrN9641nqBxlBP4ffQ4iOALXar/exec';

  // Random session ID (not stored between visits)
  var sid = Math.random().toString(36).slice(2, 10);
  var page = location.pathname.split('/').pop() || 'index.html';

  function send(event, label, value) {
    if (!ENDPOINT || ENDPOINT.includes('URL_HERE')) return; // skip if not configured
    var data = {
      timestamp: new Date().toISOString(),
      page: page,
      event: event,
      label: label || '',
      value: value || '',
      referrer: document.referrer || '',
      sessionId: sid
    };
    // Use sendBeacon for reliability (survives page unload)
    if (navigator.sendBeacon) {
      navigator.sendBeacon(ENDPOINT, JSON.stringify(data));
    } else {
      fetch(ENDPOINT, { method: 'POST', body: JSON.stringify(data), keepalive: true }).catch(function(){});
    }
  }

  // Expose globally so we can call from inline handlers
  window.lcTrack = send;

  // Auto-track page view
  send('page_view', document.title);

  // Auto-track payment success redirect
  if (location.search.indexOf('success=1') !== -1) {
    send('payment_success');
  }

  // Auto-track CTA link clicks (nav-cta, btn-primary, btn-secondary, pc-btn)
  document.addEventListener('click', function(e) {
    var el = e.target.closest('a.nav-cta, a.btn-primary, a.btn-secondary, a.pc-btn, button.pc-btn');
    if (el) {
      send('cta_click', el.textContent.trim().substring(0, 50));
    }
  });
})();
