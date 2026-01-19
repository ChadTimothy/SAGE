import React from 'react';
import ReactDOM from 'react-dom/client';
import { ProgressWidget } from './ProgressWidget';
import '../shared/styles.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ProgressWidget />
  </React.StrictMode>
);
