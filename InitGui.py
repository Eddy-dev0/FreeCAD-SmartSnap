# SPDX-License-Identifier: LGPL-2.1-or-later
"""FreeCAD SmartSnap GUI initializer."""

import FreeCAD as App
import FreeCADGui as Gui


_SMARTSNAP_ICON = """
/* XPM */
static const char *smartsnap_xpm[] = {
"16 16 4 1",
"  c None",
". c #3DAEE9",
"+ c #232629",
"@ c #E95420",
"                ",
"   ....  ....   ",
"  .++++..++++.  ",
" .++        ++. ",
" .+   ....   +. ",
" .+  .++++.  +. ",
" .+  .+  +.  +. ",
" .+  .+@@+.  +. ",
" .+  .+@@+.  +. ",
" .+  .++++.  +. ",
" .+   ....   +. ",
" .++        ++. ",
"  .++++++++++.  ",
"   ..........   ",
"                ",
"                "
};
"""


class SmartSnapWorkbench(Gui.Workbench):
    """Small utility workbench used to configure SmartSnap."""

    MenuText = "SmartSnap"
    ToolTip = "Blender-like hold-to-snap helper for FreeCAD Sketcher"
    Icon = _SMARTSNAP_ICON

    def Initialize(self):
        from SmartSnap import commands  # noqa: F401

        commands_list = ["SmartSnap_Toggle", "SmartSnap_Settings"]
        self.appendToolbar("SmartSnap", commands_list)
        self.appendMenu("SmartSnap", commands_list)

    def Activated(self):
        return

    def Deactivated(self):
        return

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(SmartSnapWorkbench())

# SmartSnap is useful while the user is in Sketcher/Part Design, not only while
# the SmartSnap workbench itself is active. Start the lightweight controller at
# GUI startup. It only attaches mouse callbacks to the current 3D view.
try:
    from SmartSnap.engine import get_controller

    get_controller().start()
except Exception as exc:  # Never prevent FreeCAD from starting because of an addon.
    App.Console.PrintError("[SmartSnap] Failed to start: %s\n" % exc)
