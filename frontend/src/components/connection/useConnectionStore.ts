import { create } from "zustand";
import type { Node, Edge } from "@xyflow/react";
import dagre from "dagre";

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
  | "driver"
  | "safety"
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
  ground: "#444444",
  signal: "#FFD700",
  data: "#4488FF",
  pwm: "#4488FF",
  can: "#4488FF",
  feedback: "#00FF00",
  safety: "#FFD700",
};

const toNodeId = (name: string, existingIds: Set<string>): string => {
  let base = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_|_$/g, '') || 'component'

  if (!existingIds.has(base)) {
    existingIds.add(base)
    return base
  }

  // Collision — append a suffix derived from the original name
  const suffix = name
    .split('')
    .reduce((acc, c) => (acc * 31 + c.charCodeAt(0)) & 0xffff, 0)
    .toString(36)

  const unique = `${base}_${suffix}`
  if (!existingIds.has(unique)) {
    existingIds.add(unique)
    return unique
  }

  // If the base + suffix also collides, append a counter suffix until unique
  let counter = 1
  let candidate = `${unique}_${counter}`
  while (existingIds.has(candidate)) {
    counter++
    candidate = `${unique}_${counter}`
  }
  existingIds.add(candidate)
  return candidate
}

const normalizeNodeId = (name: string): string => toNodeId(name, new Set());

// ─── API payload types ─────────────────────────────────────────────────────────

interface GenerateComponent {
  id: string;
  name: string;
  type: string;
}

interface GenerateResponse {
  erc_report?: string;
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
    style: { stroke: WIRE_COLORS[wt], strokeWidth: 3 },
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
  ercReport: string | null;

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

  generate: (components: GenerateComponent[], prompt: string, subsystems?: any) => Promise<void>;
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
  ercReport: null,

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
      if (n.includes("controller") || n.includes("mcu") || n.includes("arduino") || n.includes("raspberry") || n.includes("sbc") || n.includes("plc")) return "microcontroller";
      if (n.includes("driver") || n.includes("relay") || n.includes("contactor") || (n.includes("controller") && n.includes("motor"))) return "driver";
      if (n.includes("sensor") || n.includes("imu") || n.includes("lidar") || n.includes("camera") || n.includes("encoder") || n.includes("switch")) return "sensor";
      if (n.includes("motor") || n.includes("actuator") || n.includes("servo") || n.includes("solenoid") || n.includes("pump") || n.includes("wheel") || n.includes("gripper")) return "motor";
      if (n.includes("power") || n.includes("battery") || n.includes("supply") || n.includes("buck") || n.includes("lipo") || n.includes("ground") || n.includes("psu") || n.includes("fuse")) return "power";
      if (n.includes("stop") || n.includes("safety") || n.includes("estop")) return "safety";
      if (n.includes("display") || n.includes("lcd") || n.includes("oled") || n.includes("screen")) return "display";
      if (n.includes("wifi") || n.includes("bluetooth") || n.includes("telemetry") || n.includes("transceiver") || n.includes("module")) return "module";
      return "other";
    }

    const rowHeights: Record<NodeType, number> = {
      power: 200,
      safety: -100,
      sensor: -100,
      microcontroller: 200,
      module: 200,
      driver: 500,
      motor: 800,
      display: -100,
      other: 200
    };

    const rowCounts: Record<NodeType, number> = {
      power: 0,
      safety: 0,
      microcontroller: 0,
      module: 0,
      sensor: 0,
      driver: 0,
      motor: 0,
      display: 0,
      other: 0
    };

    const rawConnections = designData.connections || [];
    const connections = rawConnections.filter((conn: any) => {
        const relation = (conn.relation || "").toLowerCase();
        const protocol = (conn.protocol || "").toLowerCase();
        return relation !== "mounted_on" && relation !== "attached_to" && relation !== "fastened_to" && protocol !== "mechanical";
    });
    
    // Pass 1: Collect required ports for each component from the explicit connections
    const collectedPorts = new Map<string, Set<string>>();
    const normalizeId = (id: any) => id ? id.toString().toLowerCase().replace(/\s+/g, '_') : "";
    
    // Create a map of all component IDs to components to do fuzzy matching BEFORE collecting ports
    const validCompIds = new Map<string, any>();
    const designSubsystems = designData.subsystems || [];
    designSubsystems.forEach((sub: any) => {
      (sub.components || []).forEach((comp: any) => {
        validCompIds.set(normalizeId(comp.id), comp);
      });
    });

    const resolvedConnections = connections.map((conn: any) => {
      let fromId = normalizeId(conn.from);
      let toId = normalizeId(conn.to);
      
      if (!validCompIds.has(fromId)) {
        const fuzzyId = Array.from(validCompIds.keys()).find(k => k.includes(fromId) || validCompIds.get(k).name.toLowerCase().includes(fromId));
        if (fuzzyId) fromId = fuzzyId;
      }
      if (!validCompIds.has(toId)) {
        const fuzzyId = Array.from(validCompIds.keys()).find(k => k.includes(toId) || validCompIds.get(k).name.toLowerCase().includes(toId));
        if (fuzzyId) toId = fuzzyId;
      }
      
      return { ...conn, resolvedFrom: fromId, resolvedTo: toId };
    });

    resolvedConnections.forEach((conn: any) => {
      const fId = conn.resolvedFrom;
      const tId = conn.resolvedTo;
      const fPort = conn.from_port || "IO1";
      const tPort = conn.to_port || "IO1";
      
      if (fId) {
        if (!collectedPorts.has(fId)) collectedPorts.set(fId, new Set());
        collectedPorts.get(fId)!.add(fPort);
      }
      if (tId) {
        if (!collectedPorts.has(tId)) collectedPorts.set(tId, new Set());
        collectedPorts.get(tId)!.add(tPort);
      }
    });

    // Helper to format an ID for a port (React Flow wants strict uniqueness per node if desired, but we scope by port label)
    const getPortId = (compId: string, label: string) => `${compId}-${label.replace(/\s+/g, "_").toLowerCase()}`;

    const rfNodes: CircuitNode[] = [];
    
    designSubsystems.forEach((sub: any) => {
      const components = sub.components || [];
      components.forEach((comp: any) => {
        const compId = normalizeId(comp.id) || `comp-${Math.random().toString(36).substr(2,9)}`;
        const isConnected = collectedPorts.has(compId);
        
        // Skip purely mechanical components (like brackets, mounts) UNLESS they have electrical connections
        const isMechanical = (comp.interface || "").toLowerCase().includes("mechanical") || 
                             (comp.voltage || "").toLowerCase() === "n/a" || 
                             (comp.role || "").toLowerCase().includes("bracket") || 
                             (comp.role || "").toLowerCase().includes("mount") || 
                             (comp.name || "").toLowerCase().includes("bracket");
        
        if (isMechanical && !isConnected) {
            return;
        }

        const shape = inferShape(comp.name, comp.role || "");
        const type = inferType(comp.name, comp.role || "");

        // Generate port layouts based on collected dynamic ports
        const nodePorts: Port[] = [];
        const portLabels = Array.from(collectedPorts.get(compId) || []);
        
        // Ensure VCC and GND exist
        if (!portLabels.some(l => l.toUpperCase() === "VCC" || l.toUpperCase() === "VIN" || l.toUpperCase() === "5V")) portLabels.push("VCC");
        if (!portLabels.some(l => l.toUpperCase() === "GND")) portLabels.push("GND");

        // Categorize into sides
        const topPorts: string[] = [];
        const leftPorts: string[] = [];
        const rightPorts: string[] = [];
        const bottomPorts: string[] = [];

        portLabels.forEach(lbl => {
            const L = lbl.toUpperCase();
            if (L.includes("VCC") || L.includes("VIN") || L.includes("5V") || L.includes("3V") || L.includes("GND") || L.includes("PWR")) {
                topPorts.push(lbl);
            } else if (L.includes("TX") || L.includes("RX") || L.includes("SDA") || L.includes("SCL") || L.includes("MISO") || L.includes("MOSI") || L.includes("SCK") || L.includes("CS") || L.includes("IN") || L.includes("ENA") || L.includes("ENB")) {
                leftPorts.push(lbl);
            } else {
                rightPorts.push(lbl);
            }
        });

        const distribute = (labels: string[], side: "top"|"bottom"|"left"|"right") => {
            labels.forEach((lbl, idx) => {
                const offset = (100 / (labels.length + 1)) * (idx + 1);
                nodePorts.push({
                    id: getPortId(compId, lbl),
                    label: lbl,
                    side,
                    offsetPercent: Math.round(offset)
                });
            });
        };

        distribute(topPorts, "top");
        distribute(leftPorts, "left");
        distribute(rightPorts, "right");
        distribute(bottomPorts, "bottom");
        rfNodes.push({
          id: compId,
          type: "circuitNode",
          position: { x: 0, y: 0 },
          draggable: true,
          data: {
            label: comp.name,
            type,
            shape,
            ports: nodePorts,
          }
        });
      });
    });

    const rfEdges: CircuitEdge[] = [];
    resolvedConnections.forEach((conn: any, idx: number) => {
      const fromNodeId = conn.resolvedFrom;
      const toNodeId = conn.resolvedTo;

      if (!rfNodes.some(n => n.id === fromNodeId) || !rfNodes.some(n => n.id === toNodeId)) {
        return; // skip if nodes were filtered out (e.g. mechanical) or missing
      }

      const fPortLabel = conn.from_port || "IO1";
      const tPortLabel = conn.to_port || "IO1";
      
      let wireType: WireType = "signal";
      if (conn.wire_type && WIRE_COLORS[conn.wire_type as WireType]) {
        wireType = conn.wire_type as WireType;
      } else {
        const protocol = (conn.protocol || "signal").toUpperCase();
        if (protocol.includes("I2C") || protocol.includes("UART") || protocol.includes("SPI") || protocol.includes("RS485")) {
          wireType = "data";
        } else if (protocol.includes("CAN")) {
          wireType = "can";
        } else if (protocol.includes("PWM")) {
          wireType = "pwm";
        } else if (protocol.includes("DC") || protocol.includes("POWER") || fPortLabel.toUpperCase().includes("VCC") || fPortLabel.toUpperCase().includes("GND")) {
          wireType = "power";
        }
      }

      const srcPortId = getPortId(fromNodeId, fPortLabel);
      const tgtPortId = getPortId(toNodeId, tPortLabel);

      rfEdges.push({
        id: `wire-design-${idx}-${Date.now()}`,
        source: fromNodeId,
        target: toNodeId,
        sourceHandle: srcPortId,
        targetHandle: tgtPortId,
        type: "circuitWire",
        label: conn.protocol || conn.relation || "signal",
        data: {
          from: { nodeId: fromNodeId, portId: srcPortId },
          to: { nodeId: toNodeId, portId: tgtPortId },
          color: WIRE_COLORS[wireType],
          label: conn.protocol || conn.relation || "signal",
          wireType
        },
        style: {
          stroke: WIRE_COLORS[wireType],
          strokeWidth: 2
        },
        animated: false
      });
    });

    // Apply Dagre auto-layout with tighter spacing to keep components closer
    const g = new dagre.graphlib.Graph();
    g.setGraph({ rankdir: "TB", nodesep: 150, ranksep: 200, marginx: 50, marginy: 50 });
    g.setDefaultEdgeLabel(() => ({}));

    rfNodes.forEach((node) => {
      g.setNode(node.id, { width: 260, height: 200 });
    });

    rfEdges.forEach((edge) => {
      g.setEdge(edge.source, edge.target);
    });

    dagre.layout(g);

    rfNodes.forEach((node) => {
      const nodeWithPosition = g.node(node.id);
      if (nodeWithPosition) {
        node.position = {
          x: nodeWithPosition.x - 110,
          y: nodeWithPosition.y - 75,
        };
      }
    });

    const loadedComponentNames = designSubsystems.flatMap((sub: any) =>
      (sub.components || []).map((c: any) => c.name)
    ).filter(Boolean);
    const newPrompt = loadedComponentNames.length > 0 ? loadedComponentNames.join(" + ") : get().prompt;

    set({ nodes: rfNodes, edges: rfEdges, error: null, isGenerating: false, prompt: newPrompt });
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

  generate: async (components, prompt, subsystems) => {
    set({ isGenerating: true, error: null, ercReport: null, nodes: [], edges: [] });
    try {
      const payload = { components, prompt, subsystems };
      let res: Response | null = null;
      let retries = 3;
      while (retries > 0) {
        try {
          res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/connections/generate`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "ngrok-skip-browser-warning": "true"
            },
            body: JSON.stringify(payload),
          });
          if (res.ok) break;
        } catch (e) {
          if (retries === 1) throw e;
        }
        retries--;
        await new Promise(r => setTimeout(r, 3000)); // wait 3s before retry
      }

      if (!res || !res.ok) {
        const errText = res ? await res.text() : "Connection refused (backend starting?)";
        throw new Error(errText);
      }

      const data: GenerateResponse = await res.json();

      // Convert API response → React Flow nodes
      const rfNodes: CircuitNode[] = data.nodes.map((n) => ({
        id: n.id.toString().toLowerCase().replace(/\s+/g, '_'),
        type: "circuitNode",
        position: { x: n.x, y: n.y },
        data: {
          label: n.label,
          type: n.type,
          shape: n.shape,
          ports: n.ports.map((port) => ({
            ...port,
            id: port.id.toString().toLowerCase().replace(/\s+/g, '_')
          })),
        },
        draggable: true,
      }));

      // Convert API response → React Flow edges
      const rfEdges: CircuitEdge[] = data.wires.map((w) => {
        const fromNodeId = w.from.nodeId.toString().toLowerCase().replace(/\s+/g, '_');
        const toNodeId = w.to.nodeId.toString().toLowerCase().replace(/\s+/g, '_');
        const fromPortId = w.from.portId.toString().toLowerCase().replace(/\s+/g, '_');
        const toPortId = w.to.portId.toString().toLowerCase().replace(/\s+/g, '_');

        const fromNodeExists = rfNodes.find(n => n.id === fromNodeId);
        const toNodeExists = rfNodes.find(n => n.id === toNodeId);
        if (!fromNodeExists) {
          console.warn(`Generated edge references non-existent source node ID: ${fromNodeId}`);
        }
        if (!toNodeExists) {
          console.warn(`Generated edge references non-existent target node ID: ${toNodeId}`);
        }

        // Force green color for sensor feedback wires if LLM missed it
        let finalColor = w.color;
        let finalType = w.type;
        
        const isSensorNode = (n: any) => {
          if (!n) return false;
          const str = (n.data.type + " " + n.data.label + " " + n.id).toLowerCase();
          return str.includes("sensor") || str.includes("feedback") || str.includes("ultrasonic") || str.includes("camera") || str.includes("encoder") || str.includes("imu") || str.includes("switch") || str.includes("limit") || str.includes("hall") || str.includes("potentiometer");
        };

        if (isSensorNode(fromNodeExists) || isSensorNode(toNodeExists) || w.type === "feedback" || w.label.toLowerCase().includes("feedback") || w.label.toLowerCase().includes("sensor")) {
          finalColor = "#00FF00";
          finalType = "feedback";
        }

        return {
          id: w.id,
          source: fromNodeId,
          target: toNodeId,
          sourceHandle: fromPortId,
          targetHandle: toPortId,
          type: "circuitWire",
          label: w.label,
          data: {
            from: { nodeId: fromNodeId, portId: fromPortId },
            to: { nodeId: toNodeId, portId: toPortId },
            color: finalColor,
            label: w.label,
            wireType: finalType,
          },
          style: {
            stroke: finalColor,
            strokeWidth: 3.5,
          },
          markerEnd: undefined,
          animated: false,
        };
      });

      set({ nodes: rfNodes, edges: rfEdges, ercReport: data.erc_report || null });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      set({ error: msg });
    } finally {
      set({ isGenerating: false });
    }
  },
}));
