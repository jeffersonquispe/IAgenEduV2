import { useEffect, useRef } from 'react'

const FOCALIZABLES = 'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])'

// Diálogo accesible: role="dialog", Esc para cerrar, foco atrapado dentro y devuelto al cerrar.
export default function Modal({ titulo, onClose, children, className = 'max-w-2xl', cerrarConClicFuera = true }) {
  const caja = useRef(null)
  const alCerrar = useRef(onClose)
  alCerrar.current = onClose

  useEffect(() => {
    const previo = document.activeElement
    const enfocables = () => [...(caja.current?.querySelectorAll(FOCALIZABLES) ?? [])]
    ;(enfocables()[0] ?? caja.current)?.focus()

    const alPulsar = (e) => {
      if (e.key === 'Escape') { e.stopPropagation(); alCerrar.current?.(); return }
      if (e.key !== 'Tab') return
      const lista = enfocables()
      if (lista.length === 0) { e.preventDefault(); return }
      const primero = lista[0], ultimo = lista[lista.length - 1]
      if (e.shiftKey && document.activeElement === primero) { e.preventDefault(); ultimo.focus() }
      else if (!e.shiftKey && document.activeElement === ultimo) { e.preventDefault(); primero.focus() }
    }
    document.addEventListener('keydown', alPulsar)
    return () => { document.removeEventListener('keydown', alPulsar); previo?.focus?.() }
  }, [])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60"
      onMouseDown={(e) => { if (cerrarConClicFuera && e.target === e.currentTarget) onClose?.() }}>
      <div ref={caja} role="dialog" aria-modal="true" aria-label={titulo} tabIndex={-1}
        className={`w-full ${className} bg-surface border border-line rounded-3xl shadow-2xl relative overflow-hidden`}>
        {children}
      </div>
    </div>
  )
}
