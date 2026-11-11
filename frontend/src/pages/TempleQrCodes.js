import { useEffect, useState } from 'react';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import TempleQrDialog, { isSuperAdminUser, renderTempleQr } from '../components/TempleQrDialog';
import { QrCode } from 'lucide-react';
import { toast } from 'sonner';

const TempleQrCard = ({ temple, onOpen }) => {
  const [preview, setPreview] = useState(null);

  useEffect(() => {
    let cancelled = false;
    renderTempleQr(temple, 320)
      .then((canvas) => { if (!cancelled) setPreview(canvas.toDataURL('image/png')); })
      .catch(() => setPreview(null));
    return () => { cancelled = true; };
  }, [temple]);

  return (
    <div data-testid={`qr-card-${temple.id}`} className="bg-white rounded-2xl shadow-sm border border-[#E2E8F0] p-5 flex flex-col items-center text-center">
      <div className="w-40 h-40 flex items-center justify-center">
        {preview && <img src={preview} alt={`Feedback QR code for ${temple.name}`} className="w-full h-full" />}
      </div>
      <p className="mt-4 font-bold text-[#721C24]">{temple.name}</p>
      <p className="text-sm text-[#4A5568]">{temple.location}</p>
      <Button
        onClick={() => onOpen(temple)}
        className="mt-4 w-full bg-[#721C24] hover:bg-[#5A161C] text-white"
      >
        View &amp; Download Poster
      </Button>
    </div>
  );
};

const TempleQrCodes = () => {
  const [temples, setTemples] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState(null);
  const allowed = isSuperAdminUser();

  useEffect(() => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    api.get('/temples')
      .then((res) => setTemples(res.data))
      .catch(() => toast.error('Failed to load temples'))
      .finally(() => setLoading(false));
  }, [allowed]);

  if (!allowed) {
    return <div className="text-center py-16 text-[#721C24] font-semibold">Temple QR codes are available to the Super Admin only.</div>;
  }

  if (loading) return <div className="text-center py-8">Loading...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <QrCode className="text-[#721C24]" size={36} />
        <div>
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-[#721C24]">Temple QR Codes</h1>
          <p className="text-[#4A5568] mt-1">
            Print each temple's poster and display it there. Devotees scan it to give feedback for that temple on their own phone.
          </p>
        </div>
      </div>

      {temples.length === 0 ? (
        <p className="text-center py-8 text-[#4A5568]">No temples yet. Add temples on the Temples page first.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          {temples.map((temple) => (
            <TempleQrCard key={temple.id} temple={temple} onOpen={setSelected} />
          ))}
        </div>
      )}

      <TempleQrDialog temple={selected} onClose={() => setSelected(null)} />
    </div>
  );
};

export default TempleQrCodes;
