"""State persistence helpers for the manual classification tool."""

from __future__ import annotations

from pathlib import Path

from backend.classification.dataset import ClassificationRecord, load_state, write_state


class ClassificationStateMixin:
    def _load_existing_state(self):
        state = load_state(self.state_path)
        if state is None:
            self._save_state()
            return
        if state.classes:
            self.classes = list(state.classes)
        if state.class_directories:
            self.class_directories = dict(state.class_directories)
            for dirname in self.class_directories.values():
                (self.output_dir / dirname).mkdir(parents=True, exist_ok=True)
        self.records = self._latest_records_by_source(state.records)

    def _save_state(self):
        write_state(
            self.state_path,
            classes=self.classes,
            class_directories=self.class_directories,
            source_root=self.data_root,
            records=self.records,
        )

    def _counts_by_class(self) -> dict[str, int]:
        counts = {class_name: 0 for class_name in self.classes}
        for record in self.records:
            counts[record.class_name] = counts.get(record.class_name, 0) + 1
        return counts

    def _classified_sources(self) -> set[Path]:
        return {record.source_path for record in self.records}

    @staticmethod
    def _latest_records_by_source(records) -> list[ClassificationRecord]:
        latest: dict[Path, ClassificationRecord] = {}
        order: list[Path] = []
        for record in records:
            source_path = Path(record.source_path).expanduser()
            if source_path not in latest:
                order.append(source_path)
            latest[source_path] = record
        return [latest[source_path] for source_path in order]

    def _record_for_source(self, source_path: Path) -> ClassificationRecord | None:
        for record in reversed(self.records):
            if record.source_path == source_path:
                return record
        return None

    def _remove_previous_classification(self, record: ClassificationRecord):
        self.records = [item for item in self.records if item != record]
        self.undo_stack = [item for item in self.undo_stack if item != record]
