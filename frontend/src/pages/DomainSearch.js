import React, { useState, useEffect } from 'react';
import { Box, TextField, Button, Typography, Container, Switch, FormControlLabel, CircularProgress, LinearProgress, Alert } from '@mui/material';
import { DataGrid } from '@mui/x-data-grid';
import axios from 'axios';

function DomainSearch() {
  const [domain, setDomain] = useState('');
  const [loading, setLoading] = useState(false);
  const [httpxLoading, setHttpxLoading] = useState(false);
  const [subdomains, setSubdomains] = useState([]);
  const [httpxResults, setHttpxResults] = useState([]);
  const [useCache, setUseCache] = useState(true);
  const [useBackgroundTask, setUseBackgroundTask] = useState(false);
  const [taskStatus, setTaskStatus] = useState(null);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const [runHttpx, setRunHttpx] = useState(false);
  const [httpxStatus, setHttpxStatus] = useState('not_started');

  // Polling for background task status
  useEffect(() => {
    let intervalId = null;
    
    if (taskStatus === 'processing') {
      intervalId = setInterval(async () => {
        try {
          const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/domains/status?domain=${domain}`);
          
          if (response.data) {
            setProgress(response.data.progress || 0);
            
            // If completed, fetch the results
            if (response.data.status === 'completed') {
              clearInterval(intervalId);
              setTaskStatus('completed');
              fetchResults();
            } else if (response.data.status === 'error') {
              clearInterval(intervalId);
              setTaskStatus('error');
              setError(response.data.message || 'An error occurred during processing');
              setLoading(false);
            }
            
            // Check httpx status if available
            if (response.data.httpx_status) {
              setHttpxStatus(response.data.httpx_status);
              if (response.data.httpx_status === 'completed') {
                fetchHttpxResults();
              }
            }
          }
        } catch (error) {
          console.error('Error checking task status:', error);
        }
      }, 3000); // Poll every 3 seconds
    }
    
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [taskStatus, domain]);
  
  // Polling for httpx results when httpx is running
  useEffect(() => {
    let httpxIntervalId = null;
    
    if (httpxStatus === 'running') {
      httpxIntervalId = setInterval(async () => {
        try {
          // Check if httpx has completed
          const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/domains/status?domain=${domain}`);
          
          if (response.data && response.data.httpx_status === 'completed') {
            clearInterval(httpxIntervalId);
            setHttpxStatus('completed');
            fetchHttpxResults();
          }
        } catch (error) {
          console.error('Error checking httpx status:', error);
        }
      }, 5000); // Poll every 5 seconds for httpx
    }
    
    return () => {
      if (httpxIntervalId) {
        clearInterval(httpxIntervalId);
      }
    };
  }, [httpxStatus, domain]);

  const fetchResults = async () => {
    try {
      const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/domains?domain=${domain}&use_cache=${useCache}`);
      
      if (response.data) {
        // Update subdomains
        if (response.data.subdomains) {
          setSubdomains(response.data.subdomains.map((subdomain, index) => ({
            id: index,
            subdomain: subdomain
          })));
        }
        
        // Update httpx results if available
        if (response.data.httpx_results) {
          setHttpxResults(response.data.httpx_results.map((result, index) => ({
            id: `httpx-${index}`,
            ...result
          })));
        }
        
        // Update httpx status
        if (response.data.httpx_status) {
          setHttpxStatus(response.data.httpx_status);
        }
      }
      
      setLoading(false);
    } catch (error) {
      console.error('Error fetching results:', error);
      setError(error.response?.data?.detail || 'An error occurred while fetching results');
      setLoading(false);
    }
  };
  
  const fetchHttpxResults = async () => {
    try {
      const response = await axios.get(`${process.env.REACT_APP_API_URL}/api/domains?domain=${domain}&use_cache=${useCache}`);
      
      if (response.data && response.data.httpx_results) {
        setHttpxResults(response.data.httpx_results.map((result, index) => ({
          id: `httpx-${index}`,
          ...result
        })));
      }
      
      setHttpxLoading(false);
    } catch (error) {
      console.error('Error fetching httpx results:', error);
      setHttpxLoading(false);
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    
    if (!domain) {
      setError('Please enter a domain name');
      return;
    }
    
    setLoading(true);
    setError(null);
    setSubdomains([]);
    setHttpxResults([]);
    setProgress(0);
    setTaskStatus(null);
    setHttpxStatus('not_started');
    
    try {
      // Make the API request including the background_task parameter
      const response = await axios.get(
        `${process.env.REACT_APP_API_URL}/api/domains?domain=${domain}&use_cache=${useCache}&background_task=${useBackgroundTask}&run_httpx=${runHttpx}`
      );
      
      if (response.data.status === 'processing') {
        // If it's a background task, update the status and start polling
        setTaskStatus('processing');
      } else {
        // If it's a direct response, update the UI with the results
        if (response.data.subdomains) {
          setSubdomains(response.data.subdomains.map((subdomain, index) => ({
            id: index,
            subdomain: subdomain
          })));
        }
        
        if (response.data.httpx_results) {
          setHttpxResults(response.data.httpx_results.map((result, index) => ({
            id: `httpx-${index}`,
            ...result
          })));
        }
        
        if (response.data.httpx_status) {
          setHttpxStatus(response.data.httpx_status);
        }
        
        setLoading(false);
      }
    } catch (error) {
      console.error('Error submitting request:', error);
      setError(error.response?.data?.detail || 'An error occurred while processing the request');
      setLoading(false);
    }
  };
  
  const runHttpxScan = async () => {
    setHttpxLoading(true);
    setHttpxStatus('running');
    
    try {
      await axios.get(`${process.env.REACT_APP_API_URL}/api/domains/httpx?domain=${domain}&use_cache=${useCache}`);
      // The status will be updated by the polling function
    } catch (error) {
      console.error('Error starting httpx scan:', error);
      setHttpxStatus('error');
      setError(error.response?.data?.detail || 'An error occurred while starting httpx scan');
      setHttpxLoading(false);
    }
  };

  const subdomainColumns = [
    { field: 'subdomain', headerName: 'Subdomain', flex: 1 }
  ];

  const httpxColumns = [
    { field: 'url', headerName: 'URL', flex: 1 },
    { field: 'status_code', headerName: 'Status Code', width: 150 },
    { field: 'title', headerName: 'Title', flex: 1 },
    { field: 'content_length', headerName: 'Content Length', width: 150 }
  ];

  return (
    <Container maxWidth="lg">
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Domain Search
        </Typography>
        
        <Box component="form" onSubmit={handleSubmit} noValidate sx={{ mt: 1 }}>
          <TextField
            margin="normal"
            required
            fullWidth
            id="domain"
            label="Domain Name"
            name="domain"
            autoFocus
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
          />
          
          <Box sx={{ display: 'flex', alignItems: 'center', mt: 2 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={useCache}
                  onChange={(e) => setUseCache(e.target.checked)}
                  color="primary"
                />
              }
              label="Use Cache"
            />
            
            <FormControlLabel
              control={
                <Switch
                  checked={useBackgroundTask}
                  onChange={(e) => setUseBackgroundTask(e.target.checked)}
                  color="primary"
                />
              }
              label="Background Task"
            />
            
            <FormControlLabel
              control={
                <Switch
                  checked={runHttpx}
                  onChange={(e) => setRunHttpx(e.target.checked)}
                  color="primary"
                />
              }
              label="Run HTTPX (may cause timeouts for large domains)"
            />
          </Box>
          
          <Button
            type="submit"
            fullWidth
            variant="contained"
            sx={{ mt: 3, mb: 2 }}
            disabled={loading || !domain}
          >
            {loading ? 'Searching...' : 'Search'}
          </Button>
        </Box>
        
        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
        
        {taskStatus === 'processing' && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="body1" sx={{ mb: 1 }}>
              Processing in background... ({progress}%)
            </Typography>
            <LinearProgress variant="determinate" value={progress} />
          </Box>
        )}
        
        {loading && !taskStatus && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
            <CircularProgress />
          </Box>
        )}
        
        {subdomains.length > 0 && (
          <Box sx={{ mt: 4 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="h6" component="h2" gutterBottom>
                Subdomains ({subdomains.length})
              </Typography>
              
              {httpxStatus === 'not_started' && subdomains.length > 0 && (
                <Button 
                  variant="outlined" 
                  onClick={runHttpxScan}
                  disabled={httpxLoading}
                >
                  Run HTTPX Scan
                </Button>
              )}
              
              {httpxStatus === 'running' && (
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <CircularProgress size={24} sx={{ mr: 1 }} />
                  <Typography variant="body2">HTTPX Scan in progress...</Typography>
                </Box>
              )}
            </Box>
            
            <Box sx={{ height: 400, width: '100%' }}>
              <DataGrid
                rows={subdomains}
                columns={subdomainColumns}
                pageSize={10}
                rowsPerPageOptions={[10, 25, 50, 100]}
                disableSelectionOnClick
              />
            </Box>
          </Box>
        )}
        
        {httpxResults.length > 0 && (
          <Box sx={{ mt: 4 }}>
            <Typography variant="h6" component="h2" gutterBottom>
              HTTPX Results ({httpxResults.length})
            </Typography>
            <Box sx={{ height: 400, width: '100%' }}>
              <DataGrid
                rows={httpxResults}
                columns={httpxColumns}
                pageSize={10}
                rowsPerPageOptions={[10, 25, 50, 100]}
                disableSelectionOnClick
              />
            </Box>
          </Box>
        )}
      </Box>
    </Container>
  );
}

export default DomainSearch; 