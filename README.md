# Clip Local

App local en español para convertir videos en clips verticales para TikTok, YouTube Shorts e Instagram Reels. No utiliza APIs de pago, créditos ni suscripciones.

## Iniciar

Desde esta carpeta:

```bash
./start.sh
```

Abre http://127.0.0.1:8000 en tu navegador. Para detenerla, presiona Ctrl+C en la terminal. Solo escucha conexiones desde tu computadora.

Si faltan dependencias o la instalación fue interrumpida:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./start.sh
```

Requiere Python 3.10 o posterior. Para los enlaces de YouTube se recomienda Node.js 20 o posterior; en este equipo ya hay Node.js. Las dependencias se instalan dentro de `.venv`. FFmpeg viene incluido mediante imageio-ffmpeg. La primera transcripción descarga el modelo multilingüe `base` de faster-whisper (aproximadamente 150 MB); luego se reutiliza desde `data/models`. No hay cargos por uso. La descarga necesita internet; el procesamiento usa CPU, disco y electricidad de tu equipo.

## Uso

1. Pega un enlace HTTPS de YouTube o selecciona un archivo local de hasta 2 GB.
2. Elige duración y cantidad de propuestas. Espera la transcripción local.
3. Abre un proyecto y selecciona una propuesta. Revisa el video y ajusta inicio y final.
4. Elige video completo con márgenes o recorte centrado, resolución y subtítulos.
5. Exporta y descarga el MP4 y el SRT. Sube el clip manualmente a tu red social.

El campo de texto permite reemplazar los subtítulos por un texto dividido en fragmentos cortos durante el corte. Los subtítulos aparecen pequeños en la parte inferior, con hasta dos líneas; su tamaño se adapta proporcionalmente a 720p y 1080p. La división dentro de cada segmento aproxima los tiempos según la longitud del texto. Si se deja vacío se conservan los segmentos y tiempos automáticos. Los clips se exportan uno por uno. Puedes borrar proyectos cuando no estén procesándose.

## Alcance y límites

La selección usa reglas sobre la transcripción, continuidad de voz y expresiones de gancho; no predice viralidad. No analiza rostros ni energía acústica en esta versión. Funciona mejor con videos hablados. Puede ofrecer menos propuestas que las solicitadas cuando no hay suficientes segmentos distintos. Los cortes manuales admiten hasta 180 segundos.

YouTube puede bloquear la descarga o exigir verificaciones. Usa videos propios o con los permisos adecuados, respetando las condiciones de acceso y descarga; si un enlace falla, utiliza el archivo original. No se eluden restricciones de acceso ni se solicita tu cuenta de YouTube.

Los videos, transcripciones y exportaciones quedan en `data/`. La obtención desde YouTube y la primera descarga del modelo usan internet. No se envía el audio a un servicio de transcripción. No hay alojamiento ni publicación automática. Si cierras el servidor durante una tarea, esta no se reanuda automáticamente: vuelve a crear el proyecto.

## Herramientas

Python, FastAPI, JavaScript, yt-dlp, FFmpeg y faster-whisper. Se cambió whisper.cpp por faster-whisper para evitar compilar y facilitar la instalación local en CPU. Se usan archivos JSON en lugar de SQLite para esta primera versión.

Referencias: [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [yt-dlp](https://github.com/yt-dlp/yt-dlp), [FFmpeg](https://ffmpeg.org/), [FastAPI](https://fastapi.tiangolo.com/).

## Pruebas

```bash
.venv/bin/pip install pytest httpx
.venv/bin/python -m pytest -q
```

## Validación realizada

Se comprobaron rutas de la API, rechazo de enlaces ajenos a YouTube, selección de cortes sin solapamiento y exportación real de un MP4 vertical con audio y subtítulos. También se ejecutó el flujo completo con voz sintética local y el modelo instalado: produjo transcripción y una propuesta de clip. No se ha validado un enlace real de YouTube ni la apariencia en un navegador.

La prueba completa de voz puede repetirse en Linux si están disponibles las bibliotecas del sistema `libflite` y su voz `slt`:

```bash
PYTHONPATH=. .venv/bin/python tests/check_voice_pipeline.py
```

No necesita descargar un video externo y elimina su proyecto temporal al terminar. La biblioteca PyAV se limita a versiones compatibles con faster-whisper para evitar un error en la lectura de audio.
