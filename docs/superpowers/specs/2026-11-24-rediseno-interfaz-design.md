# Rediseño de la interfaz — Diseño (corto)

Fecha: 2026-11-24 · Estado: aprobado por el usuario sobre maquetas navegables

## Para qué

La primera versión funciona, pero se ve demasiado simple: todo pesa igual, no tiene imagen de marca y los legisladores aparecen como una lista de nombres. El objetivo es una interfaz más trabajada, limpia y fácil de usar para cualquiera del bloque, que se reconozca como parte de la familia de la web pública del bloque (https://web-ucr-legisladores-cba.vercel.app).

## Decisiones del usuario

- **Misma familia que la web del bloque:**
  - logo oficial de la UCR;
  - rojo `#C8102E`;
  - tipografía Public Sans, servida desde el propio sitio;
  - banda gris `#F4F5F7` bajo la cabecera, pie oscuro `#1E1E1E` y radio de 4 px.
- **Aprobó las maquetas de las 5 pantallas:**
  1. **Elegir legislador:** tarjetas con foto, tipo de banca (distrito único o departamental), cantidad de proyectos, aviso en rojo "N caducan pronto" y buscador por nombre.
  2. **Panel del legislador:**
     - Banda con foto, cargo opcional, nombre y frase "Firmó N proyectos…".
     - 4 indicadores que funcionan como filtro.
     - **"Para atender"**, en dos columnas: a la izquierda "Caducan pronto si no se tratan", con cuenta regresiva en días; a la derecha "Novedades de la semana".
     - "Todos sus proyectos", con pestañas que muestran la cantidad (Leyes y resoluciones, Declaraciones, Otros, Caducados y archivados), buscador y orden ("Más recientes" o "Vencen antes").
     - **Cada fila** muestra:
       - tipo como etiqueta de color, número y comisión principal;
       - título y último movimiento;
       - a la derecha: etapa en palabras ("En comisión, paso 2 de 4"), línea de progreso sin etiquetas, vencimiento y fotos de los coautores del bloque ("con 3 del bloque y 2 más").
  3. **Ficha:**
     - Banda con miga de pan, tipo, número, extracto como título, estado en una etiqueta redondeada y ruta grande con fechas.
     - Debajo, dos columnas:
       - **Izquierda:** recorrido agrupado por año, más el vencimiento futuro, y documentos.
       - **Derecha:** recuadro rojo "Tiempo para tratarlo" si está en trámite, comisiones (con la principal marcada), autores del bloque con foto, otros autores y botón al portal oficial.
  4. **Todo el bloque:** 4 indicadores, tabla por legislador (proyectos, en comisión, por caducar, aprobados en el año y una barra de composición) y la lista con filtros por comisión y por legislador.
  5. **Cómo avanza un proyecto:** las 4 etapas dibujadas como la ruta, un gráfico del plazo de 12 meses que marca los últimos 60 días y el glosario en dos columnas.

## Decisiones de Claude (aceptadas con el "avanzá")

- **Fotos:** se copian una vez de la web del bloque a `sitio/fotos/<slug>.webp`, para que el sitio no dependa de otro servicio. Si falta una foto, se muestran las iniciales.
- **Cargo:** `config/legisladores.json` suma un campo opcional `cargo`. Solo Ferrero lo tiene: "Presidenta del bloque".
- **Celular:** todo pasa a una columna y "Para atender" va primero.
- **Autoría en la ficha:** se compara en el navegador con `nombre_portal` y `alias`, con la misma normalización que en Python. Ya no se reconstruye el nombre desde el que se muestra en pantalla. Esto resuelve una mejora menor que había quedado pendiente.
- **Modo oscuro:** se mantiene, con los mismos tokens oscurecidos.

## Fuera de alcance

- Cambios en la recolección de datos, más allá de agregar al índice lo que la interfaz necesita.
- Avisos por mail.

## Anti-objetivos

- Que se vea como un tablero genérico o pierda la claridad actual.
- Que la página tarde en cargar. Las fotos son livianas (webp de 256 px) y no se suman fuentes ni librerías externas.
