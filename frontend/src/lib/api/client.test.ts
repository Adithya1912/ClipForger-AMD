import { describe, expect, it } from "vitest";
import { STYLE_LABEL } from "./client";

describe("caption client constants", () => {
  it("labels all four required styles", () => {
    expect(Object.keys(STYLE_LABEL)).toEqual([
      "formal",
      "sarcastic",
      "humorous_tech",
      "humorous_non_tech",
    ]);
  });
});
