from app.annotation.shared import *


class ClassConfigMixin:
    def register_category(self, class_name: str) -> int:
        """Garante que uma classe exista na tabela de categorias e retorna seu id."""
        clean_name = class_name.strip()
        if not clean_name:
            raise ValueError("Nome de classe vazio.")
        if clean_name in self.class_to_category_id:
            return self.class_to_category_id[clean_name]
        next_id = max((cat.get("id", 0) for cat in self.categories), default=0) + 1
        self.class_to_category_id[clean_name] = next_id
        self.categories.append({"id": next_id, "name": clean_name})
        return next_id

    def parse_classes_text(self, text: str) -> List[str]:
        """Converte texto CSV de classes em lista limpa sem duplicados."""
        items = [part.strip() for part in text.split(",")]
        parsed: List[str] = []
        seen = set()
        for item in items:
            if not item:
                continue
            if item in seen:
                continue
            seen.add(item)
            parsed.append(item)
        return parsed

    def apply_target_classes(self, classes: List[str]):
        """Atualiza classes alvo e tenta configurar prompt no modelo."""
        cleaned = [c.strip() for c in classes if c.strip()]
        self.target_classes = cleaned
        for cname in self.target_classes:
            self.register_category(cname)

        self.uses_text_prompt = False
        if hasattr(self.model, "set_classes") and self.target_classes:
            try:
                self.model.set_classes(self.target_classes)
                self.uses_text_prompt = True
                print(f"[INFO] Prompt de classes aplicado no modelo: {self.target_classes}")
            except Exception as exc:  # pylint: disable=broad-except
                print(f"[AVISO] Falha ao aplicar set_classes({self.target_classes}): {exc}")
        elif not hasattr(self.model, "set_classes"):
            print("[AVISO] Modelo nao suporta set_classes(); usando filtro por nome de classe.")

        if getattr(self, "target_classes_var", None) is not None:
            self.target_classes_var.set(", ".join(self.target_classes))
        if getattr(self, "manual_class_var", None) is not None:
            current_manual = self.manual_class_var.get().strip()
            if not current_manual:
                self.manual_class_var.set(self.target_classes[0] if self.target_classes else "")

    def apply_target_classes_from_ui(self):
        """Aplica classes configuradas na UI (csv)."""
        raw = self.target_classes_var.get() if self.target_classes_var is not None else ""
        parsed = self.parse_classes_text(raw)
        if not parsed:
            print("[AVISO] Informe ao menos uma classe (ex: car, bus, person).")
            return
        self.apply_target_classes(parsed)
        print(f"[INFO] Classes alvo atualizadas: {self.target_classes}")
        self.update_status()

