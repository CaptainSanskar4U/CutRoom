"""Download pinned, public model weights; verify checksums before admitting them."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib, os, shutil, sys, tempfile, urllib.request
from pathlib import Path
from cutroom.config import MODELS

WHISPER='https://huggingface.co/Systran/faster-whisper-base/resolve/main/'
MINILM='https://huggingface.co/Xenova/all-MiniLM-L6-v2/resolve/main/'
CAMP='https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/3dspeaker_speech_campplus_sv_en_voxceleb_16k.onnx'
YU='https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx'
FILES={
 'whisper-base/config.json': (WHISPER+'config.json','56a6d8110d311f19c8f0471e562832c7527f146b567275bfca59fcf7c184da9a'),
 'whisper-base/model.bin': (WHISPER+'model.bin','d01c3014881c9c6f3133c182f3d2887eb6ca1c789a7538c5c007196857a0a6a9'),
 'whisper-base/tokenizer.json': (WHISPER+'tokenizer.json','fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab'),
 'whisper-base/vocabulary.txt': (WHISPER+'vocabulary.txt','34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913'),
 'minilm/tokenizer.json': (MINILM+'tokenizer.json','da0e79933b9ed51798a3ae27893d3c5fa4a201126cef75586296df9b4d2c62a0'),
 'minilm/model_quantized.onnx': (MINILM+'onnx/model_quantized.onnx','afdb6f1a0e45b715d0bb9b11772f032c399babd23bfc31fed1c170afc848bdb1'),
 'campplus.onnx': (CAMP,'357a834f702b80161e5b981182c038e18553c1f2ca752ed6cec2052365d4129b'),
 'face_detection_yunet.onnx': (YU,'8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4'),
}

def sha(path):
    with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

def get(root,key):
    url,checksum=FILES[key]; dest=root/key; dest.parent.mkdir(mode=0o755,parents=True,exist_ok=True)
    if dest.is_file() and sha(dest)==checksum: return key+' verified'
    temp=None
    try:
        with tempfile.NamedTemporaryFile(mode='wb',dir=dest.parent,prefix=dest.name+'.',delete=False) as output:
            temp=Path(output.name)
            req=urllib.request.Request(url,headers={'User-Agent':'Cutroom-Model-Bootstrap/1.0'})
            with urllib.request.urlopen(req,timeout=50) as source:
                max_size=200*1024**2; size=0
                while buf:=source.read(512*1024):
                    size+=len(buf)
                    if size>max_size: raise ValueError(f'Model is larger than expected: {key}')
                    output.write(buf)
        if sha(temp)!=checksum: raise ValueError(f'Checksum mismatch: {key}. Do not use the changed file.')
        os.chmod(temp,0o644); temp.replace(dest)
    finally:
        if temp: temp.unlink(missing_ok=True)
    return key+' installed'

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--dir',type=Path,default=MODELS); a=ap.parse_args()
    with ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(lambda key:get(a.dir,key),FILES): print(result,flush=True)

if __name__=='__main__': main()
