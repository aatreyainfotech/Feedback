import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../utils/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';

// Admins and officers live in separate tables, so one form tries the admin login and then the officer login.
const authenticate = async (credentials) => {
  try {
    const response = await axios.post(`${API}/auth/admin/login`, credentials);
    return { data: response.data, home: '/admin/dashboard' };
  } catch (error) {
    if (error.response?.status !== 401) throw error;
  }
  const response = await axios.post(`${API}/auth/officer/login`, credentials);
  return { data: response.data, home: '/officer/dashboard' };
};

const inputClass = 'mt-1.5 border-[#E2E8F0] focus:border-[#721C24] focus:ring-[#721C24]';
const submitClass = 'w-full bg-[#721C24] hover:bg-[#5A161C] text-white py-6 text-lg rounded-lg transition-all duration-300';
const linkClass = 'text-sm text-[#721C24] hover:underline font-medium';

const Login = () => {
  // Secure login - credentials hidden from UI
  const navigate = useNavigate();
  // 'login' -> 'forgot' (ask for OTP) -> 'reset' (enter OTP and new password)
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [identifier, setIdentifier] = useState('');
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const showLogin = () => {
    setMode('login');
    setOtp('');
    setNewPassword('');
    setConfirmPassword('');
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const { data, home } = await authenticate({ email, password });

      localStorage.setItem('token', data.token);
      localStorage.setItem('user', JSON.stringify(data.user));
      toast.success('Login successful!');
      navigate(home);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSendOtp = async (e) => {
    e?.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post(`${API}/auth/forgot-password`, { identifier });
      toast.success(response.data.message);
      setMode('reset');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Could not send OTP');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async (e) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }
    setLoading(true);
    try {
      const response = await axios.post(`${API}/auth/reset-password`, {
        identifier,
        otp,
        new_password: newPassword,
      });
      toast.success(response.data.message);
      if (identifier.includes('@')) setEmail(identifier);
      setPassword('');
      showLogin();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Could not reset password');
    } finally {
      setLoading(false);
    }
  };

  const titles = { login: 'Feedback Login', forgot: 'Forgot Password', reset: 'Reset Password' };

  return (
    <div
      className="min-h-screen flex items-center justify-center bg-cover bg-center bg-no-repeat relative px-4"
      style={{
        backgroundImage:
          'url(https://customer-assets.emergentagent.com/job_temple-feedback-1/artifacts/0cablq1w_image.png)',
      }}
    >
      <div className="absolute inset-0 bg-black/50"></div>

      <div className="relative z-10 bg-white/95 backdrop-blur-sm p-8 rounded-2xl shadow-2xl w-full max-w-md">
        <div className="text-center mb-6">
          <h1 className="text-4xl font-bold text-[#721C24] mb-2">{titles[mode]}</h1>
          <p className="text-[#4A5568]">Temple Feedback Management System</p>
        </div>

        {mode === 'login' && (
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
                data-testid="login-email-input"
                placeholder="you@temple.com"
                className={inputClass}
                required
              />
            </div>

            <div>
              <div className="flex items-center justify-between">
                <Label htmlFor="password" className="text-[#721C24] font-medium">
                  Password
                </Label>
                <button
                  type="button"
                  onClick={() => {
                    setIdentifier(email);
                    setMode('forgot');
                  }}
                  data-testid="forgot-password-link"
                  className={linkClass}
                >
                  Forgot password?
                </button>
              </div>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                data-testid="login-password-input"
                placeholder="Enter your password"
                className={inputClass}
                required
              />
            </div>

            <Button type="submit" disabled={loading} data-testid="login-button" className={submitClass}>
              {loading ? 'Logging in...' : 'Login'}
            </Button>
          </form>
        )}

        {mode === 'forgot' && (
          <form onSubmit={handleSendOtp} className="space-y-5">
            <div>
              <Label htmlFor="identifier" className="text-[#721C24] font-medium">
                Email or mobile number
              </Label>
              <Input
                id="identifier"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                data-testid="forgot-identifier-input"
                placeholder="you@temple.com or 10-digit mobile"
                className={inputClass}
                required
              />
              <p className="text-xs text-[#4A5568] mt-2">
                We will send an OTP on WhatsApp to the mobile number saved on your account.
              </p>
            </div>

            <Button type="submit" disabled={loading} data-testid="send-otp-button" className={submitClass}>
              {loading ? 'Sending...' : 'Send OTP on WhatsApp'}
            </Button>
          </form>
        )}

        {mode === 'reset' && (
          <form onSubmit={handleReset} className="space-y-5">
            <p className="text-sm text-[#4A5568]">
              Enter the 6-digit OTP sent on WhatsApp for <span className="font-medium">{identifier}</span>. It is valid for 10 minutes.
            </p>
            <div>
              <Label htmlFor="otp" className="text-[#721C24] font-medium">
                OTP
              </Label>
              <Input
                id="otp"
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="[0-9]{6}"
                maxLength={6}
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                data-testid="reset-otp-input"
                placeholder="6-digit OTP"
                className={inputClass}
                required
              />
            </div>
            <div>
              <Label htmlFor="new-password" className="text-[#721C24] font-medium">
                New password
              </Label>
              <Input
                id="new-password"
                type="password"
                minLength={6}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                data-testid="reset-new-password-input"
                placeholder="At least 6 characters"
                className={inputClass}
                required
              />
            </div>
            <div>
              <Label htmlFor="confirm-password" className="text-[#721C24] font-medium">
                Confirm new password
              </Label>
              <Input
                id="confirm-password"
                type="password"
                minLength={6}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                data-testid="reset-confirm-password-input"
                placeholder="Re-enter new password"
                className={inputClass}
                required
              />
            </div>

            <Button type="submit" disabled={loading} data-testid="reset-password-button" className={submitClass}>
              {loading ? 'Saving...' : 'Reset Password'}
            </Button>
            <div className="text-center">
              <button type="button" onClick={() => handleSendOtp()} disabled={loading} className={linkClass}>
                Resend OTP
              </button>
            </div>
          </form>
        )}

        {mode !== 'login' && (
          <div className="mt-6 text-center">
            <button type="button" onClick={showLogin} className={linkClass}>
              ← Back to Login
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Login;
