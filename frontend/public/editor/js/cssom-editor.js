window.cssomEditor = {
  getStyles(el) {
    if (!el) return {};
    var cs = getComputedStyle(el);
    return {
      color: cs.color, backgroundColor: cs.backgroundColor,
      fontSize: cs.fontSize, fontWeight: cs.fontWeight,
      fontStyle: cs.fontStyle, textAlign: cs.textAlign,
      padding: cs.padding, margin: cs.margin,
      borderRadius: cs.borderRadius, border: cs.border,
      lineHeight: cs.lineHeight,
    };
  },

  setStyle(el, prop, val) {
    if (!el) return;
    el.style[prop] = val;
    this._emitChange(el);
  },

  applyStyleSet(el, styles) {
    if (!el) return;
    Object.keys(styles).forEach(function (k) { el.style[k] = styles[k]; });
    this._emitChange(el);
  },

  _emitChange(el) {
    window.events.emit('style:changed', el);
    window.iframeManager.pushSnapshot();
  },

  // Quick presets
  presets: {
    'heading-primary': { fontSize: '32px', fontWeight: '700', color: '#1e3a5f' },
    'heading-secondary': { fontSize: '20px', fontWeight: '600', color: '#3d5f9a' },
    'body-text': { fontSize: '15px', lineHeight: '1.8', color: '#374151' },
    'caption': { fontSize: '12px', color: '#6b7280', lineHeight: '1.5' },
    'highlight-box': { padding: '16px', borderRadius: '8px', backgroundColor: '#eef3f9' },
  },

  applyPreset(el, name) {
    if (!el || !this.presets[name]) return;
    this.applyStyleSet(el, this.presets[name]);
  }
};
