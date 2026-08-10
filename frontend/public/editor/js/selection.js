window.selection = {
  selected: null,
  onChange: null,

  select(el) {
    if (this.selected === el) return;
    this.clear();
    this.selected = el;
    this.showSelectBox(el);
    if (typeof this.onChange === 'function') this.onChange(el);
    window.events.emit('selection:changed', el);
  },

  clear() {
    if (this.selected) {
      try { this.selected.classList.remove('editor-selected'); } catch (e) { /* */ }
    }
    this.selected = null;
    var box = document.getElementById('selectBox');
    if (box) box.style.display = 'none';
  },

  showSelectBox(el) {
    var ifr = document.getElementById('editor-iframe');
    if (!ifr) return;
    try {
      var doc = ifr.contentDocument || ifr.contentWindow.document;
      var rect = el.getBoundingClientRect();
      var ifrRect = ifr.getBoundingClientRect();
      var box = document.getElementById('selectBox');
      if (!box) return;
      box.style.display = 'block';
      box.style.left = (rect.left - ifrRect.left) + 'px';
      box.style.top = (rect.top - ifrRect.top) + 'px';
      box.style.width = rect.width + 'px';
      box.style.height = rect.height + 'px';
    } catch (e) { /* cross-origin fallback */ }
  },

  getSelected: function () { return this.selected; }
};

(function bindIframeClick() {
  function attach() {
    var ifr = document.getElementById('editor-iframe');
    if (!ifr || !ifr.contentWindow) return;
    try {
      var doc = ifr.contentDocument || ifr.contentWindow.document;
      doc.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        window.selection.select(e.target);
      });
      doc.addEventListener('dblclick', function (e) {
        window.inlineEditor.start(e.target);
      });
    } catch (e) { /* */ }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      var f = document.getElementById('editor-iframe');
      if (f) f.addEventListener('load', attach);
    });
  } else {
    var f = document.getElementById('editor-iframe');
    if (f) f.addEventListener('load', attach);
  }
})();
