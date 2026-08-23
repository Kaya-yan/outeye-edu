// 页面管理只维护页面状态（标题 + HTML 字符串），渲染统一委托给
// iframeManager 的唯一 editor-iframe。此前本模块自建一套平行 iframe，
// 导致点击监听（selection.js 只绑 editor-iframe）失效与视觉错位。
window.pageManager = {
  pages: [],
  current: 0,

  init() {
    if (this.pages.length === 0) {
      // 已有渲染内容（平台载入的课件）时收编为第 1 页，避免被空白页覆盖
      var rendered = window.iframeManager ? window.iframeManager.getHTML() : '';
      var hasContent = rendered && rendered.replace(/<[^>]*>/g, '').trim().length > 0;
      this.addPage({ title: '第 1 页', html: hasContent ? rendered : '' }, true);
    }
    this.switchTo(0);
    window.events.emit('page:changed', 0);
  },

  blankHTML(title) {
    return '<div style="padding:40px;text-align:center;color:#9ca3af;font-family:system-ui,sans-serif"><h2 style="font-size:24px;margin-bottom:8px">' + title + '</h2><p style="font-size:14px">在此添加内容</p></div>';
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
    if (!silent) {
      this.switchTo(this.pages.length - 1);
      window.events.emit('pages:changed');
    }
    return page;
  },

  removePage(idx) {
    if (this.pages.length <= 1) return false;
    this.pages.splice(idx, 1);
    var newIdx = Math.min(idx, this.pages.length - 1);
    this.switchTo(newIdx);
    window.events.emit('pages:changed');
    return true;
  },

  switchTo(idx) {
    if (idx < 0 || idx >= this.pages.length) return;
    this.saveCurrentHTML();
    this.current = idx;
    var page = this.pages[idx];
    if (window.iframeManager) {
      window.iframeManager.setHTML(page.html || this.blankHTML(page.title));
    }
    window.events.emit('page:changed', idx);
  },

  saveCurrentHTML() {
    var cur = this.pages[this.current];
    if (!cur || !window.iframeManager || !window.iframeManager.iframe) return;
    try {
      var doc = window.iframeManager.getDoc();
      if (doc && doc.documentElement) cur.html = doc.documentElement.outerHTML;
    } catch (e) { /* cross-origin */ }
  },

  getCurrentHTML() {
    this.saveCurrentHTML();
    var cur = this.pages[this.current];
    return cur ? (cur.html || '') : '';
  },

  getAllHTML() {
    this.saveCurrentHTML();
    return this.pages.map(function (p) {
      return p.html || '<div></div>';
    }).join('\n');
  },

  getCurrentIframe() {
    return window.iframeManager ? window.iframeManager.iframe : null;
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
