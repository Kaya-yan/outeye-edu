window.layoutDetector = {
  detect(el) {
    if (!el) return 'unknown';
    var cs = getComputedStyle(el);
    var display = cs.display;

    if (display === 'flex' || display === 'inline-flex') {
      var dir = cs.flexDirection;
      if (dir === 'row' || dir === 'row-reverse') return 'flex-row';
      if (dir === 'column' || dir === 'column-reverse') return 'flex-col';
      return 'flex';
    }
    if (display === 'grid' || display === 'inline-grid') return 'grid';
    if (display === 'block') return 'block';
    if (display === 'inline' || display === 'inline-block') return 'inline';
    if (display === 'none') return 'hidden';
    return display;
  },

  getLayoutInfo(el) {
    if (!el) return null;
    var cs = getComputedStyle(el);
    return {
      display: cs.display,
      position: cs.position,
      flexDirection: cs.flexDirection,
      gridTemplateColumns: cs.gridTemplateColumns,
      width: cs.width,
      height: cs.height,
      padding: cs.padding,
      margin: cs.margin,
      childrenCount: el.children.length,
    };
  },

  suggestImprovements(el) {
    var info = this.getLayoutInfo(el);
    if (!info) return [];
    var tips = [];
    if (info.display === 'block' && info.childrenCount >= 3) tips.push('考虑使用 flex 布局改善对齐');
    if (info.padding === '0px' && el.tagName !== 'SPAN') tips.push('添加内边距可以让内容呼吸');
    return tips;
  }
};
