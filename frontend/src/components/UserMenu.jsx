import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { LogOut, Shield, UserCog } from 'lucide-react';

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
        <Button variant="outline" size="sm" className="gap-2" data-testid="user-menu-btn">
          <span
            aria-hidden
            className="w-6 h-6 rounded-full bg-indigo-600 text-white text-xs font-semibold flex items-center justify-center"
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
