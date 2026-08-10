window.animationManager = {
  presets: {
    'fade-in': 'animation:fadeIn 0.4s ease-out',
    'slide-up': 'animation:slideUp 0.5s ease-out',
    'scale-in': 'animation:scaleIn 0.3s ease-out',
    'none': '',
  },

  init() {
    // Inject animation keyframes into the editor iframe
    this._injectStyles();
  },

  _injectStyles() {
    var css = '@keyframes fadeIn{from{opacity:0}to{opacity:1}}@keyframes slideUp{from{transform:translateY(20px);opacity:0}to{transform:translateY(0);opacity:1}}@keyframes scaleIn{from{transform:scale(0.95);opacity:0}to{transform:scale(1);opacity:1}}';
    var style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);
  },

  apply(el, name) {
    if (!el || !name) return;
    var preset = this.presets[name];
    if (preset) el.style.cssText = (el.style.cssText || '') + ';' + preset;
    if (!preset) el.style.cssText = (el.style.cssText || '').replace(/animation:[^;]+;?/g, '');
  },

  setEntranceAnimation(el, type) {
    this.apply(el, type);
  },

  removeAnimation(el) {
    if (!el) return;
    el.style.cssText = (el.style.cssText || '').replace(/animation:[^;]+;?/g, '');
  }
};
