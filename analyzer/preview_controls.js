'use strict';

function findPoseIndex(count, timeAt, currentTime) {
  // Browsers can truncate rational PTS to microseconds. Display tolerance only.
  let lo = 0, hi = count - 1;
  while (lo < hi) {
    const mid = Math.ceil((lo + hi) / 2);
    if (timeAt(mid) <= currentTime + 1e-5) lo = mid;
    else hi = mid - 1;
  }
  return lo;
}

function bindMediaMetadata(video, seek, redraw) {
  const update = () => {
    if (Number.isFinite(video.duration)) seek.max = video.duration;
    redraw();
  };
  video.addEventListener('loadedmetadata', update);
  // Large embedded diagnostics may finish parsing after the media event fired.
  if (video.readyState >= 1) update();
}

if (typeof module !== 'undefined') module.exports = {findPoseIndex, bindMediaMetadata};
