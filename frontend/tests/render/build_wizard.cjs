// Empaqueta entry.jsx con el esbuild del proyecto. Uso: node build.cjs <ruta-al-componente> <salida>
const path = require('path')
const fs = require('fs')
const FRONTEND = path.resolve(__dirname, '..', '..')
const CACHE = path.join(FRONTEND, 'node_modules', '.cache', 'render')
fs.mkdirSync(CACHE, { recursive: true })
const esbuild = require(path.join(FRONTEND, 'node_modules', 'esbuild'))
const [componente, salida] = process.argv.slice(2)

// El componente real, con la API y Supabase sustituidas (no hay red ni sesión en esta prueba).
const sustitutos = {
  // Respuestas con la misma forma que las del backend real.
  api: `export const api = {
    get: async (url) => {
      if (String(url).startsWith('/data/options'))
        return { data: { areas: ['Matemática', 'Comunicación'], grados: ['1°', '2°', '3°'], competencias: [], temas_por_area: {} } }
      if (String(url).startsWith('/data/temas')) return { data: { temas: [] } }
      return { data: [] }          // /data/competencias, /data/unidades
    },
    post: async () => ({ data: {} }), put: async () => ({ data: {} }), delete: async () => ({ data: {} }) }`,
  supabase: `export const supabase = { auth: { getSession: async () => ({ data: { session: null } }) } }`,
}
const plugin = {
  name: 'sustituir-modulos',
  setup(build) {
    build.onResolve({ filter: /lib\/(api|supabaseClient)$/ }, a => ({ path: a.path, namespace: 'stub' }))
    build.onLoad({ filter: /.*/, namespace: 'stub' }, a => ({
      contents: a.path.endsWith('api') ? sustitutos.api : sustitutos.supabase, loader: 'js' }))
  },
}

const entrada = fs.readFileSync(path.join(__dirname, 'entry_wizard.jsx'), 'utf8')
  .replace('__COMPONENTE__', componente.replace(/\\/g, '/'))
fs.writeFileSync(path.join(CACHE, 'entry_wizard.generado.jsx'), entrada)

esbuild.build({
  entryPoints: [path.join(CACHE, 'entry_wizard.generado.jsx')],
  outfile: salida, bundle: true, platform: 'node', format: 'cjs', jsx: 'automatic',
  loader: { '.jsx': 'jsx' }, nodePaths: [path.join(FRONTEND, 'node_modules')],
  plugins: [plugin], logLevel: 'error', define: { 'process.env.NODE_ENV': '"development"' },
}).catch(() => process.exit(1))
