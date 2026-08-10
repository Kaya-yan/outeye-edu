window.EventBus = class EventBus {
  constructor() { this._listeners = {}; }
  on(event, fn) { (this._listeners[event] = this._listeners[event] || []).push(fn); return () => this.off(event, fn); }
  off(event, fn) { const list = this._listeners[event]; if (list) this._listeners[event] = list.filter(f => f !== fn); }
  emit(event, ...args) { (this._listeners[event] || []).forEach(fn => fn(...args)); }
};
window.events = new window.EventBus();
