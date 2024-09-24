import os
import shutil
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from ttkthemes import ThemedTk
from PIL import Image, ImageTk  # Import Pillow to handle image resizing

config_file = 'file_types.json'

# Load the configuration file with file types, or use defaults
def load_file_types():
    if not os.path.exists(config_file):
        return {
            "Documents": ['.pdf', '.docx', '.txt', '.pptx', '.xlsx', '.csv'],
            "Images": ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg'],
            "Videos": ['.mp4', '.mov', '.avi', '.mkv', '.flv'],
            "Music": ['.mp3', '.wav', '.flac', '.aac'],
            "Archives": ['.zip', '.rar', '.tar', '.gz', '.7z'],
            "Programs": ['.exe', '.msi', '.dmg'],
            "Scripts": ['.py', '.js', '.html', '.css', '.sh'],
            "Others": []
        }
    with open(config_file, 'r') as f:
        return json.load(f)

file_types = load_file_types()

# Function to save the updated file types
def save_file_types():
    with open(config_file, 'w') as f:
        json.dump(file_types, f, indent=4)

# Function to add new file type mapping
def add_file_type(folder_name, extensions):
    if folder_name and extensions:
        extensions_list = [ext.strip() for ext in extensions.split(',')]
        file_types[folder_name] = extensions_list
        save_file_types()
        messagebox.showinfo("Success", f"File type for '{folder_name}' added successfully.")
    else:
        messagebox.showerror("Error", "Please enter both folder name and extensions.")

# Function to organize files based on their extension or size
def organize_files(folder_path, copy_files=False):
    try:
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)

            # Skip directories
            if os.path.isdir(file_path):
                continue

            # Get the file extension
            file_extension = os.path.splitext(filename)[1].lower()

            # Move the file to the correct folder based on extension
            moved = False
            for folder, extensions in file_types.items():
                if file_extension in extensions:
                    destination_folder = os.path.join(folder_path, folder)
                    os.makedirs(destination_folder, exist_ok=True)
                    if copy_files:
                        shutil.copy(file_path, destination_folder)
                    else:
                        shutil.move(file_path, destination_folder)
                    moved = True
                    break

            # If no match, move to "Others"
            if not moved:
                other_folder = os.path.join(folder_path, "Others")
                os.makedirs(other_folder, exist_ok=True)
                if copy_files:
                    shutil.copy(file_path, other_folder)
                else:
                    shutil.move(file_path, other_folder)

        messagebox.showinfo("Success", "Files have been organized successfully!")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred: {str(e)}")

# Function to open folder dialog and organize the selected folder
def select_folder(copy_files):
    folder_selected = filedialog.askdirectory()  # Open folder selection dialog
    if folder_selected:
        organize_files(folder_selected, copy_files=copy_files)

# Center the window on the screen
def center_window(root, width=550, height=400):  # Increased height to 400
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x_coordinate = int((screen_width / 2) - (width / 2))
    y_coordinate = int((screen_height / 2) - (height / 2))
    root.geometry(f"{width}x{height}+{x_coordinate}+{y_coordinate}")

# Resize images dynamically
def resize_image(image_path, width, height):
    image = Image.open(image_path)  # Open the image file
    
    # Use LANCZOS resampling for high-quality resizing
    resized_image = image.resize((width, height), Image.LANCZOS)  # Resize the image
    
    return ImageTk.PhotoImage(resized_image)  # Convert to PhotoImage

# GUI Setup with a Discord-like theme
def setup_gui():
    root = ThemedTk(theme="equilux")  # Discord-like dark theme
    root.title("File Organizer - Discord Theme")
    
    # Add window icon (replace 'app_icon.ico' with your actual icon file)
    root.iconbitmap('app_icon.ico')  # You must have an .ico file named 'app_icon.ico'

    # Resize icons dynamically
    folder_icon = resize_image("folder_icon.png", 24, 24)  # Resize to 24x24
    add_icon = resize_image("add_icon.png", 24, 24)  # Resize to 24x24
    exit_icon = resize_image("exit_icon.png", 24, 24)  # Resize to 24x24

    # Fix the window size and make it non-resizable
    window_width = 550
    window_height = 400  # Increased the height
    root.resizable(False, False)  # Disable resizing
    center_window(root, width=window_width, height=window_height)  # Center on screen

    # ttk Styles for modern UI
    style = ttk.Style(root)
    style.configure("TLabel", font=("Verdana", 10), background="#2c2f33", foreground="#ffffff")
    style.configure("TButton", font=("Verdana", 10), background="#7289da", foreground="#ffffff", padding=10)
    style.configure("TCheckbutton", background="#2c2f33", foreground="#ffffff")
    root.configure(background="#2c2f33")

    # Add a title and description
    title_label = ttk.Label(root, text="File Organizer", font=("Verdana", 16), padding=10)
    title_label.pack()

    description_label = ttk.Label(root, text="Organize your files into folders based on their extensions", padding=10)
    description_label.pack()

    # Add a form to configure new file type mappings
    folder_label = ttk.Label(root, text="Folder Name:")
    folder_label.pack(pady=5)
    folder_entry = ttk.Entry(root, font=("Verdana", 10))
    folder_entry.pack(pady=5)

    extension_label = ttk.Label(root, text="Extensions (comma separated):")
    extension_label.pack(pady=5)
    extension_entry = ttk.Entry(root, font=("Verdana", 10))
    extension_entry.pack(pady=5)

    # Button to add new file types with an icon
    add_button = ttk.Button(root, text="Add File Type", image=add_icon, compound=tk.LEFT, command=lambda: add_file_type(folder_entry.get(), extension_entry.get()))
    add_button.pack(pady=5)

    # Add backup/copy files option
    copy_var = tk.BooleanVar()
    copy_check = ttk.Checkbutton(root, text="Copy files instead of moving", variable=copy_var)
    copy_check.pack(pady=10)

    # Organize button with folder icon
    button = ttk.Button(root, text="Select Folder & Organize", image=folder_icon, compound=tk.LEFT, command=lambda: select_folder(copy_var.get()))
    button.pack(pady=10)

    # Exit button with an icon
    exit_button = ttk.Button(root, text="Exit", image=exit_icon, compound=tk.LEFT, command=root.destroy)
    exit_button.pack(pady=15)

    root.mainloop()

# Run the GUI
if __name__ == "__main__":
    setup_gui()
