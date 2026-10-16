import { useState, useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import VerificarCorreoBanner from '../components/VerificarCorreoBanner'
import GenerationWizard from '../components/GenerationWizard'
import { ArrowRight, BookOpen, Clock, FileText, Search, Loader2, AlertTriangle, Copy, Download, Trash2, ExternalLink } from 'lucide-react'
import { api } from '../lib/api'
import { toast, confirmar, mensajeDeError } from '../lib/notify'
import { exportarDocumento } from '../lib/documento'
import Menu from '../components/ui/Menu'

const PAGE_SIZE = 10
const FILTROS_VACIOS = { q: '', type: '', area: '', grado: '' }

// HU-33: estados de un job de generación que siguen en curso.
const esActivo = (j) => j.status === 'pending' || j.status === 'running'
// La API devuelve fechas UTC sin zona ("2026-10-08T12:00:00"); sin la Z el
// navegador las leería como hora local y la antigüedad saldría desplazada.
const fechaUtc = (iso) => new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + 'Z')
const HORAS_FALLOS_VISIBLES = 24

// "hace 2 días" para lo reciente; fecha completa para lo antiguo.
const fechaRelativa = (iso) => {
  const f = fechaUtc(iso)
  const seg = (f.getTime() - Date.now()) / 1000
  const abs = Math.abs(seg)
  const rtf = new Intl.RelativeTimeFormat('es', { numeric: 'auto' })
  if (abs < 60) return 'hace un momento'
  if (abs < 3600) return rtf.format(Math.round(seg / 60), 'minute')
  if (abs < 86400) return rtf.format(Math.round(seg / 3600), 'hour')
  if (abs < 86400 * 30) return rtf.format(Math.round(seg / 86400), 'day')
  return f.toLocaleDateString('es')
}

const ETIQUETA_TIPO = { unidad: 'Unidad', sesion: 'Sesión' }

export default function Dashboard({ user }) {
  const navigate = useNavigate()
  const location = useLocation()
  const [wizard, setWizard] = useState({ open: false, type: 'unidad' })
  const [recentDocs, setRecentDocs] = useState([])
  const [total, setTotal] = useState(0)
  const [loadingDocs, setLoadingDocs] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [filtros, setFiltros] = useState(FILTROS_VACIOS)
  const [qAplicada, setQAplicada] = useState('')   // `q` con espera (debounce) para no consultar por tecla
  const [opciones, setOpciones] = useState({ areas: [], grados: [] })
  const ultimaPeticion = useRef(0)                 // descarta respuestas que llegan fuera de orden
  const [jobs, setJobs] = useState([])
  const activosPrevios = useRef(new Set())         // para detectar cuándo un job activo termina
  const fetchDocsRef = useRef(null)                // última versión de fetchDocs (la usa el intervalo)

  useEffect(() => {
    const nuevo = location.state?.nuevo
    if (nuevo === 'unidad' || nuevo === 'sesion') {
      setWizard({ open: true, type: nuevo })
      navigate('.', { replace: true, state: null })
    }
  }, [location.state, navigate])

  const hayFiltros = Object.values(filtros).some(Boolean)

  const fetchDocs = async (offset = 0) => {
    const id = ++ultimaPeticion.current
    const params = { limit: PAGE_SIZE, offset }
    if (qAplicada.trim()) params.q = qAplicada.trim()
    if (filtros.type) params.type = filtros.type
    if (filtros.area) params.area_curricular = filtros.area
    if (filtros.grado) params.grado = filtros.grado
    try {
      const res = await api.get('/data/documents', { params })
      if (id !== ultimaPeticion.current) return
      setRecentDocs(prev => (offset === 0 ? res.data : [...prev, ...res.data]))
      setTotal(parseInt(res.headers['x-total-count'] ?? res.data.length, 10))
    } catch (err) {
      console.error("Error fetching docs", err)
    } finally {
      if (id === ultimaPeticion.current) {
        setLoadingDocs(false)
        setLoadingMore(false)
      }
    }
  }

  useEffect(() => {
    api.get('/data/options')
      .then(res => setOpciones({ areas: res.data.areas || [], grados: res.data.grados || [] }))
      .catch(console.error)
  }, [])

  useEffect(() => {
    const t = setTimeout(() => setQAplicada(filtros.q), 300)
    return () => clearTimeout(t)
  }, [filtros.q])

  useEffect(() => {
    setLoadingDocs(true)
    fetchDocs(0)
  }, [qAplicada, filtros.type, filtros.area, filtros.grado])

  fetchDocsRef.current = fetchDocs

  // HU-33: jobs de generación en segundo plano (siguen vivos aunque se cierre la pestaña).
  const fetchJobs = async () => {
    try {
      const res = await api.get('/generate/jobs', { params: { limit: 10 } })
      const data = res.data
      const terminaron = data.some(j => j.status === 'done' && activosPrevios.current.has(j.id))
      activosPrevios.current = new Set(data.filter(esActivo).map(j => j.id))
      setJobs(data)
      if (terminaron) fetchDocsRef.current(0)       // el documento nuevo aparece en "Recientes"
    } catch (err) {
      console.error("Error fetching jobs", err)
    }
  }

  const hayJobsActivos = jobs.some(esActivo)

  useEffect(() => { fetchJobs() }, [])

  useEffect(() => {
    if (!hayJobsActivos) return
    const t = setInterval(fetchJobs, 4000)
    return () => clearInterval(t)
  }, [hayJobsActivos])

  const jobsVisibles = jobs.filter(j =>
    esActivo(j) ||
    (j.status === 'failed' && Date.now() - fechaUtc(j.updated_at || j.created_at).getTime() < HORAS_FALLOS_VISIBLES * 3600 * 1000)
  )

  const cargarMas = () => {
    setLoadingMore(true)
    fetchDocs(recentDocs.length)
  }

  const setFiltro = (campo) => (e) => setFiltros(f => ({ ...f, [campo]: e.target.value }))

  const handleComplete = (data) => {
    navigate('/editor', { state: { content: data } })
  }

  const duplicarDoc = async (doc) => {
    try {
      await api.post(`/data/documents/${doc.id}/duplicate`)
      toast.success(`Se creó una copia de «${doc.title}».`)
      fetchDocs(0)
    } catch (err) {
      toast.error('No se pudo duplicar: ' + mensajeDeError(err))
    }
  }

  const eliminarDoc = async (doc) => {
    const seguir = await confirmar({
      titulo: 'Eliminar documento',
      mensaje: `Se eliminará «${doc.title}» junto con su historial de versiones. Esta acción no se puede deshacer.`,
      confirmar: 'Eliminar',
      peligro: true,
    })
    if (!seguir) return
    try {
      await api.delete(`/data/documents/${doc.id}`)
      setRecentDocs(docs => docs.filter(d => d.id !== doc.id))
      setTotal(t => Math.max(0, t - 1))
      toast.success('Documento eliminado.')
    } catch (err) {
      toast.error('No se pudo eliminar: ' + mensajeDeError(err))
    }
  }

  // Exporta sin abrir el Editor; con errores críticos pide confirmación igual que allí.
  const exportarDoc = (doc, formato) => {
    const val = doc.content?.validacion
    const criticos = (val?.detalle || []).filter(d => d.tipo === 'CRITICO')
    return exportarDocumento({ ...doc.content, titulo: doc.content?.titulo || doc.title }, formato, criticos)
  }

  const itemsDe = (doc) => [
    { etiqueta: 'Abrir', icono: <ExternalLink size={16} aria-hidden="true" />, onClick: () => abrirDoc(doc) },
    { etiqueta: 'Duplicar', icono: <Copy size={16} aria-hidden="true" />, onClick: () => duplicarDoc(doc) },
    { etiqueta: 'Exportar Word (.docx)', icono: <Download size={16} aria-hidden="true" />, onClick: () => exportarDoc(doc, 'docx'), separador: true },
    { etiqueta: 'Exportar PDF', icono: <Download size={16} aria-hidden="true" />, onClick: () => exportarDoc(doc, 'pdf') },
    { etiqueta: 'Eliminar', icono: <Trash2 size={16} aria-hidden="true" />, onClick: () => eliminarDoc(doc), peligro: true, separador: true },
  ]

  const abrirDoc = (doc) =>
    navigate('/editor', { state: { content: { ...doc.content, id: doc.id, version: doc.current_version } } })

  const nombre = user?.user_metadata?.full_name?.trim().split(/\s+/)[0]
  const ultimo = !hayFiltros && !loadingDocs ? recentDocs[0] : null

  return (
    <div className="flex flex-col lg:flex-row h-screen bg-bg">
      <Sidebar />

      <main className="flex-1 min-h-0 overflow-y-auto p-5 sm:p-8 lg:p-10">
        <VerificarCorreoBanner />
        <header className="mb-8">
          <h1 className="text-3xl sm:text-4xl font-bold mb-2">{nombre ? `Hola, ${nombre}` : 'Hola'}</h1>
          <p className="text-fg-muted text-lg">¿Qué quieres planificar hoy?</p>
        </header>

        {/* Generaciones en segundo plano (HU-33) */}
        {jobsVisibles.length > 0 && (
          <section className="mb-8" aria-label="Generaciones en curso">
            <h2 className="text-xl font-bold mb-3">Generaciones</h2>
            <div className="space-y-3">
              {jobsVisibles.map(j => (
                <div key={j.id}
                  className={`glass p-4 rounded-2xl flex items-center gap-4 border ${
                    j.status === 'failed' ? 'border-danger/30' : 'border-accent/30'
                  }`}>
                  {j.status === 'failed'
                    ? <AlertTriangle className="text-danger-text shrink-0" size={20} aria-hidden="true" />
                    : <Loader2 className="text-accent-text shrink-0 animate-spin" size={20} aria-hidden="true" />}
                  <div className="min-w-0">
                    <p className="font-bold text-sm">
                      {j.tipo === 'unidad' ? 'Unidad Didáctica' : 'Sesión de Aprendizaje'}
                      {' — '}
                      {j.status === 'failed' ? 'falló'
                        : j.status === 'pending' ? 'en cola'
                        : j.etapa === 'validando' ? 'validando y estructurando…' : 'generando con IA…'}
                    </p>
                    {j.status === 'failed'
                      ? <p className="text-xs text-danger-text break-words">{j.error}</p>
                      : <p className="text-xs text-fg-subtle">Puedes seguir usando la plataforma; aparecerá en Recientes cuando termine.</p>}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Continuar donde lo dejaste */}
        {ultimo && (
          <section className="mb-8" aria-label="Continuar donde lo dejaste">
            <h2 className="text-xl font-bold mb-3">Continuar donde lo dejaste</h2>
            <button type="button" onClick={() => abrirDoc(ultimo)}
              className="glass w-full text-left p-5 rounded-2xl flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4 hover:bg-surface-2 transition-colors group">
              <div className="min-w-0">
                <p className="font-bold line-clamp-2">{ultimo.title}</p>
                <MetaDocumento doc={ultimo} />
              </div>
              <span className="shrink-0 inline-flex items-center gap-2 text-accent-text font-bold group-hover:translate-x-1 transition-transform">
                Abrir <ArrowRight size={18} aria-hidden="true" />
              </span>
            </button>
          </section>
        )}

        {/* Crear */}
        <section className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-10" aria-label="Crear un documento">
          <ActionCard
            title="Unidad Didáctica"
            desc="Planificación curricular completa con competencias y secuencia de sesiones."
            icon={<BookOpen className="w-8 h-8 text-accent-text" />}
            onClick={() => setWizard({ open: true, type: 'unidad' })}
          />
          <ActionCard
            title="Sesión de Aprendizaje"
            desc="El detalle de una clase: inicio, desarrollo y cierre."
            icon={<Clock className="w-8 h-8 text-success-text" />}
            onClick={() => setWizard({ open: true, type: 'sesion' })}
          />
        </section>

        {/* Mis documentos: búsqueda y filtros (HU-24) */}
        <section>
          <h2 className="text-2xl font-bold mb-6">
            {hayFiltros ? 'Resultados' : 'Recientes'}
          </h2>

          <div className="flex flex-wrap gap-3 mb-6" role="search">
            <div className="relative flex-1 min-w-[220px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-fg-subtle" size={16} aria-hidden="true" />
              <input
                type="search"
                value={filtros.q}
                onChange={setFiltro('q')}
                maxLength={100}
                placeholder="Buscar por título…"
                aria-label="Buscar documentos por título"
                className="w-full bg-surface border border-line rounded-xl pl-9 pr-3 py-2 text-sm placeholder:text-fg-subtle focus:outline-none focus:border-accent"
              />
            </div>
            <select value={filtros.type} onChange={setFiltro('type')} aria-label="Filtrar por tipo"
              className="bg-surface border border-line rounded-xl px-3 py-2 text-sm">
              <option value="">Todos los tipos</option>
              <option value="unidad">Unidad</option>
              <option value="sesion">Sesión</option>
            </select>
            <select value={filtros.area} onChange={setFiltro('area')} aria-label="Filtrar por área curricular"
              className="bg-surface border border-line rounded-xl px-3 py-2 text-sm">
              <option value="">Todas las áreas</option>
              {opciones.areas.map(a => <option key={a} value={a}>{a}</option>)}
            </select>
            <select value={filtros.grado} onChange={setFiltro('grado')} aria-label="Filtrar por grado"
              className="bg-surface border border-line rounded-xl px-3 py-2 text-sm">
              <option value="">Todos los grados</option>
              {opciones.grados.map(g => <option key={g} value={g}>{g}</option>)}
            </select>
            {hayFiltros && (
              <button onClick={() => setFiltros(FILTROS_VACIOS)}
                className="text-sm text-accent-text hover:underline px-2">
                Limpiar filtros
              </button>
            )}
          </div>
          {hayFiltros && !loadingDocs && (
            <p className="text-xs text-fg-subtle mb-4" role="status">
              {total} documento(s) encontrado(s).
            </p>
          )}
          <div className="space-y-3">
            {loadingDocs ? (
              <div role="status" aria-label="Cargando documentos" className="space-y-3">
                {[0, 1, 2, 3].map(i => (
                  <div key={i} className="glass p-5 rounded-2xl flex items-center gap-4 animate-pulse">
                    <div className="w-12 h-12 rounded-xl bg-surface-2" />
                    <div className="flex-1 space-y-2">
                      <div className="h-4 w-2/3 rounded bg-surface-2" />
                      <div className="h-3 w-1/3 rounded bg-surface-2" />
                    </div>
                  </div>
                ))}
              </div>
            ) : recentDocs.length > 0 ? (
              recentDocs.map(doc => (
                <div key={doc.id}
                  className="glass rounded-2xl flex items-center gap-2 pr-3 hover:bg-surface-2 transition-colors group">
                  <button type="button" onClick={() => abrirDoc(doc)}
                    className="flex-1 min-w-0 text-left p-5 flex items-center gap-4 cursor-pointer rounded-2xl">
                    <div className="w-12 h-12 bg-surface-2 rounded-xl flex items-center justify-center shrink-0">
                      <FileText className="text-fg-subtle group-hover:text-accent-text transition-colors" size={20} aria-hidden="true" />
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-bold line-clamp-2">{doc.title}</h3>
                      <MetaDocumento doc={doc} />
                    </div>
                  </button>
                  <Menu etiqueta={`Acciones de ${doc.title}`} items={itemsDe(doc)} />
                </div>
              ))
            ) : (
              <div className="text-center p-12 bg-surface-2/40 rounded-3xl border border-dashed border-line">
                <p className="text-fg-muted mb-4">
                  {hayFiltros
                    ? 'Ningún documento coincide con tu búsqueda.'
                    : 'Aún no has generado documentos.'}
                </p>
                {!hayFiltros && (
                  <button type="button" onClick={() => setWizard({ open: true, type: 'unidad' })}
                    className="bg-accent hover:bg-accent-hover text-white px-5 py-2 rounded-xl font-bold transition-colors">
                    Crear mi primera unidad
                  </button>
                )}
              </div>
            )}
          </div>
          {!loadingDocs && recentDocs.length < total && (
            <div className="flex justify-center mt-6">
              <button onClick={cargarMas} disabled={loadingMore}
                className="bg-surface-2 hover:bg-line disabled:opacity-50 px-6 py-2 rounded-xl text-sm font-bold transition-colors">
                {loadingMore ? 'Cargando…' : `Cargar más (${recentDocs.length} de ${total})`}
              </button>
            </div>
          )}
        </section>

        <GenerationWizard
          isOpen={wizard.open}
          type={wizard.type}
          onClose={() => { setWizard({ ...wizard, open: false }); fetchJobs() }}
          onComplete={handleComplete}
        />
      </main>
    </div>
  )
}

// Línea de metadatos de un documento: tipo, área, grado, antigüedad y estado de validación.
function MetaDocumento({ doc }) {
  const val = doc.content?.validacion
  const criticos = Number(val?.errores_criticos) || 0
  const avisos = Number(val?.errores_advertencia) || 0
  const ultima = doc.updated_at || doc.created_at
  const editado = fechaUtc(ultima).getTime() - fechaUtc(doc.created_at).getTime() > 60 * 1000
  return (
    <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-fg-subtle font-medium">
      <span className={`px-2 py-0.5 rounded-full font-bold ${doc.type === 'unidad' ? 'bg-accent/10 text-accent-text' : 'bg-success/10 text-success-text'}`}>
        {ETIQUETA_TIPO[doc.type] || doc.type}
      </span>
      {doc.area_curricular && <span>{doc.area_curricular}</span>}
      {doc.grado && <span>{doc.grado}</span>}
      <span title={fechaUtc(ultima).toLocaleString('es')}>{editado ? 'Editado' : 'Creado'} {fechaRelativa(ultima)}</span>
      {criticos > 0 && <span className="px-2 py-0.5 rounded-full bg-danger/10 text-danger-text font-bold">Revisar estructura</span>}
      {criticos === 0 && avisos > 0 && <span className="px-2 py-0.5 rounded-full bg-warning/10 text-warning-text font-bold">Con avisos</span>}
    </p>
  )
}

function ActionCard({ title, desc, icon, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="text-left p-5 rounded-2xl bg-surface border border-line hover:border-accent hover:bg-surface-2 transition-colors cursor-pointer group flex items-start gap-4"
    >
      <span className="shrink-0 mt-0.5" aria-hidden="true">{icon}</span>
      <span className="min-w-0">
        <span className="block text-lg font-bold">{title}</span>
        <span className="block text-sm text-fg-muted mt-1">{desc}</span>
        <span className="mt-3 inline-flex items-center gap-2 text-accent-text font-bold text-sm group-hover:translate-x-1 transition-transform">
          Comenzar <ArrowRight size={16} aria-hidden="true" />
        </span>
      </span>
    </button>
  )
}
