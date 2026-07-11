import { helper } from "./helper.js";

export class BaseService {}

export class Service extends BaseService {
  run(value) {
    return normalize(helper(value));
  }
}

export function normalize(value) {
  return value;
}
