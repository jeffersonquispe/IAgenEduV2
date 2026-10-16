import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import GenerationWizard from '__COMPONENTE__'

globalThis.IS_REACT_ACT_ENVIRONMENT = true

const errores = []
const consolaOriginal = console.error
console.error = (...args) => { errores.push(args.map(a => (a && a.message) || String(a)).join(' ').slice(0, 300)) }

const contenedor = document.createElement('div')
document.body.appendChild(contenedor)
const raiz = createRoot(contenedor)
const props = { type: 'unidad', onClose() {}, onComplete() {} }
const pasos = []

async function paso(nombre, abierto, type) {
  try {
    await act(async () => { raiz.render(<GenerationWizard {...props} type={type} isOpen={abierto} />) })
    const texto = document.body.textContent
    const visible = texto.includes('Generador de')
    pasos.push({ nombre, ok: abierto ? visible : !visible, detalle: abierto ? (visible ? 'se muestra' : 'NO se muestra') : (visible ? 'sigue visible' : 'oculto') })
  } catch (e) {
    pasos.push({ nombre, ok: false, detalle: 'EXCEPCIÓN: ' + String(e.message).split('\n')[0].slice(0, 160) })
  }
}

async function principal() {
  await paso('1. cerrado', false, 'unidad')
  await paso('2. se abre (Unidad)', true, 'unidad')
  await paso('3. se cierra', false, 'unidad')
  await paso('4. se abre (Sesión)', true, 'sesion')
  await paso('5. se cierra otra vez', false, 'sesion')
  await paso('6. se abre otra vez', true, 'unidad')


console.error = consolaOriginal
for (const p of pasos) console.log((p.ok ? 'OK    ' : 'FALLA ') + p.nombre + ' -> ' + p.detalle)
const graves = errores.filter(e => /hooks|Rendered|Cannot read|is not defined|is not a function/i.test(e))
if (graves.length) console.log('Errores de React:', graves.slice(0, 3))
console.log(pasos.every(p => p.ok) && !graves.length ? 'RESULTADO: el wizard abre y cierra sin errores' : 'RESULTADO: HAY ERRORES')
process.exit(pasos.every(p => p.ok) && !graves.length ? 0 : 1)
}
principal()
