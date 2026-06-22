import sys
import os

def test_bbox(filepath):
    if not os.path.exists(filepath):
        print(f"Error: File does not exist at {filepath}")
        return

    try:
        import cadquery as cq
    except ImportError:
        print("Error: The 'cadquery' module is required. A background installation is currently running.")
        print("You can manually install it via: pip install cadquery")
        return

    print(f"Reading {filepath}...")
    try:
        # Import the step file
        shape = cq.importers.importStep(filepath)
        if shape is None or shape.val() is None:
            print("Error: empty shape or invalid file format.")
            return
            
        # Compute bounding box
        bbox = shape.val().BoundingBox()
        print(f"Bounding Box: X[{bbox.xmin}, {bbox.xmax}] Y[{bbox.ymin}, {bbox.ymax}] Z[{bbox.zmin}, {bbox.zmax}]")
    except Exception as e:
        print(f"Failed to process STEP file: {e}")

if __name__ == "__main__":
    filepath = sys.argv[1] if len(sys.argv) > 1 else "knowledgebase/rm_models/RX75R-6FB-V.STEP"
    test_bbox(filepath)
