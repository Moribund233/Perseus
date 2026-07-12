import { useState, useEffect } from 'react';
import EditorSkeleton from '../../components/skeleton/EditorSkeleton';

export default function EditorPage() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 600);
    return () => clearTimeout(timer);
  }, []);

  if (loading) {
    return <EditorSkeleton />;
  }

  return <div>Code Editor</div>;
}
