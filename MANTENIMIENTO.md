# Guía de mantenimiento

Esta guía explica cómo mantener el sitio de seguimiento de proyectos. Todo se hace desde la web de GitHub; no hace falta instalar nada.

## Cómo funciona

1. Todos los días hábiles a las 7:00, GitHub corre el **recolector**. Es un programa que consulta el portal de la Legislatura, en https://gld.legislaturacba.gob.ar.
2. El recolector busca los proyectos de cada legislador del bloque y guarda los datos en la carpeta `sitio/data`.
3. Después se publica el sitio con los datos nuevos.

En un día normal se revisan:
- los proyectos con estado parlamentario de los **últimos 45 días**, para encontrar los nuevos;
- todos los proyectos que siguen en trámite, para ver si se movieron.

Los lunes, además:
- se revisan los caducados, por si alguno se rehabilitó;
- se compara la lista del bloque con la página oficial de legisladores.

## Ver cómo salió la última actualización

1. En el repositorio, entrá a la pestaña **Actions** y abrí **actualizar**.
2. Cada corrida aparece en verde si salió bien o en rojo si falló.
3. Al abrir una corrida, el **resumen** muestra las advertencias.

Si una corrida falla, GitHub te manda un mail. Mientras tanto, el sitio sigue mostrando los datos anteriores. Si pasan más de 2 días hábiles sin una actualización completa, el sitio muestra arriba un aviso de "datos desactualizados".

## Forzar una actualización

1. Entrá a **Actions → actualizar → Run workflow**.
2. Marcá **completo** si querés recorrer todo el mandato. Se usa para la **primera carga** o si sospechás que falta algún proyecto. Tarda varias horas.
3. Si la corrida se corta por tiempo, volvé a lanzarla. Continúa desde donde quedó.

## Agregar o quitar un legislador

1. Abrí `config/legisladores.json` y tocá el lápiz (**Edit this file**).
2. Para **quitar** a alguien, borrá su renglón completo. Cuidá las comas: el último renglón no lleva coma al final.
3. Para **agregar** a alguien, copiá un renglón y cambiá los datos:
   - `slug`: el apellido en minúsculas, sin tildes ni espacios. Va en la dirección de su página.
   - `id_portal`: el número interno del portal. Para obtenerlo, abrí `https://gld.legislaturacba.gob.ar/Handlers/Persona.ashx?term=APELLIDO` y copiá el `id` que corresponde.
   - `nombre_portal`: el nombre tal como lo escribe ese mismo listado, por ejemplo `"Ferrero, Alejandra"`.
   - `nombre_mostrar`: el nombre como querés que aparezca en el sitio, con tildes.
   - `departamental`: `true` si es legislador o legisladora departamental, `false` si no.
4. Tocá **Commit changes**. En la próxima actualización aparece en el sitio. Para que se carguen todos sus proyectos, corré una actualización **completa**.

## Qué significan las advertencias

| Advertencia | Qué hacer |
|---|---|
| **Nuevo en el bloque según la web oficial: …** | Alguien figura en el bloque en legislaturacba.gob.ar pero no en la configuración. Agregalo si corresponde. |
| **Ya no figura en el bloque según la web oficial: …** | Revisá si dejó el bloque y, si es así, quitalo. |
| **Estado desconocido en el portal: …** | El portal usó un estado nuevo. El sitio lo muestra tal cual. Para traducirlo, agregalo en `config/etapas.json`. |
| **se leyeron X de Y expedientes** | Ese día el portal no devolvió todos los resultados. Se reintenta solo en la próxima corrida. |
| **La corrida falló: …** | El portal no respondió o cambió su formato. Si se repite varios días, hay que revisar el programa. |
| **La corrida se cortó por tiempo** | Volvé a lanzarla: continúa desde donde quedó. |

## Ajustes

`config/ajustes.json` tiene los valores que se pueden cambiar:

- `dias_por_caducar` (60): cuántos días antes de caducar un proyecto aparece en "Por caducar".
- `dias_ventana_diaria` (45): cuántos días hacia atrás se buscan proyectos nuevos cada día.
- `dias_desactualizado` (2): días hábiles sin actualizar antes de mostrar el aviso.
- `desde_fecha` (2023-12-10): inicio del mandato. No se buscan proyectos anteriores a esta fecha.
- `pausa_segundos` (1.0): espera entre consultas, para no cargar el portal de la Legislatura.
