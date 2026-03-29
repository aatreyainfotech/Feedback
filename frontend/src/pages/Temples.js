import { useState, useEffect } from 'react';
import api, { API } from '../utils/api';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Plus, Trash2, Edit, Upload } from 'lucide-react';
import { toast } from 'sonner';

const Temples = () => {
  const [temples, setTemples] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage] = useState(5);
  const [editingTemple, setEditingTemple] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    location: '',
    email: '',
    logo_path: '',
  });

  useEffect(() => {
    fetchTemples();
  }, []);

  const fetchTemples = async () => {
    try {
      const response = await api.get('/temples');
      setTemples(response.data);
    } catch (error) {
      toast.error('Failed to fetch temples');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingTemple) {
        await api.put(`/temples/${editingTemple.id}`, formData);
        toast.success('Temple updated successfully');
      } else {
        await api.post('/temples', formData);
        toast.success('Temple created successfully');
      }
      setOpen(false);
      setFormData({ name: '', location: '' });
      setEditingTemple(null);
      fetchTemples();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Operation failed');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this temple?')) return;
    try {
      await api.delete(`/temples/${id}`);
      toast.success('Temple deleted successfully');
      fetchTemples();
    } catch (error) {
      toast.error('Failed to delete temple');
    }
  };

  const handleEdit = (temple) => {
    setEditingTemple(temple);
    setFormData({ 
      name: temple.name, 
      location: temple.location, 
      email: temple.email || '',
      logo_path: temple.logo_path || ''
    });
    setOpen(true);
  };

  const handleCloseDialog = () => {
    setOpen(false);
    setEditingTemple(null);
    setFormData({ name: '', location: '', email: '', logo_path: '' });
  };

  const handleLogoUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      toast.error('Please select an image file');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      toast.error('Logo file is too large. Maximum size is 5MB.');
      return;
    }

    setUploading(true);
    try {
      const uploadFormData = new FormData();
      uploadFormData.append('file', file);

      const response = await axios.post(`${API}/upload/logo`, uploadFormData, {
        headers: { 
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      setFormData({ ...formData, logo_path: response.data.path });
      toast.success('Logo uploaded successfully');
    } catch (error) {
      toast.error('Failed to upload logo');
    } finally {
      setUploading(false);
    }
  };

  const totalPages = Math.max(1, Math.ceil(temples.length / rowsPerPage));
  const pagedTemples = temples.slice((currentPage - 1) * rowsPerPage, currentPage * rowsPerPage);
  const handlePageChange = (newPage) => {
    if (newPage < 1 || newPage > totalPages) return;
    setCurrentPage(newPage);
  };

  if (loading) {
    return <div className="text-center py-8">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-2">Temples</h1>
          <p className="text-[#4A5568]">Manage temple locations and services</p>
        </div>

        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button
              data-testid="add-temple-button"
              onClick={() => handleCloseDialog()}
              className="bg-[#721C24] hover:bg-[#5A161C] text-white"
            >
              <Plus size={20} className="mr-2" />
              Add Temple
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-white">
            <DialogHeader>
              <DialogTitle className="text-[#721C24] text-2xl">
                {editingTemple ? 'Edit Temple' : 'Add New Temple'}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label htmlFor="name" className="text-[#721C24]">Temple Name</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  data-testid="temple-name-input"
                  placeholder="Enter temple name"
                  required
                  className="mt-1.5"
                />
              </div>
              <div>
                <Label htmlFor="location" className="text-[#721C24]">Location</Label>
                <Input
                  id="location"
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  data-testid="temple-location-input"
                  placeholder="Enter location"
                  required
                  className="mt-1.5"
                />
              </div>
              <div>
                <Label htmlFor="email" className="text-[#721C24]">Temple Email (Optional)</Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email || ''}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  data-testid="temple-email-input"
                  placeholder="Enter temple email"
                  className="mt-1.5"
                />
              </div>
              <div>
                <Label className="text-[#721C24]">Temple Logo (Optional)</Label>
                <div className="mt-2 space-y-3">
                  {formData.logo_path && (
                    <div className="flex items-center gap-3 p-3 bg-[#FFF9E6] rounded-lg border border-[#E2E8F0]">
                      <img 
                        src={`${API}/files/${formData.logo_path}`}
                        alt="Temple Logo"
                        className="w-16 h-16 object-contain rounded border border-[#721C24]"
                      />
                      <span className="text-sm text-[#4A5568]">Logo uploaded</span>
                    </div>
                  )}
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleLogoUpload}
                    className="hidden"
                    id="logo-upload"
                    disabled={uploading}
                  />
                  <label htmlFor="logo-upload">
                    <Button
                      type="button"
                      onClick={() => document.getElementById('logo-upload').click()}
                      disabled={uploading}
                      variant="outline"
                      className="w-full border-2 border-[#721C24] text-[#721C24] hover:bg-[#721C24] hover:text-white"
                    >
                      <Upload size={18} className="mr-2" />
                      {uploading ? 'Uploading...' : formData.logo_path ? 'Change Logo' : 'Upload Logo'}
                    </Button>
                  </label>
                  <p className="text-xs text-[#4A5568]">Max size: 5MB | Format: PNG, JPG, JPEG</p>
                </div>
              </div>
              <Button
                type="submit"
                data-testid="submit-temple-button"
                className="w-full bg-[#721C24] hover:bg-[#5A161C] text-white"
              >
                {editingTemple ? 'Update Temple' : 'Create Temple'}
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-[#FDFBF7] hover:bg-[#FDFBF7]">
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider">
                Logo
              </TableHead>
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider">
                Temple Name
              </TableHead>
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider">
                Location
              </TableHead>
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider text-right">
                Actions
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {pagedTemples.map((temple) => (
              <TableRow
                key={temple.id}
                data-testid={`temple-row-${temple.id}`}
                className="hover:bg-[#FFF9E6] transition-colors"
              >
                <TableCell>
                  {temple.logo_path ? (
                    <img 
                      src={`${API}/files/${temple.logo_path}`}
                      alt={`${temple.name} logo`}
                      className="w-12 h-12 object-contain rounded border border-[#E2E8F0]"
                    />
                  ) : (
                    <div className="w-12 h-12 bg-[#FFF9E6] rounded border border-[#E2E8F0] flex items-center justify-center text-xs text-[#721C24]">
                      No Logo
                    </div>
                  )}
                </TableCell>
                <TableCell className="font-medium">{temple.name}</TableCell>
                <TableCell className="text-[#4A5568]">{temple.location}</TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleEdit(temple)}
                      data-testid={`edit-temple-${temple.id}`}
                      className="text-[#721C24] hover:bg-[#721C24]/10"
                    >
                      <Edit size={16} />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(temple.id)}
                      data-testid={`delete-temple-${temple.id}`}
                      className="text-red-600 hover:bg-red-50"
                    >
                      <Trash2 size={16} />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <div className="flex items-center justify-between p-4 bg-white border-t border-slate-200">
          <div className="text-sm text-slate-500">
            Showing {Math.min((currentPage - 1) * rowsPerPage + 1, temples.length)} - {Math.min(currentPage * rowsPerPage, temples.length)} of {temples.length}
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

      </div>
    </div>
  );
};

export default Temples;