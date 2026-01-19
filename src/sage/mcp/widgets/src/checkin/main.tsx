import React from 'react';
import ReactDOM from 'react-dom/client';
import { CheckinWidget } from './CheckinWidget';
import '../shared/styles.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <CheckinWidget />
  </React.StrictMode>
);
