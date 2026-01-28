/**
 * WebSocket API - Real-time connection utilities
 */

const API_URL = process.env.REACT_APP_BACKEND_URL;

// ==================== WebSocket for Notifications ====================

export const connectNotificationsWS = (token, onMessage, onError) => {
  const wsUrl = API_URL.replace('https://', 'wss://').replace('http://', 'ws://');
  const ws = new WebSocket(`${wsUrl}/ws/notifications/${token}`);
  
  let pingInterval = null;
  
  ws.onopen = () => {
    console.log('WebSocket connected');
    // Send ping every 30 seconds to keep alive
    pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
      }
    }, 30000);
  };
  
  ws.onmessage = (event) => {
    if (event.data === 'pong') return;
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (e) {
      console.error('Failed to parse WebSocket message:', e);
    }
  };
  
  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    if (onError) onError(error);
  };
  
  ws.onclose = () => {
    console.log('WebSocket disconnected');
    if (pingInterval) {
      clearInterval(pingInterval);
    }
  };
  
  return ws;
};

// ==================== WebSocket for Project Updates ====================

export const connectProjectWS = (projectId, token, onMessage, onError) => {
  const wsUrl = API_URL.replace('https://', 'wss://').replace('http://', 'ws://');
  const ws = new WebSocket(`${wsUrl}/ws/project/${projectId}?token=${token}`);
  
  ws.onopen = () => {
    console.log(`Project WebSocket connected: ${projectId}`);
  };
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch (e) {
      console.error('Failed to parse WebSocket message:', e);
    }
  };
  
  ws.onerror = (error) => {
    console.error('Project WebSocket error:', error);
    if (onError) onError(error);
  };
  
  ws.onclose = () => {
    console.log(`Project WebSocket disconnected: ${projectId}`);
  };
  
  return ws;
};
