from hermes_cli.overlay_loader import load_architecture_overlay


def test_architecture_overlay_loader_imports_autonomy_module():
    overlay = load_architecture_overlay("autonomy")

    assert overlay.is_autonomous_mission_prompt("AUTONOMOUS_MISSION: smoke")
