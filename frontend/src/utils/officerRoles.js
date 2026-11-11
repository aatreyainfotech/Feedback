import { useCallback, useEffect, useState } from 'react';
import api from './api';

// Officer roles are kept on the server (Super Admin > Officer Roles). These are the built-in ones,
// used until the list loads or when the server is unreachable.
export const DEFAULT_OFFICER_ROLES = [
  { value: 'officer', label: 'Officer', access: 'assigned', color: 'green' },
  { value: 'supervisor', label: 'Supervisor', access: 'temple', color: 'blue' },
  { value: 'eo', label: 'Executive Officer', access: 'temple', color: 'purple' },
  { value: 'asst_commissioner', label: 'Asst Commissioner', access: 'all', color: 'amber' },
  { value: 'commissioner', label: 'Commissioner', access: 'all', color: 'red' },
];

// Written out in full so Tailwind keeps the classes.
export const ROLE_COLOR_CLASSES = {
  green: 'bg-green-100 text-green-700',
  blue: 'bg-blue-100 text-blue-700',
  purple: 'bg-purple-100 text-purple-700',
  amber: 'bg-amber-100 text-amber-700',
  red: 'bg-red-100 text-red-700',
  teal: 'bg-teal-100 text-teal-700',
  pink: 'bg-pink-100 text-pink-700',
  slate: 'bg-slate-200 text-slate-700',
};

export const ROLE_ACCESS_OPTIONS = [
  { value: 'assigned', label: 'Only feedback assigned to them' },
  { value: 'temple', label: 'All feedback of their temple' },
  { value: 'all', label: 'All temples' },
];

export const roleAccessLabel = (access) => ROLE_ACCESS_OPTIONS.find((a) => a.value === access)?.label || ROLE_ACCESS_OPTIONS[0].label;

export const roleColorClass = (color) => ROLE_COLOR_CLASSES[color] || ROLE_COLOR_CLASSES.slate;

export const findRole = (roles, value) => roles.find((r) => r.value === (value || 'officer'));

export const roleLabel = (roles, value) => findRole(roles, value)?.label || (value ? String(value).replace(/_/g, ' ') : 'Officer');

export const useOfficerRoles = () => {
  const [roles, setRoles] = useState(DEFAULT_OFFICER_ROLES);

  const reload = useCallback(() => (
    api.get('/officer-roles', { forceRefresh: true })
      .then((res) => {
        if (Array.isArray(res.data) && res.data.length) setRoles(res.data);
      })
      .catch(() => {})
  ), []);

  useEffect(() => {
    reload();
  }, [reload]);

  return { roles, reload };
};
