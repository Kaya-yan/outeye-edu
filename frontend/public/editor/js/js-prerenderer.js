window.jsPrerenderer = {
  prerender(html) {
    if (!html) return html;
    // Wrap in a container to let inline scripts execute safely
    var container = document.createElement('div');
    container.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden;pointer-events:none;visibility:hidden';
    container.innerHTML = html;
    document.body.appendChild(container);

    // Execute any script tags in a safe isolated context
    var scripts = container.querySelectorAll('script');
    scripts.forEach(function (s) {
      try {
        if (s.src) return; // Skip external scripts for prerender
        var fn = new Function(s.textContent || '');
        fn();
      } catch (e) {
        // Silently skip failed scripts in prerender
      }
    });

    var result = container.innerHTML;
    document.body.removeChild(container);
    return result;
  },

  stripInteractive(html) {
    // Remove script and event handlers for static preview
    return (html || '')
      .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
      .replace(/\son\w+\s*=\s*"[^"]*"/gi, '')
      .replace(/\son\w+\s*=\s*'[^']*'/gi, '');
  }
};
