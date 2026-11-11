"""Verify actual native-run ZIP/video/watch-page artifacts. No model or network."""
from __future__ import annotations
import argparse
import base64
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import re
import struct
import subprocess
import zipfile
from PIL import Image

class CopyParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[];self.active=None;self.copy=[]
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if attrs.get('class') in ('rp-head','rp-body','rp-cta-link'):
            self.active=(tag,attrs);self.parts=[]
    def handle_data(self,data):
        if self.active:self.parts.append(data)
    def handle_endtag(self,tag):
        if self.active and self.active[0]==tag:
            self.copy.append((self.active[1].get('class'),''.join(self.parts),self.active[1].get('href')));self.active=None

def verify(directory):
    record=json.loads((directory/'verified.json').read_text())
    receipt=record['verification'];rev=record['revisions'][-1]
    payload=(directory/'handoff.zip').read_bytes()
    sha=lambda b:hashlib.sha256(b).hexdigest()
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        assert z.testzip() is None
        assert sha(z.read('index.html'))==rev['artifact_hash']==receipt['artifact_hash']
        assert json.loads(z.read('review.json'))==record
        assert json.loads(z.read('verification.json'))==receipt
        assert not any('key' in name.lower() for name in z.namelist())
        assert z.read('review.html') == (directory/'review.html').read_bytes()
        embedded_images = re.findall(rb'data:image/png;base64,([A-Za-z0-9+/=]+)', z.read('review.html'))
        assert sorted(sha(base64.b64decode(b, validate=True)) for b in embedded_images) == sorted(sha(z.read(n)) for n in z.namelist() if n.endswith('.png'))
        for line in z.read('SHA256SUMS.txt').decode().splitlines():
            digest, name = line.split('  ', 1)
            assert sha(z.read(name)) == digest
        images=[]
        for vp in record['source']['viewports']+receipt['viewports']:
            name=vp['screenshot'];blob=z.read(name)
            hashes=record['source_integrity']['image_hashes'] if name.startswith('source-') else receipt['image_hashes']
            assert sha(blob)==hashes[name]
            with Image.open(io.BytesIO(blob)) as image:
                image.load();assert image.size==(vp['width'],vp['height'])
                images.append({'name':name,'width':image.width,'height':image.height,'sha256':sha(blob)})
        parser=CopyParser();parser.feed(z.read('index.html').decode('utf-8'))
        elements={e['id']:e for v in record['source']['viewports'] if v['name']=='desktop' for e in v['elements']}
        contract=record['contract']
        expected=[('rp-head',elements[contract['headline_id']]['text'],None)]
        expected += [('rp-body',elements[eid]['text'],None) for eid in contract['body_ids']]
        expected += [('rp-cta-link',contract['cta_text'],contract['cta_destination'])]
        assert parser.copy==expected,'Exported copy and destination must exactly match approved captured selections'
    assert receipt['protocol'] == 2 and len(receipt['checks']) == 29 and len({c['id'] for c in receipt['checks']}) == 29
    assert all(c['status']=='pass' for c in receipt['checks'])
    video=directory/'demo-android.mp4';vb=video.read_bytes();offset=0;boxes=[]
    while offset+8<=len(vb):
        length,kind=struct.unpack_from('>I4s',vb,offset);boxes.append(kind.decode('ascii'));assert length>=8;offset+=length
    assert boxes.index('moov')<boxes.index('mdat')
    media=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','stream=codec_name,profile,width,height,pix_fmt,level:format=duration,size','-of','json',str(video)]))
    assert len(media['streams'])==1
    stream=media['streams'][0]
    assert stream['codec_name']=='h264' and stream['profile']=='Constrained Baseline' and stream['pix_fmt']=='yuv420p' and stream['level']==31
    assert float(media['format']['duration'])<90
    subprocess.run(['ffmpeg','-nostdin','-v','error','-i',str(video),'-f','null','-'],check=True,capture_output=True)
    page=(directory/'watch.html').read_text()
    embedded=re.search(r'data:video/mp4;base64,([A-Za-z0-9+/=]+)',page)
    assert embedded and base64.b64decode(embedded[1],validate=True)==vb
    assert '<script' not in page.lower() and 'media-src data:' in page
    return {'review_id':record['id'],'revision':rev['number'],'provider':rev['provider'],'model':rev['model'],'artifact_hash':rev['artifact_hash'],'checks_passed':len(receipt['checks']),'zip_bytes':len(payload),'zip_sha256':sha(payload),'copy_and_cta_exact':True,'images':images,'video':media,'video_sha256':sha(vb),'faststart':True,'full_decode_pass':True,'embedded_watch_bytes_match':True,'android_device_playback':'unverified'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);args=p.parse_args()
    proof=verify(args.directory)
    (args.directory/'artifact-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(proof,indent=2))
