import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.colors as mcolors  # <-- NEW: Needed to convert plot colors to UI colors
import re
import csv
import os

# --- 1. ROBUST DATA LOADER ---
def load_data(filename):
    encodings = ['utf-8-sig', 'utf-16', 'latin1', 'cp1252']
    raw_text = None
    
    for enc in encodings:
        try:
            with open(filename, 'r', encoding=enc, errors='ignore') as f:
                temp_text = f.read()
                if 'freq' in temp_text.lower() or 'hz' in temp_text.lower():
                    raw_text = temp_text
                    break
        except Exception:
            pass
            
    if not raw_text:
        messagebox.showerror("Error", f"Could not read the file format of:\n{filename}")
        return []

    raw_text = raw_text.replace(';', ',').replace('\t', ',')
    lines = raw_text.splitlines()

    samples = []
    counts = {}  
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        if 'freq' in line.lower() and 'hz' in line.lower():
            headers = [cell.strip().strip('"').strip("'").lower() for cell in line.split(',')]
            z_real_idx, z_imag_idx = 7, 8
            
            try:
                z_real_idx = next(idx for idx, h in enumerate(headers) if "z'" in h and "ohm" in h and not "-" in h)
                z_imag_idx = next(idx for idx, h in enumerate(headers) if "-z''" in h and "ohm" in h)
            except StopIteration:
                pass
                
            if i > 0:
                raw_name = lines[i-1].strip().strip('",\'').strip(',')
            else:
                raw_name = "Sample"
                
            match = re.search(r'10\^\(-?\d+\)M|1M', raw_name)
            clean_name = match.group(0) if match else raw_name
            
            counts[clean_name] = counts.get(clean_name, 0) + 1
            unique_name = f"{clean_name} (Run {counts[clean_name]})"
            
            z_real, z_imag = [], []
            i += 1
            
            while i < len(lines):
                data_line = lines[i].strip()
                if not data_line: break
                    
                cells = [cell.strip().strip('"').strip("'") for cell in data_line.split(',')]
                
                if len(cells) <= max(z_real_idx, z_imag_idx): break
                    
                try:
                    float(cells[0])
                    z_real.append(float(cells[z_real_idx]))
                    z_imag.append(float(cells[z_imag_idx]))
                except (ValueError, IndexError):
                    break
                i += 1
                
            if z_real and z_imag:
                samples.append({
                    "base_name": clean_name, 
                    "name": unique_name,     
                    "z_real": [x / 1000.0 for x in z_real],  
                    "z_imag": [x / 1000.0 for x in z_imag]   
                })
            continue 
        i += 1
    return samples

# --- 2. THE MAIN VIEWER APPLICATION ---
def run_viewer(filepath):
    samples = load_data(filepath)
    if not samples:
        return 

    filename_only = os.path.basename(filepath)

    root = tk.Tk()
    root.title(f"EIS Viewer - {filename_only}")
    root.geometry("1200x800")

    # LEFT SIDE: THE PLOT
    plot_frame = tk.Frame(root)
    plot_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    fig, ax = plt.subplots(figsize=(8, 6))
    fig.subplots_adjust(left=0.1, right=0.95, top=0.9, bottom=0.15) 
    
    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    toolbar = NavigationToolbar2Tk(canvas, plot_frame)
    toolbar.update()
    
    ax.set_xlabel("Z' (kΩ)", fontsize=12, fontweight='bold')
    ax.set_ylabel("-Z'' (kΩ)", fontsize=12, fontweight='bold')
    ax.set_title(f"Nyquist Plot: {filename_only}", fontsize=14, fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.axhline(0, color='black', linewidth=1.2, alpha=0.5)
    ax.set_aspect('equal', 'box')

    # RIGHT SIDE: THE CONTROL PANEL
    control_frame = tk.Frame(root, width=320, bd=2, relief=tk.SUNKEN)
    control_frame.pack(side=tk.RIGHT, fill=tk.Y)
    
    def load_new_file():
        root.destroy()  
        main()          

    tk.Button(control_frame, text="📁 Upload Another CSV", command=load_new_file, bg="#2196F3", fg="white", font=("Arial", 10, "bold")).pack(fill=tk.X, padx=5, pady=(10, 5))

    # AXIS RANGE CONTROLS 
    axis_frame = tk.LabelFrame(control_frame, text="Axis Limits (kΩ)", font=("Arial", 10, "bold"))
    axis_frame.pack(fill=tk.X, padx=5, pady=5)
    
    grid_frame = tk.Frame(axis_frame)
    grid_frame.pack(pady=5)
    
    tk.Label(grid_frame, text="X:").grid(row=0, column=0, padx=2)
    x_min_var = tk.StringVar()
    tk.Entry(grid_frame, textvariable=x_min_var, width=6).grid(row=0, column=1)
    tk.Label(grid_frame, text="to").grid(row=0, column=2)
    x_max_var = tk.StringVar()
    tk.Entry(grid_frame, textvariable=x_max_var, width=6).grid(row=0, column=3)
    
    tk.Label(grid_frame, text="Y:").grid(row=1, column=0, padx=2, pady=2)
    y_min_var = tk.StringVar()
    tk.Entry(grid_frame, textvariable=y_min_var, width=6).grid(row=1, column=1, pady=2)
    tk.Label(grid_frame, text="to").grid(row=1, column=2, pady=2)
    y_max_var = tk.StringVar()
    tk.Entry(grid_frame, textvariable=y_max_var, width=6).grid(row=1, column=3, pady=2)

    def apply_limits():
        try:
            if x_min_var.get() and x_max_var.get():
                ax.set_xlim(float(x_min_var.get()), float(x_max_var.get()))
            if y_min_var.get() and y_max_var.get():
                ax.set_ylim(float(y_min_var.get()), float(y_max_var.get()))
            
            autoscale_var.set(False) 
            canvas.draw()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numbers for the axis limits.")

    def force_autoscale():
        x_min_var.set("")
        x_max_var.set("")
        y_min_var.set("")
        y_max_var.set("")
        ax.relim()
        ax.autoscale_view()
        autoscale_var.set(True) 
        canvas.draw()

    btn_axis = tk.Frame(axis_frame)
    btn_axis.pack(fill=tk.X, padx=5, pady=2)
    
    tk.Button(btn_axis, text="Apply Limits", command=apply_limits, bg="#FF9800", fg="white", font=("Arial", 9, "bold")).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,2))
    tk.Button(btn_axis, text="Auto-Scale", command=force_autoscale, bg="#9E9E9E", fg="white", font=("Arial", 9, "bold")).pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(2,0))

    autoscale_var = tk.BooleanVar(value=True)
    tk.Checkbutton(axis_frame, text="Auto-scale when clicking traces", variable=autoscale_var).pack(anchor="w", padx=2, pady=2)

    tk.Label(control_frame, text="Trace Controls", font=("Arial", 12, "bold")).pack(pady=5)
    
    btn_frame = tk.Frame(control_frame)
    btn_frame.pack(fill=tk.X, padx=5, pady=0)
    
    lines_plot = [] 
    vars_cb = []  

    def update_plot():
        for txt in list(ax.texts):
            txt.remove()
            
        seen_base_names = set()
        
        for idx, (line, var) in enumerate(zip(lines_plot, vars_cb)):
            is_vis = var.get()
            line.set_visible(is_vis)
            
            if is_vis:
                base_name = samples[idx]['base_name']
                if base_name not in seen_base_names:
                    seen_base_names.add(base_name)
                    x_data = line.get_xdata()
                    if len(x_data) > 0:
                        end_x = x_data[-1]
                        ax.annotate(base_name, 
                                    xy=(end_x, 0),             
                                    xytext=(0, -15),           
                                    textcoords="offset points",
                                    color=line.get_color(),
                                    fontsize=11, 
                                    fontweight='bold',
                                    ha='center',               
                                    va='top',                  
                                    annotation_clip=False)     
        
        if autoscale_var.get():
            ax.relim()
            ax.autoscale_view()
            
        canvas.draw()

    def set_all(state):
        for var in vars_cb:
            var.set(state)
        update_plot()

    tk.Button(btn_frame, text="Select All", command=lambda: set_all(True)).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,2))
    tk.Button(btn_frame, text="Clear All", command=lambda: set_all(False)).pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(2,0))

    # EXPORT TO CSV
    def export_csv():
        selected_samples = [s for s, var in zip(samples, vars_cb) if var.get()]
        if not selected_samples:
            messagebox.showwarning("No Selection", "Please check at least one box to export.")
            return
            
        save_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="Export Selected Traces to CSV",
            initialfile="Cleaned_EIS_Data.csv"
        )
        if not save_path:
            return 
            
        headers = []
        for s in selected_samples:
            headers.extend([f"{s['name']} Z' (kOhm)", f"{s['name']} -Z'' (kOhm)"])
            
        max_len = max(len(s['z_real']) for s in selected_samples)
        rows = []
        
        for idx_row in range(max_len):
            row = []
            for s in selected_samples:
                if idx_row < len(s['z_real']):
                    row.extend([s['z_real'][idx_row], s['z_imag'][idx_row]])
                else:
                    row.extend(["", ""])
            rows.append(row)
            
        try:
            with open(save_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(rows)
            messagebox.showinfo("Success!", f"Successfully exported {len(selected_samples)} traces.")
        except Exception as e:
            messagebox.showerror("Export Error", f"An error occurred while saving:\n{str(e)}")

    export_btn = tk.Button(control_frame, text="Export Selected to CSV", command=export_csv, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
    export_btn.pack(fill=tk.X, padx=5, pady=(10, 10))

    # SCROLLABLE CHECKBOX LIST WITH GROUPS
    scroll_canvas = tk.Canvas(control_frame)
    scrollbar = ttk.Scrollbar(control_frame, orient="vertical", command=scroll_canvas.yview)
    checkbox_frame = ttk.Frame(scroll_canvas)

    checkbox_frame.bind("<Configure>", lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all")))
    scroll_canvas.create_window((0, 0), window=checkbox_frame, anchor="nw")
    scroll_canvas.configure(yscrollcommand=scrollbar.set)

    scroll_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _on_mousewheel(event):
        scroll_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    scroll_canvas.bind_all("<MouseWheel>", _on_mousewheel)

    colors = plt.cm.tab20.colors + plt.cm.tab20b.colors + plt.cm.tab20c.colors 
    
    groups = {}
    for idx, s in enumerate(samples):
        bname = s.get("base_name", "Unknown")
        if bname not in groups:
            groups[bname] = []
        groups[bname].append(idx)
        
    for idx, s in enumerate(samples):
        c = colors[idx % len(colors)]
        line, = ax.plot(s['z_real'], s['z_imag'], marker='o', markersize=3, linewidth=1, color=c)
        lines_plot.append(line)
        
        var = tk.BooleanVar(value=True)
        vars_cb.append(var)
        
    for base_name, indices in groups.items():
        grp_frame = tk.Frame(checkbox_frame)
        grp_frame.pack(fill=tk.X, pady=4, anchor="w")
        
        def make_toggle(inds):
            def toggle():
                all_true = all(vars_cb[i].get() for i in inds)
                new_state = not all_true
                for i in inds:
                    vars_cb[i].set(new_state)
                update_plot()
            return toggle
            
        tk.Button(grp_frame, text=f"Toggle All {base_name}", command=make_toggle(indices), 
                  font=("Arial", 9, "bold"), bg="#d9d9d9", relief=tk.RAISED).pack(anchor="w", fill=tk.X, padx=2)
        
        # --- NEW FEATURE: COLOR BLOCKS NEXT TO CHECKBOXES ---
        for idx in indices:
            s = samples[idx]
            var = vars_cb[idx]
            c = colors[idx % len(colors)]
            
            # Convert the Matplotlib RGB color to a UI Hex color (e.g., "#1f77b4")
            hex_color = mcolors.to_hex(c)
            
            # Create a mini-frame for this row
            row_frame = tk.Frame(grp_frame)
            row_frame.pack(anchor="w", padx=15, fill=tk.X)
            
            # Create a small color block with a black border
            color_lbl = tk.Label(row_frame, bg=hex_color, width=2, height=1, relief=tk.SOLID, bd=1)
            color_lbl.pack(side=tk.LEFT, pady=2)
            
            # Add the checkbox right next to it
            cb = tk.Checkbutton(row_frame, text=s['name'], variable=var, command=update_plot)
            cb.pack(side=tk.LEFT, padx=(5, 0))

    update_plot()
    root.mainloop()

# --- 3. THE UPLOAD LAUNCHER MENU ---
def main():
    launcher = tk.Tk()
    launcher.title("Upload EIS Data")
    launcher.geometry("500x180")
    launcher.eval('tk::PlaceWindow . center') 
    
    tk.Label(launcher, text="Electrochemical Impedance Data Viewer", font=("Arial", 14, "bold")).pack(pady=(15, 5))
    tk.Label(launcher, text="Select a PalmSens CSV file to begin:", font=("Arial", 10)).pack(pady=(0, 10))
    
    file_path_var = tk.StringVar()
    
    browse_frame = tk.Frame(launcher)
    browse_frame.pack(fill=tk.X, padx=20, pady=5)
    
    path_entry = tk.Entry(browse_frame, textvariable=file_path_var, font=("Arial", 10), state='readonly')
    path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
    
    def browse_file():
        filename = filedialog.askopenfilename(
            title="Select EIS CSV File",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if filename:
            file_path_var.set(filename)

    tk.Button(browse_frame, text="Browse...", command=browse_file, font=("Arial", 10)).pack(side=tk.RIGHT)
    
    def submit_file():
        selected_file = file_path_var.get()
        if not selected_file:
            messagebox.showwarning("Missing File", "Please Browse and select a CSV file first!")
            return
            
        launcher.destroy()         
        run_viewer(selected_file)  

    tk.Button(launcher, text="Submit & Open Viewer", command=submit_file, bg="#4CAF50", fg="white", font=("Arial", 11, "bold")).pack(pady=15)
    
    launcher.mainloop()

if __name__ == "__main__":
    main()