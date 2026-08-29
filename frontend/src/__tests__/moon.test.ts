import { moonIllumination } from '../moon';

describe('moon module', () => {
  describe('moonIllumination', () => {
    it('calculates roughly 0 illumination at a known new moon date', () => {
      // Jan 6, 2000 18:14 UTC was a known new moon (according to the code)
      const date = new Date(Date.UTC(2000, 0, 6, 18, 14));
      const illum = moonIllumination(date);
      expect(illum).toBeCloseTo(0, 3);
    });

    it('calculates roughly 1 illumination at a known full moon date', () => {
      // ~14.76 days after the known new moon
      const date = new Date(Date.UTC(2000, 0, 6, 18, 14) + 14.765294335 * 86400000);
      const illum = moonIllumination(date);
      expect(illum).toBeCloseTo(1, 3);
    });

    it('calculates roughly 0.5 illumination at first quarter moon', () => {
      // ~7.38 days after new moon
      const date = new Date(Date.UTC(2000, 0, 6, 18, 14) + 7.382647167 * 86400000);
      const illum = moonIllumination(date);
      expect(illum).toBeCloseTo(0.5, 3);
    });

    it('calculates roughly 0.5 illumination at last quarter moon', () => {
      // ~22.15 days after new moon
      const date = new Date(Date.UTC(2000, 0, 6, 18, 14) + 22.147941502 * 86400000);
      const illum = moonIllumination(date);
      expect(illum).toBeCloseTo(0.5, 3);
    });

    it('uses current date as default argument', () => {
      // It's hard to mock new Date() without altering global scope,
      // but we can ensure calling it without args doesn't throw and returns a valid float.
      const illum = moonIllumination();
      expect(typeof illum).toBe('number');
      expect(illum).toBeGreaterThanOrEqual(0);
      expect(illum).toBeLessThanOrEqual(1);
    });
  });
});
