// Computes a base prefix for building URLs that work both at
// domain root and when mounted under a subpath like /movies/.
// Exposes window.PREFIX and window.api(path).
(function () {
  try {
    const seg = (window.location.pathname.split('/')[1] || '').trim();
    // Known top-level routes of this app when hosted at domain root
    const KNOWN = new Set([
      '',
      'admin',
      'tests',
      'api',
      'static',
      'database-status',
      'init-movie-database'
    ]);
    const prefix = KNOWN.has(seg) ? '' : '/' + seg;

    function buildApiPath(p) {
      let s = String(p || '');
      // Handle hash fragment
      let hash = '';
      const hashIdx = s.indexOf('#');
      if (hashIdx >= 0) {
        hash = s.slice(hashIdx);
        s = s.slice(0, hashIdx);
      }
      // Separate query string
      const qIdx = s.indexOf('?');
      const qs = qIdx >= 0 ? s.slice(qIdx) : '';
      const path = (qIdx >= 0 ? s.slice(0, qIdx) : s).replace(/^\/+/, '');
      const base = prefix || '';
      return (base ? base + '/' : '/') + path + qs + hash;
    }

    window.PREFIX = prefix;
    window.api = buildApiPath;
  } catch (e) {
    // Fallback: no prefixing
    window.PREFIX = '';
    window.api = function (p) {
      const s = String(p || '').replace(/^\/+/, '');
      return '/' + s;
    };
  }
})();

