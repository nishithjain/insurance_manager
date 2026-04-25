import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Layers, LogOut, Shield, UserCog, Users } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useAuth } from '@/auth/AuthContext';

/**
 * Small header widget: shows the signed-in user and exposes Sign out + (for
 * admins) a link to the User management page. Drop this into any page header.
 */
export default function UserMenu() {
  const { user, isAdmin, logout } = useAuth();
  const navigate = useNavigate();

  if (!user) return null;

  const initial = (user.full_name || user.email || '?').charAt(0).toUpperCase();

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="h-9 shrink-0 gap-2 rounded-xl border-[#E5E7EB] bg-white px-2.5 text-xs font-semibold text-[#334155] shadow-none transition-all duration-150 hover:bg-[#F8FAFC] active:scale-95"
          data-testid="user-menu-btn"
        >
          <span
            aria-hidden
            className="flex h-6 w-6 items-center justify-center rounded-full bg-[#2563EB] text-xs font-semibold text-white"
          >
            {initial}
          </span>
          <span className="hidden sm:inline max-w-[140px] truncate">{user.full_name}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>
          <div className="flex flex-col">
            <span className="text-sm font-semibold">{user.full_name}</span>
            <span className="text-xs text-gray-500 truncate">{user.email}</span>
            <span className="mt-1 text-[10px] uppercase tracking-wide text-indigo-700">
              {user.role}
            </span>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {isAdmin && (
          <DropdownMenuItem asChild>
            <Link to="/admin/users" className="cursor-pointer">
              <UserCog className="w-4 h-4 mr-2" />
              User management
            </Link>
          </DropdownMenuItem>
        )}
        {isAdmin && (
          <DropdownMenuItem asChild>
            <Link to="/admin/customers" className="cursor-pointer" data-testid="nav-customer-management">
              <Users className="w-4 h-4 mr-2" />
              Customer management
            </Link>
          </DropdownMenuItem>
        )}
        {isAdmin && (
          <DropdownMenuItem asChild>
            <Link
              to="/admin/insurance-master"
              className="cursor-pointer"
              data-testid="nav-insurance-master"
            >
              <Layers className="w-4 h-4 mr-2" />
              Insurance Master
            </Link>
          </DropdownMenuItem>
        )}
        {isAdmin && (
          <DropdownMenuItem disabled>
            <Shield className="w-4 h-4 mr-2" />
            Admin
          </DropdownMenuItem>
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={handleLogout} className="cursor-pointer text-red-600">
          <LogOut className="w-4 h-4 mr-2" />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
