import { create } from "zustand";
import type { Node, Edge } from "@xyflow/react";

// ─── Wire / Port Types ─────────────────────────────────────────────────────────

export type WireType = "power" | "ground" | "signal" | "data" | "pwm" | "can" | "feedback" | "safety";
export type NodeShape =
  | "raspberry-pi"
  | "arduino-uno"
  | "esp32"
  | "breadboard"
  | "ic-chip"
  | "generic-board";
export type NodeType =
  | "microcontroller"
  | "sensor"
  | "motor"
  | "power"
  | "display"
  | "module"
  | "other";

export interface Port {
  id: string;
  label: string;
  side: "top" | "bottom" | "left" | "right";
  offsetPercent: number;
}

export interface CircuitNodeData extends Record<string, unknown> {
  label: string;
  type: NodeType;
  shape: NodeShape;
  ports: Port[];
}

export interface WireData extends Record<string, unknown> {
  from: { nodeId: string; portId: string };
  to: { nodeId: string; portId: string };
  color: string;
  label: string;
  wireType: WireType;
}

export type CircuitNode = Node<CircuitNodeData>;
export type CircuitEdge = Edge<WireData>;

// ─── Wire color map ────────────────────────────────────────────────────────────

export const WIRE_COLORS: Record<WireType, string> = {
  power: "#FF4444",
  ground: "#888888",
  signal: "#4488FF",
  data: "#4488FF",
  pwm: "#4488FF",
  can: "#4488FF",
  feedback: "#00FF00",
  safety: "#FFD700",
};

// ─── API payload types ─────────────────────────────────────────────────────────

interface GenerateComponent {
  id: string;
  name: string;
  type: string;
}

interface GenerateResponse {
  nodes: Array<{
    id: string;
    label: string;
    type: NodeType;
    shape: NodeShape;
    x: number;
    y: number;
    ports: Port[];
  }>;
  wires: Array<{
    id: string;
    from: { nodeId: string; portId: string };
    to: { nodeId: string; portId: string };
    color: string;
    label: string;
    type: WireType;
  }>;
}

// ─── Demo / seed data ─────────────────────────────────────────────────────────
// Complex autonomous robot controller:
//   Raspberry Pi 4 (high-level AI master)
//     ↔ Arduino Mega (real-time motor/sensor I/O via UART)
//     ↔ ESP32       (WiFi telemetry & OTA)
//   Arduino Mega → L298N dual motor driver
//   Arduino Mega ← MPU6050 IMU       (I²C)
//   Arduino Mega ← HC-SR04 Ultrasonic (trigger/echo)
//   Raspberry Pi → SSD1306 OLED      (I²C)
//   12V Battery  → LM2596 Buck       → 5V rail → RPi / Arduino

const DEMO_NODES: CircuitNode[] = [

  // ── 12V LiPo Battery (top-left) ──────────────────────────────────────────
  {
    id: "battery",
    type: "circuitNode",
    position: { x: -60, y: -180 },
    draggable: true,
    data: {
      label: "12V LiPo Battery",
      type: "power",
      shape: "generic-board",
      ports: [
        // right side: 2 ports → 33, 67
        { id: "bat-vout", label: "12V+", side: "right", offsetPercent: 33 },
        { id: "bat-gnd",  label: "GND",  side: "right", offsetPercent: 67 },
      ],
    },
  },

  // ── LM2596 Buck Converter (top-centre) ───────────────────────────────────
  {
    id: "buck",
    type: "circuitNode",
    position: { x: 380, y: -200 },
    draggable: true,
    data: {
      label: "LM2596 Buck (5V)",
      type: "power",
      shape: "generic-board",
      ports: [
        // left side: 2 ports → 33, 67
        { id: "buck-vin",    label: "VIN", side: "left",  offsetPercent: 33 },
        { id: "buck-gnd-in", label: "GND", side: "left",  offsetPercent: 67 },
        // right side: 2 ports → 33, 67
        { id: "buck-vout",   label: "5V",  side: "right", offsetPercent: 33 },
        { id: "buck-gnd",    label: "GND", side: "right", offsetPercent: 67 },
      ],
    },
  },

  // ── Raspberry Pi 4 (centre-left) ─────────────────────────────────────────
  {
    id: "rpi",
    type: "circuitNode",
    position: { x: 120, y: 80 },
    draggable: true,
    data: {
      label: "Raspberry Pi 4",
      type: "microcontroller",
      shape: "raspberry-pi",
      ports: [
        // top side: 4 ports → 20, 40, 60, 80
        { id: "rpi-5v",   label: "5V",      side: "top",   offsetPercent: 20 },
        { id: "rpi-gnd",  label: "GND",     side: "top",   offsetPercent: 40 },
        { id: "rpi-sda",  label: "SDA",     side: "top",   offsetPercent: 60 },
        { id: "rpi-scl",  label: "SCL",     side: "top",   offsetPercent: 80 },
        // right side: 4 ports → 20, 40, 60, 80
        { id: "rpi-tx",   label: "TX",      side: "right", offsetPercent: 20 },
        { id: "rpi-rx",   label: "RX",      side: "right", offsetPercent: 40 },
        { id: "rpi-tx2",  label: "TX(ESP)", side: "right", offsetPercent: 60 },
        { id: "rpi-rx2",  label: "RX(ESP)", side: "right", offsetPercent: 80 },
        // left side: 2 ports → 33, 67
        { id: "rpi-vin",  label: "VIN",     side: "left",  offsetPercent: 33 },
        { id: "rpi-gnd2", label: "GND",     side: "left",  offsetPercent: 67 },
      ],
    },
  },

  // ── Arduino Mega (centre-right) ───────────────────────────────────────────
  {
    id: "mega",
    type: "circuitNode",
    position: { x: 720, y: 100 },
    draggable: true,
    data: {
      label: "Arduino Mega 2560",
      type: "microcontroller",
      shape: "arduino-uno",
      ports: [
        // top side: 2 ports → 33, 67
        { id: "mega-5v",   label: "5V",   side: "top",    offsetPercent: 33 },
        { id: "mega-gnd",  label: "GND",  side: "top",    offsetPercent: 67 },
        // left side: 4 ports → 20, 40, 60, 80
        { id: "mega-rx0",  label: "RX0",  side: "left",   offsetPercent: 20 },
        { id: "mega-tx0",  label: "TX0",  side: "left",   offsetPercent: 40 },
        { id: "mega-sda",  label: "SDA",  side: "left",   offsetPercent: 60 },
        { id: "mega-scl",  label: "SCL",  side: "left",   offsetPercent: 80 },
        // right side: 6 ports → ~14, 29, 43, 57, 71, 86
        { id: "mega-d4",   label: "D4",   side: "right",  offsetPercent: 14 },
        { id: "mega-d5",   label: "D5~",  side: "right",  offsetPercent: 29 },
        { id: "mega-d6",   label: "D6~",  side: "right",  offsetPercent: 43 },
        { id: "mega-d7",   label: "D7",   side: "right",  offsetPercent: 57 },
        { id: "mega-d8",   label: "D8~",  side: "right",  offsetPercent: 71 },
        { id: "mega-d9",   label: "D9~",  side: "right",  offsetPercent: 86 },
        // bottom side: 3 ports → 25, 50, 75
        { id: "mega-trig", label: "D11",  side: "bottom", offsetPercent: 25 },
        { id: "mega-echo", label: "D12",  side: "bottom", offsetPercent: 50 },
        { id: "mega-vin",  label: "VIN",  side: "bottom", offsetPercent: 75 },
      ],
    },
  },

  // ── ESP32 WiFi Module (top-right) ─────────────────────────────────────────
  {
    id: "esp32",
    type: "circuitNode",
    position: { x: 780, y: -200 },
    draggable: true,
    data: {
      label: "ESP32 (WiFi/BT)",
      type: "module",
      shape: "esp32",
      ports: [
        // top side: 2 ports → 33, 67
        { id: "esp-vcc", label: "VCC", side: "top",  offsetPercent: 33 },
        { id: "esp-gnd", label: "GND", side: "top",  offsetPercent: 67 },
        // left side: 2 ports → 33, 67
        { id: "esp-rx",  label: "RX",  side: "left", offsetPercent: 33 },
        { id: "esp-tx",  label: "TX",  side: "left", offsetPercent: 67 },
      ],
    },
  },

  // ── L298N Dual Motor Driver (far-right) ───────────────────────────────────
  {
    id: "l298n",
    type: "circuitNode",
    position: { x: 1160, y: 120 },
    draggable: true,
    data: {
      label: "L298N Motor Driver",
      type: "module",
      shape: "ic-chip",
      ports: [
        // top side: 3 ports → 25, 50, 75
        { id: "l298n-12v", label: "12V",  side: "top",   offsetPercent: 25 },
        { id: "l298n-vcc", label: "5V",   side: "top",   offsetPercent: 50 },
        { id: "l298n-gnd", label: "GND",  side: "top",   offsetPercent: 75 },
        // left side: 6 ports → ~14, 29, 43, 57, 71, 86
        { id: "l298n-in1", label: "IN1",  side: "left",  offsetPercent: 14 },
        { id: "l298n-in2", label: "IN2",  side: "left",  offsetPercent: 29 },
        { id: "l298n-ena", label: "ENA",  side: "left",  offsetPercent: 43 },
        { id: "l298n-in3", label: "IN3",  side: "left",  offsetPercent: 57 },
        { id: "l298n-in4", label: "IN4",  side: "left",  offsetPercent: 71 },
        { id: "l298n-enb", label: "ENB",  side: "left",  offsetPercent: 86 },
        // right side: 4 ports → 20, 40, 60, 80
        { id: "l298n-ma1", label: "M-A+", side: "right", offsetPercent: 20 },
        { id: "l298n-ma2", label: "M-A-", side: "right", offsetPercent: 40 },
        { id: "l298n-mb1", label: "M-B+", side: "right", offsetPercent: 60 },
        { id: "l298n-mb2", label: "M-B-", side: "right", offsetPercent: 80 },
      ],
    },
  },

  // ── MPU6050 IMU (bottom-centre) ───────────────────────────────────────────
  {
    id: "mpu6050",
    type: "circuitNode",
    position: { x: 660, y: 480 },
    draggable: true,
    data: {
      label: "MPU6050 IMU",
      type: "sensor",
      shape: "generic-board",
      ports: [
        // top side: 2 ports → 33, 67
        { id: "mpu-vcc", label: "VCC", side: "top",   offsetPercent: 33 },
        { id: "mpu-gnd", label: "GND", side: "top",   offsetPercent: 67 },
        // left side: 2 ports → 33, 67
        { id: "mpu-sda", label: "SDA", side: "left",  offsetPercent: 33 },
        { id: "mpu-scl", label: "SCL", side: "left",  offsetPercent: 67 },
        // right side: 1 port → 50
        { id: "mpu-int", label: "INT", side: "right", offsetPercent: 50 },
      ],
    },
  },

  // ── HC-SR04 Ultrasonic (bottom-right) ─────────────────────────────────────
  {
    id: "hcsr04",
    type: "circuitNode",
    position: { x: 1040, y: 500 },
    draggable: true,
    data: {
      label: "HC-SR04 Ultrasonic",
      type: "sensor",
      shape: "generic-board",
      ports: [
        // top side: 2 ports → 33, 67
        { id: "hc-vcc",  label: "VCC",  side: "top",  offsetPercent: 33 },
        { id: "hc-gnd",  label: "GND",  side: "top",  offsetPercent: 67 },
        // left side: 2 ports → 33, 67
        { id: "hc-trig", label: "TRIG", side: "left", offsetPercent: 33 },
        { id: "hc-echo", label: "ECHO", side: "left", offsetPercent: 67 },
      ],
    },
  },

  // ── SSD1306 OLED Display (bottom-left) ────────────────────────────────────
  {
    id: "oled",
    type: "circuitNode",
    position: { x: 60, y: 480 },
    draggable: true,
    data: {
      label: "SSD1306 OLED 128×64",
      type: "display",
      shape: "generic-board",
      ports: [
        // top side: 2 ports → 33, 67
        { id: "oled-vcc", label: "VCC", side: "top",   offsetPercent: 33 },
        { id: "oled-gnd", label: "GND", side: "top",   offsetPercent: 67 },
        // right side: 2 ports → 33, 67
        { id: "oled-sda", label: "SDA", side: "right", offsetPercent: 33 },
        { id: "oled-scl", label: "SCL", side: "right", offsetPercent: 67 },
      ],
    },
  },
];

function _wire(
  id: string,
  fromNode: string,
  fromPort: string,
  toNode: string,
  toPort: string,
  wt: WireType,
  lbl: string
): CircuitEdge {
  return {
    id,
    source: fromNode,
    target: toNode,
    sourceHandle: fromPort,
    targetHandle: toPort,
    type: "circuitWire",
    label: lbl,
    data: {
      from: { nodeId: fromNode, portId: fromPort },
      to:   { nodeId: toNode,   portId: toPort   },
      color: WIRE_COLORS[wt],
      label: lbl,
      wireType: wt,
    },
    style: { stroke: WIRE_COLORS[wt], strokeWidth: 2 },
  };
}

const DEMO_EDGES: CircuitEdge[] = [
  // ── 12V Battery → Buck converter ─────────────────────────────────────────
  _wire("w01", "battery", "bat-vout",    "buck",    "buck-vin",     "power",  "12V"),
  _wire("w02", "battery", "bat-gnd",     "buck",    "buck-gnd-in",  "ground", "GND"),

  // ── 12V Battery → L298N motor power ──────────────────────────────────────
  _wire("w03", "battery", "bat-vout",    "l298n",   "l298n-12v",    "power",  "12V"),
  _wire("w04", "battery", "bat-gnd",     "l298n",   "l298n-gnd",    "ground", "GND"),

  // ── Buck 5V → Raspberry Pi ────────────────────────────────────────────────
  _wire("w05", "buck",    "buck-vout",   "rpi",     "rpi-vin",      "power",  "5V"),
  _wire("w06", "buck",    "buck-gnd",    "rpi",     "rpi-gnd2",     "ground", "GND"),

  // ── Buck 5V → Arduino Mega ────────────────────────────────────────────────
  _wire("w07", "buck",    "buck-vout",   "mega",    "mega-vin",     "power",  "5V"),
  _wire("w08", "mega",    "mega-gnd",    "l298n",   "l298n-vcc",    "power",  "5V logic"),

  // ── RPi ↔ Arduino Mega UART (serial bridge) ───────────────────────────────
  _wire("w09", "rpi",     "rpi-tx",      "mega",    "mega-rx0",     "data",   "UART TX→RX"),
  _wire("w10", "mega",    "mega-tx0",    "rpi",     "rpi-rx",       "data",   "UART RX←TX"),

  // ── RPi ↔ ESP32 UART (WiFi telemetry) ────────────────────────────────────
  _wire("w11", "rpi",     "rpi-tx2",     "esp32",   "esp-rx",       "data",   "TX→RX"),
  _wire("w12", "esp32",   "esp-tx",      "rpi",     "rpi-rx2",      "data",   "RX←TX"),

  // ── Buck 5V → ESP32 power ─────────────────────────────────────────────────
  _wire("w13", "buck",    "buck-vout",   "esp32",   "esp-vcc",      "power",  "3.3V"),
  _wire("w14", "buck",    "buck-gnd",    "esp32",   "esp-gnd",      "ground", "GND"),

  // ── RPi → OLED (I²C) ──────────────────────────────────────────────────────
  _wire("w15", "rpi",     "rpi-5v",      "oled",    "oled-vcc",     "power",  "3.3V"),
  _wire("w16", "rpi",     "rpi-gnd",     "oled",    "oled-gnd",     "ground", "GND"),
  _wire("w17", "rpi",     "rpi-sda",     "oled",    "oled-sda",     "data",   "I²C SDA"),
  _wire("w18", "rpi",     "rpi-scl",     "oled",    "oled-scl",     "data",   "I²C SCL"),

  // ── Arduino Mega ↔ MPU6050 IMU (I²C) ─────────────────────────────────────
  _wire("w19", "mega",    "mega-5v",     "mpu6050", "mpu-vcc",      "power",  "3.3V"),
  _wire("w20", "mega",    "mega-gnd",    "mpu6050", "mpu-gnd",      "ground", "GND"),
  _wire("w21", "mega",    "mega-sda",    "mpu6050", "mpu-sda",      "data",   "I²C SDA"),
  _wire("w22", "mega",    "mega-scl",    "mpu6050", "mpu-scl",      "data",   "I²C SCL"),
  _wire("w23", "mpu6050", "mpu-int",     "mega",    "mega-d4",      "signal", "INT"),

  // ── Arduino Mega ↔ HC-SR04 Ultrasonic ────────────────────────────────────
  _wire("w24", "mega",    "mega-5v",     "hcsr04",  "hc-vcc",       "power",  "5V"),
  _wire("w25", "mega",    "mega-gnd",    "hcsr04",  "hc-gnd",       "ground", "GND"),
  _wire("w26", "mega",    "mega-trig",   "hcsr04",  "hc-trig",      "signal", "TRIG"),
  _wire("w27", "hcsr04",  "hc-echo",     "mega",    "mega-echo",    "signal", "ECHO"),

  // ── Arduino Mega PWM → L298N motor control ────────────────────────────────
  _wire("w28", "mega",    "mega-d5",     "l298n",   "l298n-ena",    "pwm",    "ENA~"),
  _wire("w29", "mega",    "mega-d6",     "l298n",   "l298n-enb",    "pwm",    "ENB~"),
  _wire("w30", "mega",    "mega-d7",     "l298n",   "l298n-in1",    "signal", "IN1"),
  _wire("w31", "mega",    "mega-d8",     "l298n",   "l298n-in2",    "signal", "IN2"),
  _wire("w32", "mega",    "mega-d9",     "l298n",   "l298n-in3",    "signal", "IN3"),
  _wire("w33", "mega",    "mega-d4",     "l298n",   "l298n-in4",    "signal", "IN4"),
];

// ─── Store ────────────────────────────────────────────────────────────────────

interface ConnectionStore {
  // React Flow state
  nodes: CircuitNode[];
  edges: CircuitEdge[];

  // UI state
  selectedEdgeId: string | null;
  sidebarOpen: boolean;
  isGenerating: boolean;
  prompt: string;
  error: string | null;

  // Actions
  setNodes: (nodes: CircuitNode[] | ((prev: CircuitNode[]) => CircuitNode[])) => void;
  setEdges: (edges: CircuitEdge[]) => void;
  setPrompt: (prompt: string) => void;
  setSelectedEdge: (id: string | null) => void;
  setSidebarOpen: (open: boolean) => void;

  updateEdge: (
    id: string,
    patch: Partial<{
      from: { nodeId: string; portId: string };
      to: { nodeId: string; portId: string };
      wireType: WireType;
      label: string;
    }>
  ) => void;
  deleteEdge: (id: string) => void;
  addEdge: (edge: CircuitEdge) => void;

  generate: (components: GenerateComponent[], prompt: string) => Promise<void>;
  loadDesignData: (designData: any) => void;
}

export const useConnectionStore = create<ConnectionStore>((set, get) => ({
  nodes: DEMO_NODES,
  edges: DEMO_EDGES,
  selectedEdgeId: null,
  sidebarOpen: false,
  isGenerating: false,
  prompt: "Raspberry Pi 4 + Arduino Mega + ESP32 WiFi + L298N motors + MPU6050 IMU + HC-SR04 + OLED display",
  error: null,

  loadDesignData: (designData) => {
    if (!designData) return;

    function inferShape(name: string, role: string): NodeShape {
      const n = (name + " " + role).toLowerCase();
      if (n.includes("raspberry") || n.includes("rpi") || n.includes("sbc") || n.includes("jetson")) return "raspberry-pi";
      if (n.includes("arduino") || n.includes("mega") || n.includes("uno") || n.includes("nano")) return "arduino-uno";
      if (n.includes("esp32") || n.includes("esp8266") || n.includes("node-mcu")) return "esp32";
      if (n.includes("breadboard")) return "breadboard";
      if (n.includes("driver") || n.includes("h-bridge") || n.includes("mosfet") || n.includes("ic ") || n.includes("chip")) return "ic-chip";
      return "generic-board";
    }

    function inferType(name: string, role: string): NodeType {
      const n = (name + " " + role).toLowerCase();
      if (n.includes("controller") || n.includes("mcu") || n.includes("arduino") || n.includes("raspberry") || n.includes("sbc")) return "microcontroller";
      if (n.includes("sensor") || n.includes("imu") || n.includes("lidar") || n.includes("camera") || n.includes("encoder")) return "sensor";
      if (n.includes("motor") || n.includes("actuator") || n.includes("servo") || n.includes("solenoid") || n.includes("pump")) return "motor";
      if (n.includes("power") || n.includes("battery") || n.includes("supply") || n.includes("buck") || n.includes("lipo")) return "power";
      if (n.includes("display") || n.includes("lcd") || n.includes("oled") || n.includes("screen")) return "display";
      if (n.includes("wifi") || n.includes("bluetooth") || n.includes("telemetry") || n.includes("transceiver") || n.includes("module")) return "module";
      return "other";
    }

    function getPortsForInterface(compId: string, interfaceStr: string): Port[] {
      const ports: Port[] = [];
      ports.push({ id: `${compId}-vcc`, label: "VCC", side: "top", offsetPercent: 30 });
      ports.push({ id: `${compId}-gnd`, label: "GND", side: "top", offsetPercent: 70 });
      
      const cleanInterface = (interfaceStr || "").toUpperCase();
      if (cleanInterface.includes("I2C")) {
        ports.push({ id: `${compId}-sda`, label: "SDA", side: "left", offsetPercent: 40 });
        ports.push({ id: `${compId}-scl`, label: "SCL", side: "left", offsetPercent: 60 });
      } else if (cleanInterface.includes("SPI")) {
        ports.push({ id: `${compId}-mosi`, label: "MOSI", side: "left", offsetPercent: 20 });
        ports.push({ id: `${compId}-miso`, label: "MISO", side: "left", offsetPercent: 40 });
        ports.push({ id: `${compId}-sck`, label: "SCK", side: "left", offsetPercent: 60 });
        ports.push({ id: `${compId}-cs`, label: "CS", side: "left", offsetPercent: 80 });
      } else if (cleanInterface.includes("CAN")) {
        ports.push({ id: `${compId}-canh`, label: "CANH", side: "left", offsetPercent: 40 });
        ports.push({ id: `${compId}-canl`, label: "CANL", side: "left", offsetPercent: 60 });
      } else if (cleanInterface.includes("UART") || cleanInterface.includes("RS485")) {
        ports.push({ id: `${compId}-tx`, label: "TX", side: "left", offsetPercent: 40 });
        ports.push({ id: `${compId}-rx`, label: "RX", side: "left", offsetPercent: 60 });
      } else if (cleanInterface.includes("PWM")) {
        ports.push({ id: `${compId}-pwm`, label: "PWM", side: "right", offsetPercent: 50 });
      } else {
        ports.push({ id: `${compId}-io1`, label: "IO1", side: "right", offsetPercent: 30 });
        ports.push({ id: `${compId}-io2`, label: "IO2", side: "right", offsetPercent: 70 });
      }
      return ports;
    }

    const rowHeights: Record<NodeType, number> = {
      power: -200,
      microcontroller: 80,
      module: 80,
      sensor: 400,
      motor: 400,
      display: 400,
      other: 400
    };

    const rowCounts: Record<NodeType, number> = {
      power: 0,
      microcontroller: 0,
      module: 0,
      sensor: 0,
      motor: 0,
      display: 0,
      other: 0
    };

    const rfNodes: CircuitNode[] = [];
    const designSubsystems = designData.subsystems || [];

    designSubsystems.forEach((sub: any) => {
      const components = sub.components || [];
      components.forEach((comp: any) => {
        const shape = inferShape(comp.name, comp.role || "");
        const type = inferType(comp.name, comp.role || "");
        const ports = getPortsForInterface(comp.id, comp.interface || "");

        const rowCount = rowCounts[type] || 0;
        rowCounts[type] = rowCount + 1;

        const x = 80 + rowCount * 300;
        const y = rowHeights[type] || 400;

        rfNodes.push({
          id: comp.id,
          type: "circuitNode",
          position: { x, y },
          draggable: true,
          data: {
            label: comp.name,
            type,
            shape,
            ports,
          }
        });
      });
    });

    const connections = designData.connections || [];
    const rfEdges: CircuitEdge[] = connections.map((conn: any, idx: number) => {
      const fromNodeId = conn.from;
      const toNodeId = conn.to;
      const protocol = (conn.protocol || "signal").toUpperCase();
      
      let wireType: WireType = "signal";
      if (protocol.includes("I2C") || protocol.includes("UART") || protocol.includes("SPI") || protocol.includes("RS485")) {
        wireType = "data";
      } else if (protocol.includes("CAN")) {
        wireType = "can";
      } else if (protocol.includes("PWM")) {
        wireType = "pwm";
      } else if (protocol.includes("DC") || protocol.includes("POWER")) {
        wireType = "power";
      } else if (protocol.includes("SAFETY")) {
        wireType = "safety";
      } else if (protocol.includes("FEEDBACK")) {
        wireType = "feedback";
      }

      let srcPort = `${fromNodeId}-io1`;
      let tgtPort = `${toNodeId}-io1`;
      
      const fromNode = rfNodes.find(n => n.id === fromNodeId);
      const toNode = rfNodes.find(n => n.id === toNodeId);
      
      if (fromNode && fromNode.data.ports.length > 0) {
        const match = fromNode.data.ports.find((p: any) => 
          p.id.includes("sda") || p.id.includes("tx") || p.id.includes("can") || p.id.includes("pwm") || p.id.includes("io1")
        );
        srcPort = match ? match.id : fromNode.data.ports[0].id;
      }
      if (toNode && toNode.data.ports.length > 0) {
        const match = toNode.data.ports.find((p: any) => 
          p.id.includes("sda") || p.id.includes("rx") || p.id.includes("can") || p.id.includes("pwm") || p.id.includes("io1")
        );
        tgtPort = match ? match.id : toNode.data.ports[0].id;
      }
      
      if (wireType === "power") {
        const srcVcc = `${fromNodeId}-vcc`;
        const tgtVcc = `${toNodeId}-vcc`;
        if (fromNode?.data.ports.some(p => p.id === srcVcc)) srcPort = srcVcc;
        if (toNode?.data.ports.some(p => p.id === tgtVcc)) tgtPort = tgtVcc;
      }

      return {
        id: `wire-design-${idx}-${Date.now()}`,
        source: fromNodeId,
        target: toNodeId,
        sourceHandle: srcPort,
        targetHandle: tgtPort,
        type: "circuitWire",
        label: conn.protocol || conn.relation || "signal",
        data: {
          from: { nodeId: fromNodeId, portId: srcPort },
          to: { nodeId: toNodeId, portId: tgtPort },
          color: WIRE_COLORS[wireType],
          label: conn.protocol || conn.relation || "signal",
          wireType
        },
        style: {
          stroke: WIRE_COLORS[wireType],
          strokeWidth: 2
        }
      };
    });

    set({ nodes: rfNodes, edges: rfEdges, error: null, isGenerating: false });
  },

  setNodes: (nodesOrUpdater) =>
    set((state) => ({
      nodes:
        typeof nodesOrUpdater === "function"
          ? nodesOrUpdater(state.nodes)
          : nodesOrUpdater,
    })),
  setEdges: (edges) => set({ edges }),
  setPrompt: (prompt) => set({ prompt }),
  setSelectedEdge: (id) =>
    set({ selectedEdgeId: id, sidebarOpen: id !== null }),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  updateEdge: (id, patch) => {
    const edges = get().edges.map((e) => {
      if (e.id !== id) return e;
      const data = { ...(e.data as WireData) };
      if (patch.from) data.from = patch.from;
      if (patch.to) data.to = patch.to;
      if (patch.wireType) {
        data.wireType = patch.wireType;
        data.color = WIRE_COLORS[patch.wireType];
      }
      if (patch.label !== undefined) data.label = patch.label;
      return {
        ...e,
        data,
        style: { ...e.style, stroke: data.color },
        label: data.label,
      };
    });
    set({ edges });
  },

  deleteEdge: (id) => {
    set({
      edges: get().edges.filter((e) => e.id !== id),
      selectedEdgeId: null,
      sidebarOpen: false,
    });
  },

  addEdge: (edge) => {
    set({ edges: [...get().edges, edge] });
  },

  generate: async (components, prompt) => {
    set({ isGenerating: true, error: null });
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/connections/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ components, prompt }),
      });

      if (!res.ok) throw new Error(`API error ${res.status}`);

      const data: GenerateResponse = await res.json();

      // Convert API response → React Flow nodes
      const rfNodes: CircuitNode[] = data.nodes.map((n) => ({
        id: n.id,
        type: "circuitNode",
        position: { x: n.x, y: n.y },
        data: {
          label: n.label,
          type: n.type,
          shape: n.shape,
          ports: n.ports,
        },
        draggable: true,
      }));

      // Convert API response → React Flow edges
      const rfEdges: CircuitEdge[] = data.wires.map((w) => ({
        id: w.id,
        source: w.from.nodeId,
        target: w.to.nodeId,
        sourceHandle: w.from.portId,
        targetHandle: w.to.portId,
        type: "circuitWire",
        label: w.label,
        data: {
          from: w.from,
          to: w.to,
          color: w.color,
          label: w.label,
          wireType: w.type,
        },
        style: {
          stroke: w.color,
          strokeWidth: 2,
        },
        markerEnd: undefined,
        animated: false,
      }));

      set({ nodes: rfNodes, edges: rfEdges });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      set({ error: msg });
    } finally {
      set({ isGenerating: false });
    }
  },
}));
