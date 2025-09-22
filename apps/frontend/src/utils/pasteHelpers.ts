/**
 * Utility functions for detecting and splitting multi-step content in recipe instructions
 */

/**
 * Determines if pasted text contains multiple recipe steps based on heuristics
 * @param text - The pasted text to analyze
 * @returns True if the text appears to contain multiple steps
 */
export function looksMultiStep(text: string): boolean {
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
  // First, try splitting on blank line groups
  const blocks = raw
    .split(/\n{2,}/)
    .map((block) => block.trim())
    .filter(Boolean);

  let candidates = blocks;

  // If only one block resulted, fallback to numbered list splitting
  if (candidates.length === 1) {
    const lines = raw.split(/\n+/);
    const accum: string[] = [];
    let current: string[] = [];
    const numberRe = /^\s*\d+[.)]\s+/;

    for (const line of lines) {
      const trimmedLine = line.trim();
      if (!trimmedLine) continue; // Skip empty lines

      if (numberRe.test(trimmedLine) && current.length > 0) {
        // Start of a new numbered step, save current and start new
        accum.push(current.join(' ').trim());
        current = [trimmedLine.replace(numberRe, '').trim()];
      } else if (numberRe.test(trimmedLine)) {
        // First numbered step
        current.push(trimmedLine.replace(numberRe, '').trim());
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
  return candidates.map((step) => step.replace(/\s+/g, ' ').trim()).filter(Boolean);
}