import { moonKind, moonIllumination, moonLabelKey } from "../moon";

describe("moonKind", () => {
  it("should return the correct moon kind for a known new moon date", () => {
    // New moon on January 6, 2000 18:14 UTC (same as the 'known' base date)
    const date = new Date(Date.UTC(2000, 0, 6, 18, 14));
    expect(moonKind(date)).toBe("new");
  });

  it("should return the correct moon kind for a waxing moon", () => {
    // Approx 7 days after new moon
    const date = new Date(Date.UTC(2000, 0, 6 + 7, 18, 14));
    expect(moonKind(date)).toBe("waxing");
  });

  it("should return the correct moon kind for a full moon", () => {
    // Full moon approx 14.76 days after new moon
    const date = new Date(Date.UTC(2000, 0, 6 + 15, 18, 14));
    expect(moonKind(date)).toBe("full");
  });

  it("should return the correct moon kind for a waning moon", () => {
    // Approx 22 days after new moon
    const date = new Date(Date.UTC(2000, 0, 6 + 22, 18, 14));
    expect(moonKind(date)).toBe("waning");
  });

  it("should return a kind when no date is passed", () => {
    const kind = moonKind();
    expect(["new", "waxing", "full", "waning"]).toContain(kind);
  });
});

describe("moonIllumination", () => {
  it("should return 0 for a known new moon date", () => {
    const date = new Date(Date.UTC(2000, 0, 6, 18, 14));
    expect(moonIllumination(date)).toBeCloseTo(0, 5);
  });

  it("should return 1 for a full moon", () => {
    // Approx 14.76 days after new moon
    const date = new Date(Date.UTC(2000, 0, 6 + 14.765, 18, 14));
    expect(moonIllumination(date)).toBeCloseTo(1, 1);
  });

  it("should return ~0.5 for waxing quarter", () => {
    const date = new Date(Date.UTC(2000, 0, 6 + 7.38, 18, 14));
    expect(moonIllumination(date)).toBeCloseTo(0.5, 1);
  });

  it("should return an illumination when no date is passed", () => {
    const ill = moonIllumination();
    expect(ill).toBeGreaterThanOrEqual(0);
    expect(ill).toBeLessThanOrEqual(1);
  });
});

describe("moonLabelKey", () => {
  it("should return the correct locale string keys", () => {
    expect(moonLabelKey("new")).toBe("moon_new");
    expect(moonLabelKey("waxing")).toBe("moon_waxing");
    expect(moonLabelKey("full")).toBe("moon_full");
    expect(moonLabelKey("waning")).toBe("moon_waning");
  });
});
