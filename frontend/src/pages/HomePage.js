import React from 'react';
import { Box, Typography, Paper, Button, Grid, Card, CardContent, CardActions } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import DnsIcon from '@mui/icons-material/Dns';
import BusinessIcon from '@mui/icons-material/Business';

const HomePage = () => {
  return (
    <Box>
      <Paper elevation={3} sx={{ p: 4, mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Welcome to Subdomain Finder
        </Typography>
        <Typography variant="body1" paragraph>
          A modern web application for finding subdomains using subfinder, crt.sh, and httpx.
          This tool helps security researchers and penetration testers discover subdomains
          quickly and efficiently with multithreaded processing and caching.
        </Typography>
      </Paper>

      <Grid container spacing={4}>
        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <CardContent sx={{ flexGrow: 1 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <DnsIcon fontSize="large" sx={{ mr: 1 }} />
                <Typography variant="h5" component="h2">
                  Domain Search
                </Typography>
              </Box>
              <Typography>
                Search for subdomains of a specific domain using both subfinder and crt.sh.
                Get comprehensive information about each subdomain with httpx scan results.
              </Typography>
            </CardContent>
            <CardActions>
              <Button 
                variant="contained" 
                component={RouterLink} 
                to="/domain"
                fullWidth
              >
                Search by Domain
              </Button>
            </CardActions>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={6}>
          <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
            <CardContent sx={{ flexGrow: 1 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <BusinessIcon fontSize="large" sx={{ mr: 1 }} />
                <Typography variant="h5" component="h2">
                  Organization Search
                </Typography>
              </Box>
              <Typography>
                Find domains registered by an organization using crt.sh certificate
                transparency logs. Get detailed information about all discovered domains.
              </Typography>
            </CardContent>
            <CardActions>
              <Button 
                variant="contained" 
                component={RouterLink} 
                to="/organization"
                fullWidth
              >
                Search by Organization
              </Button>
            </CardActions>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default HomePage; 