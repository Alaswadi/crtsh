import React, { useState, useEffect } from 'react';
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
  Grid,
  LinearProgress
} from '@mui/material';
import axios from 'axios';

const DomainSearch = () => {
  const [domain, setDomain] = useState('');
  const [useCache, setUseCache] = useState(true);
  const [useBackgroundTask, setUseBackgroundTask] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [results, setResults] = useState(null);
  const [taskStatus, setTaskStatus] = useState(null);
  const [progress, setProgress] = useState(0);
  
  // Poll for background task status
  useEffect(() => {
    let interval = null;
    
    if (taskStatus && taskStatus.status === 'processing') {
      interval = setInterval(async () => {
        try {
          const response = await axios.get(`/api/domains/status?domain=${taskStatus.domain}`);
          setProgress(response.data.progress || 0);
          
          // If the task is completed, fetch the results
          if (response.data.status === 'completed') {
            clearInterval(interval);
            const resultResponse = await axios.get(`/api/domains/?domain=${taskStatus.domain}&use_cache=true`);
            setResults(resultResponse.data);
            setTaskStatus(null);
            setLoading(false);
          } else if (response.data.status === 'error') {
            clearInterval(interval);
            setError(`Background task error: ${response.data.error}`);
            setTaskStatus(null);
            setLoading(false);
          }
        } catch (err) {
          console.error("Error polling task status:", err);
        }
      }, 3000); // Poll every 3 seconds
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [taskStatus]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!domain) {
      setError('Please enter a domain name');
      return;
    }
    
    setLoading(true);
    setError('');
    setResults(null);
    setTaskStatus(null);
    
    try {
      const response = await axios.get(`/api/domains/?domain=${domain}&use_cache=${useCache}&background_task=${useBackgroundTask}`);
      
      // Check if it's a background task
      if (response.data.status === 'processing') {
        setTaskStatus({
          domain: domain,
          status: 'processing'
        });
        setProgress(response.data.progress || 0);
      } else {
        // Regular response with immediate results
        setResults(response.data);
        setLoading(false);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'An error occurred while fetching data');
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
          
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
            <FormControlLabel
              control={
                <Switch 
                  checked={useCache} 
                  onChange={(e) => setUseCache(e.target.checked)} 
                />
              }
              label="Use Cache (faster if you've searched this domain before)"
            />
            
            <FormControlLabel
              control={
                <Switch 
                  checked={useBackgroundTask} 
                  onChange={(e) => setUseBackgroundTask(e.target.checked)} 
                />
              }
              label="Background Task (for large domains like hilton.com)"
            />
          </Box>
          
          <Button 
            type="submit" 
            variant="contained" 
            size="large"
            disabled={loading || !domain}
            sx={{ mt: 2 }}
            fullWidth
          >
            {loading && !taskStatus ? <CircularProgress size={24} /> : 'Search'}
          </Button>
        </Box>
      </Paper>
      
      {error && (
        <Alert severity="error" sx={{ mb: 4 }}>
          {error}
        </Alert>
      )}
      
      {taskStatus && taskStatus.status === 'processing' && (
        <Paper elevation={3} sx={{ p: 4, mb: 4 }}>
          <Typography variant="h5" gutterBottom>
            Processing domain {taskStatus.domain}
          </Typography>
          <Typography variant="body1" paragraph>
            This domain is being processed in the background. This may take a few minutes for large domains.
          </Typography>
          
          <Box sx={{ width: '100%', mt: 2, mb: 2 }}>
            <LinearProgress variant="determinate" value={progress} />
            <Typography variant="body2" align="center" sx={{ mt: 1 }}>
              {progress}% Complete
            </Typography>
          </Box>
        </Paper>
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

export default DomainSearch; 