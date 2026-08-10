window.inlineEditor = {
  isEditing: false,
  editingEl: null,

  start(el) {
    if (!el || el === document.body || el === document.documentElement) return;
    if (this.isEditing) this.stop();
    this.isEditing = true;
    this.editingEl = el;
    el.contentEditable = 'true';
    el.focus();
    el.style.outline = '2px solid var(--accent, #7c3aed)';
    var sel = window.getSelection();
    if (sel) { var range = document.createRange(); range.selectNodeContents(el); sel.removeAllRanges(); sel.addRange(range); }

    var done = function () {
      el.contentEditable = 'false';
      el.style.outline = '';
      window.inlineEditor.isEditing = false;
      window.inlineEditor.editingEl = null;
      window.iframeManager.pushSnapshot();
    };
    el.addEventListener('blur', done, { once: true });
    el.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { e.preventDefault(); el.blur(); }
    }, { once: true });
  },

  stop() {
    if (!this.editingEl) return;
    this.editingEl.contentEditable = 'false';
    this.editingEl.style.outline = '';
    this.isEditing = false;
    this.editingEl = null;
  }
};
