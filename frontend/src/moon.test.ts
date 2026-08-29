import { moonKind, moonIllumination, moonLabelKey } from './moon';

describe('Moon Calculations', () => {
  describe('moonKind', () => {
    it('identifies new moon correctly', () => {
      // Known new moon: Jan 6, 2000, 18:14 UTC
      const newMoonDate = new Date(Date.UTC(2000, 0, 6, 18, 14));
      expect(moonKind(newMoonDate)).toBe('new');
    });

    it('identifies waxing moon correctly', () => {
      // 7 days after new moon
      const waxingMoonDate = new Date(Date.UTC(2000, 0, 13, 18, 14));
      expect(moonKind(waxingMoonDate)).toBe('waxing');
    });

    it('identifies full moon correctly', () => {
      // Approx 14.76 days after new moon
      const fullMoonDate = new Date(Date.UTC(2000, 0, 21, 12, 0));
      expect(moonKind(fullMoonDate)).toBe('full');

      // Known full moon: Dec 27, 2023, 00:33 UTC
      const knownFullMoon = new Date(Date.UTC(2023, 11, 27, 0, 33));
      expect(moonKind(knownFullMoon)).toBe('full');
    });

    it('identifies waning moon correctly', () => {
      // Approx 22 days after new moon
      const waningMoonDate = new Date(Date.UTC(2000, 0, 28, 12, 0));
      expect(moonKind(waningMoonDate)).toBe('waning');
    });

    it('works without arguments (uses current date)', () => {
      // Just test that it runs without throwing and returns a valid kind
      const kind = moonKind();
      expect(['new', 'waxing', 'full', 'waning']).toContain(kind);
    });
  });

  describe('moonIllumination', () => {
    it('calculates ~0 illumination for new moon', () => {
      const newMoonDate = new Date(Date.UTC(2000, 0, 6, 18, 14));
      expect(moonIllumination(newMoonDate)).toBeCloseTo(0, 2);
    });

    it('calculates ~0.5 illumination for first quarter (waxing)', () => {
      // Approx 7.38 days after new moon
      const firstQuarter = new Date(Date.UTC(2000, 0, 14, 3, 20)); // Approx
      expect(moonIllumination(firstQuarter)).toBeCloseTo(0.5, 1);
    });

    it('calculates ~1 illumination for full moon', () => {
      const fullMoonDate = new Date(Date.UTC(2023, 11, 27, 0, 33));
      expect(moonIllumination(fullMoonDate)).toBeCloseTo(1, 2);
    });

    it('works without arguments (uses current date)', () => {
      const illumination = moonIllumination();
      expect(illumination).toBeGreaterThanOrEqual(0);
      expect(illumination).toBeLessThanOrEqual(1);
    });
  });

  describe('moonLabelKey', () => {
    it('returns correct key for "new"', () => {
      expect(moonLabelKey('new')).toBe('moon_new');
    });

    it('returns correct key for "waxing"', () => {
      expect(moonLabelKey('waxing')).toBe('moon_waxing');
    });

    it('returns correct key for "full"', () => {
      expect(moonLabelKey('full')).toBe('moon_full');
    });

    it('returns correct key for "waning"', () => {
      expect(moonLabelKey('waning')).toBe('moon_waning');
    });
  });
});
