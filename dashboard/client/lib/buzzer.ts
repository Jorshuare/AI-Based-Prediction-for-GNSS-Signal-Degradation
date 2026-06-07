/** Lightweight audible alert using the Web Audio API (no audio file needed). */
let ctx: AudioContext | null = null;

function getCtx(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (!ctx) {
    const AC = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    if (AC) ctx = new AC();
  }
  return ctx;
}

/**
 * Two-tone urgent buzzer for a CRITICAL degradation alert.
 * Call from a user-gesture-initiated flow (the Play button) so the browser allows audio.
 */
export function playBuzzer() {
  const ac = getCtx();
  if (!ac) return;
  if (ac.state === "suspended") ac.resume();
  const now = ac.currentTime;
  const beep = (start: number, freq: number) => {
    const osc = ac.createOscillator();
    const gain = ac.createGain();
    osc.type = "square";
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0.0001, now + start);
    gain.gain.exponentialRampToValueAtTime(0.18, now + start + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + start + 0.16);
    osc.connect(gain).connect(ac.destination);
    osc.start(now + start);
    osc.stop(now + start + 0.18);
  };
  beep(0, 880);     // A5
  beep(0.2, 1175);  // D6 — rising = urgency
}

/** Unlock audio inside a user gesture (browsers block autoplay otherwise). */
export function primeAudio() {
  const ac = getCtx();
  if (ac && ac.state === "suspended") ac.resume();
}
