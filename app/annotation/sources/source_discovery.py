from app.annotation.shared import *


class SourceDiscoveryMixin:
    @staticmethod
    def is_video_source(source: Path) -> bool:
        return source.is_file() and source.suffix.lower() in VIDEO_EXTENSIONS

    @staticmethod
    def is_image_source(source: Path) -> bool:
        return source.is_file() and source.suffix.lower() in IMAGE_EXTENSIONS

    @staticmethod
    def is_image_list_source(source: Path) -> bool:
        return source.is_file() and source.suffix.lower() in IMAGE_LIST_EXTENSIONS

    def discover_sources(self, data_root: Path) -> List[Path]:
        """Discovers sources: videos, image directory, single image, or image list."""
        if data_root.is_file():
            if self.is_video_source(data_root) or self.is_image_source(data_root) or self.is_image_list_source(data_root):
                return [data_root]
            return []

        video_paths = sorted(
            [p for p in data_root.rglob("*") if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS]
        )
        if video_paths:
            return video_paths

        image_paths = sorted(
            [p for p in data_root.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS]
        )
        if image_paths:
            # the entire directory becomes a single frame sequence
            return [data_root]

        image_list_paths = sorted(
            [p for p in data_root.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_LIST_EXTENSIONS]
        )
        return image_list_paths

    def load_image_list(self, list_file: Path) -> List[Path]:
        """Loads image paths from a .txt/.lst file."""
        image_paths: List[Path] = []
        try:
            lines = list_file.read_text(encoding="utf-8").splitlines()
        except Exception:  # pylint: disable=broad-except
            return image_paths
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            p = Path(line)
            if not p.is_absolute():
                p = (list_file.parent / p).resolve()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
                image_paths.append(p)
        return image_paths

    def build_image_sequence(self, source: Path) -> List[Path]:
        """Builds an image sequence for a given source."""
        if source.is_dir():
            return sorted([p for p in source.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS])
        if self.is_image_source(source):
            return [source]
        if self.is_image_list_source(source):
            return self.load_image_list(source)
        return []

    def read_next_image_frame(self) -> Optional[np.ndarray]:
        """Reads the next image from the current sequence."""
        while self.current_image_cursor < len(self.current_image_paths):
            image_path = self.current_image_paths[self.current_image_cursor]
            self.current_image_cursor += 1
            frame = cv2.imread(str(image_path))
            if frame is None:
                print(f"[AVISO] Falha ao ler imagem: {image_path}")
                continue
            self.current_source_image_path = image_path
            return frame
        self.current_source_image_path = None
        return None

    def remove_current_image_from_sequence(self, image_path: Path):
        """Removes an image from the current sequence and adjusts the cursor."""
        resolved = image_path.resolve()
        for idx, candidate in enumerate(list(self.current_image_paths)):
            try:
                same_file = candidate.resolve() == resolved
            except Exception:  # pylint: disable=broad-except
                same_file = candidate == image_path
            if not same_file:
                continue
            del self.current_image_paths[idx]
            if idx < self.current_image_cursor:
                self.current_image_cursor = max(0, self.current_image_cursor - 1)
            return

    # ===================== VIDEO CONTROL =====================
