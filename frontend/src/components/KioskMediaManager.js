import { useEffect, useRef, useState } from 'react';
import api, { API } from '../utils/api';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { ArrowDown, ArrowUp, MonitorPlay, Trash2, Upload } from 'lucide-react';
import { toast } from 'sonner';

const ACCEPTED_TYPES = '.jpg,.jpeg,.png,.webp,.gif,.mp4,.webm';

const KioskMediaManager = () => {
  const [media, setMedia] = useState([]);
  const [settings, setSettings] = useState({ idle_seconds: 60, image_seconds: 10 });
  const [loading, setLoading] = useState(true);
  const [uploadStatus, setUploadStatus] = useState('');
  const fileInputRef = useRef(null);

  const applyPlaylist = (data) => {
    setMedia(data.media);
    setSettings({ idle_seconds: data.idle_seconds, image_seconds: data.image_seconds });
  };

  useEffect(() => {
    api.get('/kiosk/playlist')
      .then((res) => applyPlaylist(res.data))
      .catch((e) => toast.error(e.response?.data?.detail || 'Failed to load screensaver media'))
      .finally(() => setLoading(false));
  }, []);

  const handleFiles = async (e) => {
    const files = Array.from(e.target.files || []);
    e.target.value = '';
    for (const [index, file] of files.entries()) {
      const label = `${file.name} (${index + 1} of ${files.length})`;
      setUploadStatus(`Uploading ${label}...`);
      try {
        const body = new FormData();
        body.append('file', file);
        const res = await api.post('/kiosk/media', body, {
          headers: { 'Content-Type': 'multipart/form-data' },
          // Large videos on a slow connection can outlast the default API timeout.
          timeout: 0,
          onUploadProgress: ({ progress }) => {
            if (progress) setUploadStatus(`Uploading ${label}: ${Math.round(progress * 100)}%`);
          },
        });
        applyPlaylist(res.data);
        toast.success(`${file.name} added`);
      } catch (e2) {
        toast.error(`${file.name}: ${e2.response?.data?.detail || 'Upload failed'}`);
      }
    }
    setUploadStatus('');
  };

  const move = async (index, offset) => {
    const reordered = [...media];
    const [item] = reordered.splice(index, 1);
    reordered.splice(index + offset, 0, item);
    try {
      const res = await api.put('/kiosk/media/order', { ids: reordered.map((m) => m.id) });
      applyPlaylist(res.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to reorder');
    }
  };

  const handleDelete = async (item) => {
    if (!window.confirm('Remove this from the tablet screensaver?')) return;
    try {
      const res = await api.delete(`/kiosk/media/${item.id}`);
      applyPlaylist(res.data);
      toast.success('Removed');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to remove');
    }
  };

  const saveSettings = async (e) => {
    e.preventDefault();
    try {
      const res = await api.put('/kiosk/settings', {
        idle_seconds: Number(settings.idle_seconds),
        image_seconds: Number(settings.image_seconds),
      });
      applyPlaylist(res.data);
      toast.success('Timings saved');
    } catch {
      toast.error('Idle time must be 10-3600 seconds and image time 3-300 seconds');
    }
  };

  return (
    <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-lg overflow-hidden">
      <div className="p-6 border-b border-[#E2E8F0] flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <MonitorPlay className="text-[#721C24]" size={22} />
          <div>
            <h2 className="text-xl font-bold text-[#721C24]">Tablet Screensaver</h2>
            <p className="text-sm text-[#4A5568]">Plays on all temple tablets when idle. Touching the screen opens the feedback app.</p>
          </div>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_TYPES}
          multiple
          onChange={handleFiles}
          data-testid="kiosk-media-input"
          className="hidden"
        />
        <Button
          onClick={() => fileInputRef.current?.click()}
          disabled={Boolean(uploadStatus)}
          data-testid="kiosk-media-upload-button"
          className="bg-[#721C24] hover:bg-[#5A161C] text-white"
        >
          <Upload size={18} className="mr-2" />
          Upload Image / Video
        </Button>
      </div>

      <div className="p-6 space-y-6">
        <p className="text-sm text-[#4A5568]">
          Images: JPG, PNG, WEBP or GIF, up to 10 MB. Videos: MP4 or WEBM, up to 100 MB. Videos play without sound.
        </p>
        {uploadStatus && <p className="text-sm font-medium text-[#721C24]">{uploadStatus}</p>}

        {loading ? (
          <div className="text-center py-8">Loading...</div>
        ) : media.length === 0 ? (
          <p className="text-center py-8 text-[#4A5568]">
            Nothing uploaded yet. Idle tablets show the temple name and logo.
          </p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {media.map((item, index) => (
              <div key={item.id} data-testid="kiosk-media-item" className="border border-[#E2E8F0] rounded-xl overflow-hidden bg-white">
                <div className="aspect-video bg-black">
                  {item.type === 'video' ? (
                    <video src={`${API}/files/${item.path}`} controls muted preload="metadata" className="w-full h-full object-contain" />
                  ) : (
                    <img src={`${API}/files/${item.path}`} alt={`Screensaver item ${index + 1}`} className="w-full h-full object-contain" />
                  )}
                </div>
                <div className="flex items-center justify-between p-2">
                  <span className="text-sm text-[#4A5568] pl-2">{index + 1}. {item.type === 'video' ? 'Video' : 'Image'}</span>
                  <div className="flex items-center gap-1">
                    <Button variant="ghost" size="sm" disabled={index === 0} onClick={() => move(index, -1)} aria-label="Play earlier">
                      <ArrowUp size={16} />
                    </Button>
                    <Button variant="ghost" size="sm" disabled={index === media.length - 1} onClick={() => move(index, 1)} aria-label="Play later">
                      <ArrowDown size={16} />
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleDelete(item)} aria-label="Remove" className="text-red-600 hover:bg-red-50">
                      <Trash2 size={16} />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        <form onSubmit={saveSettings} className="flex flex-wrap items-end gap-4 pt-4 border-t border-[#E2E8F0]">
          <div>
            <Label className="text-[#721C24]">Start after idle (seconds)</Label>
            <Input
              type="number"
              min={10}
              max={3600}
              required
              value={settings.idle_seconds}
              onChange={(e) => setSettings({ ...settings, idle_seconds: e.target.value })}
              data-testid="kiosk-idle-seconds"
              className="mt-1.5 w-44"
            />
          </div>
          <div>
            <Label className="text-[#721C24]">Show each image (seconds)</Label>
            <Input
              type="number"
              min={3}
              max={300}
              required
              value={settings.image_seconds}
              onChange={(e) => setSettings({ ...settings, image_seconds: e.target.value })}
              data-testid="kiosk-image-seconds"
              className="mt-1.5 w-44"
            />
          </div>
          <Button type="submit" variant="outline" className="border-2 border-[#721C24] text-[#721C24] hover:bg-[#721C24] hover:text-white">
            Save Timings
          </Button>
        </form>
      </div>
    </div>
  );
};

export default KioskMediaManager;
