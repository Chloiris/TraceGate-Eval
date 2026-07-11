import { helper, ValueSource } from "./helper";

export class BaseService {}

export class Service extends BaseService implements ValueSource {
  run(value: number): number {
    return helper(value);
  }

  value(): number {
    return this.run(1);
  }
}

export function normalize(value: number): number {
  return value;
}
