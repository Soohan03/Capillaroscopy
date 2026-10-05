import tkinter as tk

from FrameClasses import VideoFrame,ParticipantList


class Analyze_Frame(tk.Frame):
    """Analyze tab: the video list on the right, the selected video with its two ROI boxes."""
    def __init__(self, master, *args, **kwargs):
        super(Analyze_Frame,self).__init__()
        self.master = master
        self.master.configure(bg=self.master.color_hex)

        self.participant_list = ParticipantList(self.master,path=self.master.recorded_video_directory_path)
        if self.master.selected_item is not None:
            self.video_frame = VideoFrame(self.master,path=self.master.selected_item)
        else:
            self.video_frame = None

        self.master.previously_selected_item = ''
        self._pack()
        self.update()

    def _unpack(self):
        self.participant_list._unpack()
        if self.video_frame is not None:
            self.video_frame._unpack()

    def _pack(self):
        self.participant_list._pack()
        if self.video_frame is not None:
            self.video_frame._pack()

    def _destroy(self):
        self.participant_list._destroy()
        if self.video_frame is not None:
            self.video_frame._destroy()

    def update(self):
        if self.master.selected_item != None:
            if self.master.selected_item!=self.master.previously_selected_item:
                if self.video_frame is not None:
                    self.video_frame.set_video(self.master.selected_item)
                else:
                    self.video_frame = VideoFrame(self.master,path=self.master.selected_item)
                    self.video_frame._pack()
                self.master.previously_selected_item=self.master.selected_item
                self.video_frame.update(force=True)

        if self.video_frame is not None:
            self.video_frame.update()
