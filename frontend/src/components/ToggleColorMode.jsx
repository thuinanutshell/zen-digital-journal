import React, { useState, useEffect } from 'react';
import '/src/App.css';

const ToggleColorMode = () => {
  // Initialize state from localStorage or system preference
  const [darkMode, setDarkMode] = useState(() => {
    // First check localStorage
    const savedMode = localStorage.getItem('darkMode');
    if (savedMode !== null) {
      return savedMode === 'true';
    }
    // If not saved, check system preference
    return window.matchMedia && 
      window.matchMedia('(prefers-color-scheme: dark)').matches;
  });
  
  // Apply the dark mode class when the component mounts and when darkMode changes
  useEffect(() => {
    if (darkMode) {
      document.body.classList.add('dark-mode');
    } else {
      document.body.classList.remove('dark-mode');
    }
    // Save the preference to localStorage
    localStorage.setItem('darkMode', darkMode);
  }, [darkMode]);
  
  // Listen for system preference changes
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    const handleChange = (e) => {
      // Only update if user hasn't manually set a preference
      if (localStorage.getItem('darkMode') === null) {
        setDarkMode(e.matches);
      }
    };
    
    // Add listener (with compatibility for older browsers)
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange);
    } else {
      // Older browsers support
      mediaQuery.addListener(handleChange);
    }
    
    // Clean up
    return () => {
      if (mediaQuery.removeEventListener) {
        mediaQuery.removeEventListener('change', handleChange);
      } else {
        // Older browsers support
        mediaQuery.removeListener(handleChange);
      }
    };
  }, []);
  
  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
  };
  
  return (
    <div className="dark-mode-toggle">
      <label className="switch" title={darkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}>
        <input 
          type="checkbox" 
          onChange={toggleDarkMode} 
          checked={darkMode} 
          aria-label="Toggle dark mode"
        />
        <span className="slider round"></span>
      </label>
    </div>
  );
};

export default ToggleColorMode;