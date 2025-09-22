export function dayButtonAriaLabel(
  dayOfWeek: string,
  date: string,
  isToday: boolean
): string {
  return `Add recipe to ${dayOfWeek}, ${date}${isToday ? ' (Today)' : ''}`;
}
