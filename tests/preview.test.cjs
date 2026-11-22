const {test} = require('node:test');
const assert = require('node:assert/strict');
const {findPoseIndex, bindMediaMetadata} = require('../analyzer/preview_controls.js');

test('consecutive steps accept browser-rounded rational timestamps', () => {
  const times = [0, 203/600, 223/600, 243/600, 263/600];
  for (let i=0; i<times.length; i++) {
    const browserTime = Math.floor(times[i]*1e6)/1e6;
    assert.equal(findPoseIndex(times.length, i=>times[i], browserTime), i);
  }
});

test('playback uses preceding pose and clamps timeline ends', () => {
  const times = [0, .04, .11, .35];
  const at = i=>times[i];
  assert.equal(findPoseIndex(4, at, .1), 1);
  assert.equal(findPoseIndex(4, at, -1), 0);
  assert.equal(findPoseIndex(4, at, 99), 3);
});

test('metadata that arrived before script initialization sets full seek range', () => {
  const handlers = {}, seek = {max:1}; let redraws=0;
  const video = {duration:112.371667, readyState:2, addEventListener:(event,fn)=>handlers[event]=fn};
  bindMediaMetadata(video,seek,()=>redraws++);
  assert.equal(seek.max,112.371667);
  assert.equal(redraws,1);
});

test('late media metadata also initializes range without a race', () => {
  const handlers = {}, seek = {max:1}; let redraws=0;
  const video = {duration:NaN, readyState:0, addEventListener:(event,fn)=>handlers[event]=fn};
  bindMediaMetadata(video,seek,()=>redraws++);
  assert.equal(redraws,0);
  video.duration=112.371667; video.readyState=1; handlers.loadedmetadata();
  assert.equal(seek.max,112.371667);
  assert.equal(redraws,1);
});
