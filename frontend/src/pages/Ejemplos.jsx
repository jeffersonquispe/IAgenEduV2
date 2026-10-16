import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BookOpen, Clock, Eye, Loader2, Wand2 } from 'lucide-react'
import Sidebar from '../components/Sidebar'
import { api } from '../lib/api'
import { CONTENT_FIELDS, SECTION_LABELS, EditableSection } from './Editor'

const NOMBRE_TIPO = { unidad: 'Unidad Didáctica', sesion: 'Sesión de Aprendizaje' }
const noEditar = () => {}

// HU-44: biblioteca de ejemplos completos de Unidad y Sesión, para entender qué se espera de
// cada sección. Usa el visor del Editor en modo solo lectura. Es solo lectura de verdad: no llama
// a la IA, no crea documentos y no suma puntos ni estadísticas.
export default function Ejemplos() {
  const navigate = useNavigate()
  const [lista, setLista] = useState([])
  const [seleccionado, setSeleccionado] = useState(null)   // ejemplo completo
  const [cargandoLista, setCargandoLista] = useState(true)
  const [cargandoEjemplo, setCargandoEjemplo] = useState(false)
  const [error, setError] = useState('')

  const abrir = async (id) => {
    setCargandoEjemplo(true)
    setError('')
    try {
      setSeleccionado((await api.get(`/data/ejemplos/${id}`)).data)
    } catch (err) {
      setError(err.response?.data?.detail || 'No se pudo cargar el ejemplo.')
    } finally {
      setCargandoEjemplo(false)
    }
  }

  useEffect(() => {
    api.get('/data/ejemplos')
      .then(res => {
        setLista(res.data)
        if (res.data.length) abrir(res.data[0].id)
      })
      .catch(() => setError('No se pudieron cargar los ejemplos.'))
      .finally(() => setCargandoLista(false))
  }, [])

  // Solo las secciones que el Editor sabe mostrar, en el orden en que vienen en el ejemplo.
  const secciones = seleccionado
    ? Object.entries(seleccionado.content).filter(([clave, valor]) => CONTENT_FIELDS.includes(clave) && String(valor).trim())
    : []

  return (
    <div className="flex flex-col lg:flex-row h-screen bg-bg">
      <Sidebar />

      <main className="flex-1 min-h-0 overflow-y-auto p-5 sm:p-8 lg:p-10 bg-surface/20">
        <div className="max-w-4xl mx-auto">
          <header className="mb-8">
            <h1 className="text-3xl font-bold flex items-center gap-3"><BookOpen className="text-accent-text" /> Ejemplos</h1>
            <p className="text-fg-muted mt-2">
              Documentos completos de referencia para ver qué se espera de cada sección antes de generar el tuyo.
              Verlos no consume generaciones ni suma puntos.
            </p>
          </header>

          {cargandoLista ? (
            <div className="flex justify-center p-12"><Loader2 className="animate-spin text-accent-text" /></div>
          ) : lista.length === 0 ? (
            <p className="text-fg-subtle">{error || 'Todavía no hay ejemplos disponibles.'}</p>
          ) : (
            <>
              <div className="flex flex-wrap gap-3 mb-8" role="tablist" aria-label="Ejemplos disponibles">
                {lista.map(e => {
                  const activo = seleccionado?.id === e.id
                  return (
                    <button
                      key={e.id}
                      role="tab"
                      aria-selected={activo}
                      onClick={() => abrir(e.id)}
                      className={`text-left p-4 rounded-2xl border transition-all max-w-sm ${
                        activo ? 'border-accent/60 bg-accent/10' : 'border-line bg-surface-2/40 hover:bg-surface-2/70'
                      }`}
                    >
                      <span className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-accent-text mb-1">
                        {e.tipo === 'unidad' ? <BookOpen size={14} /> : <Clock size={14} />} {NOMBRE_TIPO[e.tipo] || e.tipo}
                      </span>
                      <span className="block font-bold text-sm">{e.titulo}</span>
                      {e.descripcion && <span className="block text-xs text-fg-muted mt-1">{e.descripcion}</span>}
                    </button>
                  )
                })}
              </div>

              {error && <p role="alert" className="text-danger-text text-sm mb-4">{error}</p>}

              {cargandoEjemplo ? (
                <div className="flex justify-center p-12"><Loader2 className="animate-spin text-accent-text" /></div>
              ) : seleccionado && (
                <article className="glass rounded-[2rem] overflow-hidden shadow-2xl">
                  <div className="bg-accent/10 p-8 border-b border-line flex justify-between items-start gap-4">
                    <h2 className="text-xl font-bold gradient-text">{seleccionado.titulo}</h2>
                    <span className="shrink-0 flex items-center gap-1.5 bg-success/15 text-success-text px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider">
                      <Eye size={14} /> Ejemplo · solo lectura
                    </span>
                  </div>

                  <div className="p-8 space-y-12">
                    {secciones.map(([clave, valor]) => (
                      <EditableSection
                        key={clave}
                        label={SECTION_LABELS[clave] || clave.replace(/_/g, ' ').toUpperCase()}
                        value={valor}
                        isSecuenciaSesiones={clave === 'secuencia_de_sesiones'}
                        isRefining={false}
                        disabled
                        onChange={noEditar}
                        onRefine={noEditar}
                      />
                    ))}
                  </div>

                  {seleccionado.fuente && (
                    <p className="px-8 pb-6 text-xs text-fg-subtle italic">{seleccionado.fuente}</p>
                  )}
                </article>
              )}

              <div className="mt-8 flex justify-end">
                <button
                  onClick={() => navigate('/')}
                  className="flex items-center gap-2 bg-accent hover:bg-accent-hover text-white px-6 py-2.5 rounded-xl font-bold transition-all"
                >
                  <Wand2 size={18} /> Crear el mío
                </button>
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  )
}
