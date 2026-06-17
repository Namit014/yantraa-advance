# LeKiwi Datasheet

## General Specifications
- **Type:** Mobile Manipulator
- **Degrees of Freedom (DOF):** 3 (Mobile Base Holonomic) + 6 (Arm) = 9 DOF total
- **Main Controller:** Raspberry Pi 5 (4GB)

## Mobile Base
- **Drive Type:** Holonomic omni-drive (3 wheels)
- **Wheels:** 4-inch Omni wheels
- **Actuators:** STS3215 serial bus servos
- **Power:** 5V (Laptop Powerbank) or 12V (Li-ion Battery Pack)

## Manipulator (SO-100/SO-101)
- **Type:** 6-DOF Articulated Arm
- **Actuators:** STS3215 servos
- **End Effector:** Parallel Jaw Gripper

## Vision System
- **Sensors:** 2x USB Cameras
- **Placements:** 
  - Base camera for forward navigation view
  - Wrist camera for manipulation feedback
