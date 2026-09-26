
## Issue 8: WSLg 3D rendering freezes during Nav2 activation

**Symptom:** Gazebo and RViz would freeze completely (unresponsive to mouse clicks, terminal logs stalled) right around the moment Nav2's lifecycle manager activated all navigation nodes (`Managed nodes are active`).

**Root cause — three layered problems:**

1. **Software rendering fallback.** `glxinfo | grep "OpenGL renderer"` showed `llvmpipe` — WSLg was rendering 3D graphics entirely on the CPU instead of using the GPU. Fixed by updating the NVIDIA driver via the NVIDIA App (driver 616.92) and running `wsl --update` + `wsl --shutdown` to refresh the WSL platform.

2. **Wrong GPU selected.** After the driver update, `glxinfo` showed `D3D12 (Intel(R) UHD Graphics)` — this is a hybrid-GPU (Optimus) laptop, and WSLg defaulted to the integrated Intel GPU instead of the dedicated NVIDIA GPU. Fixed with:
   Confirmed fixed when `glxinfo` showed `D3D12 (NVIDIA GeForce RTX 5050 Laptop GPU)`.

3. **Windows GPU scheduling bug.** Even after both fixes above, freezes recurred specifically during interactive RViz actions. `wsl dmesg` showed repeated kernel errors:
   This is a documented, actively-tracked Microsoft WSL bug affecting NVIDIA/AMD/Intel GPUs alike (see microsoft/WSL issue #11293 and related issues). Worked around by turning off **Hardware-accelerated GPU scheduling** in Windows Settings -> System -> Display -> Graphics -> Advanced graphics settings, then rebooting.

**Practical workaround going forward:** avoid RViz's interactive "Nav2 Goal" tool (fragile under WSLg); instead set the initial pose visually with "2D Pose Estimate," then send navigation goals from the command line:

## Issue 9: AMCL localization drift after guessed initial pose

**Symptom:** Nav2 goals repeatedly ended with `Goal finished with status: ABORTED` after many recovery attempts, even in open areas.

**Root cause:** The initial pose was set via a rough guess through `ros2 topic pub /initialpose` rather than a properly confirmed estimate. AMCL's belief about the robot's position drifted out of sync with its true position in Gazebo, causing the costmap to "see" phantom obstacles.

**Fix:** Always set the initial pose visually in RViz with **2D Pose Estimate**, clicking as close as possible to the robot's actual position and facing direction, then **wait 15-20 seconds** before sending any navigation goal to let AMCL's particle filter converge.

## Issue 10: Default turtlebot3_world has tightly packed obstacles

**Symptom:** Some goal coordinates (including the original "kitchen" waypoint at `(2.0, 1.0)`) caused the robot to get boxed in between pylons/walls and abort just centimeters from the target.

**Root cause:** The default turtlebot3_world Gazebo map has densely spaced pillar obstacles. Not every coordinate on the map is safely reachable within normal costmap inflation margins.

**Verified-safe coordinates for testing** (robot spawn near `x=-1.98, y=-0.5`):
- `x=-1.0, y=0.0` — open corridor, confirmed reachable
- `x=0.0, y=0.0` — open corridor, confirmed reachable

**Recommendation:** Update `config/waypoints.yaml` with coordinates confirmed clear from this list, or switch to a more open custom world for natural-language waypoint demos.

**Reference commands used to diagnose Issue 8:**
- Check GPU rendering: `glxinfo | grep "OpenGL renderer"`
- Force NVIDIA adapter: `export MESA_D3D12_DEFAULT_ADAPTER_NAME="NVIDIA"`
- Check for the scheduling bug: `wsl dmesg | grep dxgkio_query_adapter_info` (look for `Ioctl failed: -2`)

## Issue 11: Hardware-accelerated GPU scheduling setting reverts on its own

**Symptom:** After Issue 8 was fixed by disabling "Hardware-accelerated GPU scheduling" in Windows, the exact same freeze (RViz/Gazebo fully unresponsive, `dxgkio_query_adapter_info: Ioctl failed: -22`/`-2` repeating in `wsl dmesg`) came back a couple of days later on the very first launch of a fresh session — not after repeated relaunches like the original pattern.

**Root cause:** The Windows setting had silently reverted to On. This is a known behavior with this particular setting — a Windows Update or an NVIDIA driver update installing in the background can reset it without any notification.

**Fix:** Recheck Settings → System → Display → Graphics → Advanced graphics settings periodically, especially after any Windows Update. If "Hardware-accelerated GPU scheduling" is On again, turn it Off and reboot before starting a new session.

**Diagnostic command used:** since PowerShell doesn't have `grep`/`tail`, use:

## Issue 12: Nav2 behavior tree recovery-retry limit too low for a cluttered map

**Symptom:** Nav2 goals repeatedly ended `ABORTED` after ~16-22 recovery attempts, even when the robot's final position was within centimeters (once within 1.79e-07 m) of the exact goal.

**Root cause:** The default behavior tree (`navigate_to_pose_w_replanning_and_recovery.xml`) caps the top-level `NavigateRecovery` node at `number_of_retries="6"`. In a map with densely packed obstacles, the controller needs more replanning/recovery cycles than that to finish converging, so the task gets marked as failed just before it would have succeeded.

**Fix:** Copied the default behavior tree and params file into the project (`config/behavior_trees/navigate_to_pose_custom.xml`, `config/waffle_custom.yaml`), raised `number_of_retries` from 6 to 20, and pointed `launch/nl_nav2_bringup.launch.py`'s `params_file` at the custom copy instead of the system default. Also had to add the new `behavior_trees` folder to `setup.py`'s `data_files` list — colcon silently skips files it isn't told to install, which caused a confusing "Couldn't open input XML file" error from `bt_navigator` on the first attempt.

## Issue 13: tf lookups mixing simulation time and wall-clock time (investigating)

**Symptom:** Goal aborted in ~25 seconds with only 1 recovery attempt (much faster than Issue 12's pattern). Logs showed repeated `Received plan with zero length` and `Transform data too old when converting from map to odom`, with a wall-clock Unix timestamp being compared against a simulation-time value a few minutes in.

**Likely cause:** A node using real time instead of simulation time for transform lookups, causing every lookup to appear stale. Under investigation — see whether `use_sim_time` is consistently `true` across all nodes in `config/waffle_custom.yaml`.

## Issue 13 (resolved): tf time mismatch was a one-off, not a real bug

Investigated further and ruled out a clock-sync problem (`date` matched actual wall-clock time exactly). The fast "zero length plan" abort was likely a rare startup timing fluke on that particular run, not a reproducible issue — see Issue 14 for the actual root cause found afterward.

## Issue 14: DWB's Oscillation critic blocks the maneuvering needed in tight spaces

**Symptom:** Robot visibly unable to find an alternate route around obstacles — appears to get stuck rather than backing up/re-angling to try a different path, then eventually aborts.

**Root cause:** DWB's `Oscillation` critic (in the `critics` list for `FollowPath`) uses default thresholds (~5cm net movement / ~11° net turning) before it starts penalizing back-and-forth motion. In a densely packed map, backing up or re-angling is sometimes the only way to route around a pillar, and the default thresholds were too tight to allow it.

**Fix:** Added explicit, looser values to `config/waffle_custom.yaml` under the `FollowPath` plugin: `oscillation_reset_dist: 0.25`, `oscillation_reset_angle: 1.0`, `oscillation_reset_time: 5.0`. Not yet fully confirmed successful in a clean end-to-end test — next session should retest `front_door` with this change in place.

## SLAM mode added

Added `launch/nl_nav2_slam.launch.py`, which brings up Gazebo + `slam_toolbox` (online async mode) instead of the pre-built map + AMCL, letting the robot build its own occupancy grid map live by driving it around with `teleop_twist_keyboard`. Map can be saved with `nav2_map_server`'s `map_saver_cli`.

**Known issue (unresolved):** `slam_toolbox`'s default RViz config shows `Map` and `LaserScan` displays in an error state ("No tf data") even several minutes after launch. Not yet root-caused — next session should expand the status details in RViz's Displays panel to see the exact error text, and check whether `/map` and `/scan` topics are actually being selected/published correctly.
