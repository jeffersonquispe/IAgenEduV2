import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { MoreVertical } from 'lucide-react'

// Menú de acciones (botón "⋮"): se cierra con Esc o clic fuera, navegable con flechas.
// items: [{ etiqueta, icono, onClick, peligro, separador }]
export default function Menu({ etiqueta, items, deshabilitado = false }) {
  const [abierto, setAbierto] = useState(false)
  const caja = useRef(null)
  const boton = useRef(null)
  const lista = useRef(null)
  const [arriba, setArriba] = useState(false)   // no cabe debajo del botón: se abre hacia arriba

  useLayoutEffect(() => {
    if (!abierto) { setArriba(false); return }
    const r = lista.current?.getBoundingClientRect()
    if (r && r.bottom > window.innerHeight - 8) setArriba(true)
  }, [abierto])

  useEffect(() => {
    if (!abierto) return
    const fuera = (e) => { if (caja.current && !caja.current.contains(e.target)) setAbierto(false) }
    const tecla = (e) => {
      if (e.key === 'Escape') { setAbierto(false); boton.current?.focus(); return }
      if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return
      const opciones = [...caja.current.querySelectorAll('[role="menuitem"]')]
      if (!opciones.length) return
      e.preventDefault()
      const i = opciones.indexOf(document.activeElement)
      const sig = e.key === 'ArrowDown' ? (i + 1) % opciones.length : (i <= 0 ? opciones.length - 1 : i - 1)
      opciones[sig].focus()
    }
    document.addEventListener('mousedown', fuera)
    document.addEventListener('keydown', tecla)
    caja.current?.querySelector('[role="menuitem"]')?.focus()
    return () => { document.removeEventListener('mousedown', fuera); document.removeEventListener('keydown', tecla) }
  }, [abierto])

  return (
    <div ref={caja} className="relative shrink-0">
      <button ref={boton} type="button" onClick={() => setAbierto(a => !a)} disabled={deshabilitado}
        aria-label={etiqueta} aria-haspopup="menu" aria-expanded={abierto}
        className="p-2 rounded-lg text-fg-muted hover:text-fg hover:bg-surface-2 disabled:opacity-50 transition-colors">
        <MoreVertical size={18} aria-hidden="true" />
      </button>
      {abierto && (
        <div ref={lista} role="menu" aria-label={etiqueta}
          className={`absolute right-0 ${arriba ? 'bottom-full mb-1' : 'top-full mt-1'} w-52 rounded-xl border border-line bg-surface shadow-lg p-1 z-30`}>
          {items.map((it, i) => (
            <div key={i}>
              {it.separador && <div role="separator" className="my-1 border-t border-line" />}
              <button role="menuitem" type="button" tabIndex={-1}
                onClick={() => { setAbierto(false); it.onClick() }}
                className={`w-full text-left flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-semibold hover:bg-surface-2 focus:bg-surface-2 focus:outline-none ${
                  it.peligro ? 'text-danger-text' : ''}`}>
                {it.icono}
                {it.etiqueta}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
