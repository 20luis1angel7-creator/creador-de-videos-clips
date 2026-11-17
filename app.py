import json
import re
import shutil
import subprocess
import threading
import textwrap
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
DATA.mkdir(exist_ok=True)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
@asynccontextmanager
async def lifespan(application):
    for f in DATA.glob('*/project.json'):
        p = json.loads(f.read_text())
        if p.get('status') in ('queued', 'processing'):
            p.update(status='error', message='La tarea se interrumpió al cerrar la app. Crea el proyecto de nuevo.')
        if p.get('export_status') == 'processing':
            p.update(export_status='error', export_message='La exportación se interrumpió. Puedes volver a exportar.')
        f.write_text(json.dumps(p, ensure_ascii=False))
    yield


app = FastAPI(title='Clip Local', lifespan=lifespan)
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', 'testserver'])


@app.middleware('http')
async def local_requests(request, call_next):
    origin = request.headers.get('origin')
    if request.method in ('POST', 'DELETE', 'PUT', 'PATCH') and origin and origin not in ('http://127.0.0.1:8000', 'http://localhost:8000'):
        return JSONResponse({'detail': 'Origen no permitido.'}, status_code=403)
    return await call_next(request)


pool = ThreadPoolExecutor(max_workers=1)
lock = threading.RLock()
model = None


def folder(pid):
    if not re.fullmatch(r'[a-f0-9]{32}', pid):
        raise HTTPException(404, 'Proyecto inexistente')
    p = DATA / pid
    if not (p / 'project.json').exists():
        raise HTTPException(404, 'Proyecto inexistente')
    return p


def read(pid):
    with lock:
        return json.loads((folder(pid) / 'project.json').read_text())


def save(p):
    with lock:
        dest = DATA / p['id'] / 'project.json'
        temp = dest.with_suffix('.tmp')
        temp.write_text(json.dumps(p, ensure_ascii=False))
        temp.replace(dest)


def update(pid, **fields):
    with lock:
        p = read(pid)
        p.update(fields)
        save(p)


def run(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=7200)
    if result.returncode:
        raise RuntimeError('No se pudo procesar el video. ' + result.stderr[-1200:])
    return result


def duration(video):
    import av
    with av.open(str(video)) as container:
        if container.duration:
            return container.duration / av.time_base
        stream = container.streams.video[0]
        return float(stream.duration * stream.time_base)


def select_clips(segments, length, count, total):
    candidates = []
    hooks = ('cómo', 'porque', 'por qué', 'secreto', 'error', 'mejor', 'nunca', 'imagina', 'consejo', '?', 'importante')
    for i, seg in enumerate(segments):
        start = max(0, seg['start'] - .15)
        end = min(total, start + length)
        inside = [s for s in segments[i:] if s['start'] < end]
        if not inside or end - start < 5:
            continue
        # End on a complete segment near the requested duration.
        endings = [s['end'] for s in inside if s['end'] <= end and s['end'] - start >= length * .65]
        if endings:
            end = endings[-1]
        text = ' '.join(s['text'].strip() for s in inside if s['end'] <= end + .1)
        if not text:
            continue
        spoken = sum(max(0, min(end, s['end']) - max(start, s['start'])) for s in inside)
        hook = sum(h in text.lower() for h in hooks)
        score = hook * 2 + spoken / max(1, end - start) * 5 + min(len(text.split()) / 60, 2)
        candidates.append(dict(start=round(start, 2), end=round(end, 2), title=' '.join(text.split()[:9]) + '…', reason='Idea con gancho y buena continuidad' if hook else 'Fragmento con voz continua', score=score))
    chosen = []
    for c in sorted(candidates, key=lambda c: c['score'], reverse=True):
        if all(max(0, min(c['end'], x['end']) - max(c['start'], x['start'])) == 0 for x in chosen):
            c.pop('score')
            c['id'] = uuid.uuid4().hex[:10]
            chosen.append(c)
        if len(chosen) >= count:
            break
    return sorted(chosen, key=lambda c: c['start'])


def process(pid):
    global model
    try:
        p = read(pid)
        work = folder(pid)
        if p.get('url'):
            update(pid, status='processing', message='Obteniendo el video de YouTube…')
            import yt_dlp
            # Only YouTube URLs are accepted, never playlists or arbitrary extractors.
            with yt_dlp.YoutubeDL({'format': 'best[ext=mp4]/best', 'outtmpl': str(work / 'source.%(ext)s'), 'noplaylist': True, 'max_filesize': 2 * 1024**3, 'quiet': True, 'js_runtimes': {'node': {'path': shutil.which('node')}} if shutil.which('node') else {}, 'socket_timeout': 30}) as ydl:
                info = ydl.extract_info(p['url'], download=True)
                video = Path(ydl.prepare_filename(info))
                update(pid, title=info.get('title', 'Video de YouTube'))
            video.rename(work / 'source.mp4')
        video = work / 'source.mp4'
        update(pid, status='processing', message='Preparando el video para la vista previa…')
        normalized = work / 'normalized.mp4'
        run([FFMPEG, '-y', '-i', str(video), '-map', '0:v:0', '-map', '0:a:0?', '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-movflags', '+faststart', str(normalized)])
        normalized.replace(video)
        total = duration(video)
        update(pid, duration=total, status='processing', message='Extrayendo el audio…')
        run([FFMPEG, '-y', '-i', str(video), '-vn', '-ac', '1', '-ar', '16000', str(work / 'audio.wav')])
        update(pid, message='Transcribiendo en tu equipo. La primera vez se descarga el modelo gratuito…')
        if model is None:
            import onnxruntime
            onnxruntime.disable_telemetry_events()
            from faster_whisper import WhisperModel
            snapshots = sorted((DATA / 'models' / 'models--Systran--faster-whisper-base' / 'snapshots').glob('*'))
            local = next((str(p) for p in snapshots if (p / 'model.bin').exists() and (p / 'config.json').exists() and (p / 'tokenizer.json').exists()), 'base')
            model = WhisperModel(local, device='cpu', compute_type='int8', cpu_threads=4, download_root=str(DATA / 'models'))
        result, _ = model.transcribe(str(work / 'audio.wav'), beam_size=3, vad_filter=True)
        segments = []
        for s in result:
            segments.append({'start': s.start, 'end': s.end, 'text': s.text.strip()})
        clips = select_clips(segments, p['length'], p['count'], total)
        update(pid, status='ready', message='Revisa tus propuestas y exporta las que prefieras.' if clips else 'No se detectó suficiente voz. Puedes crear un corte manual.', segments=segments, clips=clips)
        (work / 'audio.wav').unlink(missing_ok=True)
    except Exception as e:
        update(pid, status='error', message=str(e)[:1500])


@app.get('/')
def index():
    return FileResponse(ROOT / 'static/index.html')


@app.get('/api/projects')
def projects():
    result = []
    for f in DATA.glob('*/project.json'):
        p = read(f.parent.name)
        result.append({k: v for k, v in p.items() if k != 'segments'})
    return result[::-1]


@app.post('/api/projects')
async def create(url: str = Form(''), length: int = Form(30), count: int = Form(3), file: UploadFile | None = File(None)):
    if not 15 <= length <= 60 or not 1 <= count <= 5:
        raise HTTPException(400, 'Elige duración de 15 a 60 segundos y de 1 a 5 clips.')
    if not file and not url:
        raise HTTPException(400, 'Añade un enlace o un archivo.')
    if url and not file:
        try:
            parsed = urlparse(url)
        except ValueError:
            raise HTTPException(400, 'El enlace no es válido.')
        if parsed.scheme != 'https' or parsed.netloc not in ('youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be'):
            raise HTTPException(400, 'Usa un enlace HTTPS de YouTube.')
    pid = uuid.uuid4().hex
    work = DATA / pid
    work.mkdir()
    p = dict(id=pid, title=file.filename if file else 'Video de YouTube', url='' if file else url, status='queued', message='Esperando turno…', length=length, count=count, clips=[], segments=[])
    save(p)
    if file:
        size = 0
        with (work / 'source.mp4').open('wb') as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > 2 * 1024**3:
                    shutil.rmtree(work)
                    raise HTTPException(413, 'El archivo supera 2 GB.')
                out.write(chunk)
    pool.submit(process, pid)
    return p


@app.get('/api/projects/{pid}')
def project(pid: str):
    return read(pid)


class Cut(BaseModel):
    start: float = Field(ge=0, allow_inf_nan=False)
    end: float = Field(gt=0, allow_inf_nan=False)
    layout: str = 'fit'
    subtitles: bool = True
    text: str | None = None
    resolution: int = 720


def timestamp(t):
    ms = round(max(0, t) * 1000)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'


def subtitle_cues(segments, cut):
    """Split before clipping so partial cuts retain their original timing."""
    source = segments if cut.text is None else [dict(start=cut.start, end=cut.end, text=cut.text)]
    cues = []
    for seg in source:
        if seg['end'] <= cut.start or seg['start'] >= cut.end:
            continue
        # Strip formatting/control characters: user text must stay plain text.
        words = re.sub(r'[\\{}<>]', '', seg['text']).split()
        groups, group = [], []
        for word in words:
            if group and (len(group) >= 6 or len(' '.join(group + [word])) > 36):
                groups.append(' '.join(group))
                group = []
            group.append(word)
        if group:
            groups.append(' '.join(group))
        blocks = []
        for group in groups:
            lines = textwrap.wrap(group, width=24)
            blocks.extend('\n'.join(lines[i:i+2]) for i in range(0, len(lines), 2))
        weight = sum(len(b) for b in blocks)
        cursor = seg['start']
        for block in blocks:
            end = min(seg['end'], cursor + (seg['end']-seg['start']) * len(block) / weight)
            a, b = max(cursor, cut.start), min(end, cut.end)
            if b - a >= .01:
                cues.append((a-cut.start, b-cut.start, block))
            cursor = end
    return cues


def ass_subtitles(cues):
    # Explicit portrait script resolution keeps font and margins proportional
    # at both 720p and 1080p; alignment 2 anchors text at the bottom.
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,28,&H00FFFFFF,&H00FFFFFF,&H00111111,&H00000000,0,0,0,0,100,100,0,0,1,1.5,0,2,55,55,100,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def clock(t):
        cs = round(max(0, t) * 100)
        h, cs = divmod(cs, 360000)
        m, cs = divmod(cs, 6000)
        sec, cs = divmod(cs, 100)
        return f'{h}:{m:02}:{sec:02}.{cs:02}'
    rows = []
    for a, b, text in cues:
        plain = text.replace('\n', r'\N')
        rows.append(f'Dialogue: 0,{clock(a)},{clock(b)},Default,,0,0,0,,{plain}')
    return header + '\n'.join(rows) + '\n'


def render(pid, cid, cut):
    try:
        p = read(pid)
        work = folder(pid)
        cues = subtitle_cues(p['segments'], cut)
        srt = work / f'{cid}.srt'
        srt.write_text('\n\n'.join(f'{i+1}\n{timestamp(a)} --> {timestamp(b)}\n{t}' for i, (a,b,t) in enumerate(cues)), encoding='utf-8')
        ass = work / f'{cid}.ass'
        ass.write_text(ass_subtitles(cues), encoding='utf-8')
        w = cut.resolution
        h = int(w * 16 / 9)
        if cut.layout == 'crop':
            vf = f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1'
        else:
            vf = f'scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x111320,setsar=1'
        if cut.subtitles and cues:
            vf += f",ass={ass}"
        run([FFMPEG, '-y', '-ss', str(cut.start), '-i', str(work/'source.mp4'), '-t', str(cut.end-cut.start), '-vf', vf, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-movflags', '+faststart', str(work/f'{cid}.mp4')])
        update(pid, export_status='ready', export_id=cid, export_message='Tu clip está listo para descargar.')
    except Exception as e:
        update(pid, export_status='error', export_message=str(e)[:1500])


@app.post('/api/projects/{pid}/export')
def export(pid: str, cut: Cut):
    with lock:
        p = read(pid)
        if p['status'] != 'ready' or p.get('export_status') == 'processing':
            raise HTTPException(409, 'Espera a que termine el procesamiento actual.')
        if cut.end <= cut.start or cut.end > p['duration'] + .1 or cut.end-cut.start > 180:
            raise HTTPException(400, 'Revisa los tiempos: máximo 180 segundos y dentro del video.')
        if cut.layout not in ('fit', 'crop') or cut.resolution not in (720, 1080):
            raise HTTPException(400, 'Formato no válido.')
        cid = uuid.uuid4().hex
        update(pid, export_status='processing', export_message='Exportando el clip en tu equipo…', export_id=cid)
        pool.submit(render, pid, cid, cut)
    return {'id': cid}


@app.get('/api/projects/{pid}/files/{name}')
def media(pid: str, name: str, download: bool = False):
    if not re.fullmatch(r'(source|[a-f0-9]{32})\.(mp4|srt)', name):
        raise HTTPException(404)
    path = folder(pid) / name
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path, filename=name if download else None)


@app.delete('/api/projects/{pid}')
def delete(pid: str):
    with lock:
        p = read(pid)
        if p['status'] in ('queued', 'processing') or p.get('export_status') == 'processing':
            raise HTTPException(409, 'Espera a que termine antes de borrar.')
        shutil.rmtree(folder(pid))
    return {'ok': True}
