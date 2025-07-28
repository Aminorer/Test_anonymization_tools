import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import UploadPage from './pages/UploadPage';
import EntityControlPage from './pages/EntityControlPage';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/" element={<UploadPage />} />
          <Route path="/control" element={<EntityControlPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;