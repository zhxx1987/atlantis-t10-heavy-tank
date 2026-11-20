# T-10 simplified driving

Use Operate Vehicle on the T-10 Gallery work page, then Start driving. Driving stays in the same work page. Inspect Model returns to inspection. W/S drive, A/D steer, Space brakes, mouse looks and aims, left click plays the firing effect, H opens hatches, and Esc releases input. The camera stays in third person.

The browser runs editable Python in Pyodide. This is a reduced vehicle model, with 14 unilateral spring contacts, gravity, body heave/pitch/roll, reduced traction when contact is lost, and a visible ground profile. Road wheels, swing arms and the lower track path follow suspension travel. Braking is stronger than coasting; opposite throttle brakes to a complete stop before reversing. Hard braking gives a small nose dip and damped recovery. An airborne vehicle retains horizontal momentum and falls before regaining traction. This implementation does not run Isaac Sim or native PhysX in the browser.

Simulation uses a persistent 120 Hz accumulator and limits long inactive-tab frames. Driver defaults contain editable acceleration, braking, coast, spring/damping, travel and gauge parameters. terrain.json supplies the common contact/visible-course height profile. These values are tuned for this demonstration rather than measured T-10 dynamics.

## Downloaded local browser version

Extract the full model download. Install Python and Atlantis, set ATLANTIS_WORKSPACE to the installed Atlantis workspace containing rendering/tools/serve_scene_viewer.py, then run Start-Game.cmd or python game_server.py. Use the URL printed by the server in a WebGPU browser.

The separate simplified-code archive can update an extracted full model package; it includes GameCourse.glb but requires the model, rig, audio and bundled Pyodide runtime from the full download. Extract it alongside those files. The new game uses game_drive_core.py. Isaac continues using the separate drive_core.py, isaac_drive.py, original Course.glb and Drive.usda.

Run python check_game_drive.py for the portable regression, or await window.t10RunCheck() in the running browser for the identical checks in Pyodide. Checks cover braking/hold, coast distance, stop-before-reverse, nose dip/settle, airborne/landing, uneven ground/roll, flat stability, 30/60/144 FPS, snapshot restoration and native-mode isolation.
