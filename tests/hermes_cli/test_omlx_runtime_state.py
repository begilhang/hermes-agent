from hermes_cli.autonomy.omlx_runtime_state import build_omlx_runtime_state


def test_omlx_runtime_state_separates_default_from_loaded_unknown():
    health = {
        "default_model": "Qwopus3.6-35B-A3B-v1-6bit-MTPLX-Optimized-Speed",
        "engine_pool": {
            "loaded_count": 1,
            "current_model_memory": 17861562629,
            "final_ceiling": 59055800320,
        },
    }

    state = build_omlx_runtime_state(
        health=health,
        requested_route_model="Qwopus3.6-27B-v2-oQ4-mtp",
        models={},
    )

    assert state["configured_default_model"] == "Qwopus3.6-35B-A3B-v1-6bit-MTPLX-Optimized-Speed"
    assert state["requested_route_model"] == "Qwopus3.6-27B-v2-oQ4-mtp"
    assert state["loaded_model_name"] == "UNKNOWN"
    assert state["current_model_memory"] == 17861562629
    assert state["default_label_mismatch_possible"] is True


def test_omlx_runtime_state_uses_loaded_model_when_exposed():
    health = {
        "default_model": "Qwopus35",
        "engine_pool": {
            "loaded_count": 1,
            "current_model_memory": 100,
            "loaded_model": "Qwopus27",
        },
    }

    state = build_omlx_runtime_state(
        health=health,
        requested_route_model="Qwopus27",
        models={},
    )

    assert state["loaded_model_name"] == "Qwopus27"
    assert state["default_label_mismatch_possible"] is True
