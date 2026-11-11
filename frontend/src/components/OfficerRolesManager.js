import { useState } from 'react';
import api from '../utils/api';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './ui/table';
import { BadgeCheck, Edit2, Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { ROLE_ACCESS_OPTIONS, ROLE_COLOR_CLASSES, roleAccessLabel, roleColorClass, useOfficerRoles } from '../utils/officerRoles';

const emptyRole = { label: '', access: 'assigned', color: 'green' };

// Super Admin: add / edit the officer roles shown on the Officers and Administration pages.
const OfficerRolesManager = () => {
  const { roles, reload } = useOfficerRoles();
  const [editing, setEditing] = useState(null); // null = closed, {} = new, role = edit
  const [form, setForm] = useState(emptyRole);
  const [saving, setSaving] = useState(false);

  const openNew = () => {
    setForm(emptyRole);
    setEditing({});
  };

  const openEdit = (role) => {
    setForm({ label: role.label, access: role.access || 'assigned', color: role.color || 'green' });
    setEditing(role);
  };

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      if (editing?.value) {
        await api.put(`/officer-roles/${editing.value}`, form);
        toast.success('Role updated');
      } else {
        await api.post('/officer-roles', form);
        toast.success('Role added');
      }
      setEditing(null);
      reload();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save the role');
    } finally {
      setSaving(false);
    }
  };

  const remove = async (role) => {
    if (!window.confirm(`Remove the role "${role.label}"?`)) return;
    try {
      await api.delete(`/officer-roles/${role.value}`);
      toast.success('Role removed');
      reload();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to remove the role');
    }
  };

  return (
    <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-lg overflow-hidden" data-testid="officer-roles-manager">
      <div className="p-6 border-b border-[#E2E8F0] flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <BadgeCheck className="text-[#721C24]" size={22} />
          <div>
            <h2 className="text-xl font-bold text-[#721C24]">Officer Roles</h2>
            <p className="text-sm text-[#4A5568]">Roles shown when adding or editing an officer, and what each role can see</p>
          </div>
        </div>
        <Button onClick={openNew} data-testid="add-officer-role" className="bg-[#721C24] hover:bg-[#5A161C] text-white">
          <Plus size={18} className="mr-2" /> Add Role
        </Button>
      </div>
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="bg-[#FDFBF7] hover:bg-[#FDFBF7]">
              <TableHead className="text-[#721C24] uppercase text-xs">Role</TableHead>
              <TableHead className="text-[#721C24] uppercase text-xs">Can see</TableHead>
              <TableHead className="text-[#721C24] uppercase text-xs text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {roles.map((role) => (
              <TableRow key={role.value} data-testid={`officer-role-${role.value}`} className="hover:bg-[#FFF9E6]">
                <TableCell>
                  <span className={`px-3 py-1 rounded-full text-xs font-medium ${roleColorClass(role.color)}`}>{role.label}</span>
                </TableCell>
                <TableCell className="text-sm text-[#4A5568]">{roleAccessLabel(role.access)}</TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-2">
                    <Button variant="ghost" size="sm" onClick={() => openEdit(role)} className="text-[#721C24] hover:bg-[#FFF9E6]">
                      <Edit2 size={16} className="mr-1" /> Edit
                    </Button>
                    {role.value !== 'officer' && (
                      <Button variant="ghost" size="sm" onClick={() => remove(role)} title="Remove role" className="text-red-600 hover:bg-red-50">
                        <Trash2 size={16} />
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <Dialog open={editing !== null} onOpenChange={(isOpen) => { if (!isOpen) setEditing(null); }}>
        <DialogContent className="bg-white max-w-md">
          <DialogHeader>
            <DialogTitle className="text-[#721C24] text-2xl">{editing?.value ? 'Edit Role' : 'Add Role'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={save} className="space-y-4">
            <div>
              <Label className="text-[#721C24]">Role name *</Label>
              <Input
                value={form.label}
                onChange={(e) => setForm({ ...form, label: e.target.value })}
                placeholder="e.g. Deputy Commissioner"
                maxLength={100}
                required
                data-testid="officer-role-name"
                className="mt-1.5"
              />
            </div>
            <div>
              <Label className="text-[#721C24]">Can see</Label>
              <Select value={form.access} onValueChange={(v) => setForm({ ...form, access: v })}>
                <SelectTrigger className="mt-1.5" data-testid="officer-role-access"><SelectValue /></SelectTrigger>
                <SelectContent className="bg-white">
                  {ROLE_ACCESS_OPTIONS.map((a) => (
                    <SelectItem key={a.value} value={a.value}>{a.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-[#721C24]">Colour</Label>
              <div className="flex flex-wrap gap-2 mt-2">
                {Object.keys(ROLE_COLOR_CLASSES).map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setForm({ ...form, color: c })}
                    className={`px-3 py-1 rounded-full text-xs font-medium capitalize ${ROLE_COLOR_CLASSES[c]} ${form.color === c ? 'ring-2 ring-offset-1 ring-[#721C24]' : ''}`}
                  >
                    {form.label || c}
                  </button>
                ))}
              </div>
            </div>
            <Button type="submit" disabled={saving} data-testid="save-officer-role" className="w-full bg-[#721C24] hover:bg-[#5A161C] text-white py-6">
              {saving ? 'Saving...' : editing?.value ? 'Update Role' : 'Add Role'}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default OfficerRolesManager;
