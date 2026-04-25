import React from 'react';
import { NavLink } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { BarChart3, FileUp, Settings, TableProperties } from 'lucide-react';
import UserMenu from '@/components/UserMenu';

/** Top navigation bar: branding + links to other pages + user menu. */
const DashboardHeader = () => {
  const navItems = [
    { to: '/statistics', label: 'Statistics', icon: BarChart3, testId: 'nav-statistics-btn' },
    { to: '/settings', label: 'Settings', icon: Settings, testId: 'nav-settings-btn' },
    { to: '/import-export', label: 'Import', icon: FileUp, testId: 'nav-import-export-btn' },
    { to: '/statements', label: 'Statements', icon: TableProperties, testId: 'nav-statements-btn' },
  ];

  return (
    <div className="sticky top-0 z-30 border-b border-[#E5E7EB]/80 bg-white/95 shadow-[0_1px_8px_rgba(15,23,42,0.04)] backdrop-blur">
      <div className="mx-auto max-w-7xl px-[14px] sm:px-6 lg:px-8">
        <div className="flex flex-col gap-3 py-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 items-center gap-2.5">
          <img
            src="/InsuranceManager.png"
            alt=""
              className="h-9 w-9 rounded-xl object-cover shadow-sm sm:h-10 sm:w-10"
          />
            <div className="min-w-0">
              <h1 className="truncate text-lg font-bold leading-tight text-[#0F172A] sm:text-xl">
                Insurance Manager
              </h1>
              <p className="text-xs font-medium text-[#64748B]">Local dashboard</p>
            </div>
          </div>
          <div className="flex items-center gap-2 overflow-x-auto pb-0.5 sm:overflow-visible sm:pb-0">
            {navItems.map(({ to, label, icon: Icon, testId }) => (
              <NavLink key={to} to={to}>
                {({ isActive }) => (
                  <Button
                    variant="outline"
                    size="sm"
                    data-testid={testId}
                    className={`h-9 shrink-0 rounded-xl border-[#E5E7EB] px-3 text-xs font-semibold shadow-none transition-all duration-150 active:scale-95 ${
                      isActive
                        ? 'border-[#2563EB]/30 bg-[#EFF6FF] text-[#2563EB]'
                        : 'bg-white text-[#334155] hover:bg-[#F8FAFC]'
                    }`}
                  >
                    <Icon className="mr-1.5 h-[18px] w-[18px] stroke-[2]" />
                    {label}
                  </Button>
                )}
              </NavLink>
            ))}
            <UserMenu />
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardHeader;
