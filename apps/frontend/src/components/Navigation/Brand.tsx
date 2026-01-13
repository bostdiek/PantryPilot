import type { FC } from 'react';
import logoSvg from '../../assets/logo/smartmealplanner-logo.svg';

/**
 * Brand component that displays the SmartMealPlanner logo with text.
 * Responsive: shows text on desktop, hides on mobile if space constrained.
 */
export const Brand: FC = () => {
  return (
    <div className="flex items-center gap-2">
      <img src={logoSvg} alt="SmartMealPlanner" className="h-8 w-8" />
      <span className="hidden text-lg font-bold text-gray-800 sm:inline">
        SmartMealPlanner
      </span>
    </div>
  );
};

export default Brand;
