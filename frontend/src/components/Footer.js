import React from 'react';
import { Box, Typography, Container, Link } from '@mui/material';

const Footer = () => {
  return (
    <Box 
      component="footer" 
      sx={{ 
        py: 3, 
        mt: 'auto',
        backgroundColor: (theme) => theme.palette.background.paper
      }}
    >
      <Container maxWidth="lg">
        <Typography variant="body2" color="text.secondary" align="center">
          Subdomain Finder - A tool for finding subdomains using subfinder, crt.sh and httpx
        </Typography>
        <Typography variant="body2" color="text.secondary" align="center">
          &copy; {new Date().getFullYear()} - Built with FastAPI, PHP, Redis & React
        </Typography>
      </Container>
    </Box>
  );
};

export default Footer; 