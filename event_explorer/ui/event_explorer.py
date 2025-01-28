"""Main UI class for Event Explorer"""
import sys
import tkinter as tk
import numpy as np
import os
from tkinter import ttk, filedialog, simpledialog, messagebox
from tkinter.messagebox import askokcancel, showinfo, WARNING
from pathlib import Path
from typing import Optional, List, Dict, Any

from event_explorer.data.data_manager import DataManager
from event_explorer.utils.config import EventExplorerConfig
from event_explorer.ui.views import (
    SimplePlotView, PointsSelectorView, IndexPickerView,
    SlopeAnalyzerView, DynamicStrainArrivalPickerView, CZMFitterView
)

class EventExplorer:
    def __init__(self, root: tk.Tk):
        self.config = EventExplorerConfig()
        self.root = root
        self.root.title(self.config.WINDOW_TITLE)
        
        self.data_manager = DataManager()
        self.child_windows: List[tk.Toplevel] = []
        self.data_tree: Optional[ttk.Treeview] = None
        self.active_context_menu: Optional[tk.Menu] = None
        
        self.setup_window()
        self.create_widgets()
        self.setup_bindings()


        # debug
        file_path = Path("/Users/hueyke/sources/PSU-Dynamic-Strain/Data/p5993e.npz")
        self.data_manager.load_file(file_path)
        self.save_button.configure(state="normal")
        self.refresh_tree()
        print(f"File loaded: {file_path}")

    def setup_window(self) -> None:
        screen_height = self.root.winfo_screenheight()
        window_height = screen_height - (self.config.WINDOW_GAP * 3)
        
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(2, weight=1)
        self.root.geometry(
            f"{self.config.WINDOW_WIDTH}x{window_height}+"
            f"{self.config.WINDOW_GAP}+{self.config.WINDOW_GAP}"
        )
        self.root.lift()
        self.root.focus_force()

    def create_widgets(self) -> None:
        self.create_context_menus()
        self.create_buttons()
        self.init_data_tree()

    def create_context_menus(self) -> None:
        self.run_menu = tk.Menu(self.root, tearoff=0)
        self.run_menu.add_command(label="Pick Events", command=self.pick_events)

        self.event_menu = tk.Menu(self.root, tearoff=0)
        self.event_menu.add_command(label="Pick Arrivals", command=self.pick_strain_array_arrivals)
        self.event_menu.add_command(label="Fit Cohesive Zone Model", command=self.fit_cohesive_zone_model)

        self.array_menu = tk.Menu(self.root, tearoff=0)
        self.array_menu.add_command(label="Pick Indices", command=self.pick_indices)
        self.array_menu.add_command(label="Extract Slopes", command=self.extract_slope)
        self.array_menu.add_command(label="Extract Run", command=self.pick_run)

        self.event_indices_menu = tk.Menu(self.root, tearoff=0)
        self.event_indices_menu.add_command(label="Extract Events", command=self.extract_events)

        self.string_menu = tk.Menu(self.root, tearoff=0)
        self.string_menu.add_command(label="Edit String", command=self.edit_string)

    def create_buttons(self) -> None:
        buttons = [
            ("Load", self.load_file, "normal", 0),
            ("Refresh", self.refresh_tree, "normal", 1),
            ("Save As", self.save_file, "disabled", 3)
        ]
        
        for text, command, state, col in buttons:
            btn = tk.Button(self.root, text=text, command=command, state=state)
            btn.grid(row=1, column=col, padx=2, pady=2, sticky="w" if col < 2 else "e")
            if text == "Save As":
                self.save_button = btn

    def init_data_tree(self) -> None:
        if self.data_tree:
            self.data_tree.destroy()
            
        self.data_tree = ttk.Treeview(self.root)
        self.data_tree.grid(row=0, column=0, columnspan=4, padx=2, pady=2, sticky="nsew")
        self.data_tree.heading("#0", text="[Data File]", anchor="w")
        
        self.data_tree.bind("<Double-1>", self.on_double_click)
        self.data_tree.bind("<Button-1>", self.on_left_click)
        self.data_tree.bind("<Button-2>", self.on_right_click)
        self.data_tree.bind("<Button-3>", self.on_right_click)

    def load_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select data file",
            filetypes=self.config.FILE_TYPES
        )
        if not file_path:
            return

        try:
            self.data_manager.load_file(Path(file_path))
            self.save_button.configure(state="normal")
            self.refresh_tree()
            print(f"File loaded: {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {e}")

    def save_file(self) -> None:
        file_path = filedialog.asksaveasfilename(
            title="Save data file",
            filetypes=(
                ("NPZ file", ".npz"),
                ("HDF5 file", ".h5 .hdf5"),
                ("All files", "*")
            )
        )
        if not file_path:
            return

        try:
            self.data_manager.save_file(Path(file_path))
            print(f"File saved: {file_path}")
            messagebox.showinfo("Success", "File saved successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {e}")

    def refresh_tree(self) -> None:
        if not self.data_manager.data:
            return
            
        selected_item = self.data_tree.selection()[0] if self.data_tree.selection() else None
        self.init_data_tree()
        self.build_tree(self.data_manager.data, "")
        
        if selected_item:
            try:
                self.data_tree.focus(selected_item)
                self.data_tree.selection_set(selected_item)
                self.data_tree.see(selected_item)
            except:
                pass

    def build_tree(self, data: Dict[str, Any], parent_iid: str) -> None:
        """Recursively build tree view from data"""
        if isinstance(data, dict):
            for key, value in data.items():
                label = self.format_tree_label(key, value)
                iid = self.data_tree.insert(parent_iid, "end", text=label)
                
                if isinstance(value, (dict, list)):
                    self.build_tree(value, iid)
        elif isinstance(data, list):
            for i, value in enumerate(data):
                label = self.format_tree_label(f"[{i}]", value)
                iid = self.data_tree.insert(parent_iid, "end", text=label)
                
                if isinstance(value, (dict, list)):
                    self.build_tree(value, iid)

    def format_tree_label(self, key: str, value: Any) -> str:
        if isinstance(value, str):
            return f"{key}: {value}"
        elif isinstance(value, (int, float, np.floating, np.integer)):
            return f"{key}: {value}"
        elif isinstance(value, (list, np.ndarray)):
            try:
                if len(value) == 1:
                    return f"{key}: {value[0]}"
                else:
                    return f"{key}: array[{len(value)}]"
            except:
                if value.size == 1:
                    return f"{key}: {value.flatten()[0]}"
                else:
                    return f"{key}: array[{value.size}]"
        return f"{key}: {type(value).__name__}"
    
    def get_full_path(self, item=None):
        def clean_up_text(s):
            return s.split(':')[0].strip()
        if item is None:
            item = self.data_tree.selection()[0]
        parent_iid = self.data_tree.parent(item)
        node = []
        # go backward until reaching root
        while parent_iid != '':
            node.insert(0, clean_up_text(self.data_tree.item(parent_iid)['text']))
            parent_iid = self.data_tree.parent(parent_iid)
        i = clean_up_text(self.data_tree.item(item, "text"))
        return os.path.join(*node, i), i
    

    def pick_events(self) -> None:
        path, item = self.get_full_path()
        y = self.data_manager.get_data(path)
        x = np.arange(len(y))
        save_path = path[:path.rfind('/')+1] + "event_indices"
        parent_id = self.data_tree.parent(self.data_tree.selection()[0])
        if self.has_child_named(parent_id, "event_indices"):
            picked_idx = self.data_manager.get_data(self.get_full_path(parent_id)[0] + "/event_indices")
        else:
            picked_idx = []
        def save_and_refresh(data):
            self.data_manager.set_data(save_path, data, add_key=True)
            self.refresh_tree()
        view = PointsSelectorView(self, x, y, picked_idx, add_remove_enabled=True, 
                                 callback=save_and_refresh,
                                 xlabel='index', ylabel=item, title=path)
        self.child_windows.append(view)


    def pick_strain_array_arrivals(self):
        path, item = self.get_full_path()
        run_idx = int(path[path.find('runs/[')+6:path.find(']/events')])
        temp = path[path.find('events/[')+8::]
        event_idx = int(temp[:temp.find(']')])
        view = DynamicStrainArrivalPickerView(self, run_idx, event_idx)
        self.child_windows.append(view)
        
    def fit_cohesive_zone_model(self):
        path, item = self.get_full_path()
        run_idx = int(path[path.find('runs/[')+6:path.find(']/events')])
        temp = path[path.find('events/[')+8::]
        event_idx = int(temp[:temp.find(']')])
        view = CZMFitterView(self, run_idx, event_idx)
        self.child_windows.append(view)


    def pick_indices(self):
        item = self.data_tree.selection()[0]
        item_name = self.data_tree.item(item)['text'].split(':')[0]
        view = IndexPickerView(self, item_y=item_name)
        self.child_windows.append(view)

    def extract_slope(self):
        item = self.data_tree.selection()[0]
        item_name = self.data_tree.item(item)['text'].split(':')[0]
        view = SlopeAnalyzerView(self, item_y=item_name)
        self.child_windows.append(view)

    def pick_run(self):
        item_id = self.data_tree.selection()[0]
        item_path, item_name = self.get_full_path(item_id)

        y = self.get_data(self.data, item_path)
        x = np.arange(len(y))
        picked_idx = [int(len(y)/3), int(len(y)/3*2)]
        view = PointsSelectorView(self, x, y, picked_idx, add_remove_enabled=False, 
                                 callback=lambda idx: self.extract_run(idx),
                                 xlabel='index', ylabel=item_name, title=item_path)
        self.child_windows.append(view)

    def extract_events(self):
        """Handle UI for event extraction and delegate to EventProcessor"""
        # Get selected item and paths
        item_id = self.data_tree.selection()[0]
        parent = self.data_tree.parent(item_id)
        event_indices_path = self.get_full_path()[0]
        parent_path = self.get_full_path(parent)[0]
        events_path = f"{parent_path}/events"

        # Check for existing events
        if self.has_child_named(parent, "events"):
            ans = askokcancel(
                title="Confirmation", 
                message=f'This procedure will replace all data in "{events_path}".', 
                icon=WARNING
            )
            if not ans:
                return

        # Get window size from user
        window = simpledialog.askfloat(
            'Set event time window length', 
            'Please set the duration before and after the event to be extracted.',
            initialvalue=5
        )
        if window is None:
            print('Event extraction aborted.')
            return
        print(f'Window set to (-{window}, {window})')

        try:
            # Get run data and indices
            run_data = self.data_manager.get_data(parent_path)
            event_indices = self.data_manager.get_data(event_indices_path)

            # Extract events using EventProcessor
            events = self.data_manager.event_processor.extract_events(
                run_data,
                event_indices,
                window
            )

            # Save results
            self.data_manager.set_data(events_path, events, add_key=True)
            self.refresh_tree()
            showinfo(title="Success", message="Events extracted.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to extract events: {str(e)}")

    def edit_string(self):
        """Edit a string value in the data structure"""
        path, item = self.get_full_path()
        data = self.data_manager.get_data(path)

        new_string = simpledialog.askstring('Edit String', f'{path}', initialvalue=data)
        if new_string is None:
            print('Edit String aborted.')
            return
        
        self.data_manager.set_data(path, new_string)
        self.refresh_tree()
            
    def on_double_click(self, event):
        path, item = self.get_full_path()
        print(f"Double-clicked on item: {path}")
        data = self.data_manager.get_data(path)
        if type(data) is np.ndarray:
            print(f"plotting {item}")
            view = SimplePlotView(self)
            view.ax.plot(data)
            view.ax.set_xlabel('index')
            view.ax.set_ylabel(item)
            view.ax.set_title(path.replace('/[', '['))
        elif type(data) is dict:
            print('dict')
        elif type(data) is list:
            print('list')
        else:
            print(data)
        
    def on_left_click(self, event):
        if self.active_context_menu:
            self.active_context_menu.unpost()

    def on_right_click(self, event):
        # Clear previous menu
        if self.active_context_menu:
            self.active_context_menu.unpost()
        self.active_context_menu = None

        try:
            item = self.data_tree.selection()[0]
        except:
            item = None
        if not item:
            return

        # data-structure-specific context menus
        item_label = self.data_tree.item(item)['text'].split(':')
        parent = self.data_tree.parent(item)
        parent_name = self.data_tree.item(parent)['text'].split(':')[0] if parent else ""
        grandparent = self.data_tree.parent(parent)
        grandparent_name = self.data_tree.item(grandparent)['text'].split(':')[0] if grandparent else ""

        if grandparent_name == "runs":
            if item_label[0] == "event_indices":
                self.active_context_menu = self.event_indices_menu
            elif len(item_label) > 1 and "array" in item_label[1]:
                self.active_context_menu = self.run_menu
        elif grandparent_name == "events":
            if len(item_label) > 1 and "array" in item_label[1]:
                self.active_context_menu = self.event_array_menu
            else:
                self.active_context_menu = self.event_menu
        elif parent_name == "events":
            self.active_context_menu = self.event_menu

        # general purpose context menus
        if not self.active_context_menu:
            path, _ = self.get_full_path()
            data = self.data_manager.get_data(path)
            if isinstance(data, str):
                self.active_context_menu = self.string_menu
            elif len(item_label) > 1 and "array" in item_label[1] and parent_name == "":
                self.active_context_menu = self.array_menu

        # post context menu
        if self.active_context_menu:
            self.active_context_menu.post(event.x_root, event.y_root)
    
    def has_child_name_contains(self, item_id, keyword):
        if not item_id:
            return False
        children = self.data_tree.get_children(item_id)
        return any(keyword in self.data_tree.item(child_id, "text") for child_id in children)
    
    def has_child_named(self, item_id, name):
        if not item_id:
            return False
        children = self.data_tree.get_children(item_id)
        return any(name == self.data_tree.item(child_id, "text").split(":")[0] for child_id in children)

    def on_delete(self, event):
        item_id = self.data_tree.selection()[0]
        item_path = self.get_full_path(item_id)[0]
        ans = askokcancel(title="Confirmation", message=f"This procedure will delete \"{item_path}\".", icon=WARNING)
        if not ans:
            return
        parent_id = self.data_tree.parent(item_id)
        parent_path = self.get_full_path(parent_id)[0]
        parent = self.get_data(self.data, parent_path)
        item_name = self.data_tree.item(item_id, "text").split(":")[0]
        if type(parent) is dict:
            parent.pop(item_name)
        elif type(parent) is list:
            parent.pop(int(item_name.split(']')[0].split('[')[1]))
        self.refresh_tree()

    def on_closing(self) -> None:
        try:
            for window in self.child_windows[:]:
                if window.winfo_exists():
                    window.destroy()
                self.child_windows.remove(window)
            self.root.destroy()
            sys.exit(0)
        except Exception as e:
            print(f"Error during cleanup: {e}")
            sys.exit(1)

    def setup_bindings(self) -> None:
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.bind("<Delete>", self.on_delete)