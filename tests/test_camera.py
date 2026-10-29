"""Desktop browser regression tests; fake camera, never an Android certification.
Run: python3 -m unittest discover -s tests -v
Requires Python Playwright and Chromium (CHROMIUM_PATH can override executable).
"""
import base64
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import threading
import unittest

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class CameraTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(
            executable_path=os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium'),
            args=['--no-sandbox', '--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        self.page.set_default_timeout(7000)
        self.errors = []
        self.external = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.context.route('https://**', lambda route: (self.external.append(route.request.url), route.abort()))

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [], 'Unexpected JavaScript errors')

    def open(self, script=None):
        if script:
            self.context.add_init_script(script)
        self.page.goto(self.url)

    def camera_active(self):
        self.page.wait_for_function("document.getElementById('cameraStatus').textContent.startsWith('Kamera aktiv')")
        self.page.wait_for_function("document.getElementById('cameraTestPreview').videoWidth>0")
        self.page.evaluate("window.savedTracks=document.getElementById('live').srcObject.getTracks()")

    def stopped(self):
        self.assertTrue(self.page.evaluate("savedTracks.every(t=>t.readyState==='ended') && !document.getElementById('live').srcObject && !document.getElementById('cameraTestPreview').srcObject"))

    def test_independent_camera_and_restart(self):
        self.open()
        self.assertTrue(self.page.locator('#start').is_disabled())
        self.page.locator('#cameraTest').click()
        self.camera_active()
        self.assertIn('640 × 480', self.page.locator('#cameraDiagnostics').text_content())
        self.assertTrue(self.page.locator('#start').is_disabled())
        self.assertFalse(self.page.evaluate("savedTracks.some(t=>t.kind==='audio')"))
        self.page.locator('#cameraTestStop').click()
        self.stopped()
        self.page.locator('#camera').click()
        self.camera_active()
        self.page.locator('#stop').click()
        self.stopped()
        self.assertEqual(self.external, [])

    def test_named_errors_and_explicit_fallback(self):
        errors = {
            'NotAllowedError': 'Kameraberechtigung verweigert',
            'NotFoundError': 'Keine passende Kamera',
            'NotReadableError': 'Kamera ist belegt',
            'OverconstrainedError': 'Auflösung ist nicht verfügbar',
            'SecurityError': 'Sicherheitsrichtlinie',
            'AbortError': 'abgebrochen',
            'TypeError': 'akzeptiert die Kameraanfrage nicht',
            'UnknownError': 'Browserunterstützung',
        }
        for name, expected in errors.items():
            with self.subTest(error=name):
                self.page.goto(self.url)
                self.page.evaluate('''name=>{window.cameraCalls=0;window.realGum=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
                  navigator.mediaDevices.getUserMedia=async()=>{cameraCalls++;throw new DOMException('test',name)}}''', name)
                self.page.locator('#cameraTest').click()
                self.page.wait_for_function("!document.getElementById('cameraTest').disabled")
                self.assertIn(expected, self.page.locator('#cameraStatus').inner_text())
                self.assertEqual(self.page.evaluate('cameraCalls'), 1)
                self.assertTrue(self.page.evaluate("!document.getElementById('live').srcObject"))
        self.page.evaluate('''()=>{navigator.mediaDevices.getUserMedia=constraints=>{
          window.lastConstraints=constraints;return realGum(constraints)}}''')
        self.page.locator('#cameraBasic').click()
        self.camera_active()
        self.assertEqual(self.page.evaluate('lastConstraints'), {'video': True, 'audio': False})

    def test_insecure_http_origin(self):
        def serve(route):
            path = ROOT / route.request.url.split('android-insecure.test/', 1)[1].split('?', 1)[0]
            if path == ROOT:
                path = ROOT / 'index.html'
            content_type = 'text/javascript' if path.suffix == '.js' else 'text/css' if path.suffix == '.css' else 'text/html'
            route.fulfill(body=path.read_bytes(), content_type=content_type)
        self.context.route('http://android-insecure.test/**', serve)
        self.page.goto('http://android-insecure.test/')
        self.assertFalse(self.page.evaluate('isSecureContext'))
        self.page.locator('#cameraTest').click()
        self.assertIn('Unsicherer Ursprung', self.page.locator('#cameraStatus').inner_text())
        self.assertIn('HTTPS', self.page.locator('#cameraStatus').inner_text())

    def test_missing_camera_api(self):
        self.open("Object.defineProperty(navigator,'mediaDevices',{value:undefined})")
        self.page.locator('#cameraTest').click()
        self.assertIn('Kamera-API fehlt', self.page.locator('#cameraStatus').inner_text())

    def test_android_browser_hints(self):
        for ua, expected in [('Mozilla/5.0 (Linux; Android 14; wv) Chrome/130', 'In-App'),
                             ('Mozilla/5.0 Android SamsungBrowser/27 Chrome/130', 'Samsung Internet'),
                             ('Mozilla/5.0 Android Firefox/130', 'Firefox'),
                             ('Mozilla/5.0 Android Chrome/130 EdgA/130', 'Edge Android')]:
            with self.subTest(browser=expected):
                self.page.goto(self.url)
                self.page.evaluate("ua=>Object.defineProperty(navigator,'userAgent',{value:ua,configurable:true})", ua)
                self.page.locator('summary').filter(has_text='Kameradiagnose').click()
                self.page.locator('#cameraDiagnose').click()
                self.assertIn(expected, self.page.locator('#cameraDiagnostics').text_content())
                self.assertEqual(self.external, [])

    def test_no_optional_apis_or_permissions_query(self):
        self.open('''HTMLCanvasElement.prototype.captureStream=undefined;window.MediaRecorder=undefined;
          window.AudioContext=undefined;window.webkitAudioContext=undefined;
          Object.defineProperty(navigator,'permissions',{value:undefined});
          Element.prototype.requestFullscreen=undefined;''')
        self.page.locator('#cameraTest').click()
        self.camera_active()
        self.assertIn('Abfrage nicht unterstützt', self.page.locator('#cameraDiagnostics').text_content())
        self.page.locator('#cameraTestStop').click()
        self.stopped()

    def test_no_device_enumeration_before_grant(self):
        self.open('''window.enumerations=0;const real=navigator.mediaDevices.enumerateDevices.bind(navigator.mediaDevices);
          navigator.mediaDevices.enumerateDevices=()=>{enumerations++;return real()};''')
        self.assertEqual(self.page.evaluate('enumerations'), 0)
        self.page.locator('#cameraTest').click()
        self.camera_active()
        self.page.wait_for_function('enumerations===1')

    def test_stop_cancels_pending_permission_and_stale_stream(self):
        self.open('''window.requests=[];const real=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
          window.realGum=real;navigator.mediaDevices.getUserMedia=()=>new Promise(resolve=>requests.push(resolve));''')
        self.page.locator('#cameraTest').click()
        self.assertTrue(self.page.locator('#camera').is_disabled())
        self.page.locator('#cameraTestStop').click()
        self.page.locator('#cameraBasic').click()
        self.page.evaluate("async()=>{window.stale=await realGum({video:true});requests[0](stale)}")
        self.page.wait_for_function("stale.getTracks().every(t=>t.readyState==='ended')")
        self.assertTrue(self.page.locator('#cameraBasic').is_disabled())
        self.page.evaluate("async()=>requests[1](await realGum({video:true}))")
        self.camera_active()
        self.assertFalse(self.page.locator('#cameraBasic').is_disabled())

    def test_stop_while_video_play_pending(self):
        self.open("HTMLMediaElement.prototype.play=()=>new Promise(()=>{})")
        self.page.locator('#cameraTest').click()
        self.page.wait_for_function("!!document.getElementById('live').srcObject")
        self.page.evaluate("window.savedTracks=document.getElementById('live').srcObject.getTracks()")
        self.page.locator('#cameraTestStop').click()
        self.stopped()
        self.assertFalse(self.page.locator('#cameraTest').is_disabled())

    def test_video_timeout_releases_camera(self):
        self.page.clock.install()
        self.open("HTMLMediaElement.prototype.play=()=>new Promise(()=>{})")
        self.page.locator('#cameraTest').click()
        self.page.wait_for_function("!!document.getElementById('live').srcObject")
        self.page.evaluate("window.savedTracks=document.getElementById('live').srcObject.getTracks()")
        self.page.clock.fast_forward(10001)
        self.assertIn('VideoTimeout', self.page.locator('#cameraStatus').inner_text())
        self.stopped()

    def test_video_failure_releases_camera(self):
        self.open('''const play=HTMLMediaElement.prototype.play;HTMLMediaElement.prototype.play=function(){
          if(this.id==='live') {window.failedTracks=this.srcObject.getTracks();return Promise.reject(new Error('play failed'))}
          return play.call(this)};''')
        self.page.locator('#cameraTest').click()
        self.page.wait_for_function("document.getElementById('cameraStatus').textContent.includes('VideoPlaybackError')")
        self.assertTrue(self.page.evaluate("failedTracks.every(t=>t.readyState==='ended')"))

    def test_pagehide_visibility_and_track_ended(self):
        self.open()
        for event in ['pagehide', 'visibilitychange', 'ended']:
            with self.subTest(event=event):
                self.page.locator('#cameraTest').click()
                self.camera_active()
                if event == 'pagehide':
                    self.page.evaluate("window.dispatchEvent(new Event('pagehide'))")
                elif event == 'visibilitychange':
                    self.page.evaluate("Object.defineProperty(document,'hidden',{value:true,configurable:true});document.dispatchEvent(new Event('visibilitychange'))")
                else:
                    self.page.evaluate("savedTracks[0].dispatchEvent(new Event('ended'))")
                self.stopped()
                self.page.evaluate("Object.defineProperty(document,'hidden',{value:false,configurable:true})")

    def import_clip(self):
        clip = self.page.evaluate('''async()=>{
          const canvas=document.createElement('canvas');canvas.width=640;canvas.height=480;
          const ctx=canvas.getContext('2d'),stream=canvas.captureStream(10),r=new MediaRecorder(stream,{mimeType:'video/webm'}),chunks=[];
          r.ondataavailable=e=>chunks.push(e.data);
          const result=new Promise(resolve=>r.onstop=async()=>{const data=new Uint8Array(await new Blob(chunks).arrayBuffer());resolve(btoa(String.fromCharCode(...data)))});
          r.start();for(let i=0;i<30;i++){ctx.fillStyle=i%2?'red':'blue';ctx.fillRect(0,0,640,480);await new Promise(r=>setTimeout(r,100))}
          r.stop();const data=await result;stream.getTracks().forEach(t=>t.stop());return data;
        }''')
        self.page.locator('#file').set_input_files({'name':'test.webm','mimeType':'video/webm','buffer':base64.b64decode(clip)})
        self.page.wait_for_function("document.getElementById('ref').videoWidth===640")

    def test_v12_import_effects_training_recording_smoke(self):
        self.open()
        # Stub the remote model only: this tests wiring, not pose quality or WASM.
        self.context.route('https://cdn.jsdelivr.net/**', lambda route: route.fulfill(
            content_type='text/javascript', body='''export const FilesetResolver={forVisionTasks:async()=>({})};
            export const PoseLandmarker={createFromOptions:async()=>({detect:()=>({landmarks:[],segmentationMasks:[]})})};'''))
        self.import_clip()
        self.page.wait_for_function("document.getElementById('preview').height===480")
        self.page.locator('#crop').select_option('full')
        self.page.wait_for_function("document.getElementById('preview').height===240")
        self.page.locator('#cameraMirror').check()
        self.assertIn('gespiegelt', self.page.locator('#cameraLabel').text_content())
        self.page.locator('#backgroundEnabled').check()
        self.page.locator('#load').click()
        self.page.wait_for_function("document.getElementById('status').textContent.startsWith('Erkennung geladen')")
        self.page.locator('#camera').click()
        self.camera_active()
        self.page.wait_for_function("!document.getElementById('start').disabled")
        self.page.locator('#backgroundEnabled').uncheck()
        self.page.locator('#mirror').check()
        self.page.locator('#recordEnabled').check()
        self.page.locator('#start').click()
        self.page.wait_for_function("document.getElementById('recordStatus').textContent.startsWith('Aufnahme läuft')",timeout=15000)
        self.page.wait_for_function("document.getElementById('ref').currentTime>0.7",timeout=10000)
        self.page.locator('#stageStop').click()
        self.page.wait_for_function("document.querySelectorAll('#downloads a').length===2",timeout=10000)
        self.stopped()
        self.assertTrue(self.page.locator('#review').is_visible())
        self.page.locator('#reviewRate').select_option('0.5')
        self.page.locator('#reviewPlay').click()
        self.page.wait_for_function("document.getElementById('recordSplit').playbackRate===0.5")
        self.page.locator('#reviewPause').click()
        self.assertIn('Keine Bewertung', self.page.locator('#score').inner_text())
