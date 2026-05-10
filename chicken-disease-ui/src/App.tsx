import { useState, useEffect } from 'react';
import { HomePage } from './pages/HomePage';

function App() {
  const [clientId] = useState(() => {
    // Generate or retrieve client ID
    let id = localStorage.getItem('chicken-disease-client-id');
    if (!id) {
      id = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('chicken-disease-client-id', id);
    }
    return id;
  });

  return <HomePage clientId={clientId} />;
}

export default App;
