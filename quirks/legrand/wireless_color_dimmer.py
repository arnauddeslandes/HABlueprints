"""Legrand Wireless Color Dimmer ZHA quirk.

Device signature:
  Manufacturer : " Legrand"
  Model        : " Wireless Color Dimmer"
  Endpoint 1   :
    Profile    : 0x0104 (Home Automation)
    Device type: 0x0006
    In clusters : Basic, PowerConfig, Identify, BinaryInput,
                  PollControl, LegrandCluster (0xFC01)
    Out clusters: Basic, Identify, Scenes, OnOff, LevelControl,
                  Ota, LegrandCluster (0xFC01)

Place this file in <config>/custom_zha_quirks/legrand/
and set `zha: custom_quirks_path: /config/custom_zha_quirks`
in your configuration.yaml.
"""

import zigpy.profiles.zha as zha_p
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PollControl,
    PowerConfiguration,
    Scenes,
)
from zigpy.zcl.clusters.measurement import BinaryInput

from zhaquirks import CustomCluster
from zhaquirks.const import (
    ARGS,
    COMMAND,
    DEVICE_TYPE,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    LONG_RELEASE,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
)

LEGRAND_MANUFACTURER = " Legrand"
LEGRAND_CLUSTER_ID = 0xFC01

# ---------------------------------------------------------------------------
# Manufacturer-specific cluster 0xFC01
# ---------------------------------------------------------------------------


class LegrandCluster(CustomCluster):
    """Legrand proprietary cluster (0xFC01).

    Handles device-specific attributes such as LED night-mode brightness
    and device operating mode.  Actual attribute/command IDs are
    manufacturer-defined; extend as needed once sniffed from the device.
    """

    cluster_id = LEGRAND_CLUSTER_ID
    name = "LegrandCluster"
    ep_attribute = "legrand_cluster"

    attributes = {
        0x0000: ("led_in_dark", None),
        0x0001: ("led_if_on", None),
    }

    server_commands = {}
    client_commands = {}


# ---------------------------------------------------------------------------
# Device quirk
# ---------------------------------------------------------------------------


class LegrandWirelessColorDimmer(CustomDevice):
    """Quirk for the Legrand Wireless Color Dimmer.

    This battery-powered remote sends On/Off and LevelControl commands to
    paired lights.  The manufacturer-specific cluster 0xFC01 is replaced by
    LegrandCluster so that ZHA can read its attributes (e.g. LED brightness).

    Supported device-automation triggers
    ─────────────────────────────────────
    short_press  / turn_on       → OnOff "on"
    short_press  / turn_off      → OnOff "off"
    short_press  / dim_up        → LevelControl "step_with_on_off" (↑)
    short_press  / dim_down      → LevelControl "step" (↓)
    long_press   / dim_up        → LevelControl "move_with_on_off" (↑ continuous)
    long_press   / dim_down      → LevelControl "move" (↓ continuous)
    long_release / dim_up        → LevelControl "stop_with_on_off"
    long_release / dim_down      → LevelControl "stop"
    """

    # -- Signature (must match the device exactly) --------------------------

    signature = {
        MODELS_INFO: [(LEGRAND_MANUFACTURER, " Wireless Color Dimmer")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,  # 0x0104
                DEVICE_TYPE: 0x0006,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,               # 0x0000
                    PowerConfiguration.cluster_id,  # 0x0001
                    Identify.cluster_id,             # 0x0003
                    BinaryInput.cluster_id,          # 0x000F
                    PollControl.cluster_id,          # 0x0020
                    LEGRAND_CLUSTER_ID,              # 0xFC01
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,               # 0x0000
                    Identify.cluster_id,             # 0x0003
                    Scenes.cluster_id,               # 0x0005
                    OnOff.cluster_id,                # 0x0006
                    LevelControl.cluster_id,         # 0x0008
                    Ota.cluster_id,                  # 0x0019
                    LEGRAND_CLUSTER_ID,              # 0xFC01
                ],
            }
        },
    }

    # -- Replacement (swap raw 0xFC01 for our typed LegrandCluster) ---------

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: 0x0006,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    BinaryInput.cluster_id,
                    PollControl.cluster_id,
                    LegrandCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    LegrandCluster,
                ],
            }
        },
    }

    # -- Device-automation triggers -----------------------------------------
    #
    # step_size 51 ≈ 20 % of 255 per short press.
    # move rate 85 ≈ reaches full brightness in ~3 s.

    device_automation_triggers = {
        (SHORT_PRESS, "turn_on"): {
            COMMAND: "on",
            ENDPOINT_ID: 1,
        },
        (SHORT_PRESS, "turn_off"): {
            COMMAND: "off",
            ENDPOINT_ID: 1,
        },
        (SHORT_PRESS, "dim_up"): {
            COMMAND: "step_with_on_off",
            ENDPOINT_ID: 1,
            ARGS: {"step_mode": 0, "step_size": 51, "transition_time": 5},
        },
        (SHORT_PRESS, "dim_down"): {
            COMMAND: "step",
            ENDPOINT_ID: 1,
            ARGS: {"step_mode": 1, "step_size": 51, "transition_time": 5},
        },
        (LONG_PRESS, "dim_up"): {
            COMMAND: "move_with_on_off",
            ENDPOINT_ID: 1,
            ARGS: {"move_mode": 0, "rate": 85},
        },
        (LONG_PRESS, "dim_down"): {
            COMMAND: "move",
            ENDPOINT_ID: 1,
            ARGS: {"move_mode": 1, "rate": 85},
        },
        (LONG_RELEASE, "dim_up"): {
            COMMAND: "stop_with_on_off",
            ENDPOINT_ID: 1,
        },
        (LONG_RELEASE, "dim_down"): {
            COMMAND: "stop",
            ENDPOINT_ID: 1,
        },
    }
