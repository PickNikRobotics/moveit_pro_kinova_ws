# moveit_pro_kinova_ws — `picknik_006_gen3` branch

This branch holds the [MoveIt Pro](https://picknik.ai/pro) robot configuration
for the **picknik_006_gen3** asset: a Kinova Gen3 7DoF arm + Robotiq 2F-85
(via the Kinova internal bus) + a wrist-mounted RealSense D415. The
arm-integrated Vision Module is also enabled.

Refer to the [Kinova Gen3 Hardware Setup Guide](https://docs.picknik.ai/hardware_guides/robot_arms/kinova_hardware_setup_guide/)
for installation.

## Asset-ID naming

Per the [robot config naming guidance](https://docs.picknik.ai/how_to/configuration_tutorials/robot_and_objective_inheritance/#robot-naming-conventions),
this branch's packages carry the `picknik_006_gen3_` prefix to mark them as
the configuration of a specific physical robot. New asset-ID branches should
fork `main` (which holds the bare-arm boilerplate `kinova_gen3_{mock,sim,hw}`)
rather than this one.

## Configurations on this branch

```
picknik_006_gen3_mock  →  picknik_006_gen3_sim  →  picknik_006_gen3_hw
```

- `picknik_006_gen3_mock` — trunk. Carries the URDF (arm + Robotiq 2F-85 +
  wrist RealSense + integrated Vision Module), SRDF, MoveIt configuration,
  and `ros2_control` config that the other two inherit. Runs ros2_control
  fake hardware so you can dev-test gripper and motion workflows without a
  physical arm.
- `picknik_006_gen3_sim` — MuJoCo. Inherits from `_mock` and overrides
  `urdf_params` to drop the gripper and wrist RealSense, so the URDF matches
  the bare-arm `description/mujoco/scene.xml` carried over from `main`. Use
  this for motion-only sim validation.
- `picknik_006_gen3_hw` — real hardware. Inherits from `_sim` and overrides
  `simulated`, `robot_ip`, `use_fake_hardware`, the driver launch file, and
  the `controllers_active_at_startup` list. Re-enables the gripper and wrist
  RealSense and uncomments the `cameras.launch.xml` include for the wrist
  RealSense driver. Set `robot_ip` to your robot's IP before running.
- `kinova_pstop_manager` — protective-stop helper, used by `_hw`.

## Relation to `main`

This branch does not merge back into `main`. `main` holds the bare-arm
boilerplate (`kinova_gen3_mock` → `kinova_gen3_sim` → `kinova_gen3_hw`); use
that as the reference when starting a new asset-ID branch.

## Meta Quest teleop over USB (ADB reverse tunnel)

The Quest teleop objective (`picknik_006_gen3_mock/objectives/quest_teleop.xml`)
talks to the headset over a TCP socket served by `ros_tcp_endpoint`. The path
can be either WLAN or USB; **USB is strongly preferred** because the Quest's
WLAN radio aggressively power-saves between bursts and produces multi-100ms
RTT staircases under load. ADB-reverse over USB-C tunnels the Quest app's
TCP connection through the cable to localhost on this machine, sidestepping
WLAN entirely.

### A. First-time setup on a new machine

One-time per rtpc. Steps assume a Debian/Ubuntu host with `sudo` access.

1. **Enable Developer Mode on the Quest.** In the Meta Quest mobile app:
   *Devices → (your headset) → Headset Settings → Developer Mode → On*. Requires
   the headset's Meta account to be in a developer organization (free; create
   one in the Meta developer dashboard).
2. **Install `adb` on the host.**
   ```bash
   sudo apt install android-tools-adb
   ```
3. **Add yourself to the `plugdev` group.** The group already exists on this
   rtpc; on other hosts run `getent group plugdev` first and `sudo groupadd
   plugdev` if missing.
   ```bash
   sudo usermod -aG plugdev $USER
   ```
4. **Install a udev rule for Meta/Oculus USB devices.** The vendor ID is
   `2833`. Create `/etc/udev/rules.d/51-quest.rules` containing:
   ```
   SUBSYSTEM=="usb", ATTR{idVendor}=="2833", MODE="0660", GROUP="plugdev", TAG+="uaccess"
   ```
   Then reload udev:
   ```bash
   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```
5. **Refresh group membership** by rebooting, or from a separate TTY:
   ```bash
   sudo loginctl terminate-user $USER
   ```
   Logging out from a single terminal usually isn't enough — graphical / SSH /
   `systemd --user` sessions pin the old group set.
6. **Plug the Quest into a USB-C port.** USB-C is required for charging while
   in use; USB-A trickle-charges at 2.5 W which is under the Quest's draw.
7. **Authorize on the headset.** `adb devices` should show the Quest as
   `unauthorized` initially. Put on the headset and accept the *"Allow USB
   debugging?"* prompt — **tick "Always allow from this computer"** or you'll
   see this prompt on every connection. After approval:
   ```bash
   adb devices       # Quest should now show "device"
   ```
8. **Start the reverse tunnel.**
   ```bash
   adb reverse tcp:10000 tcp:10000
   adb reverse --list   # confirm "UsbFfs tcp:10000 tcp:10000"
   ```
9. **Confirm the ROS side is listening on loopback.** The drivers launch file
   already binds `ros_tcp_endpoint` to `0.0.0.0` (see
   `picknik_006_gen3_hw/launch/robot_drivers_to_persist.launch.py`), which
   accepts both the loopback path (USB) and WLAN simultaneously.
10. **Configure the Quest app to target localhost.** In the Quest's ROS
    configuration UI, set the host IP to `127.0.0.1` and port `10000`. The
    Quest app's TCP connection to that loopback address is what `adb reverse`
    tunnels to the host.

### B. Subsequent use after unplug or Quest power-off

The reverse tunnel mapping is ephemeral — it dies whenever the cable is
unplugged or `adbd` restarts (which happens on Quest reboot/power-off too).
Everything else (udev rule, `plugdev` membership, the Quest's saved
authorization key) persists across reboots and power cycles.

1. Plug the Quest into the USB-C port. Wake it.
2. Re-establish the tunnel:
   ```bash
   adb devices                      # should show "device" (not "unauthorized")
   adb reverse tcp:10000 tcp:10000
   ```
3. If `adb devices` instead shows `unauthorized`, accept the on-headset
   prompt. This shouldn't happen if you ticked "Always allow" originally; if
   it does, double-check that the same `~/.android/adbkey` is in use
   (`md5sum ~/.android/adbkey.pub` should be stable).

The Quest app can be started before or after `adb reverse` — it will retry the
TCP connection on its own.
