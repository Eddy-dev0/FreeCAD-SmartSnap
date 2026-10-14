# SPDX-License-Identifier: LGPL-2.1-or-later
"""Persistent SmartSnap settings stored in FreeCAD's parameter system."""

import FreeCAD as App

PARAM_PATH = "User parameter:BaseApp/Preferences/Mod/SmartSnap"
MODIFIERS = ("Shift", "Ctrl", "Alt")


def params():
    return App.ParamGet(PARAM_PATH)


def enabled():
    return params().GetBool("Enabled", True)


def set_enabled(value):
    params().SetBool("Enabled", bool(value))


def modifier():
    value = params().GetString("Modifier", "Shift")
    return value if value in MODIFIERS else "Shift"


def set_modifier(value):
    if value not in MODIFIERS:
        raise ValueError("Unsupported modifier: %s" % value)
    params().SetString("Modifier", value)


def vertex_snap():
    return params().GetBool("VertexSnap", True)


def set_vertex_snap(value):
    params().SetBool("VertexSnap", bool(value))


def edge_snap():
    return params().GetBool("EdgeSnap", True)


def set_edge_snap(value):
    params().SetBool("EdgeSnap", bool(value))


def search_radius():
    return max(0, min(30, params().GetInt("SearchRadiusPx", 8)))


def set_search_radius(value):
    params().SetInt("SearchRadiusPx", max(0, min(30, int(value))))


def auto_constraints():
    return params().GetBool("AutoConstraints", True)


def set_auto_constraints(value):
    params().SetBool("AutoConstraints", bool(value))


def console_logging():
    return params().GetBool("ConsoleLogging", False)


def set_console_logging(value):
    params().SetBool("ConsoleLogging", bool(value))
