"""Filesystem source discovery independent from the annotation UI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from backend.config import IMAGE_EXTENSIONS, IMAGE_LIST_EXTENSIONS, VIDEO_EXTENSIONS


@dataclass(frozen=True)
class SourceSummary:
    sources: List[Path]
    video_count: int
    image_count: int
    image_list_count: int

    @property
    def total(self) -> int:
        return len(self.sources)

    @property
    def has_sources(self) -> bool:
        return bool(self.sources)


class SourceDiscoveryService:
    """Discover videos, image sequences, single images, and image lists."""

    def summarize(self, data_root: Path) -> SourceSummary:
        sources = self.discover(data_root)
        video_count = sum(1 for source in sources if self.is_video_source(source))
        image_count = self._count_images(data_root, sources)
        image_list_count = sum(1 for source in sources if self.is_image_list_source(source))
        return SourceSummary(sources, video_count, image_count, image_list_count)

    def discover(self, data_root: Path) -> List[Path]:
        data_root = Path(data_root)
        if data_root.is_file():
            if self.is_supported_file(data_root):
                return [data_root]
            return []

        video_paths = sorted(p for p in data_root.rglob("*") if self.is_video_source(p))
        if video_paths:
            return video_paths

        image_paths = sorted(p for p in data_root.rglob("*") if self.is_image_source(p))
        if image_paths:
            return [data_root]

        return sorted(p for p in data_root.rglob("*") if self.is_image_list_source(p))

    @staticmethod
    def is_supported_file(source: Path) -> bool:
        return (
            SourceDiscoveryService.is_video_source(source)
            or SourceDiscoveryService.is_image_source(source)
            or SourceDiscoveryService.is_image_list_source(source)
        )

    @staticmethod
    def is_video_source(source: Path) -> bool:
        return source.is_file() and source.suffix.lower() in VIDEO_EXTENSIONS

    @staticmethod
    def is_image_source(source: Path) -> bool:
        return source.is_file() and source.suffix.lower() in IMAGE_EXTENSIONS

    @staticmethod
    def is_image_list_source(source: Path) -> bool:
        return source.is_file() and source.suffix.lower() in IMAGE_LIST_EXTENSIONS

    def _count_images(self, data_root: Path, sources: List[Path]) -> int:
        data_root = Path(data_root)
        if data_root.is_file():
            return 1 if self.is_image_source(data_root) else 0
        if sources == [data_root]:
            return sum(1 for p in data_root.rglob("*") if self.is_image_source(p))
        return sum(1 for p in sources if self.is_image_source(p))

