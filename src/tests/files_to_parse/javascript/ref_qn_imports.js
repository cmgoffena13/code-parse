import { alpha as renamed } from "./relative/mod.js";
import * as Star from "../lib/util.ts";

function helper() {
  return 1;
}

function caller() {
  renamed();
  Star.go();
  helper();
}
