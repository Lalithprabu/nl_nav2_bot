
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
