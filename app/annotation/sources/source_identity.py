"""Identidade de cada fonte da sessao, usada para que fontes diferentes nunca compartilhem file_name.

Ex.: cam1/video.mp4 e cam2/video.mp4 geram ambos "video_frame_00001.jpg"; sem isso o
segundo sobrescreve o JPG do primeiro e as caixas do primeiro passam a apontar para
uma imagem de outra resolucao.
"""

from app.annotation.shared import *


class SourceIdentityMixin:
    def _source_identity(self, source: Path) -> Tuple[str, ...]:
        """Partes do caminho da fonte relativas ao data_root (ou so o nome)."""
        cache = self.__dict__.setdefault("_source_identity_cache", {})
        key = str(source)
        if key not in cache:
            try:
                parts = source.resolve().relative_to(self.data_root.resolve()).parts
            except (ValueError, OSError):
                parts = ()
            cache[key] = tuple(parts) or (source.name,)
        return cache[key]

    def _record_matches_source(self, record_video: str, source: Path) -> bool:
        identity = self._source_identity(source)
        parts = Path(record_video).parts
        return len(parts) >= len(identity) and tuple(parts[-len(identity):]) == identity

    def _is_foreign_record(self, record: dict) -> bool:
        """True quando o registro pertence comprovadamente a outra fonte da sessao.

        Registros sem fonte reconhecivel (dataset movido, formato antigo) contam como
        da fonte atual, preservando a retomada de sessoes existentes.
        """
        current = getattr(self, "video_path", None)
        record_video = str(record.get("video", "") or "")
        if current is None or not record_video:
            return False
        if self._record_matches_source(record_video, current):
            return False
        return any(
            self._record_matches_source(record_video, other)
            for other in getattr(self, "video_files", [])
            if Path(other) != Path(current)
        )

    def _qualified_output_file_name(self, base_name: str) -> str:
        """Nome prefixado pela fonte atual, usado quando o nome base colide com outra fonte."""
        if self.video_path is None:
            return base_name
        source_key = Path(*self._source_identity(self.video_path)).with_suffix("").as_posix()
        return f"{source_key}/{base_name}"

