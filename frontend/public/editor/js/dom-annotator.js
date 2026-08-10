window.domAnnotator = {
  annotate(doc) {
    if (!doc) return;
    var stageMap = (window.elementFactory && window.elementFactory.stageMap) || {};
    var allComps = doc.querySelectorAll('[data-component]');
    allComps.forEach(function (el) {
      var type = el.getAttribute('data-component');
      var stage = stageMap[type];
      if (stage && !el.querySelector('.tc-stage-badge')) {
        var badge = doc.createElement('div');
        badge.className = 'tc-stage-badge';
        badge.textContent = stage;
        badge.style.cssText = 'position:absolute;top:-10px;left:8px;font-size:10px;padding:1px 6px;border-radius:3px;background:#7c3aed;color:#fff;z-index:5;pointer-events:none;display:none';
        var cs = el.style.position || getComputedStyle(el).position;
        if (cs === 'static') el.style.position = 'relative';
        el.appendChild(badge);
      }
    });

    var styleEl = doc.getElementById('tc-editor-styles');
    if (!styleEl) {
      styleEl = doc.createElement('style');
      styleEl.id = 'tc-editor-styles';
      styleEl.textContent = '[data-editable]:hover{outline:1px dashed rgba(124,58,237,0.3);outline-offset:2px;cursor:text} [data-component]:hover .tc-stage-badge{display:block!important}';
      (doc.head || doc.documentElement).appendChild(styleEl);
    }
  },

  clear() {},

  getTeachingStructure(doc) {
    if (!doc) return { pages: [] };
    var comps = doc.querySelectorAll('[data-component]');
    var structure = [];
    comps.forEach(function (el, i) {
      structure.push({
        index: i,
        type: el.getAttribute('data-component') || '',
        stage: ((window.elementFactory && window.elementFactory.stageMap) || {})[el.getAttribute('data-component')] || '未知',
        text: (el.textContent || '').trim().substring(0, 80),
      });
    });
    return { pages: [{ components: structure }] };
  }
};
