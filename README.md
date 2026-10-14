# FreeCAD-SmartSnap

A small FreeCAD 1.1+ addon that makes Sketcher snapping feel closer to Blender:

**Draw a Sketcher shape → hold `Shift` → move onto an existing 3D edge/vertex → snap.**

The modifier is configurable (`Shift`, `Ctrl`, or `Alt`).

## What v0.1 does

SmartSnap does **not** copy an arbitrary XYZ coordinate into the sketch. Instead it uses FreeCAD's parametric workflow:

1. Detect the external **Vertex** or **Edge** under/near the mouse.
2. Project that sub-element into the active sketch as **reference external geometry**.
3. Let FreeCAD Sketcher's native `Snap to objects` handle the actual cursor snap.
4. If `Auto constraints` is enabled, FreeCAD can create the corresponding Sketcher constraint.

This means the snap stays linked to the source geometry instead of becoming a one-off visual placement.

### Modes

- **Vertex snap** — external vertices/corners.
- **Edge snap** — external edges and nearest point on the curve.
- **Midpoints** — after an edge is projected, FreeCAD 1.1's native object snapping can also lock to line/arc midpoints.
- **Hold-to-snap modifier** — `Shift` by default; change it in SmartSnap Settings.
- **Fallback pick radius** — searches a screen-space radius around the cursor if FreeCAD's preselection is not already on an edge/vertex.

## Installation for testing

This repository is still an early prototype and is not in the official Addon Manager index yet.

### Windows

1. Close FreeCAD.
2. Clone or download this repository into your user Mod folder, normally:

   ```text
   %APPDATA%\FreeCAD\Mod\FreeCAD-SmartSnap
   ```

3. The folder should directly contain `Init.py`, `InitGui.py`, and `package.xml`.
4. Start FreeCAD.

You should see **SmartSnap** in the Workbench selector.

## Usage

1. Create/open a sketch and enter Sketch edit mode.
2. Start a normal Sketcher geometry tool such as Rectangle or Line.
3. Move the cursor close to an existing solid's edge/corner.
4. Hold **Shift**.
5. SmartSnap projects the targeted edge/vertex as reference geometry.
6. Move the cursor a tiny amount if necessary; FreeCAD's native snap marker will lock onto the projected reference.
7. Click to place the point.

The projected reference stays in the sketch, so the relation remains parametric.

### Change the key

Switch to the **SmartSnap** workbench and choose **SmartSnap → SmartSnap Settings…**.

Available hold keys:

- Shift (default)
- Ctrl
- Alt

You can also enable/disable Vertex snap, Edge snap, Auto constraints and change the pick radius.

## Important FreeCAD 1.1 detail

FreeCAD 1.1 can create external projection geometry as defining geometry. SmartSnap explicitly requests **reference geometry** so the automatic reference should not become part of a Pad/Pocket profile.

SmartSnap also makes sure Sketcher's native:

- `Snap`
- `Snap to objects`

are enabled while it is being used.

## Current limitations (v0.1)

- This first version targets **FreeCAD 1.1+**.
- It currently targets external **Vertices** and **Edges**. Face-center, intersection, quadrant, extension and perpendicular snap modes are planned later.
- FreeCAD decides whether an external reference is legal. Cross-body references, circular dependencies, or unsupported source geometry can therefore be rejected.
- The addon relies on FreeCAD's existing Sketcher SnapManager for the final cursor snap. The first mouse event adds the parametric reference; on some systems a very small mouse movement may be needed before the native snap indicator refreshes.
- It has not yet been tested across all operating systems/navigation styles.

## Roadmap

- [x] Hold-to-snap modifier, default Shift
- [x] Configurable Shift/Ctrl/Alt
- [x] Vertex target detection
- [x] Edge target detection
- [x] Parametric external projection as reference geometry
- [x] Native Sketcher object snapping + optional auto constraints
- [ ] Dedicated on-cursor SmartSnap marker
- [ ] Intersection snap
- [ ] Edge extension snap
- [ ] Circle quadrant/center snap
- [ ] Perpendicular/tangent snap
- [ ] Better handling for links/sub-shape binders
- [ ] Automated FreeCAD integration tests
- [ ] Official FreeCAD Addon Manager submission

## Debugging

Enable **Verbose messages in Report view** in SmartSnap Settings.

If a target cannot be referenced, SmartSnap will leave the sketch unchanged and print an error beginning with:

```text
[SmartSnap]
```

Please include that message and your **Help → About FreeCAD → Copy to clipboard** version information when opening an issue.
