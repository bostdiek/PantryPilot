export const dialogSizes = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  full: 'max-w-full mx-4',
} as const;

export const inputSizes = {
  sm: 'text-sm py-1 px-2',
  md: 'text-base py-2 px-3',
  lg: 'text-lg py-2.5 px-4',
} as const;

export const switchTrackSizes = {
  sm: 'h-5 w-9',
  md: 'h-6 w-11',
  lg: 'h-7 w-14',
} as const;

export const switchKnobSizes = {
  sm: 'h-3 w-3 translate-x-0.5 group-data-[checked]:translate-x-5',
  md: 'h-4 w-4 translate-x-1 group-data-[checked]:translate-x-6',
  lg: 'h-5 w-5 translate-x-1 group-data-[checked]:translate-x-8',
} as const;
