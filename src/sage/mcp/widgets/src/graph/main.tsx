import React from 'react';
import ReactDOM from 'react-dom/client';
import { GraphWidget } from './GraphWidget';
import '../shared/styles.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <GraphWidget />
  </React.StrictMode>
);
