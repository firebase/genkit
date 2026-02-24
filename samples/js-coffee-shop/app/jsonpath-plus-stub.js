export class JSONPath {
  static cache = {};
  static toPathArray(expr) {
    if (typeof expr !== 'string') return expr;
    if (this.cache[expr]) return this.cache[expr].concat();
    const parts = ['$'];
    let s = expr.replace(/^\$\.?/, '');
    const re = /^\.([^.[]+)|^\[(\d+)\]|^\['([^']*)'\]|^\["([^"]*)"\]/;
    while (s.length) {
      const m = s.match(re);
      if (m) {
        parts.push(m[1] ?? m[2] ?? m[3] ?? m[4]);
        s = s.slice(m[0].length);
      } else break;
    }
    this.cache[expr] = parts;
    return this.cache[expr].concat();
  }
}