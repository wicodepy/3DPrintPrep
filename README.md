# 3DPrintPrep - Blender Add-on


A Blender add-on that cuts a 3D object can make cuts and keys. This is particularly useful for 3D printing preparation where you need to split a mesh.


## Features
- Takes selected object and returns a top and bottom with either a cut or key.
- Makes a copy so the original is unaffected.
- Automatically applies scale before cutting/keying.
- Can be undone with `Ctrl+Z`.
- Located in the 3D Viewport Sidebar (`N` panel) under 3DPrintPrep tab.


## Installation

1. Download the `__init__.py` file.
2. Open Blender and navigate to **Edit** > **Preferences** > **Add-ons** > **⌄** > **Install from Disk...**.
3. Locate and select your downloaded `__init__.py` file.
4. The extension will automatically install and enable itself.

## Blender Settings

- Scene settings will need to be adjusted so that 1 Blender unit = 1 mm.
- Unit System: Metric
- Unit Scale: 0.001
- Length: does not need to be adjusted as Blender's system automatically converts the units. Recommended units are cm or mm.

## Settings

| Section | Setting | Description |
| --- | --- | --- |
| Cutmaker | **Global Cut Height** | Global Z value to cut the object along |
| Keymaker | **Global Cut Height** | Global Z value to cut the object along |
| Keymaker | **Key Size(%)** | Key(cube) size as a percentage of the smaller cross-section width (X or Y). Ensures that key does not poke out |
| Keymaker | **Clearance** | Total clearance for hole. Default is 0.2 mm, which adds 0.1 mm to each side |

## Usage Guide

1. **Open Sidebar:** Press `N` to open the Sidebar menu on the right side of the 3D Viewport (if not already open).
2. **Select Tab:** Choose the **3D Print Prep** tab.
2. **Select Object:** In the 3D Viewport, select the mesh object you wish to process.
3. **Enter preferred settings:** Adjust as applicable for your needs.
4. **Run Tool:** Press the applicable "Make" button. The object will processed.
6. **Hide Original:** The original object will be present and overlapping. Press `H` to hide it and examine the two new halves.


## Technical Details

The script utilizes Blender's `bpy`, `mathutils`, and `bmesh`:

1. Duplicates the original and perform a bisect operation to analyze the cross section.
2. Finds the X and Y width of cut cross-section to determine the center.
3. Generates a cube for the key and scales it to the smaller X/Y width * size percentage.
4. Generates a cube for the hole and scales it by the key size + clearance.
5. Makes two copies of the original
6. Uses booleans to cut the top and bottom.
7. Uses booleans to join/cut the key and hole to top and bottom.


## Limitations

- Designed for functional 3D printing where an object exceeded the print height. 
- The cut axis is limited to the Z axis.
- Users may have difficulty with more organically shaped models/limbs or where more than one part of the mesh exceeds the print.
- Aim to cut along a section where only one solid body intersects the cut line.
- The key(protruding part) will always attach to the bottom piece. This is for ease of FDM printing.
