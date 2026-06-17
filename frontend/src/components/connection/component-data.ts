export interface ComponentItem {
  id: string;
  name: string;
  icon: string; // emoji or lucide icon name
  category: string;
}

export interface ComponentCategory {
  name: string;
  count: number;
  items: ComponentItem[];
}

export const COMPONENT_CATEGORIES: ComponentCategory[] = [
  {
    name: "CONTROLLERS",
    count: 8,
    items: [
      { id: "arduino-uno", name: "Arduino Uno", icon: "🔲", category: "controllers" },
      { id: "esp32", name: "ESP32", icon: "📟", category: "controllers" },
      { id: "raspberry-pi", name: "Raspberry Pi", icon: "🍓", category: "controllers" },
      { id: "stm32", name: "STM32", icon: "⚡", category: "controllers" },
    ],
  },
  {
    name: "MOTORS & ACTUATORS",
    count: 15,
    items: [
      { id: "servo-motor", name: "Servo Motor", icon: "⚙️", category: "motors" },
      { id: "dc-motor", name: "DC Motor", icon: "🔄", category: "motors" },
      { id: "stepper-motor", name: "Stepper Motor", icon: "🔧", category: "motors" },
      { id: "bldc-motor", name: "BLDC Motor", icon: "💨", category: "motors" },
      { id: "linear-actuator", name: "Linear Actuator", icon: "↔️", category: "motors" },
      { id: "solenoid", name: "Solenoid", icon: "🧲", category: "motors" },
      { id: "relay", name: "Relay", icon: "🔀", category: "motors" },
      { id: "gear-motor", name: "Gear Motor", icon: "⚙️", category: "motors" },
    ],
  },
  {
    name: "SENSORS",
    count: 21,
    items: [
      { id: "ultrasonic", name: "Ultrasonic", icon: "📡", category: "sensors" },
      { id: "ir-sensor", name: "IR Sensor", icon: "🔴", category: "sensors" },
      { id: "limit-switch", name: "Limit Switch", icon: "🔘", category: "sensors" },
      { id: "encoders", name: "Encoders", icon: "📊", category: "sensors" },
      { id: "imu", name: "IMU", icon: "🧭", category: "sensors" },
      { id: "force-sensor", name: "Force Sensor", icon: "💪", category: "sensors" },
      { id: "line-sensor", name: "Line Sensor", icon: "➖", category: "sensors" },
      { id: "camera", name: "Camera", icon: "📷", category: "sensors" },
    ],
  },
  {
    name: "POWER",
    count: 10,
    items: [
      { id: "power-supply", name: "Power Supply", icon: "🔌", category: "power" },
      { id: "battery", name: "Battery", icon: "🔋", category: "power" },
      { id: "voltage-regulator", name: "Voltage Regulator", icon: "⚡", category: "power" },
      { id: "dc-dc-converter", name: "DC-DC Converter", icon: "🔃", category: "power" },
    ],
  },
  {
    name: "DRIVERS & MODULES",
    count: 14,
    items: [
      { id: "motor-driver-l298n", name: "Motor Driver L298N", icon: "🎛️", category: "drivers" },
      { id: "servo-driver-pca9685", name: "Servo Driver PCA9685", icon: "🎚️", category: "drivers" },
      { id: "mosfet-module", name: "MOSFET Module", icon: "🔲", category: "drivers" },
      { id: "sim800l-gsm", name: "Sim800L GSM", icon: "📱", category: "drivers" },
    ],
  },
  {
    name: "COMMUNICATION",
    count: 9,
    items: [
      { id: "hc-05-bluetooth", name: "HC-05 Bluetooth", icon: "🔵", category: "communication" },
      { id: "nrf24l01", name: "NRF24L01 2.4GHz", icon: "📶", category: "communication" },
      { id: "lora-module", name: "LoRa Module", icon: "📻", category: "communication" },
      { id: "wifi-module", name: "WiFi Module", icon: "📡", category: "communication" },
    ],
  },
];

export const CONNECTION_TYPES = [
  { name: "Power", color: "#ef4444" },
  { name: "Signal", color: "#22c55e" },
  { name: "Data", color: "#3b82f6" },
  { name: "Communication", color: "#a855f7" },
  { name: "Mechanical", color: "#6b7280" },
  { name: "Safety", color: "#f59e0b" },
];
