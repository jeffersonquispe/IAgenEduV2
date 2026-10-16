import { useSyncExternalStore } from 'react'

// Avisos (toast) y confirmaciones propias, en lugar de alert()/confirm() del navegador.
// Son un almacén de módulo, sin Provider: se pueden llamar desde cualquier handler. Si no hay un
// <Toaster /> montado (p. ej. en las pruebas de render), degradan a window.alert/confirm.
let toasts = []
let confirmacion = null          // { titulo, mensaje, detalle, confirmar, cancelar, peligro, resolver }
let hosts = 0
let siguienteId = 1
const oyentes = new Set()
const emitir = () => oyentes.forEach(fn => fn())
const suscribir = (fn) => { oyentes.add(fn); return () => oyentes.delete(fn) }

export function registrarHost() {
  hosts++
  return () => { hosts-- }
}

function agregar(tipo, mensaje) {
  if (hosts === 0) {
    if (tipo !== 'success') window.alert(mensaje)
    return
  }
  const id = siguienteId++
  toasts = [...toasts, { id, tipo, mensaje }]
  emitir()
  setTimeout(() => quitar(id), tipo === 'error' ? 10000 : 5000)
}

export function quitar(id) {
  toasts = toasts.filter(t => t.id !== id)
  emitir()
}

export const toast = {
  error: (mensaje) => agregar('error', mensaje),
  success: (mensaje) => agregar('success', mensaje),
  info: (mensaje) => agregar('info', mensaje),
}

// Devuelve una promesa con true/false. `detalle` es una lista opcional de viñetas.
export function confirmar({ titulo, mensaje, detalle = [], confirmar = 'Aceptar', cancelar = 'Cancelar', peligro = false }) {
  if (hosts === 0) {
    const lista = detalle.length ? '\n\n' + detalle.map(d => `• ${d}`).join('\n') : ''
    return Promise.resolve(window.confirm(`${titulo}\n\n${mensaje}${lista}`))
  }
  return new Promise(resolver => {
    // Si ya había una abierta, se descarta como "cancelada".
    confirmacion?.resolver(false)
    confirmacion = { titulo, mensaje, detalle, confirmar, cancelar, peligro, resolver }
    emitir()
  })
}

export function responderConfirmacion(valor) {
  const actual = confirmacion
  confirmacion = null
  emitir()
  actual?.resolver(valor)
}

export const useToasts = () => useSyncExternalStore(suscribir, () => toasts, () => toasts)
export const useConfirmacion = () => useSyncExternalStore(suscribir, () => confirmacion, () => confirmacion)

// Texto legible de un error de axios/fetch.
export function mensajeDeError(err, porDefecto = 'Ocurrió un error inesperado.') {
  const detalle = err?.response?.data?.detail
  if (typeof detalle === 'string') return detalle
  if (detalle?.message) return detalle.message
  return err?.message || porDefecto
}
