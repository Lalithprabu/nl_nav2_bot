# nl_nav2_bot

Natural-language commander for ROS 2 + Nav2. Type (or eventually speak) a
command like **"go to the kitchen"** and a simulated TurtleBot3 autonomously
navigates there using Nav2's `NavigateToPose` action — no manual waypoint
picking, no rviz clicking.

Command understanding is rule-based by default (fast, deterministic, works
fully offline via fuzzy string matching), with an optional LLM fallback
(OpenAI) for free-form phrasing the rules can't resolve, e.g. *"I'm hungry,
take me to where the food is"* → kitchen.

## Why this project

- Combines two of the most active areas in robotics right now: **Nav2
  autonomous navigation** and **LLM-assisted robot interfaces**.
- Fully simulation-based (Gazebo + RViz) — no hardware required.
- The LLM piece is optional and gracefully degrades, so the project is
  usable, testable, and CI-friendly with zero API keys.

## Architecture

```
 text_input_node  --/nl_command (String)-->  nl_command_node  --NavigateToPose-->  Nav2
        ^                                          |
        |<---------- /nl_command_status ----------+
```

- `text_input_node`: CLI stand-in for a voice/chat front-end. Publishes
  typed text to `/nl_command`.
- `nl_command_node`: subscribes to `/nl_command`, resolves it to a named
  waypoint (see `command_parser.py`), and sends a goal to Nav2's
  `navigate_to_pose` action server. Publishes human-readable status to
  `/nl_command_status`.
- `command_parser.py`: pure-Python, no ROS dependency, unit-tested in
  isolation. Rule-based matching first (substring + fuzzy match against
  `config/waypoints.yaml`), then an optional LLM call if
  `OPENAI_API_KEY` is set and nothing else matched.

## Requirements

- ROS 2 Humble (Ubuntu 22.04) — or run via the `osrf/ros:humble-desktop`
  Docker image, which is what CI uses.
- `turtlebot3_gazebo` and `turtlebot3_navigation2` packages
  (`sudo apt install ros-humble-turtlebot3*`)
- Python: `pyyaml` (and optionally `openai` for the LLM fallback)

## Setup

```bash
# In your ROS 2 workspace's src/ folder
git clone <this-repo-url> nl_nav2_bot
cd ..
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
```

## Running the simulation

```bash
export TURTLEBOT3_MODEL=waffle
ros2 launch nl_nav2_bot nl_nav2_bringup.launch.py
```

This brings up Gazebo with the TurtleBot3 world, the full Nav2 stack, and
`nl_command_node`. In RViz, set the initial pose estimate once (2D Pose
Estimate) so Nav2's localization has a starting point.

In a second terminal:

```bash
ros2 run nl_nav2_bot text_input_node
> go to the kitchen
[status] Understood "go to the kitchen" -> "kitchen" (method=rule, confidence=1.00)
[status] Sending goal: navigate to "kitchen".
[status] Arrived at destination.
```

Or publish directly without the CLI node:

```bash
ros2 topic pub --once /nl_command std_msgs/String "data: 'go to the charging station'"
```

## Editing locations

Edit `config/waypoints.yaml` to match your own map — add, rename, or
reposition named locations (x, y in meters, yaw in radians, map frame).

## Optional: enabling the LLM fallback

```bash
pip install openai
export OPENAI_API_KEY=sk-...
```

With this set, commands that don't match any waypoint by name or fuzzy
match are sent to an LLM, which picks the closest known location (or
declines if nothing fits). No key set → the node still works, just with
rule-based matching only.

## Testing

The command parser has no ROS dependency and can be tested without a ROS 2
install at all:

```bash
pip install pytest pyyaml
pytest test/test_command_parser.py -v
```

Full package build + lint + test (needs a ROS 2 Humble environment):

```bash
colcon test --packages-select nl_nav2_bot
colcon test-result --verbose
```

## Roadmap ideas

- Swap `text_input_node` for real speech-to-text (e.g. Whisper) — the
  `/nl_command` topic contract doesn't need to change.
- Multi-step commands ("go to the kitchen then the lab").
- Auto-generate `waypoints.yaml` from semantic map labels.

## License

MIT — see [LICENSE](LICENSE).
