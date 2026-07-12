import { useState, useEffect } from 'react';
import SettingsSkeleton from '../../components/skeleton/SettingsSkeleton';

export default function SettingsPage() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 600);
    return () => clearTimeout(timer);
  }, []);

  if (loading) {
    return <SettingsSkeleton />;
  }

  return <div>Settings</div>;
}
