(function () {
  'use strict';

  var editorState = {
    html: '',
    schema: null,
    projectId: null,
    versionId: null,
    mode: 'slides',
    title: '',
    autoSaveTimer: null,
  };

  function init() {
    window.iframeManager.init('editor-iframe');

    window.events.on('iframe:loaded', function () {
      if (editorState.html) {
        window.iframeManager.setHTML(editorState.html);
      }
    });

    initUI();
    initMessages();
    console.log('[Editor] Initialized');
  }

  function initUI() {
    var importPage = document.getElementById('importPage');
    // Hide import page, show workspace immediately if we received data from platform
    var workspace = document.querySelector('.workspace');
    if (importPage) importPage.style.display = 'none';
    if (workspace) workspace.style.display = 'flex';

    window.propertyPanel.init('propertyContent');
  }

  function initMessages() {
    window.addEventListener('message', function (e) {
      if (!e.data || !e.data.type) return;

      switch (e.data.type) {
        case 'editor:load':
          handleLoad(e.data.payload);
          break;
        case 'editor:requestState':
          sendState();
          break;
        case 'editor:setMode':
          editorState.mode = e.data.payload.mode;
          break;
        default:
          break;
      }
    });

    // Notify parent that editor is ready
    window.parent.postMessage({ type: 'editor:ready' }, window.location.origin);
  }

  function handleLoad(payload) {
    editorState.html = payload.rendered_html || payload.html || '';
    editorState.schema = payload.editor_schema_json || null;
    editorState.projectId = payload.project_id || null;
    editorState.versionId = payload.version_id || null;
    editorState.mode = payload.mode || 'slides';
    editorState.title = payload.title || '';

    if (window.iframeManager && window.iframeManager.setHTML) {
      window.iframeManager.setHTML(editorState.html);
    }

    document.querySelector('.brand-name') && (document.querySelector('.brand-name').textContent = editorState.title || 'OutEye Edu');
    updateAutoSaveIndicator();
  }

  function sendState() {
    var html = window.iframeManager ? window.iframeManager.getHTML() : editorState.html;
    window.parent.postMessage({
      type: 'editor:state',
      payload: {
        rendered_html: html,
        editor_schema_json: editorState.schema,
        project_id: editorState.projectId,
        version_id: editorState.versionId,
        mode: editorState.mode,
      }
    }, window.location.origin);
  }

  function updateAutoSaveIndicator() {
    var el = document.querySelector('.auto-save-time');
    if (el) {
      var now = new Date();
      el.textContent = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');
    }
  }

  // Expose for toolbar buttons
  window.editorAPI = {
    getState: function () { return editorState; },
    requestSave: function () {
      sendState();
      window.parent.postMessage({ type: 'editor:requestSave' }, window.location.origin);
    },
    updateHtml: function (html) {
      editorState.html = html;
      updateAutoSaveIndicator();
    },
  };

  // Component save bridge
  window.coursewareAPI = {
    saveAsComponent: function () {
      var el = window.selection.getSelected();
      if (!el) return alert('请先选中要保存为组件的元素');
      sendState();
      window.parent.postMessage({
        type: 'editor:saveAsComponent',
        payload: {
          name: prompt('组件名称：', (el.getAttribute('data-component') || el.className || '自定义组件').replace(/-/g, ' ')),
          html_snippet: el.outerHTML,
          tag: (el.tagName || '').toLowerCase(),
          teaching_stage: el.closest('[data-teaching-stage]') ? el.closest('[data-teaching-stage]').getAttribute('data-teaching-stage') : null,
        }
      }, window.location.origin);
    },
    requestComponentSave: function () {
      var el = window.selection.getSelected();
      if (!el) return;
      sendState();
      window.parent.postMessage({
        type: 'editor:saveAsComponent',
        payload: {
          html_snippet: el.outerHTML,
          tag: (el.tagName || '').toLowerCase(),
        }
      }, window.location.origin);
    }
  };

  // Wire up toolbar buttons
  function wireButtons() {
    var saveBtn = document.getElementById('saveBtn');
    var exportBtn = document.getElementById('exportBtn');
    var exportDownload = document.getElementById('exportDownload');
    var exportCopy = document.getElementById('exportCopy');
    var previewBtn = document.getElementById('previewBtn');
    var undoBtn = document.getElementById('undoBtn');
    var redoBtn = document.getElementById('redoBtn');
    var startEditBtn = document.getElementById('startEditBtn');

    // Import page: start editing
    if (startEditBtn) {
      startEditBtn.addEventListener('click', function () {
        var textarea = document.getElementById('importTextarea');
        if (textarea && textarea.value.trim()) {
          editorState.html = textarea.value.trim();
          window.iframeManager.setHTML(editorState.html);
        }
        document.getElementById('importPage').style.display = 'none';
        document.querySelector('.workspace').style.display = 'flex';
      });
    }

    // Save
    if (saveBtn) saveBtn.addEventListener('click', function () { window.editorAPI.requestSave(); });
    if (exportBtn) exportBtn.addEventListener('click', function () {
      var menu = document.getElementById('exportMenu');
      if (menu) menu.style.display = menu.style.display === 'none' ? 'block' : 'none';
    });
    if (exportDownload) exportDownload.addEventListener('click', function () { window.exporter.download((editorState.title || 'courseware') + '.html'); });
    if (exportCopy) exportCopy.addEventListener('click', function () { window.exporter.copyToClipboard(); });

    // Preview
    if (previewBtn) previewBtn.addEventListener('click', function () {
      var iframe = document.getElementById('editor-iframe');
      if (iframe && iframe.requestFullscreen) { iframe.requestFullscreen(); }
    });

    // Undo/Redo
    if (undoBtn) undoBtn.addEventListener('click', function () {
      var prevState = window.undoRedo.undo();
      if (prevState && prevState.html) window.iframeManager.setHTML(prevState.html);
      updateUndoRedoButtons();
    });
    if (redoBtn) redoBtn.addEventListener('click', function () {
      var nextState = window.undoRedo.redo();
      if (nextState && nextState.html) window.iframeManager.setHTML(nextState.html);
      updateUndoRedoButtons();
    });

    // Breakpoint buttons
    document.querySelectorAll('.bp-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        document.querySelectorAll('.bp-btn').forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        var bp = btn.getAttribute('data-bp');
        var wrapper = document.getElementById('iframeWrapper');
        if (wrapper) {
          var widths = { desktop: '100%', tablet: '768px', mobile: '375px' };
          wrapper.style.maxWidth = widths[bp] || '100%';
        }
      });
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); window.editorAPI.requestSave(); }
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) { e.preventDefault(); undoBtn && undoBtn.click(); }
      if ((e.ctrlKey || e.metaKey) && e.key === 'z' && e.shiftKey) { e.preventDefault(); redoBtn && redoBtn.click(); }
    });
  }

  function updateUndoRedoButtons() {
    var undoBtn = document.getElementById('undoBtn');
    var redoBtn = document.getElementById('redoBtn');
    if (undoBtn) undoBtn.classList.toggle('disabled', !window.undoRedo.canUndo());
    if (redoBtn) redoBtn.classList.toggle('disabled', !window.undoRedo.canRedo());
  }

  // Auto-save (push state snapshot periodically)
  function startAutoSave() {
    if (editorState.autoSaveTimer) clearInterval(editorState.autoSaveTimer);
    editorState.autoSaveTimer = setInterval(function () {
      var html = window.iframeManager ? window.iframeManager.getHTML() : '';
      if (html && html !== editorState.html) {
        window.undoRedo.push({ html: html });
        editorState.html = html;
        updateAutoSaveIndicator();
      }
    }, 30000); // every 30s
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { init(); wireButtons(); startAutoSave(); });
  } else {
    init(); wireButtons(); startAutoSave();
  }
})();
