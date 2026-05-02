import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API, getApiCandidates, setBackendUrlOverride } from '../utils/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import Header from '../components/Header';
import Footer from '../components/Footer';

const TempleSetup = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);

  const findTempleByEmail = async (templeEmail) => {
    const candidates = getApiCandidates();
    let lastError = null;

    for (const apiBase of candidates) {
      try {
        // Allow up to 60s per candidate so Azure SQL can wake from auto-pause on the first request.
        const response = await axios.get(`${apiBase}/temples`, { timeout: 60000 });
        const temple = response.data.find(
          (t) => t.email && t.email.toLowerCase() === templeEmail.toLowerCase()
        );

        const backendBase = apiBase.replace(/\/api$/, '');
        setBackendUrlOverride(backendBase);
        return temple;
      } catch (error) {
        lastError = error;
      }
    }

    throw lastError || new Error('Unable to reach backend');
  };

  const handleSetup = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      // Verify temple email exists
      const temple = await findTempleByEmail(email);

      if (!temple) {
        toast.error('Temple email not found. Please contact admin.');
        setLoading(false);
        return;
      }

      // Save temple info to localStorage (tablet registration)
      localStorage.setItem('registered_temple', JSON.stringify({
        id: temple.id,
        name: temple.name,
        email: temple.email,
        location: temple.location,
        logo_path: temple.logo_path,
        registered_at: new Date().toISOString()
      }));

      toast.success(`Tablet registered to ${temple.name}`);
      
      // Redirect to feedback form
      setTimeout(() => {
        navigate('/submit-feedback');
      }, 1500);

    } catch (error) {
      toast.error('Failed to register tablet. Please try again.');
      console.error('Temple registration error:', error.response?.data || error.message);
      if (error.response?.status === 401) {
        toast.error('Unauthorized: Check API token');
      } else if (error.code === 'ECONNABORTED') {
        toast.error('Request timeout: Check backend connection');
      } else if (error.code === 'ENOTFOUND' || error.code === 'ENETUNREACH') {
        toast.error('Cannot reach server: Check network and backend URL');
      } else if (error.message === 'Network Error') {
        toast.error('Network Error: Backend may be down or CORS blocked');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#FDFBF7]">
      <Header logo="/ts-logo.png" />
      
      <div
        className="flex-1 flex items-center justify-center bg-cover bg-center bg-no-repeat relative"
        style={{
          backgroundImage: 'url(https://customer-assets.emergentagent.com/job_temple-feedback-1/artifacts/0cablq1w_image.png)',
          minHeight: 'calc(100vh - 180px)',
        }}
      >
        <div className="absolute inset-0 bg-black/50"></div>

      <div className="relative z-10 bg-white/95 backdrop-blur-sm p-6 sm:p-10 rounded-2xl shadow-2xl w-full max-w-lg">
        <div className="text-center mb-8">
          <h1 className="text-3xl sm:text-5xl font-bold text-[#721C24] mb-3">Setup Temple</h1>
          <p className="text-base sm:text-lg text-[#4A5568]">Register this tablet for your temple</p>
        </div>

        <form onSubmit={handleSetup} className="space-y-6">
          <div>
            <Label htmlFor="email" className="text-[#721C24] font-medium text-lg">
              Temple Email *
            </Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              data-testid="temple-setup-email-input"
              placeholder="Enter temple email"
              className="mt-2 h-14 border-2 border-[#E2E8F0] focus:border-[#721C24] text-lg"
              required
            />
            <p className="text-sm text-[#4A5568] mt-2">
              This tablet will be registered to the temple associated with this email.
            </p>
          </div>

          <Button
            type="submit"
            disabled={loading}
            data-testid="temple-setup-submit-button"
            className="w-full h-16 bg-[#721C24] hover:bg-[#5A161C] text-white text-xl"
          >
            {loading ? 'Registering Tablet...' : 'Submit'}
          </Button>
        </form>

        <div className="mt-6 text-center text-sm text-[#4A5568]">
          <p>⚠️ This tablet will be locked to the selected temple.</p>
          <p className="mt-1">Contact admin to change temple registration.</p>
        </div>
      </div>
      </div>
      
      <Footer />
    </div>
  );
};

export default TempleSetup;