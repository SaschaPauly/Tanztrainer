/* Camera access and local diagnostics; no model, reference video or uploads. */
window.createCameraController = function ({video, preview, onStream, onEnded, onReady}) {
  const byId = id => document.getElementById(id);
  const buttons = ['camera', 'cameraTest', 'cameraBasic'];
  let active = null, generation = 0, pending = false, cancelWait = null;
  let permission = 'unbekannt (Abfrage nicht unterstützt)', devices = 'erst nach Kamerafreigabe';

  function diagnose() {
    const ua = navigator.userAgent;
    const embedded = /; wv\)|\bwv\b|FBAN|FBAV|Instagram|WhatsApp|Line\//i.test(ua);
    const browser = embedded ? 'Möglicher In-App-Browser / WebView' : /SamsungBrowser/i.test(ua)
      ? 'Samsung Internet' : /EdgA/i.test(ua) ? 'Edge Android' : /Firefox/i.test(ua)
      ? 'Firefox' : /Chrome/i.test(ua) ? 'Chrome / Chromium' : 'Nicht sicher bestimmbar';
    const track = active?.getVideoTracks()[0];
    const rows = {
      Browser: browser,
      'Browserkennung (nur lokal)': ua,
      'Sicherer Kontext': window.isSecureContext ? 'ja' : 'nein – HTTPS erforderlich',
      Protokoll: location.protocol,
      Sichtbarkeit: document.visibilityState,
      mediaDevices: navigator.mediaDevices ? 'vorhanden' : 'fehlt',
      getUserMedia: typeof navigator.mediaDevices?.getUserMedia === 'function' ? 'vorhanden' : 'fehlt',
      Kameraberechtigung: permission,
      Kameras: devices,
      'Video readyState': String(video.readyState),
      Auflösung: `${video.videoWidth} × ${video.videoHeight}`,
      Kameratrack: track ? `${track.readyState}${track.muted ? ' (stumm / unterbrochen)' : ''}` : 'kein aktiver Track',
      'Optionale APIs': `Vollbild: ${!!document.documentElement.requestFullscreen}; captureStream: ${!!HTMLCanvasElement.prototype.captureStream}; MediaRecorder: ${!!window.MediaRecorder}; AudioContext: ${!!(window.AudioContext || window.webkitAudioContext)}`
    };
    const list = byId('cameraDiagnostics');
    list.replaceChildren();
    for (const [key, value] of Object.entries(rows)) {
      const dt = document.createElement('dt'), dd = document.createElement('dd');
      dt.textContent = key; dd.textContent = value; list.append(dt, dd);
    }
    byId('cameraBrowserHint').textContent = embedded
      ? 'In-App-Browser können Kamerazugriff blockieren. Öffne die HTTPS-Seite direkt in Chrome für Android.'
      : 'Auf Android bevorzugt direkt in aktuellem Chrome über HTTPS testen. Samsung Internet, Firefox und Edge können sich bei Berechtigungen und Video-APIs unterscheiden; die Browserkennung garantiert keine Kompatibilität.';
  }

  async function checkPermission() {
    try {
      const result = await navigator.permissions.query({name: 'camera'});
      permission = result.state;
      // A hint only: never block a user-initiated request based on this query.
    } catch (_) { permission = 'unbekannt (Abfrage nicht unterstützt)'; }
    diagnose();
  }

  function busy(value) {
    pending = value;
    buttons.forEach(id => { byId(id).disabled = value; });
  }

  function stop() {
    generation++;
    cancelWait?.();
    cancelWait = null;
    const previous = active;
    active = null;
    previous?.getTracks().forEach(track => track.stop());
    video.srcObject = null;
    preview.srcObject = null;
    busy(false);
    onStream(null);
    byId('cameraStatus').textContent = 'Kamera aus. Ein neuer Versuch benötigt einen Tastendruck.';
    diagnose();
  }

  function cameraError(error) {
    const messages = {
      InsecureContext: 'Unsicherer Ursprung: Öffne die Seite über vertrauenswürdiges HTTPS. HTTP über eine LAN-IP reicht auf Android nicht; localhost gilt nur auf demselben Gerät. Datei-URLs sind nicht zuverlässig.',
      MissingAPI: 'Die Kamera-API fehlt. Öffne die HTTPS-Seite direkt in einem aktuellen Browser, bevorzugt Chrome für Android; In-App-Browser können den Zugriff einschränken.',
      NotAllowedError: 'Kameraberechtigung verweigert oder durch Browser-/Website-Richtlinie blockiert. Prüfe Android → Apps → dein Browser → Berechtigungen → Kamera sowie die Kamera-Freigabe der Website. In-App-Browser: Seite direkt in Chrome öffnen. Danach bewusst erneut versuchen.',
      NotFoundError: 'Keine passende Kamera gefunden. Prüfe, ob das Gerät eine verfügbare Kamera hat. Versuche gegebenenfalls „Ohne Kameravorgabe testen“.',
      NotReadableError: 'Kamera ist belegt oder kann vom System nicht geöffnet werden. Schließe andere Kamera-Apps und Tabs; prüfe die Android-Kamerasperre und versuche erneut.',
      OverconstrainedError: 'Die gewünschte Kamera oder Auflösung ist nicht verfügbar. Versuche „Ohne Kameravorgabe testen“; es gibt keinen automatischen Neuversuch.',
      SecurityError: 'Die Kamera wird durch eine Sicherheitsrichtlinie gesperrt. Prüfe HTTPS, Website-/Browser-Einstellungen und gegebenenfalls die Einbettung der Seite.',
      AbortError: 'Der Kamerastart wurde vom Browser oder System abgebrochen. Schließe andere Kamera-Apps und starte bewusst erneut.',
      TypeError: 'Der Browser akzeptiert die Kameraanfrage nicht. Prüfe HTTPS und einen aktuellen Browser; versuche „Ohne Kameravorgabe testen“.',
      VideoPlaybackError: 'Die Kamera wurde geöffnet, aber das Livevideo konnte nicht abgespielt werden. Prüfe den Browser und starte den Test erneut.',
      VideoTimeout: 'Die Kamera lieferte nicht rechtzeitig ein abspielbares Bild. Andere Kamera-Apps schließen und den Test erneut starten.'
    };
    return `${messages[error.name] || 'Kamerastart fehlgeschlagen. Prüfe die Browserunterstützung und versuche den Test direkt in Chrome über HTTPS.'} (${error.name || 'Unbekannter Fehler'})`;
  }

  function playable(token) {
    return new Promise((resolve, reject) => {
      let played = false, settled = false;
      const cleanup = () => {
        clearTimeout(timeout);
        for (const element of [video, preview]) {
          element.removeEventListener('loadeddata', check);
          element.removeEventListener('error', failed);
        }
        cancelWait = null;
      };
      const finish = error => {
        if (settled) return;
        settled = true;
        cleanup();
        error ? reject(error) : resolve();
      };
      const check = () => {
        if (token !== generation) finish({name: 'Cancelled'});
        else if (played && [video, preview].every(element => element.readyState >= 2 && element.videoWidth > 0)) finish();
      };
      const failed = () => finish({name: 'VideoPlaybackError'});
      const timeout = setTimeout(() => finish({name: 'VideoTimeout'}), 10000);
      cancelWait = () => finish({name: 'Cancelled'});
      for (const element of [video, preview]) {
        element.addEventListener('loadeddata', check);
        element.addEventListener('error', failed);
      }
      // play() may remain pending: the timeout and Stop must still work.
      try {
        Promise.all([video.play(), preview.play()]).then(() => { played = true; check(); }, failed);
      } catch (_) { failed(); }
      check();
    });
  }

  async function start(basic = false) {
    if (pending) return;
    stop();
    const token = generation;
    busy(true);
    byId('cameraStatus').textContent = 'Warte auf Kamerafreigabe und Livebild. Bei einem offenen Berechtigungsdialog bitte im Browser entscheiden.';
    let acquired = null;
    try {
      if (!window.isSecureContext) throw {name: 'InsecureContext'};
      if (typeof navigator.mediaDevices?.getUserMedia !== 'function') throw {name: 'MissingAPI'};
      acquired = await navigator.mediaDevices.getUserMedia({video: basic ? true : {
        facingMode: 'user', width: {ideal: 640}, height: {ideal: 480}
      }, audio: false});
      if (token !== generation || document.hidden) {
        acquired.getTracks().forEach(track => track.stop());
        if (token === generation) stop();
        return;
      }
      active = acquired;
      video.srcObject = active;
      preview.srcObject = active;
      await playable(token);
      if (token !== generation) return;
      // The raw test stays independent of canvas capture, model and fullscreen.
      onStream(active);
      byId('cameraStatus').textContent = 'Kamera aktiv. Die Rohvorschau benötigt weder Referenzvideo noch Pose-Modell.';
      try { onReady(); } catch (_) {
        byId('cameraStatus').textContent += ' Die zusätzliche Trainingsvorschau ist in diesem Browser nicht verfügbar.';
      }
      active.getVideoTracks().forEach(track => {
        track.addEventListener('ended', () => {
          if (token !== generation) return;
          onEnded();
          byId('cameraStatus').textContent = 'Kameraverbindung beendet. Prüfe die Berechtigung und starte bei Bedarf erneut.';
        });
        for (const event of ['mute', 'unmute']) track.addEventListener(event, diagnose);
      });
      // Do not enumerate devices before the explicit successful grant.
      navigator.mediaDevices.enumerateDevices?.().then(items => {
        if (token !== generation) return;
        devices = `${items.filter(item => item.kind === 'videoinput').length} verfügbar (nach Freigabe)`;
        diagnose();
      }).catch(() => {});
      checkPermission();
    } catch (error) {
      acquired?.getTracks().forEach(track => track.stop());
      if (token !== generation) return;
      stop();
      byId('cameraStatus').textContent = cameraError(error);
      byId('status').textContent = cameraError(error);
      checkPermission();
    } finally {
      if (token === generation) busy(false);
      diagnose();
    }
  }

  byId('cameraTest').onclick = () => start();
  byId('cameraBasic').onclick = () => start(true);
  byId('cameraDiagnose').onclick = () => { diagnose(); checkPermission(); };
  video.addEventListener('loadeddata', diagnose);
  video.addEventListener('resize', diagnose);
  document.addEventListener('visibilitychange', diagnose);
  diagnose();
  checkPermission();
  return {start, stop};
};
