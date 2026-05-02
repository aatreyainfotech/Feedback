import { useState, useEffect } from 'react';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Users, Shield, Key, Edit2, Trash2, Plus } from 'lucide-react';
import { toast } from 'sonner';

const Administration = () => {
  const [officers, setOfficers] = useState([]);
  const [temples, setTemples] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editOpen, setEditOpen] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage] = useState(5);
  const [addOpen, setAddOpen] = useState(false);
  const [selectedOfficer, setSelectedOfficer] = useState(null);
  const [newOfficer, setNewOfficer] = useState({
    name: '',
    email: '',
    password: '',
    temple_id: '',
    role: 'officer',
    permissions: ['view_feedback', 'update_status'],
  });

  const roleOptions = [
    { value: 'officer', label: 'Officer', color: 'bg-green-100 text-green-700' },
    { value: 'supervisor', label: 'Supervisor', color: 'bg-blue-100 text-blue-700' },
    { value: 'eo', label: 'Executive Officer', color: 'bg-purple-100 text-purple-700' },
    { value: 'asst_commissioner', label: 'Asst Commissioner', color: 'bg-amber-100 text-amber-700' },
    { value: 'commissioner', label: 'Commissioner', color: 'bg-red-100 text-red-700' },
  ];

  const permissionOptions = [
    { value: 'view_feedback', label: 'View Feedback', icon: '👁️' },
    { value: 'update_status', label: 'Update Status', icon: '✏️' },
    { value: 'assign_officers', label: 'Assign Officers', icon: '👥' },
    { value: 'delete_feedback', label: 'Delete Feedback', icon: '🗑️' },
    { value: 'manage_services', label: 'Manage Services', icon: '⚙️' },
    { value: 'view_reports', label: 'View Reports', icon: '📊' },
    { value: 'export_data', label: 'Export Data', icon: '📤' },
  ];

  useEffect(() => {
    fetchOfficers();
    fetchTemples();
  }, []);

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

  const handleAddOfficer = async (e) => {
    e.preventDefault();
    try {
      await api.post('/officers', newOfficer);
      toast.success('Officer created successfully');
      setAddOpen(false);
      setNewOfficer({
        name: '',
        email: '',
        password: '',
        temple_id: '',
        role: 'officer',
        permissions: ['view_feedback', 'update_status'],
      });
      fetchOfficers();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create officer');
    }
  };

  const handleDeleteOfficer = async (id) => {
    if (!window.confirm('Are you sure you want to delete this officer?')) return;
    try {
      await api.delete(`/officers/${id}`);
      toast.success('Officer deleted successfully');
      fetchOfficers();
    } catch (error) {
      toast.error('Failed to delete officer');
    }
  };

  const handleEditRole = (officer) => {
    setSelectedOfficer({
      ...officer,
      role: officer.role || 'officer',
      permissions: officer.permissions || ['view_feedback', 'update_status'],
    });
    setEditOpen(true);
  };

  const handleUpdateRole = async () => {
    try {
      await api.put(`/officers/${selectedOfficer.id}/role`, {
        role: selectedOfficer.role,
        permissions: selectedOfficer.permissions,
      });
      toast.success('Role and permissions updated successfully');
      setEditOpen(false);
      fetchOfficers();
    } catch (error) {
      toast.error('Failed to update role');
    }
  };

  const getRoleColor = (role) => {
    const found = roleOptions.find(r => r.value === role);
    return found ? found.color : 'bg-gray-100 text-gray-700';
  };

  const getRoleLabel = (role) => {
    const found = roleOptions.find(r => r.value === role);
    return found ? found.label : 'Officer';
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
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-2 text-[#721C24]">Administration</h1>
          <p className="text-[#4A5568]">Manage roles, permissions, and system settings</p>
        </div>
        
        <Dialog open={addOpen} onOpenChange={setAddOpen}>
          <DialogTrigger asChild>
            <Button className="bg-[#721C24] hover:bg-[#5A161C] text-white">
              <Plus size={20} className="mr-2" />
              Add Officer
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-white max-w-lg max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="text-[#721C24] text-2xl">Add New Officer</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleAddOfficer} className="space-y-4">
              <div>
                <Label className="text-[#721C24]">Full Name *</Label>
                <Input
                  value={newOfficer.name}
                  onChange={(e) => setNewOfficer({ ...newOfficer, name: e.target.value })}
                  placeholder="Enter officer name"
                  required
                  className="mt-1.5"
                />
              </div>
              <div>
                <Label className="text-[#721C24]">Email *</Label>
                <Input
                  type="email"
                  value={newOfficer.email}
                  onChange={(e) => setNewOfficer({ ...newOfficer, email: e.target.value })}
                  placeholder="officer@temple.com"
                  required
                  className="mt-1.5"
                />
              </div>
              <div>
                <Label className="text-[#721C24]">Password *</Label>
                <Input
                  type="password"
                  value={newOfficer.password}
                  onChange={(e) => setNewOfficer({ ...newOfficer, password: e.target.value })}
                  placeholder="Create password"
                  required
                  className="mt-1.5"
                />
              </div>
              <div>
                <Label className="text-[#721C24]">Assign Temple *</Label>
                <Select
                  value={newOfficer.temple_id}
                  onValueChange={(value) => setNewOfficer({ ...newOfficer, temple_id: value })}
                >
                  <SelectTrigger className="mt-1.5">
                    <SelectValue placeholder="Select temple" />
                  </SelectTrigger>
                  <SelectContent className="bg-white">
                    <SelectItem value="all">All Temples</SelectItem>
                    {temples.map((temple) => (
                      <SelectItem key={temple.id} value={temple.id}>
                        {temple.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-[#721C24]">Role *</Label>
                <Select
                  value={newOfficer.role}
                  onValueChange={(value) => setNewOfficer({ ...newOfficer, role: value })}
                >
                  <SelectTrigger className="mt-1.5">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white">
                    {roleOptions.map((role) => (
                      <SelectItem key={role.value} value={role.value}>
                        <span className={`px-2 py-1 rounded ${role.color}`}>{role.label}</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-[#721C24]">Permissions</Label>
                <div className="grid grid-cols-2 gap-2 mt-2">
                  {permissionOptions.map((perm) => (
                    <label key={perm.value} className="flex items-center gap-2 text-sm cursor-pointer p-2 rounded hover:bg-[#FFF9E6]">
                      <input
                        type="checkbox"
                        checked={newOfficer.permissions.includes(perm.value)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setNewOfficer({ ...newOfficer, permissions: [...newOfficer.permissions, perm.value] });
                          } else {
                            setNewOfficer({ ...newOfficer, permissions: newOfficer.permissions.filter(p => p !== perm.value) });
                          }
                        }}
                        className="w-4 h-4 text-[#721C24] rounded"
                      />
                      <span>{perm.icon}</span>
                      <span className="text-[#4A5568]">{perm.label}</span>
                    </label>
                  ))}
                </div>
              </div>
              <Button type="submit" className="w-full bg-[#721C24] hover:bg-[#5A161C] text-white py-6">
                Create Officer
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-6 shadow-lg border-l-4 border-[#721C24]">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-[#721C24]/10 rounded-xl flex items-center justify-center">
              <Users className="text-[#721C24]" size={24} />
            </div>
            <div>
              <p className="text-sm text-[#4A5568]">Total Officers</p>
              <p className="text-3xl font-bold text-[#721C24]">{officers.length}</p>
            </div>
          </div>
        </div>
        
        <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-6 shadow-lg border-l-4 border-purple-500">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center">
              <Shield className="text-purple-600" size={24} />
            </div>
            <div>
              <p className="text-sm text-[#4A5568]">Executive Officers</p>
              <p className="text-3xl font-bold text-purple-600">
                {officers.filter(o => o.role === 'eo').length}
              </p>
            </div>
          </div>
        </div>
        
        <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-6 shadow-lg border-l-4 border-blue-500">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center">
              <Key className="text-blue-600" size={24} />
            </div>
            <div>
              <p className="text-sm text-[#4A5568]">Supervisors</p>
              <p className="text-3xl font-bold text-blue-600">
                {officers.filter(o => o.role === 'supervisor').length}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Officers Table with Role Management */}
      <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-lg overflow-hidden">
        <div className="p-6 border-b border-[#E2E8F0]">
          <h2 className="text-xl font-bold text-[#721C24]">Role & Permission Management</h2>
          <p className="text-sm text-[#4A5568]">Assign roles and permissions to officers</p>
        </div>
        <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="bg-[#FDFBF7] hover:bg-[#FDFBF7]">
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider">
                Officer
              </TableHead>
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider">
                Temple
              </TableHead>
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider">
                Role
              </TableHead>
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider">
                Permissions
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
                className="hover:bg-[#FFF9E6] transition-colors"
              >
                <TableCell>
                  <div>
                    <p className="font-medium">{officer.name}</p>
                    <p className="text-sm text-[#4A5568]">{officer.email}</p>
                  </div>
                </TableCell>
                <TableCell className="text-[#4A5568]">
                  {officer.temple_name || 'Not assigned'}
                </TableCell>
                <TableCell>
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${getRoleColor(officer.role)}`}>
                    {getRoleLabel(officer.role)}
                  </span>
                </TableCell>
                <TableCell>
                  <div className="flex flex-wrap gap-1">
                    {(officer.permissions || ['view_feedback', 'update_status']).slice(0, 3).map((perm, idx) => (
                      <span key={idx} className="px-2 py-0.5 bg-[#FFF9E6] text-[#721C24] rounded text-xs">
                        {permissionOptions.find(p => p.value === perm)?.label || perm}
                      </span>
                    ))}
                    {(officer.permissions || []).length > 3 && (
                      <span className="px-2 py-0.5 bg-[#E2E8F0] text-[#4A5568] rounded text-xs">
                        +{officer.permissions.length - 3} more
                      </span>
                    )}
                  </div>
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleEditRole(officer)}
                      className="text-[#721C24] hover:bg-[#FFF9E6]"
                    >
                      <Edit2 size={16} className="mr-1" />
                      Edit
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeleteOfficer(officer.id)}
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

      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="bg-white max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-[#721C24] text-2xl">Edit Officer Permissions</DialogTitle>
          </DialogHeader>

          {selectedOfficer && (
            <div className="space-y-4">
              <div>
                <Label className="text-[#721C24] font-medium">Role</Label>
                <Select
                  value={selectedOfficer.role}
                  onValueChange={(value) => setSelectedOfficer({ ...selectedOfficer, role: value })}
                >
                  <SelectTrigger className="mt-1.5">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-white">
                    {roleOptions.map((role) => (
                      <SelectItem key={role.value} value={role.value}>
                        <span className={`px-2 py-1 rounded ${role.color}`}>{role.label}</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label className="text-[#721C24] font-medium">Permissions</Label>
                <div className="grid grid-cols-2 gap-3 mt-3">
                  {permissionOptions.map((perm) => (
                    <label
                      key={perm.value}
                      className={`flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all ${
                        selectedOfficer.permissions.includes(perm.value)
                          ? 'bg-[#721C24]/10 border-2 border-[#721C24]'
                          : 'bg-[#FDFBF7] border-2 border-transparent hover:border-[#E2E8F0]'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedOfficer.permissions.includes(perm.value)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedOfficer({
                              ...selectedOfficer,
                              permissions: [...selectedOfficer.permissions, perm.value],
                            });
                          } else {
                            setSelectedOfficer({
                              ...selectedOfficer,
                              permissions: selectedOfficer.permissions.filter((p) => p !== perm.value),
                            });
                          }
                        }}
                        className="w-4 h-4 text-[#721C24] rounded focus:ring-[#721C24]"
                      />
                      <span className="text-lg">{perm.icon}</span>
                      <span className="text-sm font-medium text-[#4A5568]">{perm.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              <Button
                onClick={handleUpdateRole}
                className="w-full bg-[#721C24] hover:bg-[#5A161C] text-white py-6"
              >
                Save Changes
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Administration;
