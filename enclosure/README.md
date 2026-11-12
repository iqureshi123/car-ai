# Enclosure

3D-printable enclosures for the OBD-II AI Car Assistant, designed in OpenSCAD by Zidan Zuberi.

There are two designs. Both are parametric: change the numbers at the top of the `.scad` file, set `part`, then render (F6) and export STL (F7). Made with OpenSCAD 2021.01.

## Dashboard enclosure: Raspberry Pi 5 + Waveshare 7" DSI LCD (with camera)

File: [`pi_screen_dashboard_case.scad`](pi_screen_dashboard_case.scad)

Set `part` to one of:

| `part`  | What it is |
|---------|------------|
| `back`  | Rear shell with a 5x5 vent grid over the Pi cooler and port windows on two edges |
| `bezel` | Front frame with the screen window, a camera hole, and an inner lip that locates it in the shell |
| `stand` | Wedge stand, 18 degree tilt, 90 mm deep |

Outer size is about 201.96 x 119.76 mm. The display footprint, screen window and camera hole come from the Waveshare datasheet. The stack depth (50 mm), the Pi's position on the back, and the port windows are estimates, marked with a star in the file. They should be checked against the real hardware before a final print.

## ELM327 WiFi adapter enclosure

File: [`elm327_adapter_case.scad`](elm327_adapter_case.scad)

A two-part case (`part = "base"` or `"lid"`) for an ELM327 WiFi adapter that plugs straight into the car's OBD-II port. The front is open so the connector can reach the port. The base has side vents. The lid has four LED windows and a snap lip.

The five measurements at the top of the file (`body_l`, `body_w`, `body_h`, `conn_w`, `conn_h`) are starting values. Measure your own adapter and replace them before printing.

## Print files

`stl/` holds the exported STL files that were shared with the team for the dashboard enclosure:

| File | Size (mm) | Notes |
|------|-----------|-------|
| `armor_back.stl` | 217.0 x 134.8 x 43.5 | Rear shell with a rectangular opening for the lid and corner mounting tabs |
| `armor_face.stl` | 217.0 x 134.8 x 16.2 | Front frame with the screen window and a camera hole |
| `armor_lid.stl` | 98.6 x 70.6 x 3.5 | Access lid with a grid of round vent holes |

These STLs were not exported from the `.scad` files in this folder. They are larger (217.0 x 134.8 mm, against about 201.96 x 119.76 mm outer for `pi_screen_dashboard_case.scad`) and the lid is a separate part. Use the STLs as the print files, and treat the `.scad` files as the base parametric designs.
