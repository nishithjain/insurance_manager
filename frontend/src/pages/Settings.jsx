import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ArrowLeft, Save } from 'lucide-react';
import { settingsAPI } from '@/utils/api';

const Settings = () => {
  const [backupFolder, setBackupFolder] = useState('');
  const [initialBackupFolder, setInitialBackupFolder] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await settingsAPI.get();
        if (cancelled) return;
        const value = res.data?.database_backup_folder || '';
        setBackupFolder(value);
        setInitialBackupFolder(value);
      } catch (err) {
        if (!cancelled) {
          setError(err.response?.data?.detail || err.message || 'Could not load settings.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSave = async (event) => {
    event.preventDefault();
    setSaving(true);
    setMessage('');
    setError('');
    try {
      const value = backupFolder.trim();
      const res = await settingsAPI.update({ database_backup_folder: value || null });
      const saved = res.data?.database_backup_folder || '';
      setBackupFolder(saved);
      setInitialBackupFolder(saved);
      setMessage(saved ? 'Backup folder saved.' : 'Database backups disabled.');
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Could not save settings.');
    } finally {
      setSaving(false);
    }
  };

  const changed = backupFolder !== initialBackupFolder;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center gap-4">
              <Link to="/dashboard">
                <Button variant="outline" size="sm">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Dashboard
                </Button>
              </Link>
              <div className="flex items-center gap-2">
                <img src="/InsuranceManager.png" alt="" className="w-8 h-8 rounded-md object-cover" />
                <div>
                  <h1 className="text-lg font-semibold text-gray-900">Settings</h1>
                  <p className="text-sm text-gray-500">Local</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Card>
          <CardHeader>
            <CardTitle>Database backups</CardTitle>
            <CardDescription>
              Configure a server folder for SQLite backups. Leave blank to disable automatic backups.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleSave}>
              <div className="space-y-2">
                <Label htmlFor="backup-folder">Backup folder path</Label>
                <Input
                  id="backup-folder"
                  value={backupFolder}
                  onChange={(event) => setBackupFolder(event.target.value)}
                  placeholder="D:\\InsuranceBackups"
                  disabled={loading || saving}
                />
              </div>

              {error ? (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              ) : null}
              {message ? (
                <Alert>
                  <AlertDescription>{message}</AlertDescription>
                </Alert>
              ) : null}

              <Button type="submit" disabled={loading || saving || !changed}>
                <Save className="w-4 h-4 mr-2" />
                {saving ? 'Saving...' : 'Save settings'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Settings;
