import AsyncStorage from "@react-native-async-storage/async-storage";
import { Storage } from "./index.web";

jest.mock("@react-native-async-storage/async-storage", () => ({
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
}));

describe("Storage (Web)", () => {
  let storage: Storage;

  beforeEach(() => {
    storage = new Storage();
    jest.clearAllMocks();

    // Silence console.warn from the Storage class during expected error tests
    jest.spyOn(console, "warn").mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe("Error Fallbacks", () => {
    it("getItem gracefully handles AsyncStorage throwing an error and returns fallback", async () => {
      // Mocking AsyncStorage which the actual index.web.ts uses
      jest.spyOn(AsyncStorage, "getItem").mockRejectedValue(new Error("Storage Error"));

      const result = await storage.getItem("my_key", "my_fallback");

      expect(result).toBe("my_fallback");
      expect(AsyncStorage.getItem).toHaveBeenCalledWith("my_key");
      expect(console.warn).toHaveBeenCalled();
    });

    it("setItem gracefully handles AsyncStorage throwing an error and returns false", async () => {
      jest.spyOn(AsyncStorage, "setItem").mockRejectedValue(new Error("Storage Error"));

      const result = await storage.setItem("my_key", "my_value");

      expect(result).toBe(false);
      expect(AsyncStorage.setItem).toHaveBeenCalledWith("my_key", JSON.stringify("my_value"));
      expect(console.warn).toHaveBeenCalled();
    });

    it("removeItem gracefully handles AsyncStorage throwing an error and returns false", async () => {
      jest.spyOn(AsyncStorage, "removeItem").mockRejectedValue(new Error("Storage Error"));

      const result = await storage.removeItem("my_key");

      expect(result).toBe(false);
      expect(AsyncStorage.removeItem).toHaveBeenCalledWith("my_key");
      expect(console.warn).toHaveBeenCalled();
    });
  });
});
