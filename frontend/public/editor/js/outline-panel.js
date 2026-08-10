window.outlinePanel = {
  el: null,

  init(containerId) {
    this.el = document.getElementById(containerId);
    if (!this.el) return;
    this.renderEmpty();
    window.events.on('pages:changed', this.refresh.bind(this));
    window.events.on('page:changed', this.refresh.bind(this));
    window.events.on('component:inserted', this.refresh.bind(this));
  },

  refresh() {
    if (!this.el) return;
    var ifr = window.pageManager ? window.pageManager.getCurrentIframe() : null;
    if (!ifr || !ifr.contentWindow) { this.renderEmpty(); return; }
    try {
      var doc = ifr.contentDocument || ifr.contentWindow.document;
      var structure = window.domAnnotator.getTeachingStructure(doc);
      this.render(structure);
    } catch (e) { this.renderEmpty(); }
  },

  render(structure) {
    if (!this.el) return;
    var comps = (structure.pages && structure.pages[0] && structure.pages[0].components) || [];
    if (comps.length === 0) { this.renderEmpty(); return; }

    var stageColors = { '导入': '#f59e0b', '讲授': '#3d5f9a', '阅读': '#059669', '活动': '#7c3aed', '检测': '#e11d48', '总结': '#0891b2', '作业': '#ea580c', '辅助': '#6b7280' };

    var html = '<div style="padding:8px"><div style="font-size:10px;font-weight:600;color:var(--text-tertiary,#6b7280);text-transform:uppercase;margin-bottom:6px;padding:0 4px">教学大纲</div>';
    comps.forEach(function (c, i) {
      var color = stageColors[c.stage] || '#6b7280';
      html += '<div style="display:flex;align-items:center;gap:6px;padding:5px 8px;margin:1px 0;font-size:11px;color:var(--text-secondary,#4b5563);border-radius:4px;cursor:pointer" onclick="var els=window.pageManager.getCurrentIframe().contentDocument.querySelectorAll(\'[data-component]\');var t=els[' + i + '];if(t)t.scrollIntoView({behavior:\'smooth\',block:\'center\'})">';
      html += '<span style="width:3px;height:3px;border-radius:50%;background:' + color + ';flex-shrink:0"></span>';
      html += '<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + (c.text || c.type || '组件') + '</span>';
      html += '<span style="font-size:9px;color:' + color + '">' + c.stage + '</span>';
      html += '</div>';
    });
    html += '</div>';
    this.el.innerHTML = html;
  },

  renderEmpty() {
    if (!this.el) return;
    this.el.innerHTML = '<div style="padding:16px;text-align:center;font-size:11px;color:var(--text-tertiary,#9ca3af)">暂无教学组件<br/><span style="font-size:10px">从左侧拖入组件开始构建课件</span></div>';
  }
};
