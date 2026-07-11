export interface ValueSource {
  value(): number;
}

export function helper(value: number): number {
  return value + 1;
}
