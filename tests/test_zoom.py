"""Real Chromium decoding, synthetic poses. Does not certify MediaPipe or Android."""
import subprocess
import tempfile
import unittest
import test_camera as camera_tests


class ZoomTests(unittest.TestCase):
    setUpClass = classmethod(camera_tests.CameraTests.setUpClass.__func__)
    tearDownClass = classmethod(camera_tests.CameraTests.tearDownClass.__func__)
    setUp = camera_tests.CameraTests.setUp
    tearDown = camera_tests.CameraTests.tearDown
    open = camera_tests.CameraTests.open
    camera_active = camera_tests.CameraTests.camera_active

    def setup_video(self, size='640x480', mode='good'):
        self.open()
        self.page.evaluate('window.zoomCalls=0;window.zoomMode="'+mode+'"')
        self.context.route('https://cdn.jsdelivr.net/**', lambda route: route.fulfill(
            content_type='text/javascript', body='''export const FilesetResolver={forVisionTasks:async()=>({})};
            export const PoseLandmarker={createFromOptions:async()=>({detect:()=>{
              window.zoomCalls++;
              const p=Array.from({length:33},(_,i)=>({x:i%2?.45:.55,y:.2+i/50,visibility:.99}));p[0].y=.18;
              if(window.zoomMode==='missing')p[31].visibility=.1;
              return {landmarks:window.zoomMode==='none'?[]:[p],segmentationMasks:[]};
            }})};'''))
        self.page.locator('#crop').select_option('full')
        with tempfile.TemporaryDirectory() as folder:
            path=folder+'/clip.mp4'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-f','lavfi','-i',
                            'color=c=blue:s='+size+':r=10','-t','1.2','-c:v','libx264',
                            '-pix_fmt','yuv420p','-movflags','+faststart',path],check=True)
            with open(path,'rb') as clip_file:
                self.clip=clip_file.read()
        self.upload()
        self.page.locator('#load').click()

    def upload(self):
        self.page.locator('#file').set_input_files({'name':'clip.mp4','mimeType':'video/mp4','buffer':self.clip})

    def done(self):
        self.page.wait_for_function('!zoomPending && !!model')

    def test_analysis_cache_toggle_and_static_training_with_camera(self):
        self.setup_video()
        self.done()
        self.assertIn('Statischer Autozoom bereit',self.page.locator('#zoomStatus').text_content())
        calls=self.page.evaluate('zoomCalls')
        self.assertGreaterEqual(calls,4)
        self.assertEqual(self.page.evaluate("document.getElementById('ref').currentTime"),0)
        self.page.locator('#autoZoom').uncheck()
        self.assertTrue(self.page.evaluate('zoomBox===null'))
        self.page.locator('#autoZoom').check()
        self.done()
        self.assertEqual(self.page.evaluate('zoomCalls'),calls)
        self.assertIn('zwischengespeichert',self.page.locator('#zoomStatus').text_content())
        self.upload()
        self.done()
        self.assertEqual(self.page.evaluate('zoomCalls'),calls)
        self.page.locator('#camera').click()
        self.camera_active()
        self.page.evaluate('window.before=JSON.stringify(zoomBox)')
        self.page.locator('#start').click()
        self.assertTrue(self.page.locator('#autoZoom').is_disabled())
        self.assertTrue(self.page.locator('#crop').is_disabled())
        self.page.wait_for_function("document.getElementById('ref').currentTime>.3",timeout=12000)
        self.assertTrue(self.page.evaluate('JSON.stringify(zoomBox)===before'))
        self.page.locator('#stageStop').click()
        self.assertFalse(self.page.locator('#autoZoom').is_disabled())
        self.page.locator('#autoZoom').uncheck()
        self.page.reload()
        self.assertFalse(self.page.locator('#autoZoom').is_checked())

    def test_portrait_decoder_and_missing_person_fallback(self):
        self.setup_video('360x640','missing')
        self.done()
        self.assertTrue(self.page.evaluate('zoomBox===null'))
        calls=self.page.evaluate('zoomCalls')
        self.page.locator('#autoZoom').uncheck()
        self.page.locator('#autoZoom').check()
        self.done()
        self.assertEqual(self.page.evaluate('zoomCalls'),calls)
        self.assertIn('bisherige Darstellung',self.page.locator('#zoomStatus').text_content())

    def test_skip_pending_analysis_and_stale_results(self):
        self.setup_video()
        self.done()
        self.page.evaluate('''()=>{VideoZoom.analyze=({signal})=>new Promise((resolve,reject)=>{
          signal.addEventListener('abort',()=>reject(new DOMException('abort','AbortError')));
        });}''')
        self.page.locator('#crop').select_option('right')
        self.page.wait_for_function('zoomPending')
        self.page.locator('#camera').click()
        self.camera_active()
        self.assertTrue(self.page.locator('#start').is_disabled())
        self.page.locator('#zoomSkip').click()
        self.assertFalse(self.page.locator('#start').is_disabled())
        self.assertTrue(self.page.evaluate('zoomBox===null'))
        self.assertIn('übersprungen',self.page.locator('#zoomStatus').text_content())

    def test_fingerprint_changes_with_content_and_storage_disabled(self):
        self.open()
        result=self.page.evaluate('''async()=>{
          const a=new File(['aaaa'],'same.mp4'),b=new File(['aaab'],'same.mp4');
          const s=new AbortController().signal;
          const hashes=await Promise.all([VideoZoom.fingerprint(a,s),VideoZoom.fingerprint(b,s)]);
          Storage.prototype.setItem=()=>{throw Error('blocked')};
          VideoZoom.writeCache('x',{x:.1,y:.1,w:.8,h:.8});
          return hashes[0]!==hashes[1];
        }''')
        self.assertTrue(result)

    def test_full_timeline_adaptive_sampling_and_camera_during_analysis(self):
        self.setup_video()
        self.done()
        self.page.locator('#camera').click()
        self.camera_active()
        result=self.page.evaluate("""async()=>{
          let count=0;const progress=[];
          const result=await VideoZoom.analyze({file:document.getElementById('file').files[0],
            crop:'right',signal:new AbortController().signal,onProgress:p=>progress.push(p),
            detect:()=>{count++;const p=Array.from({length:33},(_,i)=>({x:(i%2?.4:.5)+(count%2?.12:0),y:.2+i/50,visibility:.99}));p[0].y=.18;return p;}});
          return {count,progress,box:result.box,live:savedTracks.every(t=>t.readyState==='live')};
        }""")
        self.assertGreater(result['count'],4)
        self.assertEqual(result['progress'][0],0)
        self.assertEqual(max(result['progress']),99)
        self.assertTrue(result['live'])
        self.assertGreater(result['box']['w'],.3)

    def test_no_person_fallback_and_analysis_timeout(self):
        self.setup_video(mode='none')
        self.done()
        self.assertTrue(self.page.evaluate('zoomBox===null'))
        self.assertIn('bisherige Darstellung',self.page.locator('#zoomStatus').text_content())
        self.page.evaluate("""()=>{
          VideoZoom.analyze=({signal})=>new Promise((resolve,reject)=>signal.addEventListener('abort',()=>reject(Error('timeout'))));
          const original=window.setTimeout;
          window.setTimeout=(fn,ms,...args)=>original(fn,ms===90000?50:ms,...args);
        }""")
        self.page.locator('#crop').select_option('right')
        self.done()
        self.assertTrue(self.page.evaluate('zoomBox===null'))
        self.assertIn('Zeitlimit',self.page.locator('#zoomStatus').text_content())
