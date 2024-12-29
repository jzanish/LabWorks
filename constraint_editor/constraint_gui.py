# constraint_editor/constraint_gui.py

import tkinter as tk
from tkinter import ttk, messagebox

class ConstraintsEditorTab:
    def __init__(self, parent_frame, constraints_manager, staff_manager, shift_manager):
        """
        :param parent_frame: the parent container (Notebook frame)
        :param constraints_manager: an instance of your ConstraintsManager
        :param staff_manager: to fetch staff list
        :param shift_manager: to fetch shift list
        """
        self.parent_frame = parent_frame
        self.constraints_manager = constraints_manager
        self.staff_manager = staff_manager
        self.shift_manager = shift_manager

        self.tree = None

        self._build_ui()
        self._populate_constraint_list()

    def _build_ui(self):
        # Frame for the treeview
        tree_frame = ttk.Frame(self.parent_frame)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)

        columns = ("type", "staff", "shift", "params")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        self.tree.pack(fill="both", expand=True)

        self.tree.heading("type", text="Constraint Type")
        self.tree.heading("staff", text="Staff")
        self.tree.heading("shift", text="Shift")
        self.tree.heading("params", text="Parameters")

        # Buttons frame
        btn_frame = ttk.Frame(self.parent_frame)
        btn_frame.pack(fill="x", padx=5, pady=5)

        add_btn = ttk.Button(btn_frame, text="Add", command=self._on_add)
        add_btn.pack(side="left", padx=5)

        edit_btn = ttk.Button(btn_frame, text="Edit", command=self._on_edit)
        edit_btn.pack(side="left", padx=5)

        del_btn = ttk.Button(btn_frame, text="Delete", command=self._on_delete)
        del_btn.pack(side="left", padx=5)

    def _populate_constraint_list(self):
        # Clear old rows
        for row in self.tree.get_children():
            self.tree.delete(row)

        constraints = self.constraints_manager.list_constraints()
        for idx, c in enumerate(constraints):
            ctype = c.get("type", "")
            staff = c.get("staff", "")
            shift = c.get("shift", "")
            # Remaining keys in 'params'
            param_text = str({k: v for k, v in c.items() if k not in ["type","staff","shift"]})
            self.tree.insert("", "end", values=(ctype, staff, shift, param_text))

    def _on_add(self):
        # Open a custom Toplevel (form) for adding a new constraint
        AddOrEditConstraintForm(
            parent=self.parent_frame,
            staff_manager=self.staff_manager,
            shift_manager=self.shift_manager,
            on_save=self._handle_new_constraint
        )

    def _handle_new_constraint(self, constraint_dict):
        """
        Callback from the form when user clicks OK with new constraint data.
        """
        self.constraints_manager.add_constraint(constraint_dict)
        self.constraints_manager.save_data()
        self._populate_constraint_list()
        messagebox.showinfo("Constraint Added", "New constraint has been added successfully.")

    def _on_edit(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("No Selection", "Please select a constraint to edit.")
            return
        item_id = sel[0]
        index_in_list = self.tree.index(item_id)
        existing_constraint = self.constraints_manager.list_constraints()[index_in_list]

        # open the form again, but prepopulate with existing data
        AddOrEditConstraintForm(
            parent=self.parent_frame,
            staff_manager=self.staff_manager,
            shift_manager=self.shift_manager,
            initial_data=existing_constraint,
            on_save=lambda updated: self._handle_edit_constraint(index_in_list, updated)
        )

    def _handle_edit_constraint(self, index, updated_constraint):
        self.constraints_manager.update_constraint(index, updated_constraint)
        self.constraints_manager.save_data()
        self._populate_constraint_list()
        messagebox.showinfo("Constraint Updated", "Constraint updated successfully.")

    def _on_delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("No Selection", "Please select a constraint to remove.")
            return
        item_id = sel[0]
        index_in_list = self.tree.index(item_id)
        self.constraints_manager.remove_constraint(index_in_list)
        self.constraints_manager.save_data()
        self._populate_constraint_list()
        messagebox.showinfo("Constraint Deleted", "Constraint was removed.")


class AddOrEditConstraintForm(tk.Toplevel):
    """
    A Toplevel form to let user pick: Constraint Type, Staff, Shift, and parameters.
    If initial_data is provided, we populate the fields for editing.
    on_save is called with the resulting constraint dict when the user hits OK.
    """
    def __init__(self, parent, staff_manager, shift_manager, on_save, initial_data=None):
        super().__init__(parent)
        self.title("Add/Edit Constraint")

        self.staff_manager = staff_manager
        self.shift_manager = shift_manager
        self.on_save = on_save
        self.initial_data = initial_data or {}

        # We could define a small set of known constraint types
        self.constraint_types = [
            "LimitWeeklyShift",
            "AvoidBackToBack",
            "KLPreference",
            "NoBackToBackEUSFNA",
            # ... etc ...
        ]

        self._create_widgets()
        self._populate_initial_values()
        self.grab_set()  # Keep focus on this window

    def _create_widgets(self):
        pad = 5

        # Constraint Type
        ttk.Label(self, text="Constraint Type:").grid(row=0, column=0, padx=pad, pady=pad, sticky="e")
        self.type_var = tk.StringVar()
        self.type_combo = ttk.Combobox(self, textvariable=self.type_var, values=self.constraint_types, state="readonly")
        self.type_combo.grid(row=0, column=1, padx=pad, pady=pad, sticky="w")

        # Staff
        ttk.Label(self, text="Staff:").grid(row=1, column=0, padx=pad, pady=pad, sticky="e")
        self.staff_var = tk.StringVar()
        # get staff initials from staff_manager
        staff_list = [s.initials for s in self.staff_manager.list_staff()]
        self.staff_combo = ttk.Combobox(self, textvariable=self.staff_var, values=staff_list, state="readonly")
        self.staff_combo.grid(row=1, column=1, padx=pad, pady=pad, sticky="w")

        # Shift
        ttk.Label(self, text="Shift:").grid(row=2, column=0, padx=pad, pady=pad, sticky="e")
        self.shift_var = tk.StringVar()
        # get shift names from shift_manager
        shift_objs = self.shift_manager.list_shifts()
        shift_list = [sh.name for sh in shift_objs]
        self.shift_combo = ttk.Combobox(self, textvariable=self.shift_var, values=shift_list, state="readonly")
        self.shift_combo.grid(row=2, column=1, padx=pad, pady=pad, sticky="w")

        # Param1 Label & Entry (for demonstration, e.g. “exact_count”)
        ttk.Label(self, text="Param 1:").grid(row=3, column=0, padx=pad, pady=pad, sticky="e")
        self.param1_var = tk.StringVar()
        self.param1_entry = ttk.Entry(self, textvariable=self.param1_var)
        self.param1_entry.grid(row=3, column=1, padx=pad, pady=pad, sticky="w")

        # Additional parameter(s) can be added similarly if needed

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)

        ok_btn = ttk.Button(btn_frame, text="OK", command=self._on_ok)
        ok_btn.pack(side="left", padx=10)

        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.destroy)
        cancel_btn.pack(side="left", padx=10)

    def _populate_initial_values(self):
        # If editing, fill combos with existing data
        ctype = self.initial_data.get("type", "")
        staff = self.initial_data.get("staff", "")
        shift = self.initial_data.get("shift", "")
        param1 = ""
        # param1 can be read from e.g. self.initial_data.get("exact_count") if type=LimitWeeklyShift
        # or we do a generic approach
        leftover = {k: v for k, v in self.initial_data.items() if k not in ("type","staff","shift")}
        if leftover:
            # We'll just pick the first leftover key as param1
            # Real code might handle multiple or do something more sophisticated
            first_key = list(leftover.keys())[0]
            param1 = leftover[first_key]

        self.type_var.set(ctype)
        self.staff_var.set(staff)
        self.shift_var.set(shift)
        self.param1_var.set(str(param1))

    def _on_ok(self):
        # Gather data from widgets
        ctype = self.type_var.get().strip()
        staff = self.staff_var.get().strip()
        shift = self.shift_var.get().strip()
        param1_value = self.param1_var.get().strip()

        if not ctype:
            messagebox.showerror("Missing Type", "Please select a constraint type.")
            return

        # Build a constraint dict
        constraint_dict = {
            "type": ctype,
            "staff": staff,
            "shift": shift
        }
        # We'll store param1_value as "param1", or if ctype=LimitWeeklyShift => "exact_count"...
        # For now, let's do something generic
        if ctype == "LimitWeeklyShift":
            # param1_value might be an integer for "exact_count"
            try:
                param_int = int(param1_value)
                constraint_dict["exact_count"] = param_int
            except:
                constraint_dict["exact_count"] = param1_value
        else:
            # just store it in param1 as a string
            constraint_dict["param1"] = param1_value

        self.on_save(constraint_dict)
        self.destroy()
