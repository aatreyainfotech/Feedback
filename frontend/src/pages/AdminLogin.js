import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../utils/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';

const AdminLogin = () => {
  // Secure login - credentials hidden from UI
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await axios.post(`${API}/auth/admin/login`, {
        email,
        password,
      });

      localStorage.setItem('token', response.data.token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      toast.success('Login successful!');
      navigate('/admin/dashboard');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center bg-cover bg-center bg-no-repeat relative"
      style={{
        backgroundImage:
          'url(https://customer-assets.emergentagent.com/job_temple-feedback-1/artifacts/0cablq1w_image.png)',
      }}
    >
      <div className="absolute inset-0 bg-black/50"></div>

      <div className="relative z-10 bg-white/95 backdrop-blur-sm p-8 rounded-2xl shadow-2xl w-full max-w-md">
        <div className="text-center mb-6">
          <h1 className="text-4xl font-bold text-[#721C24] mb-2">Admin Login</h1>
          <p className="text-[#4A5568]">Temple Feedback Management System</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-5">
          <div>
            <Label htmlFor="email" className="text-[#721C24] font-medium">
              Email
            </Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              data-testid="admin-email-input"
              placeholder="admin@temple.com"
              className="mt-1.5 border-[#E2E8F0] focus:border-[#721C24] focus:ring-[#721C24]"
              required
            />
          </div>

          <div>
            <Label htmlFor="password" className="text-[#721C24] font-medium">
              Password
            </Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              data-testid="admin-password-input"
              placeholder="Enter your password"
              className="mt-1.5 border-[#E2E8F0] focus:border-[#721C24] focus:ring-[#721C24]"
              required
            />
          </div>

          <Button
            type="submit"
            disabled={loading}
            data-testid="admin-login-button"
            className="w-full bg-[#721C24] hover:bg-[#5A161C] text-white py-6 text-lg rounded-lg transition-all duration-300"
          >
            {loading ? 'Logging in...' : 'Login'}
          </Button>
        </form>

        <div className="mt-6 text-center text-sm text-[#4A5568]">
          
          <button
            onClick={() => navigate('/officer/login')}
            className="mt-3 text-[#721C24] hover:underline font-medium"
          >
            Officer Login →
          </button>
        </div>
      </div>
    </div>
  );
};

export default AdminLogin;