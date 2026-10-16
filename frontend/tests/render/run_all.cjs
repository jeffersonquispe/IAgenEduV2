// Pruebas de renderizado (jsdom): empaqueta las pantallas con esbuild (el de Vite), con la API y Supabase
// sustituidas por dobles, y las ejecuta. Uso: npm run test:render
const { spawnSync } = require('child_process')
const path = require('path')
const fs = require('fs')
const CACHE = path.join(__dirname, '..', '..', 'node_modules', '.cache', 'render')
fs.mkdirSync(CACHE, { recursive: true })
const componente = path.join(__dirname, '..', '..', 'src', 'components', 'GenerationWizard.jsx')

const pasos = [
  ['Wizard (abrir/cerrar)', 'build_wizard.cjs', [componente, path.join(CACHE, 'wizard.cjs')], 'wizard.cjs'],
  ['Pantallas', 'build_paginas.cjs', [path.join(CACHE, 'paginas.cjs')], 'paginas.cjs'],
]
let fallo = false
for (const [titulo, build, args, paquete] of pasos) {
  console.log(`\n=== ${titulo} ===`)
  const b = spawnSync(process.execPath, [path.join(__dirname, build), ...args], { stdio: 'inherit' })
  if (b.status !== 0) { fallo = true; console.log('No se pudo empaquetar'); continue }
  const r = spawnSync(process.execPath, [path.join(__dirname, 'run.cjs'), path.join(CACHE, paquete)], { stdio: 'inherit' })
  if (r.status !== 0) fallo = true
}
process.exit(fallo ? 1 : 0)
