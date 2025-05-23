import React, { useState, useEffect } from 'react';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import IconButton from '@mui/material/IconButton';
import CloseIcon from '@mui/icons-material/Close';

// Sample list of prompts
const promptList = [
  "What made you smile today?",
  "What's one thing you learned today?",
  "What are you grateful for today?",
  "What's something you're looking forward to?",
  "Describe a challenge you faced today."
];

function JournalForm({ day, onClose }) {
  const [prompt, setPrompt] = useState("");
  const [answer, setAnswer] = useState("");
  
  useEffect(() => {
    // Function to get a random prompt from the list
    const getRandomPrompt = () => {
      const randomIndex = Math.floor(Math.random() * promptList.length);
      return promptList[randomIndex];
    };
    
    setPrompt(getRandomPrompt());
    
    // Optional: You could check if this day already has a journal entry
    // and load it instead of setting a new prompt
  }, [day]); // Re-run when the day changes
  
  const handleAnswerChange = (event) => {
    setAnswer(event.target.value);
  };
  
  const handleSubmit = () => {
    console.log("Saving journal entry for day", day, ":", { prompt, answer });
    // Here you would add the API call to your backend
    // Example: saveJournalEntry(day, prompt, answer);
    
    // Close the dialog after saving
    onClose();
  };
  
  return (
    <>
      <DialogTitle id="journal-dialog-title" sx={{ m: 0, p: 2 }}>
        Journal Entry for Day {day}
        <IconButton
          aria-label="close"
          onClick={onClose}
          sx={{
            position: 'absolute',
            right: 8,
            top: 8,
            color: (theme) => theme.palette.grey[500],
          }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      
      <DialogContent dividers>
        <Typography variant="h6" gutterBottom>
          Today's Prompt:
        </Typography>
        <Typography variant="body1" sx={{ mb: 3, fontWeight: 'medium' }}>
          {prompt}
        </Typography>
        
        <TextField
          fullWidth
          multiline
          rows={6}
          variant="outlined"
          label="Your Response"
          value={answer}
          onChange={handleAnswerChange}
          sx={{ mb: 2 }}
          autoFocus
        />
      </DialogContent>
      
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button 
          variant="contained" 
          onClick={handleSubmit}
          disabled={!answer.trim()}
        >
          Save Entry
        </Button>
      </DialogActions>
    </>
  );
}

export default JournalForm;