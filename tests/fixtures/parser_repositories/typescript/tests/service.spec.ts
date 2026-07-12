import { Service } from "../src/service";

const result: number = new Service().run(1);
if (result !== 2) throw new Error("unexpected result");
