window.T = {
  C: window.__ccb, I: window.__ccbi,
  start(batFirst) { this.C.newGame({innings: 3, batFirst}); this.C.S.paused = true; this.until(() => this.C.S.phase === 'ready', 400); },
  until(f, n) { for (let i = 0; i < n; i++) { if (f()) return i; this.C.tick(); } return -1; },
  run(n) { for (let i = 0; i < n; i++) this.C.tick(); },
  press(dir) { const h = this.C.human; h.dir = dir || null; h.vx = dir === 'l' ? -1 : dir === 'r' ? 1 : 0; h.vy = dir === 'u' ? 1 : dir === 'd' ? -1 : 0; h.btn = true; this.C.tick(); this.release(); },
  hold(dir) { const h = this.C.human; h.dir = dir; h.vx = dir === 'l' ? -1 : dir === 'r' ? 1 : 0; h.vy = dir === 'u' ? 1 : dir === 'd' ? -1 : 0; },
  release() { const h = this.C.human; h.dir = null; h.vx = 0; h.vy = 0; h.btn = false; },
  put(bases) { const S = this.C.S; S.runners = []; bases.forEach(b => this.C.newRunner(b)); },
  rs() { return this.C.S.runners.filter(r => !r.out && !r.scored).map(r => r.to == null ? '' + r.at : r.at + '>' + r.to + '@' + r.p.toFixed(2)).join(','); },
  toast() { return document.getElementById('tt').textContent + ' / ' + (document.getElementById('ts').hidden ? '' : document.getElementById('ts').textContent); },
  watch(n) { const out = []; let last = ''; for (let i = 0; i < n; i++) { this.C.tick(); const t = this.toast(), on = document.getElementById('toast').classList.contains('on'); if (on && t !== last) { last = t; out.push(this.C.S.t + ' ' + t + ' [' + this.rs() + ']'); } if (this.C.S.phase === 'ready') break; } return out; }
};
