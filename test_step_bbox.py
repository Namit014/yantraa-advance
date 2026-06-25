import sys
from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.BRepBndLib import brepbndlib_Add
from OCC.Core.Bnd import Bnd_Box

def test_bbox(filepath):
    reader = STEPControl_Reader()
    status = reader.ReadFile(filepath)
    if status != 1:
        print("Error reading file")
        return
    
    reader.TransferRoots()
    shape = reader.OneShape()
    
    bbox = Bnd_Box()
    brepbndlib_Add(shape, bbox)
    
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    print(f"Bounding Box: X[{xmin}, {xmax}] Y[{ymin}, {ymax}] Z[{zmin}, {zmax}]")

if __name__ == "__main__":
    test_bbox("knowledgebase/Full_System_A-2403-02.step")
