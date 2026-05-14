import { useState, useEffect } from 'react';
import { registerToast } from '../services/api.js';

export default function Toast() {
  const [message, setMessage] = useState(null);

  useEffect(() => {
    registerToast((msg) => {
      setMessage(msg);
    });
  }, []);

  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(() => setMessage(null), 3000);
    return () => clearTimeout(timer);
  }, [message]);

  if (!message) return null;

  return (
    <div className="toast-container notif-banner">
      <div className="toast">{message}</div>
    </div>
  );
}
