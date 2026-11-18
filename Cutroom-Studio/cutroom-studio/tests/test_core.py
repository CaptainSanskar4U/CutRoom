from pathlib import Path
import copy, shutil, subprocess
import numpy as np
import pytest
from cutroom import schema, video, media

ROOT=Path(__file__).resolve().parents[1]

def test_ratio_dimensions_and_keyframes():
    assert video.output_size('9:16',1080)==(1080,1920)
    assert video.output_size('16:9',720)==(1280,720)
    assert video.output_size('1:1',480)==(480,480)
    assert video.output_size('4:5',720)==(720,900)
    assert video.output_size('16:9',2160)==(3840,2160)
    tr=[{'t':0.,'x':.15,'y':.5},{'t':1.,'x':.5,'y':.6},{'t':2.,'x':.8,'y':.5,'cut':True}]
    assert video.points_at(tr,.5)[0]==pytest.approx(.325)
    assert video.points_at(tr,1.7)[0]==pytest.approx(.5)
    assert video.points_at(tr,2)[0]==pytest.approx(.8)
    assert 'if(' in video.cv_expression(video.keyframes(tr,0,2.5),1)


def test_transcript_corrections_respect_cuts():
    words=[dict(i=0,s=1,e=1.5,t='Original'),dict(i=1,s=1.5,e=2,t='sentence.'),dict(i=2,s=3.1,e=3.4,t='Again.')]
    edit=schema.Edit(word_edits=[{'i':0,'t':'Fixed','s':1,'e':1.5}],cuts=[{'s':2,'e':3}]).model_dump()
    s=video.srt(words,1,4,edit)
    assert 'Fixed sentence.' in s and 'Original' not in s
    assert '00:00:01,100 --> 00:00:01,400' in s
    assert video.kept_ranges(1,4,[{'s':0,'e':2},{'s':1.7,'e':2.4},{'s':3,'e':10}])==[(2.4,3)]


def test_import_refuses_unsupported_urls():
    # Admission validation without making requests to any target.
    assert media.valid_import('https://upload.wikimedia.org/wikipedia/commons/example.mp4').hostname=='upload.wikimedia.org'
    for p in ['http://upload.wikimedia.org/file.mp4','https://unlisted.example/video.mp4','https://upload.wikimedia.org:444/a.mp4']:
        with pytest.raises(media.ImportErrorMessage): media.valid_import(p)


def test_sparse_and_visual_candidates_are_not_fake_scores():
    from cutroom import intelligence as ai
    p=schema.Prefs(length='short').model_dump()
    picks=ai.rank([],57,p,[{'t':9,'m':.1},{'t':30,'m':.5,'cut':True}])
    assert picks and picks[0]['mode']=='visual' and picks[0]['score'] is None
    assert all(0<=x['s']<x['e']<=57 for x in picks)
    words=media.read_analysis({'sample':'lunar'})['words']
    r=ai.rank(words,60.402,p)
    assert len(r)>=2 and len(r[0]['axes'])==9 and r[0]['reason'] and r[0]['description']


def frame(path,at):
    raw=subprocess.check_output(['ffmpeg','-v','error','-ss',str(at),'-i',str(path),'-an','-frames:v','1','-pix_fmt','rgb24','-f','rawvideo','pipe:1'])
    return np.frombuffer(raw,dtype=np.uint8).reshape(480,480,3).astype(np.int16)

@pytest.mark.skipif(not shutil.which('ffmpeg'),reason='FFmpeg is required for the render integration test')
def test_render_burns_words_and_preserves_timeline(tmp_path):
    source=media.source_file({'sample':'lunar'}); data=media.read_analysis({'sample':'lunar'})
    settings={'resolution':480,'quality':'standard'}
    clip={'start_at':0.08,'end_at':3.4,'edit':schema.Edit(ratio='1:1',framing='manual',crop_x=.78).model_dump()}
    cap=tmp_path/'cap.mp4'; plain=tmp_path/'plain.mp4'; ps=[]
    result=video.render(source,cap,data['info'],data,clip,settings,{},ps.append)
    assert ps and ps[-1]==1 and result['height']==480 and result['width']==480
    baseline=copy.deepcopy(clip); baseline['edit']['caption']['enabled']=False
    video.render(source,plain,data['info'],data,baseline,settings,{},lambda _:None)
    for at in [.44,1.04]:
        difference=np.abs(frame(cap,at)-frame(plain,at)); assert int((difference[340:416].max(axis=2)>55).sum())>130
        # Independent lossy H.264 encodes can differ slightly across the whole frame.
        assert difference[345:412].mean() > difference[:310].mean() + 1.2
        assert float(difference[:310].mean())<4.5
    assert video.inspect(cap)['duration']==pytest.approx(3.32,abs=.10)

@pytest.mark.skipif(not shutil.which('ffmpeg'),reason='FFmpeg is required for the audio alignment test')
def test_delayed_audio_is_not_shifted_to_start(tmp_path):
    import wave
    src=tmp_path/'delay.mp4'; wav=tmp_path/'extracted.wav'; out=tmp_path/'render.mp4'; wav2=tmp_path/'render.wav'
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i','testsrc2=s=320x180:r=30:d=2.5','-itsoffset','0.8','-f','lavfi','-i','sine=f=1000:r=16000:d=1.5','-c:v','libx264','-c:a','aac',str(src)],check=True)
    info=video.inspect(src); video.audio_extract(src,wav,info,lambda _:None)
    settings={'resolution':480,'quality':'standard'}
    clip={'start_at':.2,'end_at':2.1,'edit':schema.Edit(ratio='16:9',framing='fit').model_dump()}
    video.render(src,out,info,{'track':[],'words':[]},clip,settings,{},lambda _:None)
    video.audio_extract(out,wav2,video.inspect(out),lambda _:None)
    def tone_after(p):
        with wave.open(str(p),'rb') as w: a=np.abs(np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(int))
        return np.where(a>450)[0][0]/16000
    assert tone_after(wav)==pytest.approx(.8,abs=.065)
    assert tone_after(wav2)==pytest.approx(.6,abs=.065)
