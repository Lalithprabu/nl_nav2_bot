#!/usr/bin/env bash
# Fixes a pluginlib class-name mismatch seen in the stock
# turtlebot3_navigation2 (Humble) default params file, where the
# GridBased planner is declared as "nav2_navfn_planner::NavfnPlanner"
# (colon form) but the installed nav2_navfn_planner plugin on a stock
# Humble system is registered as "nav2_navfn_planner/NavfnPlanner"
# (slash form). See TROUBLESHOOTING.md, issue 5, for the full story.
#
# This script only touches that one plugin line. If your install shows
# a *different* pluginlib mismatch (the [FATAL] log will name the exact
# class and list what's actually "Declared"), adapt the sed pattern
# below rather than blanket-converting the whole file - other plugin
# families (nav2_controller, dwb_core) use the OPPOSITE convention on a
# stock Humble install and a blanket find/replace will break them.
set -euo pipefail

MODEL="${TURTLEBOT3_MODEL:-waffle}"
PARAMS_FILE="/opt/ros/humble/share/turtlebot3_navigation2/param/${MODEL}.yaml"

if [ ! -f "$PARAMS_FILE" ]; then
  echo "Could not find $PARAMS_FILE - is turtlebot3_navigation2 installed, and is TURTLEBOT3_MODEL set correctly?" >&2
  exit 1
fi

BACKUP="${PARAMS_FILE}.bak"
if [ ! -f "$BACKUP" ]; then
  sudo cp "$PARAMS_FILE" "$BACKUP"
  echo "Backed up original to $BACKUP"
else
  echo "Backup already exists at $BACKUP (not overwriting)"
fi

sudo sed -i 's|"nav2_navfn_planner::NavfnPlanner"|"nav2_navfn_planner/NavfnPlanner"|' "$PARAMS_FILE"

echo ""
echo "Done. Current plugin lines in ${PARAMS_FILE}:"
grep -n "plugin" "$PARAMS_FILE"
