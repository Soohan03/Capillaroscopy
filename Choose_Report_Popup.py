
import sys
if "Tkinter" not in sys.modules:
    import tkinter as tk
import numpy as np
import pickle
from PIL import ImageTk,Image
import cv2
import time
import datetime
from Utilities import *
import sys
from webcolors import rgb_to_hex
from tkinter import ttk as ttk



class Choose_Report_Popup(tk.Frame):
    def __init__(self, master,list_of_reports,*args, **kwargs):
        #super(Popup_Frame,self).__init__()
        super().__init__()
        self.master = master
        self.top= tk.Toplevel()
        # self.main_frame=self.master.master_canvas
        #self.frame = tk.Frame(self.top,width=300,height=100,bg=self.master.color_hex,
        #                        borderwidth=0,highlightthickness=0)

        self.width = 220
        self.height_of_button = 20
        self.height=self.height_of_button*10

        self.master.options=None
        #self.master.url=url


        self.canvas = tk.Canvas(self.top,width=self.width,height=self.height,bg=self.master.color_hex,borderwidth=0,highlightthickness=0)


        factor = 0.10

        self.top.wm_title('Choose report')


        self.listbox1 = tk.Listbox(self.canvas) #,width=int(self.width*0.4),height=int(self.height*0.4)
        self.vsb = tk.Scrollbar(orient="vertical",command=self.listbox1.yview,bg=self.master.color_hex,borderwidth=0,
                                highlightthickness=0)
        self.listbox1.configure(yscrollcommand=self.vsb.set)

        for item in list_of_reports:
            self.listbox1.insert(tk.END, item)

        self.btn1 = tk.Button(self.canvas,text='OK',bg=self.master.color_hex,borderwidth=0,highlightthickness=0,
                              width=int(self.width * factor),command=self.cmd1)

        #self.entry1 = tk.Entry(self.canvas,text="your_report.csv")
        #
        #self.btn1 = tk.Button(self.canvas, text='Save',bg=self.master.color_hex,borderwidth=0,highlightthickness=0,width=int(self.width*factor),command=self.cmd1)
        # self.btn2 = tk.Button(self.canvas, text='Stabilize',bg=self.master.color_hex,borderwidth=0,highlightthickness=0,width=int(self.width*factor),command=self.cmd2)
        # self.btn3 = tk.Button(self.canvas,text='Stabilize all videos',bg=self.master.color_hex,borderwidth=0,highlightthickness=0,width=int(self.width*factor),command=self.cmd3)
        # self.btn4 = tk.Button(self.canvas, text='Calculate flow',bg=self.master.color_hex,borderwidth=0,highlightthickness=0,width=int(self.width*factor),command=self.cmd4)
        # self.btn5 = tk.Button(self.canvas,text='Calculate flow for all',bg=self.master.color_hex,borderwidth=0,highlightthickness=0,width=int(self.width*factor),command=self.cmd5)

        #
        #self.window1= self.canvas.create_window(int((self.width/2)-4.5*((self.width*factor))),self.height_of_button,anchor=tk.NW,window=self.input1)
        #self.window2 = self.canvas.create_window(int((self.width/2)-4.5*((self.width*factor))),self.height_of_button*2,anchor=tk.NW,window=self.input2)
        # self.window3= self.canvas.create_window(int((self.width/2)-4.5*((self.width*factor))),self.height_of_button*3,anchor=tk.NW,window=self.btn3)
        # self.window4 = self.canvas.create_window(int((self.width / 2) - 4.5 * ((self.width *factor))),self.height_of_button * 4,anchor=tk.NW,window=self.btn4)
        #self.window5 = self.canvas.create_window(int((self.width / 2) - 4.5 * ((self.width*factor))),self.height_of_button * 5,anchor=tk.NW,window=self.btn1)

        x = self.master.winfo_x()
        y = self.master.winfo_y()
        w = self.width
        h = self.height
        dx=int(self.master.width*0.7)
        dy = int(self.master.height*0.2)
        self.top.geometry("%dx%d+%d+%d" % (w,h,x + dx,y + dy))

        self.master.protocol('WM_DELETE_WINDOW',self.on_closing)

        self._pack()

    def cmd1(self):

        try:
            # get selected line index
            index = self.listbox1.curselection()
            # get the line's text
            self.master.chosen_report_to_generate = self.listbox1.get(index)


        except:
            tk.messagebox.showerror("Error","You did not select an item, try again")

        self._unpack()
        self._destroy()
        self.top.destroy()
    def cmd2(self):
        self.master.options='stabilize'
        self._unpack()
        self._destroy()
        self.top.destroy()
    def cmd3(self):
        self.master.options='stabilize_all'
        self._unpack()
        self._destroy()
        self.top.destroy()
    def cmd4(self):
        self.master.options='flow'
        self._unpack()
        self._destroy()
        self.top.destroy()
    def cmd5(self):
        self.master.options='flow_all'
        self._unpack()
        self._destroy()
        self.top.destroy()

    def _resize(self,event=None):
        pass


    def _unpack(self):

        # self.btn2.pack_forget()
        # self.btn3.pack_forget()
        # self.btn1.place_forget()
        # self.btn2.place_forget()
        # self.btn3.place_forget()
        self.listbox1.pack_forget()
        self.btn1.pack_forget()
        self.canvas.pack_forget()
        # self.frame.pack_forget()
        # self.matplotlib_frame._unpack()
        # self.main_frame.pack_forget()

    def _pack(self):

        # self.btn2.pack(anchor=tk.CENTER)
        # self.btn3.pack(anchor=tk.CENTER)
        # self.frame.pack()
        self.listbox1.pack(side='top')
        self.btn1.pack(side='bottom')
        self.canvas.pack()
        # self.btn1.pack(side='top')
        # self.btn2.pack(side='top')
        # self.btn3.pack(side='top')
        # self.btn1.place(x=int(self.width/2-((self.width/30)/2)),y=self.height_of_button)
        # self.btn2.place(x=int(self.width/2-((self.width/30))),y=self.height_of_button*2)
        # self.btn3.place(x=150,y=self.height_of_button*3)

        # self.canvas.pack(fill=tk.BOTH,expand=1)
        # self.matplotlib_frame._pack()
        # self.main_frame.pack()

    def _destroy(self):
        # self.btn1.destroy()
        # self.btn2.destroy()
        # self.btn3.destroy()
        self.canvas.destroy()

    #handles clicking close button
    def on_closing(self):
        self._unpack()
        self._destroy()
        self.top.destroy()