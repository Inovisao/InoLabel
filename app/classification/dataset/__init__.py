"""Operações do dataset de classificação manual (pastas por classe + estado em JSON).

API pública do pacote; cada parte vive no módulo da sua responsabilidade.
"""
from app.classification.dataset.models import (
    STATE_FILE_NAME,
    ClassificationRecord,
    ClassificationState,
    ClassificationOutputState,
)
from app.classification.dataset.files import (
    unique_destination_path,
)
from app.classification.dataset.class_dirs import (
    sanitize_class_dir_name,
    class_directories_for,
    prepare_dataset,
    add_class_directory,
    class_directory_path,
    class_directory_has_files,
    remove_class_directory,
)
from app.classification.dataset.sources import (
    discover_images,
    source_looks_used,
)
from app.classification.dataset.state_files import (
    STATE_PATTERN,
    NEW_STATE_PATTERN,
    find_state_path,
    load_state,
    load_required_state,
    write_state,
    list_output_states,
    list_output_states_for_sources,
    latest_output_state_for_sources,
)
from app.classification.dataset.transfers import (
    classify_image_source,
    transfer_image_to_class,
    copy_image_to_class,
    reclassify_record,
    undo_record,
    export_classification_dataset,
)

__all__ = [
    "ClassificationOutputState",
    "ClassificationRecord",
    "ClassificationState",
    "NEW_STATE_PATTERN",
    "STATE_FILE_NAME",
    "STATE_PATTERN",
    "add_class_directory",
    "class_directories_for",
    "class_directory_has_files",
    "class_directory_path",
    "classify_image_source",
    "copy_image_to_class",
    "discover_images",
    "export_classification_dataset",
    "find_state_path",
    "latest_output_state_for_sources",
    "list_output_states",
    "list_output_states_for_sources",
    "load_required_state",
    "load_state",
    "prepare_dataset",
    "reclassify_record",
    "remove_class_directory",
    "sanitize_class_dir_name",
    "source_looks_used",
    "transfer_image_to_class",
    "undo_record",
    "unique_destination_path",
    "write_state",
]
