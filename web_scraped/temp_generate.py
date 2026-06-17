import trimesh
import numpy as np

# Define the dimensions of the parts
bar_length = 200
bar_width = 20
bar_thickness = 10
articulation_radius = 30
workpiece_radius = 20
tool_radius = 10

# Create the parts of the Scara Robot
bar = trimesh.creation.box((1, bar_length, bar_thickness), 
                           (0, 0, 0), (1, 0, 0))
articulation = trimesh.creation.cylinder(radius=articulation_radius, 
                                          height=2 * articulation_radius, 
                                          # Axis of the cylinder should match the orientation of the Z-axis
                                          AxisOfCylinderMatchOrientationOfZAxis=True)
workpiece = trimesh.creation.cylinder(radius=workpiece_radius, 
                                       height=bar_length, 
                                       AxisOfCylinderMatchOrientationOfZAxis=True)
tool = trimesh.creation.cylinder(radius=tool_radius, 
                                  height=1, 
                                  AxisOfCylinderMatchOrientationOfZAxis=True)

# Combine the parts into a single scene
scene = trimesh.Scene([bar, articulation, workpiece, tool])

# Save the scene to a file as STL
scene.export(r'D:\RAG model\yantra\web_scraped\generated_model.stl')