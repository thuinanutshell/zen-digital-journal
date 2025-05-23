import React, { useState } from 'react';
import Box from '@mui/material/Box';
import { styled } from '@mui/material/styles';
import Dialog from '@mui/material/Dialog';
import JournalForm from '../Journal/JournalForm';
import ToggleColorMode from 'src/components/ToggleColorMode';

// Create a styled square component that is clickable
const Square = styled(Box)(({ theme }) => ({
  width: '48px',
  height: '48px',
  backgroundColor: '#fff',
  margin: '5px',
  borderRadius: '5px',
  border: 'solid',
  cursor: 'pointer', // Show cursor pointer on hover
  transition: 'transform 0.2s, background-color 0.2s',
  '&:hover': {
    transform: 'scale(1.1)',
    backgroundColor: theme.palette.primary.light,
  },
}));

export default function GridLayout() {
  // State to control the dialog
  const [open, setOpen] = useState(false);
  // State to track which day was clicked (optional, if you want to pass the day to the form)
  const [selectedDay, setSelectedDay] = useState(null);

  // Handle opening the dialog
  const handleSquareClick = (day) => {
    setSelectedDay(day);
    setOpen(true);
  };

  // Handle closing the dialog
  const handleClose = () => {
    setOpen(false);
  };

  return (
    <>
      <h1 center>Daily Log of Journaling</h1>
      <ToggleColorMode />
      <Box
        sx={{
          width: '100%',
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
        }}
      >
        {[...Array(365)].map((_, index) => (
          <Square 
            key={index} 
            onClick={() => handleSquareClick(index + 1)}
          />
        ))}
      </Box>

      {/* Dialog that opens when a square is clicked */}
      <Dialog
        open={open}
        onClose={handleClose}
        fullWidth
        maxWidth="md"
        aria-labelledby="journal-dialog-title"
      >
        {/* Pass the selected day to the JournalForm if needed */}
        <JournalForm day={selectedDay} onClose={handleClose} />
      </Dialog>
    </>
  );
}