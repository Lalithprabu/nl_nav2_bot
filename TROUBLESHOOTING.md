# Troubleshooting Log — Getting nl_nav2_bot Running on a Real Machine

This document is a running log of the issues we hit while taking this project from
"code on GitHub" to "actually running in Gazebo/RViz on a Windows laptop via
WSL2 + Ubuntu 22.04 + ROS2 Humble", and how each one was diagnosed and fixed.
It's kept here so future contributors (including future us) don't have to
re-discover the same things.

## Environment

- Windows 11 laptop, WSL2 with Ubuntu 22.04
- ROS2 Humble (desktop-full)
- Gazebo 11 (classic), RViz2
- Nav2 (navigation2) + turtlebot3_navigation2 + turtlebot3_gazebo
- TurtleBot3 model: `waffle`

## 1. GitHub authentication for pushing from the sandbox

**Symptom:** `gh auth login` device-flow OAuth kept failing because
background/detached processes don't survive across separate tool calls in the
automation sandbox used to build this repo.

**Fix:** Used a GitHub Personal Access Token (classic, `repo` scope) instead,
wired up via `GH_TOKEN` and a `~/.git-credentials` entry
(`https://x-access-token:${GH_TOKEN}@github.com`). Later needed to add the
`workflow` scope to the same token to allow pushing changes to
`.github/workflows/ci.yml`.

## 2. `rclpy_action` invalid rosdep key

**Symptom:** `rosdep install` failed because `package.xml` declared
`<depend>rclpy_action</depend>`, which isn't a real rosdep key (the action
client API lives inside `rclpy` itself in Humble).

**Fix:** Removed the line. Commit `42b6f84`.

## 3. Nav2 launch: empty `params_file` crash

**Symptom:**
```
FileNotFoundError: [Errno 2] No such file or directory: ''
```
raised from `nav2_common/launch/rewritten_yaml.py` when including
`turtlebot3_navigation2`'s `navigation2.launch.py`.

**Diagnosis:** Relying on that launch file's own defaults for `params_file`
and `map` doesn't work when it's included from a different launch file the
way we were including it — the substitution ends up empty.

**Fix:** Pass `params_file` and `map` explicitly in
`launch/nl_nav2_bringup.launch.py`, pointed at
`turtlebot3_navigation2`'s own `param/<model>.yaml` and `map/map.yaml`.
Commit `8374c49`.

## 4. "Nav2 action server not available" (5s timeout too short)

**Symptom:** `nl_command_node` would give up waiting for the
`navigate_to_pose` action server before Nav2 had finished bringing up its
full stack.

**Fix:** Increased `wait_for_server(timeout_sec=...)` from 5.0 to 30.0 in
`nl_command_node.py`. Commit `cf2b5a0`. (This alone wasn't the full story —
see issue 5 below, which was the real root cause of navigation never
becoming available in the first place.)

## 5. Nav2 pluginlib class-name mismatches (the big one)

**Symptom:** After the above fixes, Nav2's navigation lifecycle manager
would still fail to bring the stack up, with errors like:

```
[planner_server]: Failed to create global planner. Exception: According to
the loaded plugin descriptions the class nav2_navfn_planner::NavfnPlanner
with base class type nav2_core::GlobalPlanner does not exist. Declared types
are nav2_navfn_planner/NavfnPlanner ...
```

and (after a naive blanket fix) similar errors for `nav2_controller`'s
progress/goal checkers and `dwb_core::DWBLocalPlanner`, and later for
`nav2_behaviors` (spin/backup/wait/etc).

**Diagnosis:** The `turtlebot3_navigation2` apt package (Humble) ships a
default `param/<model>.yaml` whose plugin names use a mix of two different
pluginlib naming conventions (`package::ClassName` vs `package/ClassName`).
Depending on which specific plugin package is involved, *only one* of the
two forms actually matches what's registered on a stock Humble install:

| Plugin family                          | Naming that matches Humble |
|-----------------------------------------|-----------------------------|
| `nav2_navfn_planner`                    | `package/ClassName` (slash) |
| `nav2_behaviors` (Spin/BackUp/Wait/...) | `package/ClassName` (slash) |
| `nav2_controller` (progress/goal check) | `package::ClassName` (colon)|
| `dwb_core::DWBLocalPlanner`             | `package::ClassName` (colon)|

A blanket find/replace of `::` → `/` (or vice versa) across the whole file
breaks whichever half you didn't need to touch — we learned this the hard
way and had to restore from a backup and apply only the one line that was
actually broken (`nav2_navfn_planner`).

**Fix:** In `/opt/ros/humble/share/turtlebot3_navigation2/param/<model>.yaml`,
only the `planner_plugins` entry (`nav2_navfn_planner::NavfnPlanner` →
`nav2_navfn_planner/NavfnPlanner`) needed changing on this install. See
`scripts/fix_turtlebot3_nav2_plugin_names.sh` in this repo, which:

1. Makes a `.bak` backup of the file.
2. Applies just that one, precise substitution.
3. Prints a `grep -n plugin` diff-style view so you can confirm before
   relaunching.

If your install shows a *different* mismatch (the exact plugin registration
can vary with package versions), the same script's structure can be
adapted — fix one plugin line at a time, relaunch, and read the next
`[FATAL]` in the log rather than guessing.

Once this was fixed, the full Nav2 stack (planner_server, controller_server,
behavior_server, bt_navigator, waypoint_follower, velocity_smoother) came up
cleanly and `lifecycle_manager_navigation` reported
`Managed nodes are active`.

## 6. Planner can't reach the default "kitchen" waypoint

**Symptom:**
```
[planner_server]: GridBased: failed to create plan with tolerance 0.50.
Planning algorithm GridBased failed to generate a valid path to (2.00, 1.00)
```

**Diagnosis:** `config/waypoints.yaml`'s coordinates were chosen for a
conceptual "house" layout, but the Gazebo world actually being used for
local testing is the stock `turtlebot3_world` — a small arena with a 3x3
grid of pillar obstacles, not a house. `(2.0, 1.0)` happens to land too
close to/inside one of those pillars in that particular world.

**Status / fix direction:** Confirmed via manually sending a `Nav2 Goal` in
RViz to an open area — that's the next thing to re-verify once issue 7 is
resolved. The real fix is either (a) update `waypoints.yaml` with
coordinates that are actually free space in whichever world you're testing
against, or (b) build/use a custom map+world that matches the intended
"house" waypoint layout.

## 7. WSLg freezing after Nav2 fully activates (in progress)

**Symptom:** Repeatedly, right after `lifecycle_manager_navigation` logs
`Managed nodes are active` and `Creating bond timer...`, the whole
RViz/terminal session stops responding — no new log lines, RViz window not
interactive (can't even rotate the camera). Happened identically across a
`wsl --shutdown` + relaunch, and again after increasing WSL2's memory
allocation via `.wslconfig`, so it isn't simple RAM exhaustion.

**Leading theory:** WSLg falling back to software rendering ("llvmpipe")
instead of using the machine's NVIDIA GPU for Gazebo + RViz's simultaneous
3D rendering — a known class of issue with WSLg/NVIDIA driver interaction.
Early log evidence: RViz reported `OpenGL version: 4.1 (GLSL 4.1)`, which is
consistent with the software-rendering fallback rather than real GPU
acceleration.

**Next steps to try:**
1. Update the NVIDIA driver on the Windows host (not inside WSL) to the
   latest version.
2. `wsl --update` from PowerShell.
3. `sudo apt install mesa-utils -y && glxinfo | grep "OpenGL renderer"`
   inside WSL — if it reports `llvmpipe`, that confirms the theory.
4. If confirmed, follow WSLg's GPU-passthrough troubleshooting docs (see
   README references) to get proper NVIDIA acceleration working.

This section will be updated once resolved.

## Current status

- All ROS2 nodes, the custom natural-language command parser, and the full
  Nav2 stack come up and activate cleanly.
- Command parsing verified end-to-end: `"go to the kitchen"` correctly
  resolves to the `kitchen` waypoint with `confidence=1.00`.
- Blocked on confirming actual robot movement in Gazebo due to the WSLg
  rendering freeze (issue 7) cutting testing short before a reachable goal
  could be fully driven to completion.
