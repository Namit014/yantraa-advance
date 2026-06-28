"""
cad_registry.py — Maps CAD aliases to filenames and S3 paths

S3 Structure:
  s3://yantraa-labs-bucket/knowledgebase/
    Hebi_CAD/Actuators/           → HEBI actuator STEP files
    Hebi_CAD/End_Effectors/       → HEBI gripper STEP files
    Hebi_CAD/Electronics_and_Power/ → HEBI electronics STEP files
    Hebi_CAD/Structural_and_Mounts/ → HEBI bracket/adapter STEP files
    Hebi_CAD/Sensors/             → HEBI sensor STEP files
    delta_robot/delta_robot_cad/  → DeltaRobot2.STEP
    scara_robot/scara_robot_cad/  → scara_robot_cad.stp
    welding_robot/welding_robot_cad/ → welding_robot.stp
    Machine_Tending_Robot/        → machine_tending_robot.stp
    Painting_Robot/               → Painting_Robot.step
    Palletizing_Robot/            → palletizing_robot.STEP
    inspection_robot/             → inspection_robot_cad.STEP
    openarm/cad/openarm_cad/      → OpenArm_2.0.STEP etc.
    rm_models/                    → ECO/RM/RX series arm STEPs
    reBot-DevArm/                 → reBot_B601_DM_v1.1.step
"""

import os
import json
import boto3
from botocore.exceptions import ClientError

# ── Alias → filename mapping ──────────────────────────────────────────────────
# Maps user-facing keywords to the exact filename in S3/knowledgebase
KNOWN_CADS = {
    # Robotic Arm / Manipulator
    "arm": "Robotic_Arm.stp",
    "robotic arm": "Robotic_Arm.stp",
    "6dof arm": "Robotic_Arm.stp",
    "6 dof arm": "Robotic_Arm.stp",
    "manipulator": "Robotic_Arm.stp",
    "articulated": "Robotic_Arm.stp",
    "cobot": "Robotic_Arm.stp",
    "collaborative": "Robotic_Arm.stp",
    "fanuc": "FANUC-430_Robot.STEP",

    # AGV / Mobile / Automation
    "agv": "Klebe_und_Schweissroboteranlage_Reis-01.stp",
    "autonomous mobile": "Klebe_und_Schweissroboteranlage_Reis-01.stp",
    "amr": "Klebe_und_Schweissroboteranlage_Reis-01.stp",
    "mobile robot": "Klebe_und_Schweissroboteranlage_Reis-01.stp",
    "machine tending": "Klebe_und_Schweissroboteranlage_Reis-01.stp",

    # Delta
    "delta": "delta_robot.stp",
    "delta robot": "delta_robot.stp",
    "delta drawing": "Delta_Drawing_Robot.STEP",
    "parallel": "delta_robot.stp",
    
    # Hexapod
    "hexapod": "hexapod.stp",
    "stewart": "hexapod.stp",

    # Cartesian / SCARA
    "scara": "SCARA_ROBOTIC_ASSEMBLY.STEP",
    "cartesian": "SCARA_ROBOTIC_ASSEMBLY.STEP",
    "gantry": "SCARA_ROBOTIC_ASSEMBLY.STEP",

    # Welding
    "welding": "JIG_WELDING.stp",
    "welding robot": "JIG_WELDING.stp",
    "aluminium welding": "Aluminium_welding.STEP",
    "jig welding": "JIG_WELDING.stp",
    "pallet welding": "PALLET_WELDING.stp",

    # Humanoid
    "humanoid": "HUMANOID.stp",
    "bipedal": "HUMANOID.stp",
    "android": "HUMANOID.stp",

    # Other Robots
    "painting": "Robotic_Arm.stp",
    "inspection": "hexapod.stp",
    "palletizing": "PALLET_WELDING.stp",
    
    # Drone
    "drone": "quadcopter_frame.step",
    "quadcopter": "quadcopter_frame.step",
    "uav": "quadcopter_frame.step",
}

# ── S3 path index: filename (lowercase) → S3 key under bucket root ──────────
# This tells assembly_engine and design.py exactly which S3 path to use.
S3_FILE_INDEX = {
    # HEBI Actuators
    "a-2020-05.step":                          "knowledgebase/Hebi_CAD/Actuators/A-2020-05.STEP",
    "a-2020-08.step":                          "knowledgebase/Hebi_CAD/Actuators/A-2020-08.STEP",
    "a-2200-08.step":                          "knowledgebase/Hebi_CAD/Actuators/A-2200-08.STEP",
    "a-2269-01_r-series_double_shoulder.step": "knowledgebase/Hebi_CAD/Actuators/A-2269-01_R-Series_Double_Shoulder.STEP",
    "a-2475-05.step":                          "knowledgebase/Hebi_CAD/Actuators/A-2475-05.STEP",
    "a-2475-08.step":                          "knowledgebase/Hebi_CAD/Actuators/A-2475-08.STEP",  # closest match — use 08 for T8
    "a-2438-02.step":                          "knowledgebase/Hebi_CAD/Actuators/A-2475-05.STEP",  # fallback to T5
    "a-2488-25-xx.step":                       "knowledgebase/Hebi_CAD/Actuators/A-2488-25-XX.STEP",

    # HEBI End Effectors
    "a-2055-01_gripper_assembly.step":         "knowledgebase/Hebi_CAD/End_Effectors/A-2055-01_Gripper_Assembly.STEP",
    "a-2143-02.step":                          "knowledgebase/Hebi_CAD/End_Effectors/A-2143-02.STEP",

    # HEBI Electronics
    "a-2433-01_motor_driver_rj45.step":        "knowledgebase/Hebi_CAD/Electronics_and_Power/A-2463-01.STEP",
    "a-2525-01.step":                          "knowledgebase/Hebi_CAD/Electronics_and_Power/A-2473-01.STEP",
    "a-2432-01.step":                          "knowledgebase/Hebi_CAD/Electronics_and_Power/A-2545-01_IO_Utility_Board.STEP",

    # HEBI Structural
    "a-2221-01_heavy_right_angle_bracket_inside.step": "knowledgebase/Hebi_CAD/Structural_and_Mounts/A-2221-01_Heavy_Right_Angle_Bracket_Inside.STEP",
    "a-2220-01_light_right_angle_bracket.step":        "knowledgebase/Hebi_CAD/Structural_and_Mounts/A-2220-01_Light_Right_Angle_Bracket.STEP",
    "a-2218-01_output_tube_adapter.step":              "knowledgebase/Hebi_CAD/Structural_and_Mounts/A-2218-01_Output_Tube_Adapter.STEP",
    "a-2219-01_input_tube_adapter.step":               "knowledgebase/Hebi_CAD/Structural_and_Mounts/A-2219-01_Input_Tube_Adapter.STEP",
    "a-2096-02_six_tube_adapter.step":                 "knowledgebase/Hebi_CAD/Structural_and_Mounts/A-2096-02_Six_Tube_Adapter.STEP",
    "a-2228-01_t-slot_right_angle_adapter.step":       "knowledgebase/Hebi_CAD/Structural_and_Mounts/A-2228-01_T-Slot_Right_Angle_Adapter.STEP",
    "a-2227-01_wheel_adapter.step":                    "knowledgebase/Hebi_CAD/Structural_and_Mounts/A-2227-01_Wheel_Adapter.STEP",

    # Whole-robot STEP files
    "deltarobot2.step":                        "knowledgebase/delta_robot/delta_robot_cad/DeltaRobot2.STEP",
    "scara_robot_cad.stp":                     "knowledgebase/scara_robot/scara_robot_cad/scara_robot_cad.stp",
    "welding_robot.stp":                       "knowledgebase/welding_robot/welding_robot_cad/welding_robot.stp",
    "painting_robot.step":                     "knowledgebase/Painting_Robot/Painting_Robot.step",
    "machine_tending_robot.stp":               "knowledgebase/Machine_Tending_Robot/machine_tending_robot.stp",
    "inspection_robot_cad.step":               "knowledgebase/inspection_robot/inspection_robot_cad.STEP",
    "openarm_2.0.step":                        "knowledgebase/openarm/cad/openarm_cad/OpenArm_2.0.STEP",
    "rm65-6f_robot_model.step":                "knowledgebase/rm_models/RM65-6F_robot_model.STEP",
    "rm65-b_robot_model.step":                 "knowledgebase/rm_models/RM65-B_robot_model.STEP",
    "eco63-6f_robot_model.step":               "knowledgebase/rm_models/ECO63-6F_robot_model.STEP",
    "rebot_b601_dm_v1.1_20260425.step":        "knowledgebase/reBot-DevArm/reBot_B601_DM_v1.1_20260425.step",
}


def get_s3_url(filename: str, s3_base_url: str) -> str:
    """
    Build the correct S3 URL for a given STEP filename.
    If AWS credentials are provided, generates a 15-minute pre-signed URL.
    Otherwise, builds a standard public URL.
    """
    key = filename.lower()
    s3_path = S3_FILE_INDEX.get(key)

    # Partial match fallback
    if not s3_path:
        base_noext = os.path.splitext(key)[0]
        for idx_key, idx_path in S3_FILE_INDEX.items():
            if os.path.splitext(idx_key)[0] == base_noext:
                s3_path = idx_path
                break

    # Final fallback if still not found
    if not s3_path:
        s3_path = f"knowledgebase/{filename}"
        print(f"[cad_registry] No S3 index match for {filename!r}, using generic path: {s3_path}")

    # Check for AWS credentials to generate a pre-signed URL
    bucket_name = os.getenv("S3_BUCKET_NAME")
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region_name = os.getenv("AWS_REGION", "ap-south-1")

    if bucket_name and aws_access_key_id and aws_secret_access_key:
        try:
            s3_client = boto3.client(
                's3',
                region_name=region_name,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key
            )
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': s3_path},
                ExpiresIn=900  # 15 minutes
            )
            print(f"[cad_registry] Generated pre-signed URL for {s3_path}")
            return presigned_url
        except Exception as e:
            print(f"[cad_registry] Error generating pre-signed URL: {e}")

    # Fallback to public URL (if pre-signing fails or keys are missing)
    if not s3_base_url and bucket_name:
        s3_base_url = f"https://{bucket_name}.s3.{region_name}.amazonaws.com"
        
    url = f"{s3_base_url}/{s3_path}"
    print(f"[cad_registry] Using public S3 URL for {s3_path}")
    return url


_hebi_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "knowledgebase", "Robots_MetaData", "hebi_components.json"))


def get_known_cads() -> dict:
    cads = KNOWN_CADS.copy()
    try:
        if os.path.exists(_hebi_path):
            with open(_hebi_path, "r", encoding="utf-8") as f:
                hebi_data = json.load(f)
                for comp in hebi_data.get("components", []):
                    name = comp.get("name", "")
                    filename = comp.get("filename", "")
                    if name and filename:
                        cads[name.lower()] = filename
                        cads[name.lower().replace("-", " ")] = filename
    except Exception as e:
        print(f"[cad_registry] Error loading HEBI cads: {e}")
    return cads
