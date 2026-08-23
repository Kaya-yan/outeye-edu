window.iframeManager = {
  iframe: null,
  _lastSrcdoc: null,
  _applyingSrcdoc: false,
  init(iframeId) {
    this.iframe = document.getElementById(iframeId);
    if (this.iframe) {
      this.iframe.addEventListener('load', () => {
        if (this._applyingSrcdoc) {
          // 本次 load 由 setHTML 的 srcdoc 写入触发，不能再向 main.js 广播
          // iframe:loaded，否则会重复回灌 editorState.html 造成循环重载
          this._applyingSrcdoc = false;
          return;
        }
        window.events.emit('iframe:loaded');
      });
    }
  },
  getDoc() { return this.iframe ? (this.iframe.contentDocument || this.iframe.contentWindow.document) : null; },
  // 用 srcdoc 取代 doc.open/write/close：每次写入都解析为全新文档，
  // 页内脚本（如 PLAN_DATA 声明）不会跨次残留重执行，动画课件不再白屏
  setHTML(html) {
    if (!this.iframe || html === this._lastSrcdoc) return;
    this._applyingSrcdoc = true;
    this._lastSrcdoc = html;
    this.iframe.srcdoc = html;
  },
  getHTML() {
    const doc = this.getDoc();
    return doc && doc.documentElement ? doc.documentElement.outerHTML : '';
  },
  pushSnapshot() {
    const html = this.getHTML();
    if (html && window.undoRedo) window.undoRedo.push({ html: html });
  }
};
