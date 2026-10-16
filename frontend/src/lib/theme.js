import { useCallback, useSyncExternalStore } from 'react'

// Tema claro por defecto; el oscuro se guarda en localStorage y se aplica como clase `dark`
// en <html> (index.html lo aplica antes de pintar para evitar el destello).
const CLAVE = 'tema'
const oyentes = new Set()

const leer = () => document.documentElement.classList.contains('dark') ? 'dark' : 'light'

export function aplicarTema(tema) {
  document.documentElement.classList.toggle('dark', tema === 'dark')
  try { localStorage.setItem(CLAVE, tema) } catch { /* almacenamiento bloqueado: el tema vale solo en esta sesión */ }
  oyentes.forEach(fn => fn())
}

const suscribir = (fn) => { oyentes.add(fn); return () => oyentes.delete(fn) }

export function useTema() {
  const tema = useSyncExternalStore(suscribir, leer, () => 'light')
  const alternar = useCallback(() => aplicarTema(leer() === 'dark' ? 'light' : 'dark'), [])
  return { tema, alternar }
}
