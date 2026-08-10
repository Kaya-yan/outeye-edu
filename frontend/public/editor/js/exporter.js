window.exporter = {
  getHTML() { return window.iframeManager.getHTML(); },
  download(filename) {
    const html = this.getHTML();
    const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
  },
  copyToClipboard() {
    navigator.clipboard.writeText(this.getHTML()).catch(() => {});
  }
};
