// Empaqueta entry_paginas.jsx. API y Supabase se sustituyen por un doble programable (globalThis.__api).
const path = require('path')
const fs = require('fs')
const FRONTEND = path.resolve(__dirname, '..', '..')
const CACHE = path.join(FRONTEND, 'node_modules', '.cache', 'render')
fs.mkdirSync(CACHE, { recursive: true })
const esbuild = require(path.join(FRONTEND, 'node_modules', 'esbuild'))
const salida = process.argv[2]

const stubs = {
  api: `const llamar = (m) => (url, arg) => globalThis.__api(m, String(url), arg)
        export const api = { get: llamar('get'), post: llamar('post'), put: llamar('put'), delete: llamar('delete') }`,
  supabase: `export const supabase = { auth: {
      getSession: async () => ({ data: { session: { user: { email: 'docente@x.com' }, access_token: 't' } } }),
      signOut: async () => ({}), signInWithPassword: async () => ({ error: null }),
      signUp: async () => ({ data: { session: null }, error: null }),
      resend: async () => ({ error: null }), resetPasswordForEmail: async () => ({ error: null }),
      onAuthStateChange: () => ({ data: { subscription: { unsubscribe() {} } } }) } }`,
}
const plugin = {
  name: 'dobles',
  setup(build) {
    // Prueba de control: con WIZARD_ROTO se usa la copia con el hook después del return anticipado.
    if (process.env.WIZARD_ROTO) {
      build.onResolve({ filter: /components\/GenerationWizard$/ }, () => ({ path: process.env.WIZARD_ROTO }))
    }
    build.onResolve({ filter: /(lib\/api|lib\/supabaseClient|\.\/supabaseClient|\.\/api)$/ }, a => ({ path: a.path, namespace: 'stub' }))
    build.onLoad({ filter: /.*/, namespace: 'stub' }, a => ({
      contents: a.path.endsWith('api') ? stubs.api : stubs.supabase, loader: 'js' }))
  },
}
const entrada = fs.readFileSync(path.join(__dirname, 'entry_paginas.jsx'), 'utf8')
  .replace(/__SRC__/g, (FRONTEND + '/src').replace(/\\/g, '/'))
fs.writeFileSync(path.join(CACHE, 'entry_paginas.generado.jsx'), entrada)

esbuild.build({
  entryPoints: [path.join(CACHE, 'entry_paginas.generado.jsx')],
  outfile: salida, bundle: true, platform: 'node', format: 'cjs', jsx: 'automatic',
  loader: { '.jsx': 'jsx' }, nodePaths: [path.join(FRONTEND, 'node_modules')],
  plugins: [plugin], logLevel: 'error', define: { 'process.env.NODE_ENV': '"development"' },
}).catch(() => process.exit(1))
