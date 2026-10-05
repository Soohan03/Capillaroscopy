import tkinter as tk
from tkinter import messagebox


class Save_Data_Popup(tk.Frame):
    """Asks for the name of the data set about to be saved (master.save_report_name)."""
    def __init__(self, master,*args, **kwargs):
        super().__init__()
        self.master = master
        self.top= tk.Toplevel()

        self.width = 220
        self.height_of_button = 20
        self.height=self.height_of_button*7

        self.master.options=None

        self.canvas = tk.Canvas(self.top,width=self.width,height=self.height,bg=self.master.color_hex,borderwidth=0,highlightthickness=0)

        factor = 0.10

        self.top.wm_title('Save report')
        self.input1 = tk.Label(self.canvas,text="Report name: ")
        self.entry1 = tk.Entry(self.canvas,text="your_report.csv")
        self.btn1 = tk.Button(self.canvas, text='Save',bg=self.master.color_hex,borderwidth=0,highlightthickness=0,width=int(self.width*factor),command=self._save)

        x = self.master.winfo_x()
        y = self.master.winfo_y()
        w = self.width
        h = self.height
        dx=int(self.master.width*0.7)
        dy = int(self.master.height*0.2)
        self.top.geometry("%dx%d+%d+%d" % (w,h,x + dx,y + dy))

        self.master.protocol('WM_DELETE_WINDOW',self.on_closing)

        self._pack()

    def _save(self):
        self.master.save_report_name = self.entry1.get()

        try:
            self.master.save_report_name.encode('ascii')
        except:
            messagebox.showerror("Error","The file was not saved, save again using only English characters in the name.")

        if (' ' in self.master.save_report_name):
            messagebox.showerror("Error","The file was not saved, save again without using spaces in the name.")

        self._unpack()
        self._destroy()
        self.top.destroy()

    def _unpack(self):
        self.input1.pack_forget()
        self.entry1.pack_forget()
        self.btn1.pack_forget()
        self.canvas.pack_forget()

    def _pack(self):
        self.input1.pack()
        self.entry1.pack()
        self.btn1.pack()
        self.canvas.pack()

    def _destroy(self):
        self.canvas.destroy()

    #handles clicking close button
    def on_closing(self):
        self._unpack()
        self._destroy()
        self.top.destroy()
