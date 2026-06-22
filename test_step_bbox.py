import sys
import os
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.BRepBndLib import brepbndlib_Add
from OCC.Core.Bnd import Bnd_Box

def test_bbox(filepath):
    if not os.path.exists(filepath):
        print(f"Error: File does not exist at {filepath}")
        return

    reader = STEPControl_Reader()
    status = reader.ReadFile(filepath)
    if status != 1:
        print(f"Error reading file {filepath}")
        return
    
    reader.TransferRoots()
    shape = reader.OneShape()
    
    bbox = Bnd_Box()
    brepbndlib_Add(shape, bbox)
    
    if bbox.IsVoid():
        print("Bounding box is void (empty shape)")
        return

    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    print(f"Bounding Box: X[{xmin}, {xmax}] Y[{ymin}, {ymax}] Z[{zmin}, {zmax}]")

if __name__ == "__main__":
    filepath = sys.argv[1] if len(sys.argv) > 1 else "knowledgebase/rm_models/RX75R-6FB-V.STEP"
    test_bbox(filepath)
