import React from 'react';
import { Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import Navigation from './components/Navigation';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import MealPlanPage from './pages/MealPlanPage';
import RecipesDetail from './pages/RecipesDetail';
import NewRecipePage from './pages/RecipesNewPage';
import RecipesPage from './pages/RecipesPage';

const App: React.FC = () => (
  <Router>
    <Navigation />
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/recipes" element={<RecipesPage />} />
      <Route path="/recipes/new" element={<NewRecipePage />} />
      <Route path="/recipes/:id" element={<RecipesDetail />} />
      <Route path="/meal-plan" element={<MealPlanPage />} />
      <Route path="/login" element={<LoginPage />} />
    </Routes>
  </Router>
);

export default App;
