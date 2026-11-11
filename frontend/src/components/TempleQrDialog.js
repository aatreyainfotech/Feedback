import { useEffect, useState } from 'react';
import QRCode from 'qrcode';
import { Button } from './ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Copy, Download } from 'lucide-react';
import { toast } from 'sonner';
import { API } from '../utils/api';

// Fixed so a QR made from the tablet app or a dev machine still points at the public site.
const PUBLIC_SITE_URL = process.env.REACT_APP_PUBLIC_SITE_URL || 'https://fb.aatreya.org';
const MAROON = '#721C24';

export const templeFeedbackUrl = (temple) => `${PUBLIC_SITE_URL}/feedback/${String(temple.id).toLowerCase()}`;

// QR codes are made and downloaded only by the Super Admin.
export const isSuperAdminUser = () => {
  try {
    return JSON.parse(localStorage.getItem('user') || 'null')?.role === 'superadmin';
  } catch {
    return false;
  }
};

const loadLogo = (temple) => new Promise((resolve) => {
  if (!temple?.logo_path) return resolve(null);
  const img = new Image();
  img.crossOrigin = 'anonymous'; // the API sends Access-Control-Allow-Origin, so the PNG can still be saved
  img.onload = () => resolve(img);
  img.onerror = () => resolve(null); // no logo: plain QR code
  img.src = `${API}/files/${temple.logo_path}`;
});

// The QR code with the temple logo in the centre. Level H keeps it readable with the centre covered.
export const renderTempleQr = async (temple, size) => {
  const canvas = document.createElement('canvas');
  const logo = await loadLogo(temple);
  await QRCode.toCanvas(canvas, templeFeedbackUrl(temple), {
    width: size,
    margin: 2,
    errorCorrectionLevel: logo ? 'H' : 'M',
    color: { dark: '#2B0A0E', light: '#FFFFFF' },
  });
  if (logo) {
    const ctx = canvas.getContext('2d');
    const c = canvas.width / 2;
    const badge = canvas.width * 0.24; // under 30% of the code, the most level H can lose
    ctx.beginPath();
    ctx.arc(c, c, badge / 2, 0, Math.PI * 2);
    ctx.fillStyle = '#FFFFFF';
    ctx.fill();
    ctx.lineWidth = Math.max(2, badge * 0.04);
    ctx.strokeStyle = MAROON;
    ctx.stroke();
    const inner = badge * 0.8;
    const scale = Math.min(inner / logo.width, inner / logo.height);
    const w = logo.width * scale;
    const h = logo.height * scale;
    ctx.save();
    ctx.beginPath();
    ctx.arc(c, c, inner / 2, 0, Math.PI * 2);
    ctx.clip();
    ctx.drawImage(logo, c - w / 2, c - h / 2, w, h);
    ctx.restore();
  }
  return canvas;
};

const wrapLines = (ctx, text, maxWidth) => {
  const lines = [];
  let line = '';
  for (const word of String(text || '').split(/\s+/).filter(Boolean)) {
    const next = line ? `${line} ${word}` : word;
    if (line && ctx.measureText(next).width > maxWidth) {
      lines.push(line);
      line = word;
    } else {
      line = next;
    }
  }
  if (line) lines.push(line);
  return lines;
};

// A ready-to-print A-series poster: temple name, the QR code and a short instruction.
const renderPoster = async (temple, url) => {
  const width = 1240;
  const height = 1754;
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');

  ctx.fillStyle = '#FFFFFF';
  ctx.fillRect(0, 0, width, height);
  ctx.fillStyle = MAROON;
  ctx.fillRect(0, 0, width, 24);
  ctx.fillRect(0, height - 24, width, 24);
  ctx.textAlign = 'center';

  ctx.font = 'bold 76px Georgia, serif';
  let y = 170;
  for (const line of wrapLines(ctx, temple.name, width - 160).slice(0, 3)) {
    ctx.fillText(line, width / 2, y);
    y += 92;
  }
  if (temple.location) {
    ctx.fillStyle = '#4A5568';
    ctx.font = '44px Arial, sans-serif';
    ctx.fillText(temple.location, width / 2, y);
    y += 40;
  }

  const qrSize = 900;
  const qrCanvas = await renderTempleQr(temple, qrSize);
  const qrTop = Math.max(y + 40, 420);
  ctx.drawImage(qrCanvas, (width - qrSize) / 2, qrTop, qrSize, qrSize);

  ctx.fillStyle = MAROON;
  ctx.font = 'bold 64px Arial, sans-serif';
  ctx.fillText('Scan to give your feedback', width / 2, qrTop + qrSize + 110);
  ctx.fillStyle = '#4A5568';
  ctx.font = '30px Arial, sans-serif';
  ctx.fillText(url, width / 2, qrTop + qrSize + 180);

  return canvas.toDataURL('image/png');
};

const TempleQrDialog = ({ temple, onClose }) => {
  const [poster, setPoster] = useState(null);
  const allowed = isSuperAdminUser();
  const url = temple ? templeFeedbackUrl(temple) : '';

  useEffect(() => {
    setPoster(null);
    if (!temple || !allowed) return undefined;
    let cancelled = false;
    renderPoster(temple, templeFeedbackUrl(temple))
      .then((dataUrl) => { if (!cancelled) setPoster(dataUrl); })
      .catch(() => toast.error('Failed to create QR code'));
    return () => { cancelled = true; };
  }, [temple, allowed]);

  const fileName = temple ? `feedback-qr-${temple.name.replace(/[^a-z0-9]+/gi, '-').toLowerCase()}.png` : '';

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(url);
      toast.success('Link copied');
    } catch {
      toast.error('Could not copy the link');
    }
  };

  return (
    <Dialog open={Boolean(temple) && allowed} onOpenChange={(isOpen) => { if (!isOpen) onClose(); }}>
      <DialogContent className="bg-white max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-[#721C24] text-2xl">Feedback QR Code</DialogTitle>
        </DialogHeader>
        <p className="text-sm text-[#4A5568]">
          Devotees scan this with their phone camera to open the feedback form for <span className="font-semibold">{temple?.name}</span>. Print it and display it at the temple.
        </p>
        <div className="border border-[#E2E8F0] rounded-xl overflow-hidden bg-white">
          {poster ? (
            <img src={poster} alt={`Feedback QR code for ${temple?.name}`} data-testid="temple-qr-image" className="w-full" />
          ) : (
            <div className="aspect-[1240/1754] flex items-center justify-center text-[#4A5568]">Creating QR code...</div>
          )}
        </div>
        <p className="text-xs text-[#4A5568] break-all">{url}</p>
        <div className="grid grid-cols-2 gap-3">
          <Button
            asChild={Boolean(poster)}
            disabled={!poster}
            data-testid="temple-qr-download"
            className="bg-[#721C24] hover:bg-[#5A161C] text-white"
          >
            {poster ? (
              <a href={poster} download={fileName}>
                <Download size={16} className="mr-2" />
                Download PNG
              </a>
            ) : (
              <span>Download PNG</span>
            )}
          </Button>
          <Button
            variant="outline"
            onClick={copyLink}
            className="border-2 border-[#721C24] text-[#721C24] hover:bg-[#721C24] hover:text-white"
          >
            <Copy size={16} className="mr-2" />
            Copy Link
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default TempleQrDialog;
