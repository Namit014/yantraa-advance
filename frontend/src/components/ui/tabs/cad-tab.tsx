"use client";

import { useState, useEffect, Suspense, useMemo, useRef } from "react";
import { Loader2, Box, Info, Play, Pause, Eye, EyeOff, ListTree, Ruler, Ghost, MessageSquare, Mic, MicOff, Move, Maximize2, RotateCw, Settings, Layers, Network, Scissors, BoxSelect, AlertTriangle, Magnet } from "lucide-react";
import * as THREE from "three";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { 
    OrbitControls, 
    Environment, 
    Grid, 
    Center, 
    GizmoHelper, 
    GizmoViewport,
    PivotControls,
    ContactShadows,
    Html,
    Line,
    TransformControls
} from "@react-three/drei";

interface CADTabProps {
    currentQuery?: string;
    cadUrls?: string[] | null;
    designData?: any;
    onGeneratedCad?: (url: string) => void;
}

interface LoadedMesh {
    id: string;
    geometry: THREE.BufferGeometry;
    color: THREE.Color | null;
    name: string;
}

interface Annotation {
    id: string;
    position: THREE.Vector3;
    text: string;
}

const INDUSTRIAL_COLORS = [
    new THREE.Color("#d4af37"), // Metallic Gold
    new THREE.Color("#b87333"), // Metallic Copper
    new THREE.Color("#ff1144"), // Candy Apple Red Metallic
    new THREE.Color("#0066ff"), // Electric Blue Metallic
    new THREE.Color("#00df88"), // Emerald Green Metallic
];

const MOCK_COMPONENT_DB: Record<string, {
    function: string;
    specs: { label: string; value: string }[];
    cost: string;
    manufacturer: string;
    datasheet: string;
    alternatives: string[];
}> = {
    "default": {
        function: "Structural housing and mechanical support.",
        specs: [
            { label: "Material", value: "A36 Steel / 6061-T6 Aluminum" },
            { label: "Tolerance", value: "±0.05 mm" },
            { label: "Finishing", value: "Anodized / Powder Coated" }
        ],
        cost: "$45.00 (Est. Machining)",
        manufacturer: "Custom Yantra Fab",
        datasheet: "https://www.matweb.com/",
        alternatives: ["Cast Iron", "Titanium Ti-6Al-4V"]
    },
    "motor": {
        function: "Provides rotational actuation for joint movement.",
        specs: [
            { label: "Type", value: "NEMA 17 Stepper" },
            { label: "Holding Torque", value: "45 N·cm" },
            { label: "Rated Current", value: "1.5A / phase" },
            { label: "Step Angle", value: "1.8°" }
        ],
        cost: "$12.50",
        manufacturer: "StepperOnline",
        datasheet: "https://www.omc-stepperonline.com/download/17HS15-1504S-X1.pdf",
        alternatives: ["NEMA 23", "Moons' 17HD Series", "ClearPath Servo"]
    },
    "gear": {
        function: "Torque multiplication and speed reduction.",
        specs: [
            { label: "Type", value: "Harmonic Drive (Strain Wave)" },
            { label: "Reduction Ratio", value: "100:1" },
            { label: "Backlash", value: "< 1 arcmin" },
            { label: "Peak Torque", value: "23 Nm" }
        ],
        cost: "$350.00",
        manufacturer: "Harmonic Drive LLC",
        datasheet: "https://www.harmonicdrive.net/products/gear-units/csf",
        alternatives: ["Cycloidal Drive", "Planetary Gearbox"]
    },
    "bearing": {
        function: "Reduces friction between moving parts.",
        specs: [
            { label: "Type", value: "Deep Groove Ball Bearing" },
            { label: "Dynamic Load Rating", value: "4.5 kN" },
            { label: "Static Load Rating", value: "2.5 kN" },
            { label: "Max RPM", value: "30,000 RPM" }
        ],
        cost: "$4.20",
        manufacturer: "SKF / Timken",
        datasheet: "https://www.skf.com/group/products/rolling-bearings",
        alternatives: ["Crossed Roller Bearing", "Needle Roller"]
    }
};

function getComponentData(meshName: string) {
    const name = meshName.toLowerCase();
    if (name.includes("motor") || name.includes("stepper") || name.includes("servo") || name.includes("actuator")) return MOCK_COMPONENT_DB["motor"];
    if (name.includes("gear") || name.includes("drive") || name.includes("transmission")) return MOCK_COMPONENT_DB["gear"];
    if (name.includes("bearing") || name.includes("roller")) return MOCK_COMPONENT_DB["bearing"];
    return MOCK_COMPONENT_DB["default"];
}

const CAD_CONFIG: Record<string, { scale: number, rotation: [number, number, number] }> = {
    "scara": { scale: 1.5, rotation: [0, 0, -Math.PI / 2] },
    "cobot": { scale: 0.15, rotation: [0, 0, 0] },
    "delta": { scale: 0.5, rotation: [0, 0, 0] },
};

function CameraFlyTo({ selectedMesh, meshes, controlsRef }: { selectedMesh: string | null, meshes: LoadedMesh[], controlsRef: any }) {
    const { camera, scene } = useThree();
    const targetPosition = useRef(new THREE.Vector3());
    const targetLookAt = useRef(new THREE.Vector3());
    const isAnimating = useRef(false);

    useEffect(() => {
        if (!selectedMesh || !controlsRef.current) return;
        
        // Use a timeout to ensure the mesh has been rendered and added to the scene graph
        const timer = setTimeout(() => {
            const object3D = scene.getObjectByName(selectedMesh);
            if (object3D) {
                const box = new THREE.Box3().setFromObject(object3D);
                const center = new THREE.Vector3();
                box.getCenter(center);
                
                const size = new THREE.Vector3();
                box.getSize(size);
                const maxDim = Math.max(size.x, size.y, size.z);
                
                targetLookAt.current.copy(center);
                // Position camera to look at the center from an optimal distance
                targetPosition.current.copy(center).add(new THREE.Vector3(maxDim * 1.5, maxDim * 1.0, maxDim * 1.5));
                
                isAnimating.current = true;
            }
        }, 50);
        
        // Failsafe: stop animating after 1.5s so user regains control
        const stopTimer = setTimeout(() => {
            isAnimating.current = false;
        }, 1500);
        
        return () => {
            clearTimeout(timer);
            clearTimeout(stopTimer);
        };
    }, [selectedMesh, scene, controlsRef]);

    useFrame((state, delta) => {
        if (!isAnimating.current || !controlsRef.current) return;

        camera.position.lerp(targetPosition.current, 5 * delta);
        controlsRef.current.target.lerp(targetLookAt.current, 5 * delta);
        controlsRef.current.update();

        if (camera.position.distanceTo(targetPosition.current) < 1.0) {
            isAnimating.current = false;
        }
    });

    return null;
}

function CADModel({ 
    meshes, 
    url, 
    explosion, 
    hoveredMesh, 
    setHoveredMesh, 
    selectedMesh, 
    setSelectedMesh,
    hiddenMeshes,
    clipAxis,
    clipValue,
    autoScale,
    isMeasuring,
    measurePoints,
    setMeasurePoints,
    renderMode,
    isAnnotating,
    onAddAnnotation,
    optimizedParts,
    activePivot,
    setActivePivot,
    transformMode,
    partTransforms,
    setPartTransforms,
    setTransforming,
    showBoundingBox,
    magnetEnabled
}: { 
    meshes: LoadedMesh[], 
    url: string, 
    explosion: number, 
    hoveredMesh: string | null, 
    setHoveredMesh: (id: string | null) => void, 
    selectedMesh: string | null, 
    setSelectedMesh: (id: string | null) => void,
    hiddenMeshes: Set<string>,
    clipAxis: 'x' | 'y' | 'z' | null,
    clipValue: number,
    autoScale: number,
    isMeasuring: boolean,
    measurePoints: THREE.Vector3[],
    setMeasurePoints: (points: THREE.Vector3[]) => void,
    renderMode: number,
    isAnnotating: boolean,
    onAddAnnotation: (pos: THREE.Vector3) => void,
    optimizedParts: Set<string>,
    activePivot: string | null,
    setActivePivot: (id: string | null) => void,
    transformMode: 'translate' | 'rotate' | 'scale' | null,
    partTransforms: Record<string, { position?: [number, number, number], rotation?: [number, number, number], scale?: [number, number, number] }>,
    setPartTransforms: React.Dispatch<React.SetStateAction<Record<string, { position?: [number, number, number], rotation?: [number, number, number], scale?: [number, number, number] }>>>,
    setTransforming: (v: boolean) => void,
    showBoundingBox?: boolean,
    magnetEnabled: boolean
}) {
    const { explosionVectors, globalBox, boundingBoxes } = useMemo(() => {
        const vectors = new Map();
        const bBoxes = new Map<string, THREE.Box3>();
        const gBox = new THREE.Box3();
        
        // Compute transformed bounding boxes for all meshes
        meshes.forEach(m => {
            if (!m.geometry.boundingBox) m.geometry.computeBoundingBox();
            
            const box = m.geometry.boundingBox!.clone();
            const pTransform = partTransforms[m.id] || {};
            
            // Apply scale
            const scale = new THREE.Vector3(
                pTransform.scale?.[0] ?? 1,
                pTransform.scale?.[1] ?? 1,
                pTransform.scale?.[2] ?? 1
            );
            box.min.multiply(scale);
            box.max.multiply(scale);
            
            // Apply translation
            const pos = new THREE.Vector3(
                pTransform.position?.[0] ?? 0,
                pTransform.position?.[1] ?? 0,
                pTransform.position?.[2] ?? 0
            );
            box.translate(pos);
            
            bBoxes.set(m.id, box);
            gBox.union(box);
        });

        const globalCenter = gBox.getCenter(new THREE.Vector3());

        // Compute explosion vectors based on original center
        meshes.forEach(m => {
            const box = bBoxes.get(m.id)!;
            const center = box.getCenter(new THREE.Vector3());
            const dir = center.clone().sub(globalCenter);
            vectors.set(m.id, dir);
        });

        return { explosionVectors: vectors, globalBox: gBox, boundingBoxes: bBoxes };
    }, [meshes, partTransforms]);

    const clippingPlane = useMemo(() => {
        if (!clipAxis) return null;
        
        const globalBox = new THREE.Box3();
        meshes.forEach(m => {
            if (m.geometry.boundingBox) globalBox.union(m.geometry.boundingBox);
        });
        
        const min = globalBox.min[clipAxis];
        const max = globalBox.max[clipAxis];
        const pos = min + (max - min) * (clipValue / 100);
        
        const normal = new THREE.Vector3(0, 0, 0);
        normal[clipAxis] = -1; 
        
        return new THREE.Plane(normal, pos);
    }, [clipAxis, clipValue, meshes]);

    let rotation: [number, number, number] = [0, 0, 0];
    const lowerUrl = url.toLowerCase();
    for (const [key, config] of Object.entries(CAD_CONFIG)) {
        if (lowerUrl.includes(key)) {
            rotation = config.rotation;
            break;
        }
    }

    const robotColor = useMemo(() => {
        let hash = 0;
        for (let i = 0; i < lowerUrl.length; i++) {
            hash = lowerUrl.charCodeAt(i) + ((hash << 5) - hash);
        }
        return INDUSTRIAL_COLORS[Math.abs(hash) % INDUSTRIAL_COLORS.length];
    }, [lowerUrl]);

    const materialMap = useMemo(() => {
        const mats = new Map();
        let maxVolume = 0;
        let lowestY = Infinity;
        let highestY = -Infinity;
        
        meshes.forEach(m => {
            if (!m.geometry.boundingBox) m.geometry.computeBoundingBox();
            const size = m.geometry.boundingBox!.getSize(new THREE.Vector3());
            const volume = size.x * size.y * size.z;
            if (volume > maxVolume) maxVolume = volume;
            
            const minY = m.geometry.boundingBox!.min.y;
            const maxY = m.geometry.boundingBox!.max.y;
            if (minY < lowestY) lowestY = minY;
            if (maxY > highestY) highestY = maxY;
            
            mats.set(m.id, volume);
        });

        const totalHeight = highestY - lowestY;

        meshes.forEach(m => {
            const volume = mats.get(m.id);
            const ratio = maxVolume > 0 ? volume / maxVolume : 0;
            
            const box = m.geometry.boundingBox!;
            const isBase = totalHeight > 0 && (box.min.y - lowestY) <= (totalHeight * 0.1) && ratio > 0.01;
            
            let props;
            if (renderMode === 1 && (isBase || ratio > 0.05)) {
                // Ghost mode: Frosted glass for large structural shells
                props = {
                    color: new THREE.Color("#ffffff"),
                    transmission: 0.9,
                    opacity: 1,
                    transparent: true,
                    roughness: 0.1,
                    ior: 1.5,
                    thickness: 2,
                    envMapIntensity: 1.5,
                    clearcoat: 1.0,
                    clearcoatRoughness: 0.1,
                    depthWrite: false
                };
            } else if (renderMode === 2) {
                // Actual CAD Mode: Raw original colors without Yantra overrides
                props = { 
                    color: m.color || new THREE.Color("#aaaaaa"), 
                    metalness: 0.2, 
                    roughness: 0.8 
                };
            } else if (m.color) {
                props = { color: m.color, metalness: 0.6, roughness: 0.4, clearcoat: 0.5, clearcoatRoughness: 0.3, envMapIntensity: 1.0 };
            } else if (isBase) {
                // Base structure: Heavy Steel
                props = { 
                    color: new THREE.Color("#2b2c2f"), 
                    metalness: 0.8, 
                    roughness: 0.6, 
                    clearcoat: 0.0, 
                    envMapIntensity: 1.0
                };
            } else if (ratio > 0.005) {
                // Large structural parts: Glossy Carbon Fiber
                props = { 
                    color: new THREE.Color("#151515"), 
                    metalness: 0.3, 
                    roughness: 0.7, 
                    clearcoat: 1.0, 
                    clearcoatRoughness: 0.1,
                    envMapIntensity: 1.5
                };
            } else if (ratio > 0.0005) {
                // Medium arms/links: Brushed Aluminum
                props = { 
                    color: new THREE.Color("#d1d5db"), // Light silver
                    metalness: 0.9, 
                    roughness: 0.3, 
                    clearcoat: 0.2, 
                    envMapIntensity: 2.0
                };
            } else if (ratio > 0.00005) {
                // Covers, joints, small shells: Molded Plastic
                props = { 
                    color: robotColor, 
                    metalness: 0.1, 
                    roughness: 0.8, 
                    clearcoat: 0.1, 
                    envMapIntensity: 0.5
                };
            } else {
                // Tiny parts (Screws/Hardware): Bright Steel/Chrome
                props = { 
                    color: new THREE.Color("#e5e7eb"), 
                    metalness: 1.0, 
                    roughness: 0.1, 
                    clearcoat: 0.5, 
                    clearcoatRoughness: 0.0,
                    envMapIntensity: 2.5
                };
            }
            mats.set(m.id, { 
                ...props, 
                volume,
                clippingPlanes: clippingPlane ? [clippingPlane] : [],
                clipShadows: true,
                side: clippingPlane ? THREE.DoubleSide : THREE.FrontSide
            });
        });
        
        return mats;
    }, [meshes, robotColor, clippingPlane, renderMode]);

    return (
        <group scale={autoScale} rotation={rotation}>
            {meshes.map((mesh) => {
                const matProps = materialMap.get(mesh.id);
                const dir = explosionVectors.get(mesh.id);
                // Multiply explosion percentage by 0.5 to keep parts somewhat close
                const basePos = dir ? dir.clone().multiplyScalar(explosion * 0.015) : new THREE.Vector3();
                
                const isHovered = hoveredMesh === mesh.id;
                const isSelected = selectedMesh === mesh.id;
                const isHidden = hiddenMeshes.has(mesh.id);
                const isOptimized = optimizedParts?.has(mesh.id);
                const hasPivot = activePivot === mesh.id;
                const pTransform = partTransforms[mesh.id] || {};
                
                if (isHidden) return null;

                const centerPos = new THREE.Vector3();
                if (mesh.geometry.boundingBox) mesh.geometry.boundingBox.getCenter(centerPos);

                const MeshComponent = (
                    <group 
                        key={mesh.id} 
                        position={pTransform.position || basePos}
                        rotation={pTransform.rotation || [0, 0, 0]}
                        scale={pTransform.scale || [1, 1, 1]}
                    >
                        {isOptimized ? (
                            <mesh name={mesh.id} geometry={mesh.geometry} castShadow receiveShadow>
                                <meshStandardMaterial 
                                    color="#00ffcc" 
                                    wireframe={true} 
                                    emissive="#00ffcc"
                                    emissiveIntensity={2.0}
                                    transparent={true}
                                    opacity={0.8}
                                />
                            </mesh>
                        ) : (
                            <mesh
                                name={mesh.id}
                                geometry={mesh.geometry}
                                castShadow
                                receiveShadow
                                onPointerOver={(e) => {
                                    e.stopPropagation();
                                    if (!isMeasuring) setHoveredMesh(mesh.id); 
                                    document.body.style.cursor = isMeasuring ? 'crosshair' : 'pointer'; 
                                }}
                                onPointerOut={(e) => {
                                    e.stopPropagation();
                                    setHoveredMesh(null);
                                    document.body.style.cursor = 'auto'; 
                                }}
                                onClick={(e) => {
                                    e.stopPropagation();
                                    if (isMeasuring) {
                                        if (measurePoints.length >= 2) {
                                            setMeasurePoints([e.point]);
                                        } else {
                                            setMeasurePoints([...measurePoints, e.point]);
                                        }
                                    } else if (isAnnotating) {
                                        onAddAnnotation(e.point);
                                    } else {
                                        setSelectedMesh(isSelected ? null : mesh.id);
                                        // Auto-activate pivot on double click or simple select
                                        if (e.detail === 2) {
                                            setActivePivot(hasPivot ? null : mesh.id);
                                        }
                                    }
                                }}
                            >
                                {renderMode === 1 ? (
                                    <meshPhysicalMaterial 
                                        {...matProps} 
                                        emissive={isHovered || isSelected ? new THREE.Color(0x3a5a7a) : new THREE.Color(0x000000)}
                                        emissiveIntensity={isHovered ? 1.0 : (isSelected ? 2.0 : 0)}
                                    />
                                ) : (
                                    <meshStandardMaterial 
                                        {...matProps} 
                                        emissive={isHovered || isSelected ? new THREE.Color(0x3a5a7a) : new THREE.Color(0x000000)}
                                        emissiveIntensity={isHovered ? 1.0 : (isSelected ? 2.0 : 0)}
                                    />
                                )}
                                
                            </mesh>
                        )}
                        
                        {/* Highlight outlines */}
                        {(isHovered || isSelected) && !isOptimized && (
                            <mesh geometry={mesh.geometry}>
                                <meshBasicMaterial 
                                    color={isSelected ? "#3b82f6" : "#ffffff"} 
                                    wireframe 
                                    transparent 
                                    opacity={isSelected ? 0.8 : 0.3} 
                                    depthTest={false}
                                />
                            </mesh>
                        )}
                    </group>
                );

                if (isSelected && transformMode) {
                    return (
                        <TransformControls
                            key={`transform-${mesh.id}`}
                            mode={transformMode}
                            onMouseUp={(e: any) => {
                                setTransforming(false);
                                if (e?.target?.object) {
                                    const obj = e.target.object;
                                    let newPos = new THREE.Vector3(obj.position.x, obj.position.y, obj.position.z);
                                    const newRot: [number, number, number] = [obj.rotation.x, obj.rotation.y, obj.rotation.z];
                                    const newScale: [number, number, number] = [obj.scale.x, obj.scale.y, obj.scale.z];

                                    if (transformMode === 'translate' && magnetEnabled && mesh.geometry.boundingBox) {
                                        const threshold = 15.0; // Snapping threshold
                                        
                                        const dragBox = mesh.geometry.boundingBox.clone();
                                        const scaleVec = new THREE.Vector3(...newScale);
                                        dragBox.min.multiply(scaleVec);
                                        dragBox.max.multiply(scaleVec);
                                        dragBox.translate(newPos);
                                        
                                        const dragCenter = dragBox.getCenter(new THREE.Vector3());
                                        let snapPos = newPos.clone();

                                        let bestDistX = threshold, bestDistY = threshold, bestDistZ = threshold;

                                        meshes.forEach(m => {
                                            if (m.id === mesh.id || hiddenMeshes.has(m.id)) return;
                                            const otherBox = boundingBoxes.get(m.id);
                                            if (!otherBox) return;
                                            
                                            const otherCenter = otherBox.getCenter(new THREE.Vector3());
                                            
                                            const axes: ('x'|'y'|'z')[] = ['x', 'y', 'z'];
                                            axes.forEach(ax => {
                                                const dCenter = Math.abs(dragCenter[ax] - otherCenter[ax]);
                                                const dMaxMin = Math.abs(dragBox.max[ax] - otherBox.min[ax]);
                                                const dMinMax = Math.abs(dragBox.min[ax] - otherBox.max[ax]);

                                                let bestLocalDist = Math.min(dCenter, dMaxMin, dMinMax);
                                                let currentBest = ax === 'x' ? bestDistX : (ax === 'y' ? bestDistY : bestDistZ);

                                                if (bestLocalDist < currentBest) {
                                                    if (bestLocalDist === dCenter) {
                                                        snapPos[ax] -= (dragCenter[ax] - otherCenter[ax]);
                                                    } else if (bestLocalDist === dMaxMin) {
                                                        snapPos[ax] -= (dragBox.max[ax] - otherBox.min[ax]);
                                                    } else {
                                                        snapPos[ax] -= (dragBox.min[ax] - otherBox.max[ax]);
                                                    }
                                                    
                                                    if (ax === 'x') bestDistX = bestLocalDist;
                                                    if (ax === 'y') bestDistY = bestLocalDist;
                                                    if (ax === 'z') bestDistZ = bestLocalDist;
                                                }
                                            });
                                        });
                                        
                                        newPos.copy(snapPos);
                                        obj.position.copy(newPos);
                                    }

                                    setPartTransforms(prev => ({
                                        ...prev,
                                        [mesh.id]: {
                                            position: [newPos.x, newPos.y, newPos.z],
                                            rotation: newRot,
                                            scale: newScale
                                        }
                                    }));
                                }
                            }}
                            onMouseDown={() => setTransforming(true)}
                        >
                            {MeshComponent}
                        </TransformControls>
                    );
                }

                if (hasPivot || isSelected) {
                    return (
                        <PivotControls
                            key={`pivot-${mesh.id}`}
                            scale={50 / autoScale}
                            depthTest={false}
                            lineWidth={3}
                            anchor={[0, 0, 0]}
                            visible={hasPivot && !transformMode} // Hide pivot if transform mode is active
                            disableAxes={transformMode !== null}
                            disableRotations={transformMode !== null}
                            disableSliders={transformMode !== null}
                        >
                            {MeshComponent}
                        </PivotControls>
                    );
                }

                return MeshComponent;
            })}

            {showBoundingBox && (
                <group>
                    <box3Helper args={[globalBox, new THREE.Color('#06b6d4')]} />
                    <Html position={globalBox.max}>
                        <div className="bg-cyan-900/80 border border-cyan-500/50 text-cyan-300 text-[10px] font-mono px-2 py-1 rounded whitespace-nowrap shadow-xl backdrop-blur-md">
                            X: {((globalBox.max.x - globalBox.min.x) * autoScale).toFixed(1)}mm
                        </div>
                    </Html>
                    <Html position={[globalBox.min.x, globalBox.max.y, globalBox.max.z]}>
                        <div className="bg-cyan-900/80 border border-cyan-500/50 text-cyan-300 text-[10px] font-mono px-2 py-1 rounded whitespace-nowrap shadow-xl backdrop-blur-md">
                            Y: {((globalBox.max.y - globalBox.min.y) * autoScale).toFixed(1)}mm
                        </div>
                    </Html>
                    <Html position={[globalBox.max.x, globalBox.max.y, globalBox.min.z]}>
                        <div className="bg-cyan-900/80 border border-cyan-500/50 text-cyan-300 text-[10px] font-mono px-2 py-1 rounded whitespace-nowrap shadow-xl backdrop-blur-md">
                            Z: {((globalBox.max.z - globalBox.min.z) * autoScale).toFixed(1)}mm
                        </div>
                    </Html>
                </group>
            )}
        </group>
    );
}

function FallbackAssembly({ designData }: { designData: any }) {
    if (!designData || !designData.subsystems) return null;
    
    const nodes: any[] = [];
    const assemblyTransforms = designData.assembly_transforms || [];
    const assemblyMode = designData.assembly_mode || "side_by_side";
    
    designData.subsystems.forEach((sub: any, subIdx: number) => {
        const components = sub.components || [];
        components.forEach((comp: any, compIdx: number) => {
            const name = comp.name.toLowerCase();
            const role = (comp.role || "").toLowerCase();
            
            let size: [number, number, number] = [12, 12, 12];
            let color = "#94a3b8"; 
            
            if (name.includes("frame")) {
                size = [120, 6, 120];
                color = "#475569";
            } else if (name.includes("propeller") || name.includes("wing")) {
                size = [80, 2, 10];
                color = "#e2e8f0";
            } else if (name.includes("controller") || name.includes("mcu") || name.includes("arduino") || name.includes("raspberry") || name.includes("flight_controller")) {
                size = [24, 4, 16]; 
                color = "#a78bfa";
            } else if (name.includes("motor") || name.includes("actuator") || name.includes("servo") || name.includes("brushless_motor")) {
                size = [15, 18, 15]; 
                color = "#f97316";
            } else if (name.includes("sensor") || name.includes("imu") || name.includes("lidar")) {
                size = [6, 6, 6]; 
                color = "#22d3ee";
            } else if (name.includes("power") || name.includes("battery") || name.includes("supply") || name.includes("lipo_battery")) {
                size = [40, 15, 20]; 
                color = "#facc15";
            } else if (name.includes("display") || name.includes("screen") || name.includes("oled")) {
                size = [16, 10, 2]; 
                color = "#4ade80";
            }
            
            let position: [number, number, number] = [0, 0, 0];
            let rotation: [number, number, number] = [0, 0, 0];
            
            if (assemblyMode === "assembled" && assemblyTransforms.length > 0) {
                const match = assemblyTransforms.find((t: any) => t.id === comp.id);
                if (match) {
                    // Convert positions if they are scaled differently
                    position = match.position;
                    rotation = match.rotation;
                } else {
                    const x = (subIdx - (designData.subsystems.length - 1) / 2) * 50;
                    const y = compIdx * 25 + size[1] / 2;
                    position = [x, y, 0];
                }
            } else {
                const x = (subIdx - (designData.subsystems.length - 1) / 2) * 50;
                const y = compIdx * 25 + size[1] / 2;
                position = [x, y, 0];
            }
            
            nodes.push({
                id: comp.id || `cad-${subIdx}-${compIdx}`,
                name: comp.name,
                role: comp.role || "",
                size,
                color,
                position,
                rotation
            });
        });
    });
    
    return (
        <group position={[0, 10, 0]}>
            {nodes.map((node) => (
                <group key={node.id} position={node.position} rotation={node.rotation}>
                    <mesh castShadow receiveShadow>
                        <boxGeometry args={node.size} />
                        <meshStandardMaterial 
                            color={node.color} 
                            roughness={0.4} 
                            metalness={0.2} 
                        />
                    </mesh>
                    <mesh>
                        <boxGeometry args={[node.size[0] + 0.2, node.size[1] + 0.2, node.size[2] + 0.2]} />
                        <meshBasicMaterial 
                            color="#ffffff" 
                            wireframe 
                            transparent 
                            opacity={0.12} 
                        />
                    </mesh>
                </group>
            ))}
        </group>
    );
}

export function CADTab({ currentQuery, cadUrls, designData, onGeneratedCad }: CADTabProps) {
    const [meshes, setMeshes] = useState<LoadedMesh[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    
    // Advanced UX State
    const [explosion, setExplosion] = useState(0);
    const [hoveredMesh, setHoveredMesh] = useState<string | null>(null);
    const [selectedMesh, setSelectedMesh] = useState<string | null>(null);
    const [autoRotate, setAutoRotate] = useState(false);
    const [hiddenMeshes, setHiddenMeshes] = useState<Set<string>>(new Set());
    const [showBOM, setShowBOM] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");
    const [clipAxis, setClipAxis] = useState<'x'|'y'|'z'|null>(null);
    const [clipValue, setClipValue] = useState(50);
    const [isMeasuring, setIsMeasuring] = useState(false);
    const [measurePoints, setMeasurePoints] = useState<THREE.Vector3[]>([]);
    const [renderMode, setRenderMode] = useState(0); // 0=Styled, 1=Ghost, 2=Actual
    const [envPreset, setEnvPreset] = useState<"warehouse" | "studio" | "city" | "dawn">("warehouse");
    const [isAnnotating, setIsAnnotating] = useState(false);
    const [annotations, setAnnotations] = useState<Annotation[]>([]);
    
    // Jarvis Voice Control
    const [isListening, setIsListening] = useState(false);
    const [transcript, setTranscript] = useState('');
    
    // Generative Design & Interaction
    const [optimizedParts, setOptimizedParts] = useState<Set<string>>(new Set());
    const [activePivot, setActivePivot] = useState<string | null>(null);
    const [transformMode, setTransformMode] = useState<'translate' | 'rotate' | 'scale' | null>(null);
    const [partTransforms, setPartTransforms] = useState<Record<string, { position?: [number, number, number], rotation?: [number, number, number], scale?: [number, number, number] }>>({});
    const [transforming, setTransforming] = useState(false);
    
    // Engineering Analysis State
    const [showBoundingBox, setShowBoundingBox] = useState(false);
    const [magnetEnabled, setMagnetEnabled] = useState(true);
    
    const controlsRef = useRef<any>(null);

    const [generatingParts, setGeneratingParts] = useState<Record<string, string>>({});

    const handleGenerateCAD = async (partName: string) => {
        setGeneratingParts(prev => ({ ...prev, [partName]: "Initiating..." }));
        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            const filename = `${partName.replace(/[^a-zA-Z0-9_-]/g, "_")}.step`;
            
            setGeneratingParts(prev => ({ ...prev, [partName]: "Generating (Zoo AI)..." }));
            
            const response = await fetch(`${apiUrl}/api/generate-cad`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    prompt: partName,
                    filename: filename
                })
            });
            
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Zoo generation failed.");
            }
            
            const data = await response.json();
            if (data.cad_url) {
                setGeneratingParts(prev => {
                    const next = { ...prev };
                    delete next[partName];
                    return next;
                });
                if (onGeneratedCad) {
                    onGeneratedCad(data.cad_url);
                }
            }
        } catch (err: any) {
            console.error("Zoo generation error:", err);
            setGeneratingParts(prev => ({ ...prev, [partName]: `Error: ${err.message || err}` }));
        }
    };

    const autoScale = useMemo(() => {
        if (!meshes.length) return 1;
        const box = new THREE.Box3();
        meshes.forEach(m => {
            if (!m.geometry.boundingBox) {
                m.geometry.computeBoundingBox();
            }
            if (m.geometry.boundingBox) {
                box.union(m.geometry.boundingBox);
            }
        });
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        return maxDim > 0 ? 150 / maxDim : 1;
    }, [meshes]);

    // Jarvis Voice Command Engine
    useEffect(() => {
        if (!isListening) return;

        // @ts-ignore
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            alert("Voice commands are not supported in this browser.");
            setIsListening(false);
            return;
        }

        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onresult = (event: any) => {
            const current = event.resultIndex;
            const text = event.results[current][0].transcript.toLowerCase();
            setTranscript(text);

            if (text.includes("ghost") || text.includes("x-ray")) setRenderMode(1);
            else if (text.includes("actual") || text.includes("original") || text.includes("raw")) setRenderMode(2);
            else if (text.includes("thermal") || text.includes("heat")) setRenderMode(3);
            else if (text.includes("stress") || text.includes("structural")) setRenderMode(4);
            else if (text.includes("styled") || text.includes("default") || text.includes("normal") || text.includes("beautiful")) setRenderMode(0);
            else if (text.includes("explode") || text.includes("disassemble") || text.includes("blow apart")) setExplosion(prev => Math.min(prev + 40, 100));
            else if (text.includes("combine") || text.includes("assemble") || text.includes("together") || text.includes("reset")) setExplosion(0);
            else if (text.includes("rotate") || text.includes("spin") || text.includes("turn around")) setAutoRotate(true);
            else if (text.includes("stop") || text.includes("pause") || text.includes("halt")) setAutoRotate(false);
        };

        recognition.onerror = (event: any) => {
            if (event.error === 'not-allowed') {
                alert("Microphone access denied. Please ensure you are running on localhost or HTTPS, and have granted microphone permissions.");
            } else {
                console.warn("Speech recognition error:", event.error);
            }
            setIsListening(false);
        };

        recognition.start();

        return () => {
            recognition.stop();
        };
    }, [isListening]);

    const toggleMeshVisibility = (id: string) => {
        setHiddenMeshes(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    };

    const handleAddAnnotation = (pos: THREE.Vector3) => {
        const text = prompt("Enter annotation text:");
        if (text && text.trim()) {
            setAnnotations(prev => [...prev, {
                id: Math.random().toString(36).substring(7),
                position: pos.clone(),
                text: text.trim()
            }]);
        }
        setIsAnnotating(false);
    };

    const snapView = (view: 'front' | 'top' | 'side' | 'iso') => {
        if (!controlsRef.current) return;
        const dist = 300;
        const target = new THREE.Vector3(0, 50, 0);
        let pos = new THREE.Vector3();
        
        switch (view) {
            case 'front': pos.set(0, 50, dist); break;
            case 'top': pos.set(0, dist, 0); break;
            case 'side': pos.set(dist, 50, 0); break;
            case 'iso': pos.set(dist, dist, dist); break;
        }
        
        controlsRef.current.object.position.copy(pos);
        controlsRef.current.target.copy(target);
        controlsRef.current.update();
    };

    useEffect(() => {
        if (!cadUrls || cadUrls.length === 0) {
            setMeshes([]);
            return;
        }

        let isMounted = true;

        // Extract assembly transforms from designData if available
        const assemblyTransforms: Array<{id: string, part: string, cad_url: string, position: number[], rotation: number[]}> = 
            designData?.assembly_transforms || [];
        const assemblyMode = designData?.assembly_mode || "side_by_side";

        async function loadStepFiles() {
            setIsLoading(true);
            setError(null);
            
            try {
                // Dynamically import to avoid SSR issues
                // @ts-ignore
                const occtimportjs = (await import("occt-import-js")).default;
                
                // Initialize OCCT WebAssembly
                const occt = await occtimportjs({
                    locateFile: (name: string) => `/${name}`
                });

                const loadedMeshes: LoadedMesh[] = [];
                let globalMeshId = 0;

                // Load all step files concurrently — skip missing files gracefully
                const fetchPromises = cadUrls!.map(async (url, fileIndex) => {
                    try {
                        const fetchUrl = url.startsWith('/api') && process.env.NEXT_PUBLIC_API_URL 
                            ? `${process.env.NEXT_PUBLIC_API_URL}${url}` 
                            : url;
                        const res = await fetch(fetchUrl);
                        if (!res.ok) {
                            console.warn(`[CAD] Skipping unavailable file: ${url} (${res.status})`);
                            return;
                        }
                        const buffer = await res.arrayBuffer();
                        
                        const fileBuffer = new Uint8Array(buffer);
                        const result = occt.ReadStepFile(fileBuffer, null);
                        
                        if (!result || !result.meshes || result.meshes.length === 0) {
                            console.warn(`No valid meshes found in CAD file: ${url}`);
                            return;
                        }
                        
                        // Compute transform matrix — either from assembly engine or side-by-side fallback
                        let offsetMatrix: THREE.Matrix4;
                        let partName = url.split('/').pop()?.replace('.STEP', '').replace('.step', '').replace('.stp', '') || `Part_${fileIndex}`;
                        
                        // Match by index first since cadUrls and assemblyTransforms are in the same order.
                        // This avoids the duplicate .find() matching bug for identical parts.
                        let matchingTransform: typeof assemblyTransforms[0] | null = assemblyTransforms[fileIndex] || null;
                        
                        // Failsafe: if index match does not align with the URL, search the entire array
                        if (matchingTransform) {
                            const tUrl = matchingTransform.cad_url || '';
                            const cleanUrl = url.split('/').pop() || '';
                            const cleanTUrl = tUrl.split('/').pop() || '';
                            if (cleanUrl !== cleanTUrl) {
                                matchingTransform = assemblyTransforms.find(t => {
                                    const tu = t.cad_url || '';
                                    return url === tu || url.endsWith(tu.split('/').pop() || '___');
                                }) || null;
                            }
                        }
                        
                        if (assemblyMode === "assembled" && matchingTransform) {
                            // ASSEMBLY MODE: Apply computed transforms from the assembly engine
                            const pos = matchingTransform.position || [0, 0, 0];
                            const rot = matchingTransform.rotation || [0, 0, 0];
                            partName = matchingTransform.part || partName;
                            
                            const rotMatrix = new THREE.Matrix4().makeRotationFromEuler(
                                new THREE.Euler(rot[0], rot[1], rot[2], 'XYZ')
                            );
                            offsetMatrix = new THREE.Matrix4()
                                .multiply(rotMatrix)
                                .setPosition(pos[0], pos[1], pos[2]);
                                
                            console.log(`[CAD Assembly] ${partName} → pos=[${pos}] rot=[${rot.map((r: number) => (r * 180/Math.PI).toFixed(1))}°]`);
                        } else {
                            // FALLBACK: Side-by-side spacing
                            offsetMatrix = new THREE.Matrix4().makeTranslation(fileIndex * 150, 0, 0);
                        }

                        for (const m of result.meshes) {
                            const geometry = new THREE.BufferGeometry();
                            
                            geometry.setAttribute('position', new THREE.Float32BufferAttribute(m.attributes.position.array, 3));
                            if (m.attributes.normal) {
                                geometry.setAttribute('normal', new THREE.Float32BufferAttribute(m.attributes.normal.array, 3));
                            }
                            const index = Uint32Array.from(m.index.array);
                            geometry.setIndex(new THREE.BufferAttribute(index, 1));
                            
                            // Apply the transform (either assembly or spacing)
                            geometry.applyMatrix4(offsetMatrix);
                            
                            geometry.computeVertexNormals();
                            geometry.computeBoundingBox();
                            geometry.computeBoundingSphere();

                            let color = null;
                            if (m.color) {
                                color = new THREE.Color(m.color[0], m.color[1], m.color[2]);
                            }

                            loadedMeshes.push({
                                id: `mesh-${fileIndex}-${globalMeshId++}`,
                                geometry,
                                color,
                                name: m.name || partName || `Component ${globalMeshId}`
                            });
                        }
                    } catch (fileErr) {
                        console.warn(`[CAD] Error loading ${url}, skipping:`, fileErr);
                    }
                });

                await Promise.all(fetchPromises);

                if (isMounted) {
                    setMeshes(loadedMeshes);
                }
            } catch (err: any) {
                console.error("CAD load error:", err);
                if (isMounted) setError(err.message || "Failed to parse the CAD files.");
            } finally {
                if (isMounted) setIsLoading(false);
            }
        }

        loadStepFiles();

        return () => { isMounted = false; };
    }, [cadUrls, designData?.assembly_transforms, designData?.assembly_mode]);

    return (
        <div className="relative w-full h-full bg-[#060810] overflow-hidden rounded-xl border border-neutral-800 select-none">
            {/* Cinematic Controls Overlay */}
            {meshes.length > 0 && !isLoading && (
                <div className="absolute top-4 right-4 z-20 flex flex-col gap-3">
                    {/* View Controls */}
                    <div className="bg-neutral-900/80 backdrop-blur-md border border-neutral-800 rounded-lg shadow-xl p-2 flex flex-col gap-2">
                        <span className="text-[10px] uppercase font-bold text-neutral-500 px-1 tracking-wider">Camera</span>
                        <div className="grid grid-cols-2 gap-1">
                            <button onClick={() => snapView('front')} className="px-3 py-1.5 bg-neutral-800 hover:bg-blue-600/50 text-xs font-medium text-neutral-300 rounded transition-colors">Front</button>
                            <button onClick={() => snapView('top')} className="px-3 py-1.5 bg-neutral-800 hover:bg-blue-600/50 text-xs font-medium text-neutral-300 rounded transition-colors">Top</button>
                            <button onClick={() => snapView('side')} className="px-3 py-1.5 bg-neutral-800 hover:bg-blue-600/50 text-xs font-medium text-neutral-300 rounded transition-colors">Side</button>
                            <button onClick={() => snapView('iso')} className="px-3 py-1.5 bg-neutral-800 hover:bg-blue-600/50 text-xs font-medium text-neutral-300 rounded transition-colors">Iso</button>
                        </div>
                        <button onClick={() => setAutoRotate(!autoRotate)} className={`mt-1 flex items-center justify-center gap-2 px-3 py-2 rounded text-xs font-medium transition-colors ${autoRotate ? 'bg-blue-600 text-white shadow-[0_0_15px_rgba(37,99,235,0.4)]' : 'bg-neutral-800 text-neutral-300 hover:bg-neutral-700'}`}>
                            {autoRotate ? <Pause size={12} /> : <Play size={12} />}
                            {autoRotate ? 'Stop Rotation' : 'Auto-Rotate'}
                        </button>
                    </div>

                    <div className="bg-neutral-900/80 backdrop-blur-md border border-neutral-800 rounded-lg shadow-xl p-3 flex flex-col gap-2">
                        <span className="text-[10px] uppercase font-bold text-neutral-500 tracking-wider">Visuals</span>
                        <div className="flex flex-col gap-2">
                            <button 
                                onClick={() => setRenderMode((prev) => (prev + 1) % 5)}
                                className={`w-full flex items-center justify-center gap-2 px-3 py-2 rounded text-xs font-medium transition-colors ${
                                    renderMode === 1 ? 'bg-cyan-600/90 text-white shadow-[0_0_15px_rgba(8,145,178,0.4)]' : 
                                    renderMode === 2 ? 'bg-amber-600/90 text-white shadow-[0_0_15px_rgba(217,119,6,0.4)]' : 
                                    renderMode === 3 ? 'bg-rose-600/90 text-white shadow-[0_0_15px_rgba(225,29,72,0.4)]' :
                                    renderMode === 4 ? 'bg-indigo-600/90 text-white shadow-[0_0_15px_rgba(79,70,229,0.4)]' :
                                    'bg-neutral-800 text-neutral-300 hover:bg-neutral-700'
                                }`}
                                title="Toggle Render Mode: Styled -> Ghost -> Actual -> Thermal -> Stress"
                            >
                                <Ghost size={12} />
                                {renderMode === 1 ? 'Ghost Mode' : renderMode === 2 ? 'Actual CAD' : renderMode === 3 ? 'Thermal Analysis' : renderMode === 4 ? 'Stress Analysis' : 'Enable Advanced Render'}
                            </button>
                        </div>
                    </div>
                    



                    {selectedMesh && (
                        <div className="space-y-3 pt-4 border-t border-white/5 animate-in fade-in slide-in-from-left-4 duration-300">
                            <span className="text-[10px] uppercase font-bold text-cyan-500 tracking-wider">Part Selected</span>
                            <div className="flex flex-col gap-2">
                                <button 
                                    onClick={() => {
                                        setOptimizedParts(prev => {
                                            const next = new Set(prev);
                                            if (next.has(selectedMesh)) next.delete(selectedMesh);
                                            else next.add(selectedMesh);
                                            return next;
                                        });
                                    }}
                                    className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded text-xs font-medium bg-emerald-600/20 text-emerald-400 hover:bg-emerald-600/40 border border-emerald-500/30 transition-colors"
                                >
                                    <Box size={12} />
                                    {optimizedParts?.has(selectedMesh) ? "Restore Original Part" : "AI Topology Optimize"}
                                </button>
                                <button 
                                    onClick={() => setActivePivot(activePivot === selectedMesh ? null : selectedMesh)}
                                    className={`w-full flex items-center justify-center gap-2 px-3 py-2 rounded text-xs font-medium border transition-colors ${activePivot === selectedMesh ? 'bg-indigo-600/40 text-indigo-300 border-indigo-500/50' : 'bg-indigo-600/10 text-indigo-400 hover:bg-indigo-600/20 border-indigo-500/20'}`}
                                >
                                    <ListTree size={12} />
                                    {activePivot === selectedMesh ? "Lock Assembly" : "Unlock for Assembly"}
                                </button>
                                <p className="text-[9px] text-neutral-500 italic text-center mt-1">
                                    Double-click part to quick-unlock pivot.
                                </p>
                            </div>
                        </div>
                    )}
                    
                    <div className="space-y-3 pt-4 border-t border-white/5">
                        <div className="flex items-center justify-between">
                            <span className="text-[10px] uppercase font-bold text-neutral-500 tracking-wider">Annotation</span>
                            <button
                                onClick={() => setAnnotations([])}
                                className="text-[10px] text-red-400 hover:text-red-300"
                            >
                                Clear All
                            </button>
                        </div>
                        <button 
                            onClick={() => {
                                setIsAnnotating(!isAnnotating);
                                if (isMeasuring) setIsMeasuring(false);
                            }}
                            className={`w-full flex items-center justify-center gap-2 px-3 py-2 rounded text-xs font-medium transition-colors ${isAnnotating ? 'bg-purple-600 text-white shadow-[0_0_15px_rgba(147,51,234,0.4)]' : 'bg-neutral-800 text-neutral-300 hover:bg-neutral-700'}`}
                        >
                            <MessageSquare size={12} />
                            {isAnnotating ? 'Click model to add note' : 'Add Note'}
                        </button>
                    </div>

                    {/* Exploded View Slider */}
                    <div className="bg-neutral-900/80 backdrop-blur-md border border-neutral-800 rounded-lg shadow-xl p-3 flex flex-col gap-2">
                        <span className="text-[10px] uppercase font-bold text-neutral-500 tracking-wider">Environment Studio</span>
                        <div className="grid grid-cols-2 gap-1">
                            {(['warehouse', 'studio', 'city', 'dawn'] as const).map(preset => (
                                <button 
                                    key={preset}
                                    onClick={() => setEnvPreset(preset)}
                                    className={`px-2 py-1.5 rounded text-[10px] font-bold uppercase transition-colors ${envPreset === preset ? 'bg-indigo-600 text-white shadow-[0_0_10px_rgba(79,70,229,0.4)]' : 'bg-neutral-800 text-neutral-400 hover:bg-neutral-700'}`}
                                >
                                    {preset}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Exploded View Slider */}
                    <div className="bg-neutral-900/80 backdrop-blur-md border border-neutral-800 rounded-lg shadow-xl p-3 flex flex-col gap-2">
                        <div className="flex items-center justify-between">
                            <span className="text-[10px] uppercase font-bold text-neutral-500 tracking-wider">Exploded View</span>
                            <span className="text-[10px] text-blue-400 font-mono">{explosion}%</span>
                        </div>
                        <input 
                            type="range" 
                            min="0" 
                            max="100" 
                            value={explosion} 
                            onChange={(e) => setExplosion(parseInt(e.target.value))}
                            className="w-full accent-blue-500 h-1.5 bg-neutral-800 rounded-lg appearance-none cursor-pointer mt-1"
                        />
                    </div>

                    {/* Cross-Section Tool */}
                    <div className="bg-neutral-900/80 backdrop-blur-md border border-neutral-800 rounded-lg shadow-xl p-3 flex flex-col gap-2">
                        <div className="flex items-center justify-between">
                            <span className="text-[10px] uppercase font-bold text-neutral-500 tracking-wider">Cross-Section</span>
                            <div className="flex gap-1">
                                {(['x', 'y', 'z'] as const).map(axis => (
                                    <button 
                                        key={axis}
                                        onClick={() => setClipAxis(clipAxis === axis ? null : axis)}
                                        className={`w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold uppercase transition-colors ${clipAxis === axis ? 'bg-blue-600 text-white shadow-[0_0_10px_rgba(37,99,235,0.4)]' : 'bg-neutral-800 text-neutral-400 hover:bg-neutral-700'}`}
                                    >
                                        {axis}
                                    </button>
                                ))}
                            </div>
                        </div>
                        {clipAxis && (
                            <input 
                                type="range" 
                                min="0" 
                                max="100" 
                                value={clipValue} 
                                onChange={(e) => setClipValue(parseInt(e.target.value))}
                                className="w-full accent-blue-500 h-1.5 bg-neutral-800 rounded-lg appearance-none cursor-pointer mt-1"
                            />
                        )}
                    </div>

                    {/* Measurement Tool */}
                    <div className="bg-neutral-900/80 backdrop-blur-md border border-neutral-800 rounded-lg shadow-xl p-3 flex flex-col gap-2">
                        <div className="flex items-center justify-between">
                            <span className="text-[10px] uppercase font-bold text-neutral-500 tracking-wider">Distance Tool</span>
                        </div>
                        <button 
                            onClick={() => {
                                setIsMeasuring(!isMeasuring);
                                if (isMeasuring) setMeasurePoints([]);
                            }}
                            className={`w-full flex items-center justify-center gap-2 px-3 py-2 rounded text-xs font-medium transition-colors ${isMeasuring ? 'bg-yellow-600 text-white shadow-[0_0_15px_rgba(202,138,4,0.4)]' : 'bg-neutral-800 text-neutral-300 hover:bg-neutral-700'}`}
                        >
                            <Ruler size={12} />
                            {isMeasuring ? 'Measuring Active' : 'Measure Gap'}
                        </button>
                        {isMeasuring && measurePoints.length > 0 && (
                            <span className="text-[10px] text-neutral-400 text-center leading-tight">
                                {measurePoints.length === 1 ? 'Click 2nd point...' : 'Click to start new measurement'}
                            </span>
                        )}
                    </div>
                </div>
            )}

            {/* Loading Overlay */}
            {isLoading && (
                <div className="absolute inset-0 z-30 flex flex-col items-center justify-center bg-[#060810]/85 backdrop-blur-md gap-4">
                    <Loader2 size={40} className="text-blue-500 animate-spin" />
                    <div className="flex flex-col items-center gap-1">
                        <span className="text-blue-400 text-sm font-medium">Parsing High-Fidelity B-Rep CAD...</span>
                        <span className="text-blue-500/60 text-xs text-center max-w-xs">Using WebAssembly to render exact continuous surfaces directly from the .stp file.</span>
                    </div>
                </div>
            )}

            {/* Error Overlay */}
            {error && !isLoading && (
                <div className="absolute inset-0 z-30 flex flex-col items-center justify-center bg-[#060810]/85 backdrop-blur-md gap-4">
                    <Info size={40} className="text-red-500" />
                    <span className="text-red-400 text-sm font-medium px-6 text-center">{error}</span>
                </div>
            )}

            {/* Empty State Overlay */}
            {(!cadUrls || cadUrls.length === 0) && !designData && !isLoading && !error && (
                <div className="absolute inset-0 z-30 flex flex-col items-center justify-center bg-[#060810]/50 backdrop-blur-sm gap-4">
                    <Box size={40} className="text-neutral-500" />
                    <span className="text-neutral-400 text-sm font-medium">No 3D CAD available for this model yet.</span>
                </div>
            )}

            {/* 3D Canvas */}
            <div className="w-full h-full">
                <Canvas camera={{ position: [200, 150, 250], fov: 45 }} gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.1, localClippingEnabled: true }}>
                    <color attach="background" args={['#0e1117']} />
                    
                    <ambientLight intensity={0.5} color="#ffffff" />
                    <spotLight position={[100, 300, 100]} intensity={1.5} angle={0.5} penumbra={1} castShadow color="#fffaf0" />
                    <directionalLight position={[-150, 50, -150]} intensity={1.2} color="#88bbee" />
                    
                    <Environment preset={envPreset} />

                    {/* Classic CAD Grid */}
                    <Grid 
                        infiniteGrid 
                        fadeDistance={1000} 
                        cellColor="#4b5563" 
                        sectionColor="#6b7280"
                        cellThickness={0.7}
                        sectionThickness={1.2}
                        cellSize={10}
                        sectionSize={50}
                        position={[0, -0.01, 0]}
                    />

                    {/* Infinite X Axis (Red) */}
                    <mesh position={[0, -0.005, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                        <planeGeometry args={[2000, 0.4]} />
                        <meshBasicMaterial color="#cc2222" toneMapped={false} transparent opacity={0.6} />
                    </mesh>

                    {/* Infinite Z Axis (Green) */}
                    <mesh position={[0, -0.005, 0]} rotation={[-Math.PI / 2, 0, Math.PI / 2]}>
                        <planeGeometry args={[2000, 0.4]} />
                        <meshBasicMaterial color="#22cc22" toneMapped={false} transparent opacity={0.6} />
                    </mesh>

                    <ContactShadows position={[0, 0, 0]} opacity={0.75} scale={300} blur={2} far={100} resolution={1024} color="#000000" />

                    <Suspense fallback={null}>
                        {meshes.length > 0 ? (
                            <PivotControls 
                                activeAxes={[true, true, true]} 
                                depthTest={false} 
                                scale={80} 
                                anchor={[0, -1, 0]}
                                lineWidth={3}
                            >
                                <Center bottom>
                                    <CADModel 
                                        meshes={meshes} 
                                        url={cadUrls ? cadUrls[0] : ''}
                                        explosion={explosion}
                                        hoveredMesh={hoveredMesh}
                                        setHoveredMesh={setHoveredMesh}
                                        selectedMesh={selectedMesh}
                                        setSelectedMesh={setSelectedMesh}
                                        hiddenMeshes={hiddenMeshes}
                                        clipAxis={clipAxis}
                                        clipValue={clipValue}
                                        autoScale={autoScale}
                                        isMeasuring={isMeasuring}
                                        measurePoints={measurePoints}
                                        setMeasurePoints={setMeasurePoints}
                                        renderMode={renderMode}
                                        isAnnotating={isAnnotating}
                                        onAddAnnotation={handleAddAnnotation}
                                        optimizedParts={optimizedParts}
                                        activePivot={activePivot}
                                        setActivePivot={setActivePivot}
                                        transformMode={transformMode}
                                        partTransforms={partTransforms}
                                        setPartTransforms={setPartTransforms}
                                        setTransforming={setTransforming}
                                        showBoundingBox={showBoundingBox}
                                        magnetEnabled={magnetEnabled}
                                    />
                                </Center>
                            </PivotControls>
                        ) : (
                            designData && <FallbackAssembly designData={designData} />
                        )}
                    </Suspense>

                    {/* Measurement Visuals */}
                    {measurePoints.map((p, i) => (
                        <mesh key={i} position={p}>
                            <sphereGeometry args={[1.5, 16, 16]} />
                            <meshBasicMaterial color="#eab308" depthTest={false} />
                        </mesh>
                    ))}
                    {measurePoints.length === 2 && (
                        <>
                            <Line 
                                points={[measurePoints[0], measurePoints[1]]} 
                                color="#eab308" 
                                lineWidth={2}
                                dashed
                                dashScale={10}
                                dashSize={2}
                                gapSize={1}
                                depthTest={false}
                            />
                            <Html position={measurePoints[0].clone().lerp(measurePoints[1], 0.5)} center zIndexRange={[100, 0]}>
                                <div className="bg-neutral-900/90 text-yellow-400 font-mono text-xs px-2 py-1 rounded border border-yellow-700/50 shadow-xl pointer-events-none whitespace-nowrap">
                                    {(measurePoints[0].distanceTo(measurePoints[1]) / autoScale).toFixed(2)} units
                                </div>
                            </Html>
                        </>
                    )}

                    {/* Annotations Visuals */}
                    {annotations.map(ann => (
                        <Html key={ann.id} position={ann.position} center zIndexRange={[100, 0]}>
                            <div className="flex flex-col items-center">
                                <div className="bg-blue-600/90 backdrop-blur-sm text-white font-medium text-[10px] px-2 py-1.5 rounded shadow-xl max-w-[150px] break-words pointer-events-auto border border-blue-400/30">
                                    {ann.text}
                                </div>
                                <div className="w-0 h-0 border-l-[4px] border-l-transparent border-r-[4px] border-r-transparent border-t-[6px] border-t-blue-600/90"></div>
                            </div>
                        </Html>
                    ))}

                    <CameraFlyTo selectedMesh={selectedMesh} meshes={meshes} controlsRef={controlsRef} />
                    <OrbitControls 
                        ref={controlsRef}
                        makeDefault 
                        enableDamping={!transforming} 
                        enabled={!transforming}
                        dampingFactor={0.05} 
                        minDistance={5} 
                        maxDistance={1000} 
                        target={[0, 50, 0]}
                        autoRotate={autoRotate && !transforming}
                        autoRotateSpeed={1.5}
                    />

                    <GizmoHelper alignment="top-right" margin={[40, 40]}>
                        <GizmoViewport axisColors={['#ff3653', '#8adb00', '#2c8fdf']} labelColor="white" />
                    </GizmoHelper>
                </Canvas>
            </div>

            {/* Component Count & BOM Toggle */}
            {(meshes.length > 0 || (designData?.missing && designData.missing.length > 0)) ? (
                <div className="absolute top-4 left-4 z-20 flex flex-col gap-2">
                    <button 
                        onClick={() => setShowBOM(!showBOM)}
                        className={`flex items-center gap-2 px-3 py-2 rounded-lg border shadow-xl backdrop-blur-md transition-colors ${showBOM ? 'bg-blue-600/90 border-blue-500 text-white' : 'bg-neutral-900/80 border-neutral-800 text-neutral-200 hover:bg-neutral-800'}`}
                    >
                        <ListTree size={16} />
                        <span className="text-xs font-medium">Assembly Tree ({meshes.length})</span>
                    </button>
                    
                    {showBOM && (
                        <div className="w-64 max-h-[60vh] bg-neutral-900/90 backdrop-blur-md border border-neutral-800 rounded-lg shadow-xl overflow-hidden flex flex-col">
                            <div className="p-3 border-b border-neutral-800 flex items-center justify-between">
                                <span className="text-[10px] uppercase tracking-widest text-neutral-500 font-bold">Bill of Materials</span>
                                <button 
                                    onClick={() => setHiddenMeshes(new Set())}
                                    className="text-[10px] text-blue-400 hover:text-blue-300 transition-colors"
                                >
                                    Show All
                                </button>
                            </div>
                            <div className="p-2 border-b border-neutral-800">
                                <input 
                                    type="text" 
                                    placeholder="Search components..." 
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="w-full bg-black/40 border border-neutral-700/50 rounded px-2 py-1.5 text-xs text-white placeholder-neutral-500 focus:outline-none focus:border-blue-500 transition-colors"
                                />
                            </div>
                            <div className="overflow-y-auto flex-1 p-2 flex flex-col gap-1 custom-scrollbar">
                                {meshes.filter(m => m.name.toLowerCase().includes(searchQuery.toLowerCase())).map(mesh => {
                                    const isHidden = hiddenMeshes.has(mesh.id);
                                    const isSelected = selectedMesh === mesh.id;
                                    const isHovered = hoveredMesh === mesh.id;
                                    
                                    return (
                                        <div 
                                            key={mesh.id}
                                            className={`flex items-center justify-between px-2 py-1.5 rounded transition-colors cursor-pointer ${isSelected ? 'bg-blue-600/20 border border-blue-500/30' : isHovered ? 'bg-neutral-800' : 'hover:bg-neutral-800/50 border border-transparent'}`}
                                            onMouseEnter={() => setHoveredMesh(mesh.id)}
                                            onMouseLeave={() => setHoveredMesh(null)}
                                            onClick={() => setSelectedMesh(isSelected ? null : mesh.id)}
                                        >
                                            <span className={`text-xs truncate max-w-[140px] ${isHidden ? 'text-neutral-500 line-through' : 'text-neutral-300'}`}>
                                                {mesh.name}
                                            </span>
                                            <button 
                                                className="text-neutral-500 hover:text-neutral-300 transition-colors p-1"
                                                onClick={(e) => { e.stopPropagation(); toggleMeshVisibility(mesh.id); }}
                                            >
                                                {isHidden ? <EyeOff size={14} /> : <Eye size={14} />}
                                            </button>
                                        </div>
                                    );
                                })}
                            </div>
                            
                            {designData?.missing && designData.missing.length > 0 && (
                                <div className="p-3 border-t border-neutral-800 flex flex-col gap-2">
                                    <span className="text-[10px] uppercase tracking-widest text-red-400 font-bold">Missing Parts (No CAD)</span>
                                    <div className="flex flex-col gap-1.5 max-h-[20vh] overflow-y-auto custom-scrollbar">
                                        {designData.missing.map((item: any, idx: number) => {
                                            const partName = item.name;
                                            const status = generatingParts[partName];
                                            return (
                                                <div key={idx} className="flex flex-col gap-1 p-2 bg-neutral-950/60 rounded border border-neutral-800/60">
                                                    <span className="text-[11px] text-neutral-300 font-medium truncate" title={partName}>
                                                        {partName}
                                                    </span>
                                                    {status ? (
                                                        <span className="text-[10px] text-yellow-500 animate-pulse font-mono">
                                                            {status}
                                                        </span>
                                                    ) : (
                                                        <button 
                                                            onClick={() => handleGenerateCAD(partName)}
                                                            className="text-[10px] text-left text-blue-400 hover:text-blue-300 font-medium transition-colors hover:underline"
                                                        >
                                                            ⚡ Generate with Zoo AI
                                                        </button>
                                                    )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            ) : (
                designData && (
                    <div className="absolute top-4 left-4 z-10 flex flex-col gap-2">
                        <div className="flex items-center gap-2 px-3 py-2 bg-neutral-900/80 backdrop-blur-md border border-neutral-800 rounded-lg shadow-xl">
                            <Box size={14} className="text-purple-400" />
                            <span className="text-xs font-medium text-neutral-200">
                                3D Block Assembly Generated
                            </span>
                        </div>
                    </div>
                )
            )}
            
            {/* Inspector Sidebar for Component Mapping */}
            {selectedMesh && (
                <div className="absolute top-0 right-0 h-full w-80 bg-neutral-900/95 backdrop-blur-xl border-l border-neutral-800 shadow-2xl z-30 flex flex-col transform transition-transform duration-300 ease-in-out translate-x-0">
                    {(() => {
                        const activeMesh = meshes.find(m => m.id === selectedMesh);
                        if (!activeMesh) return null;
                        const data = getComponentData(activeMesh.name);
                        return (
                            <div className="h-full flex flex-col p-5 overflow-y-auto custom-scrollbar">
                                <div className="flex justify-between items-center mb-6">
                                    <div className="flex items-center gap-2">
                                        <Info size={16} className="text-cyan-400" />
                                        <h3 className="text-xs uppercase tracking-widest text-neutral-400 font-bold">Component Inspector</h3>
                                    </div>
                                    <button onClick={() => setSelectedMesh(null)} className="text-neutral-500 hover:text-white transition-colors">✕</button>
                                </div>
                                
                                <h2 className="text-lg font-bold text-white mb-2">{activeMesh.name}</h2>
                                <p className="text-xs text-neutral-400 mb-6 pb-4 border-b border-neutral-800">
                                    {data.function}
                                </p>
                                
                                <h4 className="text-[10px] uppercase font-bold text-neutral-500 tracking-wider mb-3">Transformation Tools</h4>
                                <div className="grid grid-cols-3 gap-2 mb-6">
                                    <button 
                                        onClick={() => setTransformMode(transformMode === 'translate' ? null : 'translate')}
                                        className={`flex flex-col items-center justify-center gap-1 p-2 rounded border transition-colors ${transformMode === 'translate' ? 'bg-cyan-600/90 border-cyan-400 text-white' : 'bg-black/40 border-neutral-800/50 text-neutral-400 hover:bg-neutral-800'}`}
                                    >
                                        <Move size={16} />
                                        <span className="text-[10px] font-medium">Move</span>
                                    </button>
                                    <button 
                                        onClick={() => setTransformMode(transformMode === 'rotate' ? null : 'rotate')}
                                        className={`flex flex-col items-center justify-center gap-1 p-2 rounded border transition-colors ${transformMode === 'rotate' ? 'bg-amber-600/90 border-amber-400 text-white' : 'bg-black/40 border-neutral-800/50 text-neutral-400 hover:bg-neutral-800'}`}
                                    >
                                        <RotateCw size={16} />
                                        <span className="text-[10px] font-medium">Rotate</span>
                                    </button>
                                    <button 
                                        onClick={() => setTransformMode(transformMode === 'scale' ? null : 'scale')}
                                        className={`flex flex-col items-center justify-center gap-1 p-2 rounded border transition-colors ${transformMode === 'scale' ? 'bg-rose-600/90 border-rose-400 text-white' : 'bg-black/40 border-neutral-800/50 text-neutral-400 hover:bg-neutral-800'}`}
                                    >
                                        <Maximize2 size={16} />
                                        <span className="text-[10px] font-medium">Stretch</span>
                                    </button>
                                </div>
                                <button
                                    onClick={() => setMagnetEnabled(!magnetEnabled)}
                                    className={`w-full flex items-center justify-center gap-2 mb-6 px-3 py-2 rounded text-xs font-medium border transition-colors ${magnetEnabled ? 'bg-fuchsia-600/40 border-fuchsia-500 text-fuchsia-300 shadow-[0_0_15px_rgba(192,38,211,0.3)]' : 'bg-black/40 border-neutral-800/50 text-neutral-400 hover:bg-neutral-800'}`}
                                >
                                    <Magnet size={14} />
                                    {magnetEnabled ? "Magnet Snap: ON" : "Magnet Snap: OFF"}
                                </button>
                                
                                <h4 className="text-[10px] uppercase font-bold text-neutral-500 tracking-wider mb-3">Specifications</h4>
                                <div className="bg-black/40 rounded border border-neutral-800/50 p-3 flex flex-col gap-2 mb-6">
                                    {data.specs.map((spec, i) => (
                                        <div key={i} className="flex justify-between items-center text-xs">
                                            <span className="text-neutral-500">{spec.label}</span>
                                            <span className="text-cyan-300 font-mono text-right">{spec.value}</span>
                                        </div>
                                    ))}
                                </div>

                                <h4 className="text-[10px] uppercase font-bold text-neutral-500 tracking-wider mb-3">Economics</h4>
                                <div className="bg-black/40 rounded border border-neutral-800/50 p-3 flex flex-col gap-2 mb-6">
                                    <div className="flex justify-between items-center text-xs">
                                        <span className="text-neutral-500">MSRP</span>
                                        <span className="text-emerald-400 font-bold">{data.cost}</span>
                                    </div>
                                    <div className="flex justify-between items-center text-xs">
                                        <span className="text-neutral-500">Manufacturer</span>
                                        <span className="text-white">{data.manufacturer}</span>
                                    </div>
                                </div>

                                <h4 className="text-[10px] uppercase font-bold text-neutral-500 tracking-wider mb-3">Alternatives</h4>
                                <div className="flex flex-wrap gap-2 mb-8">
                                    {data.alternatives.map((alt, i) => (
                                        <span key={i} className="px-2 py-1 bg-neutral-800 border border-neutral-700 rounded text-[10px] text-neutral-300 hover:bg-neutral-700 hover:text-white cursor-pointer transition-colors">
                                            {alt}
                                        </span>
                                    ))}
                                </div>

                                <div className="mt-auto">
                                    <a 
                                        href={data.datasheet}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="w-full flex items-center justify-center gap-2 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded font-medium text-xs transition-colors"
                                    >
                                        <Box size={14} />
                                        View Datasheet (PDF)
                                    </a>
                                </div>
                            </div>
                        );
                    })()}
                </div>
            )}
            
            {/* Central Toolbar */}
            <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2 z-20">
                <div className="flex items-center gap-1 p-1.5 bg-neutral-900/80 backdrop-blur-xl border border-neutral-800 rounded-2xl shadow-2xl">
                    <button 
                        onClick={() => setAutoRotate(!autoRotate)}
                        className={`p-2.5 rounded-xl transition-all ${autoRotate ? 'bg-blue-600/20 text-blue-400' : 'text-neutral-400 hover:text-white hover:bg-neutral-800'}`}
                        title="Auto Rotate"
                    >
                        <RotateCw size={18} />
                    </button>
                    <div className="w-px h-6 bg-neutral-800 mx-1" />
                    <button 
                        onClick={() => setIsMeasuring(!isMeasuring)}
                        className={`p-2.5 rounded-xl transition-all ${isMeasuring ? 'bg-amber-600/20 text-amber-400' : 'text-neutral-400 hover:text-white hover:bg-neutral-800'}`}
                        title="Measure Distance"
                    >
                        <Ruler size={18} />
                    </button>
                    <button 
                        onClick={() => setRenderMode((renderMode + 1) % 3)}
                        className={`p-2.5 rounded-xl transition-all ${renderMode === 1 ? 'bg-purple-600/20 text-purple-400' : renderMode === 2 ? 'bg-orange-600/20 text-orange-400' : 'text-neutral-400 hover:text-white hover:bg-neutral-800'}`}
                        title={renderMode === 0 ? "Standard View" : renderMode === 1 ? "Ghost View" : "Original CAD View"}
                    >
                        <Layers size={18} />
                    </button>
                    <div className="w-px h-6 bg-neutral-800 mx-1" />
                    <button 
                        onClick={() => setShowBoundingBox(!showBoundingBox)}
                        className={`p-2.5 rounded-xl transition-all ${showBoundingBox ? 'bg-cyan-600/20 text-cyan-400' : 'text-neutral-400 hover:text-white hover:bg-neutral-800'}`}
                        title="Bounding Box & Clearances"
                    >
                        <BoxSelect size={18} />
                    </button>
                    <div className="w-px h-6 bg-neutral-800 mx-1" />
                    <button 
                        onClick={() => setExplosion(explosion === 0 ? 50 : 0)}
                        className={`p-2.5 rounded-xl transition-all ${explosion > 0 ? 'bg-orange-600/20 text-orange-400' : 'text-neutral-400 hover:text-white hover:bg-neutral-800'}`}
                        title="Exploded View"
                    >
                        <Network size={18} />
                    </button>
                    <button 
                        onClick={() => setClipAxis(clipAxis ? null : 'x')}
                        className={`p-2.5 rounded-xl transition-all ${clipAxis ? 'bg-emerald-600/20 text-emerald-400' : 'text-neutral-400 hover:text-white hover:bg-neutral-800'}`}
                        title="Cross Section"
                    >
                        <Scissors size={18} />
                    </button>
                </div>
                
                {/* Secondary Panels (Clipping & Explosion Sliders) */}
                {(clipAxis || explosion > 0) && (
                    <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-4 w-64 p-3 bg-neutral-900/90 backdrop-blur-xl border border-neutral-800 rounded-xl shadow-xl flex flex-col gap-3">
                        {clipAxis && (
                            <div className="flex flex-col gap-2">
                                <div className="flex items-center justify-between">
                                    <span className="text-[10px] uppercase font-bold tracking-widest text-neutral-500">Section Plane</span>
                                    <div className="flex gap-1">
                                        {['x', 'y', 'z'].map(axis => (
                                            <button 
                                                key={axis}
                                                onClick={() => setClipAxis(axis as 'x'|'y'|'z')}
                                                className={`px-2 py-0.5 rounded text-[10px] uppercase ${clipAxis === axis ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-neutral-800 text-neutral-400 hover:text-white'}`}
                                            >
                                                {axis}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                                <input 
                                    type="range" 
                                    min="0" max="100" 
                                    value={clipValue} 
                                    onChange={(e) => setClipValue(parseInt(e.target.value))}
                                    className="w-full accent-emerald-500"
                                />
                            </div>
                        )}
                        {explosion > 0 && (
                            <div className="flex flex-col gap-2">
                                <div className="flex items-center justify-between">
                                    <span className="text-[10px] uppercase font-bold tracking-widest text-neutral-500">Explode Assembly</span>
                                    <span className="text-[10px] text-orange-400 font-mono">{explosion}%</span>
                                </div>
                                <input 
                                    type="range" 
                                    min="0" max="100" 
                                    value={explosion} 
                                    onChange={(e) => setExplosion(parseInt(e.target.value))}
                                    className="w-full accent-orange-500"
                                />
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Status Info */}
            <div className="absolute bottom-4 left-4 z-10 pointer-events-none">
                <div className="px-3 py-1.5 bg-blue-900/30 border border-blue-500/30 rounded-full flex items-center gap-2 backdrop-blur-sm">
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                    <span className="text-[10px] font-medium text-blue-300">WASM Parser Active</span>
                </div>
            </div>
        </div>
    );
}
