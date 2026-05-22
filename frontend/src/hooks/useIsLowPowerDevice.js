export function useIsLowPowerDevice() {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const isMobile = window.matchMedia('(max-width: 768px)').matches;
  const isCoarsePointer = window.matchMedia('(pointer: coarse)').matches;
  const lowCores = (navigator.hardwareConcurrency || 4) <= 4;
  const lowMemory = (navigator.deviceMemory || 8) <= 4;
  return reducedMotion || isMobile || isCoarsePointer || (lowCores && lowMemory);
}
