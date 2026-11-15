export interface EpochInfo {
  epoch: number;
  label: string;
  seedA: number;
  seedB: number;
  shiftA: number;
  shiftB: number;
}

/** Epoch time-lapse cards: each card pairs an A/B frame pair. */
export const EPOCHS: EpochInfo[] = [
  { epoch: 0, label: "Epoch 1 (Oct 2026)", seedA: 11, seedB: 12, shiftA: -6, shiftB: -3 },
  { epoch: 1, label: "Epoch 2 (Apr 2026)", seedA: 21, seedB: 22, shiftA: 0, shiftB: 3 },
  { epoch: 2, label: "Epoch 3 (Oct 2026)", seedA: 31, seedB: 32, shiftA: 6, shiftB: 9 },
];

export function getEpochLabel(epoch: number): string {
  return EPOCHS.find((e) => e.epoch === epoch)?.label ?? `Epoch ${epoch + 1}`;
}
