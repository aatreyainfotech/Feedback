import { useState, useEffect } from 'react';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Plus, Trash2, Edit2 } from 'lucide-react';
import { toast } from 'sonner';

const serviceIcons = {
  'Annadhanam': '🍚',
  'Darshan': '🙏',
  'Prasadam': '🍲',
  'Pooja': '🪔',
  'Donation': '💰',
  'Other': '📝',
  'General': '📋',
  'Seva': '🙏',
  'Archana': '🌸',
  'Abhishekam': '💧',
  'Homam': '🔥',
  'Marriage': '💍',
  'Blessing': '✨',
  'Priest': '👳',
  'Pujari': '👳',
  'Temple': '🛕',
  'Ticket': '🎫',
  'VIP': '⭐',
  'Queue': '📊',
  'Accommodation': '🏨',
  'Parking': '🅿️',
  'Laddu': '🍪',
  'Flowers': '💐',
  'Kalyanam': '💒',
  'Annaprasana': '🍼',
  'Naamkaran': '📜',
  'Upanayanam': '📿',
  'Satyanarayana': '🙏',
  'Ganapathi': '🐘',
  'Lakshmi': '🪷',
  'Vishnu': '🔱',
  'Shiva': '🕉️'
};

const getServiceIcon = (name) => {
  return serviceIcons[name] || '📋';
};

const Services = () => {
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [serviceName, setServiceName] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage] = useState(8);


  useEffect(() => {
    fetchServices();
  }, []);

  const fetchServices = async () => {
    try {
      const response = await api.get('/services');
      setServices(response.data);
    } catch (error) {
      toast.error('Failed to fetch services');
    } finally {
      setLoading(false);
    }
  };

  const totalPages = Math.max(1, Math.ceil(services.length / rowsPerPage));
  const pagedServices = services.slice((currentPage - 1) * rowsPerPage, currentPage * rowsPerPage);
  const handlePageChange = (newPage) => {
    if (newPage < 1 || newPage > totalPages) return;
    setCurrentPage(newPage);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!serviceName.trim()) {
      toast.error('Please enter service name');
      return;
    }

    try {
      await api.post('/services', null, {
        params: { name: serviceName }
      });
      toast.success('Service created successfully');
      setOpen(false);
      setServiceName('');
      fetchServices();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create service');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this service?')) return;
    try {
      await api.delete(`/services/${id}`);
      toast.success('Service deleted successfully');
      fetchServices();
    } catch (error) {
      toast.error('Failed to delete service');
    }
  };

  if (loading) {
    return <div className="text-center py-8">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-2">Services</h1>
          <p className="text-[#4A5568]">Manage feedback service categories</p>
        </div>

        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button
              data-testid="add-service-button"
              className="bg-[#721C24] hover:bg-[#5A161C] text-white"
            >
              <Plus size={20} className="mr-2" />
              Add Service
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-white">
            <DialogHeader>
              <DialogTitle className="text-[#721C24] text-2xl">Add New Service</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label htmlFor="name" className="text-[#721C24]">Service Name</Label>
                <Input
                  id="name"
                  value={serviceName}
                  onChange={(e) => setServiceName(e.target.value)}
                  data-testid="service-name-input"
                  placeholder="Enter service name"
                  required
                  className="mt-1.5"
                />
                <p className="text-sm text-[#4A5568] mt-2">
                  Suggested: Annadhanam, Darshan, Prasadam, Pooja, Donation, Seva, Archana
                </p>
              </div>
              <Button
                type="submit"
                data-testid="submit-service-button"
                className="w-full bg-[#721C24] hover:bg-[#5A161C] text-white"
              >
                Create Service
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="bg-white rounded-2xl shadow-sm overflow-hidden p-6">
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {pagedServices.map((service) => (
            <div
              key={service.id}
              data-testid={`service-row-${service.id}`}
              className="relative group bg-gradient-to-br from-[#FDFBF7] to-white border-2 border-[#E8D5B7] rounded-xl p-6 text-center hover:shadow-lg hover:border-[#721C24] transition-all duration-300"
            >
              {/* Icon */}
              <div className="text-4xl mb-3">{getServiceIcon(service.name)}</div>
              
              {/* Service Name */}
              <h3 className="font-semibold text-[#721C24] text-lg">{service.name}</h3>
              
              {/* Delete Button - Shows on hover */}
              <button
                onClick={() => handleDelete(service.id)}
                data-testid={`delete-service-${service.id}`}
                className="absolute top-2 right-2 w-8 h-8 bg-red-100 hover:bg-red-500 text-red-600 hover:text-white rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all duration-300"
              >
                <Trash2 size={16} />
              </button>
              
              {/* Decorative corner */}
              <div className="absolute bottom-0 right-0 w-8 h-8 bg-[#F4C430] rounded-tl-xl opacity-20"></div>
            </div>
          ))}
        </div>

        {services.length === 0 && (
          <div className="text-center py-12 text-[#4A5568]">
            <div className="text-6xl mb-4">📋</div>
            <p className="text-lg">No services added yet</p>
            <p className="text-sm">Click "Add Service" to create your first service category</p>
          </div>
        )}

        {services.length > 0 && (
          <div className="flex items-center justify-between p-4 bg-white border-t border-slate-200">
            <div className="text-sm text-slate-500">
              Showing {Math.min((currentPage - 1) * rowsPerPage + 1, services.length)} - {Math.min(currentPage * rowsPerPage, services.length)} of {services.length}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage === 1}
                className="px-3 py-1 rounded-lg border border-slate-300 bg-white text-slate-600 hover:bg-slate-100 disabled:opacity-50"
              >
                Prev
              </button>
              {[...Array(totalPages)].map((_, idx) => {
                const page = idx + 1;
                return (
                  <button
                    key={page}
                    onClick={() => handlePageChange(page)}
                    className={`px-3 py-1 rounded-lg border ${page === currentPage ? 'border-[#721C24] bg-[#721C24] text-white' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-100'}`}
                  >
                    {page}
                  </button>
                );
              })}
              <button
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="px-3 py-1 rounded-lg border border-slate-300 bg-white text-slate-600 hover:bg-slate-100 disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Services;