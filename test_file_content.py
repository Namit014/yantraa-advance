with open("knowledgebase/Full_System_A-2403-02.step", "rb") as f:
    header = f.read(2000)
    print(header.decode("ascii", errors="replace"))
