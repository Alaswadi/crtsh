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

// Get the API base URL from .env or use empty string if undefined
const API_BASE_URL = process.env.REACT_APP_API_URL || '';

const OrganizationSearch = () => {
  const [orgName, setOrgName] = useState('');
  const [useCache, setUseCache] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [results, setResults] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!orgName) {
      setError('Please enter an organization name');
      return;
    }
    
    setLoading(true);
    setError('');
    setResults(null);
    
    try {
      const response = await axios.get(`${API_BASE_URL}/organizations/?org_name=${orgName}&use_cache=${useCache}`);
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
          Organization Search
        </Typography>
        <Typography variant="body1" paragraph>
          Find domains registered by an organization using certificate transparency logs (crt.sh).
        </Typography>
        
        <Box component="form" onSubmit={handleSubmit} sx={{ mt: 3 }}>
          <TextField
            fullWidth
            label="Organization Name"
            variant="outlined"
            value={orgName}
            onChange={(e) => setOrgName(e.target.value)}
            placeholder="Example Inc"
            sx={{ mb: 2 }}
            helperText="For best results, try using the full organization name. For organizations with spaces in their name, try replacing spaces with '+' (e.g., 'Example+Inc')"
          />
          
          <FormControlLabel
            control={
              <Switch 
                checked={useCache} 
                onChange={(e) => setUseCache(e.target.checked)} 
              />
            }
            label="Use Cache (faster if you've searched this organization before)"
          />
          
          <Button 
            type="submit" 
            variant="contained" 
            size="large"
            disabled={loading || !orgName}
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
              Results for {results.organization}
            </Typography>
            <Typography variant="body1">
              Found {results.total_domains} domains
            </Typography>
            
            <Divider sx={{ my: 2 }} />
            
            <Typography variant="h6" gutterBottom>
              Domains List
            </Typography>
            
            <List dense sx={{ maxHeight: 300, overflow: 'auto', bgcolor: 'background.paper', border: '1px solid rgba(255, 255, 255, 0.12)', borderRadius: 1 }}>
              {results.domains.map((domain, index) => (
                <ListItem key={index}>
                  <ListItemText primary={domain} />
                </ListItem>
              ))}
            </List>
            
            <Typography variant="h6" gutterBottom sx={{ mt: 4 }}>
              HTTP Information
            </Typography>
            
            {results.httpx_results && results.httpx_results.length > 0 ? (
              <Grid container spacing={2}>
                {results.httpx_results.map((result, index) => (
                  <Grid item xs={12} sm={6} md={4} key={index}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle1" gutterBottom>
                          {result.url || result.host || 'Unknown host'}
                        </Typography>
                        <Box sx={{ mt: 1 }}>
                          <Chip 
                            label={`Status: ${result.status_code || 'N/A'}`} 
                            color={result.status_code >= 200 && result.status_code < 400 ? 'success' : 'error'} 
                            size="small" 
                            sx={{ mr: 1, mb: 1 }} 
                          />
                          {result.technologies && result.technologies.length > 0 ? (
                            result.technologies.map((tech, techIndex) => (
                              <Chip key={techIndex} label={tech} size="small" sx={{ mr: 1, mb: 1 }} />
                            ))
                          ) : (
                            <Chip label="No tech detected" size="small" sx={{ mr: 1, mb: 1 }} />
                          )}
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            ) : (
              <Alert severity="info" sx={{ mt: 2 }}>
                No HTTP information available. This could be because httpx didn't return any results
                or the domains are not accessible.
              </Alert>
            )}
          </Paper>
        </Box>
      )}
    </Box>
  );
};

export default OrganizationSearch; 