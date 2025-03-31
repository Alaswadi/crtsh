import React from 'react';
import { AppBar, Toolbar, Typography, Button, Box } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import DnsIcon from '@mui/icons-material/Dns';

const Header = () => {
  return (
    <AppBar position="static">
      <Toolbar>
        <DnsIcon sx={{ mr: 2 }} />
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          Subdomain Finder
        </Typography>
        <Box>
          <Button color="inherit" component={RouterLink} to="/">
            Home
          </Button>
          <Button color="inherit" component={RouterLink} to="/domain">
            Domain Search
          </Button>
          <Button color="inherit" component={RouterLink} to="/organization">
            Organization Search
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Header; 