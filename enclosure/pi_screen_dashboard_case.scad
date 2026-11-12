// ===== Pi 5 + Waveshare 7" DSI LCD (w/ Camera) — Dashboard Enclosure =====
// Footprint/screen/camera = OFFICIAL Waveshare datasheet values.
// Only depth + Pi-back-position are estimates (✱) — confirm those two.

/* ---- Display board (CONFIRMED) ---- */
board_w = 192.96;
board_h = 110.76;

/* ---- Active screen window (CONFIRMED) ---- */
view_w  = 154.88;
view_h  = 86.72;
view_x  = 19.04;   // left border
view_y  = 11.00;   // top border

/* ---- Front camera hole (CONFIRMED, short edge, centered) ---- */
cam_x   = 183.0;
cam_y   = 55.4;
cam_d   = 8;

/* ---- Pi position on back (✱ from your photos — confirm) ---- */
pi_x    = 54;      // (board_w-85)/2  ≈ centered
pi_y    = 27;      // (board_h-56)/2  ≈ centered
fan_x   = pi_x + 28;
fan_y   = pi_y + 28;

/* ---- Depth & shell ---- */
stack_depth = 50;  // ✱ glass -> back of fan (display 20 + Pi 16 + cooler 12)
clear  = 1.5;
wall   = 3;
corner = 6;
$fn    = 64;

iw = board_w + clear*2;  ih = board_h + clear*2;
ow = iw + wall*2;        oh = ih + wall*2;   // outer ≈ 201.96 × 119.76

part = "back";  // "back" | "bezel" | "stand"

module rbox(l,w,h,r){ hull() for(x=[r,l-r],y=[r,w-r]) translate([x,y,0]) cylinder(r=r,h=h); }

module back(){
  difference(){
    rbox(ow, oh, stack_depth+wall, corner);
    translate([wall,wall,wall]) rbox(iw, ih, stack_depth+1, corner-wall);
    // fan vent grid over the cooler
    for(ix=[-2:2], iy=[-2:2])
      translate([wall+clear+fan_x+ix*9, wall+clear+fan_y+iy*9, -1])
        cylinder(d=6, h=wall+2);
    // ✱ PORT WINDOWS — adjust edge/size to your routing
    translate([wall+clear+pi_x, -1, wall+2]) cube([56, wall+2, 18]); // USB/Eth long edge
    translate([-1, wall+clear+pi_y, wall+2]) cube([wall+2, 40, 16]); // power/HDMI short edge
  }
}

module bezel(){
  difference(){
    rbox(ow, oh, wall, corner);
    translate([wall+clear+view_x, wall+clear+view_y, -1])
      cube([view_w, view_h, wall+2]);                       // screen window
    translate([wall+clear+cam_x, wall+clear+cam_y, -1])
      cylinder(d=cam_d, h=wall+2);                          // camera hole
  }
  translate([wall+0.4, wall+0.4, wall-0.01])
    difference(){
      rbox(iw-0.8, ih-0.8, 4, corner-wall);
      translate([wall,wall,-1]) rbox(iw-0.8-wall*2, ih-0.8-wall*2, 6, 1);
    }
}

tilt = 18; stand_d = 90;
module stand(){ linear_extrude(ow) polygon([[0,0],[stand_d,0],[0,stand_d*tan(tilt)]]); }

if(part=="back") back();
else if(part=="bezel") bezel();
else stand();
