window.iframeManager = {
  iframe: null,
  init(iframeId) {
    this.iframe = document.getElementById(iframeId);
    if (this.iframe) {
      this.iframe.addEventListener('load', () => {
        window.events.emit('iframe:loaded');
      });
    }
  },
  getDoc() { return this.iframe ? (this.iframe.contentDocument || this.iframe.contentWindow.document) : null; },
  setHTML(html) {
    const doc = this.getDoc();
    if (doc) { doc.open(); doc.write(html); doc.close(); }
  },
  getHTML() {
    const doc = this.getDoc();
    return doc ? doc.documentElement.outerHTML : '';
  }
};
