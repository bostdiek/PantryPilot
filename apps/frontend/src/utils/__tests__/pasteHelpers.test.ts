import { describe, it, expect } from 'vitest';
import { looksMultiStep, splitSteps } from '../pasteHelpers';

describe('pasteHelpers', () => {
  describe('looksMultiStep', () => {
    it('should return true for text with blank line separators', () => {
      const text = 'Step 1 content\n\nStep 2 content';
      expect(looksMultiStep(text)).toBe(true);
    });

    it('should return true for numbered list patterns', () => {
      const text = '1. Mix ingredients\n2. Bake for 30 minutes';
      expect(looksMultiStep(text)).toBe(true);
    });

    it('should return true for text with 3+ newlines', () => {
      const text = 'First step\nSecond step\nThird step\nFourth step';
      expect(looksMultiStep(text)).toBe(true);
    });

    it('should return false for single-line text', () => {
      const text = 'Mix all ingredients together';
      expect(looksMultiStep(text)).toBe(false);
    });

    it('should return false for text with only 1-2 newlines', () => {
      const text = 'Mix ingredients\nBake in oven';
      expect(looksMultiStep(text)).toBe(false);
    });
  });

  describe('splitSteps', () => {
    it('should split on blank lines', () => {
      const text = 'Heat oil in pan\n\nAdd onions and cook until soft\n\nAdd garlic and stir';
      const result = splitSteps(text);
      expect(result).toEqual([
        'Heat oil in pan',
        'Add onions and cook until soft',
        'Add garlic and stir'
      ]);
    });

    it('should split numbered lists with periods', () => {
      const text = '1. Preheat oven to 350°F\n2. Mix dry ingredients\n3. Add wet ingredients';
      const result = splitSteps(text);
      expect(result).toEqual([
        'Preheat oven to 350°F',
        'Mix dry ingredients',
        'Add wet ingredients'
      ]);
    });

    it('should split numbered lists with parentheses', () => {
      const text = '1) Heat oil\n2) Add vegetables\n3) Season with salt';
      const result = splitSteps(text);
      expect(result).toEqual([
        'Heat oil',
        'Add vegetables',
        'Season with salt'
      ]);
    });

    it('should handle multiline numbered steps', () => {
      const text = '1. Heat oil in a large pan\nover medium heat\n2. Add chopped onions\nand cook until translucent';
      const result = splitSteps(text);
      expect(result).toEqual([
        'Heat oil in a large pan over medium heat',
        'Add chopped onions and cook until translucent'
      ]);
    });

    it('should remove leading/trailing whitespace', () => {
      const text = '  \n  Step 1 content  \n\n  Step 2 content  \n  ';
      const result = splitSteps(text);
      expect(result).toEqual([
        'Step 1 content',
        'Step 2 content'
      ]);
    });

    it('should collapse multiple spaces', () => {
      const text = 'Mix    all     ingredients\n\nBake   for    30   minutes';
      const result = splitSteps(text);
      expect(result).toEqual([
        'Mix all ingredients',
        'Bake for 30 minutes'
      ]);
    });

    it('should filter out empty steps', () => {
      const text = 'Step 1\n\n\n\nStep 2\n\n';
      const result = splitSteps(text);
      expect(result).toEqual([
        'Step 1',
        'Step 2'
      ]);
    });

    it('should return single step if no clear separators found', () => {
      const text = 'Mix all ingredients together and bake';
      const result = splitSteps(text);
      expect(result).toEqual(['Mix all ingredients together and bake']);
    });

    it('should handle complex numbered list with spacing', () => {
      const text = '1.  First step with extra spacing\n 2. Second step\n  3.   Third step   ';
      const result = splitSteps(text);
      expect(result).toEqual([
        'First step with extra spacing',
        'Second step',
        'Third step'
      ]);
    });
  });
});