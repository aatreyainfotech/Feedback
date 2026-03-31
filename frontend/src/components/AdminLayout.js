import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { LayoutDashboard, Building2, Users, List, MessageSquare, MessageCircle, FileText, LogOut, Settings, Menu, X } from 'lucide-react';
import Header from './Header';
import Footer from './Footer';

const AdminLayout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);

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
    console.log('AdminLayout auth check', { token, user, userRole });

    if (!token || !user || userRole !== 'admin') {
      navigate('/login');
    }
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/login');
  };

  const menuItems = [
    { path: '/admin/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/admin/temples', icon: Building2, label: 'Temples' },
    { path: '/admin/officers', icon: Users, label: 'Officers' },
    { path: '/admin/services', icon: List, label: 'Services' },
    { path: '/admin/feedback', icon: MessageSquare, label: 'Feedback' },
    { path: '/admin/whatsapp-logs', icon: MessageCircle, label: 'WhatsApp Logs' },
    { path: '/admin/reports', icon: FileText, label: 'Reports' },
    { path: '/admin/administration', icon: Settings, label: 'Administration' },
  ];

  return (
    <div className="flex flex-col min-h-screen bg-gradient-to-b from-[#721C24] to-[#4A1016]">
      <Header logo="/ts-logo.png" />

      {/* Mobile hamburger button */}
      <button
        className="md:hidden fixed top-4 left-4 z-50 bg-[#721C24] text-white p-2 rounded-lg shadow-lg"
        onClick={() => setSidebarOpen(!sidebarOpen)}
        aria-label="Toggle menu"
      >
        {sidebarOpen ? <X size={22} /> : <Menu size={22} />}
      </button>

      {/* Mobile overlay backdrop */}
      {sidebarOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black/50 z-30"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <div className="flex flex-1">
        {/* Sidebar — overlay on mobile, always visible on md+ */}
        <aside className={`
          fixed md:relative inset-y-0 left-0 z-40
          w-64 flex flex-col p-6 text-white
          bg-gradient-to-b from-[#721C24] to-[#4A1016]
          transform transition-transform duration-300 ease-in-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
          md:flex
        `}>
          <div className="mb-8 mt-12 md:mt-0">
            <h1 className="text-2xl font-bold text-[#F4C430]">Temple Admin</h1>
            <p className="text-sm text-white/70 mt-1">Feedback Management</p>
          </div>

          <nav className="flex-1 space-y-2 custom-scrollbar overflow-y-auto">
            {menuItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  data-testid={`menu-${item.label.toLowerCase().replace(' ', '-')}`}
                  onClick={() => setSidebarOpen(false)}
                  className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-300 ${
                    isActive
                      ? 'bg-white/20 shadow-lg scale-105'
                      : 'hover:bg-white/10'
                  }`}
                >
                  <Icon size={20} strokeWidth={1.5} />
                  <span className="font-medium">{item.label}</span>
                </Link>
              );
            })}
          </nav>

          <button
            onClick={handleLogout}
            data-testid="logout-button"
            className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-white/10 transition-all duration-300 mt-4"
          >
            <LogOut size={20} strokeWidth={1.5} />
            <span className="font-medium">Logout</span>
          </button>
        </aside>

        {/* Main Content with Temple Background */}
        <main
          className="flex-1 rounded-tl-[2.5rem] p-4 md:p-8 overflow-y-auto custom-scrollbar relative"
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

export default AdminLayout;