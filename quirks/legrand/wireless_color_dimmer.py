"""Legrand Wireless Color Dimmer ZHA quirk.

Reference: https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/src/devices/legrand.ts
           model 067767 – "Wireless Color Ambiance Switch 067767/68/69 - 077710L"

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

Supported ZHA device-automation triggers
─────────────────────────────────────────
  short_press  / turn_on              OnOff  "on"
  short_press  / turn_off             OnOff  "off"
  short_press  / toggle               OnOff  "toggle"
  short_press  / dim_up               LevelCtrl  "step_with_on_off" (↑)
  short_press  / dim_down             LevelCtrl  "step"             (↓)
  long_press   / dim_up               LevelCtrl  "move_with_on_off" (↑ continuous)
  long_press   / dim_down             LevelCtrl  "move"             (↓ continuous)
  long_release / dim_up               LevelCtrl  "stop_with_on_off"
  long_release / dim_down             LevelCtrl  "stop"
  short_press  / scene_1              Scenes  "recall" scene_id=1
  short_press  / scene_2              Scenes  "recall" scene_id=2
  short_press  / scene_3              Scenes  "recall" scene_id=3

Place this file in <config>/custom_zha_quirks/legrand/
and set `zha: custom_quirks_path: /config/custom_zha_quirks`
in your configuration.yaml.
"""

import zigpy.profiles.zha as zha_p
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    BinaryInput,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PollControl,
    PowerConfiguration,
    Scenes,
)

from zhaquirks import CustomCluster
from zhaquirks.const import (
    ARGS,
    CLUSTER_ID,
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
    """Quirk for the Legrand Wireless Color Dimmer (model 067767).

    Battery-powered "Color Ambiance" remote.  Sends On/Off, LevelControl
    and Scenes commands to paired lights.  The manufacturer-specific cluster
    0xFC01 is replaced by LegrandCluster so ZHA can read its attributes.
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
    # On/Off cluster  ──────────────────────────────────────────────────────
    #   on / off / toggle buttons.
    #
    # LevelControl cluster  ────────────────────────────────────────────────
    #   step_size 51 ≈ 20 % of 255 per short press.
    #   move rate  85 ≈ full range in ~3 s.
    #   step_with_on_off / move_with_on_off also turn the light on if needed.
    #
    # Scenes cluster (genScenes)  ──────────────────────────────────────────
    #   The three colour-temperature preset buttons send "recall" commands.

    device_automation_triggers = {
        # --- On/Off -------------------------------------------------------
        (SHORT_PRESS, "turn_on"): {
            COMMAND: "on",
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 1,
        },
        (SHORT_PRESS, "turn_off"): {
            COMMAND: "off",
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 1,
        },
        (SHORT_PRESS, "toggle"): {
            COMMAND: "toggle",
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 1,
        },
        # --- Brightness: short press (step) --------------------------------
        (SHORT_PRESS, "dim_up"): {
            COMMAND: "step_with_on_off",
            CLUSTER_ID: LevelControl.cluster_id,
            ENDPOINT_ID: 1,
            ARGS: {"step_mode": 0, "step_size": 51, "transition_time": 5},
        },
        (SHORT_PRESS, "dim_down"): {
            COMMAND: "step",
            CLUSTER_ID: LevelControl.cluster_id,
            ENDPOINT_ID: 1,
            ARGS: {"step_mode": 1, "step_size": 51, "transition_time": 5},
        },
        # --- Brightness: long press (continuous move) ----------------------
        (LONG_PRESS, "dim_up"): {
            COMMAND: "move_with_on_off",
            CLUSTER_ID: LevelControl.cluster_id,
            ENDPOINT_ID: 1,
            ARGS: {"move_mode": 0, "rate": 85},
        },
        (LONG_PRESS, "dim_down"): {
            COMMAND: "move",
            CLUSTER_ID: LevelControl.cluster_id,
            ENDPOINT_ID: 1,
            ARGS: {"move_mode": 1, "rate": 85},
        },
        # --- Brightness: release (stop) ------------------------------------
        (LONG_RELEASE, "dim_up"): {
            COMMAND: "stop_with_on_off",
            CLUSTER_ID: LevelControl.cluster_id,
            ENDPOINT_ID: 1,
        },
        (LONG_RELEASE, "dim_down"): {
            COMMAND: "stop",
            CLUSTER_ID: LevelControl.cluster_id,
            ENDPOINT_ID: 1,
        },
        # --- Colour-temperature presets (scene recall) ---------------------
        (SHORT_PRESS, "scene_1"): {
            COMMAND: "recall",
            CLUSTER_ID: Scenes.cluster_id,
            ENDPOINT_ID: 1,
            ARGS: {"group_id": 0, "scene_id": 1},
        },
        (SHORT_PRESS, "scene_2"): {
            COMMAND: "recall",
            CLUSTER_ID: Scenes.cluster_id,
            ENDPOINT_ID: 1,
            ARGS: {"group_id": 0, "scene_id": 2},
        },
        (SHORT_PRESS, "scene_3"): {
            COMMAND: "recall",
            CLUSTER_ID: Scenes.cluster_id,
            ENDPOINT_ID: 1,
            ARGS: {"group_id": 0, "scene_id": 3},
        },
    }
