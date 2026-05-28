"""Flet design tokens — fonte única de verdade para cores, tipografia, espaçamento."""

from __future__ import annotations

COLORS: dict[str, str] = {
    # Fundos
    "bg":              "#F7F9FC",
    "surface":         "#FFFFFF",
    "surface_alt":     "#F0F4FB",
    "surface_hover":   "#EBF0F9",
    # Bordas
    "border":          "#E2EAF4",
    "border_strong":   "#C5D3E8",
    # Texto
    "text":            "#111827",
    "muted":           "#64748B",
    "disabled":        "#9CA3AF",
    "on_primary":      "#FFFFFF",
    "on_danger":       "#FFFFFF",
    "on_accent":       "#FFFFFF",
    "on_neutral":      "#1E293B",
    # Primária — azul moderno
    "primary":         "#2563EB",
    "primary_hover":   "#1D4ED8",
    "primary_muted":   "#EFF6FF",
    # Accent — âmbar
    "accent":          "#F59E0B",
    "accent_hover":    "#D97706",
    "accent_muted":    "#FFFBEB",
    # Danger — vermelho
    "danger":          "#EF4444",
    "danger_hover":    "#DC2626",
    "danger_muted":    "#FEF2F2",
    # Sucesso
    "success":         "#10B981",
    "success_muted":   "#ECFDF5",
    # Neutro — cinza-azulado suave
    "neutral":         "#E9EEF7",
    "neutral_hover":   "#D8E0EF",
    # Canvas
    "canvas_bg":       "#0F1117",
}

SIZES: dict[str, int] = {
    "sidebar_w":     300,
    "topbar_h":       52,
    "statusbar_h":    40,
    "btn_h":          38,
    "btn_h_sm":       30,
    "radius":          8,
    "radius_sm":       6,
    "radius_lg":      12,
    "input_h":        40,
    "icon":           18,
}

SPACING: dict[str, int] = {
    "xs":   4,
    "sm":   8,
    "md":  16,
    "lg":  24,
    "xl":  32,
    "2xl": 48,
}

FONT: dict[str, int] = {
    "title":   22,
    "heading": 16,
    "subhead": 14,
    "body":    13,
    "label":   13,
    "button":  13,
    "caption": 11,
    "mono":    12,
}
