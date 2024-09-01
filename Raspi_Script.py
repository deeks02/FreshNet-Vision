import cv2
import cvzone
from picamera2 import Picamera2
import numpy as np
import pandas as pd
from PIL import Image, ImageTk
from pathlib import Path
import pandas as pd
from tkinter import Tk, Canvas, Entry, Text, Button, PhotoImage
from ultralytics import YOLO
import threading
import time
import spidev


OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / Path(r"E:\Major Pro\build-20240426T051822Z-001\build\assets\frame0")

# Define SPI bus and CE pin
spi_bus = 0
spi_device = 0

# Open SPI connection
spi = spidev.SpiDev()
spi.open(spi_bus, spi_device)
spi.max_speed_hz = 1000000  # Set max speed to 1 Mbps

# Initialize the camera
picam2 = Picamera2()
picam2.preview_configuration.main.size = (640, 480)
picam2.preview_configuration.main.format = "RGB888"
picam2.preview_configuration.controls.FrameRate = 60
picam2.preview_configuration.align()
picam2.configure("preview")
picam2.start()

def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)

#Load the model
model = YOLO('/content/bestyolov8n.pt')

# Define fish data
data = {
    'Species': ['Catla', 'Croaker', 'HorseMackerel', 'Mackerel', 'MilkFish', 'Rohu', 'Sardine', 'SeaBass', 'Threadfin', 'Tilapia'],
    'small': [50, 25, 25, 20, 25, 25, 15, 25, 25, 20],
    'medium': [100, 45, 35, 35, 45, 40, 20, 35, 35, 25],
    'large': [150, 60, 40, 40, 55, 50, 25, 55, 55, 30]
}
df = pd.DataFrame(data)

# Define counters and scaling factor
small_c, medium_c, large_c = 0, 0, 0
sf = 0.15  # 1 pixel = 0.1 units (e.g., cm)

# Define function to update fish count text labels in GUI
def update_fish_counts():
    canvas.itemconfig(small_fish_count_text, text=f"{small_c}")
    canvas.itemconfig(medium_fish_count_text, text=f"{medium_c}")
    canvas.itemconfig(large_fish_count_text, text=f"{large_c}")

# Define variables to hold fish counts
small_fish_count = 0
medium_fish_count = 0
large_fish_count = 0
rejected_fish_count = 0

# Function to send fish size (string) over SPI
def send_fish_size(fish_size):
    # Convert fish size to list of ASCII values
    size_bytes = [ord(char) for char in fish_size]
    # Send each byte individually
    for byte in size_bytes:
        spi.xfer2([byte])
    # Send termination byte (0xFF) to indicate end of fish size
    spi.xfer2([0xFF])

# Function to send species match (boolean) over SPI
def send_species_match(species_match):
    # Convert boolean to integer (0 for False, 1 for True)
    match_byte = int(species_match)
    # Send match byte
    spi.xfer2([match_byte])

# Define a function to update the selected species
def update_species(species_name):
    global selected_species
    selected_species = species_name
    canvas.itemconfig(species_text, text=selected_species)

# Function to handle starting the conveyor belt
def start_conveyor():
    print("Starting conveyor belt...")
    spi.open(spi_bus, spi_device)  # Open SPI connection
    spi.xfer([0x01])  # Send byte 0x01 to start the motor via SPI
    time.sleep(0.1)  # Small delay for SPI communication
    spi.close()  # Close SPI connection
    print("Conveyor belt started.")

# Function to handle stopping the conveyor belt
def stop_conveyor():
    print("Stopping conveyor belt...")
    spi.open(spi_bus, spi_device)  # Open SPI connection
    spi.xfer([0x00])  # Send byte 0x00 to stop the motor via SPI
    time.sleep(0.1)  # Small delay for SPI communication
    spi.close()  # Close SPI connection
    print("Conveyor belt stopped.")


# Function to run fish classification and update the frame with the processed image
def update_frame(img):
    img = run_fish_classification()
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    # Resize the image to fit the frame
    width, height = 1153 - 682, 474 - 185
    pil_img = pil_img.resize((width, height), Image.ANTIALIAS)   
    tk_img = ImageTk.PhotoImage(image=pil_img)
    canvas.create_image((682.0, 185.0), anchor="nw", image=tk_img)
    canvas.image = tk_img  # Keep a reference to avoid garbage collection
    window.after(1000, update_frame)  # Keep updating the frame after a delay

def run_fish_classification():
    global small_c, medium_c, large_c
    while True:
        img = picam2.capture_array() # Replace with your image path
        img = cv2.resize(img, (260, 240))
        results = model.predict(img)

        a = results[0].boxes.data
        px = pd.DataFrame(a).astype("float")

        for _, row in px.iterrows():
            x1, y1, x2, y2, _, d = map(int, row[:6])
            Fspecie = data['Species'][d]
            width = (x2 - x1) * sf
            height = (y2 - y1) * sf
            Fsize = max(width, height)

            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cvzone.putTextRect(img, Fspecie, (x1, y1), 2, 2, font=cv2.FONT_HERSHEY_PLAIN)

            if Fspecie == selected_species:
                s_match = True
                size = 'small' if Fsize <= df.loc[df['Species'] == selected_species, 'small'].iloc[0] else (
                    'medium' if Fsize <= df.loc[df['Species'] == selected_species, 'medium'].iloc[0] else 'large')
                if size == 'small':
                    small_c += 1
                elif size == 'medium':
                    medium_c += 1
                else:
                    large_c += 1
                update_fish_counts()  # Update GUI fish counts
                 # Send fish size and species match over SPI
                send_fish_size(size)
                send_species_match(s_match)
            else:
                s_match = False
                continue
        update_frame(img)

        if cv2.waitKey(1) == ord('q'):
            # Close camera preview
            picam2.stop()
            spi.close()
            cv2.destroyAllWindows()
            break


# GUI elements (similar to the previous code)
window = Tk()

window.geometry("1280x720")
window.configure(bg = "#05194E")


canvas = Canvas(
    window,
    bg = "#05194E",
    height = 720,
    width = 1280,
    bd = 0,
    highlightthickness = 0,
    relief = "ridge"
)

canvas.place(x = 0, y = 0)
canvas.create_rectangle(
    126.0,
    104.0,
    657.0,
    154.0,
    fill="#1BC9FA",
    outline="")

canvas.create_text(
    138.0,
    115.0,
    anchor="nw",
    text="CHOOSE A FISH SPECIES",
    fill="#041B59",
    font=("Inter Bold", 25 * -1,"bold")
)

image_image_1 = PhotoImage(
    file=relative_to_assets("image_1.png"))
image_1 = canvas.create_image(
    270.0,
    595.0,
    image=image_image_1
)

image_image_2 = PhotoImage(
    file=relative_to_assets("image_2.png"))
image_2 = canvas.create_image(
    419.0,
    210.0,
    image=image_image_2
)

canvas.create_text(
    174.0,
    572.0,
    anchor="nw",
    text="SMALL FISH",
    fill="#000000",
    font=("Inter Bold", 20 * -1,"bold")
)

canvas.create_text(
    262.0,
    185.0,
    anchor="nw",
    text="SELECTED  FISH",
    fill="#000000",
    font=("Inter Bold", 16 * -1,"bold")
)

small_fish_count_text = canvas.create_text(
    177.0,
    596.0,
    anchor="nw",
    text=small_fish_count,
    fill="#000000",
    font=("Inter Bold", 20 * -1)
)

image_image_3 = PhotoImage(
    file=relative_to_assets("image_3.png"))
image_3 = canvas.create_image(
    506.0,
    595.0,
    image=image_image_3
)

canvas.create_text(
    411.0,
    572.0,
    anchor="nw",
    text="MEDIUM FISH",
    fill="#000000",
    font=("Inter Bold", 20 * -1,"bold")
)

medium_fish_count_text = canvas.create_text(
    412.0,
    597.0,
    anchor="nw",
    text=medium_fish_count,
    fill="#000000",
    font=("Inter Bold", 20 * -1)
)

image_image_4 = PhotoImage(
    file=relative_to_assets("image_4.png"))
image_4 = canvas.create_image(
    270.0,
    661.0,
    image=image_image_4
)

canvas.create_text(
    170.0,
    638.0,
    anchor="nw",
    text="LARGE FISH",
    fill="#000000",
    font=("Inter Bold", 20 * -1,"bold")
)

large_fish_count_text = canvas.create_text(
    177.0,
    662.0,
    anchor="nw",
    text=large_fish_count,
    fill="#000000",
    font=("Inter Bold", 20 * -1)
)

image_image_5 = PhotoImage(
    file=relative_to_assets("image_5.png"))
image_5 = canvas.create_image(
    506.0,
    661.0,
    image=image_image_5
)

canvas.create_text(
    411.0,
    638.0,
    anchor="nw",
    text="REJECTED FISHES",
    fill="#000000",
    font=("Inter Bold", 20 * -1,"bold")
)

rejected_fish_count_text = canvas.create_text(
    412.0,
    662.0,
    anchor="nw",
    text=rejected_fish_count,
    fill="#000000",
    font=("Inter Bold", 20 * -1)
)

image_image_6 = PhotoImage(
    file=relative_to_assets("image_6.png"))
image_6 = canvas.create_image(
    613.0,
    129.0,
    image=image_image_6
)

canvas.create_rectangle(
    320.0,
    18.0,
    1020.0,
    77.0,
    fill="#06153B",
    outline=""
)
# Image disp
'''canvas.create_rectangle(
    682.0,
    185.0,
    1153.0,
    474.0,
    fill="#472398",
    outline=""
)'''

canvas.create_rectangle(
    680.0,
    504.0,
    1153.0,
    552.0,
    fill="#1BC9FA",
    outline="")

canvas.create_rectangle(
    687.0,
    104.0,
    1145.0,
    154.0,
    fill="#1BC9FA",
    outline="")

canvas.create_text(
    712.0,
    117.0,
    anchor="nw",
    text="CAMERA FEED",
    fill="#06153B",
    font=("Inter Bold", 25 * -1,"bold")
)

# Create a variable to store the selected species
selected_species =""
species_text = canvas.create_text(
    264.0,
    205.0,
    anchor="nw",
    text=selected_species,
    fill="#04277F",
    font=("Inter Bold", 20 * -1,"bold")
)

image_image_7 = PhotoImage(
    file=relative_to_assets("image_7.png"))
image_7 = canvas.create_image(
    497.0,
    47.0,
    image=image_image_7
)

canvas.create_text(
    554.0,
    28.0,
    anchor="nw",
    text="FreshNet Vision",
    fill="#FFFFFF",
    font=("Inter Bold", 40 * -1,"bold")
)

button_image_1 = PhotoImage(
    file=relative_to_assets("button_1.png"))
button_1 = Button(
    image=button_image_1,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("Croaker Selected"),
    relief="flat"
)
button_image_1 = PhotoImage(file=relative_to_assets("button_1.png"))
button_1 = Button(
    image=button_image_1,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: update_species("Croaker"),
    relief="flat"
)
button_1.place(
    x=322,
    y=255,
    width=161.0296630859375,
    height=48.064674377441406
)

button_image_3 = PhotoImage(
    file=relative_to_assets("button_3.png"))
button_3 = Button(
    image=button_image_3,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("Mackerel Selected"),
    relief="flat"
)
button_image_3 = PhotoImage(file=relative_to_assets("button_3.png"))
button_3 = Button(
    image=button_image_3,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: update_species("Mackerel"),
    relief="flat"
)
button_3.place(
    x=148,
    y=315,
    width=161.0296630859375,
    height=48.064674377441406
)

button_image_4 = PhotoImage(
    file=relative_to_assets("button_4.png"))
button_4 = Button(
    image=button_image_4,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("Horse Mackerel Selected"),
    relief="flat"
)
button_image_4 = PhotoImage(file=relative_to_assets("button_4.png"))
button_4 = Button(
    image=button_image_4,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: update_species("Horse Mackerel"),
    relief="flat"
)

button_4.place(
    x=497,
    y=255,
    width=161.0296630859375,
    height=48.064674377441406
)

button_image_5 = PhotoImage(
    file=relative_to_assets("button_5.png"))
button_5 = Button(
    image=button_image_5,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("MilkFish Selected"),
    relief="flat"
)
button_image_5 = PhotoImage(file=relative_to_assets("button_5.png"))
button_5 = Button(
    image=button_image_5,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: update_species("Milkfish"),
    relief="flat"
)
button_5.place(
    x=322,
    y=321,
    width=161.0296630859375,
    height=48.064674377441406
)

button_image_6 = PhotoImage(
    file=relative_to_assets("button_6.png"))
button_6 = Button(
    image=button_image_6,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("Sardine Selected"),
    relief="flat"
)
button_image_6 = PhotoImage(file=relative_to_assets("button_6.png"))
button_6 = Button(
    image=button_image_6,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: update_species("Sardine"),
    relief="flat"
)

button_6.place(
    x=148,
    y=376,
    width=161.0296630859375,
    height=48.064674377441406
)

button_image_7 = PhotoImage(
    file=relative_to_assets("button_7.png"))
button_7 = Button(
    image=button_image_7,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("Rohu selected"),
    relief="flat"
)
button_image_7 = PhotoImage(file=relative_to_assets("button_7.png"))
button_7 = Button(
    image=button_image_7,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: update_species("Rohu"),
    relief="flat"
)
button_7.place(
    x=497,
    y=320,
    width=161.0296630859375,
    height=48.064674377441406
)

button_image_8 = PhotoImage(
    file=relative_to_assets("button_8.png"))
button_8 = Button(
    image=button_image_8,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("SeaBass Selected"),
    relief="flat"
)
button_image_8 = PhotoImage(file=relative_to_assets("button_8.png"))
button_8 = Button(
    image=button_image_8,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: update_species("Sea Bass"),
    relief="flat"
)
button_8.place(
    x=322,
    y=378,
    width=161.0296630859375,
    height=48.064674377441406
)

button_image_9 = PhotoImage(
    file=relative_to_assets("button_9.png"))
button_9 = Button(
    image=button_image_9,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("Threadfin Selected"),
    relief="flat"
)
button_image_9 = PhotoImage(file=relative_to_assets("button_9.png"))
button_9 = Button(
    image=button_image_9,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: update_species("Threadfin"),
    relief="flat"
)
button_9.place(
    x=497,
    y=380,
    width=161.0296630859375,
    height=48.064674377441406
)

button_image_10 = PhotoImage(
    file=relative_to_assets("button_10.png"))
button_10 = Button(
    image=button_image_10,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("Tilapia selected"),
    relief="flat"
)
button_image_10 = PhotoImage(file=relative_to_assets("button_10.png"))
button_10 = Button(
    image=button_image_10,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: update_species("Tilapia"),
    relief="flat"
)
button_10.place(
    x=322,
    y=435,
    width=161.0296630859375,
    height=48.064674377441406
)

image_image_8 = PhotoImage(
    file=relative_to_assets("image_8.png"))
image_8 = canvas.create_image(
    1099.0,
    125.0,
    image=image_image_8
)

image_image_9 = PhotoImage(
    file=relative_to_assets("image_9.png"))
image_9 = canvas.create_image(
    1101.0,
    528.0,
    image=image_image_9
)

button_image_11 = PhotoImage(
    file=relative_to_assets("button_11.png"))
button_11 = Button(
    image=button_image_11,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: print("Catla Selected"),
    relief="flat"
)
button_image_11 = PhotoImage(file=relative_to_assets("button_11.png"))
button_11 = Button(
    image=button_image_11,
    borderwidth=0,
    highlightthickness=0,
    command=lambda: update_species("Catla"),
    relief="flat"
)
button_11.place(
    x=148,
    y=255,
    width=161.0296630859375,
    height=48.064674377441406
)

# DC Motor Control
button_image_12 = PhotoImage(
    file=relative_to_assets("button_12.png"))
button_12 = Button(
    image=button_image_12,
    borderwidth=0,
    highlightthickness=0,
    command=start_conveyor,
    relief="flat"
)
button_12.place(
    x=811.36083984375,
    y=582.369140625,
    width=83.79434204101562,
    height=78.3320541381836
)

button_image_13 = PhotoImage(
    file=relative_to_assets("button_13.png"))
button_13 = Button(
    image=button_image_13,
    borderwidth=0,
    highlightthickness=0,
    command=stop_conveyor,
    relief="flat"
)
button_13.place(
    x=958.0009765625,
    y=582.369140625,
    width=83.79418182373047,
    height=74.92633819580078
)

canvas.create_text(
    
    687.0,
    510.0,
    anchor="nw",
    text="CONVEYER MOTOR CONTROL",
    fill="#05194E",
    font=("Inter Bold", 25 * -1,"bold")
)

canvas.create_rectangle(
    126.0,
    504.0,
    657.0,
    552.0,
    fill="#1BC9FA",
    outline="")

canvas.create_text(
    163.0,
    510.0,
    anchor="nw",
    text="FISH COUNT",
    fill="#05194E",
    font=("Inter Bold", 25 * -1,"bold")
)

image_image_10 = PhotoImage(
    file=relative_to_assets("image_10.png"))
image_10 = canvas.create_image(
    604.0,
    529.0,
    image=image_image_10
)
window.resizable(False, False)

# Main
# Start a separate thread to run fish classification and update the frame
thread = threading.Thread(target=run_fish_classification)
thread.daemon = True
thread.start()

window.mainloop()
