import React, { useState } from 'react';
import { 
  Box, 
  Typography, 
  Paper, 
  TextField, 
  Button, 
  FormControlLabel,
  Switch,
  CircularProgress,
  Alert,
  Divider,
  List,
  ListItem,
  ListItemText,
  Chip,
  Card,
  CardContent,
  Grid
} from '@mui/material';
import axios from 'axios';

const DomainSearch = () => {
  const [domain, setDomain] = useState('');
  const [useCache, setUseCache] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [results, setResults] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!domain) {
      setError('Please enter a domain name');
      return;
    }
    
    setLoading(true);
    setError('');
    setResults(null);
    
    try {
      const response = await axios.get(`/api/domains?domain=${domain}&use_cache=${useCache}`);
      setResults(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'An error occurred while fetching data');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <Box>
      <Paper elevation={3} sx={{ p: 4, mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Domain Search
        </Typography>
        <Typography variant="body1" paragraph>
          Search for subdomains of a specific domain using both subfinder and crt.sh.
        </Typography>
        
        <Box component="form" onSubmit={handleSubmit} sx={{ mt: 3 }}>
          <TextField
            fullWidth
            label="Domain Name"
            variant="outlined"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            placeholder="example.com"
            sx={{ mb: 2 }}
          />
          
          <FormControlLabel
            control={
              <Switch 
                checked={useCache} 
                onChange={(e) => setUseCache(e.target.checked)} 
              />
            }
            label="Use Cache (faster if you've searched this domain before)"
          />
          
          <Button 
            type="submit" 
            variant="contained" 
            size="large"
            disabled={loading || !domain}
            sx={{ mt: 2 }}
            fullWidth
          >
            {loading ? <CircularProgress size={24} /> : 'Search'}
          </Button>
        </Box>
      </Paper>
      
      {error && (
        <Alert severity="error" sx={{ mb: 4 }}>
          {error}
        </Alert>
      )}
      
      {results && (
        <Box>
          <Paper elevation={3} sx={{ p: 4, mb: 4 }}>
            <Typography variant="h5" gutterBottom>
              Results for {results.domain}
            </Typography>
            <Typography variant="body1">
              Found {results.total_subdomains} subdomains
            </Typography>
            
            <Divider sx={{ my: 2 }} />
            
            <Typography variant="h6" gutterBottom>
              Subdomains List
            </Typography>
            
            <List dense sx={{ maxHeight: 300, overflow: 'auto', bgcolor: 'background.paper', border: '1px solid rgba(255, 255, 255, 0.12)', borderRadius: 1 }}>
              {results.subdomains.map((subdomain, index) => (
                <ListItem key={index}>
                  <ListItemText primary={subdomain} />
                </ListItem>
              ))}
            </List>
            
            <Typography variant="h6" gutterBottom sx={{ mt: 4 }}>
              HTTP Information
            </Typography>
            
            <Grid container spacing={2}>
              {results.httpx_results.map((result, index) => (
                <Grid item xs={12} sm={6} md={4} key={index}>
                  <Card variant="outlined">
                    <CardContent>
                      <Typography variant="subtitle1" gutterBottom>
                        {result.url || result.host}
                      </Typography>
                      <Box sx={{ mt: 1 }}>
                        <Chip 
                          label={`Status: ${result.status_code || 'N/A'}`} 
                          color={result.status_code >= 200 && result.status_code < 400 ? 'success' : 'error'} 
                          size="small" 
                          sx={{ mr: 1, mb: 1 }} 
                        />
                        {result.technologies && result.technologies.map((tech, techIndex) => (
                          <Chip key={techIndex} label={tech} size="small" sx={{ mr: 1, mb: 1 }} />
                        ))}
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Paper>
        </Box>
      )}
    </Box>
  );
};

export default DomainSearch; 