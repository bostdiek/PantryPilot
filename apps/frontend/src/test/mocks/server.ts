import { setupServer } from 'msw/node';
import { handlers } from './handlers';

// Setup a mock server with the defined handlers
export const server = setupServer(...handlers);
