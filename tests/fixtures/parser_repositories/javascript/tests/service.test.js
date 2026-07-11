import { Service } from "../src/service.js";

if (new Service().run(1) !== 2) {
  throw new Error("unexpected result");
}
