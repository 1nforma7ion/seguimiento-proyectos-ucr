# Seguimiento de proyectos del bloque UCR — Diseño

Fecha: 2026-11-24 · Estado: listo para aprobación (revisado por un builder; dudas resueltas)

## 1. Para qué es

Cada legislador del bloque UCR de la Legislatura de Córdoba, o su equipo, necesita ver de forma clara en qué estado está **cada proyecto en el que es autor o coautor**, si fue aprobado o no, y lo que haga falta para entenderlo, sin tener que navegar el portal oficial expediente por expediente.

Hoy toda esa información es pública en el portal de Gestión Legislativa Digital (GLD), en https://gld.legislaturacba.gob.ar, pero está dispersa. Cada dato aparece en una ventana distinta y usa vocabulario técnico. Quien pidió la herramienta no conoce a fondo el trámite legislativo. La herramienta tiene que servirle **a cualquiera**, aunque no sea especialista.

## 2. Objetivos

- Vista personal por legislador: sus proyectos, en qué etapa está cada uno, cuál fue el último movimiento y cuándo.
- Resultado de la votación a nivel proyecto: aprobado o no aprobado, y en qué sesión. **No** se registra cómo votó cada legislador ni cada bloque.
- Novedades: qué proyectos se movieron recientemente.
- Detección de proyectos parados, para saber cuáles conviene impulsar.
- Ficha de cada proyecto: línea de tiempo, coautores, comisiones y links a los documentos oficiales (despachos, actas, texto aprobado).
- Vista del bloque completo, pensada para la presidencia del bloque.
- Datos actualizados solos, una vez por día.

## 3. Fuera de alcance (no-objetivos)

- Votación nominal por legislador o por bloque, que exigiría procesar las versiones taquigráficas.
- Proyectos que pasan por las comisiones que integra el legislador sin que sea autor. Queda para una segunda etapa.
- Avisos por mail o WhatsApp. Queda para una segunda etapa.
- Datos anteriores a 2021, que el portal guarda en un sistema aparte.
- Usuarios, contraseñas o edición de datos. La herramienta es de solo lectura.

## 4. Qué la haría un fracaso aunque funcione (anti-objetivos)

- **Que "explote información en la cara":** tablas enormes, jerga del reglamento sin explicar o todo al mismo nivel de importancia.
- **Que las declaraciones de beneplácito y adhesión**, que son muchas, tapen los proyectos de fondo.
- **Que muestre datos equivocados** sin que se note: un proyecto atribuido a quien no es autor o un estado viejo presentado como actual. Siempre se muestra la fecha de la última actualización y el link a la fuente oficial.
- **Que el sistema cargue de más el portal oficial**, con demasiadas consultas o muy seguidas.
- **Que dependa de que alguien prenda una computadora** para actualizarse.

## 5. Restricciones y hechos verificados

- **Sin API pública.** El portal es ASP.NET WebForms. El detalle de un expediente se obtiene con un *postback*: un POST con `__VIEWSTATE`, `__EVENTVALIDATION` y `__EVENTTARGET`.
  - Verificado el 24/11/2026 con un script que solo usa la biblioteca estándar de Python.
  - `GET /Publics/Buscar.aspx?q=<texto>` devuelve resultados de a 10, con número de expediente y extracto.
  - El postback `ctl00$Body$R_Results$ctlNN$LB_Autores` devuelve la lista completa de autores con apellido y nombre, por ejemplo "Ferrero, Alejandra".
  - El postback `...$LB_Ruta` devuelve la secuencia de **Estado** y **Situación** con sesión y fecha, más las secciones Anexos, Actas, Despachos y Texto aprobado.
  - Hay un tercer enlace por resultado, `...$LB_Comisiones`, que todavía no se probó.
- **El buscador encuentra texto, no autores.** Buscar "Ferrero" trae 717 resultados, que incluyen proyectos donde la legisladora solo es mencionada. Por eso la autoría siempre se confirma con el postback de Autores.
- **Formato del expediente:** `NNNNN/T/AA`. La letra T indica el tipo: L (ley, a confirmar), R (resolución), D (declaración), N (nota), C (cuestión de privilegio), entre otros.
- **Estados observados en la Ruta** (verificado en 11 expedientes): Ingresado, Estado Parlamentario, En Comisión, Aprobado, **Caducado**, **Rehabilitado** y **Archivado**.
  - El evento Caducado viene sin sesión y con fecha, por ejemplo "(17/02/2025)".
- **Situaciones observadas en la Ruta:** "Art 110 (tramite normal)" y "Sobre Tablas".
  - Puede haber más valores; el sistema tiene que tolerar los que no conoce y registrarlos.
- **Caducidad.** El portal **registra la caducidad por su cuenta** como estado "Caducado".
  - En todos los casos vistos, el estado aparece exactamente 12 meses después del ingreso cuando el proyecto no tuvo tratamiento.
  - Después puede venir "Rehabilitado", que vuelve a la vida, o "Archivado".
  - No hace falta un motor de reglas de caducidad. El indicador "por caducar" se calcula como ingreso + 12 meses (o rehabilitación + 12 meses, a confirmar con datos) para proyectos que todavía no fueron aprobados.
  - En la muestra, casi todas las leyes del bloque caducaron en comisión. Por eso este indicador es de los más útiles para el usuario.
- **Despachos y votación.**
  - El paso por comisión con dictamen se detecta por la sección **Despachos** de la Ruta, que no está vacía.
  - El portal **no** muestra la votación como un evento aparte del resultado. Aprobado lleva la sesión en la que se votó.
- **Recursos:** hosting gratuito y sin servidor propio.
- **Codificación:** el portal responde en una codificación que no es UTF-8 limpio. Hay que decodificar bien los acentos.

## 6. Enfoques considerados

| Enfoque | A favor | En contra |
|---|---|---|
| Planilla de Google alimentada por un script | Herramienta conocida | Es una tabla. No se puede lograr la vista guiada ni la línea de tiempo, y es justo lo que el usuario no quiere. |
| Base de Notion | Vistas lindas | Cada equipo tiene que aprender Notion. La estética queda limitada a lo que ofrece Notion y la sincronización es más compleja. |
| **Página web estática que se actualiza sola cada día** (elegido) | Un link que se abre en el celular o la compu. Interfaz a medida, gratis y sin depender de una PC prendida. | Hay que construir el recolector de datos y la interfaz. |

**Elegido:** página web estática publicada con GitHub Pages. Un proceso programado de GitHub Actions corre una vez por día, recolecta los datos del portal, genera archivos JSON y vuelve a publicar el sitio. El usuario eligió publicarlo como link web en GitHub, frente a la alternativa de correrlo desde su PC.

## 7. Cómo funciona

### 7.1 Recolector de datos (Python)

**Configuración.** El archivo `config/legisladores.json` lista a los integrantes del bloque. Por cada uno guarda:
- Nombre tal como aparece en Autores, por ejemplo "Ferrero, Alejandra".
- Apellido para buscar.
- Opcional: alias y fecha de inicio del mandato.

**Integrantes del bloque: 18.** Confirmados por el usuario y verificados el 24/11/2026 en la página oficial https://legislaturacba.gob.ar/legisladores/, filtro "Unión Cívica Radical".

- Austin, Brenda Lis
- Bottasso, Gustavo Armando
- Bría, José Alberto
- Briner, Carlos Edgardo
- Carignano, Carlos Atilio
- Contrera, Inés Mercedes
- Ferrero, Alejandra
- Grich, Ariel Denis
- Gudiño, Daniela Soledad
- Gvozdenovich, Matías Pablo
- Jaimes, Mauricio Sebastián
- Luna, Fernando Javier
- Molina, Víctor Eduardo
- Nicolás, Miguel Osvaldo
- Nigro, Alfredo Mariano
- Saliba, Oscar Elías Mario
- Szpanin, Ariela Yanina
- Valiente, Lucas Germán

Notas sobre la lista:
- La página oficial también indica quiénes son legisladores **departamentales**: Valiente, Nigro, Jaimes, Luna, Saliba, Grich, Briner, Molina y Carignano. Ese dato se puede mostrar en el perfil de cada uno.
- **Decisión de Claude:** el recolector lee esa página una vez por semana y, si la composición del bloque cambia, lo avisa en el resumen de la corrida. No modifica la lista solo; el usuario confirma cada cambio editando `config/legisladores.json`.
- El portal escribe los nombres sin tildes, por ejemplo "Bria, Jose Alberto". La comparación debe ignorar tildes y mayúsculas.

**Descubrimiento de expedientes.**
1. Por cada legislador, buscar su apellido.
2. Por cada resultado del período vigente del mandato (desde el período 146, año 2024), consultar Autores.
3. Si el legislador figura entre los autores, el expediente queda incluido.

**Actualización diaria.**
- Re-consultar la Ruta de los expedientes que **no** están en un estado final: aprobado, rechazado, archivado o caduco.
- Buscar expedientes nuevos revisando las primeras páginas de resultados de cada apellido, o con otro método más eficiente si el builder lo encuentra.
  - Por ejemplo, los Asuntos Entrados de las sesiones nuevas.

**Cortesía con el portal.**
- Como máximo 1 consulta por segundo.
- User-Agent identificable y genérico.
- Reintentos con espera.
- La primera carga completa puede tardar; las siguientes deben ser incrementales.

**Salida.** Un JSON por expediente, más un índice:
- `data/expedientes/<id>.json`: número, tipo, extracto, autores, comisiones, eventos `[{tipo: Estado|Situación, valor, sesión, período, fecha}]`, links a documentos y fecha de recolección.
- `data/indice.json`: resumen liviano para la portada.
- `data/novedades.json`: cambios detectados en los últimos 30 días.

**Historial.** El repositorio guarda el historial de cambios a través de los commits del JSON. Así se puede saber cuándo se detectó cada movimiento.

**Si algo falla.** Si el portal cambia o falla, la corrida termina con error visible en GitHub Actions y **no** publica datos vacíos. El sitio sigue mostrando los datos anteriores con su fecha.

### 7.2 Traducción a lenguaje simple

Una tabla de mapeo, `config/etapas.json`, convierte los estados del portal en **4 etapas** que entiende cualquiera:

| Etapa visible | Qué la marca en el portal |
|---|---|
| 1. Presentado | Ingresado, Estado Parlamentario |
| 2. En estudio en comisión | En Comisión |
| 3. Con dictamen de comisión | la sección Despachos tiene al menos un documento |
| 4. Resultado | **Aprobado** (en sesión X) · **Caducó** (sin tratamiento en 12 meses) · **Archivado** |

Reglas de la tabla:
- **Rehabilitado** devuelve el proyecto a la etapa 2. En la línea de tiempo se lee "Se rehabilitó: vuelve a estar en comisión".
- **Sobre tablas** se muestra como un salto directo de la etapa 1 a la 4, con una nota explicativa.
- Si aparece un valor que la tabla no conoce, se muestra tal cual y queda registrado, para ampliar el mapeo después.

**Estados finales para la actualización diaria:** Aprobado y Archivado. Caducado no es final, porque el proyecto puede rehabilitarse. A los caducados se los re-consulta una vez por semana, no todos los días.

**Leyes.** La herramienta las sigue hasta "Aprobado". La promulgación o el veto del Poder Ejecutivo quedan fuera de la primera versión.

**Glosario.** Cada término técnico tiene una explicación corta en un botón "¿Qué significa?". Los términos son: estado parlamentario, giro a comisión, despacho, sobre tablas, Art. 110, caducidad y tipos de proyecto.

**Tipos de proyecto en lenguaje simple:**
- **Ley.**
- **Resolución:** suele ser un pedido de informes al Ejecutivo.
- **Declaración:** beneplácito o adhesión.
- **Nota** y **Cuestión de privilegio:** se agrupan en "Otros".

### 7.3 Interfaz

**Principios:**
- Primero el panorama, el detalle a pedido.
- Pensada primero para el celular.
- Sin jerga.
- Siempre se ve la fecha de actualización.

**Portada / "Mis proyectos".**
- Elegir legislador. La elección se recuerda en el navegador y el link es compartible, por ejemplo `?leg=ferrero`.
- Cuatro tarjetas resumen: **Novedades** (últimos 7 días), **Por caducar** (en comisión y a menos de 60 días de cumplir 12 meses), **En comisión** y **Aprobados este año**. Al tocar una tarjeta se filtra la lista.
  - Cada proyecto en comisión muestra además "caduca en N días".
  - Los caducados quedan en un filtro aparte, con una explicación de qué significa y de cómo se rehabilita un proyecto.
- Pestañas: **Leyes y resoluciones** (por defecto), **Declaraciones** y **Otros**.
- Buscador de texto.
- Lista de tarjetas. Cada una muestra tipo, título corto (extracto recortado), número, barra de 5 etapas y último movimiento en lenguaje simple con fecha relativa ("hace 6 días").
- Orden: primero lo que tiene novedades, después por último movimiento.

**Ficha del proyecto.**
- Extracto completo.
- Barra de etapas.
- **Línea de tiempo** vertical en lenguaje simple, con la fecha y la sesión de cada paso.
- Autores y coautores; los del bloque, destacados.
- Comisiones.
- Documentos: despachos, actas y texto aprobado, con link al original.
- Link "Ver en el portal oficial".

**Vista del bloque.** La misma interfaz sobre todos los proyectos del bloque, con un filtro por legislador y por comisión.

**Pantalla "¿Cómo funciona un proyecto?".** Un diagrama simple de las etapas y el glosario.

**Accesibilidad.**
- Contraste suficiente.
- Texto legible.
- Funciona en modo claro y oscuro.
- No depende solo del color para indicar el estado: el color va acompañado de ícono y texto.

**Identidad visual.** Sobria e institucional. Puede usar el rojo y blanco radical como acento, pero **no** imita el logo ni la marca oficial de la Legislatura.

### 7.4 Publicación

- Repositorio en GitHub con el código del recolector, la configuración y el sitio estático.
- GitHub Actions corre todos los días hábiles a las 7:00, hora de Argentina, y se puede disparar a mano.
- GitHub Pages sirve el sitio y el link se comparte con el bloque.
- Los datos son públicos, así que el sitio puede ser público.
- **Dueño y responsable:** quien administra la cuenta de GitHub es dueño del repositorio y lo gestiona; la guía MANTENIMIENTO.md explica las tareas habituales.
- **Si una actualización falla:** GitHub le avisa por mail al usuario. El sitio muestra un aviso visible de "datos desactualizados desde <fecha>" cuando la última actualización exitosa tiene más de 2 días hábiles.
- Se incluye una guía corta en castellano (`MANTENIMIENTO.md`) que explica cómo agregar o quitar un legislador, cómo forzar una actualización y qué hacer si falla.

## 8. Decisiones tomadas por Claude (el usuario puede corregirlas)

- Alcance temporal: desde el período 146 (2024), el inicio del mandato actual.
- "Por caducar" significa a menos de 60 días de la caducidad. El valor se puede cambiar en la configuración. Reemplaza la idea anterior de "parado más de 6 meses", porque el portal ya marca la caducidad a los 12 meses.
- **Primer paso del builder: verificar que el portal responde desde los servidores de GitHub Actions.**
  - Si los bloquea, se frena y se le consulta al usuario antes de cambiar el diseño. No se agrega en silencio un proxy pago ni una PC prendida.
- La primera carga completa puede repartirse en varias corridas, guardando el progreso en el repositorio.
- Sitio estático sin backend y sin login.
- Python para el recolector y HTML/CSS/JS liviano para el sitio. Si el builder lo prefiere, puede usar un generador estático simple.
- "Participar" en la primera versión equivale a ser autor o coautor.

## 9. Lo que queda a criterio del builder

- Estrategia exacta de descubrimiento incremental: búsqueda por apellido, Asuntos Entrados o una combinación.
- Si conviene usar el postback de Comisiones o extraer las comisiones de la Ruta o del acta.
- La estructura interna del JSON, siempre que cubra lo descripto en 7.1.
- El framework o la ausencia de framework en el frontend, la tipografía y los detalles visuales dentro de los principios de 7.3.
- Los tests del parser con HTML de ejemplo guardado del portal.
