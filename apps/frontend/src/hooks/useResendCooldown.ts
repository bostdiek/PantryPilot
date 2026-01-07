import { useEffect, useState } from 'react';

// Shared localStorage key for all resend verification cooldowns
const RESEND_COOLDOWN_KEY = 'pantrypilot_resend_verification_cooldown';

/**
 * Custom hook for managing resend verification email cooldown
 *
 * This hook handles:
 * - Cooldown timer state
 * - localStorage persistence (survives page refresh)
 * - Automatic countdown
 *
 * @returns Object with cooldown state and setter function
 */
export function useResendCooldown() {
  const [cooldown, setCooldown] = useState(0);

  // Initialize cooldown from localStorage on mount
  useEffect(() => {
    const storedCooldown = localStorage.getItem(RESEND_COOLDOWN_KEY);
    if (storedCooldown) {
      const endTime = parseInt(storedCooldown, 10);
      const remaining = Math.ceil((endTime - Date.now()) / 1000);
      if (remaining > 0) {
        setCooldown(remaining);
      } else {
        localStorage.removeItem(RESEND_COOLDOWN_KEY);
      }
    }
  }, []);

  // Cooldown timer effect
  useEffect(() => {
    if (cooldown <= 0) return;

    const timer = setInterval(() => {
      setCooldown((prev) => {
        if (prev <= 1) {
          localStorage.removeItem(RESEND_COOLDOWN_KEY);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [cooldown]);

  /**
   * Start a new cooldown period
   * @param seconds - Duration of cooldown in seconds (default 60)
   */
  const startCooldown = (seconds: number = 60) => {
    const endTime = Date.now() + seconds * 1000;
    localStorage.setItem(RESEND_COOLDOWN_KEY, endTime.toString());
    setCooldown(seconds);
  };

  return {
    cooldown,
    startCooldown,
  };
}
