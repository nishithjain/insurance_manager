import React from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { BarChart3, Settings } from 'lucide-react';
import UserMenu from '@/components/UserMenu';

/** Top navigation bar: branding + links to other pages + user menu. */
const DashboardHeader = () => (
  <div className="bg-white border-b">
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="flex justify-between items-center py-4">
        <div className="flex items-center gap-3">
          <img
            src="/InsuranceManager.png"
            alt=""
            className="w-10 h-10 rounded-lg object-cover shadow-sm"
          />
          <div>
            <h1 className="text-xl font-bold text-gray-900">Insurance Manager</h1>
            <p className="text-sm text-gray-500">Local</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/statistics">
            <Button variant="outline" size="sm" data-testid="nav-statistics-btn">
              <BarChart3 className="w-4 h-4 mr-2" />
              Statistics
            </Button>
          </Link>
          <Link to="/settings">
            <Button variant="outline" size="sm" data-testid="nav-settings-btn">
              <Settings className="w-4 h-4 mr-2" />
              Settings
            </Button>
          </Link>
          <Link to="/import-export">
            <Button variant="outline" size="sm" data-testid="nav-import-export-btn">
              Import &amp; Export
            </Button>
          </Link>
          <Link to="/statements">
            <Button variant="outline" size="sm" data-testid="nav-statements-btn">
              Statement CSV
            </Button>
          </Link>
          <UserMenu />
        </div>
      </div>
    </div>
  </div>
);

export default DashboardHeader;
