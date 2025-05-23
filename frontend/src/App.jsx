import React from 'react';
import { BrowserRouter as Router, Routes, Route} from 'react-router-dom';
import SignUpForm from 'src/pages/Auth/SignUp';
import LogInForm from 'src/pages/Auth/LogIn';
import GridLayout from 'src/pages/Dashboard/GridLayout';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/signup" element={<SignUpForm />} />
        <Route path="/login" element={<LogInForm />} />
        <Route path="/dashboard" element={<GridLayout />} />
        <Route path="/" element={<SignUpForm />} />
      </Routes>
    </Router>
  );
}

export default App;