"""Unit tests for command_parser.py. No ROS 2 installation required."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from nl_nav2_bot.command_parser import parse_command, rule_based_match  # noqa: E402

WAYPOINTS = ['kitchen', 'living_room', 'charging_station', 'lab', 'front_door']


def test_exact_match():
    result = rule_based_match('go to the kitchen', WAYPOINTS)
    assert result.waypoint == 'kitchen'
    assert result.confidence == 1.0


def test_underscored_name_with_spaces():
    result = rule_based_match('please navigate to living room', WAYPOINTS)
    assert result.waypoint == 'living_room'


def test_fuzzy_match_typo():
    result = rule_based_match('go to the kichen', WAYPOINTS)
    assert result.waypoint == 'kitchen'


def test_no_match_returns_none():
    result = rule_based_match('what is the weather today', WAYPOINTS)
    assert result.waypoint is None


def test_parse_command_end_to_end_rule_only():
    # With no OPENAI_API_KEY set, parse_command should behave exactly like
    # rule_based_match for a clear match.
    os.environ.pop('OPENAI_API_KEY', None)
    result = parse_command('take me to the charging station', WAYPOINTS)
    assert result.waypoint == 'charging_station'
    assert result.method == 'rule'


def test_parse_command_no_match_no_llm_key():
    os.environ.pop('OPENAI_API_KEY', None)
    result = parse_command('tell me a joke', WAYPOINTS)
    assert result.waypoint is None
    assert result.method == 'none'
