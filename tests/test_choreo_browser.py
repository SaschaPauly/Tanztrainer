"""Real Chromium worker/decoder/training integration; model and camera are synthetic."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import zipfile
import test_camera as camera

FIXTURE=Path(__file__).parent/'fixtures/synthetic.choreo'


def package(edit=None,compression=zipfile.ZIP_STORED):
    with zipfile.ZipFile(FIXTURE) as archive:data={n:archive.read(n) for n in archive.namelist()}
    manifest=json.loads(data['manifest.json'])
    if edit:edit(data,manifest)
    for name,meta in manifest['files'].items():meta.update(size=len(data[name]),sha256=hashlib.sha256(data[name]).hexdigest())
    data['manifest.json']=json.dumps(manifest).encode()
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',compression=compression) as archive:
        for name,blob in data.items():archive.writestr(name,blob)
    return output.getvalue()


class ChoreoBrowserTests(unittest.TestCase):
    setUpClass=classmethod(camera.CameraTests.setUpClass.__func__)
    tearDownClass=classmethod(camera.CameraTests.tearDownClass.__func__)
    setUp=camera.CameraTests.setUp
    tearDown=camera.CameraTests.tearDown
    open=camera.CameraTests.open
    camera_active=camera.CameraTests.camera_active

    def upload(self,blob=None):
        self.page.locator('#choreo').set_input_files({'name':'test.choreo','mimeType':'application/zip','buffer':blob or FIXTURE.read_bytes()})

    def loaded(self):
        self.page.wait_for_function('!!choreoReference && !choreoLoading && document.getElementById("ref").videoWidth>0')

    def model(self):
        with zipfile.ZipFile(FIXTURE) as archive:rows=list(struct.iter_unpack('<7f',archive.read('reference/poses.bin')))[:33]
        points=[dict(x=p[0],y=p[1],visibility=p[5],presence=p[6]) for p in rows]
        self.page.evaluate('window.modelCalls=[];window.failReferenceInference=true;window.refCanvas=rc')
        source='export const FilesetResolver={forVisionTasks:async()=>({})};export const PoseLandmarker={createFromOptions:async()=>({detect:canvas=>{const ref=canvas===window.refCanvas;window.modelCalls.push(ref);if(ref&&window.failReferenceInference)throw Error("Reference inference forbidden");return {landmarks:['+json.dumps(points)+'],segmentationMasks:[]}}})};'
        self.context.route('https://cdn.jsdelivr.net/**',lambda route:route.fulfill(content_type='text/javascript',body=source))
        self.page.locator('#load').click();self.page.wait_for_function('!!model')

    def test_valid_worker_import_quality_crop_and_no_reference_inference(self):
        self.open();self.upload();self.loaded()
        self.assertTrue(self.page.locator('#crop').is_disabled())
        self.assertEqual(self.page.locator('#crop').input_value(),'full')
        self.assertEqual(self.page.evaluate('choreoReference.poseAt(.25).length'),33)
        self.model()
        self.assertEqual(self.page.evaluate('modelCalls'),[])
        self.assertIn('keine neue Referenzanalyse',self.page.locator('#zoomStatus').text_content())
        self.assertIn('Synthetische Testdaten',self.page.locator('#choreoQuality').text_content())
        self.page.evaluate('window.originalPose=JSON.stringify(referencePose(.25))')
        self.page.locator('#autoZoom').uncheck();self.page.locator('#autoZoom').check()
        self.assertTrue(self.page.evaluate('JSON.stringify(referencePose(.25))===originalPose && modelCalls.length===0'))
        # Exact stored rectangle; do not expand it back to the 16:9 viewport.
        rectangle=self.page.evaluate('''()=>{const args=[];drawZoomReference({drawImage:(...a)=>args.push(a.slice(1))},0,0,640,480);return args[0]}''')
        self.assertAlmostEqual(rectangle[0],16);self.assertAlmostEqual(rectangle[2],128)

    def test_reference_preview_needs_neither_model_camera_nor_external_requests(self):
        self.open('HTMLVideoElement.prototype.requestVideoFrameCallback=undefined');self.upload();self.loaded()
        self.page.wait_for_function('!!document.getElementById("unifiedPreview").srcObject')
        self.page.evaluate('()=>{window.framesPainted=0;const original=liveFrame;liveFrame=()=>{framesPainted++;original()}}')
        self.page.locator('#referencePreview').click()
        self.page.wait_for_function('document.getElementById("ref").currentTime>.4 && framesPainted>0')
        self.page.locator('#referencePreview').click()
        self.assertTrue(self.page.evaluate('!model && !stream && document.getElementById("ref").paused'))
        self.assertEqual(self.external,[])

    def test_pagehide_terminates_import_and_releases_previous_pose_memory(self):
        self.open();self.upload();self.loaded()
        self.page.evaluate('''()=>{window.oldReference=choreoReference;window.terminated=0;window.Worker=class{postMessage(){}terminate(){window.terminated++}}}''')
        self.upload();self.page.wait_for_function('choreoLoading')
        self.page.evaluate('window.dispatchEvent(new Event("pagehide"))')
        self.page.wait_for_function('!choreoLoading')
        self.assertTrue(self.page.evaluate('terminated===1 && choreoReference===null && oldReference.poseView===null && !previewStream && !stream'))

    def test_rejected_replacement_keeps_previous_reference_and_renders_text_safely(self):
        self.open()
        def hostile_title(data,manifest):
            manifest['title']='<img src=x onerror=alert(1)>'
            quality=json.loads(data['reference/quality.json']);quality['warnings']=['<script>bad()</script>'];data['reference/quality.json']=json.dumps(quality).encode()
        self.upload(package(hostile_title));self.loaded()
        self.assertEqual(self.page.locator('#choreoQuality script').count(),0)
        self.assertEqual(self.page.locator('#choreoStatus img').count(),0)
        self.page.evaluate('window.oldReference=choreoReference;window.oldSource=document.getElementById("ref").src')
        self.upload(b'not zip');self.page.wait_for_function('!choreoLoading')
        self.assertTrue(self.page.evaluate('choreoReference===oldReference && document.getElementById("ref").src===oldSource'))
        self.assertIn('nicht geladen',self.page.locator('#choreoStatus').text_content())

    def test_cancel_worker_releases_it_without_replacing_reference(self):
        self.open();self.upload();self.loaded()
        self.page.evaluate('''()=>{window.oldReference=choreoReference;window.RealWorker=Worker;window.terminated=0;window.Worker=class{postMessage(){}terminate(){window.terminated++}}}''')
        self.upload();self.page.wait_for_function('choreoLoading')
        self.page.locator('#choreoCancel').click();self.page.wait_for_function('!choreoLoading')
        self.assertTrue(self.page.evaluate('terminated===1 && choreoReference===oldReference'))
        self.page.evaluate('()=>{window.Worker=RealWorker}')

    def test_deflated_import_and_oversize_preflight(self):
        self.open();self.upload(package(compression=zipfile.ZIP_DEFLATED));self.loaded()
        message=self.page.evaluate('''async()=>{try{await Choreo.open({size:64*1024*1024+1})}catch(e){return e.message}}''')
        self.assertIn('64 MiB',message)

    def test_live_training_recording_and_after_analysis_never_infer_reference(self):
        self.open();self.upload();self.loaded();self.model()
        self.page.locator('#recordEnabled').check();self.page.locator('#camera').click();self.camera_active()
        self.page.locator('#start').click()
        self.page.wait_for_function('running && recorders.length===2',timeout=7000)
        self.page.wait_for_function('!running && !finalizing && document.getElementById("recordRaw").videoWidth>0',timeout=7000)
        self.assertGreater(self.page.evaluate('scoredFrames'),0)
        self.assertTrue(self.page.evaluate('modelCalls.length>0 && modelCalls.every(ref=>!ref)'))
        self.page.locator('#analyze').click();self.page.wait_for_function('!analyzing')
        self.assertGreater(self.page.locator('#framePairs article').count(),0)
        self.assertTrue(self.page.evaluate('modelCalls.every(ref=>!ref)'))
        self.assertIn('abgeschlossen',self.page.locator('#recordStatus').text_content())

    def test_close_revokes_url_and_raw_video_path_remains_available(self):
        self.open();self.upload();self.loaded();self.model()
        self.page.evaluate('window.released=choreoReference;window.oldURL=choreoReference.url')
        self.page.locator('#referenceClear').click()
        self.assertTrue(self.page.evaluate('choreoReference===null && released.poseView===null && !document.getElementById("ref").src && !document.getElementById("crop").disabled'))
        self.page.evaluate('window.failReferenceInference=false;document.getElementById("autoZoom").checked=false')
        with zipfile.ZipFile(FIXTURE) as archive:video=archive.read('reference/video.mp4')
        self.page.locator('#file').set_input_files({'name':'normal.mp4','mimeType':'video/mp4','buffer':video})
        self.page.wait_for_function('document.getElementById("ref").videoWidth>0')
        self.assertTrue(self.page.evaluate('drawRef() && !!referencePose(.25) && modelCalls.at(-1)===true'))

    def test_nonzero_audio_offset_uses_separate_local_audio_and_mutes_before_start(self):
        self.open()
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'source.mp4';output=Path(directory)/'audio.mp4'
            with zipfile.ZipFile(FIXTURE) as archive:source.write_bytes(archive.read('reference/video.mp4'))
            subprocess.run([os.environ.get('FFMPEG_PATH','ffmpeg'),'-hide_banner','-loglevel','error','-i',str(source),'-f','lavfi','-i','sine=frequency=440:sample_rate=44100','-t','1','-c:v','copy','-c:a','aac','-shortest',str(output)],check=True)
            video_bytes=output.read_bytes()
            def audio(data,manifest):data['reference/video.mp4']=video_bytes;manifest['audio']=dict(source='reference/video.mp4',offsetSeconds=.4)
            self.upload(package(audio));self.loaded()
        self.page.wait_for_function('Number.isFinite(offsetAudio.duration)')
        self.assertEqual(self.page.evaluate('packageAudioMode()'),'offset')
        self.page.locator('#musicEnable').click()
        self.page.evaluate('''async()=>{const v=document.getElementById('ref');v.currentTime=0;await v.play();syncPackageAudio(true)}''')
        self.assertTrue(self.page.evaluate('offsetAudio.paused && referenceAudioGain.gain.value===0 && offsetAudioGain.gain.value===1'))
        self.page.wait_for_function('document.getElementById("ref").currentTime>.6')
        self.assertTrue(self.page.evaluate('!offsetAudio.paused && Math.abs(offsetAudio.currentTime-(document.getElementById("ref").currentTime-.4))<.15'))
        self.page.evaluate('document.getElementById("ref").pause()')
        self.assertTrue(self.page.evaluate('offsetAudio.paused'))
        def negative(data,manifest):data['reference/video.mp4']=video_bytes;manifest['audio']=dict(source='reference/video.mp4',offsetSeconds=-.2)
        self.upload(package(negative));self.loaded();self.page.wait_for_function('Number.isFinite(offsetAudio.duration)')
        self.page.locator('#referencePreview').click()
        self.page.wait_for_function('!offsetAudio.paused')
        self.assertTrue(self.page.evaluate('Math.abs(offsetAudio.currentTime-(document.getElementById("ref").currentTime+.2))<.15'))
        self.page.evaluate('document.getElementById("ref").pause()')
        def muted(data,manifest):data['reference/video.mp4']=video_bytes;manifest['audio']=dict(source='none',offsetSeconds=0)
        self.upload(package(muted));self.loaded();self.page.locator('#musicEnable').click()
        self.assertTrue(self.page.evaluate('packageAudioMode()==="none" && referenceAudioGain.gain.value===0 && offsetAudioGain.gain.value===0 && !audioReady'))


if __name__=='__main__':unittest.main()
