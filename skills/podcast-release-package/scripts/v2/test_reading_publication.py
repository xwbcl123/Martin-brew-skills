"""Reading publication is full grounded prose; subtitles stay canonical."""
import copy
import unittest
import test_package as f
p=f.pkg
class ReadingTests(unittest.TestCase):
 def setUp(self):
  self.ep={'publication_transcript':dict(p.READING_PUBLICATION)}
  self.segs=[{'id':0,'text':'um A'},{'id':1,'text':'uh B'}]
  self.content={'reading_transcript':[{'text':'First readable paragraph.','source_segment_ids':[0]},{'text':'第二段。','source_segment_ids':[1]}]}
 def test_full_paragraphs_and_legacy(self):
  self.assertEqual(p.publication_text(self.ep,self.content,self.segs),'First readable paragraph.\n\n第二段。')
  self.assertEqual(p.publication_text({},self.content,self.segs),'um A\nuh B')
 def test_unknown_contracts(self):
  for value in [None,{}, {'version':2,'source':'reading_transcript'},{'version':True,'source':'reading_transcript'},{'version':1,'source':'summary'}]:
   with self.assertRaises(ValueError):p.publication_text({'publication_transcript':value},self.content,self.segs)
 def test_missing_duplicate_out_of_order(self):
  for refs in [[0],[0,0,1],[1,0],[False,1]]:
   c={'reading_transcript':[{'text':'Paragraph','source_segment_ids':refs}]}
   with self.assertRaises(ValueError):p.publication_text(self.ep,c,self.segs)
 def test_paragraph_linebreaks_rejected(self):
  for value in ['A\nB','A\rB','']:
   c=copy.deepcopy(self.content);c['reading_transcript'][0]['text']=value
   with self.assertRaises(ValueError):p.publication_text(self.ep,c,self.segs)
class ReleaseReadingTests(unittest.TestCase):
 setUp=f.PackageBoundaryTests.setUp
 tearDown=f.PackageBoundaryTests.tearDown
 write=f.PackageBoundaryTests.write
 refresh=f.PackageBoundaryTests.refresh
 prepare_assembly=f.PackageBoundaryTests.prepare_assembly
 run_assembly=f.PackageBoundaryTests.run_assembly
 @classmethod
 def setUpClass(cls):f.PackageBoundaryTests.setUpClass.__func__(cls)
 @classmethod
 def tearDownClass(cls):f.PackageBoundaryTests.tearDownClass.__func__(cls)
 def reading_fixture(self):
  self.content['reading_transcript'][0]['text']='A readable complete paragraph.'
  self.ep['publication_transcript']=dict(p.READING_PUBLICATION)
  self.payload['transcript_text']=p.publication_text(self.ep,self.content,self.segments)
  self.write('payload.json',self.payload);self.write('enrichment.json',self.content)
  f.renderer.build(self.content,self.root,self.root/'preview/episode.html',self.root/'enrichment.json')
  self.names['publication_transcript']='preview/reading-transcript.txt';self.refresh()
 def test_release_reading_and_subtitles(self):
  self.reading_fixture();result=p.validate(self.root,True);self.assertTrue(result['valid'],result)
  self.assertIn('Fixture source A',(self.root/'subtitles.srt').read_text())
  self.assertNotIn('readable',(self.root/'subtitles.srt').read_text())
 def test_aligned_payload_rejected_after_all_hashes_refreshed(self):
  self.reading_fixture();self.payload['transcript_text']='Fixture source A';self.write('payload.json',self.payload);self.refresh()
  r=p.validate(self.root,True);self.assertTrue(any('declared complete publication' in x for x in r['errors']),r)
 def test_missing_publication_role(self):
  self.reading_fixture();del self.names['publication_transcript'];self.refresh();r=p.validate(self.root,True)
  self.assertTrue(any('reading publication artifact missing' in x for x in r['errors']),r)
 def test_new_assembler_defaults_to_reading(self):
  self.content['reading_transcript'][0]['text']='A readable complete paragraph.'
  self.prepare_assembly();self.run_assembly();ep=p.read(self.root/'episode.json');payload=p.read(self.root/'payload.json')
  self.assertEqual(ep['publication_transcript'],p.READING_PUBLICATION)
  self.assertEqual(payload['transcript_text'],'A readable complete paragraph.')
  self.assertEqual(ep['artifacts']['publication_transcript']['path'],'preview/reading-transcript.txt')
 def test_marker_changes_review_context(self):
  old=p.review_context(self.ep);self.ep['publication_transcript']=dict(p.READING_PUBLICATION);self.assertNotEqual(old,p.review_context(self.ep))
if __name__=='__main__':unittest.main()
