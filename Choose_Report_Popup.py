import tkinter as tk
from tkinter import messagebox


class Choose_Report_Popup(tk.Frame):
    """Lists the saved data sets of the current video.

    The selected name is stored in master.chosen_report_to_generate.
    """
    def __init__(self, master,list_of_reports,*args, **kwargs):
        super().__init__()
        self.master = master
        self.top= tk.Toplevel()

        self.width = 220
        self.height_of_button = 20
        self.height=self.height_of_button*10

        self.master.options=None

        self.canvas = tk.Canvas(self.top,width=self.width,height=self.height,bg=self.master.color_hex,borderwidth=0,highlightthickness=0)

        factor = 0.10

        self.top.wm_title('Choose report')

        self.listbox1 = tk.Listbox(self.canvas)

        for item in list_of_reports:
            self.listbox1.insert(tk.END, item)

        self.btn1 = tk.Button(self.canvas,text='OK',bg=self.master.color_hex,borderwidth=0,highlightthickness=0,
                              width=int(self.width * factor),command=self._ok)

        x = self.master.winfo_x()
        y = self.master.winfo_y()
        w = self.width
        h = self.height
        dx=int(self.master.width*0.7)
        dy = int(self.master.height*0.2)
        self.top.geometry("%dx%d+%d+%d" % (w,h,x + dx,y + dy))

        self.master.protocol('WM_DELETE_WINDOW',self.on_closing)

        self._pack()

    def _ok(self):

        try:
            # get selected line index
            index = self.listbox1.curselection()
            # get the line's text
            self.master.chosen_report_to_generate = self.listbox1.get(index)

        except:
            messagebox.showerror("Error","You did not select an item, try again")

        self._unpack()
        self._destroy()
        self.top.destroy()

    def _unpack(self):
        self.listbox1.pack_forget()
        self.btn1.pack_forget()
        self.canvas.pack_forget()

    def _pack(self):
        self.listbox1.pack(side='top')
        self.btn1.pack(side='bottom')
        self.canvas.pack()

    def _destroy(self):
        self.canvas.destroy()

    #handles clicking close button
    def on_closing(self):
        self._unpack()
        self._destroy()
        self.top.destroy()
