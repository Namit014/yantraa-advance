import sys
import traceback
try:
    import src.api.main
except Exception as e:
    traceback.print_exc()
print("DONE")
