import { createContext, Fragment, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import api, { API } from '../utils/api';

const PLAYLIST_STORAGE_KEY = 'kiosk_playlist';
const PLAYLIST_REFRESH_MS = 5 * 60 * 1000;
const MEDIA_CACHE_NAME = 'kiosk-media-v1';
const FEEDBACK_PATH = '/submit-feedback';
const ACTIVITY_EVENTS = ['pointerdown', 'pointermove', 'touchstart', 'keydown', 'input', 'scroll'];
const DEFAULT_PLAYLIST = { idle_seconds: 60, image_seconds: 10, media: [] };
const VIDEO_LOAD_TIMEOUT_MS = 60000;
const VIDEO_END_GRACE_MS = 15000;
const FAILED_RETRY_MS = 60000;

const KioskBusyContext = createContext(() => {});

// Pages call this to hold the screensaver off while someone is mid-task without touching the screen.
export const useKioskBusy = (busy) => {
  const setBusy = useContext(KioskBusyContext);
  useEffect(() => {
    setBusy(busy);
    return () => setBusy(false);
  }, [busy, setBusy]);
};

const readStoredJson = (key) => {
  try {
    return JSON.parse(localStorage.getItem(key));
  } catch {
    return null;
  }
};

const mediaUrl = (item) => `${API}/files/${item.path}`;

// Media is kept on the tablet so a looping video is not re-downloaded all day
// and the screensaver keeps playing when the network drops.
const syncMediaCache = async (media) => {
  if (!window.caches) return;
  try {
    const cache = await window.caches.open(MEDIA_CACHE_NAME);
    const wanted = new Set(media.map(mediaUrl));
    const cachedRequests = await cache.keys();
    await Promise.all(
      cachedRequests.filter((request) => !wanted.has(request.url)).map((request) => cache.delete(request))
    );
    const cachedUrls = new Set(cachedRequests.map((request) => request.url));
    for (const url of wanted) {
      if (!cachedUrls.has(url)) {
        await cache.add(url).catch(() => {});
      }
    }
  } catch {
    // Cache is only an optimisation; items still play from the network.
  }
};

const resolvePlayableUrl = async (url) => {
  try {
    const cache = await window.caches?.open(MEDIA_CACHE_NAME);
    const cached = await cache?.match(url);
    if (cached) return URL.createObjectURL(await cached.blob());
  } catch {
    // Fall through to the network URL.
  }
  return url;
};

const KioskScreensaver = ({ media, imageSeconds, temple, onDismiss }) => {
  const [position, setPosition] = useState({ index: 0, plays: 0 });
  const [source, setSource] = useState(null);
  const [failedCount, setFailedCount] = useState(0);
  const watchdogRef = useRef(null);

  const allFailed = media.length > 0 && failedCount >= media.length;
  const item = media.length > 0 && !allFailed ? media[position.index % media.length] : null;
  const itemUrl = item ? mediaUrl(item) : null;

  const advance = useCallback(() => {
    setPosition((p) => ({ index: p.index + 1, plays: p.plays + 1 }));
  }, []);

  const armWatchdog = useCallback((ms) => {
    clearTimeout(watchdogRef.current);
    watchdogRef.current = setTimeout(advance, ms);
  }, [advance]);

  const handleFailure = () => {
    setFailedCount((count) => count + 1);
    advance();
  };

  useEffect(() => {
    if (!itemUrl) return undefined;
    let cancelled = false;
    let objectUrl = null;
    resolvePlayableUrl(itemUrl).then((url) => {
      if (url !== itemUrl) objectUrl = url;
      if (cancelled) {
        if (objectUrl) URL.revokeObjectURL(objectUrl);
        return;
      }
      setSource({ for: itemUrl, url });
    });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [itemUrl]);

  // Images advance on a timer; videos on "ended", with a watchdog so a stalled video cannot freeze the screen.
  useEffect(() => {
    if (!item) return undefined;
    armWatchdog(item.type === 'video' ? VIDEO_LOAD_TIMEOUT_MS : imageSeconds * 1000);
    return () => clearTimeout(watchdogRef.current);
  }, [item, position.plays, imageSeconds, armWatchdog]);

  useEffect(() => {
    if (!allFailed) return undefined;
    const retry = setTimeout(() => setFailedCount(0), FAILED_RETRY_MS);
    return () => clearTimeout(retry);
  }, [allFailed]);

  const dismissTimerRef = useRef(null);
  useEffect(() => () => clearTimeout(dismissTimerRef.current), []);

  const activeSource = source && source.for === itemUrl ? source.url : null;

  return (
    <div
      data-testid="kiosk-screensaver"
      className="fixed inset-0 z-[9999] bg-black flex items-center justify-center select-none"
      style={{ touchAction: 'none' }}
      // Dismiss on click, not pointerdown: closing early would let the same tap land on the form underneath.
      onClick={onDismiss}
      onPointerUp={() => { dismissTimerRef.current = setTimeout(onDismiss, 300); }}
      onContextMenu={(e) => { e.preventDefault(); onDismiss(); }}
    >
      {activeSource && item.type === 'image' && (
        <img
          src={activeSource}
          alt=""
          draggable={false}
          onLoad={() => setFailedCount(0)}
          onError={handleFailure}
          className="w-full h-full object-contain"
        />
      )}

      {activeSource && item.type === 'video' && (
        <video
          key={position.plays}
          src={activeSource}
          autoPlay
          muted
          playsInline
          data-testid="kiosk-video"
          onLoadedMetadata={(e) => {
            setFailedCount(0);
            if (Number.isFinite(e.target.duration)) {
              armWatchdog(e.target.duration * 1000 + VIDEO_END_GRACE_MS);
            }
          }}
          onEnded={advance}
          onError={handleFailure}
          className="w-full h-full object-contain"
        />
      )}

      {!item && (
        <div className="text-center px-8">
          {temple?.logo_path && (
            <img
              src={`${API}/files/${temple.logo_path}`}
              alt=""
              className="w-40 h-40 object-contain mx-auto mb-8"
            />
          )}
          <p className="text-5xl font-bold text-[#F4C430]">{temple?.name || 'Temple Feedback'}</p>
          {temple?.location && <p className="text-2xl text-white/80 mt-4">{temple.location}</p>}
        </div>
      )}

      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 bg-black/60 text-white text-xl px-8 py-3 rounded-full whitespace-nowrap pointer-events-none">
        Touch the screen to give feedback
      </div>
    </div>
  );
};

const KioskLayout = () => {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  // A display board with no registered temple never gets the screensaver.
  const [temple] = useState(() => readStoredJson('registered_temple'));
  const [playlist, setPlaylist] = useState(() => readStoredJson(PLAYLIST_STORAGE_KEY) || DEFAULT_PLAYLIST);
  const [showing, setShowing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [sessionKey, setSessionKey] = useState(0);
  const syncingRef = useRef(false);

  useEffect(() => {
    if (!temple) return undefined;

    const refresh = async () => {
      try {
        const { data } = await api.get('/kiosk/playlist', { params: { temple_id: temple.id } });
        setPlaylist(data);
        localStorage.setItem(PLAYLIST_STORAGE_KEY, JSON.stringify(data));
        if (!syncingRef.current) {
          syncingRef.current = true;
          await syncMediaCache(data.media);
          syncingRef.current = false;
        }
      } catch (error) {
        // Keep playing the last known playlist while offline.
        console.error('Failed to refresh kiosk playlist:', error);
      }
    };

    refresh();
    const interval = setInterval(refresh, PLAYLIST_REFRESH_MS);
    return () => clearInterval(interval);
  }, [temple]);

  useEffect(() => {
    if (!temple || busy || showing) return undefined;

    let timer;
    const restart = () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        setShowing(true);
        // Remounting the page wipes the abandoned form so the next devotee never sees someone's details.
        setSessionKey((key) => key + 1);
        if (window.location.pathname !== FEEDBACK_PATH) {
          navigate(FEEDBACK_PATH, { replace: true });
        }
      }, playlist.idle_seconds * 1000);
    };

    restart();
    ACTIVITY_EVENTS.forEach((name) => window.addEventListener(name, restart, { capture: true, passive: true }));
    return () => {
      clearTimeout(timer);
      ACTIVITY_EVENTS.forEach((name) => window.removeEventListener(name, restart, { capture: true }));
    };
  }, [temple, busy, showing, playlist.idle_seconds, navigate, pathname]);

  // The APK keeps the screen on natively; this covers tablets running the web version in a browser.
  useEffect(() => {
    if (!temple || !navigator.wakeLock) return undefined;
    const acquire = () => {
      if (document.visibilityState === 'visible') {
        navigator.wakeLock.request('screen').catch(() => {});
      }
    };
    acquire();
    document.addEventListener('visibilitychange', acquire);
    return () => document.removeEventListener('visibilitychange', acquire);
  }, [temple]);

  return (
    <KioskBusyContext.Provider value={setBusy}>
      <Fragment key={sessionKey}>
        <Outlet />
      </Fragment>
      {showing && (
        <KioskScreensaver
          media={playlist.media}
          imageSeconds={playlist.image_seconds}
          temple={temple}
          onDismiss={() => setShowing(false)}
        />
      )}
    </KioskBusyContext.Provider>
  );
};

export default KioskLayout;
