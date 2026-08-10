window.propertyPanel = {
  el: null,
  containerId: null,

  init(containerId) {
    this.containerId = containerId;
    this.el = document.getElementById(containerId);
    if (!this.el) return;
    this.el.innerHTML = '<div style="padding:40px 16px;text-align:center;color:var(--text-tertiary, #9ca3af)"><p style="font-size:12px">点击页面元素开始编辑</p></div>';
    window.events.on('selection:changed', function (el) { window.propertyPanel.showFor(el); });
  },

  showFor(el) {
    if (!this.el) return;
    if (!el || el === document.body) {
      this.el.innerHTML = '<div style="padding:40px 16px;text-align:center;color:var(--text-tertiary, #9ca3af)"><p style="font-size:12px">点击页面元素查看属性</p></div>';
      return;
    }
    var tag = el.tagName ? el.tagName.toLowerCase() : '未知';
    var text = (el.textContent || '').trim().substring(0, 100);
    var html = '';

    html += '<div style="padding:12px">';
    html += '<h4 style="font-size:13px;font-weight:600;color:var(--text-primary,#1f2937);margin-bottom:8px">' + tag.toUpperCase() + ' 元素</h4>';

    // Text content
    if (text) {
      html += '<div style="margin-bottom:12px"><label style="font-size:10px;font-weight:600;color:var(--text-tertiary,#6b7280);text-transform:uppercase">文本</label>';
      html += '<textarea style="width:100%;min-height:60px;padding:6px 8px;border:1px solid var(--border-default, #e5e7eb);border-radius:6px;font-size:12px;resize:vertical;margin-top:4px;font-family:inherit" oninput="var s=window.selection.getSelected();if(s)s.textContent=this.value">' + text + '</textarea></div>';
    }

    // Style quick edits
    html += '<div style="margin-bottom:12px"><label style="font-size:10px;font-weight:600;color:var(--text-tertiary,#6b7280);text-transform:uppercase;display:block;margin-bottom:4px">快捷样式</label>';
    html += '<div style="display:flex;flex-wrap:wrap;gap:4px">';
    html += '<button onclick="var s=window.selection.getSelected();if(s)s.style.fontWeight=s.style.fontWeight===\'bold\'?\'\':\'bold\'" style="padding:4px 8px;border:1px solid #d1d5db;border-radius:4px;font-size:11px;background:#fff;cursor:pointer">B</button>';
    html += '<button onclick="var s=window.selection.getSelected();if(s)s.style.fontStyle=s.style.fontStyle===\'italic\'?\'\':\'italic\'" style="padding:4px 8px;border:1px solid #d1d5db;border-radius:4px;font-size:11px;background:#fff;cursor:pointer">I</button>';
    html += '<button onclick="var s=window.selection.getSelected();if(s)s.style.color=s.style.color===\'#e11d48\'?\'\':\'#e11d48\'" style="padding:4px 8px;border:1px solid #d1d5db;border-radius:4px;font-size:11px;background:#fff;cursor:pointer">A</button>';
    html += '<button onclick="var s=window.selection.getSelected();if(s)s.style.fontSize=s.style.fontSize===\'24px\'?\'\':\'24px\'" style="padding:4px 8px;border:1px solid #d1d5db;border-radius:4px;font-size:11px;background:#fff;cursor:pointer">+</button>';
    html += '</div></div>';

    // Save as component
    html += '<div style="border-top:1px solid var(--border-subtle,#f3f4f6);padding-top:12px">';
    html += '<button onclick="window.coursewareAPI.saveAsComponent()" style="width:100%;padding:8px;border:1px solid #7c3aed;border-radius:8px;background:#fff;color:#7c3aed;font-size:12px;font-weight:600;cursor:pointer">保存为我的组件</button></div>';

    // Delete element
    html += '<div style="margin-top:8px">';
    html += '<button onclick="var s=window.selection.getSelected();if(s){s.remove();window.selection.clear()}" style="width:100%;padding:6px;border:1px solid #fca5a5;border-radius:8px;background:#fff;color:#ef4444;font-size:11px;cursor:pointer">删除此元素</button></div>';

    html += '</div>';
    this.el.innerHTML = html;
  },

  showEmpty() {
    if (!this.el) return;
    this.el.innerHTML = '<div style="padding:40px 16px;text-align:center;color:var(--text-tertiary, #9ca3af)"><p style="font-size:12px">点击页面元素开始编辑</p></div>';
  }
};
