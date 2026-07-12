import { useState, useEffect } from 'react';
import PullRequestsSkeleton from '../../components/skeleton/PullRequestsSkeleton';

export default function PullRequestsPage() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 600);
    return () => clearTimeout(timer);
  }, []);

  if (loading) {
    return <PullRequestsSkeleton />;
  }

  return <div>Pull Requests</div>;
}
