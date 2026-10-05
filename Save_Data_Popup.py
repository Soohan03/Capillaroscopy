
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



class Save_Data_Popup(tk.Frame):
    def __init__(self, master,*args, **kwargs):
        #super(Popup_Frame,self).__init__()
        super().__init__()
        self.master = master
        self.top= tk.Toplevel()
        # self.main_frame=self.master.master_canvas
        #self.frame = tk.Frame(self.top,width=300,height=100,bg=self.master.color_hex,
        #                        borderwidth=0,highlightthickness=0)

        self.width = 220
        self.height_of_button = 20
        self.height=self.height_of_button*7

        self.master.options=None
        #self.master.url=url


        self.canvas = tk.Canvas(self.top,width=self.width,height=self.height,bg=self.master.color_hex,borderwidth=0,highlightthickness=0)


        factor = 0.10

        self.top.wm_title('Save report')
        self.input1 = tk.Label(self.canvas,text="Report name: ")
        self.entry1 = tk.Entry(self.canvas,text="your_report.csv")
        #
        self.btn1 = tk.Button(self.canvas, text='Save',bg=self.master.color_hex,borderwidth=0,highlightthickness=0,width=int(self.width*factor),command=self.cmd1)
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
        self.master.save_report_name = self.entry1.get()

        try:
            self.master.save_report_name.encode('ascii')
        except:
            tk.messagebox.showerror("Error","The file was not saved, save again using only English characters in the name.")

        if (' ' in self.master.save_report_name):
            tk.messagebox.showerror("Error","The file was not saved, save again without using spaces in the name.")



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
        # self.btn1.pack_forget()
        # self.btn2.pack_forget()
        # self.btn3.pack_forget()
        # self.btn1.place_forget()
        # self.btn2.place_forget()
        # self.btn3.place_forget()
        self.input1.pack_forget()
        self.entry1.pack_forget()
        self.btn1.pack_forget()
        self.canvas.pack_forget()
        # self.frame.pack_forget()
        # self.matplotlib_frame._unpack()
        # self.main_frame.pack_forget()

    def _pack(self):
        # self.btn1.pack(anchor=tk.CENTER)
        # self.btn2.pack(anchor=tk.CENTER)
        # self.btn3.pack(anchor=tk.CENTER)
        # self.frame.pack()
        self.input1.pack()
        self.entry1.pack()
        self.btn1.pack()
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