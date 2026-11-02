const {test}=require('node:test');
const assert=require('node:assert/strict');
const Z=require('../src/zoom.js');
function pose(){const p=Array.from({length:33},(_,i)=>({x:i%2?.45:.55,y:.2+i/50,visibility:.99}));p[0].y=.18;return p;}
test('all source resolutions and viewport ratios contain the padded movement union',()=>{
  const bounds=Z.padded(Z.union({x:.2,y:.18,w:.25,h:.65},{x:.5,y:.1,w:.35,h:.75}));
  for(const [sw,sh] of [[1920,1080],[1080,1920],[640,480],[3840,2160],[720,1280]])
    for(const [vw,vh] of [[1280,720],[640,688],[360,800],[800,360]]){
      const f=Z.framing(bounds,sw,sh,vw,vh);
      assert.ok(f.x>=0&&f.y>=0&&f.x+f.w<=sw+1e-8&&f.y+f.h<=sh+1e-8);
      assert.ok(f.x<=bounds.x*sw+1e-8&&f.y<=bounds.y*sh+1e-8);
      assert.ok(f.x+f.w>=(bounds.x+bounds.w)*sw-1e-8);
      assert.ok(f.y+f.h>=(bounds.y+bounds.h)*sh-1e-8);
      assert.ok(f.zoom>=1-1e-8);
    }
});
test('large arm and lateral motion expand the union; no extrema trimmed',()=>{
  const p=pose(),a=Z.poseBox(p);p[19].x=.02;p[20].x=.98;p[19].y=.02;
  const b=Z.poseBox(p),u=Z.padded(Z.union(a,b));assert.equal(u.x,0);assert.equal(u.w,1);assert.equal(u.y,0);assert.ok(Z.moved(a,b));
});
test('missing, low-confidence, NaN, outside-frame and implausible bodies fail safely',()=>{
  assert.equal(Z.poseBox(undefined),null);assert.equal(Z.poseBox([]),null);
  for(const edit of [p=>p[31]=null,p=>p[20].visibility=.2,p=>p[0].x=NaN,p=>p[32].x=1.2,p=>p.forEach(v=>v.y=.5)]){
    const p=pose();edit(p);assert.equal(Z.poseBox(p),null);
  }
});
test('camera distance, frame-edge reserves and deterministic static framing',()=>{
  for(const b of [{x:.4,y:.4,w:.1,h:.2},{x:.01,y:.01,w:.98,h:.98},{x:.2,y:.1,w:.6,h:.8}]){
    const padded=Z.padded(b);assert.ok(Z.validBox(padded));
    const a=Z.framing(padded,1920,1080,1280,720);
    assert.deepEqual(a,Z.framing(padded,1920,1080,1280,720));
    assert.ok(a.w>=b.w*1920&&a.h>=b.h*1080);
  }
  assert.equal(Z.framing({x:0,y:0,w:2,h:1},640,480,640,480),null);
});
