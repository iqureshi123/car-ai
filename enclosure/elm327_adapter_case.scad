// ===== ELM327 WiFi Enclosure (plugs directly into OBD port) =====
// ⚠️ MEASURE YOUR UNIT and overwrite these 5 numbers:
body_l = 48;     // body length (no connector)
body_w = 46;     // body width
body_h = 25;     // body height
conn_w = 38;     // OBD connector width
conn_h = 16;     // OBD connector height

part   = "base"; // "base" or "lid"
clear  = 1.0;    // gap around adapter
wall   = 2.5;    // wall thickness
corner = 4;      // corner radius
$fn    = 48;

iw = body_w + clear*2;
il = body_l + clear*2;
ih = body_h + clear;
ow = iw + wall*2;
ol = il + wall*2;

module rbox(l, w, h, r) {
    hull() for (x=[r, l-r], y=[r, w-r])
        translate([x, y, 0]) cylinder(r=r, h=h);
}

module base() {
    difference() {
        rbox(ol, ow, ih+wall, corner);
        translate([wall, wall, wall])
            rbox(il, iw, ih+wall, corner-wall);
        // FRONT fully open for OBD plug to stick out into car port
        translate([ol/2 - conn_w/2, -1, wall])
            cube([conn_w, wall+2, conn_h]);
        // side vents
        for (i=[0:3])
            translate([wall+6+i*8, -1, wall+ih*0.4])
                cube([3, ow+2, 8]);
    }
}

module lid() {
    difference() {
        rbox(ol, ow, wall, corner);
        // LED window (4 holes)
        for (i=[0:3])
            translate([ol/2-12+i*8, ow*0.30, -1])
                cylinder(d=4, h=wall+2);
    }
    // snap lip
    translate([wall+0.3, wall+0.3, -3])
        difference() {
            rbox(il-0.6, iw-0.6, 3, corner-wall);
            translate([wall, wall, -1])
                rbox(il-0.6-wall*2, iw-0.6-wall*2, 5, 1);
        }
}

if (part == "base") base(); else lid();
