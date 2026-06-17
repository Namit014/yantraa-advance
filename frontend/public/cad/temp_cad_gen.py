from build123d import *

# Pipeline robot parameters
pipeline_diameter = 50.0  # Diameter of the pipeline
robot_diameter = pipeline_diameter * 0.8  # Robot outer diameter
robot_length = 100.0  # Robot body length
wheel_diameter = robot_diameter * 0.4
wheel_width = robot_diameter * 0.15
wheel_offset_x = robot_length / 4
wheel_offset_y = robot_diameter / 2 - wheel_width / 2
sensor_diameter = robot_diameter * 0.15
sensor_height = robot_diameter * 0.2
sensor_offset_y = robot_diameter / 2 + sensor_diameter / 2
sensor_offset_x = robot_length * 0.3
rust_tool_diameter = robot_diameter * 0.2
rust_tool_length = robot_diameter * 0.3
rust_tool_offset_x = -robot_length / 4
rust_tool_offset_y = robot_diameter / 2 + rust_tool_length / 2
coating_nozzle_diameter = robot_diameter * 0.1
coating_nozzle_length = robot_diameter * 0.25
coating_nozzle_offset_x = -robot_length / 2 + coating_nozzle_length / 2
coating_nozzle_offset_y = robot_diameter / 2 + coating_nozzle_diameter / 2


# Create the main robot body
with BuildPart() as robot_body:
    with BuildCylinder(radius=robot_diameter / 2, height=robot_length):
        pass # Main body cylinder

    # Add wheels
    with BuildTransform(location=Location(Vector(wheel_offset_x, -wheel_offset_y, 0))):
        with BuildCylinder(radius=wheel_diameter / 2, height=wheel_width):
            pass
    with BuildTransform(location=Location(Vector(wheel_offset_x, wheel_offset_y, 0))):
        with BuildCylinder(radius=wheel_diameter / 2, height=wheel_width):
            pass
    with BuildTransform(location=Location(Vector(-wheel_offset_x, -wheel_offset_y, 0))):
        with BuildCylinder(radius=wheel_diameter / 2, height=wheel_width):
            pass
    with BuildTransform(location=Location(Vector(-wheel_offset_x, wheel_offset_y, 0))):
        with BuildCylinder(radius=wheel_diameter / 2, height=wheel_width):
            pass


# Add ultrasonic sensors
with BuildPart() as ultrasonic_sensors:
    with BuildTransform(location=Location(Vector(sensor_offset_x, sensor_offset_y, 0))):
        with BuildCylinder(radius=sensor_diameter / 2, height=sensor_height):
            pass
    with BuildTransform(location=Location(Vector(sensor_offset_x, -sensor_offset_y, 0))):
        with BuildCylinder(radius=sensor_diameter / 2, height=sensor_height):
            pass


# Add rust removal tools
with BuildPart() as rust_tools:
    with BuildTransform(location=Location(Vector(rust_tool_offset_x, 0, 0))):
        with BuildCylinder(radius=rust_tool_diameter / 2, height=rust_tool_length):
            pass

# Add protective coating tool
with BuildPart() as coating_tool:
    with BuildTransform(location=Location(Vector(coating_nozzle_offset_x, 0, 0))):
        with BuildCylinder(radius=coating_nozzle_diameter / 2, height=coating_nozzle_length):
            pass


# Combine all parts
final_robot = robot_body.part + ultrasonic_sensors.part + rust_tools.part + coating_tool.part

# Create the pipeline for context (optional)
with BuildPart() as pipeline:
    with BuildCylinder(radius=pipeline_diameter / 2, height=robot_length * 2):
        pass
    # Cut out the center to make it a hollow pipe
    with BuildCylinder(radius=pipeline_diameter / 2 - 2, height=robot_length * 2) as inner_cut:
        pass
    pipeline.part = pipeline.part - inner_cut.part


# Export the final robot model
final_robot.export_step("C:/Users/parve/Desktop/Repo/yantraa-advance/frontend/public/cad/gen_27924ff7.step")