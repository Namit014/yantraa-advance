"use client";

import { useState } from "react";
import type { NodeShape, Port } from "./useConnectionStore";

// ─── Port dot + label ──────────────────────────────────────────────────────────

interface PortDotProps {
  port: Port;
  parentW: number;
  parentH: number;
}

function PortDot({ port, parentW, parentH }: PortDotProps) {
  const [hovered, setHovered] = useState(false);

  const importantPins = /vcc|gnd|sda|scl|vout|vin|3\.3v|5v|tx|rx|mosi|miso|sck|cs/i;
  const alwaysShow = importantPins.test(port.label);

  // Compute absolute position from side + offsetPercent
  let cx = 0;
  let cy = 0;
  const pct = port.offsetPercent / 100;

  switch (port.side) {
    case "top":
      cx = parentW * pct;
      cy = 0;
      break;
    case "bottom":
      cx = parentW * pct;
      cy = parentH;
      break;
    case "left":
      cx = 0;
      cy = parentH * pct;
      break;
    case "right":
      cx = parentW;
      cy = parentH * pct;
      break;
  }

  // Label offset based on side
  let labelX = cx;
  let labelY = cy;
  let anchor = "middle";
  switch (port.side) {
    case "top":
      labelY = cy - 8;
      anchor = "middle";
      break;
    case "bottom":
      labelY = cy + 14;
      anchor = "middle";
      break;
    case "left":
      labelX = cx - 8;
      anchor = "end";
      break;
    case "right":
      labelX = cx + 8;
      anchor = "start";
      break;
  }

  const showLabel = alwaysShow || hovered;

  return (
    <g
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{ cursor: "crosshair" }}
    >
      {/* Glow ring on hover */}
      {hovered && (
        <circle
          cx={cx}
          cy={cy}
          r={6}
          fill="#FFD700"
          opacity={0.25}
        />
      )}
      {/* Gold pin dot */}
      <circle
        cx={cx}
        cy={cy}
        r={3.5}
        fill="#FFD700"
        stroke="#c8a800"
        strokeWidth={0.8}
      />
      {/* Label */}
      {showLabel && (
        <text
          x={labelX}
          y={labelY}
          textAnchor={anchor as "middle" | "end" | "start"}
          fontSize={7.5}
          fill="white"
          fontFamily="monospace"
          style={{ pointerEvents: "none", userSelect: "none" }}
        >
          {port.label}
        </text>
      )}
    </g>
  );
}

// ─── Silhouette shapes ─────────────────────────────────────────────────────────

function RaspberryPi({ ports }: { ports: Port[] }) {
  const W = 240;
  const H = 170;
  return (
    <svg
      width={W + 40}
      height={H + 40}
      viewBox={`-20 -20 ${W + 40} ${H + 40}`}
      style={{ overflow: "visible" }}
    >
      {/* PCB body */}
      <rect
        x={0}
        y={0}
        width={W}
        height={H}
        rx={8}
        fill="#0d1f0d"
        stroke="#2a5a2a"
        strokeWidth={1.5}
      />
      {/* GPIO header strip (top edge) */}
      <rect x={30} y={-10} width={160} height={18} rx={3} fill="#1a3a1a" stroke="#3a6a3a" strokeWidth={1} />
      {/* GPIO pins on header */}
      {Array.from({ length: 20 }).map((_, i) => (
        <rect key={i} x={34 + i * 8} y={-8} width={3} height={14} rx={0.5} fill="#FFD700" opacity={0.7} />
      ))}

      {/* USB ports (right side) */}
      <rect x={W - 4} y={25} width={20} height={28} rx={3} fill="#1a3a1a" stroke="#3a6a3a" strokeWidth={1} />
      <rect x={W - 4} y={62} width={20} height={28} rx={3} fill="#1a3a1a" stroke="#3a6a3a" strokeWidth={1} />
      {/* USB labels */}
      <text x={W + 6} y={42} textAnchor="middle" fontSize={5} fill="#888" fontFamily="monospace">USB</text>
      <text x={W + 6} y={79} textAnchor="middle" fontSize={5} fill="#888" fontFamily="monospace">USB</text>

      {/* HDMI port (bottom left) */}
      <rect x={10} y={H - 2} width={32} height={16} rx={2} fill="#1a3a1a" stroke="#3a6a3a" strokeWidth={1} />
      <text x={26} y={H + 11} textAnchor="middle" fontSize={5} fill="#888" fontFamily="monospace">HDMI</text>

      {/* Ethernet port (right) */}
      <rect x={W - 4} y={100} width={26} height={22} rx={2} fill="#1a3a1a" stroke="#3a6a3a" strokeWidth={1} />
      <text x={W + 9} y={116} textAnchor="middle" fontSize={5} fill="#888" fontFamily="monospace">ETH</text>

      {/* Mounting holes */}
      {[[8, 8], [W - 8, 8], [8, H - 8], [W - 8, H - 8]].map(([mx, my], i) => (
        <circle key={i} cx={mx} cy={my} r={4} fill="#0a150a" stroke="#2a5a2a" strokeWidth={1} />
      ))}

      {/* CPU chip */}
      <rect x={80} y={55} width={60} height={60} rx={4} fill="#162816" stroke="#2a5a2a" strokeWidth={1} />
      <text x={110} y={85} textAnchor="middle" fontSize={7} fill="#4a9a4a" fontFamily="monospace">BCM</text>
      <text x={110} y={94} textAnchor="middle" fontSize={6} fill="#3a7a3a" fontFamily="monospace">2711</text>

      {/* PCB trace lines */}
      <line x1={30} y1={8} x2={78} y2={55} stroke="#1a3a1a" strokeWidth={0.8} opacity={0.5} />
      <line x1={170} y1={8} x2={142} y2={55} stroke="#1a3a1a" strokeWidth={0.8} opacity={0.5} />
      <line x1={W} y1={35} x2={142} y2={80} stroke="#1a3a1a" strokeWidth={0.8} opacity={0.5} />

      {/* Port dots */}
      {ports.map((p) => (
        <PortDot key={p.id} port={p} parentW={W} parentH={H} />
      ))}
    </svg>
  );
}

function ArduinoUno({ ports }: { ports: Port[] }) {
  const W = 220;
  const H = 175;
  return (
    <svg
      width={W + 40}
      height={H + 40}
      viewBox={`-20 -20 ${W + 40} ${H + 40}`}
      style={{ overflow: "visible" }}
    >
      {/* PCB body with iconic notched top-left corner */}
      <path
        d={`M 20 0 L ${W} 0 L ${W} ${H} L 0 ${H} L 0 20 Z`}
        fill="#001a4d"
        stroke="#003399"
        strokeWidth={1.5}
      />

      {/* Digital pins header (top) */}
      <rect x={30} y={-12} width={160} height={16} rx={2} fill="#0a1a3a" stroke="#1a3a8a" strokeWidth={1} />
      {Array.from({ length: 14 }).map((_, i) => (
        <rect key={i} x={34 + i * 11} y={-10} width={4} height={12} rx={0.5} fill="#FFD700" opacity={0.7} />
      ))}

      {/* Analog pins (bottom) */}
      <rect x={40} y={H - 4} width={90} height={16} rx={2} fill="#0a1a3a" stroke="#1a3a8a" strokeWidth={1} />
      {Array.from({ length: 6 }).map((_, i) => (
        <rect key={i} x={44 + i * 14} y={H - 2} width={4} height={12} rx={0.5} fill="#FFD700" opacity={0.7} />
      ))}

      {/* Power header (top right) */}
      <rect x={W - 50} y={-12} width={40} height={16} rx={2} fill="#0a1a3a" stroke="#1a3a8a" strokeWidth={1} />
      {Array.from({ length: 4 }).map((_, i) => (
        <rect key={i} x={W - 46 + i * 9} y={-10} width={4} height={12} rx={0.5} fill="#FFD700" opacity={0.7} />
      ))}

      {/* USB-B port (left side) */}
      <rect x={-14} y={55} width={20} height={24} rx={3} fill="#0a1a3a" stroke="#1a3a8a" strokeWidth={1} />
      <text x={-4} y={70} textAnchor="middle" fontSize={5} fill="#888" fontFamily="monospace">USB</text>

      {/* ATmega chip */}
      <rect x={60} y={50} width={70} height={70} rx={3} fill="#0a1430" stroke="#1a3a8a" strokeWidth={1} />
      {/* chip pins */}
      {Array.from({ length: 7 }).map((_, i) => (
        <rect key={i} x={57} y={55 + i * 9} width={5} height={3} fill="#888" />
      ))}
      {Array.from({ length: 7 }).map((_, i) => (
        <rect key={i} x={128} y={55 + i * 9} width={5} height={3} fill="#888" />
      ))}
      <text x={95} y={85} textAnchor="middle" fontSize={6} fill="#4488ff" fontFamily="monospace">ATmega</text>
      <text x={95} y={94} textAnchor="middle" fontSize={6} fill="#3366cc" fontFamily="monospace">328P</text>

      {/* Mounting holes */}
      {[[6, 35], [W - 8, 8], [W - 8, H - 8], [8, H - 8]].map(([mx, my], i) => (
        <circle key={i} cx={mx} cy={my} r={4} fill="#00103a" stroke="#003399" strokeWidth={1} />
      ))}

      {/* Power LED */}
      <circle cx={W - 20} cy={H - 20} r={3} fill="#00ff44" opacity={0.8} />
      <text x={W - 20} y={H - 8} textAnchor="middle" fontSize={5} fill="#888" fontFamily="monospace">PWR</text>

      {/* Port dots */}
      {ports.map((p) => (
        <PortDot key={p.id} port={p} parentW={W} parentH={H} />
      ))}
    </svg>
  );
}

function ESP32({ ports }: { ports: Port[] }) {
  const W = 90;
  const H = 200;
  return (
    <svg
      width={W + 60}
      height={H + 40}
      viewBox={`-30 -20 ${W + 60} ${H + 40}`}
      style={{ overflow: "visible" }}
    >
      {/* PCB body */}
      <rect x={0} y={0} width={W} height={H} rx={5} fill="#1a1200" stroke="#4a3800" strokeWidth={1.5} />

      {/* Antenna bump at top */}
      <rect x={20} y={-18} width={50} height={20} rx={3} fill="#221800" stroke="#4a3800" strokeWidth={1} />
      <text x={45} y={-6} textAnchor="middle" fontSize={6} fill="#666" fontFamily="monospace">ANT</text>
      {/* Antenna lines */}
      <line x1={45} y1={-18} x2={45} y2={-22} stroke="#4a3800" strokeWidth={1} />
      <line x1={38} y1={-22} x2={52} y2={-22} stroke="#4a3800" strokeWidth={1} />

      {/* Left pin row */}
      {Array.from({ length: 19 }).map((_, i) => (
        <rect key={i} x={-8} y={10 + i * 10} width={10} height={4} rx={0.5} fill="#FFD700" opacity={0.7} />
      ))}

      {/* Right pin row */}
      {Array.from({ length: 19 }).map((_, i) => (
        <rect key={i} x={W - 2} y={10 + i * 10} width={10} height={4} rx={0.5} fill="#FFD700" opacity={0.7} />
      ))}

      {/* ESP32 module chip */}
      <rect x={10} y={20} width={70} height={60} rx={3} fill="#111000" stroke="#4a3800" strokeWidth={1} />
      <text x={45} y={50} textAnchor="middle" fontSize={7} fill="#cc8800" fontFamily="monospace">ESP32</text>
      <text x={45} y={60} textAnchor="middle" fontSize={5} fill="#886600" fontFamily="monospace">WROOM</text>

      {/* USB port (bottom) */}
      <rect x={30} y={H - 4} width={30} height={16} rx={3} fill="#221800" stroke="#4a3800" strokeWidth={1} />
      <text x={45} y={H + 11} textAnchor="middle" fontSize={5} fill="#888" fontFamily="monospace">USB</text>

      {/* Boot/EN buttons */}
      <rect x={5} y={H - 35} width={15} height={10} rx={2} fill="#221800" stroke="#4a3800" strokeWidth={1} />
      <text x={12} y={H - 28} textAnchor="middle" fontSize={4.5} fill="#888" fontFamily="monospace">EN</text>
      <rect x={70} y={H - 35} width={15} height={10} rx={2} fill="#221800" stroke="#4a3800" strokeWidth={1} />
      <text x={77} y={H - 28} textAnchor="middle" fontSize={4} fill="#888" fontFamily="monospace">BOOT</text>

      {/* Port dots */}
      {ports.map((p) => (
        <PortDot key={p.id} port={p} parentW={W} parentH={H} />
      ))}
    </svg>
  );
}

function Breadboard({ ports }: { ports: Port[] }) {
  const W = 280;
  const H = 160;
  const COLS = 30;
  const ROWS = 10;
  const HOLE_PITCH = 8;
  const startX = 20;
  const startY = 30;

  return (
    <svg
      width={W + 40}
      height={H + 40}
      viewBox={`-20 -20 ${W + 40} ${H + 40}`}
      style={{ overflow: "visible" }}
    >
      {/* Body */}
      <rect x={0} y={0} width={W} height={H} rx={6} fill="#1a1a1a" stroke="#333" strokeWidth={1.5} />

      {/* Power rails — left */}
      <rect x={4} y={5} width={12} height={H - 10} rx={2} fill="#1f0000" stroke="#550000" strokeWidth={0.8} />
      <line x1={10} y1={8} x2={10} y2={H - 8} stroke="#FF4444" strokeWidth={0.8} opacity={0.6} />
      {Array.from({ length: 12 }).map((_, i) => (
        <circle key={i} cx={10} cy={12 + i * 11} r={2} fill="#FF4444" opacity={0.8} />
      ))}

      {/* Power rails — right */}
      <rect x={W - 16} y={5} width={12} height={H - 10} rx={2} fill="#1f0000" stroke="#550000" strokeWidth={0.8} />
      <line x1={W - 10} y1={8} x2={W - 10} y2={H - 8} stroke="#888" strokeWidth={0.8} opacity={0.6} />
      {Array.from({ length: 12 }).map((_, i) => (
        <circle key={i} cx={W - 10} cy={12 + i * 11} r={2} fill="#888" opacity={0.8} />
      ))}

      {/* Tie-point holes grid — top half */}
      {Array.from({ length: ROWS / 2 }).map((_, row) =>
        Array.from({ length: COLS }).map((_, col) => (
          <circle
            key={`t-${row}-${col}`}
            cx={startX + col * HOLE_PITCH}
            cy={startY + row * HOLE_PITCH}
            r={2}
            fill="#2a2a2a"
            stroke="#444"
            strokeWidth={0.5}
          />
        ))
      )}

      {/* Center divider */}
      <rect x={16} y={H / 2 - 5} width={W - 32} height={10} rx={2} fill="#222" />

      {/* Tie-point holes grid — bottom half */}
      {Array.from({ length: ROWS / 2 }).map((_, row) =>
        Array.from({ length: COLS }).map((_, col) => (
          <circle
            key={`b-${row}-${col}`}
            cx={startX + col * HOLE_PITCH}
            cy={H / 2 + 10 + row * HOLE_PITCH}
            r={2}
            fill="#2a2a2a"
            stroke="#444"
            strokeWidth={0.5}
          />
        ))
      )}

      {/* Column labels A–E */}
      {["a", "b", "c", "d", "e"].map((l, i) => (
        <text key={l} x={8} y={startY + i * HOLE_PITCH + 2} textAnchor="end" fontSize={5} fill="#555" fontFamily="monospace">
          {l}
        </text>
      ))}

      {/* Port dots */}
      {ports.map((p) => (
        <PortDot key={p.id} port={p} parentW={W} parentH={H} />
      ))}
    </svg>
  );
}

function ICChip({ ports }: { ports: Port[] }) {
  const W = 110;
  const H = 160;
  const PIN_COUNT = 8; // each side
  return (
    <svg
      width={W + 60}
      height={H + 40}
      viewBox={`-30 -20 ${W + 60} ${H + 40}`}
      style={{ overflow: "visible" }}
    >
      {/* Body */}
      <rect x={0} y={0} width={W} height={H} rx={4} fill="#0d0d0d" stroke="#333" strokeWidth={1.5} />

      {/* Notch at top */}
      <path
        d={`M ${W / 2 - 12} 0 A 12 12 0 0 0 ${W / 2 + 12} 0`}
        fill="#0d0d0d"
        stroke="#333"
        strokeWidth={1.5}
      />

      {/* Left pins */}
      {Array.from({ length: PIN_COUNT }).map((_, i) => (
        <g key={`l-${i}`}>
          <rect x={-18} y={15 + i * 18} width={20} height={6} rx={1} fill="#888" />
          <text x={-22} y={21 + i * 18} textAnchor="end" fontSize={6} fill="#666" fontFamily="monospace">
            {i + 1}
          </text>
        </g>
      ))}

      {/* Right pins */}
      {Array.from({ length: PIN_COUNT }).map((_, i) => (
        <g key={`r-${i}`}>
          <rect x={W - 2} y={15 + i * 18} width={20} height={6} rx={1} fill="#888" />
          <text x={W + 23} y={21 + i * 18} textAnchor="start" fontSize={6} fill="#666" fontFamily="monospace">
            {PIN_COUNT * 2 - i}
          </text>
        </g>
      ))}

      {/* Chip label */}
      <text x={W / 2} y={H / 2 - 6} textAnchor="middle" fontSize={9} fill="#66aaff" fontFamily="monospace" fontWeight="bold">
        IC
      </text>
      <text x={W / 2} y={H / 2 + 8} textAnchor="middle" fontSize={7} fill="#4488cc" fontFamily="monospace">
        DIP-16
      </text>

      {/* Pin 1 marker */}
      <circle cx={8} cy={12} r={3} fill="none" stroke="#aaa" strokeWidth={0.8} />

      {/* Port dots */}
      {ports.map((p) => (
        <PortDot key={p.id} port={p} parentW={W} parentH={H} />
      ))}
    </svg>
  );
}

function GenericBoard({ ports }: { ports: Port[] }) {
  const W = 200;
  const H = 140;
  return (
    <svg
      width={W + 40}
      height={H + 40}
      viewBox={`-20 -20 ${W + 40} ${H + 40}`}
      style={{ overflow: "visible" }}
    >
      {/* Body */}
      <rect x={0} y={0} width={W} height={H} rx={6} fill="#0d1a1a" stroke="#1a4040" strokeWidth={1.5} />

      {/* PCB trace pattern */}
      <line x1={20} y1={30} x2={80} y2={30} stroke="#1a4040" strokeWidth={0.8} opacity={0.6} />
      <line x1={80} y1={30} x2={80} y2={80} stroke="#1a4040" strokeWidth={0.8} opacity={0.6} />
      <line x1={80} y1={80} x2={140} y2={80} stroke="#1a4040" strokeWidth={0.8} opacity={0.6} />
      <line x1={120} y1={40} x2={170} y2={40} stroke="#1a4040" strokeWidth={0.8} opacity={0.6} />
      <line x1={170} y1={40} x2={170} y2={100} stroke="#1a4040" strokeWidth={0.8} opacity={0.6} />
      <line x1={40} y1={60} x2={40} y2={110} stroke="#1a4040" strokeWidth={0.8} opacity={0.6} />
      <line x1={40} y1={110} x2={130} y2={110} stroke="#1a4040" strokeWidth={0.8} opacity={0.6} />

      {/* Via dots */}
      {[[80, 30], [80, 80], [140, 80], [170, 40], [170, 100], [40, 60], [40, 110], [130, 110], [120, 40]].map(([vx, vy], i) => (
        <circle key={i} cx={vx} cy={vy} r={2.5} fill="#0d1a1a" stroke="#2a6060" strokeWidth={1} />
      ))}

      {/* Center chip placeholder */}
      <rect x={70} y={45} width={60} height={50} rx={3} fill="#111" stroke="#1a4040" strokeWidth={1} />
      <text x={100} y={72} textAnchor="middle" fontSize={7} fill="#2a8080" fontFamily="monospace">MODULE</text>

      {/* Mounting holes */}
      {[[8, 8], [W - 8, 8], [8, H - 8], [W - 8, H - 8]].map(([mx, my], i) => (
        <circle key={i} cx={mx} cy={my} r={4} fill="#0a1010" stroke="#1a4040" strokeWidth={1} />
      ))}

      {/* Port dots */}
      {ports.map((p) => (
        <PortDot key={p.id} port={p} parentW={W} parentH={H} />
      ))}
    </svg>
  );
}

// ─── Main export ───────────────────────────────────────────────────────────────

interface ComponentSilhouetteProps {
  shape: NodeShape;
  ports: Port[];
  label: string;
}

export function ComponentSilhouette({ shape, ports, label }: ComponentSilhouetteProps) {
  const renderSilhouette = () => {
    switch (shape) {
      case "raspberry-pi":
        return <RaspberryPi ports={ports} />;
      case "arduino-uno":
        return <ArduinoUno ports={ports} />;
      case "esp32":
        return <ESP32 ports={ports} />;
      case "breadboard":
        return <Breadboard ports={ports} />;
      case "ic-chip":
        return <ICChip ports={ports} />;
      case "generic-board":
      default:
        return <GenericBoard ports={ports} />;
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 6,
        padding: "12px 16px 8px",
        userSelect: "none",
      }}
    >
      {renderSilhouette()}
      {/* Component name badge */}
      <div
        style={{
          backgroundColor: "rgba(255,255,255,0.08)",
          border: "1px solid rgba(255,255,255,0.12)",
          borderRadius: 6,
          padding: "2px 10px",
          color: "white",
          fontSize: 11,
          fontFamily: "monospace",
          fontWeight: "bold",
          letterSpacing: "0.04em",
          whiteSpace: "nowrap",
          maxWidth: 280,
          overflow: "hidden",
          textOverflow: "ellipsis",
        }}
      >
        {label}
      </div>
    </div>
  );
}
