from turtlebot_keyboard.keyboard_controller import velocity_for_key


def test_movement_keys_use_fixed_speed():
    speed = 0.01

    assert velocity_for_key('w', speed) == (0.01, 0.0)
    assert velocity_for_key('s', speed) == (-0.01, 0.0)
    assert velocity_for_key('a', speed) == (0.0, 0.01)
    assert velocity_for_key('d', speed) == (0.0, -0.01)


def test_uppercase_keys_are_supported():
    assert velocity_for_key('W', 0.01) == (0.01, 0.0)


def test_stop_and_unknown_keys():
    assert velocity_for_key(' ', 0.01) == (0.0, 0.0)
    assert velocity_for_key('x', 0.01) == (0.0, 0.0)
    assert velocity_for_key('?', 0.01) is None
