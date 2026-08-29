import { renderHook, act } from "@testing-library/react-hooks";
import { useAudio, playUrl, stopAudio } from "./audio";
import { createAudioPlayer, setAudioModeAsync } from "expo-audio";

// Mock expo-audio
const mockPlay = jest.fn();
const mockPause = jest.fn();
const mockReplace = jest.fn();
const mockAddListener = jest.fn();

const mockPlayer = {
  play: mockPlay,
  pause: mockPause,
  replace: mockReplace,
  addListener: mockAddListener,
};

jest.mock("expo-audio", () => {
  return {
    createAudioPlayer: jest.fn(() => mockPlayer),
    setAudioModeAsync: jest.fn(),
  };
});

describe("useAudio", () => {
  let statusListener: ((status: any) => void) | undefined;

  beforeEach(() => {
    jest.clearAllMocks();

    mockAddListener.mockImplementation((event, cb) => {
      if (event === "playbackStatusUpdate") {
        statusListener = cb;
      }
    });
  });

  afterEach(() => {
    // clean up state for next tests by sending a fake event to reset the hook's playing state
    act(() => {
      stopAudio();
      if (statusListener) statusListener({ didJustFinish: true });
    });
  });

  it("should have correct initial state", () => {
    const { result } = renderHook(() => useAudio());

    expect(result.current.url).toBeNull();
    expect(result.current.playing).toBe(false);
    expect(result.current.loading).toBe(false);
  });

  it("playUrl should configure audio mode, replace URI, and play", async () => {
    const { result } = renderHook(() => useAudio());

    await act(async () => {
      await result.current.play("http://example.com/audio.mp3");
    });

    expect(setAudioModeAsync).toHaveBeenCalledWith({ playsInSilentMode: true, allowsRecording: false });
    // In later tests createAudioPlayer won't be called because `player` is cached
    // expect(createAudioPlayer).toHaveBeenCalled();
    expect(mockPlayer.replace).toHaveBeenCalledWith({ uri: "http://example.com/audio.mp3" });
    expect(mockPlayer.play).toHaveBeenCalled();

    expect(result.current.loading).toBe(true);
    expect(result.current.url).toBe("http://example.com/audio.mp3");
    expect(result.current.playing).toBe(false);
  });

  it("should update state on playbackStatusUpdate playing", async () => {
    const { result } = renderHook(() => useAudio());

    await act(async () => {
      await result.current.play("http://example.com/audio.mp3");
    });

    // Simulate player starting to play
    act(() => {
      if (statusListener) statusListener({ playing: true });
    });

    expect(result.current.playing).toBe(true);
    expect(result.current.loading).toBe(false);
  });

  it("should update state on playbackStatusUpdate didJustFinish", async () => {
    const { result } = renderHook(() => useAudio());

    await act(async () => {
      await result.current.play("http://example.com/audio.mp3");
    });

    act(() => {
      if (statusListener) statusListener({ playing: true });
    });
    expect(result.current.playing).toBe(true);

    // Simulate playback finish
    act(() => {
      if (statusListener) statusListener({ didJustFinish: true });
    });

    expect(result.current.playing).toBe(false);
    expect(result.current.loading).toBe(false);
  });

  it("playUrl error handling", async () => {
    const { result } = renderHook(() => useAudio());

    mockPlay.mockImplementationOnce(() => {
      throw new Error("Play error");
    });

    try {
      await act(async () => {
        await result.current.play("http://example.com/error.mp3");
      });
    } catch (e) {
      // expected error
    }

    expect(result.current.loading).toBe(false);
    expect(result.current.playing).toBe(false);
  });

  it("stopAudio should pause player and reset state", async () => {
    const { result } = renderHook(() => useAudio());

    await act(async () => {
      await result.current.play("http://example.com/audio.mp3");
    });

    act(() => {
      if (statusListener) statusListener({ playing: true });
    });
    expect(result.current.playing).toBe(true);

    act(() => {
      result.current.stop();
    });

    expect(mockPlayer.pause).toHaveBeenCalled();
    expect(result.current.playing).toBe(false);
    expect(result.current.loading).toBe(false);
  });

});
