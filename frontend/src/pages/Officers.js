import { useState, useEffect } from 'react';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { KeyRound, Pencil, Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

const defaultFormData = {
  name: '',
  email: '',
  password: '',
  temple_id: '',
  role: 'officer',
  permissions: ['view_feedback', 'update_status'],
};

const Officers = () => {
  const [officers, setOfficers] = useState([]);
  const [temples, setTemples] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editingOfficerId, setEditingOfficerId] = useState(null);
  const [resetPasswordOpen, setResetPasswordOpen] = useState(false);
  const [resetOfficer, setResetOfficer] = useState(null);
  const [newPassword, setNewPassword] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage] = useState(5);
  const [formData, setFormData] = useState(defaultFormData);

  const roleOptions = [
    { value: 'officer', label: 'Officer', description: 'Can view and update feedback status' },
    { value: 'supervisor', label: 'Supervisor', description: 'Can manage officers and feedback' },
    { value: 'eo', label: 'Executive Officer (EO)', description: 'Full access to temple operations' },
  ];

  const permissionOptions = [
    { value: 'view_feedback', label: 'View Feedback' },
    { value: 'update_status', label: 'Update Status' },
    { value: 'assign_officers', label: 'Assign Officers' },
    { value: 'delete_feedback', label: 'Delete Feedback' },
    { value: 'manage_services', label: 'Manage Services' },
    { value: 'view_reports', label: 'View Reports' },
    { value: 'export_data', label: 'Export Data' },
  ];

  useEffect(() => {
    fetchOfficers();
    fetchTemples();
  }, []);

  const resetForm = () => {
    setFormData(defaultFormData);
    setEditingOfficerId(null);
  };

  const handleDialogChange = (isOpen) => {
    setOpen(isOpen);
    if (!isOpen) {
      resetForm();
    }
  };

  const handleCreateClick = () => {
    resetForm();
    setOpen(true);
  };

  const handleEdit = (officer) => {
    setEditingOfficerId(officer.id);
    setFormData({
      name: officer.name || '',
      email: officer.email || '',
      password: '',
      temple_id: officer.temple_id || '',
      role: officer.role || 'officer',
      permissions: officer.permissions || ['view_feedback', 'update_status'],
    });
    setOpen(true);
  };

  const handleResetPasswordOpen = (officer) => {
    setResetOfficer(officer);
    setNewPassword('');
    setResetPasswordOpen(true);
  };

  const handleResetPasswordClose = (isOpen) => {
    setResetPasswordOpen(isOpen);
    if (!isOpen) {
      setResetOfficer(null);
      setNewPassword('');
    }
  };

  const fetchOfficers = async () => {
    try {
      const response = await api.get('/officers');
      setOfficers(response.data);
    } catch (error) {
      toast.error('Failed to fetch officers');
    } finally {
      setLoading(false);
    }
  };

  const fetchTemples = async () => {
    try {
      const response = await api.get('/temples');
      setTemples(response.data);
    } catch (error) {
      console.error('Failed to fetch temples');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingOfficerId) {
        await api.put(`/officers/${editingOfficerId}`, formData);
        toast.success('Officer updated successfully');
      } else {
        await api.post('/officers', formData);
        toast.success('Officer created successfully');
      }
      setOpen(false);
      resetForm();
      fetchOfficers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Operation failed');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this officer?')) return;
    try {
      await api.delete(`/officers/${id}`);
      toast.success('Officer deleted successfully');
      fetchOfficers();
    } catch (error) {
      toast.error('Failed to delete officer');
    }
  };

  const handlePasswordReset = async (e) => {
    e.preventDefault();
    if (!resetOfficer) return;

    try {
      await api.put(`/officers/${resetOfficer.id}/reset-password`, { password: newPassword });
      toast.success('Password reset successfully');
      handleResetPasswordClose(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reset password');
    }
  };

  const totalPages = Math.max(1, Math.ceil(officers.length / rowsPerPage));
  const pagedOfficers = officers.slice((currentPage - 1) * rowsPerPage, currentPage * rowsPerPage);
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
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-2">Officers</h1>
          <p className="text-[#4A5568]">Manage temple officers and access</p>
        </div>

        <Dialog open={open} onOpenChange={handleDialogChange}>
          <DialogTrigger asChild>
            <Button
              data-testid="add-officer-button"
              className="bg-[#721C24] hover:bg-[#5A161C] text-white"
              onClick={handleCreateClick}
            >
              <Plus size={20} className="mr-2" />
              Add Officer
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-white">
            <DialogHeader>
              <DialogTitle className="text-[#721C24] text-2xl">
                {editingOfficerId ? 'Edit Officer' : 'Add New Officer'}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label htmlFor="name" className="text-[#721C24]">Officer Name</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  data-testid="officer-name-input"
                  placeholder="Enter officer name"
                  required
                  className="mt-1.5"
                />
              </div>
              <div>
                <Label htmlFor="email" className="text-[#721C24]">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  data-testid="officer-email-input"
                  placeholder="Enter email"
                  required
                  className="mt-1.5"
                />
              </div>
              <div>
                <Label htmlFor="password" className="text-[#721C24]">
                  {editingOfficerId ? 'Password (leave blank to keep current password)' : 'Password'}
                </Label>
                <Input
                  id="password"
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  data-testid="officer-password-input"
                  placeholder={editingOfficerId ? 'Leave blank to keep current password' : 'Enter password'}
                  required={!editingOfficerId}
                  className="mt-1.5"
                />
              </div>
              <div>
                <Label htmlFor="temple" className="text-[#721C24]">Assign Temple</Label>
                <Select
                  value={formData.temple_id}
                  onValueChange={(value) => setFormData({ ...formData, temple_id: value })}
                >
                  <SelectTrigger className="mt-1.5" data-testid="officer-temple-select">
                    <SelectValue placeholder="Select temple" />
                  </SelectTrigger>
                  <SelectContent className="bg-white">
                    {temples.map((temple) => (
                      <SelectItem key={temple.id} value={temple.id}>
                        {temple.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="role" className="text-[#721C24]">Role</Label>
                <Select
                  value={formData.role}
                  onValueChange={(value) => setFormData({ ...formData, role: value })}
                >
                  <SelectTrigger className="mt-1.5" data-testid="officer-role-select">
                    <SelectValue placeholder="Select role" />
                  </SelectTrigger>
                  <SelectContent className="bg-white">
                    {roleOptions.map((role) => (
                      <SelectItem key={role.value} value={role.value}>
                        <div>
                          <span className="font-medium">{role.label}</span>
                          <span className="text-xs text-[#4A5568] ml-2">- {role.description}</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-[#721C24]">Permissions</Label>
                <div className="grid grid-cols-2 gap-2 mt-2">
                  {permissionOptions.map((perm) => (
                    <label key={perm.value} className="flex items-center gap-2 text-sm cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.permissions.includes(perm.value)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setFormData({ ...formData, permissions: [...formData.permissions, perm.value] });
                          } else {
                            setFormData({ ...formData, permissions: formData.permissions.filter(p => p !== perm.value) });
                          }
                        }}
                        className="w-4 h-4 text-[#721C24] border-[#721C24] rounded focus:ring-[#721C24]"
                      />
                      <span className="text-[#4A5568]">{perm.label}</span>
                    </label>
                  ))}
                </div>
              </div>
              <Button
                type="submit"
                data-testid="submit-officer-button"
                className="w-full bg-[#721C24] hover:bg-[#5A161C] text-white"
              >
                {editingOfficerId ? 'Update Officer' : 'Create Officer'}
              </Button>
            </form>
          </DialogContent>
        </Dialog>

        <Dialog open={resetPasswordOpen} onOpenChange={handleResetPasswordClose}>
          <DialogContent className="bg-white">
            <DialogHeader>
              <DialogTitle className="text-[#721C24] text-2xl">Reset Officer Password</DialogTitle>
            </DialogHeader>
            <form onSubmit={handlePasswordReset} className="space-y-4">
              <div>
                <Label className="text-[#721C24]">Officer</Label>
                <div className="mt-1.5 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
                  {resetOfficer ? `${resetOfficer.name} (${resetOfficer.email})` : ''}
                </div>
              </div>
              <div>
                <Label htmlFor="reset-password" className="text-[#721C24]">New Password</Label>
                <Input
                  id="reset-password"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Enter new password"
                  required
                  minLength={6}
                  className="mt-1.5"
                />
              </div>
              <Button
                type="submit"
                data-testid="reset-password-submit"
                className="w-full bg-[#721C24] hover:bg-[#5A161C] text-white"
              >
                Reset Password
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="bg-[#FDFBF7] hover:bg-[#FDFBF7]">
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider">
                Name
              </TableHead>
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider">
                Email
              </TableHead>
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider">
                Temple
              </TableHead>
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider">
                Role
              </TableHead>
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider text-right">
                Actions
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {pagedOfficers.map((officer) => (
              <TableRow
                key={officer.id}
                data-testid={`officer-row-${officer.id}`}
                className="hover:bg-[#FFF9E6] transition-colors"
              >
                <TableCell className="font-medium">{officer.name}</TableCell>
                <TableCell className="text-[#4A5568]">{officer.email}</TableCell>
                <TableCell className="text-[#4A5568]">{officer.temple_name || 'Not assigned'}</TableCell>
                <TableCell>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    officer.role === 'eo' ? 'bg-purple-100 text-purple-700' :
                    officer.role === 'supervisor' ? 'bg-blue-100 text-blue-700' :
                    'bg-green-100 text-green-700'
                  }`}>
                    {officer.role === 'eo' ? 'Executive Officer' : 
                     officer.role === 'supervisor' ? 'Supervisor' : 'Officer'}
                  </span>
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-1 sm:gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleEdit(officer)}
                      data-testid={`edit-officer-${officer.id}`}
                      className="text-[#721C24] hover:bg-[#FFF1F2]"
                    >
                      <Pencil size={16} className="mr-1" />
                      <span className="hidden sm:inline">Edit</span>
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleResetPasswordOpen(officer)}
                      data-testid={`reset-password-${officer.id}`}
                      className="text-amber-700 hover:bg-amber-50"
                    >
                      <KeyRound size={16} className="mr-1" />
                      <span className="hidden sm:inline">Reset Password</span>
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(officer.id)}
                      data-testid={`delete-officer-${officer.id}`}
                      className="text-red-600 hover:bg-red-50"
                    >
                      <Trash2 size={16} className="mr-1" />
                      <span className="hidden sm:inline">Delete</span>
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        </div>
        <div className="flex items-center justify-between p-4 bg-white border-t border-slate-200">
          <div className="text-sm text-slate-500">
            Showing {Math.min((currentPage - 1) * rowsPerPage + 1, officers.length)} - {Math.min(currentPage * rowsPerPage, officers.length)} of {officers.length}
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

export default Officers;