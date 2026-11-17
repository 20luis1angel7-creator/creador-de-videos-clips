import ctypes
import json
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
import app

speech = ctypes.CDLL('libflite.so.1')
speech.flite_init()
voice_lib = ctypes.CDLL('libflite_cmu_us_slt.so.1')
voice_lib.register_cmu_us_slt.restype = ctypes.c_void_p
voice = voice_lib.register_cmu_us_slt(None)
speech.flite_text_to_speech.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_char_p]
speech.flite_text_to_speech.restype = ctypes.c_float
pid = uuid.uuid4().hex
work = app.DATA / pid
work.mkdir()
try:
    with tempfile.TemporaryDirectory() as d:
        audio = Path(d) / 'voice.wav'
        text = 'How can you make better videos? The most important thing is to tell a complete story. Start with a question that makes people curious. Then explain one useful idea clearly. Never try to say everything at once. Give your audience one simple action they can take today. That is the secret to making a video people remember.'
        speech.flite_text_to_speech(text.encode(), voice, str(audio).encode())
        subprocess.run([app.FFMPEG,'-y','-f','lavfi','-i','color=c=blue:s=320x240:r=24','-i',str(audio),'-shortest','-c:v','libx264','-c:a','aac',str(work/'source.mp4')],check=True,capture_output=True)
    app.save(dict(id=pid,title='Prueba de voz sintética',status='queued',url='',length=15,count=2,segments=[],clips=[]))
    app.process(pid)
    p = app.read(pid)
    assert p['status']=='ready', p.get('message')
    assert len(p['segments']) > 0, p
    assert len(p['clips']) > 0, p
    print(json.dumps({'status':p['status'],'segments':len(p['segments']),'clips':len(p['clips']),'transcript':p['segments'][0]['text']},ensure_ascii=False))
finally:
    shutil.rmtree(work)
