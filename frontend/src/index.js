import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
// React.StrictMode KAPALI — runIntelligence çift fire'ı engellemek için
root.render(<App />);
