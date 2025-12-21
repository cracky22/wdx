# minimap.py
import tkinter as tk

class Minimap:
    def __init__(self, parent_frame, project_window):
        self.parent = parent_frame          # main_frame (für place)
        self.pw = project_window            # Zugriff auf canvas, source_frames, etc.
        self.minimap_canvas = None
        self.viewport_rect_id = None

    def create(self):
        self.minimap_canvas = tk.Canvas(
            self.parent,
            width=200,
            height=150,
            bg="#f5f7fa",
            highlightthickness=1,
            highlightbackground="#cccccc"
        )
        self.minimap_canvas.place(relx=1.0, rely=1.0, x=-70, y=-70, anchor="se")

        # Klick und Drag für Navigation
        self.minimap_canvas.bind("<ButtonPress-1>", self.on_press)
        self.minimap_canvas.bind("<B1-Motion>", self.on_drag)

    def on_press(self, event):
        self.on_drag(event)

    def on_drag(self, event):
        if not self.minimap_canvas:
            return
        bbox = self.pw.canvas.bbox("all")
        if not bbox:
            return
        x1, y1, x2, y2 = bbox
        w = x2 - x1
        h = y2 - y1
        if w <= 0 or h <= 0:
            return

        # Zielkoordinate im Hauptcanvas
        target_x = x1 + (event.x / 200) * w
        target_y = y1 + (event.y / 150) * h

        # Viewport zentrieren
        view_w = self.pw.canvas.winfo_width()
        view_h = self.pw.canvas.winfo_height()
        self.pw.canvas.xview_moveto((target_x - view_w / 2) / w)
        self.pw.canvas.yview_moveto((target_y - view_h / 2) / h)

    def update(self):
        if not self.minimap_canvas:
            return
        self.minimap_canvas.delete("all")

        bbox = self.pw.canvas.bbox("all")
        if not bbox:
            return
        x1, y1, x2, y2 = bbox
        w = x2 - x1
        h = y2 - y1
        if w <= 0 or h <= 0:
            return

        # Karten zeichnen
        for item_id, (frame, canvas_id) in self.pw.source_frames.items():
            coords = self.pw.canvas.coords(canvas_id)
            if not coords:
                continue
            cx, cy = coords
            cw = frame.winfo_width()
            ch = frame.winfo_height()

            # Auf Minimap skalieren
            mx = (cx - x1) / w * 200
            my = (cy - y1) / h * 150
            mw = cw / w * 200
            mh = ch / h * 150

            # Farbe vom Frame (über Style)
            try:
                style = frame.cget("style")
                color = self.pw.root.style.lookup(style, "background")
            except:
                color = "#ffffff"

            self.minimap_canvas.create_rectangle(
                mx, my, mx + mw, my + mh,
                fill=color, outline="#aaaaaa", width=1
            )

        # Viewport-Rahmen (aktuell sichtbarer Bereich)
        vx1 = self.pw.canvas.canvasx(0)
        vy1 = self.pw.canvas.canvasy(0)
        vx2 = vx1 + self.pw.canvas.winfo_width()
        vy2 = vy1 + self.pw.canvas.winfo_height()

        mx1 = (vx1 - x1) / w * 200
        my1 = (vy1 - y1) / h * 150
        mx2 = (vx2 - x1) / w * 200
        my2 = (vy2 - y1) / h * 150

        if self.viewport_rect_id:
            self.minimap_canvas.delete(self.viewport_rect_id)

        self.viewport_rect_id = self.minimap_canvas.create_rectangle(
            mx1, my1, mx2, my2,
            outline="red", width=2, fill="", dash=(4, 4)
        )