/**
 * Utility functions for detecting and splitting multi-step content in recipe instructions
 */

import { logger } from '../lib/logger';

// Maximum content size for paste detection (50KB)
const MAX_PASTE_SIZE = 50000;
// Maximum number of steps to prevent UI freezing
const MAX_STEPS = 50;

/**
 * Determines if pasted text contains multiple recipe steps based on heuristics
 * @param text - The pasted text to analyze
 * @returns True if the text appears to contain multiple steps
 */
export function looksMultiStep(text: string): boolean {
  // Performance guard: skip detection for very large content
  if (text.length > MAX_PASTE_SIZE) {
    logger.warn(
      `Paste content too large (${text.length} chars), skipping multi-step detection`
    );
    return false;
  }

  // Quick early return for empty or very short content
  if (text.trim().length === 0) {
    return false;
  }

  // Heuristic 1: Contains two or more blank-line separated blocks
  if (/\n{2,}/.test(text)) {
    return true;
  }

  // Heuristic 2: Contains numbered list patterns at line starts
  if (/^\s*\d+[.)]\s+/m.test(text)) {
    return true;
  }

  // Heuristic 3: Contains 3+ newline characters total
  const newlineCount = (text.match(/\n/g) || []).length;
  return newlineCount >= 3;
}

/**
 * Splits raw pasted text into individual recipe steps
 * @param raw - The raw pasted text to split
 * @returns Array of individual step strings, cleaned and trimmed
 */
export function splitSteps(raw: string): string[] {
  // Performance guard: return single step for very large content
  if (raw.length > MAX_PASTE_SIZE) {
    logger.warn(
      `Paste content too large (${raw.length} chars), treating as single step`
    );
    return [raw.trim()];
  }

  // Quick early return for empty content
  if (raw.trim().length === 0) {
    return [];
  }

  // Named regex constants for readability
  const BLANK_LINE_SEPARATOR = /\n{2,}/;
  const NUMBERED_STEP_RE = /^\s*\d+[.)]\s+/;

  // First, try splitting on blank line groups
  const blocks = raw
    .split(BLANK_LINE_SEPARATOR)
    .map((block) => block.trim())
    .filter(Boolean);

  let candidates = blocks;

  // If only one block resulted, fallback to numbered list splitting
  if (candidates.length === 1) {
    const lines = raw.split(/\n+/);
    const accum: string[] = [];
    let current: string[] = [];

    for (const line of lines) {
      const trimmedLine = line.trim();
      if (!trimmedLine) continue; // Skip empty lines

      if (NUMBERED_STEP_RE.test(trimmedLine) && current.length > 0) {
        // Start of a new numbered step, save current and start new
        accum.push(current.join(' ').trim());
        current = [trimmedLine.replace(NUMBERED_STEP_RE, '').trim()];
      } else if (NUMBERED_STEP_RE.test(trimmedLine)) {
        // First numbered step
        current.push(trimmedLine.replace(NUMBERED_STEP_RE, '').trim());
      } else {
        // Continuation of current step
        current.push(trimmedLine);
      }
    }

    // Add the last step if we have one
    if (current.length > 0) {
      accum.push(current.join(' ').trim());
    }

    candidates = accum.filter(Boolean);
  }

  // Clean up candidates: collapse duplicate spaces and trim
  const cleanedSteps = candidates
    .map((step) => step.replace(/\s+/g, ' ').trim())
    .filter(Boolean);

  // Performance guard: limit number of steps to prevent UI freezing
  if (cleanedSteps.length > MAX_STEPS) {
    logger.warn(
      `Too many steps detected (${cleanedSteps.length}), limiting to ${MAX_STEPS}`
    );
    return cleanedSteps.slice(0, MAX_STEPS);
  }

  return cleanedSteps;
}
