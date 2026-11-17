# Plan de la app para crear clips

Estado: solo planificación. No se ha creado la app, instalado herramientas ni contratado servicios.

## Objetivo

Crear una app local, en español, donde pegues el enlace de un video de YouTube y obtengas propuestas de clips para TikTok, YouTube Shorts e Instagram Reels. Podrás revisarlos, ajustar sus cortes y descargarlos con subtítulos.

## Condición principal: sin servicios de pago

- El procesamiento se hará en tu computadora.
- No usaré APIs de pago, suscripciones, pruebas con cobro posterior, créditos de IA ni servidores de pago.
- No se pedirán tarjetas ni claves de servicios comerciales.
- Usaré herramientas gratuitas y de código abierto. Los modelos de voz se descargarán para ejecutarlos localmente.
- Esto evita cargos de servicios; sí utiliza tu electricidad, conexión a internet, almacenamiento y capacidad del equipo. No puedo prometer procesamiento rápido sin conocer sus características.
- Si alguna función requiere un servicio de pago, quedará fuera del proyecto.

## Cómo funcionará

1. Pegas un enlace de YouTube o eliges un archivo de video de tu computadora.
2. La app obtiene el video cuando su acceso y descarga estén permitidos. Si YouTube impide obtenerlo, podrás usar el archivo original; no se garantiza que todos los enlaces funcionen.
3. Extrae el audio y genera una transcripción con tiempos, localmente.
4. Analiza la transcripción, las pausas y la energía de la voz para proponer momentos interesantes.
5. Muestra entre 3 y 5 candidatos, según el contenido disponible, con título sugerido, duración y motivo de selección.
6. Revisas cada propuesta y puedes modificar el inicio, el final y el texto de los subtítulos.
7. Exportas los clips elegidos como MP4 vertical, con subtítulos opcionales, listos para subir manualmente.

## Qué significa seleccionar los mejores clips

La primera versión asignará una puntuación mediante reglas locales: frases que puedan funcionar como gancho, ideas completas, preguntas y respuestas, poca cantidad de silencios y variaciones de energía en la voz. Evitará proponer fragmentos casi iguales y procurará no cortar frases.

Estas señales producirán candidatos para que tú decidas. No garantizan viralidad ni equivalen al criterio de un editor humano. El resultado será más útil para entrevistas, podcasts, tutoriales y videos hablados; será más limitado con música, videojuegos sin narración o escenas cuyo interés sea principalmente visual.

## Herramientas previstas

| Herramienta | Para qué la usaré | Costo de servicio |
| --- | --- | --- |
| Python + FastAPI | Procesamiento, tareas y servidor local de la app | Sin pago |
| HTML, CSS y JavaScript | Interfaz en español que abrirás en tu navegador | Sin pago |
| yt-dlp | Intentar obtener videos de enlaces compatibles y autorizados | Sin pago |
| FFmpeg y ffprobe | Leer duración, extraer audio, recortar, adaptar a vertical e incorporar subtítulos | Sin pago |
| whisper.cpp con modelo multilingüe | Transcribir voz en tu equipo, incluido español | Sin pago por uso |
| SQLite y carpetas locales | Guardar proyectos, tiempos de clips y archivos generados | Sin pago |

La lista es una propuesta técnica. Antes de implementar comprobaré la compatibilidad con tu equipo y las licencias de los componentes elegidos. yt-dlp puede requerir un motor JavaScript compatible y componentes adicionales gratuitos, según sus requisitos vigentes.

## Primera versión

- Pantalla con entrada de enlace y opción para abrir un archivo local.
- Selección de cantidad de clips y duración deseada, inicialmente entre 15 y 60 segundos.
- Indicador de progreso y mensajes de error claros.
- Transcripción y selección automática de candidatos.
- Vista previa y ajuste manual de los tiempos de corte.
- Formato vertical 9:16; objetivo de exportación 1080 × 1920, con opción de 720 × 1280 para equipos modestos. La calidad dependerá del original.
- Elección entre recorte centrado y video completo sobre un fondo adaptado, para reducir la pérdida de contenido importante.
- Subtítulos legibles, editables y opcionales; exportación adicional en SRT.
- Descarga individual de los clips y opción para borrar los archivos del proyecto.

## Fuera de la primera versión

Publicación automática en redes, cuentas de usuarios, alojamiento en internet, seguimiento automático del rostro, edición multicámara y predicción de viralidad. Tampoco se usará un modelo de lenguaje grande al inicio: así se reducen los requisitos del equipo y las descargas.

## Pasos de construcción cuando me indiques que empiece

1. Revisar sistema operativo, memoria, espacio disponible y herramientas instaladas, sin contratar nada.
2. Crear la interfaz y el flujo de proyectos locales.
3. Integrar entrada de video, transcripción y selección de momentos.
4. Añadir vista previa, ajustes, subtítulos y exportación.
5. Probar con un video propio: comprobar cortes, sincronización, reproducción del MP4 y manejo de errores.
6. Entregar instrucciones para iniciar la app y limpiar archivos. Revisar que el flujo no dependa de servicios de pago.

## Límites prácticos

La transcripción y exportación pueden tardar bastante en una computadora sin GPU. El modelo de voz y los videos necesitan espacio; la cantidad depende del modelo, la duración y la resolución. La primera descarga del modelo y la obtención de videos requieren internet; el procesamiento de archivos ya disponibles se hará localmente.

La app se diseñará para uso personal desde tu computadora. Los enlaces se enviarán a YouTube al intentar obtener el video; el audio no se enviará a una API de transcripción. Se deben usar videos propios o con permisos adecuados y respetar las condiciones de acceso y descarga de YouTube.

## Referencias

- [yt-dlp: documentación y dependencias](https://github.com/yt-dlp/yt-dlp)
- [FFmpeg: documentación oficial](https://ffmpeg.org/documentation.html)
- [whisper.cpp: ejecución local y modelos](https://github.com/ggml-org/whisper.cpp)
- [Licencia de whisper.cpp](https://github.com/ggml-org/whisper.cpp/blob/master/LICENSE)
- [Condiciones de YouTube sobre acceso y descarga](https://www.youtube.com/static?template=terms)

Este documento describe lo que propongo hacer. La construcción queda pendiente de tu indicación.
