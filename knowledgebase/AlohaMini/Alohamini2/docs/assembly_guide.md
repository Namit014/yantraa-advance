# AlohaMini2 Assembly Guide

AlohaMini2 is the reinforced successor to AlohaMini1. It uses AM-ARM200 arms instead of SO-ARM100/101, upgrades the lift servo from STS-3215 to high-torque STS-3095, and strengthens the chassis for higher base loads. All printed parts are designed to fit a standard Bambu P2S printer.

This guide covers the AlohaMini2 Mobile Base 2 assembly. Prepare the follower and leader arms in advance using the [AM-ARM200 Assembly Guide](https://github.com/liyiteng/AM-ARM/tree/main/am-arm200).

## Servo ID Setup

Assign servo IDs before installing the servos. Configure one servo at a time to avoid ID conflicts.

| Servo | ID | Location |
|-------|----|----------|
| Rear-left wheel | 10 | Chassis |
| Front wheel | 9 | Chassis |
| Rear-right wheel | 8 | Chassis |
| Lift axis | 11 | Shoulder block |

### Using lerobot_alohamini

The recommended command is provided by the [`lerobot_alohamini`](https://github.com/liyiteng/lerobot_alohamini) repository. Clone that repository, install its dependencies, and run the command from the repository root:

```bash
git clone https://github.com/liyiteng/lerobot_alohamini.git
cd lerobot_alohamini
```

Example:

```bash
python examples/debug/motors.py configure_motor_id \
  --id 1 \
  --set_id 8 \
  --port /dev/ttyACM0
```

You can also use the Feetech FD Debug Tool through the Waveshare bus servo controller. Use baud rate `1000000`, scan the connected servo, write the target ID, then disconnect it before configuring the next servo.

## 1. Build the Chassis

Remove all print supports from the chassis parts, especially the wheel pockets, cable channels, and dowel-pin slots.

<img src="./media/assembly/chassis-kit.jpg" alt="Chassis printed parts and fasteners" width="420">

Apply epoxy to the mating surfaces.

<img src="./media/assembly/chassis-epoxy-surfaces.jpg" alt="Epoxy applied to chassis mating surfaces" width="420">

Insert `OB_Chassis_Locking_Wedge.stl` into the locking-pin slot. The three chassis locking pins are tapered; install them in the correct direction so they can wedge the tower base tightly after assembly.

<img src="./media/assembly/chassis-locking-wedge.jpg" alt="Chassis locking wedge installed" width="420">

Apply epoxy to the `OB_Chassis_Frame_Joiner.stl` joiner, then press the chassis parts together until they are fully seated.

<img src="./media/assembly/chassis-frame-joiner.jpg" alt="Chassis frame joiner before installation" width="420">
<img src="./media/assembly/chassis-joined-frame.jpg" alt="Joined chassis frame" width="420">

Install the three wheel servos in the chassis.

<img src="./media/assembly/wheel-servos.jpg" alt="Wheel servos before installation" width="420">

After assigning servo IDs, place the servos in the chassis in the orientation shown below.

<img src="./media/assembly/wheel-servo-id-layout.jpg" alt="Wheel servo ID layout in chassis" width="420">

Connect servo 8 to servo 9, servo 9 to servo 10, and servo 10 to servo 11. Because servos 10 and 11 are far apart, use at least a 90 cm 3-pin servo cable; a 140 cm cable is recommended. Fasten the servos with the screws supplied with the servos.

<img src="./media/assembly/wheel-servo-cable-routing.jpg" alt="Wheel servo cable routing" width="420">

## 2. Install the Omni Wheels

Pre-install four M3x10 screws into each wheel-to-servo connector. Press the connector onto the servo output disc, confirm that all four mounting holes are aligned, then tighten the screws through the access opening.

<img src="./media/assembly/wheel-connectors-and-screws.jpg" alt="Wheel connectors and M3x10 screws" width="420">
<img src="./media/assembly/wheel-connector-on-servo-disc.jpg" alt="Wheel connector on servo output disc" width="420">
<img src="./media/assembly/wheel-connector-tightening.jpg" alt="Tightening the wheel connector through the access opening" width="420">

Install each omni wheel with its axle, 12x18x4 mm bearings, washers, and bearing cover.

<img src="./media/assembly/omni-wheel-hardware.jpg" alt="Omni wheel axle and bearing hardware" width="420">
<img src="./media/assembly/omni-wheel-axle-install.jpg" alt="Installing the omni wheel axle" width="420">
<img src="./media/assembly/omni-wheel-cover-installed.jpg" alt="Installed omni wheel bearing cover" width="420">

The chassis assembly is now complete. At this point, you can use the debug command in the `lerobot_alohamini` repository to drive the base directly for a first test.

```bash
python examples/debug/wheels.py --port /dev/ttyACM0  # W/S/A/D drive test
```

<img src="./media/assembly/chassis-drive-test.jpg" alt="Completed chassis during drive test" width="420">

## 3. Build and Mount the Lift Tower

Build the tower in this order:

`O_POST4_Connector_Base.stl -> O_Main_Assembly_Post4.stl -> OB_Main_Assembly_Post3.stl -> OB_Main_Assembly_Post2.stl -> OB_Main_Assembly_Post1.stl`

Apply epoxy to each contact surface, stack the parts in order, and wipe away excess adhesive before it cures.

<img src="./media/assembly/lift-tower-parts.jpg" alt="Lift tower printed parts" width="420">
<img src="./media/assembly/lift-tower-assembled.jpg" alt="Assembled lift tower" width="420">

Place the chassis with servo 9 facing you. The lift rack should also face you. Press the tower's hex base into the chassis socket, flip the assembly over, and tap evenly around the six side faces until the flange sits fully flush with the chassis.

<img src="./media/assembly/tower-in-chassis-orientation.jpg" alt="Lift tower orientation in chassis socket" width="420">
<img src="./media/assembly/tower-base-locking.jpg" alt="Locking the tower base into the chassis" width="420">

Route the wheel servo cable through the center hole and side cable channels, then return the base upright.

<img src="./media/assembly/tower-cable-center-hole.jpg" alt="Wheel servo cable routed through center hole" width="420">
<img src="./media/assembly/tower-cable-side-channels.jpg" alt="Wheel servo cable routed through side channels" width="420">

## 4. Build the Shoulder Lift Block

Press the eight 4x13x5 mm track bearings into the shoulder bearing block. All bearings should sit flush and rotate freely.

<img src="./media/assembly/shoulder-bearing-kit.jpg" alt="Shoulder bearing block and track bearings" width="420">
<img src="./media/assembly/shoulder-bearing-install.jpg" alt="Installing track bearings into the shoulder block" width="420">

Pre-install four M3x10 screws into the lift gear, then insert the 12x25 mm shaft from the right side. Rotate the gear until the screw tips drop into the servo output disc holes, then tighten the screws through the side access windows.

<img src="./media/assembly/lift-gear-hardware.jpg" alt="Lift gear hardware" width="420">
<img src="./media/assembly/lift-gear-on-servo.jpg" alt="Lift gear aligned with servo output disc" width="420">
<img src="./media/assembly/lift-axis-shaft.jpg" alt="Lift axis shaft installed through the shoulder block" width="420">

Bond the shoulder T-frame with epoxy and let it fully cure before loading the arms.

<img src="./media/assembly/shoulder-t-frame.jpg" alt="Bonded shoulder T-frame" width="420">

Slide the shoulder T-frame onto the tower rails. It should travel smoothly without binding.

<img src="./media/assembly/shoulder-block-on-tower.jpg" alt="Shoulder lift block installed on tower rails" width="420">

## 5. Install the Cameras

Install the two top cameras into the printed top camera mounts. Remove each camera back cover, place the printed mount/back-cover part between the camera body and cover, and fasten it with two M2x12 screws.

<img src="./media/assembly/top-camera-parts.jpg" alt="Top camera mount parts" width="420">
<img src="./media/assembly/top-camera-back-cover.jpg" alt="Top camera back cover installation" width="420">
<img src="./media/assembly/top-camera-mount-installed.jpg" alt="Top camera installed in printed mount" width="420">

Install the chest camera in the front bracket using the same back-cover mounting method.

<img src="./media/assembly/chest-camera-parts.jpg" alt="Chest camera mount parts" width="420">
<img src="./media/assembly/chest-camera-back-cover.jpg" alt="Chest camera back cover installation" width="420">
<img src="./media/assembly/chest-camera-installed.jpg" alt="Chest camera installed in front bracket" width="420">

## 6. Mount the Follower Arms and Route Cables

Fasten the left and right follower arms to the shoulder T-frame using the long M3 socket screws and M3 nuts. One arm mounts on each side.

<img src="./media/assembly/follower-arms-mounted.jpg" alt="Follower arms mounted to the shoulder T-frame" width="420">
<img src="./media/assembly/follower-arm-fasteners.jpg" alt="Follower arm mounting fasteners" width="420">

Feed the arm and camera cables through the cable ports in the lift tower.

<img src="./media/assembly/tower-cable-port.jpg" alt="Cable port in the lift tower" width="420">
<img src="./media/assembly/arm-camera-cables-routed.jpg" alt="Arm and camera cables routed through the tower" width="420">

Connect the 3-pin cable from lift servo 11 to the servo driver board on the left arm. Leave enough slack for the shoulder to move through its full vertical travel.

| Side | Cable bundle |
|------|--------------|
| Left | Arm power, arm Type-C, wrist camera USB, chest camera USB, lift servo cable |
| Right | Arm power, arm Type-C, wrist camera USB |

Slide protective cable sleeves over the routed bundles.

<img src="./media/assembly/left-cable-bundle.jpg" alt="Left cable bundle" width="420">
<img src="./media/assembly/right-cable-bundle.jpg" alt="Right cable bundle" width="420">
<img src="./media/assembly/cable-sleeves-installed.jpg" alt="Protective cable sleeves installed" width="420">

## 7. Install Display, Compute, and Power

Fasten the display to its printed bracket with four M3x6 screws, slide the bracket into the rear dovetail slot, and connect the short micro-HDMI cable plus Type-C power cable.

<img src="./media/assembly/display-bracket-parts.jpg" alt="Display bracket parts" width="420">
<img src="./media/assembly/display-mounted.jpg" alt="Display mounted on rear dovetail bracket" width="420">

Mount the Raspberry Pi 5, buck converter, battery packs, and counterweight in the rear support.

<img src="./media/assembly/compute-power-rear-bay.jpg" alt="Raspberry Pi, buck converter, batteries, and counterweight in rear support" width="420">

Wire power as follows:

| Power path | Connection |
|------------|------------|
| Arm power | Battery 1 -> 2-to-1 splitter -> left and right arm DC cables |
| Compute power | Battery 2 -> buck converter -> Raspberry Pi Type-C power port |

<img src="./media/assembly/power-wiring.jpg" alt="AlohaMini2 power wiring" width="420">

## 8. Functional Test

Before running the full robot, test each moving subsystem:

```bash
python examples/debug/wheels.py --port /dev/ttyACM0  # W/S/A/D drive test
python examples/debug/axis.py --port /dev/ttyACM0    # U/J lift test
```
