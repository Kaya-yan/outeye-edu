window.HTMLSanitizer = {
  sanitize(html) {
    if (!html || typeof html !== 'string') return '';
    // Strip event handlers and javascript: URIs
    var cleaned = html
      .replace(/\son\w+\s*=\s*"[^"]*"/gi, '')
      .replace(/\son\w+\s*=\s*'[^']*'/gi, '')
      .replace(/\son\w+\s*=\s*[^\s>]+/gi, '')
      .replace(/javascript\s*:/gi, 'data-blocked-')
      .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
    return cleaned;
  },

  stripScripts(html) {
    return html.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
  },

  wrapBody(content) {
    return '<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><style>body{font-family:system-ui,-apple-system,sans-serif;margin:0;padding:20px;line-height:1.6;color:#1f2937} [data-editable]{outline:none} [data-reveal]{display:none}</style></head><body>' + content + '</body></html>';
  },

  injectRevealCSS(html) {
    var css = '<style>[data-reveal]{display:none}[data-reveal].revealed{display:block} [data-section]{scroll-margin-top:20px}</style>';
    var idx = html.indexOf('</head>');
    if (idx > -1) return html.substring(0, idx) + css + html.substring(idx);
    return '<style>[data-reveal]{display:none}</style>' + html;
  }
};
