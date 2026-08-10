window.undoRedo = {
  _stack: [], _index: -1,
  push(state) { this._stack = this._stack.slice(0, this._index + 1); this._stack.push(JSON.stringify(state)); this._index++; if (this._stack.length > 50) { this._stack.shift(); this._index--; } },
  undo() { if (this._index > 0) { this._index--; return JSON.parse(this._stack[this._index]); } return null; },
  redo() { if (this._index < this._stack.length - 1) { this._index++; return JSON.parse(this._stack[this._index]); } return null; },
  canUndo() { return this._index > 0; },
  canRedo() { return this._index < this._stack.length - 1; },
  clear() { this._stack = []; this._index = -1; }
};
