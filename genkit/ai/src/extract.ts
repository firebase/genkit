export function extractJson<T = unknown>(text: string): T | null {
  let openingChar: '{' | '[' | undefined;
  let closingChar: '}' | ']' | undefined;
  let startPos: number | undefined;
  let nestingCount = 0;

  for (let i = 0; i < text.length; i++) {
    const char = text[i].replace(/\u00A0/g, ' ');

    if (!openingChar && (char === '{' || char === '[')) {
      // Look for opening character
      openingChar = char;
      closingChar = char === '{' ? '}' : ']';
      startPos = i;
      nestingCount++;
    } else if (char === openingChar) {
      // Increment nesting for matching opening character
      nestingCount++;
    } else if (char === closingChar) {
      // Decrement nesting for matching closing character
      nestingCount--;
      if (!nestingCount) {
        // Reached end of target element
        return JSON.parse(text.substring(startPos || 0, i + 1)) as T;
      }
    }
  }

  if (startPos !== undefined && nestingCount > 0) {
    try {
      return JSON.parse(text.substring(startPos) + (closingChar || '')) as T;
    } catch (e) {
      throw new Error(`Invalid JSON extracted from model output: ${text}`);
    }
  }
  throw new Error(`No JSON object or array found in model output: ${text}`);
}
