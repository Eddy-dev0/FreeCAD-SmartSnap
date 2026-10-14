# SPDX-License-Identifier: LGPL-2.1-or-later
"""Hold-to-snap engine for FreeCAD Sketcher.

SmartSnap deliberately builds on FreeCAD's native Sketcher SnapManager:

1. The user edits a Sketch and starts any normal Sketcher geometry tool.
2. While the configured modifier is held (Shift by default), SmartSnap watches
   the 3D view for an external Vertex/Edge near the cursor.
3. The target is added to the active Sketch as *reference* external geometry.
4. FreeCAD's native ``Snap to objects`` then snaps the Sketcher cursor to the
   projected point/curve. Auto-constraints can create the parametric relation.

The important design choice is that SmartSnap does not merely copy XYZ
coordinates. The projected reference remains linked to the source geometry.
"""

import time

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from . import config


class SmartSnapController:
    """Singleton controller bound to the currently active 3D view."""

    def __init__(self):
        self._timer = None
        self._view = None
        self._location_callback = None
        self._keyboard_callback = None
        self._button_callback = None
        self._buttons_down = set()
        self._last_process_at = 0.0
        self._last_candidate = None
        self._runtime_refs = {}

    def start(self):
        if self._timer is None:
            self._timer = QtCore.QTimer()
            self._timer.setInterval(350)
            self._timer.timeout.connect(self._heartbeat)
            self._timer.start()
        self._heartbeat()

    def stop(self):
        self._unbind_view()
        if self._timer is not None:
            self._timer.stop()
            self._timer = None

    def set_enabled(self, value):
        config.set_enabled(value)
        if value:
            self.start()
            self._ensure_native_snap()
            self._status(
                "SmartSnap enabled — hold %s while drawing." % config.modifier()
            )
        else:
            self._last_candidate = None
            self._status("SmartSnap disabled.")

    def _heartbeat(self):
        if not config.enabled():
            self._unbind_view()
            return

        try:
            gui_doc = Gui.activeDocument()
            view = gui_doc.activeView() if gui_doc else None
        except Exception:
            view = None

        if view is not self._view:
            self._bind_view(view)

    def _bind_view(self, view):
        self._unbind_view()
        if view is None:
            return

        try:
            self._view = view
            self._location_callback = view.addEventCallback(
                "SoLocation2Event", self._on_location_event
            )
            self._keyboard_callback = view.addEventCallback(
                "SoKeyboardEvent", self._on_keyboard_event
            )
            self._button_callback = view.addEventCallback(
                "SoMouseButtonEvent", self._on_button_event
            )
        except Exception as exc:
            self._view = None
            self._log("Unable to attach to active 3D view: %s" % exc, error=True)

    def _unbind_view(self):
        if self._view is not None:
            for event_name, callback_id in (
                ("SoLocation2Event", self._location_callback),
                ("SoKeyboardEvent", self._keyboard_callback),
                ("SoMouseButtonEvent", self._button_callback),
            ):
                if callback_id is not None:
                    try:
                        self._view.removeEventCallback(event_name, callback_id)
                    except Exception:
                        pass

        self._view = None
        self._location_callback = None
        self._keyboard_callback = None
        self._button_callback = None
        self._buttons_down.clear()

    def _on_button_event(self, info):
        button = info.get("Button")
        state = info.get("State")
        if not button:
            return
        if state == "DOWN":
            self._buttons_down.add(button)
        elif state == "UP":
            self._buttons_down.discard(button)

    def _on_keyboard_event(self, info):
        # On the modifier key-down event itself, preselection may already be on
        # a valid target. Process it immediately instead of waiting for a move.
        if info.get("State") != "DOWN" or self._buttons_down:
            return
        if self._modifier_down(info):
            self._process_snap(info)

    def _on_location_event(self, info):
        if self._buttons_down:
            return
        if not self._modifier_down(info):
            self._last_candidate = None
            return
        self._process_snap(info)

    @staticmethod
    def _modifier_flag(info, name):
        return bool(info.get(name + "Down"))

    def _modifier_down(self, info):
        selected = config.modifier()
        return self._modifier_flag(info, selected)

    def _process_snap(self, info):
        if not config.enabled() or self._view is None:
            return

        # Cap processing to ~30 Hz. Selection probing is cheap, but there is no
        # reason to run it at every raw mouse event.
        now = time.monotonic()
        if now - self._last_process_at < 0.033:
            return
        self._last_process_at = now

        sketch = self._active_sketch()
        if sketch is None:
            return

        self._ensure_native_snap()
        if config.auto_constraints():
            self._enable_auto_constraints()

        candidate = self._candidate_from_preselection(sketch)
        pos = info.get("Position")
        if candidate is None and pos:
            candidate = self._candidate_from_probe(sketch, pos)

        if candidate is None:
            self._last_candidate = None
            return

        source, subname = candidate
        key = (sketch.Document.Name, sketch.Name, source.Name, subname)
        if key == self._last_candidate:
            return
        self._last_candidate = key

        if self._already_external(sketch, source, subname):
            return

        self._add_external_reference(sketch, source, subname)

    @staticmethod
    def _active_sketch():
        try:
            gui_doc = Gui.activeDocument()
            if gui_doc is None:
                return None
            view_provider = gui_doc.getInEdit()
            if not view_provider:
                return None
            obj = getattr(view_provider, "Object", None)
            if obj is not None and obj.isDerivedFrom("Sketcher::SketchObject"):
                return obj
        except Exception:
            pass
        return None

    @staticmethod
    def _enable_auto_constraints():
        try:
            gui_doc = Gui.activeDocument()
            view_provider = gui_doc.getInEdit() if gui_doc else None
            if view_provider is not None and hasattr(view_provider, "Autoconstraints"):
                view_provider.Autoconstraints = True
        except Exception:
            pass

    def _candidate_from_preselection(self, sketch):
        try:
            presel = Gui.Selection.getPreselection()
            source = getattr(presel, "Object", None)
            subnames = getattr(presel, "SubElementNames", ())
            if source is None or source is sketch or not subnames:
                return None
            return self._validate_candidate(source, subnames[0])
        except Exception:
            return None

    def _candidate_from_probe(self, sketch, pos):
        """Fallback hit-test around the cursor using FreeCAD's native picker."""
        try:
            x, y = int(pos[0]), int(pos[1])
        except Exception:
            return None

        radius = config.search_radius()
        if radius <= 0:
            return None

        try:
            infos = self._view.getObjectsInfo((x, y), float(radius)) or []
        except Exception:
            # Some older builds expose getObjectsInfo without the radius arg.
            try:
                infos = self._view.getObjectsInfo((x, y)) or []
            except Exception:
                return None

        vertex_candidates = []
        edge_candidates = []
        for info in infos:
            obj_name = info.get("Object")
            subname = info.get("Component", "")
            if not obj_name or not subname:
                continue

            try:
                source = sketch.Document.getObject(obj_name)
            except Exception:
                source = None
            if source is None or source is sketch:
                continue

            valid = self._validate_candidate(source, subname)
            if valid is None:
                continue
            if subname.startswith("Vertex"):
                vertex_candidates.append(valid)
            elif subname.startswith("Edge"):
                edge_candidates.append(valid)

        # Blender-like behaviour: when both are close, a real vertex wins over
        # the edge passing through it.
        if vertex_candidates:
            return vertex_candidates[0]
        if edge_candidates:
            return edge_candidates[0]
        return None

    @staticmethod
    def _validate_candidate(source, subname):
        if not isinstance(subname, str):
            return None
        if subname.startswith("Vertex") and config.vertex_snap():
            return source, subname
        if subname.startswith("Edge") and config.edge_snap():
            return source, subname
        return None

    def _already_external(self, sketch, source, subname):
        runtime_key = (source.Name, subname)
        refs = self._runtime_refs.setdefault(
            (sketch.Document.Name, sketch.Name), set()
        )
        if runtime_key in refs:
            return True

        try:
            for entry in sketch.ExternalGeometry:
                if not isinstance(entry, (tuple, list)) or len(entry) < 2:
                    continue
                linked_obj, linked_subs = entry[0], entry[1]
                if linked_obj is not source:
                    continue
                if isinstance(linked_subs, str):
                    linked_subs = (linked_subs,)
                if subname in linked_subs:
                    refs.add(runtime_key)
                    return True
        except Exception:
            pass

        return False

    def _add_external_reference(self, sketch, source, subname):
        doc = sketch.Document
        transaction_open = False
        try:
            doc.openTransaction("SmartSnap: add external reference")
            transaction_open = True

            # defining=False is intentional. The imported geometry is only a
            # reference for snapping/constraints and must not become part of a
            # Pad/Pocket profile (which would cause open-wire/profile issues).
            result = sketch.addExternal(source.Name, subname, False, False)
            if isinstance(result, int) and result < 0:
                raise RuntimeError("FreeCAD rejected the external reference")

            doc.recompute()
            doc.commitTransaction()
            transaction_open = False

            self._runtime_refs.setdefault(
                (sketch.Document.Name, sketch.Name), set()
            ).add((source.Name, subname))

            kind = "vertex" if subname.startswith("Vertex") else "edge"
            self._status(
                "SmartSnap: %s %s ready — click when the native snap marker locks."
                % (kind, subname)
            )
            self._log(
                "Projected %s.%s into %s as reference geometry."
                % (source.Name, subname, sketch.Name)
            )
        except Exception as exc:
            if transaction_open:
                try:
                    doc.abortTransaction()
                except Exception:
                    pass
            self._log(
                "Could not project %s.%s: %s"
                % (getattr(source, "Name", "?"), subname, exc),
                error=True,
            )
            self._status("SmartSnap: target cannot be referenced from this sketch.")

    @staticmethod
    def _ensure_native_snap():
        try:
            snap = App.ParamGet(
                "User parameter:BaseApp/Preferences/Mod/Sketcher/Snap"
            )
            if not snap.GetBool("Snap", True):
                snap.SetBool("Snap", True)
            if not snap.GetBool("SnapToObjects", True):
                snap.SetBool("SnapToObjects", True)
        except Exception:
            pass

    @staticmethod
    def _status(message):
        try:
            Gui.getMainWindow().statusBar().showMessage(message, 2600)
        except Exception:
            pass

    @staticmethod
    def _log(message, error=False):
        if error:
            App.Console.PrintError("[SmartSnap] %s\n" % message)
        elif config.console_logging():
            App.Console.PrintMessage("[SmartSnap] %s\n" % message)


_CONTROLLER = None


def get_controller():
    global _CONTROLLER
    if _CONTROLLER is None:
        _CONTROLLER = SmartSnapController()
    return _CONTROLLER
