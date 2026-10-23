/* A stand-in for supabase-js Realtime, for tests: two copies of the game in one browser talk through BroadcastChannel.
   Implements what the game uses: createClient().channel(name, { config: { presence: { key } } }), .on('broadcast'|'presence', ...),
   .subscribe(cb), .send({ type: 'broadcast', event, payload }), .track(meta), .presenceState(), removeChannel(ch).
   window.__mockLag (ms) delays every delivery, to stand in for a real network. */
(function () {
  function Chan(name, opts) {
    this.name = name; this.key = (opts && opts.config && opts.config.presence && opts.config.presence.key) || Math.random().toString(36).slice(2);
    this.h = []; this.state = {}; this.me = null; this.open = false;
    var self = this; this.bc = new BroadcastChannel('mock:' + name);
    this.bc.onmessage = function (e) { var m = e.data, lag = window.__mockLag || 0; if (lag) setTimeout(function () { self._in(m); }, lag * (0.5 + Math.random())); else self._in(m); };
  }
  Chan.prototype.on = function (type, filter, cb) { this.h.push({ type: type, ev: filter && filter.event, cb: cb }); return this; };
  Chan.prototype._fire = function (type, ev, arg) { this.h.forEach(function (x) { if (x.type === type && (x.ev === ev || x.ev === '*')) x.cb(arg); }); };
  Chan.prototype._in = function (m) {
    if (!this.open || m.from === this.key) return;
    if (m.kind === 'b') this._fire('broadcast', m.event, { event: m.event, payload: m.payload });
    else if (m.kind === 'track') { this.state[m.from] = [m.meta]; this._fire('presence', 'sync'); }
    else if (m.kind === 'hello') { if (this.me) this.bc.postMessage({ kind: 'track', from: this.key, meta: this.me }); }
    else if (m.kind === 'leave') { if (this.state[m.from]) { delete this.state[m.from]; this._fire('presence', 'leave', { key: m.from }); this._fire('presence', 'sync'); } }
  };
  Chan.prototype.subscribe = function (cb) { var self = this; this.open = true; setTimeout(function () { self.bc.postMessage({ kind: 'hello', from: self.key }); if (cb) cb('SUBSCRIBED'); }, 20); return this; };
  Chan.prototype.send = function (m) { if (this.open) this.bc.postMessage({ kind: 'b', from: this.key, event: m.event, payload: m.payload }); return Promise.resolve('ok'); };
  Chan.prototype.track = function (meta) { this.me = meta; this.state[this.key] = [meta]; this.bc.postMessage({ kind: 'track', from: this.key, meta: meta }); this._fire('presence', 'sync'); return Promise.resolve('ok'); };
  Chan.prototype.presenceState = function () { return this.state; };
  Chan.prototype.unsubscribe = function () { if (!this.open) return; this.bc.postMessage({ kind: 'leave', from: this.key }); this.open = false; var bc = this.bc; setTimeout(function () { bc.close(); }, 50); };
  window.supabase = { createClient: function () { return { channel: function (n, o) { return new Chan(n, o); }, removeChannel: function (c) { c.unsubscribe(); } }; } };
})();
