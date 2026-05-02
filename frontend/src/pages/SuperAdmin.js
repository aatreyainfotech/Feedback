import { useEffect, useState } from 'react';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Plus, ShieldCheck, Trash2, Edit2 } from 'lucide-react';
import { toast } from 'sonner';

const PERMISSIONS = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'temples', label: 'Temples' },
  { key: 'officers', label: 'Officers' },
  { key: 'services', label: 'Services' },
  { key: 'feedback', label: 'Feedback' },
  { key: 'whatsapp_logs', label: 'WhatsApp Logs' },
  { key: 'reports', label: 'Reports' },
  { key: 'administration', label: 'Administration' },
];

const emptyForm = {
  username: '',
  email: '',
  password: '',
  role: 'admin',
  permissions: ['dashboard'],
};

const SuperAdmin = () => {
  const [admins, setAdmins] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(emptyForm);

  const fetchAdmins = async () => {
    try {
      const res = await api.get('/admins');
      setAdmins(res.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to load admins');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAdmins();
  }, []);

  const togglePerm = (key) => {
    setForm((f) => {
      const exists = f.permissions.includes(key);
      return {
        ...f,
        permissions: exists ? f.permissions.filter((p) => p !== key) : [...f.permissions, key],
      };
    });
  };

  const openCreate = () => {
    setEditing(null);
    setForm(emptyForm);
    setOpen(true);
  };

  const openEdit = (admin) => {
    setEditing(admin);
    setForm({
      username: admin.username || '',
      email: admin.email || '',
      password: '',
      role: admin.role || 'admin',
      permissions: admin.role === 'superadmin' ? PERMISSIONS.map((p) => p.key) : (admin.permissions || []),
    });
    setOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = { ...form };
      if (form.role === 'superadmin') {
        payload.permissions = PERMISSIONS.map((p) => p.key);
      }
      if (editing) {
        if (!payload.password) delete payload.password;
        await api.put(`/admins/${editing.id}`, payload);
        toast.success('Admin updated');
      } else {
        await api.post('/admins', payload);
        toast.success('Admin created');
      }
      setOpen(false);
      fetchAdmins();
    } catch (e2) {
      toast.error(e2.response?.data?.detail || 'Operation failed');
    }
  };

  const handleDelete = async (admin) => {
    if (!window.confirm(`Delete admin ${admin.email}?`)) return;
    try {
      await api.delete(`/admins/${admin.id}`);
      toast.success('Admin deleted');
      fetchAdmins();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to delete');
    }
  };

  if (loading) return <div className="text-center py-8">Loading...</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-2 text-[#721C24]">Super Admin</h1>
          <p className="text-[#4A5568]">Manage admin accounts and sidebar permissions</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button onClick={openCreate} className="bg-[#721C24] hover:bg-[#5A161C] text-white">
              <Plus size={18} className="mr-2" />
              Add Admin
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-white max-w-lg max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="text-[#721C24] text-2xl">
                {editing ? 'Edit Admin' : 'Add New Admin'}
              </DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <Label className="text-[#721C24]">Username *</Label>
                <Input
                  value={form.username}
                  onChange={(e) => setForm({ ...form, username: e.target.value })}
                  required
                  className="mt-1.5"
                />
              </div>
              <div>
                <Label className="text-[#721C24]">Email *</Label>
                <Input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  required
                  className="mt-1.5"
                />
              </div>
              <div>
                <Label className="text-[#721C24]">
                  {editing ? 'Password (leave blank to keep current)' : 'Password *'}
                </Label>
                <Input
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                  required={!editing}
                  className="mt-1.5"
                />
              </div>
              <div>
                <Label className="text-[#721C24]">Role</Label>
                <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                  <SelectTrigger className="mt-1.5"><SelectValue /></SelectTrigger>
                  <SelectContent className="bg-white">
                    <SelectItem value="admin">Admin</SelectItem>
                    <SelectItem value="superadmin">Super Admin (full access)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {form.role !== 'superadmin' && (
                <div>
                  <Label className="text-[#721C24]">Sidebar Permissions</Label>
                  <div className="grid grid-cols-2 gap-2 mt-2">
                    {PERMISSIONS.map((p) => (
                      <label key={p.key} className="flex items-center gap-2 text-sm cursor-pointer p-2 rounded hover:bg-[#FFF9E6]">
                        <input
                          type="checkbox"
                          checked={form.permissions.includes(p.key)}
                          onChange={() => togglePerm(p.key)}
                          className="w-4 h-4 text-[#721C24] rounded"
                        />
                        <span className="text-[#4A5568]">{p.label}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}
              <Button type="submit" className="w-full bg-[#721C24] hover:bg-[#5A161C] text-white py-6">
                {editing ? 'Update Admin' : 'Create Admin'}
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-lg overflow-hidden">
        <div className="p-6 border-b border-[#E2E8F0] flex items-center gap-3">
          <ShieldCheck className="text-[#721C24]" size={22} />
          <div>
            <h2 className="text-xl font-bold text-[#721C24]">Admin Accounts</h2>
            <p className="text-sm text-[#4A5568]">Toggle which sidebar pages each admin can access</p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="bg-[#FDFBF7] hover:bg-[#FDFBF7]">
                <TableHead className="text-[#721C24] uppercase text-xs">Username</TableHead>
                <TableHead className="text-[#721C24] uppercase text-xs">Email</TableHead>
                <TableHead className="text-[#721C24] uppercase text-xs">Role</TableHead>
                <TableHead className="text-[#721C24] uppercase text-xs">Permissions</TableHead>
                <TableHead className="text-[#721C24] uppercase text-xs text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {admins.map((a) => (
                <TableRow key={a.id} className="hover:bg-[#FFF9E6]">
                  <TableCell className="font-medium">{a.username}</TableCell>
                  <TableCell className="text-[#4A5568]">{a.email}</TableCell>
                  <TableCell>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${a.role === 'superadmin' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'}`}>
                      {a.role === 'superadmin' ? 'Super Admin' : 'Admin'}
                    </span>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {(a.permissions || []).slice(0, 4).map((p) => (
                        <span key={p} className="px-2 py-0.5 bg-[#FFF9E6] text-[#721C24] rounded text-xs">
                          {PERMISSIONS.find((x) => x.key === p)?.label || p}
                        </span>
                      ))}
                      {(a.permissions || []).length > 4 && (
                        <span className="px-2 py-0.5 bg-[#E2E8F0] text-[#4A5568] rounded text-xs">
                          +{a.permissions.length - 4} more
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button variant="ghost" size="sm" onClick={() => openEdit(a)} className="text-[#721C24] hover:bg-[#FFF9E6]">
                        <Edit2 size={16} className="mr-1" /> Edit
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleDelete(a)} className="text-red-600 hover:bg-red-50">
                        <Trash2 size={16} />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
};

export default SuperAdmin;
