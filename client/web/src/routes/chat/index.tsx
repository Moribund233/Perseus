import { useState, useEffect } from 'react';
import ChatSkeleton from '../../components/skeleton/ChatSkeleton';

export default function ChatPage() {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 600);
    return () => clearTimeout(timer);
  }, []);

  if (loading) {
    return <ChatSkeleton />;
  }

  return <div>Team Chat</div>;
}
