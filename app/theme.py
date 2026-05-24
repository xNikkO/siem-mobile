from __future__ import annotations

from kivy.metrics import dp, sp


COLORS = {

    "bg":            (0.039, 0.055, 0.102, 1),
    "bg_alt":        (0.055, 0.071, 0.122, 1),
    "panel":         (0.078, 0.094, 0.149, 1),
    "panel_alt":     (0.102, 0.122, 0.184, 1),
    "panel_hover":   (0.125, 0.149, 0.220, 1),
    "border":        (0.145, 0.169, 0.239, 1),
    "border_strong": (0.220, 0.255, 0.341, 1),


    "text":          (0.929, 0.937, 0.949, 1),
    "text_dim":      (0.612, 0.639, 0.686, 1),
    "text_muted":    (0.420, 0.447, 0.502, 1),


    "accent":        (0.251, 0.502, 1.000, 1),
    "accent_hover":  (0.376, 0.627, 1.000, 1),
    "accent_press":  (0.180, 0.400, 0.870, 1),
    "accent_soft":   (0.251, 0.502, 1.000, 0.16),


    "ok":            (0.133, 0.773, 0.369, 1),
    "ok_soft":       (0.133, 0.773, 0.369, 0.16),
    "warn":          (0.961, 0.620, 0.043, 1),
    "warn_soft":     (0.961, 0.620, 0.043, 0.18),
    "crit":          (0.937, 0.267, 0.267, 1),
    "crit_soft":     (0.937, 0.267, 0.267, 0.18),
    "info":          (0.231, 0.510, 0.965, 1),
    "info_soft":     (0.231, 0.510, 0.965, 0.16),
    "pink":          (0.957, 0.247, 0.369, 1),
    "purple":        (0.659, 0.333, 0.969, 1),


    "shadow":        (0, 0, 0, 0.45),
    "transparent":   (0, 0, 0, 0),
}


RADIUS = dp(12)
RADIUS_SM = dp(8)
RADIUS_PILL = dp(999)

SPACE_XS = dp(4)
SPACE_SM = dp(8)
SPACE_MD = dp(12)
SPACE_LG = dp(16)
SPACE_XL = dp(24)


FONT_REGULAR = "Roboto"
FONT_MONO = "RobotoMono-Regular"

FS_XS = sp(10)
FS_SM = sp(11)
FS_MD = sp(13)
FS_LG = sp(15)
FS_XL = sp(18)
FS_XXL = sp(28)
FS_DISPLAY = sp(42)


def severity_color(severity):

    severity = (severity or "").upper()
    if severity == "CRITICAL":
        return COLORS["crit"]
    if severity == "WARNING":
        return COLORS["warn"]
    return COLORS["info"]


def severity_soft(severity):

    severity = (severity or "").upper()
    if severity == "CRITICAL":
        return COLORS["crit_soft"]
    if severity == "WARNING":
        return COLORS["warn_soft"]
    return COLORS["info_soft"]
