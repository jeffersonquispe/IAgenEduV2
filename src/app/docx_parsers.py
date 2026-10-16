import re

def extraer_secuencia_sesiones(contenido, num_sesiones_esperadas=4, *, max_titulo=500, max_criterio=600,
                               max_actividades=800):
    """
    Extrae por cada sesión: titulo, criterio de evaluación, principales actividades.
    Retorna lista de dicts con keys titulo, criterio, actividades.
    """
    resultado = []
    lineas = contenido.split('\n')
    contenido_secuencia = []
    dentro_secuencia = False
    
    for linea in lineas:
        linea_stripped = linea.strip()
        if 'SECUENCIA' in linea_stripped.upper() and 'SESION' in linea_stripped.upper():
            dentro_secuencia = True
            if '|' in linea_stripped:
                partes = linea_stripped.split('|')
                if len(partes) >= 3:
                    contenido_secuencia.append(partes[2].strip())
                elif len(partes) >= 2:
                    contenido_secuencia.append(partes[1].strip())
            continue
        if dentro_secuencia and '|' in linea_stripped:
            partes = linea_stripped.split('|')
            if len(partes) >= 3:
                item = (partes[1] or "").strip()
                if item and '**' in item and 'SECUENCIA' not in item.upper():
                    break
                contenido_secuencia.append(partes[2].strip())
            elif len(partes) >= 2:
                contenido_secuencia.append(partes[1].strip())
        elif dentro_secuencia and linea_stripped and not linea_stripped.startswith('|'):
            if contenido_secuencia:
                contenido_secuencia[-1] += " " + linea_stripped
        elif dentro_secuencia and not linea_stripped and contenido_secuencia:
            break
    
    texto = " ".join(contenido_secuencia).replace("  ", " ")

    def _cortar_en_siguiente_sesion(txt):
        """Evita cruce: corta antes de cualquier 'Sesión N° X' o 'Sesión X' que indique otra sesión."""
        if not txt:
            return txt
        partes = re.split(r"\s+Sesi[oó]n\s*(?:N°?|Nro\.?)?\s*\d+\s*[:\-]", txt, 1, flags=re.IGNORECASE)
        return (partes[0] or "").strip()

    for n in range(1, num_sesiones_esperadas + 1):
        bloque = ""
        patron_inicio = re.compile(r"Sesi[oó]n\s*(?:N°?|Nro\.?)?\s*" + str(n) + r"\s*[:\-]\s*", re.IGNORECASE)
        patron_siguiente = re.compile(r"Sesi[oó]n\s*(?:N°?|Nro\.?)?\s*" + str(n + 1) + r"\s*[:\-]\s*", re.IGNORECASE)
        match = patron_inicio.search(texto)
        if match:
            inicio = match.end()
            match_sig = patron_siguiente.search(texto[inicio:])
            if match_sig:
                bloque = texto[inicio:inicio + match_sig.start()].strip()
            else:
                bloque = texto[inicio:].strip()
        else:
            resultado.append({"titulo": "", "criterio": "", "actividades": ""})
            continue

        titulo = ""
        criterio = ""
        actividades = ""
        resto = bloque
        for sep in ("Título:", "Titulo:"):
            if sep in resto:
                resto = resto.split(sep, 1)[1].strip()
                for sep_c in ("Criterio de evaluación:", "Criterio de evaluacion:"):
                    if sep_c in resto:
                        titulo = resto.split(sep_c, 1)[0].strip()
                        resto = resto.split(sep_c, 1)[1].strip()
                        if "Principales actividades" in resto:
                            partes_act = re.split(r"Principales actividades\s*:?\s*", resto, 1, flags=re.IGNORECASE)
                            criterio = (partes_act[0] or "").strip()
                            actividades = (partes_act[-1] or "").strip() if len(partes_act) > 1 else ""
                        else:
                            criterio = resto.strip()
                        break
                else:
                    titulo = resto[:500].strip()
                break
        if not titulo and bloque:
            titulo = bloque[:400].strip()

        # Cortar en la siguiente sesión para evitar cruce de información
        titulo = _cortar_en_siguiente_sesion(titulo)
        criterio = _cortar_en_siguiente_sesion(criterio)
        actividades = _cortar_en_siguiente_sesion(actividades)

        def _limpiar_celda(t):
            if not t:
                return t
            t = re.sub(r'CONTENIDO\s*-+\s*', '', t, flags=re.IGNORECASE)
            t = re.sub(r'\s*-{5,}\s*', ' ', t)
            t = t.replace("  ", " ").strip()
            for corte in ('Estándares de aprendizaje', 'ESTÁNDARES DE APRENDIZAJE', 'Instrumento de evaluación'):
                if corte in t:
                    t = t.split(corte)[0].strip()
            return t
        titulo = _limpiar_celda(titulo[:max_titulo] if titulo else "")
        criterio = _limpiar_celda(criterio[:max_criterio] if criterio else "")
        actividades = _limpiar_celda(actividades[:max_actividades] if actividades else "")
        resultado.append({"titulo": titulo, "criterio": criterio, "actividades": actividades})
    
    while len(resultado) < num_sesiones_esperadas:
        resultado.append({"titulo": "", "criterio": "", "actividades": ""})
    return resultado[:num_sesiones_esperadas]

def extraer_competencias_transversales(contenido):
    """
    Extrae los datos de la tabla de competencias transversales del contenido generado.
    Retorna un diccionario con los estándares e instrumentos para cada competencia.
    """
    competencias_data = {
        "Se desenvuelve en los entornos virtuales generados por las TIC.": {
            "estandar": "",
            "instrumento": ""
        },
        "Gestiona su aprendizaje de manera autónoma.": {
            "estandar": "",
            "instrumento": ""
        }
    }
    
    # Buscar la tabla de competencias transversales en el contenido
    lineas = contenido.split('\n')
    dentro_tabla_comp_trans = False
    
    for i, linea in enumerate(lineas):
        linea_stripped = linea.strip()
        
        # Detectar inicio de tabla de competencias transversales (puede estar en encabezado o en contenido)
        if '|' in linea_stripped and ('COMPETENCIAS TRANSVERSALES' in linea_stripped.upper() or 
                                     ('ESTÁNDARES' in linea_stripped.upper() and 'INSTRUMENTO' in linea_stripped.upper())):
            dentro_tabla_comp_trans = True
            # Verificar si esta línea ya tiene datos (no es solo el encabezado)
            partes = linea_stripped.split('|')
            fila = [celda.strip() for celda in partes]
            # Eliminar celdas vacías al inicio y final
            while fila and not fila[0]:
                fila.pop(0)
            while fila and not fila[-1]:
                fila.pop()
            
            # Si tiene 3 columnas y contiene una competencia, procesarla
            if len(fila) == 3 and any(palabra in fila[0].upper() for palabra in ['SE DESENVUELVE', 'GESTIONA']):
                competencia = fila[0]
                estandar = fila[1] if len(fila) > 1 else ""
                instrumento = fila[2] if len(fila) > 2 else ""
                
                if "Se desenvuelve" in competencia or "entornos virtuales" in competencia:
                    competencias_data["Se desenvuelve en los entornos virtuales generados por las TIC."]["estandar"] = estandar
                    competencias_data["Se desenvuelve en los entornos virtuales generados por las TIC."]["instrumento"] = instrumento
                elif "Gestiona" in competencia or "aprendizaje" in competencia and "autónoma" in competencia:
                    competencias_data["Gestiona su aprendizaje de manera autónoma."]["estandar"] = estandar
                    competencias_data["Gestiona su aprendizaje de manera autónoma."]["instrumento"] = instrumento
            continue
        
        if dentro_tabla_comp_trans:
            # Detectar si es una fila de datos (tiene 3 columnas y contiene las competencias)
            if '|' in linea_stripped and linea_stripped.count('|') >= 3:
                partes = linea_stripped.split('|')
                fila = [celda.strip() for celda in partes]
                # Eliminar celdas vacías al inicio y final
                while fila and not fila[0]:
                    fila.pop(0)
                while fila and not fila[-1]:
                    fila.pop()
                
                # Verificar si es una fila de datos (3 columnas y contiene una de las competencias)
                if len(fila) == 3:
                    competencia = fila[0]
                    estandar = fila[1] if len(fila) > 1 else ""
                    instrumento = fila[2] if len(fila) > 2 else ""
                    
                    # Verificar si corresponde a una de las competencias conocidas
                    if "Se desenvuelve" in competencia or ("entornos virtuales" in competencia and "TIC" in competencia):
                        if not competencias_data["Se desenvuelve en los entornos virtuales generados por las TIC."]["estandar"]:
                            competencias_data["Se desenvuelve en los entornos virtuales generados por las TIC."]["estandar"] = estandar
                        if not competencias_data["Se desenvuelve en los entornos virtuales generados por las TIC."]["instrumento"]:
                            competencias_data["Se desenvuelve en los entornos virtuales generados por las TIC."]["instrumento"] = instrumento
                    elif "Gestiona" in competencia and ("aprendizaje" in competencia or "autónoma" in competencia):
                        if not competencias_data["Gestiona su aprendizaje de manera autónoma."]["estandar"]:
                            competencias_data["Gestiona su aprendizaje de manera autónoma."]["estandar"] = estandar
                        if not competencias_data["Gestiona su aprendizaje de manera autónoma."]["instrumento"]:
                            competencias_data["Gestiona su aprendizaje de manera autónoma."]["instrumento"] = instrumento
            elif linea_stripped and '|' not in linea_stripped:
                # Línea fuera de tabla, puede ser el fin
                if not any(palabra in linea_stripped.upper() for palabra in ['COMPETENCIAS', 'TRANSVERSALES', 'ESTÁNDARES', 'INSTRUMENTO', 'SE DESENVUELVE', 'GESTIONA']):
                    # Ya no estamos en la tabla
                    break
    
    return competencias_data

def extraer_propositos_aprendizaje(contenido):
    """
    Extrae los datos de PROPÓSITOS DE APRENDIZAJE del contenido generado.
    Retorna un diccionario con competencias, capacidades, criterios, evidencias e instrumentos.
    """
    propositos_data = {
        "competencias": "",
        "capacidades": "",
        "criterios": "",
        "contenidos": "",
        "evidencias": "",
        "instrumentos": ""
    }
    
    lineas = contenido.split('\n')
    dentro_propositos = False
    contenido_propositos = []
    
    for i, linea in enumerate(lineas):
        linea_stripped = linea.strip()
        
        # Detectar inicio de PROPÓSITOS DE APRENDIZAJE
        if 'PROPÓSITOS DE APRENDIZAJE' in linea_stripped.upper() or 'III. PROPÓSITOS' in linea_stripped.upper():
            dentro_propositos = True
            # Extraer contenido de esta línea si está presente
            if '|' in linea_stripped:
                partes = linea_stripped.split('|')
                if len(partes) >= 3:
                    contenido_celda = partes[2].strip() if len(partes) > 2 else ""
                    if contenido_celda:
                        contenido_propositos.append(contenido_celda)
            continue
        
        # Si estamos dentro de PROPÓSITOS DE APRENDIZAJE, seguir extrayendo
        if dentro_propositos:
            if '|' in linea_stripped:
                partes = linea_stripped.split('|')
                if len(partes) >= 3:
                    item_col = partes[1].strip()
                    contenido_celda = partes[2].strip() if len(partes) > 2 else ""
                    
                    # Verificar si encontramos otro ítem (fin de PROPÓSITOS DE APRENDIZAJE)
                    if item_col and '**' in item_col and 'PROPÓSITOS' not in item_col.upper():
                        break
                    
                    # Si hay contenido en la columna derecha, agregarlo
                    if contenido_celda:
                        contenido_propositos.append(contenido_celda)
            elif linea_stripped and not linea_stripped.startswith('|'):
                # Línea fuera de tabla, puede ser contenido multilínea
                if contenido_propositos:
                    contenido_propositos[-1] += " " + linea_stripped
            elif not linea_stripped and contenido_propositos:
                # Línea vacía, puede indicar fin de sección
                break
    
    # Procesar el contenido extraído para separar competencias, capacidades, criterios, etc.
    contenido_completo = " ".join(contenido_propositos)
    
    # Extraer Competencias
    if 'Competencias:' in contenido_completo or 'COMPETENCIAS:' in contenido_completo:
        partes = contenido_completo.split('Capacidades:')
        if len(partes) > 0:
            competencias_texto = partes[0].replace('Competencias:', '').replace('COMPETENCIAS:', '').strip()
            propositos_data["competencias"] = competencias_texto.split('Criterios')[0].split('CRITERIOS')[0].strip()
    
    # Extraer Capacidades
    if 'Capacidades:' in contenido_completo or 'CAPACIDADES:' in contenido_completo:
        partes = contenido_completo.split('Criterios de evaluación:')
        if len(partes) > 0:
            capacidades_texto = partes[0]
            if 'Capacidades:' in capacidades_texto:
                capacidades_texto = capacidades_texto.split('Capacidades:')[1].strip()
            elif 'CAPACIDADES:' in capacidades_texto:
                capacidades_texto = capacidades_texto.split('CAPACIDADES:')[1].strip()
            propositos_data["capacidades"] = capacidades_texto.split('Contenidos')[0].split('CONTENIDOS')[0].strip()
    
    # Extraer Criterios de evaluación
    if 'Criterios de evaluación:' in contenido_completo or 'CRITERIOS DE EVALUACIÓN:' in contenido_completo or 'Criterios:' in contenido_completo:
        criterios_texto = ""
        if 'Criterios de evaluación:' in contenido_completo:
            criterios_texto = contenido_completo.split('Criterios de evaluación:')[1].strip()
        elif 'CRITERIOS DE EVALUACIÓN:' in contenido_completo:
            criterios_texto = contenido_completo.split('CRITERIOS DE EVALUACIÓN:')[1].strip()
        elif 'Criterios:' in contenido_completo:
            criterios_texto = contenido_completo.split('Criterios:')[1].strip()
            
        if criterios_texto:
            propositos_data["criterios"] = criterios_texto.split('Contenidos')[0].split('CONTENIDOS')[0].split('Evidencia')[0].split('EVIDENCIA')[0].strip()
    
    # Extraer Contenidos
    if 'Contenidos:' in contenido_completo or 'CONTENIDOS:' in contenido_completo:
        partes = contenido_completo.split('Evidencia de aprendizaje:')
        if len(partes) > 0:
            contenidos_texto = partes[0]
            if 'Contenidos:' in contenidos_texto:
                contenidos_texto = contenidos_texto.split('Contenidos:')[1].strip()
            elif 'CONTENIDOS:' in contenidos_texto:
                contenidos_texto = contenidos_texto.split('CONTENIDOS:')[1].strip()
            propositos_data["contenidos"] = contenidos_texto.split('Evidencia')[0].split('EVIDENCIA')[0].strip()
    
    # Extraer Evidencias de aprendizaje
    if 'Evidencia de aprendizaje:' in contenido_completo or 'EVIDENCIA DE APRENDIZAJE:' in contenido_completo or 'Evidencia:' in contenido_completo:
        partes = contenido_completo.split('Instrumento de evaluación:')
        if len(partes) > 0:
            evidencias_texto = partes[0]
            if 'Evidencia de aprendizaje:' in evidencias_texto:
                evidencias_texto = evidencias_texto.split('Evidencia de aprendizaje:')[1].strip()
            elif 'EVIDENCIA DE APRENDIZAJE:' in evidencias_texto:
                evidencias_texto = evidencias_texto.split('EVIDENCIA DE APRENDIZAJE:')[1].strip()
            elif 'Evidencia:' in evidencias_texto:
                evidencias_texto = evidencias_texto.split('Evidencia:')[1].strip()
            propositos_data["evidencias"] = evidencias_texto.split('Instrumento')[0].strip()
    
    # Extraer Instrumentos de evaluación
    if 'Instrumento de evaluación:' in contenido_completo or 'INSTRUMENTO DE EVALUACIÓN:' in contenido_completo or 'Instrumento:' in contenido_completo:
        partes = contenido_completo.split('Instrumento de evaluación:')
        if len(partes) > 1:
            propositos_data["instrumentos"] = partes[1].strip()
        elif 'INSTRUMENTO DE EVALUACIÓN:' in contenido_completo:
            partes = contenido_completo.split('INSTRUMENTO DE EVALUACIÓN:')
            if len(partes) > 1:
                propositos_data["instrumentos"] = partes[1].strip()
        elif 'Instrumento:' in contenido_completo:
            partes = contenido_completo.split('Instrumento:')
            if len(partes) > 1:
                propositos_data["instrumentos"] = partes[1].strip()
    
    return propositos_data

def extraer_valores_enfoques_transversales(contenido):
    """
    Extrae el contenido de VALORES Y ENFOQUES TRANSVERSALES del contenido generado.
    Retorna dict con valores, enfoques_transversales, comportamientos_observables, instrumento.
    """
    data = {
        "valores": "",
        "enfoques_transversales": "",
        "comportamientos_observables": "",
        "instrumento": ""
    }
    
    lineas = contenido.split('\n')
    dentro_valores = False
    contenido_valores = []
    
    for linea in lineas:
        linea_stripped = linea.strip()
        
        if 'VALORES Y ENFOQUES TRANSVERSALES' in linea_stripped.upper():
            dentro_valores = True
            if '|' in linea_stripped:
                partes = linea_stripped.split('|')
                if len(partes) >= 3:
                    contenido_celda = partes[2].strip() if len(partes) > 2 else ""
                    if contenido_celda:
                        contenido_valores.append(contenido_celda)
            continue
        
        if dentro_valores:
            if '|' in linea_stripped:
                partes = linea_stripped.split('|')
                if len(partes) >= 3:
                    item_col = partes[1].strip()
                    contenido_celda = partes[2].strip() if len(partes) > 2 else ""
                    if item_col and '**' in item_col and 'VALORES' not in item_col.upper() and 'ENFOQUES' not in item_col.upper():
                        break
                    if contenido_celda:
                        contenido_valores.append(contenido_celda)
            elif linea_stripped and not linea_stripped.startswith('|'):
                if contenido_valores:
                    contenido_valores[-1] += " " + linea_stripped
            elif not linea_stripped and contenido_valores:
                break
    
    texto_completo = " ".join(contenido_valores).replace("  ", " ").strip()
    if not texto_completo:
        return data
    
    def _limpiar_contenido_marcas(txt):
        """Quita CONTENIDO------------, líneas de guiones y artefactos de prompt."""
        if not txt:
            return txt
        txt = re.sub(r'CONTENIDO\s*-+\s*', '', txt, flags=re.IGNORECASE)
        txt = re.sub(r'\s*-{5,}\s*', ' ', txt)  # líneas de guiones
        return txt.replace("  ", " ").strip()
    
    texto_completo = _limpiar_contenido_marcas(texto_completo)
    
    # Extraer sección Valores (después de "Valores:" hasta "Enfoques:" o "Con comportamientos")
    for sep in ('Valores:', 'VALORES:'):
        if sep in texto_completo:
            idx = texto_completo.find(sep)
            resto = texto_completo[idx + len(sep):].strip()
            for corte in ('Enfoques:', 'ENFOQUES:', 'Con comportamientos', 'con comportamientos'):
                if corte in resto:
                    resto = resto.split(corte)[0].strip()
            # Quitar instrucción del prompt y quedarnos con el listado de valores
            for instr in ('DEBES usar SOLO estos 13 valores (sin agregar ni omitir):', 'DEBES usar SOLO estos 13 valores (sin agregar ni omitir):', 'usar SOLO estos 13 valores:', 'estos 13 valores (sin agregar ni omitir):'):
                if instr in resto:
                    resto = resto.split(instr)[-1].strip()
            if resto.startswith(':'):
                resto = resto[1:].strip()
            data["valores"] = resto[:700].strip() if len(resto) > 700 else resto
            break
    
    # Extraer sección Enfoques transversales (después de "Enfoques:" hasta "Con comportamientos" o punto)
    for sep in ('Enfoques:', 'ENFOQUES:'):
        if sep in texto_completo:
            idx = texto_completo.find(sep)
            resto = texto_completo[idx + len(sep):].strip()
            for corte in ('Con comportamientos', 'con comportamientos', 'Pueden incluir'):
                if corte in resto:
                    resto = resto.split(corte)[0].strip()
            data["enfoques_transversales"] = resto[:600].strip() if len(resto) > 600 else resto
            break
    
    # Comportamientos observables: solo el texto que follows a "comportamientos observables", sin repetir valores/enfoques
    if 'comportamientos observables' in texto_completo.lower():
        idx = texto_completo.lower().find('comportamientos observables')
        candidato = texto_completo[idx:].strip()
        if candidato.startswith('comportamientos observables para cada uno'):
            candidato = candidato[len('comportamientos observables para cada uno'):].strip()
        elif candidato.startswith('comportamientos observables.'):
            candidato = candidato[len('comportamientos observables.'):].strip()
        else:
            candidato = candidato[len('comportamientos observables'):].lstrip(' :.').strip()
        # No incluir texto que repite Valores: o Enfoques: (evitar cruce de información)
        for no_incluir in ('Valores:', 'VALORES:', 'Enfoques:', 'ENFOQUES:'):
            if no_incluir in candidato:
                candidato = candidato.split(no_incluir)[0].strip()
        if candidato:
            data["comportamientos_observables"] = candidato[:800] + ("..." if len(candidato) > 800 else "")
    
    # Si faltan secciones, no duplicar: evitar poner valores/enfoques en comportamientos
    if not data["enfoques_transversales"] and not data["comportamientos_observables"]:
        mitad = len(texto_completo) // 2
        data["enfoques_transversales"] = _limpiar_contenido_marcas(texto_completo[:mitad].strip())[:600]
        data["comportamientos_observables"] = _limpiar_contenido_marcas(texto_completo[mitad:].strip())[:800] or ""
    elif not data["comportamientos_observables"] and data["enfoques_transversales"]:
        # No usar todo el texto en comportamientos (evitar duplicar enfoques/valores)
        data["comportamientos_observables"] = ""
    
    # Limpiar CONTENIDO------------ y guiones de cada campo antes de devolver
    for k in ("valores", "enfoques_transversales", "comportamientos_observables"):
        data[k] = _limpiar_contenido_marcas(data.get(k) or "")
    
    # Instrumento por defecto si no se indica en el contenido
    data["instrumento"] = data.get("instrumento") or "Lista de cotejo o rúbrica de actitudes para valores y enfoques transversales"
    
    return data

def extraer_situacion_significativa_completa(contenido):
    """Extrae el texto completo de la situación significativa del contenido generado."""
    lineas = contenido.split('\n')
    dentro_situacion = False
    contenido_situacion = []
    
    for linea in lineas:
        linea_stripped = linea.strip()
        
        # Detectar inicio de SITUACIÓN SIGNIFICATIVA
        if 'SITUACIÓN SIGNIFICATIVA' in linea_stripped.upper() or 'II. SITUACIÓN' in linea_stripped.upper():
            dentro_situacion = True
            # Extraer contenido de esta línea si está presente
            if '|' in linea_stripped:
                partes = linea_stripped.split('|')
                if len(partes) >= 3:
                    contenido_celda = partes[2].strip() if len(partes) > 2 else partes[1].strip() if len(partes) > 1 else ""
                    if contenido_celda and contenido_celda.replace('**', '').strip():
                        contenido_situacion.append(contenido_celda.replace('**', '').strip())
            continue
        
        # Si estamos dentro de SITUACIÓN SIGNIFICATIVA, seguir extrayendo
        if dentro_situacion:
            if '|' in linea_stripped:
                partes = linea_stripped.split('|')
                if len(partes) >= 3:
                    item_col = partes[1].strip()
                    contenido_celda = partes[2].strip() if len(partes) > 2 else ""
                    
                    # Verificar si encontramos otro ítem (fin de SITUACIÓN SIGNIFICATIVA)
                    if item_col and '**' in item_col and 'SITUACIÓN' not in item_col.upper():
                        break
                    
                    # Si hay contenido en la columna derecha, agregarlo
                    if contenido_celda:
                        contenido_situacion.append(contenido_celda.replace('**', '').strip())
            elif linea_stripped and not linea_stripped.startswith('|'):
                # Línea fuera de tabla, puede ser contenido multilínea
                if contenido_situacion:
                    contenido_situacion[-1] += " " + linea_stripped
            elif not linea_stripped and contenido_situacion:
                # Línea vacía, puede indicar fin de sección
                break
    
    texto_completo = " ".join(contenido_situacion).replace("  ", " ").strip()
    # Eliminar texto "CONTENIDO ----" o variantes que aparecen al final
    texto_completo = re.sub(r'\s*CONTENIDO\s*-+\s*$', '', texto_completo, flags=re.IGNORECASE).strip()
    texto_completo = re.sub(r'\s*CONTENIDO\s*-+\s*', '', texto_completo, flags=re.IGNORECASE).strip()
    return texto_completo if texto_completo else ""

def extraer_propositos_completo(contenido):
    """Extrae el texto completo de los propósitos de aprendizaje del contenido generado."""
    lineas = contenido.split('\n')
    dentro_propositos = False
    contenido_propositos = []
    
    for linea in lineas:
        linea_stripped = linea.strip()
        
        # Detectar inicio de PROPÓSITOS DE APRENDIZAJE
        if 'PROPÓSITOS DE APRENDIZAJE' in linea_stripped.upper() or 'III. PROPÓSITOS' in linea_stripped.upper():
            dentro_propositos = True
            # Extraer contenido de esta línea si está presente
            if '|' in linea_stripped:
                partes = linea_stripped.split('|')
                if len(partes) >= 3:
                    contenido_celda = partes[2].strip() if len(partes) > 2 else partes[1].strip() if len(partes) > 1 else ""
                    if contenido_celda and contenido_celda.replace('**', '').strip():
                        contenido_propositos.append(contenido_celda.replace('**', '').strip())
            continue
        
        # Si estamos dentro de PROPÓSITOS DE APRENDIZAJE, seguir extrayendo
        if dentro_propositos:
            if '|' in linea_stripped:
                partes = linea_stripped.split('|')
                if len(partes) >= 3:
                    item_col = partes[1].strip()
                    contenido_celda = partes[2].strip() if len(partes) > 2 else ""
                    
                    # Verificar si encontramos otro ítem (fin de PROPÓSITOS DE APRENDIZAJE)
                    if item_col and '**' in item_col and 'PROPÓSITOS' not in item_col.upper():
                        break
                    
                    # Si hay contenido en la columna derecha, agregarlo
                    if contenido_celda:
                        contenido_propositos.append(contenido_celda.replace('**', '').strip())
            elif linea_stripped and not linea_stripped.startswith('|'):
                # Línea fuera de tabla, puede ser contenido multilínea
                if contenido_propositos:
                    contenido_propositos[-1] += " " + linea_stripped
            elif not linea_stripped and contenido_propositos:
                # Línea vacía, puede indicar fin de sección
                break
    
    texto_completo = " ".join(contenido_propositos).replace("  ", " ").strip()
    # Eliminar texto "CONTENIDO ----" o variantes que aparecen al final
    texto_completo = re.sub(r'\s*CONTENIDO\s*-+\s*$', '', texto_completo, flags=re.IGNORECASE).strip()
    texto_completo = re.sub(r'\s*CONTENIDO\s*-+\s*', '', texto_completo, flags=re.IGNORECASE).strip()
    return texto_completo if texto_completo else ""
