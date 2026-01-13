// Lightweight logger utility for the frontend
// Keeps console.* usage centralized so we can later redirect to remote logging
type LogLevel = 'debug' | 'info' | 'warn' | 'error';

const isDev =
  import.meta.env.MODE === 'development' || import.meta.env.MODE === 'test';

function formatMessage(level: LogLevel, args: any[]) {
  const prefix = `[SmartMealPlanner:${level.toUpperCase()}]`;
  return [prefix, ...args];
}

export const logger = {
  debug: (...args: any[]) => {
    if (isDev) {
      console.debug(...formatMessage('debug', args));
    }
  },
  info: (...args: any[]) => {
    console.info(...formatMessage('info', args));
  },
  warn: (...args: any[]) => {
    console.warn(...formatMessage('warn', args));
  },
  error: (...args: any[]) => {
    console.error(...formatMessage('error', args));
  },
};

export default logger;
