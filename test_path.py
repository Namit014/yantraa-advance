import os

_src_dir = os.path.abspath(os.path.join("src", "api"))
public_cad_dir = os.path.join(_src_dir, "..", "..", "frontend", "public", "cad")
f = "A-2475-05.STEP"
public_path = os.path.join(public_cad_dir, f)

print("SRC DIR:", _src_dir)
print("PUBLIC CAD DIR:", public_cad_dir)
print("PUBLIC PATH:", public_path)
print("EXISTS:", os.path.exists(public_path))

# Also check cwd
print("CWD:", os.getcwd())
