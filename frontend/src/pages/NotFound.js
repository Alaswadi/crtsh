import React from 'react';
import { Box, Typography, Button, Paper } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';

const NotFound = () => {
  return (
    <Box sx={{ 
      display: 'flex', 
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      textAlign: 'center',
      mt: 4
    }}>
      <Paper elevation={3} sx={{ p: 4, maxWidth: 500, width: '100%' }}>
        <ErrorOutlineIcon sx={{ fontSize: 80, color: 'error.main', mb: 2 }} />
        <Typography variant="h4" component="h1" gutterBottom>
          404 - Page Not Found
        </Typography>
        <Typography variant="body1" paragraph>
          The page you are looking for doesn't exist or has been moved.
        </Typography>
        <Button 
          variant="contained" 
          component={RouterLink} 
          to="/"
          sx={{ mt: 2 }}
        >
          Go to Home
        </Button>
      </Paper>
    </Box>
  );
};

export default NotFound; 