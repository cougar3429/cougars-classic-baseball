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
  /* a ground ball off the bat at this angle (0 = up the middle, + = toward third) and exit speed, set up exactly as contact does */
  hit(ang, ev) { const S = this.C.S, rad = ang * Math.PI / 180;
    S.runners.forEach(r => { r.lead = false; r.go = false; r.to = null; r.p = 0; });
    S.bb = { bunt: false, x: 0, y: 1, ux: -Math.sin(rad), uy: Math.cos(rad), v: ev, ev, dist: 0, h: 0, hPeak: 0, foul: false, wall: false, t: 0, gone: false };
    S.phase = 'batted'; this.I.resetPlay(true); S.F.C.mv = 0; S.ctl = 'P'; S.live = { kind: 'hit', still: 0 }; S.abOver = true; S.batterGone = true; this.I.batterToFirst(false); },
  toast() { return document.getElementById('tt').textContent + ' / ' + (document.getElementById('ts').hidden ? '' : document.getElementById('ts').textContent); },
  watch(n) { const out = []; let last = ''; for (let i = 0; i < n; i++) { this.C.tick(); const t = this.toast(), on = document.getElementById('toast').classList.contains('on'); if (on && t !== last) { last = t; out.push(this.C.S.t + ' ' + t + ' [' + this.rs() + ']'); } if (this.C.S.phase === 'ready') break; } return out; }
};
