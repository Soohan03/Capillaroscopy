import tkinter as tk
from tkinter import messagebox

import numpy as np

from Caper import VideoStabilization,VideoStabilizationMultiple,FlowVideo,FlowVideoMultiple
from Utilities import list_videos,video_stem


class Process_Frame(tk.Frame):
    """'Processing ...' window running the option picked in a video's popup.

    Handles delete, stabilize and flow, plus the 'all videos' variants; the
    job advances one step per update() call from the main loop.
    """
    def __init__(self, master, url,command,tab,previously_selected_tab,*args, **kwargs):
        self.previously_selected_tab = previously_selected_tab
        super().__init__()
        self.tab = tab
        self.master = master
        self.url = url
        self.command = command

        self.top= tk.Toplevel()

        self.width = 220
        self.height_of_button = 20
        self.height=self.height_of_button*7

        self.master.options=None
        self.master.url=url

        self.iteration = 0
        self.process=None

        self.canvas = tk.Canvas(self.top,width=self.width,height=self.height,bg=self.master.color_hex,borderwidth=0,highlightthickness=0)

        factor = 0.10

        self.top.wm_title('Processing ...')
        self.information_label = tk.Label(self.canvas,text='',borderwidth=0,bg=self.master.color_hex)
        self.canvas.create_window(int((self.width/2)-4.5*((self.width*factor))),self.height_of_button,anchor=tk.NW,window=self.information_label)

        x = self.master.winfo_x()
        y = self.master.winfo_y()
        w = self.width
        h = self.height
        dx=int(self.master.width*0.7)
        dy = int(self.master.height*0.2)
        self.top.geometry("%dx%d+%d+%d" % (w,h,x + dx,y + dy))

        self._pack()

        if self.command=='delete':
            self.tab.participant_list.delete_video(self.url)

        if self.command=='stabilize':
            self.process = VideoStabilization(path=self.url)

        if self.command=='stabilize_all':
            self.process = VideoStabilizationMultiple(paths=self.recorded_videos_not_yet_stabilized())

        if self.command=='flow':
            if self.url.find('StabilizedVideos') != -1:
                self.process = FlowVideo(path=self.url)
            else:
                self.process = None
                messagebox.showerror("Error","Video needs to be stabilized first")

        if self.command=='flow_all':
            stabilized_items = list_videos(self.master.stabilized_video_directory_path)
            flow_items = list_videos(self.master.flows_directory_path)
            a = [video_stem(item) for item in stabilized_items]
            b = [video_stem(item) for item in flow_items]
            items_to_flow_process = np.array(stabilized_items)[np.invert(np.isin(a,b))]

            self.process = FlowVideoMultiple(paths=items_to_flow_process)

        self.top.protocol('WM_DELETE_WINDOW',self.on_closing)

    def _unpack(self):
        self.canvas.pack_forget()

    def _pack(self):
        self.canvas.pack()

    def _destroy(self):
        self.canvas.destroy()

    #handles clicking close button
    def on_closing(self):
        self.process = None

    def recorded_videos_not_yet_stabilized(self):
        recorded_items = list_videos(self.master.recorded_video_directory_path)
        stabilized_items = list_videos(self.master.recorded_video_directory_path.replace('RecordedVideos','StabilizedVideos'))
        a = [video_stem(item) for item in recorded_items]
        b = [video_stem(item) for item in stabilized_items]
        return np.array(recorded_items)[np.invert(np.isin(a,b))]

    def update(self):
        if self.process is None:
            self.master.selected_tab = self.previously_selected_tab
            self._unpack()
            self._destroy()
            self.top.destroy()
            self.destroy()

        else:
            self.iteration+=1

            self.process.update()
            try:
                self.information_label.config(text=str(self.iteration))
            except:
                pass

            if self.process.current_stage == 'finished':
                self.process = None
                self.master.options = None
