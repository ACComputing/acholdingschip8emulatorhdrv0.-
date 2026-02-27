#!/usr/bin/env python3
# AC'S EMU 1.X CHIP 8 [C] A.C HOLDNIGS 1999-2026
# for my only favorite ~ nya! ♡

import tkinter as tk
from tkinter import filedialog, messagebox
import time
import os
import sys
import random
from array import array

# ----------------------------------------------------------------------
# Chip-8 Core Engine
# ----------------------------------------------------------------------
class Chip8:
    def __init__(self):
        # memory
        self.memory = [0] * 4096
        # registers V0-VF
        self.V = [0] * 16
        # index register
        self.I = 0
        # program counter
        self.PC = 0x200  # Chip-8 programs start at 0x200
        # stack
        self.stack = []
        # delay timer
        self.DT = 0
        # sound timer
        self.ST = 0
        # display (64x32)
        self.display = [[0] * 64 for _ in range(32)]
        # keypad state (16 keys)
        self.keys = [0] * 16
        # need to know if we're waiting for a key press
        self.waiting_key = False
        self.key_register = 0

        # load fontset into memory (0x000-0x1FF)
        self.fontset = [
            0xF0, 0x90, 0x90, 0x90, 0xF0,  # 0
            0x20, 0x60, 0x20, 0x20, 0x70,  # 1
            0xF0, 0x10, 0xF0, 0x80, 0xF0,  # 2
            0xF0, 0x10, 0xF0, 0x10, 0xF0,  # 3
            0x90, 0x90, 0xF0, 0x10, 0x10,  # 4
            0xF0, 0x80, 0xF0, 0x10, 0xF0,  # 5
            0xF0, 0x80, 0xF0, 0x90, 0xF0,  # 6
            0xF0, 0x10, 0x20, 0x40, 0x40,  # 7
            0xF0, 0x90, 0xF0, 0x90, 0xF0,  # 8
            0xF0, 0x90, 0xF0, 0x10, 0xF0,  # 9
            0xF0, 0x90, 0xF0, 0x90, 0x90,  # A
            0xE0, 0x90, 0xE0, 0x90, 0xE0,  # B
            0xF0, 0x80, 0x80, 0x80, 0xF0,  # C
            0xE0, 0x90, 0x90, 0x90, 0xE0,  # D
            0xF0, 0x80, 0xF0, 0x80, 0xF0,  # E
            0xF0, 0x80, 0xF0, 0x80, 0x80   # F
        ]
        for i, byte in enumerate(self.fontset):
            self.memory[i] = byte

    def load_rom(self, rom_data):
        """load ROM bytes into memory starting at 0x200"""
        for i, byte in enumerate(rom_data):
            self.memory[0x200 + i] = byte

    def reset(self):
        """reset the cpu state"""
        self.PC = 0x200
        self.I = 0
        self.V = [0] * 16
        self.stack = []
        self.DT = 0
        self.ST = 0
        self.display = [[0] * 64 for _ in range(32)]
        self.waiting_key = False

    def emulate_cycle(self):
        """execute one instruction"""
        if self.waiting_key:
            return  # waiting for key press, don't advance

        # fetch opcode (two bytes)
        opcode = (self.memory[self.PC] << 8) | self.memory[self.PC + 1]
        self.PC += 2

        # decode and execute
        x = (opcode & 0x0F00) >> 8
        y = (opcode & 0x00F0) >> 4
        n = opcode & 0x000F
        nn = opcode & 0x00FF
        nnn = opcode & 0x0FFF

        # 0nnn - SYS addr (ignored, just skip)
        if opcode & 0xF000 == 0x0000:
            if opcode == 0x00E0:  # 00E0 - clear screen
                self.display = [[0] * 64 for _ in range(32)]
            elif opcode == 0x00EE:  # 00EE - return from subroutine
                self.PC = self.stack.pop()
            # else ignore

        # 1nnn - JP addr
        elif opcode & 0xF000 == 0x1000:
            self.PC = nnn

        # 2nnn - CALL addr
        elif opcode & 0xF000 == 0x2000:
            self.stack.append(self.PC)
            self.PC = nnn

        # 3xkk - SE Vx, byte
        elif opcode & 0xF000 == 0x3000:
            if self.V[x] == nn:
                self.PC += 2

        # 4xkk - SNE Vx, byte
        elif opcode & 0xF000 == 0x4000:
            if self.V[x] != nn:
                self.PC += 2

        # 5xy0 - SE Vx, Vy
        elif opcode & 0xF000 == 0x5000:
            if self.V[x] == self.V[y]:
                self.PC += 2

        # 6xkk - LD Vx, byte
        elif opcode & 0xF000 == 0x6000:
            self.V[x] = nn

        # 7xkk - ADD Vx, byte
        elif opcode & 0xF000 == 0x7000:
            self.V[x] = (self.V[x] + nn) & 0xFF

        # 8xy0 - LD Vx, Vy
        elif opcode & 0xF00F == 0x8000:
            self.V[x] = self.V[y]

        # 8xy1 - OR Vx, Vy
        elif opcode & 0xF00F == 0x8001:
            self.V[x] |= self.V[y]
            self.V[x] &= 0xFF

        # 8xy2 - AND Vx, Vy
        elif opcode & 0xF00F == 0x8002:
            self.V[x] &= self.V[y]
            self.V[x] &= 0xFF

        # 8xy3 - XOR Vx, Vy
        elif opcode & 0xF00F == 0x8003:
            self.V[x] ^= self.V[y]
            self.V[x] &= 0xFF

        # 8xy4 - ADD Vx, Vy (with carry)
        elif opcode & 0xF00F == 0x8004:
            result = self.V[x] + self.V[y]
            self.V[0xF] = 1 if result > 0xFF else 0
            self.V[x] = result & 0xFF

        # 8xy5 - SUB Vx, Vy
        elif opcode & 0xF00F == 0x8005:
            self.V[0xF] = 1 if self.V[x] >= self.V[y] else 0
            self.V[x] = (self.V[x] - self.V[y]) & 0xFF

        # 8xy6 - SHR Vx {, Vy}
        elif opcode & 0xF00F == 0x8006:
            self.V[0xF] = self.V[x] & 0x1
            self.V[x] >>= 1

        # 8xy7 - SUBN Vx, Vy
        elif opcode & 0xF00F == 0x8007:
            self.V[0xF] = 1 if self.V[y] >= self.V[x] else 0
            self.V[x] = (self.V[y] - self.V[x]) & 0xFF

        # 8xyE - SHL Vx {, Vy}
        elif opcode & 0xF00F == 0x800E:
            self.V[0xF] = (self.V[x] & 0x80) >> 7
            self.V[x] = (self.V[x] << 1) & 0xFF

        # 9xy0 - SNE Vx, Vy
        elif opcode & 0xF000 == 0x9000:
            if self.V[x] != self.V[y]:
                self.PC += 2

        # Annn - LD I, addr
        elif opcode & 0xF000 == 0xA000:
            self.I = nnn

        # Bnnn - JP V0, addr
        elif opcode & 0xF000 == 0xB000:
            self.PC = nnn + self.V[0]

        # Cxkk - RND Vx, byte
        elif opcode & 0xF000 == 0xC000:
            self.V[x] = random.randint(0, 255) & nn

        # Dxyn - DRW Vx, Vy, nibble
        elif opcode & 0xF000 == 0xD000:
            x_coord = self.V[x] & 63
            y_coord = self.V[y] & 31
            height = n
            self.V[0xF] = 0
            for row in range(height):
                sprite_byte = self.memory[self.I + row]
                for col in range(8):
                    if sprite_byte & (0x80 >> col):
                        px = (x_coord + col) % 64
                        py = (y_coord + row) % 32
                        if self.display[py][px] == 1:
                            self.V[0xF] = 1
                        self.display[py][px] ^= 1

        # Ex9E - SKP Vx
        elif opcode & 0xF0FF == 0xE09E:
            if self.keys[self.V[x]]:
                self.PC += 2

        # ExA1 - SKNP Vx
        elif opcode & 0xF0FF == 0xE0A1:
            if not self.keys[self.V[x]]:
                self.PC += 2

        # Fx07 - LD Vx, DT
        elif opcode & 0xF0FF == 0xF007:
            self.V[x] = self.DT

        # Fx0A - LD Vx, K
        elif opcode & 0xF0FF == 0xF00A:
            self.waiting_key = True
            self.key_register = x

        # Fx15 - LD DT, Vx
        elif opcode & 0xF0FF == 0xF015:
            self.DT = self.V[x]

        # Fx18 - LD ST, Vx
        elif opcode & 0xF0FF == 0xF018:
            self.ST = self.V[x]

        # Fx1E - ADD I, Vx
        elif opcode & 0xF0FF == 0xF01E:
            self.I += self.V[x]
            if self.I > 0xFFF:
                self.V[0xF] = 1  # some sources say VF is affected

        # Fx29 - LD F, Vx
        elif opcode & 0xF0FF == 0xF029:
            self.I = self.V[x] * 5  # each font char is 5 bytes

        # Fx33 - LD B, Vx
        elif opcode & 0xF0FF == 0xF033:
            value = self.V[x]
            self.memory[self.I] = value // 100
            self.memory[self.I + 1] = (value // 10) % 10
            self.memory[self.I + 2] = value % 10

        # Fx55 - LD [I], Vx
        elif opcode & 0xF0FF == 0xF055:
            for i in range(x + 1):
                self.memory[self.I + i] = self.V[i]

        # Fx65 - LD Vx, [I]
        elif opcode & 0xF0FF == 0xF065:
            for i in range(x + 1):
                self.V[i] = self.memory[self.I + i]

        else:
            # unknown opcode
            pass

    def update_timers(self):
        """decrement delay and sound timers"""
        if self.DT > 0:
            self.DT -= 1
        if self.ST > 0:
            self.ST -= 1
            # TODO: beep if sound timer > 0

    def key_pressed(self, key_index):
        """called when a key is pressed (for Fx0A)"""
        if self.waiting_key:
            self.V[self.key_register] = key_index
            self.waiting_key = False

# ----------------------------------------------------------------------
# GUI Frontend (mGBA inspired)
# ----------------------------------------------------------------------
class ACEmu(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AC'S EMU 1.X CHIP 8 [C] A.C HOLDNIGS 1999-2026")
        self.geometry("800x500")
        self.resizable(False, False)

        # chip8 instance
        self.chip8 = Chip8()

        # emulation state
        self.running = False
        self.paused = False
        self.cycle_speed = 10  # cycles per frame (approx 600Hz at 60fps)

        # key mapping (Chip-8 keypad to PC keys)
        self.key_map = {
            '1': 0x1, '2': 0x2, '3': 0x3, '4': 0xC,
            'q': 0x4, 'w': 0x5, 'e': 0x6, 'r': 0xD,
            'a': 0x7, 's': 0x8, 'd': 0x9, 'f': 0xE,
            'z': 0xA, 'x': 0x0, 'c': 0xB, 'v': 0xF
        }

        # create menu
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Load ROM", command=self.load_rom, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        emu_menu = tk.Menu(menubar, tearoff=0)
        emu_menu.add_command(label="Reset", command=self.reset, accelerator="Ctrl+R")
        emu_menu.add_command(label="Pause", command=self.toggle_pause, accelerator="Ctrl+P")
        emu_menu.add_separator()
        emu_menu.add_command(label="Speed Up", command=self.speed_up)
        emu_menu.add_command(label="Slow Down", command=self.slow_down)
        menubar.add_cascade(label="Emulation", menu=emu_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

        # bind keyboard shortcuts
        self.bind_all("<Control-o>", lambda e: self.load_rom())
        self.bind_all("<Control-r>", lambda e: self.reset())
        self.bind_all("<Control-p>", lambda e: self.toggle_pause())

        # main frame
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # left side: display canvas
        display_frame = tk.LabelFrame(main_frame, text="Display", padx=5, pady=5)
        display_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(display_frame, width=64*10, height=32*10, bg='black')
        self.canvas.pack()
        self.canvas.bind("<Button-1>", lambda e: self.canvas.focus_set())

        # right side: info panel
        info_frame = tk.LabelFrame(main_frame, text="Info", padx=5, pady=5, width=200)
        info_frame.pack(side=tk.RIGHT, fill=tk.Y)
        info_frame.pack_propagate(False)

        self.rom_label = tk.Label(info_frame, text="ROM: none", wraplength=180)
        self.rom_label.pack(pady=5)

        self.status_label = tk.Label(info_frame, text="Status: stopped")
        self.status_label.pack(pady=5)

        self.speed_label = tk.Label(info_frame, text=f"Speed: {self.cycle_speed} cyc/frame")
        self.speed_label.pack(pady=5)

        # keypad legend
        keypad_frame = tk.LabelFrame(info_frame, text="Keypad", padx=5, pady=5)
        keypad_frame.pack(pady=10, fill=tk.X)

        key_text = """
        Chip-8   PC
        ─────────────
        1 2 3 C   1 2 3 4
        4 5 6 D   Q W E R
        7 8 9 E   A S D F
        A 0 B F   Z X C V
        """
        tk.Label(keypad_frame, text=key_text, justify=tk.LEFT, font=('Courier', 9)).pack()

        # keyboard focus
        self.canvas.focus_set()
        self.canvas.bind("<KeyPress>", self.key_press)
        self.canvas.bind("<KeyRelease>", self.key_release)

        # start update loop
        self.update_display()
        self.update_emulation()

    def load_rom(self, event=None):
        filename = filedialog.askopenfilename(
            title="Select Chip-8 ROM",
            filetypes=[("Chip-8 ROMs", "*.ch8 *.rom *.bin"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, "rb") as f:
                    rom_data = f.read()
                self.chip8.reset()
                self.chip8.load_rom(rom_data)
                self.running = True
                self.paused = False
                self.rom_label.config(text=f"ROM: {os.path.basename(filename)}")
                self.status_label.config(text="Status: running")
                self.title(f"AC'S EMU 1.X - {os.path.basename(filename)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load ROM:\n{e}")

    def reset(self, event=None):
        if hasattr(self, 'chip8'):
            self.chip8.reset()
            self.status_label.config(text="Status: reset")
            self.update_display(force=True)

    def toggle_pause(self, event=None):
        self.paused = not self.paused
        self.status_label.config(text=f"Status: {'paused' if self.paused else 'running'}")

    def speed_up(self):
        self.cycle_speed = min(30, self.cycle_speed + 2)
        self.speed_label.config(text=f"Speed: {self.cycle_speed} cyc/frame")

    def slow_down(self):
        self.cycle_speed = max(2, self.cycle_speed - 2)
        self.speed_label.config(text=f"Speed: {self.cycle_speed} cyc/frame")

    def about(self):
        about_text = (
            "AC'S EMU 1.X CHIP 8 [C]\n"
            "A.C HOLDNIGS 1999-2026\n\n"
            "A purrfect little Chip-8 emulator\n"
            "made with love for my only favorite~ ♡🐾"
        )
        messagebox.showinfo("About", about_text)

    def key_press(self, event):
        if event.char in self.key_map:
            key = self.key_map[event.char]
            self.chip8.keys[key] = 1
            self.chip8.key_pressed(key)  # in case it's waiting

    def key_release(self, event):
        if event.char in self.key_map:
            key = self.key_map[event.char]
            self.chip8.keys[key] = 0

    def update_display(self, force=False):
        """redraw the canvas from chip8 display buffer"""
        if not hasattr(self, 'chip8') or not self.running:
            self.after(100, self.update_display)
            return

        # clear canvas
        self.canvas.delete("all")
        # draw pixels
        for y in range(32):
            for x in range(64):
                if self.chip8.display[y][x]:
                    x1 = x * 10
                    y1 = y * 10
                    x2 = x1 + 10
                    y2 = y1 + 10
                    self.canvas.create_rectangle(x1, y1, x2, y2, fill='white', outline='')
        self.after(16, self.update_display)  # ~60fps

    def update_emulation(self):
        """run emulation cycles"""
        if self.running and not self.paused:
            for _ in range(self.cycle_speed):
                self.chip8.emulate_cycle()
            self.chip8.update_timers()
        self.after(16, self.update_emulation)  # 60 Hz

def main():
    app = ACEmu()
    app.mainloop()

if __name__ == "__main__":
    main()
