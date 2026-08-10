window.pagePanel = {
  el: null,

  init(containerId) {
    this.el = document.getElementById(containerId);
    if (!this.el) return;
    this.render();
    window.events.on('pages:changed', this.render.bind(this));
    window.events.on('page:changed', this.render.bind(this));
  },

  render() {
    if (!this.el) return;
    var pages = window.pageManager ? window.pageManager.pages : [];
    var current = window.pageManager ? window.pageManager.current : 0;
    var html = '<div style="padding:8px"><div style="font-size:10px;font-weight:600;color:var(--text-tertiary,#6b7280);text-transform:uppercase;margin-bottom:4px;padding:0 4px">页面 (' + pages.length + ')</div>';

    pages.forEach(function (page, i) {
      var isActive = i === current;
      html += '<div style="display:flex;align-items:center;gap:6px;padding:6px 8px;margin:2px 0;border-radius:6px;cursor:pointer;' + (isActive ? 'background:#eef3f9;color:#2f4b7d;font-weight:600' : 'color:var(--text-secondary,#4b5563)') + '" onclick="window.pageManager.switchTo(' + i + ')">';
      html += '<span style="font-size:10px;opacity:0.5;min-width:18px">' + (i + 1) + '</span>';
      html += '<span style="flex:1;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + (page.title || 'Page ' + (i + 1)) + '</span>';
      if (pages.length > 1) {
        html += '<button onclick="event.stopPropagation();window.pageManager.removePage(' + i + ')" style="background:none;border:none;color:#ef4444;cursor:pointer;font-size:14px;line-height:1;padding:0 2px" title="删除">&times;</button>';
      }
      html += '</div>';
    });

    html += '<button onclick="window.pageManager.addPage({title:\'第 ' + (pages.length + 1) + ' 页\'})" style="width:100%;margin-top:8px;padding:6px;border:1px dashed #d1d5db;border-radius:6px;background:transparent;color:var(--text-tertiary,#9ca3af);font-size:11px;cursor:pointer">+ 添加页面</button>';
    html += '</div>';
    this.el.innerHTML = html;
  }
};
