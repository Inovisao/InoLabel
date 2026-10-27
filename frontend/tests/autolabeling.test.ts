import assert from "node:assert/strict";
import { useAutolabelingStore } from "../src/features/autolabeling/store.ts";
import type { Proposal } from "../src/features/autolabeling/types.ts";

const proposal: Proposal = {
  id: "proposal-a", frame_index: 0, category_id: 0, class_name: "person",
  bbox: [1, 2, 10, 20], score: 0.9, status: "pending", annotation_id: null,
};

useAutolabelingStore.getState().reset("project-a-session");
useAutolabelingStore.getState().edit(proposal, { bbox: [3, 4, 12, 24] });
useAutolabelingStore.getState().edit(proposal, { category_id: 1 });
assert.deepEqual(proposal.bbox, [1, 2, 10, 20], "draft editing must not mutate the model's proposal");
assert.deepEqual(useAutolabelingStore.getState().drafts[proposal.id], {
  bbox: [3, 4, 12, 24], category_id: 1,
}, "class edits must retain the edited geometry");

useAutolabelingStore.setState({ proposals: [proposal], offset: 100, total: 200 });
useAutolabelingStore.getState().selectRun("run-b");
assert.deepEqual(useAutolabelingStore.getState().drafts, {}, "another run must not inherit edits");
assert.deepEqual(useAutolabelingStore.getState().proposals, []);
assert.equal(useAutolabelingStore.getState().offset, 0);

useAutolabelingStore.setState({ proposals: [proposal], runs: [{} as never], selectedId: proposal.id });
useAutolabelingStore.getState().reset("project-b-session");
assert.equal(useAutolabelingStore.getState().sessionId, "project-b-session");
assert.deepEqual(useAutolabelingStore.getState().runs, []);
assert.deepEqual(useAutolabelingStore.getState().proposals, []);
assert.equal(useAutolabelingStore.getState().runId, null);
assert.equal(useAutolabelingStore.getState().selectedId, null);

useAutolabelingStore.setState({ config: { adapter: "ultralytics", model_path: "/model-a.pt", confidence: 0.7, class_mapping: { person: "person" } },
  scope: "selected", indices: "1, 3" });
useAutolabelingStore.getState().selectRun("run-c");
assert.equal(useAutolabelingStore.getState().config.model_path, "/model-a.pt", "reviewing another run must preserve configuration");
assert.equal(useAutolabelingStore.getState().indices, "1, 3");
useAutolabelingStore.getState().reset("project-c-session");
assert.equal(useAutolabelingStore.getState().config.model_path, "", "configuration must not leak between projects");
assert.equal(useAutolabelingStore.getState().scope, "current");
