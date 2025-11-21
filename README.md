
 ![AAASAAA](/img/Ship.png)
 ![AAASAAA](/img/Hull.png)
 ![AAASAAA](/img/UI.png)






==================================================================
             FROM THE DEPTHS - AUTOMATIC HULL DESIGNER
==================================================================

Version: 1.0
Created for: From The Depths (FTD)

WHAT IS THIS?
-------------
This is a standalone tool that allows you to draw the 2D shape of a ship's deck
and automatically generates a 3D tapered hull blueprint.

It handles block smoothing (using 4m, 3m, 2m, 1m slopes), generates
undercuts/tumblehomes (raked hulls), and seals gaps automatically.(mostly)

===================
   HOW TO RUN
===================
1. EXTRACT THE ZIP FILE!
   Do not try to run the tool from inside the zip folder. 
   It needs to read and write files, which won't work inside a zip.

2. Open the extracted folder.

3. Double-click "Start Generator.bat".
   (This launches the included portable engine. You do NOT need to install Python).

===================
   HOW TO USE
===================
1. DRAWING:

   - !! Ensure the taper at the front is not blunter than 45°, the solver will have issues !!

   - Left Click: Add a point to the hull outline.
   - Right Click: Remove the last point.
   - Draw from the BOW (Top) to the STERN (Bottom).
   - The grid auto-scales based on the length you set in "Design Limits".

2. SETTINGS:
   - Deck Height: How tall the vertical wall of the hull is.
   - Undercut Layers: How many layers deep the hull tapers inwards (tumblehome).
   - Generate Floor: Automatically fills the flat bottom of the hull.

3. EXPORTING:
   - Click the "EXPORT" button.
   - A file named "generated_hull.blueprint" will appear in this folder.

4. IMPORTING INTO GAME:
   - Move "generated_hull.blueprint" to your FTD Constructs folder:
     (Documents\From The Depths\Player Profiles\[YourProfile]\Constructs)
   - In-game, load the construct or use the Prefab tool to place it.

===================
 IMPORTANT FILES
===================
Do NOT delete or rename these files, or the tool will break:

- bin/             -> Contains the internal engine (Python).
- ItemDup/         -> Contains the block definitions (Slopes, Beams, Offsets).
- donor.blueprint  -> A blank template used for generation.
- Generator.py     -> The logic script.

===================
  CUSTOM BLOCKS
===================
The tool comes pre-configured for ALLOY. If you want to use Metal or Wood: -WIP(does not work yet)

1. Go into the "ItemDup" folder.
2. Replace the files with .itemdup files of the material you want.
3. CRITICAL: You must keep the naming convention in the filenames!
   - The tool looks for: "4m", "3m", "Slope", "Beam", "Offset".
   - For Offsets, the filename MUST contain "Left" or "Right".
