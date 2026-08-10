window.iconLibrary = {
  icons: [
    { name: 'book', svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/></svg>' },
    { name: 'pencil', svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 3a2.85 2.83 0 114 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>' },
    { name: 'chart', svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"/><path d="M7 14l3-3 3 3 5-5"/></svg>' },
    { name: 'users', svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75"/></svg>' },
    { name: 'clock', svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>' },
    { name: 'star', svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l3 6.5L22 9l-5 4.5L18.5 21 12 17l-6.5 4L7 13.5 2 9l7-.5z"/></svg>' },
    { name: 'lightbulb', svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18h6M10 22h4M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0018 8 6 6 0 006 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 018.91 14"/></svg>' },
    { name: 'check', svg: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5"/></svg>' },
  ],

  init() {},

  getIcon(name) {
    var found = this.icons.find(function (i) { return i.name === name; });
    return found ? found.svg : null;
  },

  getAll() { return this.icons; },

  renderInto(containerId) {
    var el = document.getElementById(containerId);
    if (!el) return;
    var html = '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:4px;padding:8px">';
    this.icons.forEach(function (icon) {
      html += '<div draggable="true" data-icon="' + icon.name + '" style="padding:8px;border-radius:6px;cursor:grab;display:flex;align-items:center;justify-content:center;transition:background 0.15s" onmouseenter="this.style.background=\'rgba(0,0,0,0.04)\'" onmouseleave="this.style.background=\'transparent\'" title="' + icon.name + '">' + icon.svg.replace('<svg', '<svg style="width:18px;height:18px"') + '</div>';
    });
    html += '</div>';
    el.innerHTML = html;
  }
};
