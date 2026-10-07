"""Synthetic package/contract fixtures live only in TemporaryDirectory.
They exercise verifier invariants, not presentation rendering or image semantics.
"""
import base64
import copy
import datetime as dt
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
import zipfile

SCRIPT = Path(__file__).resolve().parents[1]/'scripts/verify_visual_contract.py'
spec = importlib.util.spec_from_file_location('verifier', SCRIPT)
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aL1sAAAAASUVORK5CYII=')


class ContractTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ref('outline.md', b'approved content'); self.ref('style.md', b'corporate style'); self.ref('asset.png', PNG)
        self.c = {'schema_version':1,'canvas':[1000,600],
                  'outline':dict(self.ref('outline.md'),approval_ref='user decision current task'),
                  'style':{'source':self.ref('style.md'),'palette':{'accent':'#A50C0B'}},
                  'assets':[dict(self.ref('asset.png'),id='visual',origin='reused')],
                  'slides':[{'id':'s1','message':'Approved process','reading_order':'left-to-right','visual_form':'diagram','text_mode':'integrated_native',
                             'placements':[{'asset_id':'visual','box':[100,100,800,200],'fit':'contain'}],
                             'labels':[{'id':'gate','text':'Human gate','box':[350,310,200,40],'asset_id':'visual','component_id':'review','component_box':[350,200,200,100]}]}]}
        self.path=self.root/'contract.json';self.write()

    def ref(self, name, data=None):
        p=self.root/name
        if data is not None: p.write_bytes(data)
        return {'path':name,'sha256':v.digest(p.read_bytes())}

    def write(self): self.path.write_text(json.dumps(self.c),encoding='utf-8')
    def check(self, stage='plan'): self.write();return v.verify(self.path,stage)
    def review(self,name,subject,checks):
        return self.ref(name,json.dumps({'plan_sha256':v.plan_hash(self.c),'subject_sha256':subject,'reviewer':'fixture reviewer','reviewed_at':dt.datetime.now(dt.timezone.utc).isoformat(),'notes':'Synthetic evidence, not a real visual acceptance','checks':dict.fromkeys(checks,'pass')}).encode())

    def accepted_assets(self):
        self.c['evidence']={'asset_reviews':{'visual':self.review('asset-review.json',self.c['assets'][0]['sha256'],['subject','style','placement','textless','mapping','text_accuracy'])}}
        gate=self.check('assets'); self.assertTrue(gate['ok'],gate)
        self.c['evidence']['assembly_gate']=self.ref('gate.json',json.dumps(gate).encode())
        self.c['evidence']['build_started_at']=dt.datetime.now(dt.timezone.utc).isoformat()

    def package(self, text='Human gate', image=PNG, x=350, image_x=100):
        p='http://schemas.openxmlformats.org/presentationml/2006/main';a='http://schemas.openxmlformats.org/drawingml/2006/main';r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
        xf=lambda x,y,w,h:f'<a:xfrm><a:off x="{x*9525}" y="{y*9525}"/><a:ext cx="{w*9525}" cy="{h*9525}"/></a:xfrm>'
        with zipfile.ZipFile(self.root/'deck.pptx','w') as z:
            z.writestr('ppt/presentation.xml',f'<p:presentation xmlns:p="{p}" xmlns:r="{r}"><p:sldIdLst><p:sldId id="256" r:id="r1"/></p:sldIdLst><p:sldSz cx="9525000" cy="5715000"/></p:presentation>')
            z.writestr('ppt/_rels/presentation.xml.rels','<Relationships><Relationship Id="r1" Target="slides/slide1.xml"/></Relationships>')
            z.writestr('ppt/slides/slide1.xml',f'<p:sld xmlns:p="{p}" xmlns:a="{a}" xmlns:r="{r}"><p:cSld><p:spTree><p:sp><p:spPr>{xf(x,310,200,40)}</p:spPr><p:txBody><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:txBody></p:sp><p:pic><p:blipFill><a:blip r:embed="im1"/></p:blipFill><p:spPr>{xf(image_x,100,800,200)}</p:spPr></p:pic></p:spTree></p:cSld></p:sld>')
            z.writestr('ppt/slides/_rels/slide1.xml.rels','<Relationships><Relationship Id="im1" Target="../media/image1.png"/></Relationships>')
            z.writestr('ppt/media/image1.png',image)
        self.c['evidence']['final']={'pptx':self.ref('deck.pptx'),'renders':[dict(self.ref('render.png',PNG),slide_id='s1',pptx_sha256=self.ref('deck.pptx')['sha256'],review=self.review('render-review.json',v.digest(PNG),['content','style','legibility','mapping','text_accuracy']))]}

    def test_valid_all_phases(self):
        self.assertTrue(self.check()['ok']);self.accepted_assets();self.package();self.assertTrue(self.check('final')['ok'])
    def test_embedded_mode(self):
        s=self.c['slides'][0];s.update(text_mode='embedded_text',labels=[],embedded_text=['Human gate'],editable_visual_text=False)
        self.accepted_assets();self.package();self.assertTrue(self.check('final')['ok'])
    def test_native_no_assets(self):
        self.c['assets']=[];s=self.c['slides'][0];s.update(text_mode='native',placements=[]);self.c['evidence']={}
        self.assertTrue(self.check('assets')['ok'])
    def test_bad_plans(self):
        base=copy.deepcopy(self.c)
        changes=[lambda c:c['slides'][0]['labels'][0].update(box=[0,500,200,40]),lambda c:c['slides'][0]['labels'][0].update(box=[-1,0,10,10]),lambda c:c['slides'][0]['labels'][0].update(component_box=[0,0,10,10]),lambda c:c['canvas'].__setitem__(0,float('nan')),lambda c:c['slides'].append(copy.deepcopy(c['slides'][0])),lambda c:c['assets'][0].update(path='../escape.png'),lambda c:c['slides'][0].update(text_mode='embedded_text',editable_visual_text=True,embedded_text=['x']),lambda c:c['slides'][0].update(visual_form='chart',chart_mode='image',editable_data=True)]
        for change in changes:
            with self.subTest(change=change):
                self.c=copy.deepcopy(base);change(self.c);self.assertFalse(self.check()['ok'])
    def test_connector_resolves_plan_gap(self):
        l=self.c['slides'][0]['labels'][0];l.update(box=[350,500,200,40],connector=[[450,250],[450,520]])
        self.assertTrue(self.check()['ok'])
    def test_missing_final_connector(self):
        l=self.c['slides'][0]['labels'][0];l['connector']=[[450,250],[450,330]]
        self.accepted_assets();self.package();self.assertFalse(self.check('final')['ok'])
    def test_missing_review(self): self.assertFalse(self.check('assets')['ok'])
    def test_tampered_asset(self):
        self.accepted_assets();(self.root/'asset.png').write_bytes(b'changed');self.assertFalse(self.check('assets')['ok'])
    def test_stale_plan(self):
        self.accepted_assets();self.c['slides'][0]['labels'][0]['text']='Changed gate';self.assertFalse(self.check('assets')['ok'])
    def test_pending_semantic_review(self):
        self.accepted_assets();r=json.loads((self.root/'asset-review.json').read_text());r['checks']['mapping']='pending'
        self.c['evidence']['asset_reviews']['visual']=self.ref('asset-review.json',json.dumps(r).encode());self.assertFalse(self.check('assets')['ok'])
    def test_before_gate(self):
        self.accepted_assets();self.package();self.c['evidence']['build_started_at']='2000-01-01T00:00:00Z';self.assertFalse(self.check('final')['ok'])
    def test_final_negative_cases(self):
        for args in [{'text':'Wrong'}, {'image':b'changed'}, {'x':100}, {'image_x':150}]:
            with self.subTest(args=args):
                self.accepted_assets();self.package(**args);self.assertFalse(self.check('final')['ok'])
    def test_missing_gate(self):
        self.accepted_assets();self.package();del self.c['evidence']['assembly_gate'];self.assertFalse(self.check('final')['ok'])
    def test_stale_render(self):
        self.accepted_assets();self.package();self.c['evidence']['final']['renders'][0]['pptx_sha256']='0'*64;self.assertFalse(self.check('final')['ok'])
    def test_symlink_escape(self):
        with tempfile.TemporaryDirectory() as other:
            outside=Path(other)/'file';outside.write_text('outside');(self.root/'link').symlink_to(outside)
            self.c['outline']=dict(path='link',sha256=v.digest(b'outside'),approval_ref='approved');self.assertFalse(self.check()['ok'])

    def test_invalid_near_connector(self):
        self.c['slides'][0]['labels'][0]['connector']=[[0,0],[0,0]]
        self.assertFalse(self.check()['ok'])

    def test_cli_receipt_and_exit_codes(self):
        receipt=self.root/'receipt.json'
        cmd=[sys.executable,str(SCRIPT),str(self.path),'--stage','plan','--out',str(receipt)]
        first=subprocess.run(cmd,capture_output=True,text=True)
        self.assertEqual(first.returncode,0,first.stdout)
        original=receipt.read_bytes()
        self.assertTrue(json.loads(original)['ok'])
        self.assertEqual(subprocess.run(cmd,capture_output=True).returncode,1)
        self.assertEqual(receipt.read_bytes(),original)
        self.c['slides']=[];self.write()
        failed=subprocess.run(cmd[:-2],capture_output=True,text=True)
        self.assertEqual(failed.returncode,1)
        self.assertFalse(json.loads(failed.stdout)['ok'])


if __name__=='__main__': unittest.main()
