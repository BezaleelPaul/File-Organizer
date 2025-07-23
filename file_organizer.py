import os
import shutil
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from PIL import Image, ImageTk
import logging
import hashlib
import re
from collections import defaultdict

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Discord color palette
DISCORD_DARK = "#36393F"
DISCORD_DARKER = "#2F3136"
DISCORD_DARKEST = "#202225"
DISCORD_LIGHT = "#DCDDDE"
DISCORD_BLURPLE = "#5865F2"
DISCORD_GREEN = "#3BA55C"
DISCORD_RED = "#ED4245"
DISCORD_GREY = "#4F545C"

CONFIG_FILE = 'file_types.json'
UNDO_FILE = 'undo_log.json'
DEFAULT_FILE_TYPES = {
    "Documents": ['.pdf', '.docx', '.txt', '.pptx', '.xlsx', '.csv'],
    "Images": ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg'],
    "Videos": ['.mp4', '.mov', '.avi', '.mkv', '.flv'],
    "Music": ['.mp3', '.wav', '.flac', '.aac'],
    "Archives": ['.zip', '.rar', '.tar', '.gz', '.7z'],
    "Programs": ['.exe', '.msi', '.dmg'],
    "Scripts": ['.py', '.js', '.html', '.css', '.sh']
}
SIZE_RANGES = {
    "Small (<1MB)": (0, 1_000_000),
    "Medium (1-10MB)": (1_000_000, 10_000_000),
    "Large (>10MB)": (10_000_000, float('inf'))
}

def load_file_types():
    """Load file types from config file or return defaults."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        return DEFAULT_FILE_TYPES
    except json.JSONDecodeError:
        logger.error("Invalid JSON in config file. Using default file types.")
        return DEFAULT_FILE_TYPES

def save_file_types(file_types):
    """Save file types to config file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(file_types, f, indent=4)
    except Exception as e:
        logger.error(f"Failed to save config: {str(e)}")
        messagebox.showerror("Error", f"Failed to save config: {str(e)}")

def add_file_type(folder_name, extensions, file_types):
    """Add new file type mapping."""
    if not folder_name or not extensions:
        messagebox.showerror("Error", "Folder name and extensions are required.")
        return False
    try:
        extensions_list = [ext.strip().lower() for ext in extensions.split(',') if ext.strip()]
        if not extensions_list:
            messagebox.showerror("Error", "No valid extensions provided.")
            return False
        file_types[folder_name] = extensions_list
        save_file_types(file_types)
        messagebox.showinfo("Success", f"File type '{folder_name}' added.")
        return True
    except Exception as e:
        logger.error(f"Error adding file type: {str(e)}")
        messagebox.showerror("Error", f"Error adding file type: {str(e)}")
        return False

def compute_file_hash(file_path):
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        logger.error(f"Error computing hash for {file_path}: {str(e)}")
        return None

def save_undo_log(undo_log):
    """Save undo log to file."""
    try:
        with open(UNDO_FILE, 'w') as f:
            json.dump(undo_log, f, indent=4)
    except Exception as e:
        logger.error(f"Failed to save undo log: {str(e)}")

def load_undo_log():
    """Load undo log from file."""
    try:
        if os.path.exists(UNDO_FILE):
            with open(UNDO_FILE, 'r') as f:
                return json.load(f)
        return []
    except json.JSONDecodeError:
        logger.error("Invalid JSON in undo log. Returning empty log.")
        return []

def undo_last_organization():
    """Revert last file organization."""
    try:
        undo_log = load_undo_log()
        if not undo_log:
            messagebox.showinfo("Info", "No operations to undo.")
            return

        for entry in undo_log[-1]:
            src = entry['dest']
            dest = entry['src']
            if os.path.exists(src):
                shutil.move(src, dest)
                logger.info(f"Reverted: Moved {src} back to {dest}")
        undo_log.pop()
        save_undo_log(undo_log)
        messagebox.showinfo("Success", "Last organization undone successfully!")
    except Exception as e:
        logger.error(f"Error undoing organization: {str(e)}")
        messagebox.showerror("Error", f"Error undoing organization: {str(e)}")

def organize_files(folder_path, copy_files=False, dry_run=False, size_sort=False, custom_rule="", exclude_folders=None):
    """Organize files with advanced options."""
    try:
        if not os.path.exists(folder_path):
            messagebox.showerror("Error", "Selected folder does not exist.")
            return

        file_types = load_file_types()
        exclude_folders = exclude_folders or []
        undo_log = load_undo_log()
        current_log = []
        file_hashes = defaultdict(list)
        total_files = sum(1 for _ in os.listdir(folder_path) if not os.path.isdir(os.path.join(folder_path, _)))
        progress_var = tk.DoubleVar()
        progress_bar = None

        if not dry_run:
            root = tk.Toplevel()
            root.title("Progress")
            center_window(root, 300, 100)
            root.configure(bg=DISCORD_DARK)
            style = ttk.Style(root)
            configure_styles(style)
            
            progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=total_files)
            progress_bar.pack(pady=5, padx=10, fill="x")
            progress_label = ttk.Label(root, text="Organizing files...", background=DISCORD_DARK, foreground=DISCORD_LIGHT)
            progress_label.pack(pady=5)
            root.update()

        processed = 0
        preview = []

        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            
            if os.path.isdir(file_path) or any(excl in file_path for excl in exclude_folders):
                continue

            file_extension = os.path.splitext(filename)[1].lower()
            file_size = os.path.getsize(file_path)
            destination_folder = None

            if custom_rule and re.match(custom_rule, filename):
                destination_folder = "CustomRule"

            if not destination_folder:
                for folder, extensions in file_types.items():
                    if file_extension in extensions:
                        destination_folder = folder
                        break

            if size_sort and not destination_folder:
                for size_cat, (min_size, max_size) in SIZE_RANGES.items():
                    if min_size <= file_size < max_size:
                        destination_folder = size_cat
                        break

            if not destination_folder:
                destination_folder = file_extension[1:].upper() if file_extension else "NoExtension"

            dest_path = os.path.join(folder_path, destination_folder)
            final_dest = os.path.join(dest_path, filename)

            file_hash = compute_file_hash(file_path)
            if file_hash:
                if file_hash in file_hashes:
                    base, ext = os.path.splitext(filename)
                    counter = 1
                    while os.path.exists(final_dest):
                        final_dest = os.path.join(dest_path, f"{base}_{counter}{ext}")
                        counter += 1
                file_hashes[file_hash].append(final_dest)

            if dry_run:
                preview.append(f"{filename} -> {destination_folder}")
                continue

            os.makedirs(dest_path, exist_ok=True)
            try:
                if copy_files:
                    shutil.copy2(file_path, final_dest)
                else:
                    shutil.move(file_path, final_dest)
                    current_log.append({'src': file_path, 'dest': final_dest})
                logger.info(f"{'Copied' if copy_files else 'Moved'} {filename} to {destination_folder}")
            except (shutil.Error, OSError) as e:
                logger.error(f"Error processing {filename}: {str(e)}")
                continue

            processed += 1
            progress_var.set(processed)
            if progress_bar:
                root.update()

        if dry_run:
            messagebox.showinfo("Dry Run Preview", "\n".join(preview)[:500] + ("..." if len(preview) > 10 else ""))
            return

        if current_log:
            undo_log.append(current_log)
            save_undo_log(undo_log)
        if progress_bar:
            root.destroy()
        messagebox.showinfo("Success", "Files organized successfully!")
    except Exception as e:
        logger.error(f"Error organizing files: {str(e)}")
        messagebox.showerror("Error", f"Error organizing files: {str(e)}")

def select_folder(copy_files, dry_run, size_sort, custom_rule, exclude_folders):
    """Open folder selection dialog and organize files."""
    folder_selected = filedialog.askdirectory()
    if folder_selected:
        organize_files(folder_selected, copy_files=copy_files, dry_run=dry_run, 
                      size_sort=size_sort, custom_rule=custom_rule, exclude_folders=exclude_folders)

def center_window(root, width=600, height=500):
    """Center window on screen."""
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    root.geometry(f"{width}x{height}+{x}+{y}")

def resize_image(image_path, width, height):
    """Resize image while maintaining quality."""
    try:
        image = Image.open(image_path)
        resized_image = image.resize((width, height), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(resized_image)
    except Exception as e:
        logger.error(f"Error resizing image {image_path}: {str(e)}")
        return None

def show_file_types():
    """Display current file type mappings."""
    file_types = load_file_types()
    preview = "\n".join(f"{folder}: {', '.join(exts)}" for folder, exts in file_types.items())
    messagebox.showinfo("File Types", preview or "No file types defined.")

def configure_styles(style):
    """Configure ttk styles for Discord theme."""
    style.theme_use('clam')
    
    # Frame styles
    style.configure('.', background=DISCORD_DARK, foreground=DISCORD_LIGHT)
    style.configure('TFrame', background=DISCORD_DARK)
    style.configure('TLabelframe', background=DISCORD_DARK, foreground=DISCORD_LIGHT)
    style.configure('TLabelframe.Label', background=DISCORD_DARK, foreground=DISCORD_LIGHT)
    
    # Label styles
    style.configure('TLabel', background=DISCORD_DARK, foreground=DISCORD_LIGHT)
    
    # Button styles
    style.configure('TButton', 
                   background=DISCORD_GREY, 
                   foreground=DISCORD_LIGHT,
                   borderwidth=0,
                   focuscolor=DISCORD_DARK,
                   font=('Helvetica', 9))
    style.map('TButton',
              background=[('active', DISCORD_BLURPLE), ('pressed', DISCORD_BLURPLE)],
              foreground=[('active', 'white'), ('pressed', 'white')])
    
    # Entry styles
    style.configure('TEntry', 
                   fieldbackground=DISCORD_DARKER,
                   foreground=DISCORD_LIGHT,
                   insertcolor=DISCORD_LIGHT,
                   borderwidth=1,
                   relief='flat')
    style.map('TEntry',
              fieldbackground=[('focus', DISCORD_DARKER)],
              foreground=[('focus', 'white')])
    
    # Checkbutton styles
    style.configure('TCheckbutton', 
                   background=DISCORD_DARK,
                   foreground=DISCORD_LIGHT)
    style.map('TCheckbutton',
              background=[('active', DISCORD_DARK)])
    
    # Progressbar styles
    style.configure('Horizontal.TProgressbar', 
                   background=DISCORD_BLURPLE,
                   troughcolor=DISCORD_DARKER,
                   bordercolor=DISCORD_DARK,
                   lightcolor=DISCORD_BLURPLE,
                   darkcolor=DISCORD_BLURPLE)
    
    # Scrollbar styles
    style.configure('Vertical.TScrollbar', 
                   background=DISCORD_DARKER,
                   troughcolor=DISCORD_DARK,
                   bordercolor=DISCORD_DARK,
                   arrowcolor=DISCORD_LIGHT)
    style.map('Vertical.TScrollbar',
              background=[('active', DISCORD_GREY)])

def setup_gui():
    """Setup the GUI with Discord-like theme."""
    root = tk.Tk()
    root.title("File Organizer")
    root.configure(background=DISCORD_DARK)
    
    try:
        root.iconbitmap('app_icon.ico')
    except:
        logger.warning("Could not load icon file")

    # Load and resize icons
    icons = {
        'folder': resize_image("folder_icon.png", 20, 20),
        'add': resize_image("add_icon.png", 20, 20),
        'exit': resize_image("exit_icon.png", 20, 20),
        'undo': resize_image("undo_icon.png", 20, 20),
        'preview': resize_image("preview_icon.png", 20, 20)
    }

    root.resizable(False, False)
    center_window(root)

    # Configure styles
    style = ttk.Style(root)
    configure_styles(style)

    # Create main frame with scrollbar
    main_frame = ttk.Frame(root)
    main_frame.pack(fill="both", expand=True)
    
    canvas = tk.Canvas(main_frame, bg=DISCORD_DARK, highlightthickness=0)
    scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
    scrollbar.pack(side="right", fill="y")

    # Content frame
    content_frame = ttk.Frame(scrollable_frame)
    content_frame.pack(padx=10, pady=10, fill="both")

    # Title and description
    ttk.Label(content_frame, 
              text="File Organizer", 
              font=("Helvetica", 14, "bold"),
              foreground=DISCORD_LIGHT).pack(pady=10)
    ttk.Label(content_frame, 
              text="Organize files by extensions, size, or custom rules",
              font=("Helvetica", 9),
              foreground=DISCORD_LIGHT).pack(pady=3)

    # File type input frame
    file_type_frame = ttk.LabelFrame(content_frame, text="File Types", padding=10)
    file_type_frame.pack(fill="x", pady=5, padx=5)
    
    ttk.Label(file_type_frame, text="Folder Name:").pack(anchor="w")
    folder_entry = ttk.Entry(file_type_frame, font=("Helvetica", 9), width=25)
    folder_entry.pack(fill="x", pady=3)
    
    ttk.Label(file_type_frame, text="Extensions (comma-separated):").pack(anchor="w")
    extension_entry = ttk.Entry(file_type_frame, font=("Helvetica", 9), width=25)
    extension_entry.pack(fill="x", pady=3)
    
    ttk.Button(
        file_type_frame,
        text="Add File Type",
        image=icons.get('add'),
        compound=tk.LEFT,
        command=lambda: add_file_type(folder_entry.get(), extension_entry.get(), load_file_types())
    ).pack(fill="x", pady=5)
    
    ttk.Button(
        file_type_frame,
        text="View File Types",
        image=icons.get('preview'),
        compound=tk.LEFT,
        command=show_file_types
    ).pack(fill="x", pady=5)

    # Advanced options frame
    advanced_frame = ttk.LabelFrame(content_frame, text="Advanced Options", padding=10)
    advanced_frame.pack(fill="x", pady=5, padx=5)
    
    ttk.Label(advanced_frame, text="Custom Regex Rule:").pack(anchor="w")
    custom_rule_entry = ttk.Entry(advanced_frame, font=("Helvetica", 9), width=25)
    custom_rule_entry.pack(fill="x", pady=3)
    
    ttk.Label(advanced_frame, text="Exclude Folders (comma-separated):").pack(anchor="w")
    exclude_folders_entry = ttk.Entry(advanced_frame, font=("Helvetica", 9), width=25)
    exclude_folders_entry.pack(fill="x", pady=3)
    
    copy_var = tk.BooleanVar()
    ttk.Checkbutton(
        advanced_frame,
        text="Copy files instead of moving",
        variable=copy_var
    ).pack(anchor="w", pady=2)
    
    dry_run_var = tk.BooleanVar()
    ttk.Checkbutton(
        advanced_frame,
        text="Dry run (preview changes)",
        variable=dry_run_var
    ).pack(anchor="w", pady=2)
    
    size_sort_var = tk.BooleanVar()
    ttk.Checkbutton(
        advanced_frame,
        text="Sort by size categories",
        variable=size_sort_var
    ).pack(anchor="w", pady=2)

    # Action buttons frame
    action_frame = ttk.Frame(content_frame)
    action_frame.pack(fill="x", pady=10)
    
    ttk.Button(
        action_frame,
        text="Organize Folder",
        image=icons.get('folder'),
        compound=tk.LEFT,
        style='Accent.TButton',
        command=lambda: select_folder(
            copy_var.get(),
            dry_run_var.get(),
            size_sort_var.get(),
            custom_rule_entry.get(),
            [f.strip() for f in exclude_folders_entry.get().split(',') if f.strip()]
        )
    ).pack(fill="x", pady=3)
    
    ttk.Button(
        action_frame,
        text="Undo Last Operation",
        image=icons.get('undo'),
        compound=tk.LEFT,
        command=undo_last_organization
    ).pack(fill="x", pady=3)
    
    ttk.Button(
        action_frame,
        text="Exit",
        image=icons.get('exit'),
        compound=tk.LEFT,
        command=root.destroy
    ).pack(fill="x", pady=3)

    # Create an accent button style
    style.configure('Accent.TButton', 
                   background=DISCORD_BLURPLE, 
                   foreground='white',
                   font=('Helvetica', 9, 'bold'))
    style.map('Accent.TButton',
              background=[('active', '#4752C4'), ('pressed', '#3A45B5')])

    # Enable mouse wheel scrolling
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    root.mainloop()

if __name__ == "__main__":
    setup_gui()
