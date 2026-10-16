import { useEffect } from 'react'
import { CheckCircle2, AlertTriangle, Info, X } from 'lucide-react'
import { registrarHost, quitar, useToasts, useConfirmacion, responderConfirmacion } from '../../lib/notify'
import Modal from './Modal'
import Button from './Button'

const ESTILOS = {
  error: { caja: 'border-danger/40 text-danger-text', icono: AlertTriangle, rol: 'alert' },
  success: { caja: 'border-success/40 text-success-text', icono: CheckCircle2, rol: 'status' },
  info: { caja: 'border-accent/40 text-accent-text', icono: Info, rol: 'status' },
}

// Se monta una sola vez (App.jsx): avisos en la esquina y el diálogo de confirmación.
export default function Toaster() {
  useEffect(() => registrarHost(), [])
  const toasts = useToasts()
  const confirmacion = useConfirmacion()

  return (
    <>
      <div className="fixed bottom-4 right-4 z-[60] flex flex-col gap-3 w-[min(24rem,calc(100vw-2rem))]">
        {toasts.map(t => {
          const { caja, icono: Icono, rol } = ESTILOS[t.tipo]
          return (
            <div key={t.id} role={rol} className={`flex items-start gap-3 rounded-2xl border p-4 text-sm shadow-lg bg-surface ${caja}`}>
              <Icono size={18} className="shrink-0 mt-0.5" />
              <p className="flex-1 break-words">{t.mensaje}</p>
              <button onClick={() => quitar(t.id)} aria-label="Cerrar aviso" className="shrink-0 opacity-70 hover:opacity-100">
                <X size={16} />
              </button>
            </div>
          )
        })}
      </div>

      {confirmacion && (
        <Modal titulo={confirmacion.titulo} className="max-w-md" onClose={() => responderConfirmacion(false)}>
          <div className="p-6 space-y-4">
            <h3 className="text-lg font-bold">{confirmacion.titulo}</h3>
            <p className="text-sm text-fg-muted whitespace-pre-line">{confirmacion.mensaje}</p>
            {confirmacion.detalle.length > 0 && (
              <ul className="list-disc pl-5 space-y-1 text-sm text-fg-muted max-h-48 overflow-y-auto">
                {confirmacion.detalle.map((d, i) => <li key={i}>{d}</li>)}
              </ul>
            )}
            <div className="flex justify-end gap-3 pt-2">
              <Button variant="secondary" onClick={() => responderConfirmacion(false)}>{confirmacion.cancelar}</Button>
              <Button variant={confirmacion.peligro ? 'danger' : 'primary'} onClick={() => responderConfirmacion(true)}>
                {confirmacion.confirmar}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </>
  )
}
