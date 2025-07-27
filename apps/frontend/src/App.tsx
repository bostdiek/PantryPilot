import { useState } from 'react';
import './App.css';
import reactLogo from './assets/react.svg';
import viteLogo from '/vite.svg';

function App() {
  const [count, setCount] = useState(0);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-100">
      <div className="max-w-md rounded-lg bg-white p-8 shadow-md">
        <div className="mb-6 flex justify-center space-x-4">
          <a href="https://vite.dev" target="_blank">
            <img src={viteLogo} className="logo" alt="Vite logo" />
          </a>
          <a href="https://react.dev" target="_blank">
            <img src={reactLogo} className="logo react" alt="React logo" />
          </a>
        </div>
        <h1 className="mb-6 text-center text-3xl font-bold text-gray-800">
          Vite + React
        </h1>
        <div className="card text-center">
          <button
            onClick={() => setCount((count) => count + 1)}
            className="mb-4 rounded bg-blue-500 px-4 py-2 font-bold text-white hover:bg-blue-700"
          >
            count is {count}
          </button>
          <p className="mb-4 text-gray-600">
            Edit <code className="rounded bg-gray-200 px-1">src/App.tsx</code>{' '}
            and save to test HMR
          </p>
        </div>
        <p className="read-the-docs text-center text-sm text-gray-500">
          Click on the Vite and React logos to learn more
        </p>
      </div>
    </div>
  );
}

export default App;
