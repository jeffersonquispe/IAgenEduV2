import React, { act } from 'react'
import { createRoot } from 'react-dom/client'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import Login from '__SRC__/pages/Login'
import Dashboard from '__SRC__/pages/Dashboard'
import Editor from '__SRC__/pages/Editor'
import Institucion from '__SRC__/pages/Institucion'
import Ejemplos from '__SRC__/pages/Ejemplos'
import Toaster from '__SRC__/components/ui/Toaster'
import Modal from '__SRC__/components/ui/Modal'
import { toast, confirmar } from '__SRC__/lib/notify'
import { aplicarTema } from '__SRC__/lib/theme'

globalThis.IS_REACT_ACT_ENVIRONMENT = true
window.alert = (m) => { globalThis.__alertas.push(String(m)) }
window.confirm = () => true

const GRAVE = /Rendered|hooks|Cannot read|is not defined|is not a function|unique "key"|Maximum update depth|Objects are not valid/i
let errores = []
const consolaOriginal = console.error
console.error = (...a) => { errores.push(a.map(x => (x && x.message) || String(x)).join(' ').replace(/\s+/g, ' ').slice(0, 220)) }

// --- Respuestas con la forma de las del backend real ---
const STATS = {
  stats: { id: 1, user_id: 'u', docs_generados: 3, unidades_generadas: 2, sesiones_generadas: 1, mejoras_realizadas: 1,
    exportaciones_docx: 1, exportaciones_pdf: 0, nivel: 1, puntos: 120, racha_manual: 0, badges_desbloqueados: ['primer_paso'],
    areas_usadas: [], grados_usados: [], dias_uso: [], primera_visita: false },
  level: { nombre: 'Intermedio', icono: '🌿', progreso: 0.4 }, racha: 2,
  available_badges: [{ id: 'primer_paso', nombre: 'Primer Paso', descripcion: 'x', emoji: '🌱' }], new_unlocks: [],
}
const CONTENIDO_EJEMPLO = {
  titulo: 'Unidad de ejemplo', datos_informativos: '| ITEM | CONTENIDO |\n|---|---|\n| **Área curricular** | Arte |',
  situacion_significativa: 'Una situación significativa de ejemplo.',
  secuencia_de_sesiones: 'Sesión 1: Tema uno\nCriterio: c1\nActividades: a1\n\nSesión 2: Tema dos\nCriterio: c2\nActividades: a2',
}
const llamadas = []
function respuesta(m, url, arg) {
  llamadas.push({ m, url, arg })
  const ok = (data, headers = {}) => Promise.resolve({ data, headers })
  if (url.startsWith('/auth/stats')) return ok(STATS)
  if (url.startsWith('/auth/me')) return ok({ email: 'docente@x.com', email_verified: globalThis.__verificado !== false })
  if (url.startsWith('/data/options')) return ok({ areas: ['Matemática', 'Arte'], grados: ['1°', '2°'], competencias: [], temas_por_area: {} })
  if (url.startsWith('/data/documents') && m === 'get')
    return ok(globalThis.__docs || [], { 'x-total-count': String((globalThis.__docs || []).length) })
  if (url.startsWith('/data/documents/') && m === 'put') return ok({ id: 'd1', version: 2, guardado: true, validacion: globalThis.__validacionGuardada || null })
  if (url.startsWith('/data/competencias')) return ok([
    { numero: 1, nombre: 'Resuelve problemas de cantidad' }, { numero: 2, nombre: 'Resuelve problemas de forma' },
    { numero: 3, nombre: 'Resuelve problemas de datos' }])
  if (url.endsWith('/duplicate') && m === 'post') return ok({ id: 'copia1', title: 'Copia de Unidad de Fracciones' })
  if (url === '/generate/unidad/jobs' && m === 'post') return ok({ job_id: 'j9' })
  if (url === '/generate/jobs/j9') return ok(globalThis.__jobDetalle || { status: 'running', etapa: 'generando' })
  if (url.startsWith('/generate/jobs')) return ok(globalThis.__jobs || [])
  if (url.startsWith('/generate/validar'))
    return ok({ es_valido: true, puntaje_validacion: 100, errores_criticos: 0, errores_advertencia: 0, detalle: [], revalidado: true })
  if (url === '/data/ejemplos') return ok([
    { id: 'u1', tipo: 'unidad', titulo: 'Unidad de ejemplo', descripcion: 'd' },
    { id: 's1', tipo: 'sesion', titulo: 'Sesión de ejemplo', descripcion: 'd' }])
  if (url.startsWith('/data/ejemplos/')) return ok({ id: 'u1', tipo: 'unidad', titulo: 'Unidad de ejemplo', fuente: 'Fuente del ejemplo', content: CONTENIDO_EJEMPLO })
  if (url === '/institucion') return ok({ nombre_institucion: 'Colegio Salesiano de Cusco', nivel_modalidad: 'Secundaria',
    dre_ugel: 'UGEL Cusco', coordinacion_pedagogica: '', vision: 'V', mision: 'M', contexto_relevante: 'C',
    valores_institucionales: ['Fe', 'Amor'], enfoques_transversales: null,
    control_documentario: { version: '02', aprobado_por: 'Dirección' } })
  if (url === '/institucion' && m === 'put') return ok({})
  if (url.startsWith('/institucion/presets-valores')) return ok([
    { id: 'cneb', nombre: 'Valores generales (CNEB)', descripcion: 'd', valores: ['Respeto', 'Solidaridad'] },
    { id: 'catolico', nombre: 'Institución católica', descripcion: 'd', valores: ['Fe', 'Caridad'] }])
  if (url.startsWith('/institucion/plantilla')) return Promise.reject({ response: { status: 404 }, message: '404' })
  if (url === '/generate/refine') return ok({ refined_content: 'Texto MEJORADO por la IA.' })
  if (m === 'put') return ok({})
  return ok([])
}
globalThis.__api = respuesta

// --- Ayudas de interacción ---
const esperar = (ms = 60) => act(async () => { await new Promise(r => setTimeout(r, ms)) })
const texto = () => document.body.textContent.replace(/\s+/g, ' ')
const buscarBoton = (t) => [...document.querySelectorAll('button')].find(b => b.textContent.includes(t))
async function clic(t) { const b = buscarBoton(t); if (!b) throw new Error(`no hay botón "${t}"`); await act(async () => { b.click() }) }
async function escribir(el, valor) {
  const proto = el.tagName === 'TEXTAREA' ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype
  await act(async () => {
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, valor)
    el.dispatchEvent(new window.Event('input', { bubbles: true }))
  })
}

async function elegir(el, valor) {
  await act(async () => {
    Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set.call(el, valor)
    el.dispatchEvent(new window.Event('change', { bubbles: true }))
  })
}
const campo = (etiqueta) => { const l = [...document.querySelectorAll('label')].find(x => x.textContent.includes(etiqueta)); return l && document.getElementById(l.htmlFor) }
const abrirWizardUnidad = () => montar(
  <MemoryRouter initialEntries={[{ pathname: '/', state: { nuevo: 'unidad' } }]}><Dashboard user={{}} /></MemoryRouter>)

async function montar(elemento) {
  document.body.innerHTML = ''
  const cont = document.createElement('div'); document.body.appendChild(cont)
  const raiz = createRoot(cont)
  await act(async () => { raiz.render(elemento) })
  await esperar()
  return () => act(async () => { raiz.unmount() })
}

const resultados = []
async function escenario(nombre, fn) {
  errores = []; llamadas.length = 0; globalThis.__alertas = []
  let fallo = null
  try { await fn() } catch (e) { fallo = String(e.message).split('\n')[0].slice(0, 200) }
  const graves = errores.filter(e => GRAVE.test(e))
  const ok = !fallo && graves.length === 0
  resultados.push({ nombre, ok, detalle: fallo || (graves.length ? 'console.error: ' + graves[0] : `sin errores (${errores.length} avisos menores)`) })
}
const verificar = (cond, msg) => { if (!cond) throw new Error(msg) }
const enRuta = (ruta, estado, elemento) => (
  <MemoryRouter initialEntries={[{ pathname: ruta, state: estado }]}>
    <Routes><Route path={ruta} element={elemento} /><Route path="/" element={<div>DASHBOARD</div>} /></Routes>
  </MemoryRouter>)

async function principal() {
  await escenario('Login: abre y cambia a registro', async () => {
    const desmontar = await montar(<MemoryRouter><Login /></MemoryRouter>)
    verificar(texto().includes('Bienvenido'), 'no muestra el login')
    await clic('Regístrate aquí')
    verificar(document.querySelector('input[placeholder="Nombre completo"]'), 'no aparece el campo de nombre al registrarse')
    await desmontar()
  })

  globalThis.__docs = [
    { id: 'd1', title: 'Unidad de Fracciones', type: 'unidad', area_curricular: 'Matemática', grado: '1°', created_at: '2026-10-01T10:00:00', current_version: 2, content: { situacion_significativa: 'x', validacion: { errores_criticos: 1, errores_advertencia: 0 } } },
    { id: 'd2', title: 'Sesión: la noticia', type: 'sesion', created_at: '2026-10-02T10:00:00', current_version: 1, content: { reto: 'y' } }]
  globalThis.__jobs = [
    { id: 'j1', tipo: 'unidad', status: 'running', etapa: 'generando', created_at: '2026-10-14T10:00:00' },
    { id: 'j2', tipo: 'sesion', status: 'failed', error: 'Sin cuota en Bedrock', created_at: '2026-10-14T09:00:00', updated_at: new Date().toISOString().slice(0, 19) }]
  globalThis.__verificado = false
  await escenario('Dashboard: documentos, filtros, trabajos y aviso de correo', async () => {
    const desmontar = await montar(<MemoryRouter><Dashboard user={{}} /></MemoryRouter>)
    const t = texto()
    verificar(t.includes('Unidad de Fracciones') && t.includes('Sesión: la noticia'), 'no lista los documentos')
    verificar(t.includes('Generaciones') && t.includes('generando con IA') && t.includes('Sin cuota en Bedrock'), 'no muestra los trabajos en curso / fallidos')
    verificar(t.includes('Confirma tu correo electrónico'), 'no muestra el aviso de correo sin verificar')
    const buscador = document.querySelector('input[type="search"]')
    verificar(buscador, 'no hay buscador')
    await escribir(buscador, 'fracc')
    await esperar(450)
    const consulta = llamadas.filter(c => c.url === '/data/documents').pop()
    verificar(consulta && consulta.arg?.params?.q === 'fracc', 'la búsqueda no llegó a la API')
    await desmontar()
  })

  await escenario('Dashboard: abrir el wizard desde el panel', async () => {
    const desmontar = await montar(<MemoryRouter><Dashboard user={{}} /></MemoryRouter>)
    const tarjeta = [...document.querySelectorAll('button')].find(b => b.textContent.startsWith('Unidad Didáctica'))
    verificar(tarjeta, 'no hay tarjeta de Unidad')
    await act(async () => { tarjeta.click() })
    await esperar()
    verificar(texto().includes('Generador de Unidad Didáctica'), 'el wizard no se abre desde el Dashboard')
    await desmontar()
  })

  const contenidoEditor = {
    id: 'd1', version: 1, titulo: 'Unidad de prueba',
    situacion_significativa: 'Texto original de la situación.', materiales_basicos: 'Para el docente: proyector.',
    secuencia_de_sesiones: 'Sesión 1: Tema uno\nCriterio: c1\nActividades: a1\n\nSesión 2: Tema dos\nCriterio: c2\nActividades: a2',
    validacion: { es_valido: false, puntaje_validacion: 75, errores_criticos: 1, errores_advertencia: 0,
      detalle: [{ tipo: 'CRITICO', categoria: 'ESTRUCTURA', mensaje: 'Falta la sección requerida: PROPÓSITOS', seccion: 'PROPÓSITOS' }] },
  }
  globalThis.__validacionGuardada = { es_valido: true, puntaje_validacion: 100, errores_criticos: 0, errores_advertencia: 0, detalle: [] }
  await escenario('Editor: editar → sin guardar → revalidar → guardar con Ctrl+S', async () => {
    const desmontar = await montar(enRuta('/editor', { content: contenidoEditor }, <Editor user={{}} />))
    let t = texto()
    verificar(t.includes('Guardar cambios') && t.includes('Sin cambios'), 'no muestra el botón Guardar / estado inicial')
    verificar(t.includes('1 error(es) crítico(s)') || t.includes('error(es) crítico'), 'no muestra el aviso de validación')
    verificar(buscarBoton('Guardar cambios').disabled, 'Guardar debería estar deshabilitado sin cambios')
    verificar(!document.querySelector('textarea'), 'el documento debería abrir en modo lectura (sin textareas)')
    await clic('Editar')
    const area = [...document.querySelectorAll('textarea')].find(x => x.value.includes('Texto original'))
    verificar(area, 'no hay textarea de la situación significativa')
    await escribir(area, 'Texto EDITADO por el docente.')
    verificar(texto().includes('Cambios sin guardar'), 'no marca "Cambios sin guardar" tras editar')
    verificar(!buscarBoton('Guardar cambios').disabled, 'Guardar debería habilitarse tras editar')
    await esperar(1500)                                            // espera de la revalidación (1,2 s)
    const val = llamadas.find(c => c.url === '/generate/validar')
    verificar(val && val.arg.tipo === 'unidad' && val.arg.content.situacion_significativa.includes('EDITADO'), 'no se revalidó tras editar')
    await act(async () => { window.dispatchEvent(new window.KeyboardEvent('keydown', { key: 's', ctrlKey: true, bubbles: true })) })
    await esperar()
    const put = llamadas.find(c => c.m === 'put')
    verificar(put && put.url === '/data/documents/d1', 'Ctrl+S no guardó')
    verificar(put.arg.base_version === 1 && put.arg.content.situacion_significativa.includes('EDITADO'), 'el guardado no envía la versión ni el contenido editado')
    t = texto()
    verificar(t.includes('Guardado') && !t.includes('Cambios sin guardar'), 'no muestra "Guardado" tras guardar')
    await desmontar()
  })

  await escenario('Editor: documento sin id no ofrece guardar', async () => {
    const { id, version, ...sinId } = contenidoEditor
    const desmontar = await montar(enRuta('/editor', { content: sinId }, <Editor user={{}} />))
    verificar(!texto().includes('Guardar cambios'), 'ofrece guardar un documento sin id')
    verificar(texto().includes('SITUACIÓN SIGNIFICATIVA'), 'no renderiza las secciones')
    await desmontar()
  })

  const conErrorEnSecuencia = { ...contenidoEditor, validacion: { es_valido: false, puntaje_validacion: 60, errores_criticos: 0, errores_advertencia: 1,
    detalle: [{ tipo: 'ADVERTENCIA', categoria: 'CONTENIDO', mensaje: 'Las sesiones no tienen criterio', seccion: 'SECUENCIA DE SESIONES' }] } }

  await escenario('Editor: índice de secciones, avisos enlazados y barra de acciones', async () => {
    const desmontar = await montar(enRuta('/editor', { content: conErrorEnSecuencia }, <Editor user={{}} />))
    const indice = document.querySelector('nav[aria-label="Secciones del documento"]')
    verificar(indice, 'no hay índice de secciones')
    verificar(indice.textContent.includes('SITUACIÓN SIGNIFICATIVA') && indice.textContent.includes('SECUENCIA DE SESIONES'), 'el índice no lista las secciones')
    verificar(indice.textContent.includes('con advertencias'), 'el índice no marca la sección con advertencias')
    verificar(buscarBoton('Ir a la sección'), 'el aviso no enlaza con su sección')
    verificar(document.getElementById('seccion-secuencia_de_sesiones'), 'falta el ancla de la sección')
    verificar(document.querySelector('.sticky.top-0'), 'la barra de acciones no es fija')
    verificar(!texto().includes('Aprobar Documento'), 'sigue el paso "Aprobar" previo a exportar')
    await desmontar()
  })

  await escenario('Editor: refinar muestra propuesta, se acepta y se deshace', async () => {
    const desmontar = await montar(enRuta('/editor', { content: contenidoEditor }, <Editor user={{}} />))
    await act(async () => { document.querySelector('button[title="Asistente IA"]').click() })
    await clic('Más breve'); await esperar()
    verificar(texto().includes('Propuesta de la IA') && texto().includes('Texto MEJORADO por la IA.'), 'no muestra la propuesta de la IA')
    verificar(document.getElementById('seccion-situacion_significativa').textContent.includes('Texto original'), 'el texto actual no debe cambiar antes de aceptar')
    await clic('Aceptar cambio')
    const sec = () => document.getElementById('seccion-situacion_significativa').textContent
    verificar(sec().includes('Texto MEJORADO') && !sec().includes('Texto original'), 'aceptar no aplicó la propuesta')
    verificar(texto().includes('Cambios sin guardar'), 'aceptar no marca cambios sin guardar')
    await clic('Deshacer')
    verificar(sec().includes('Texto original') && !sec().includes('MEJORADO'), 'deshacer no restauró el texto')
    await desmontar()
  })

  await escenario('Editor: menú Exportar y descartar una propuesta', async () => {
    const desmontar = await montar(enRuta('/editor', { content: contenidoEditor }, <Editor user={{}} />))
    verificar(!texto().includes('Word (.docx)'), 'el menú debería estar cerrado')
    await clic('Exportar')
    verificar(document.querySelector('[role="menu"]') && texto().includes('Word (.docx)') && texto().includes('PDF'), 'no abre el menú Exportar')
    await act(async () => { document.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true })) })
    verificar(!document.querySelector('[role="menu"]'), 'Esc no cierra el menú')
    await act(async () => { document.querySelector('button[title="Asistente IA"]').click() })
    await clic('Más breve'); await esperar()
    await clic('Descartar')
    verificar(!texto().includes('Propuesta de la IA') && !texto().includes('Cambios sin guardar'), 'descartar no deja el texto intacto')
    await desmontar()
  })

  await escenario('Editor: el Sidebar no deja salir con cambios sin guardar', async () => {
    const confirmOriginal = window.confirm
    const desmontar = await montar(enRuta('/editor', { content: contenidoEditor }, <Editor user={{}} />))
    await esperar()
    await clic('Editar')
    await escribir([...document.querySelectorAll('textarea')][0], 'cambio sin guardar')
    window.confirm = () => false
    await clic('Nueva Sesión'); await esperar()
    verificar(texto().includes('SITUACIÓN SIGNIFICATIVA') && !texto().includes('DASHBOARD'), 'navegó pese a cancelar la salida')
    window.confirm = () => true
    await clic('Nueva Sesión'); await esperar()
    verificar(texto().includes('DASHBOARD'), 'no navegó tras confirmar la salida')
    window.confirm = confirmOriginal
    await desmontar()
  })

  await escenario('Dashboard: continuar, metadatos del documento y saludo con nombre', async () => {
    const desmontar = await montar(<MemoryRouter><Dashboard user={{ user_metadata: { full_name: 'María López' } }} /></MemoryRouter>)
    const t = texto()
    verificar(t.includes('Hola, María') && !t.includes('Maestro'), 'el saludo no usa el nombre del docente')
    verificar(t.includes('Continuar donde lo dejaste'), 'falta la sección para continuar')
    verificar(t.includes('Matemática') && t.includes('1°'), 'la lista no muestra área y grado')
    verificar(t.includes('Revisar estructura'), 'no marca el documento con errores críticos')
    verificar(/hace|ago|\d{1,2}\/\d{1,2}\/\d{2,4}/.test(t), 'no muestra la antigüedad del documento')
    verificar(!t.includes('PREMIUM') && !t.includes('IA Ready'), 'quedó la marca anterior')
    await desmontar()
  })

  await escenario('Dashboard: con filtros no se ofrece "Continuar" y el vacío invita a crear', async () => {
    const docsPrevios = globalThis.__docs
    globalThis.__docs = []
    const desmontar = await montar(<MemoryRouter><Dashboard user={{}} /></MemoryRouter>)
    verificar(!texto().includes('Continuar donde lo dejaste'), 'ofrece continuar sin documentos')
    verificar(buscarBoton('Crear mi primera unidad'), 'el estado vacío no invita a crear')
    await desmontar()
    globalThis.__docs = docsPrevios
  })

  await escenario('Sidebar móvil: el botón abre el panel, Esc lo cierra y navegar lo cierra', async () => {
    const desmontar = await montar(<MemoryRouter><Dashboard user={{}} /></MemoryRouter>)
    await esperar()
    verificar(!document.querySelector('#menu-movil'), 'el panel móvil debería estar cerrado')
    const abrir = document.querySelector('button[aria-label="Abrir menú"]')
    verificar(abrir && abrir.getAttribute('aria-expanded') === 'false', 'falta el botón de menú accesible')
    await act(async () => { abrir.click() })
    const panel = document.querySelector('#menu-movil[role="dialog"][aria-modal="true"]')
    verificar(panel && panel.querySelector('nav[aria-label="Navegación principal"]'), 'el panel no contiene la navegación')
    await act(async () => { document.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true })) })
    verificar(!document.querySelector('#menu-movil'), 'Esc no cierra el panel')
    await act(async () => { abrir.click() })
    const enPanel = [...document.querySelectorAll('#menu-movil button')].find(b => b.textContent.includes('Ejemplos'))
    await act(async () => { enPanel.click() }); await esperar()
    verificar(!document.querySelector('#menu-movil'), 'navegar no cierra el panel')
    await desmontar()
  })

  await escenario('Dashboard: menú por fila (duplicar, exportar, eliminar)', async () => {
    const desmontar = await montar(<MemoryRouter><Dashboard user={{}} /></MemoryRouter>)
    const abrirMenu = async (titulo) => {
      const b = document.querySelector(`button[aria-label="Acciones de ${titulo}"]`)
      verificar(b, `no hay menú de acciones para ${titulo}`)
      await act(async () => { b.click() })
    }
    verificar(!document.querySelector('[role="menu"]'), 'el menú debería estar cerrado')
    await abrirMenu('Unidad de Fracciones')
    const items = [...document.querySelectorAll('[role="menuitem"]')].map(i => i.textContent)
    verificar(['Abrir', 'Duplicar', 'Exportar Word (.docx)', 'Exportar PDF', 'Eliminar'].every(x => items.includes(x)), 'faltan acciones: ' + items.join(', '))
    verificar(!document.querySelector('button button'), 'hay botones anidados en la fila')

    await clic('Duplicar'); await esperar()
    verificar(llamadas.some(c => c.m === 'post' && c.url === '/data/documents/d1/duplicate'), 'no llamó a duplicar')
    verificar(!document.querySelector('[role="menu"]'), 'el menú no se cerró tras elegir')

    await abrirMenu('Unidad de Fracciones')
    await clic('Exportar PDF'); await esperar()
    verificar(llamadas.some(c => c.m === 'post' && c.url === '/export/pdf'), 'no llamó a exportar')

    await abrirMenu('Sesión: la noticia')
    await act(async () => { document.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true })) })
    verificar(!document.querySelector('[role="menu"]'), 'Esc no cierra el menú')

    await abrirMenu('Sesión: la noticia')
    await clic('Eliminar'); await esperar()           // sin <Toaster/> usa window.confirm (true)
    verificar(llamadas.some(c => c.m === 'delete' && c.url === '/data/documents/d2'), 'no llamó a eliminar')
    verificar(!texto().includes('Sesión: la noticia'), 'el documento eliminado sigue en la lista')
    verificar(texto().includes('Unidad de Fracciones'), 'se quitó otro documento')
    await desmontar()
  })

  await escenario('Dashboard: eliminar cancelado no borra nada', async () => {
    const confirmOriginal = window.confirm
    window.confirm = () => false
    const desmontar = await montar(<MemoryRouter><Dashboard user={{}} /></MemoryRouter>)
    await act(async () => { document.querySelector('button[aria-label="Acciones de Unidad de Fracciones"]').click() })
    await clic('Eliminar'); await esperar()
    verificar(!llamadas.some(c => c.m === 'delete'), 'eliminó pese a cancelar')
    verificar(texto().includes('Unidad de Fracciones'), 'desapareció de la lista')
    window.confirm = confirmOriginal
    await desmontar()
  })

  await escenario('Editor: una "tabla" con todo en una celda se muestra como texto, no como tabla vacía', async () => {
    const doc = { ...contenidoEditor, propositos_de_aprendizaje: '| ITEM | CONTENIDO |\n|---|---|\n| **Competencias COMPETENCIA 12 Investiga usando métodos científicos.** | |' }
    const desmontar = await montar(enRuta('/editor', { content: doc }, <Editor user={{}} />))
    const sec = document.getElementById('seccion-propositos_de_aprendizaje')
    verificar(sec, 'no se renderiza la sección de propósitos')
    verificar(!sec.querySelector('table'), 'una celda única no debería dibujarse como tabla')
    verificar(sec.textContent.includes('Competencias COMPETENCIA 12 Investiga usando métodos científicos.'), 'no muestra el texto')
    verificar(!sec.textContent.includes('**') && !sec.textContent.includes('|'), 'quedaron marcadores de Markdown a la vista')
    verificar(sec.querySelector('strong'), 'la negrita de Markdown no se renderiza como negrita')
    await desmontar()
  })

  await escenario('Editor: las celdas de una tabla real muestran la negrita sin asteriscos', async () => {
    const doc = { ...contenidoEditor, datos_informativos: '| ITEM | CONTENIDO |\n|---|---|\n| **Área curricular** | Arte |' }
    const desmontar = await montar(enRuta('/editor', { content: doc }, <Editor user={{}} />))
    const sec = document.getElementById('seccion-datos_informativos')
    verificar(sec.querySelector('table'), 'la tabla real debe seguir siendo tabla')
    verificar(sec.textContent.includes('Área curricular') && !sec.textContent.includes('**'), 'muestra asteriscos en la tabla')
    await desmontar()
  })

  await escenario('Institución: control documentario y presets de valores', async () => {
    const desmontar = await montar(<MemoryRouter><Institucion /></MemoryRouter>)
    const t = texto()
    verificar(t.includes('Control documentario'), 'no muestra la sección de control documentario')
    verificar(document.querySelector('input[name="version"]').value === '02', 'no carga la versión guardada del control documentario')
    verificar(t.includes('Valores generales (CNEB)') && t.includes('Institución católica'), 'no ofrece los presets')
    await clic('Institución católica')
    verificar(document.querySelector('input[name="valores_institucionales"]').value === 'Fe, Caridad', 'el preset no rellena el campo de valores')
    await desmontar()
  })

  await escenario('Ejemplos: lista y visor en solo lectura', async () => {
    const desmontar = await montar(<MemoryRouter><Ejemplos /></MemoryRouter>)
    const t = texto()
    verificar(t.includes('Unidad de ejemplo') && t.includes('Sesión de ejemplo'), 'no lista los ejemplos')
    verificar(t.includes('Ejemplo · solo lectura') && t.includes('Una situación significativa de ejemplo.'), 'no muestra el contenido del ejemplo')
    verificar(!buscarBoton('Guardar') && !document.querySelector('button[title="Asistente IA"]'), 'ofrece editar o refinar un ejemplo')
    await desmontar()
  })

  await escenario('Sidebar: "Nueva Sesión" abre el wizard de Sesión en el Dashboard', async () => {
    const desmontar = await montar(<MemoryRouter><Dashboard user={{}} /></MemoryRouter>)
    verificar(!texto().includes('Generador de Sesión'), 'el wizard no debería estar abierto al inicio')
    await clic('Nueva Sesión')
    await esperar()
    verificar(texto().includes('Generador de Sesión de Aprendizaje'), 'el ítem del Sidebar no abre el wizard')
    await desmontar()
  })

  await escenario('Dashboard: la navegación y los documentos son botones accesibles', async () => {
    const desmontar = await montar(<MemoryRouter><Dashboard user={{}} /></MemoryRouter>)
    verificar(buscarBoton('Unidad de Fracciones'), 'el documento no es un botón')
    verificar(document.querySelector('nav[aria-label] button[aria-current="page"]'), 'el ítem activo no marca aria-current')
    verificar(!document.body.textContent.includes('Mis Badges'), 'quedó un ítem de navegación sin destino')
    await desmontar()
  })

  await escenario('Toaster: avisos, confirmación propia y fallback sin host', async () => {
    // Sin <Toaster/>: degrada a window.alert / window.confirm.
    toast.error('sin host')
    verificar(globalThis.__alertas.includes('sin host'), 'sin host debería usar window.alert')
    verificar(await confirmar({ titulo: 'T', mensaje: 'M' }) === true, 'sin host debería usar window.confirm')

    const desmontar = await montar(<Toaster />)
    await act(async () => { toast.error('algo falló') })
    verificar(document.querySelector('[role="alert"]')?.textContent.includes('algo falló'), 'no aparece el toast de error')
    verificar(!globalThis.__alertas.includes('algo falló'), 'con host no debe usar window.alert')

    let respuesta
    await act(async () => { confirmar({ titulo: 'Exportar', mensaje: '¿Seguro?', detalle: ['Falta X'], confirmar: 'Sí, exportar' }).then(v => { respuesta = v }) })
    verificar(document.querySelector('[role="dialog"]') && texto().includes('Falta X'), 'no aparece el diálogo de confirmación')
    await clic('Sí, exportar')
    verificar(respuesta === true, 'confirmar no resolvió true')

    await act(async () => { confirmar({ titulo: 'Salir', mensaje: '¿Salir?' }).then(v => { respuesta = v }) })
    await act(async () => { document.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true })) })
    verificar(respuesta === false && !document.querySelector('[role="dialog"]'), 'Esc debería cancelar la confirmación')
    await desmontar()
  })

  await escenario('Modal: Esc cierra y el foco queda dentro', async () => {
    let cerrado = false
    const desmontar = await montar(<Modal titulo="Prueba" onClose={() => { cerrado = true }}><button>Uno</button><button>Dos</button></Modal>)
    verificar(document.querySelector('[role="dialog"][aria-modal="true"][aria-label="Prueba"]'), 'falta role=dialog/aria-modal')
    verificar(document.activeElement?.textContent === 'Uno', 'el foco no entra al diálogo')
    await act(async () => { document.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Tab', bubbles: true })) })
    await act(async () => { document.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true })) })
    verificar(cerrado, 'Esc no cierra el diálogo')
    await desmontar()
  })

  await escenario('Tema: alternar claro/oscuro aplica la clase en <html>', async () => {
    aplicarTema('dark')
    verificar(document.documentElement.classList.contains('dark'), 'no aplica el tema oscuro')
    aplicarTema('light')
    verificar(!document.documentElement.classList.contains('dark'), 'no vuelve al tema claro')
  })

  await escenario('Wizard: error en línea al avanzar sin área/grado, y competencias con tope', async () => {
    const desmontar = await abrirWizardUnidad()
    verificar(texto().includes('Generador de Unidad Didáctica'), 'no abre el wizard')
    await clic('Siguiente')
    verificar([...document.querySelectorAll('[role="alert"]')].some(a => a.textContent.includes('Elige el área')), 'no muestra el error en línea')
    verificar(texto().includes('Paso 1 de 3'), 'avanzó sin área ni grado')
    await elegir(campo('Área Curricular'), 'Matemática')
    await elegir(campo('Grado'), '1°')
    await clic('Siguiente')
    await esperar()
    verificar(texto().includes('Paso 2 de 3'), 'no avanzó con área y grado')
    const cajas = [...document.querySelectorAll('input[type="checkbox"]')]
    verificar(cajas.length === 3, 'las competencias no son checkboxes')
    await act(async () => { cajas[0].click() }); await act(async () => { cajas[1].click() })
    verificar(cajas[2].disabled, 'la tercera competencia debería estar bloqueada (tope 2)')
    verificar(texto().includes('2 de 2 seleccionada'), 'no actualiza el contador')
    await act(async () => { cajas[0].click() })
    verificar(!cajas[2].disabled, 'al desmarcar una, la tercera debe habilitarse')
    verificar(document.querySelector('details summary')?.textContent.includes('Datos informativos'), 'los datos opcionales no están plegados')
    await desmontar()
  })

  await escenario('Wizard: la generación muestra etapas (cola → generando → validando)', async () => {
    globalThis.__jobDetalle = { status: 'running', etapa: 'validando', texto_parcial: 'avance' }
    const desmontar = await abrirWizardUnidad()
    await elegir(campo('Área Curricular'), 'Matemática')
    await elegir(campo('Grado'), '1°')
    await clic('Siguiente'); await esperar()
    await clic('Siguiente'); await esperar()
    await clic('Generar')
    await esperar(2800)   // el primer sondeo ocurre a los 2,5 s
    const t = texto()
    verificar(t.includes('En cola') && t.includes('Generando con IA') && t.includes('Validando y estructurando'), 'no lista las etapas')
    const actual = document.querySelector('li[aria-current="step"]')
    verificar(actual?.textContent.includes('Validando y estructurando'), 'la etapa en curso no es "Validando"')
    verificar(t.includes('(completado)'), 'no marca como completadas las etapas previas')
    await desmontar()
    delete globalThis.__jobDetalle
  })

  console.error = consolaOriginal
  for (const r of resultados) console.log((r.ok ? 'OK    ' : 'FALLA ') + r.nombre + '\n         ' + r.detalle)
  const todoOk = resultados.every(r => r.ok)
  console.log('\n' + (todoOk ? 'RESULTADO: todas las pantallas renderizan y responden bien' : 'RESULTADO: HAY ERRORES'))
  process.exit(todoOk ? 0 : 1)
}
principal()
