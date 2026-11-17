import json
import subprocess
import time
import uuid

import pytest
from fastapi.testclient import TestClient
import app as mod


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, 'DATA', tmp_path)
    return TestClient(mod.app)


def test_rejects_external_urls_and_traversal(client):
    r = client.post('/api/projects', data={'url':'https://127.0.0.1/private'})
    assert r.status_code == 400
    assert client.get('/api/projects/not-an-id').status_code == 404
    assert client.post('/api/projects', data={'url':'https://youtube.com:bad/watch?v=test'}).status_code == 400
    assert client.post('/api/projects', data={'url':'https://youtu.be/test'}, headers={'Origin':'https://example.com'}).status_code == 403
    assert client.post('/api/projects', data={'url':'https://youtu.be/test', 'count':8}).status_code == 400


def test_selection_distinct_complete_ideas():
    segments = [{'start':i*5, 'end':i*5+4, 'text':'Cómo mejorar tu video. Una idea importante.'} for i in range(30)]
    clips = mod.select_clips(segments, 30, 3, 150)
    assert len(clips) == 3
    for a,b in zip(clips, clips[1:]):
        assert a['end'] <= b['start']
    assert mod.select_clips([], 30, 3, 100) == []


@pytest.mark.parametrize('resolution', [720, 1080])
def test_real_export_with_subtitles_and_delete(client, resolution):
    pid = uuid.uuid4().hex
    work = mod.DATA / pid
    work.mkdir()
    subprocess.run([mod.FFMPEG,'-y','-f','lavfi','-i','color=c=blue:s=320x240:d=3','-f','lavfi','-i','sine=frequency=440:duration=3','-c:v','libx264','-c:a','aac',str(work/'source.mp4')],check=True,capture_output=True)
    mod.save(dict(id=pid,title='Prueba',status='ready',duration=3,clips=[],segments=[dict(start=0,end=2.5,text='Hola, este es un clip de prueba.')]))
    assert client.get('/').status_code == 200
    assert client.post(f'/api/projects/{pid}/export',json={'start':2,'end':1}).status_code == 400
    response = client.post(f'/api/projects/{pid}/export',json={'start':0,'end':2,'subtitles':True,'resolution':resolution})
    assert response.status_code == 200
    for _ in range(100):
        p = mod.read(pid)
        if p.get('export_status') != 'processing':
            break
        time.sleep(.2)
    assert p['export_status'] == 'ready', p.get('export_message')
    cid = response.json()['id']
    import av
    with av.open(str(work/f'{cid}.mp4')) as video:
        assert (video.streams.video[0].width, video.streams.video[0].height) == (resolution, int(resolution*16/9))
        assert len(video.streams.audio) == 1
        frame = next(video.decode(video=0)).to_ndarray(format='rgb24')
        import numpy as np
        ys, xs = np.where((frame > 180).all(axis=2))
        assert len(ys), 'Los subtítulos deben estar visibles'
        h, w = frame.shape[:2]
        assert ys.min() > h * .80
        assert ys.max() < h * .94
        assert ys.max() - ys.min() < h * .09
        assert xs.max() - xs.min() < w * .80
    r = client.get(f'/api/projects/{pid}/files/{cid}.mp4',headers={'Range':'bytes=0-99'})
    assert r.status_code == 206
    assert len(r.content) == 100
    assert 'Hola' in client.get(f'/api/projects/{pid}/files/{cid}.srt').text
    assert client.delete(f'/api/projects/{pid}').status_code == 200
    assert not work.exists()


def test_short_subtitles_preserve_text_and_timing():
    text = 'Estos subtítulos deben aparecer divididos en bloques pequeños para que podamos leerlos cómodamente sin ocupar toda la pantalla del video.'
    segments = [dict(start=5, end=20, text=text)]
    cut = mod.Cut(start=0, end=25)
    cues = mod.subtitle_cues(segments, cut)
    assert len(cues) > 1
    assert ' '.join(t.replace('\n', ' ') for _, _, t in cues) == text
    for a, b, text in cues:
        assert 5 <= a < b <= 20
        assert len(text.split()) <= 6
        assert len(text.splitlines()) <= 2
        assert all(len(line) <= 24 for line in text.splitlines())
    assert all(a[1] <= b[0] + .001 for a, b in zip(cues, cues[1:]))
    clipped = mod.subtitle_cues(segments, mod.Cut(start=10, end=15))
    assert all(0 <= a < b <= 5 for a, b, _ in clipped)


def test_manual_subtitles_are_split_and_plain_text():
    cut = mod.Cut(start=2, end=20, text=' '.join(['palabra'] * 40) + r' {\an8} <b>fin</b>')
    cues = mod.subtitle_cues([], cut)
    assert len(cues) > 1
    assert all(0 <= a < b <= 18 for a, b, _ in cues)
    assert not any('{' in text or '\\' in text for _, _, text in cues)
    assert mod.subtitle_cues([], mod.Cut(start=0, end=2, text=' ')) == []
