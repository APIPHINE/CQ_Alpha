import tkinter as tk
from tkinter import filedialog

# 1. Print the current Tk/Tcl version:
print("Tk Version:", tk.TkVersion)
print("Tcl Version:", tk.TclVersion)

# 2. Minimal test for opening a file dialog:
root = tk.Tk()
root.withdraw()  # Hide the root window (optional)

selected_file = filedialog.askopenfilename(
    filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
)
print("Selected File:", selected_file)

root.destroy()