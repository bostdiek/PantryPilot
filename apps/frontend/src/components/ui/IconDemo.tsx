import { Icon } from './Icon';
import CalendarIcon from './icons/calendar.svg?react';
import ChefHatIcon from './icons/chef-hat.svg?react';
import KitchenIcon from './icons/kitchen.svg?react';
import RestaurantIcon from './icons/restaurant.svg?react';

/**
 * IconDemo component that demonstrates the usage of our custom icons
 */
export function IconDemo() {
  return (
    <div className="flex flex-wrap gap-8 p-4">
      <div className="flex flex-col items-center">
        <Icon svg={KitchenIcon} className="h-8 w-8 text-blue-600" />
        <span className="mt-2 text-sm">Kitchen</span>
      </div>

      <div className="flex flex-col items-center">
        <Icon svg={CalendarIcon} className="h-8 w-8 text-green-600" />
        <span className="mt-2 text-sm">Calendar</span>
      </div>

      <div className="flex flex-col items-center">
        <Icon svg={RestaurantIcon} className="h-8 w-8 text-orange-600" />
        <span className="mt-2 text-sm">Restaurant</span>
      </div>

      <div className="flex flex-col items-center">
        <Icon svg={ChefHatIcon} className="h-8 w-8 text-purple-600" />
        <span className="mt-2 text-sm">Chef Hat</span>
      </div>
    </div>
  );
}
