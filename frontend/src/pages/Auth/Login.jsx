import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';

function LogInForm() {
    // Define a React hook that can only be called in a React component
    // A hook is used to access the navigate function & imperatively say what we want the code to do
    const navigate = useNavigate();

    // State management
    // This hook defines the state of a variable that will be updated via some function/method
    // The set-prefix variable name is the function used to change the variable without the set prefix
    const [identifier, setIdentifier] = useState("");
    const [password, setPassword] = useState("");

    // Define what happens when the user clicks a button
    // Basically this is where the communication between the frontend and backend happens
    // When the button is clicked, data is saved to/retrieved from the database
    // and oftentimes, the user will be redirected to a different page
    const handleSubmit = async () => {
        try {
            // Make HTTP requests to retrieve or send data to a server
            // It allows the component to interact with APIs and handle data async
            // fetch returns a Promise that resolves to the response from the server
            const response = await fetch('http://127.0.0.1:5000/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ identifier, password })
            });

            if (response.ok) {
                console.log("User logged in successfully")
                navigate('/dashboard') // redirect to a different page on the frontend
            } else {
                const errorData = await response.json();
                alert(errorData.error || "Logged in failed.")
            }
        } catch (error) {
            console.error('Error:', error)
            alert("An unexpected error occurred.")
        }
    }
    return (
        <form onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
            <Typography variant="h6">Log In</Typography>
            <TextField
                fullWidth
                variant="outlined"
                label="Username or Email"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                sx={{ mb: 2 }}
                autoFocus />
            <TextField
                fullWidth
                variant="outlined"
                label="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                sx={{ mb: 2 }}
                autoFocus /> 
            <Button variant="contained" onClick={handleSubmit}>Log In</Button>
        </form>
    )
}

export default LogInForm;