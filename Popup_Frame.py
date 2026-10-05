import tkinter as tk


class Popup_Frame(tk.Frame):
    """Options window for one video in the list.

    The chosen option is handed to Application through master.options and
    then run by Process_Frame.
    """
    OPTIONS = (('Delete','delete'),
               ('Stabilize','stabilize'),
               ('Stabilize all videos','stabilize_all'),
               ('Calculate flow','flow'),
               ('Calculate flow for all','flow_all'))

    def __init__(self, master, url,*args, **kwargs):
        super().__init__()
        self.master = master
        self.top= tk.Toplevel()

        self.width = 220
        self.height_of_button = 20
        self.height=self.height_of_button*7

        self.master.options=None
        self.master.url=url

        self.canvas = tk.Canvas(self.top,width=self.width,height=self.height,bg=self.master.color_hex,borderwidth=0,highlightthickness=0)

        factor = 0.10

        self.top.wm_title('Options')
        for row,(text,option) in enumerate(self.OPTIONS,start=1):
            button = tk.Button(self.canvas,text=text,bg=self.master.color_hex,borderwidth=0,highlightthickness=0,
                               width=int(self.width*factor),command=lambda option=option: self.choose(option))
            self.canvas.create_window(int((self.width/2)-4.5*((self.width*factor))),self.height_of_button*row,anchor=tk.NW,window=button)

        x = self.master.winfo_x()
        y = self.master.winfo_y()
        w = self.width
        h = self.height
        dx=int(self.master.width*0.7)
        dy = int(self.master.height*0.2)
        self.top.geometry("%dx%d+%d+%d" % (w,h,x + dx,y + dy))

        self.master.protocol('WM_DELETE_WINDOW',self.on_closing)

        self._pack()

    def choose(self,option):
        self.master.options=option
        self._unpack()
        self._destroy()
        self.top.destroy()

    def _unpack(self):
        self.canvas.pack_forget()

    def _pack(self):
        self.canvas.pack()

    def _destroy(self):
        self.canvas.destroy()

    #handles clicking close button
    def on_closing(self):
        self._unpack()
        self._destroy()
        self.top.destroy()
