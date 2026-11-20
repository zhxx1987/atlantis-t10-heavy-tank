# T-10 simplified driving

Use Operate Vehicle on the T-10 Gallery work page, then Start driving. Driving stays in the same work page. Inspect Model returns to inspection. W/S drive, A/D steer, Space brakes, mouse looks and aims, left click plays the firing effect, H opens hatches, and Esc releases input. The camera stays in third person.

The browser runs editable Python in Pyodide. This is a reduced vehicle model, with 14 unilateral spring contacts, gravity, body heave/pitch/roll, reduced traction when contact is lost, and a visible ground profile. Road wheels, swing arms and the lower track path follow suspension travel. Braking is stronger than coasting; opposite throttle brakes to a complete stop before reversing. Hard braking gives a small nose dip and damped recovery. An airborne vehicle retains horizontal momentum and falls before regaining traction. This implementation does not run Isaac Sim or native PhysX in the browser.

Simulation uses a persistent 120 Hz accumulator and limits long inactive-tab frames. Driver defaults contain editable acceleration, braking, coast, spring/damping, travel and gauge parameters. terrain.json supplies the common contact/visible-course height profile. These values are tuned for this demonstration rather than measured T-10 dynamics.

## Downloaded local browser version

There are three downloads: MODEL assets, combined CONTROLS (simplified game +
native real physics), and editable MODELING SOURCE. Extract MODEL and CONTROLS
into the SAME new directory with relative paths preserved. Close old sessions
before replacing files. A new controls package replaces the previous controller
files; do not add an older independent simplified-motion archive. Extract the
source package into a separate directory only when rebuilding geometry.

Install Python and Atlantis. Set ATLANTIS_WORKSPACE to the installed Atlantis
workspace containing rendering/tools/serve_scene_viewer.py, then run
Start-Game.cmd or python game_server.py. Use the printed URL in a WebGPU browser.
The CONTROLS archive includes the Pyodide runtime and game_drive_core.py.
The MODEL archive supplies GameCourse.glb, the tank, textures, rig and audio.
Isaac uses the independent drive_core.py and isaac_drive.py with Drive.usda and
the original Course.glb. See ASSEMBLE_ISAAC.md and ASSEMBLE_GAME_ENGINE.md.

Run python check_game_drive.py for the portable regression, or await window.t10RunCheck() in the running browser for the identical checks in Pyodide. Checks cover braking/hold, coast distance, stop-before-reverse, nose dip/settle, airborne/landing, uneven ground/roll, flat stability, 30/60/144 FPS, snapshot restoration and native-mode isolation.
