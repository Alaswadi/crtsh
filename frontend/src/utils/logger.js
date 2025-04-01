// Simple logger utility for frontend
const logger = {
  info: (...args) => {
    if (process.env.NODE_ENV === 'development') {
      console.log('[INFO]', ...args);
    }
  },
  error: (...args) => {
    if (process.env.NODE_ENV === 'development') {
      console.error('[ERROR]', ...args);
    }
  },
  warn: (...args) => {
    if (process.env.NODE_ENV === 'development') {
      console.warn('[WARN]', ...args);
    }
  },
  debug: (...args) => {
    if (process.env.NODE_ENV === 'development') {
      console.debug('[DEBUG]', ...args);
    }
  }
};

export default logger; 