# SPDX-License-Identifier: LGPL-2.1-or-later
"""FreeCAD commands and settings dialog for SmartSnap."""

import FreeCADGui as Gui
from PySide import QtWidgets

from . import config
from .engine import get_controller


class _SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SmartSnap Settings")
        self.setModal(True)
        self.setMinimumWidth(390)

        layout = QtWidgets.QVBoxLayout(self)

        intro = QtWidgets.QLabel(
            "Hold the modifier while drawing in Sketcher. SmartSnap projects "
            "the external edge/vertex under the cursor as reference geometry, "
            "then FreeCAD's native Sketcher snapping takes over."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QtWidgets.QFormLayout()
        self.modifier = QtWidgets.QComboBox()
        self.modifier.addItems(config.MODIFIERS)
        self.modifier.setCurrentText(config.modifier())
        form.addRow("Hold-to-snap key:", self.modifier)

        self.radius = QtWidgets.QSpinBox()
        self.radius.setRange(0, 30)
        self.radius.setSuffix(" px")
        self.radius.setValue(config.search_radius())
        self.radius.setToolTip(
            "Fallback screen-space pick radius around the cursor. "
            "0 disables the fallback picker."
        )
        form.addRow("Pick radius:", self.radius)
        layout.addLayout(form)

        self.vertex = QtWidgets.QCheckBox("Vertex snapping")
        self.vertex.setChecked(config.vertex_snap())
        layout.addWidget(self.vertex)

        self.edge = QtWidgets.QCheckBox(
            "Edge snapping (also enables FreeCAD's native midpoint snap)"
        )
        self.edge.setChecked(config.edge_snap())
        layout.addWidget(self.edge)

        self.autoconstraints = QtWidgets.QCheckBox(
            "Enable Sketcher Auto constraints while SmartSnap is used"
        )
        self.autoconstraints.setChecked(config.auto_constraints())
        layout.addWidget(self.autoconstraints)

        self.logging = QtWidgets.QCheckBox("Verbose messages in Report view")
        self.logging.setChecked(config.console_logging())
        layout.addWidget(self.logging)

        note = QtWidgets.QLabel(
            "Default: Shift. You can switch the hold key to Ctrl or Alt here at any time."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        try:
            standard = QtWidgets.QDialogButtonBox.StandardButton
            button_flags = standard.Ok | standard.Cancel
        except AttributeError:  # PySide2 compatibility
            button_flags = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        buttons = QtWidgets.QDialogButtonBox(button_flags)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        config.set_modifier(self.modifier.currentText())
        config.set_search_radius(self.radius.value())
        config.set_vertex_snap(self.vertex.isChecked())
        config.set_edge_snap(self.edge.isChecked())
        config.set_auto_constraints(self.autoconstraints.isChecked())
        config.set_console_logging(self.logging.isChecked())
        get_controller().start()
        super().accept()


class ToggleCommand:
    def GetResources(self):
        state = "Disable" if config.enabled() else "Enable"
        return {
            "MenuText": "%s SmartSnap" % state,
            "ToolTip": (
                "Toggle SmartSnap. While enabled, hold %s in an active Sketch "
                "to snap to external vertices/edges." % config.modifier()
            ),
        }

    def Activated(self):
        get_controller().set_enabled(not config.enabled())

    def IsActive(self):
        return True


class SettingsCommand:
    def GetResources(self):
        return {
            "MenuText": "SmartSnap Settings…",
            "ToolTip": "Choose the hold-to-snap modifier and snapping modes.",
        }

    def Activated(self):
        dialog = _SettingsDialog(Gui.getMainWindow())
        dialog.exec()

    def IsActive(self):
        return True


Gui.addCommand("SmartSnap_Toggle", ToggleCommand())
Gui.addCommand("SmartSnap_Settings", SettingsCommand())
