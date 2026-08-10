window.dragManager = {
  dragging: null,
  insertIndicator: null,

  init() {
    var self = this;
    this.insertIndicator = document.getElementById('insertIndicator');
    if (!this.insertIndicator) {
      this.insertIndicator = document.createElement('div');
      this.insertIndicator.id = 'insertIndicator';
      this.insertIndicator.style.cssText = 'position:absolute;height:2px;background:var(--accent,#7c3aed);display:none;z-index:15;pointer-events:none';
      var wrapper = document.getElementById('iframeWrapper');
      if (wrapper) wrapper.appendChild(this.insertIndicator);
    }

    // Attach dragstart to all material items
    document.querySelectorAll('.material-item[draggable]').forEach(function (item) {
      item.addEventListener('dragstart', function (e) {
        var compType = this.getAttribute('data-component');
        if (!compType) return;
        self.dragging = compType;
        e.dataTransfer.setData('text/plain', compType);
        e.dataTransfer.effectAllowed = 'copy';
        this.style.opacity = '0.5';
      });
      item.addEventListener('dragend', function () {
        self.dragging = null;
        this.style.opacity = '1';
        if (self.insertIndicator) self.insertIndicator.style.display = 'none';
      });
    });

    // Drop target on canvas wrapper
    var canvasContainer = document.querySelector('.canvas-container');
    if (canvasContainer) {
      canvasContainer.addEventListener('dragover', function (e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'copy';
        var wrapper = document.getElementById('iframeWrapper');
        if (self.insertIndicator && wrapper) {
          var rect = wrapper.getBoundingClientRect();
          var relY = e.clientY - rect.top;
          self.insertIndicator.style.display = 'block';
          self.insertIndicator.style.top = relY + 'px';
          self.insertIndicator.style.left = '0';
          self.insertIndicator.style.width = rect.width + 'px';
        }
      });
      canvasContainer.addEventListener('dragleave', function () {
        if (self.insertIndicator) self.insertIndicator.style.display = 'none';
      });
      canvasContainer.addEventListener('drop', function (e) {
        e.preventDefault();
        if (self.insertIndicator) self.insertIndicator.style.display = 'none';
        var compType = self.dragging || e.dataTransfer.getData('text/plain');
        if (!compType) return;
        self.dragging = null;

        // Ensure page exists
        if (!window.pageManager || window.pageManager.pages.length === 0) {
          if (window.pageManager) window.pageManager.init();
          else return;
        }

        // Get current page iframe and insert component
        var ifr = window.pageManager.getCurrentIframe();
        if (!ifr) return;
        try {
          var doc = ifr.contentDocument || ifr.contentWindow.document;
          var el = window.elementFactory.create(compType, doc);
          if (el) {
            el.setAttribute('data-component', compType);
            doc.body.appendChild(el);
            window.selection.select(el);
            window.events.emit('component:inserted', el);
            window.iframeManager.pushSnapshot();
          }
        } catch (err) {
          // fallback: insert HTML into current page and reload iframe
          var page = window.pageManager.pages[window.pageManager.current];
          if (page) {
            var html = window.elementFactory.getTemplate(compType);
            if (html) {
              page.html = (page.html || '') + html;
              ifr.srcdoc = page.html;
            }
          }
        }
      });
    }
  }
};

// Auto-init on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', function () { window.dragManager.init(); });
} else {
  window.dragManager.init();
}
