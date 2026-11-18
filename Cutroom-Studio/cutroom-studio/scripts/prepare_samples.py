"""Generate editable sample metadata from real speech and video, never fixed clip lists."""
from pathlib import Path
from cutroom import media, schema, video, worker
import argparse

SAMPLES={
 'lunar':dict(title='The next trip to the Moon',type='Interview',credit='NASA / Goddard Space Flight Center',link='https://svs.gsfc.nasa.gov/14934/',poster=16.2),
 'galaxies':dict(title='How galaxies change',type='Science explainer',credit='NASA / Goddard Space Flight Center',link='https://svs.gsfc.nasa.gov/12676/',poster=21.3),
 'path':dict(title='Finding my way to space',type='Storytelling',credit='NASA / Johnson Space Center',link='https://archive.org/details/NASAAstronautBiographicalVideos',poster=53.2),
}

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--force',action='store_true'); args=parser.parse_args()
    prefs=schema.Prefs(length='short').model_dump(); index={}
    for id,meta in SAMPLES.items():
        print('Preparing',id,flush=True); source=media.SAMPLES/f'{id}.mp4'; metadata=source.with_suffix('.json')
        if args.force or not metadata.exists():
            last=[-5]
            def progress(n,stage):
                if int(n)-last[0]>=7: print(f'  {int(n)}% {stage}',flush=True); last[0]=int(n)
            data=worker.analyze_file(source,source,progress,prefs,sample=True)
            video.still(source,source.with_suffix('.jpg'),meta['poster'])
            media.store_analysis(metadata,data)
        else: data=media.read_analysis({'sample':id})
        worker.make_thumbs({'sample':id},data['candidates'])
        media.store_analysis(metadata,data)
        print(f"  {len(data['words'])} words, {len(data['candidates'])} candidates, {data['info']['speakers']} speakers",flush=True)
        index[id]=meta|dict(duration=data['info']['duration'],clip_count=len(data['candidates']),prefs=prefs)
        media.store_analysis(media.SAMPLES/'index.json',index)

if __name__=='__main__': main()
