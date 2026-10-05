import tkinter as tk

from FrameClasses import ParticipantList,FlowFrame


class Flow_Frame(tk.Frame):
    """Flow tab: the list of flow videos in Flows/ and the selected one with its drag-selected region."""
    def __init__(self, master, *args, **kwargs):
        super(Flow_Frame,self).__init__()
        self.master = master
        self.master.configure(bg=self.master.color_hex)

        self.participant_list = ParticipantList(self.master,path=self.master.flows_directory_path)
        self.empty_label = None
        if self.master.selected_item is not None:
            self.video_frame = FlowFrame(self.master,path=self.master.selected_item)
        else:
            self.video_frame = None
            self.empty_label = tk.Label(self.master,
                                        text='No flow videos found in Flows/.\n\n'
                                             'Generate one first: open a stabilized video in the video list\n'
                                             'and choose "Calculate flow" from its options menu.',
                                        bg=self.master.color_hex,font=self.master.font,justify=tk.CENTER)

        self._pack()
        self.update()

    def _unpack(self):
        self.participant_list._unpack()
        if self.video_frame is not None:
            self.video_frame._unpack()
        if self.empty_label is not None:
            self.empty_label.pack_forget()

    def _pack(self):
        self.participant_list._pack()
        if self.video_frame is not None:
            self.video_frame._pack()
        if self.empty_label is not None:
            self.empty_label.pack(expand=True)

    def _destroy(self):
        self.participant_list._destroy()
        if self.video_frame is not None:
            self.video_frame._destroy()
        if self.empty_label is not None:
            self.empty_label.destroy()

    def update(self):
        if self.master.selected_item != None:
            if self.master.selected_item!=self.master.previously_selected_item:
                if self.video_frame is not None:
                    self.video_frame.set_video(self.master.selected_item)
                else:
                    if self.empty_label is not None:
                        self.empty_label.pack_forget()
                        self.empty_label = None
                    self.video_frame = FlowFrame(self.master,path=self.master.selected_item)
                    self.video_frame._pack()
                self.master.previously_selected_item=self.master.selected_item
                self.video_frame.update(force=True)

        if self.video_frame is not None:
            self.video_frame.update()
