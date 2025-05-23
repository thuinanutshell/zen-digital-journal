import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';

function SignUpForm() {
    const navigate = useNavigate();
    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");

    const handleSubmit = async () => {
        // Save the user's information to the database
        // Redirect the user to the Log In Page
        try {
            const response = await fetch('http://127.0.0.1:5000/auth/register', {
                method: 'POST',
                // Indicates that the request body format is JSON
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ username, email, password })
            });

            if (response.ok) {
                console.log("User registered successfully")
                navigate('/login');
            } else {
                const errorData = await response.json();
                alert(errorData.error || "Registration failed.")
            }
        } catch (error) {
            console.error('Error:', error);
            alert("An unexpected error occurred.")
        }
    };

    return (
        <form onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
            <Typography variant="h6">Sign Up</Typography>
            <TextField 
                fullWidth 
                variant="outlined"
                label="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                sx={{ mb: 2 }}
                autoFocus />

            <TextField 
                fullWidth 
                variant="outlined"
                label="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                sx={{ mb: 2 }} />

            <TextField 
                fullWidth 
                variant="outlined"
                label="Password"
                type="password"
                value={password} 
                onChange={(e) => setPassword(e.target.value)}
                sx={{ mb: 2 }}
                autoFocus />
            <Button variant="contained" onClick={handleSubmit}>Sign Up</Button>
        </form>
    )
}

export default SignUpForm;