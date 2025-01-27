import tkinter as tk
from tkinter import ttk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

class SimplePlotView(tk.Toplevel):
    def __init__(self, parent):
        self.parent = parent
        super().__init__(self.parent.root)
        self.title("Simple Plot")

        # Matplotlib Figure and Tkinter Canvas
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas_widget = self.canvas.get_tk_widget()
        
        # Navigation toolbar for zooming and panning
        toolbar_frame = ttk.Frame(self)
        toolbar_frame.pack(side=tk.BOTTOM, fill=tk.X)

        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()
        
        canvas_widget = self.canvas_widget.get_tk_widget() if hasattr(self.canvas_widget, 'get_tk_widget') else self.canvas_widget
        canvas_widget.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=1)


if __name__ == "__main__":
    root = tk.Tk()
    class Parent:
        def __init__(self, root):
            self.root = root
    parent = Parent(root)
    view = SimplePlotView(parent)
    root.mainloop()
