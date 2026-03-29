import { Outlet, useNavigate } from 'react-router-dom';
import { useEffect } from 'react';
import { LogOut } from 'lucide-react';
import Header from './Header';
import Footer from './Footer';

const OfficerLayout = () => {
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('token');
    let user = null;
    const userString = localStorage.getItem('user');

    if (userString) {
      try {
        user = JSON.parse(userString);
      } catch {
        user = null;
      }
    }

    if (user && user.user) {
      user = user.user;
    }

    const userRole = user?.role;
    console.log('OfficerLayout auth check', { token, user, userRole });

    if (!token || !user || userRole !== 'officer') {
      navigate('/officer/login');
    }
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/officer/login');
  };

  const user = JSON.parse(localStorage.getItem('user') || '{}');

  return (
    <div className="flex flex-col min-h-screen bg-gradient-to-b from-[#721C24] to-[#4A1016]">
      <Header logo="/ts-logo.png" />
      
      <div className="flex flex-1">
        {/* Sidebar */}
        <aside className="w-64 flex flex-col p-6 text-white">
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-[#F4C430]">Officer Portal</h1>
            <p className="text-sm text-white/70 mt-1">{user.officer?.temple_name || 'Temple'}</p>
            <p className="text-xs text-white/60 mt-2">{user.officer?.name}</p>
          </div>

          <div className="flex-1"></div>

          <button
            onClick={handleLogout}
            data-testid="officer-logout-button"
            className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-white/10 transition-all duration-300"
          >
            <LogOut size={20} strokeWidth={1.5} />
            <span className="font-medium">Logout</span>
          </button>
        </aside>

        {/* Main Content with Temple Background */}
        <main 
          className="flex-1 rounded-tl-[2.5rem] p-8 overflow-y-auto custom-scrollbar relative"
          style={{
            backgroundImage: 'url(https://images.pexels.com/photos/6416960/pexels-photo-6416960.jpeg?auto=compress&cs=tinysrgb&w=1920)',
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            backgroundAttachment: 'fixed'
          }}
        >
          <div className="absolute inset-0 bg-gradient-to-br from-[#FDFBF7]/85 to-[#FFF9E6]/80 rounded-tl-[2.5rem]"></div>
          <div className="relative z-10">
            <Outlet />
          </div>
        </main>
      </div>
      
      <Footer />
    </div>
  );
};

export default OfficerLayout;