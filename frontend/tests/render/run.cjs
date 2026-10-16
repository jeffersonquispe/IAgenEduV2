// Prepara el DOM (jsdom) y ejecuta el paquete. Uso: node run.cjs <paquete.cjs>
const { JSDOM } = require('jsdom')
const dom = new JSDOM('<!doctype html><html><body></body></html>', { url: 'http://localhost/' })
global.window = dom.window
global.document = dom.window.document
Object.defineProperty(global, 'navigator', { value: dom.window.navigator, configurable: true })
for (const k of ['HTMLElement', 'Node', 'Element', 'MutationObserver', 'getComputedStyle', 'requestAnimationFrame', 'cancelAnimationFrame']) {
  if (dom.window[k] && !global[k]) global[k] = dom.window[k]
}
require(require('path').resolve(process.argv[2]))
