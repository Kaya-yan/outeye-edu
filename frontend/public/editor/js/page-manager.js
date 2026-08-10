window.pageManager = {
  pages: [],
  current: 0,

  init() {
    // Create initial blank page
    if (this.pages.length === 0) {
      this.addPage({ title: '第 1 页' }, true);
    }
    this.switchTo(0);
    window.events.emit('page:changed', 0);
  },

  addPage(opts, silent) {
    opts = opts || {};
    var id = 'page-' + Date.now().toString(36) + '-' + Math.random().toString(36).substring(2, 6);
    var page = {
      id: id,
      title: opts.title || ('第 ' + (this.pages.length + 1) + ' 页'),
      html: opts.html || '',
    };
    this.pages.push(page);

    // Create iframe in wrapper
    var wrapper = document.getElementById('iframeWrapper');
    if (wrapper) {
      var ifr = document.createElement('iframe');
      ifr.id = id;
      ifr.setAttribute('sandbox', 'allow-same-origin allow-scripts');
      ifr.style.cssText = 'width:100%;min-height:600px;border:0;display:none;position:absolute;top:0;left:0';
      ifr.srcdoc = page.html || '<div style="padding:40px;text-align:center;color:#9ca3af;font-family:system-ui,sans-serif"><h2 style="font-size:24px;margin-bottom:8px">' + page.title + '</h2><p style="font-size:14px">在此添加内容</p></div>';
      wrapper.style.position = 'relative';
      wrapper.appendChild(ifr);
    }

    if (!silent) {
      this.switchTo(this.pages.length - 1);
      window.events.emit('pages:changed');
    }
    return page;
  },

  removePage(idx) {
    if (this.pages.length <= 1) return false;
    var page = this.pages[idx];
    var ifr = document.getElementById(page.id);
    if (ifr) ifr.remove();
    this.pages.splice(idx, 1);
    var newIdx = Math.min(idx, this.pages.length - 1);
    this.switchTo(newIdx);
    window.events.emit('pages:changed');
    return true;
  },

  switchTo(idx) {
    if (idx < 0 || idx >= this.pages.length) return;
    // Save current page HTML before switching
    this.saveCurrentHTML();
    // Hide all, show target
    this.current = idx;
    this.pages.forEach(function (p) {
      var f = document.getElementById(p.id);
      if (f) f.style.display = 'none';
    });
    var target = document.getElementById(this.pages[idx].id);
    if (target) {
      target.style.display = 'block';
      target.style.position = 'static';
    }
    window.events.emit('page:changed', idx);
  },

  saveCurrentHTML() {
    var cur = this.pages[this.current];
    if (!cur) return;
    var ifr = document.getElementById(cur.id);
    if (!ifr) return;
    try {
      var doc = ifr.contentDocument || ifr.contentWindow.document;
      cur.html = doc.documentElement.outerHTML;
    } catch (e) { /* cross-origin */ }
  },

  getCurrentHTML() {
    var cur = this.pages[this.current];
    if (!cur) return '';
    var ifr = document.getElementById(cur.id);
    if (!ifr) return cur.html || '';
    try {
      return (ifr.contentDocument || ifr.contentWindow.document).documentElement.outerHTML;
    } catch (e) {
      return cur.html || '';
    }
  },

  getAllHTML() {
    var self = this;
    this.saveCurrentHTML();
    return this.pages.map(function (p) {
      return p.html || '<div></div>';
    }).join('\n');
  },

  getCurrentIframe() {
    return document.getElementById(this.pages[this.current] ? this.pages[this.current].id : '');
  },

  listPages: function () { return this.pages; },

  reorderPages(from, to) {
    if (from < 0 || to < 0 || from >= this.pages.length || to >= this.pages.length) return;
    this.saveCurrentHTML();
    var item = this.pages.splice(from, 1)[0];
    this.pages.splice(to, 0, item);
    this.switchTo(to);
    window.events.emit('pages:changed');
  },

  renamePage(idx, title) {
    if (idx < 0 || idx >= this.pages.length) return;
    this.pages[idx].title = title;
    window.events.emit('pages:changed');
  }
};
