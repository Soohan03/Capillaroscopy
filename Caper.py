import cv2
import numpy as np
from Utilities import *
import tkinter as tk
from PIL import ImageTk,Image
import datetime
import glob


from sys import platform

if platform == 'win32':
    import skvideo
    skvideo.setFFmpegPath(r'ffmpeg\ffmpeg-20191226-b0d0d7e-win64-shared\bin')
    skvideo.setFFmpegPath(r'ffmpeg\ffmpeg-20191226-b0d0d7e-win64-shared\bin')
    skvideo.setFFmpegPath(r'ffmpeg\ffmpeg-20191226-b0d0d7e-win64-shared\bin')
import skvideo.io as io

import SingleStepDFT as DFT
import pandas as pd
import cv2
import os
import matplotlib.pyplot as plt
import seaborn as sns

import cv2
import numpy as np
import datetime
from ProgressMonitor import ProgressMonitor
import os
from skimage import data
from skimage.filters import threshold_multiotsu

# The measurement itself lives in the GUI-free `capillary` package so that the
# Analyze tab, the batch CLI and the unit tests all run the same arithmetic.
from capillary.roi import ROI
from capillary.velocity import lag_and_correlation

class VideoCamera:
    def __init__(self,directory):
        self.cap = cv2.VideoCapture(0)
        self.width_ = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640.0
        self.height_ = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480.0
        self.fps_ = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.resolution_ = int(self.width_*self.height_)
        self.aspect_ratio_ = self.height_/self.width_

        self.path = str(datetime.datetime.now().strftime('%m-%d-%Y_%H-%M-%S-%f'))+'.avi'
        self.directory = directory
        self.outputfile = os.path.join(self.directory,self.path)
        self.writer = None

    def get_frame(self):
        (grabbed,frame) = self.cap.read()
        if not grabbed or frame is None:
            return np.zeros((int(self.height_),int(self.width_),3),dtype=np.uint8)
        return frame[:,:,::-1]

    def destroy_capture(self):
        self.cap.release()

    def destroy_writer(self):
        self.writer.release()

    def reopen(self):
        self.cap.open(0)

    def save_frame(self,frame):
        if self.writer is None:
            self.writer = cv2.VideoWriter(self.outputfile,cv2.VideoWriter_fourcc(*'MP4V'),30.0,(640,480))
        frame = rgb_to_negR_posG(frame)
        frame = cv2.merge((frame,frame,frame))
        self.writer.write(frame.astype(np.uint8))


        #videowriter
        #https: // gist.github.com / docPhil99 / a612c355cd31e69a0d3a6d2f87bfde8b





class Video:
    #this class will can be given to a videoplayer object that is integrated with TKinter Canvas
    def __init__(self,path=''):
        # do super of identification class
        # path can arrive as None when no video is selected (e.g. empty Flows/);
        # keep it a string so path manipulation below doesn't crash.
        self.path = path if path is not None else ''
        self.number_of_frames_ = 0
        self.fps_ = 30
        self.resolution_ = None
        self.height_ = None
        self.width_ = None
        self.frames_ = []
        self.frames_processed_ = []
        self.blur_vector = []
        self.thumbnail_ = None
        self.cap = cv2.VideoCapture()
        self.cap_open=False
        self.writer = None
        self.blur_vector = []
        self.test_frame_number=0
        self.pause=0
        self.finished = False
        self.frame = None

        self.output_path = self.path.replace('RecordedVideos','StabilizedVideos')



    def generate_thumbnail(self,video_is_stabilised=False,video_has_been_analysed=False,factor=0.15):
        # downscale the sharpest image in the video
        # max_blur_index = np.argmax(self.blur_vector)

        self.cap.open(self.path)
        self.number_of_frames_ = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps_ = int(self.cap.get(cv2.CAP_PROP_FPS)) or 30 #fall back to the recorder's rate when the file reports none
        self.width_=int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height_=int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.resolution_ = int(self.width_*self.height_)

        #self.set_frame(10)
        frame =self.get_frame()
        try: #easier to do this than to create a new class for flow lists
            # frame = cv2.bitwise_and(frame,frame,mask=self.mask)
            frame = cv2.cvtColor(frame,cv2.COLOR_HSV2BGR)
        except:
            pass
        thumbnail = cv2.resize(frame,None,fx=factor,fy=factor)


        if video_is_stabilised:
            #https://stackoverflow.com/questions/40895785/using-opencv-to-overlay-transparent-image-onto-another-image
            #add a indicator in image
            pass
        if video_has_been_analysed:
            #add a indicator in image
            pass
        self.thumbnail_= thumbnail

    def destroy_writer(self):
        self.writer.release()

    def save_frame(self,frame):
        if self.writer is None:
            self.writer = cv2.VideoWriter(self.output_path,cv2.VideoWriter_fourcc(*'MP4V'),30.0,(640,480))

        self.writer.write(cv2.merge((frame,frame,frame)).astype(np.uint8))


        #videowriter
        #https: // gist.github.com / docPhil99 / a612c355cd31e69a0d3a6d2f87bfde8b


    # def save_frame(self,path=''):
    #     #videowriter
    #     #https: // gist.github.com / docPhil99 / a612c355cd31e69a0d3a6d2f87bfde8b
    #     pass

    def load(self,max_frames=None):
        #only for BW right now

        #for debugging, want everything to go fast so only look at a few frames


        self.cap.open(self.path)

        if max_frames == None:
            self.number_of_frames_ = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        else:
            self.number_of_frames_ = max_frames

        self.fps_ = int(self.cap.get(cv2.CAP_PROP_FPS)) or 30 #fall back to the recorder's rate when the file reports none
        self.width_=int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height_=int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.resolution_ = int(self.width_*self.height_)
        self.aspect_ratio_ = self.height_/self.width_
        self.frames_ = np.zeros([self.number_of_frames_,self.height_,self.width_])
        self.frames_processed_ = np.zeros([self.number_of_frames_,self.height_,self.width_])
        self.blur_vector = np.zeros([self.number_of_frames_])
        self.pause = 0
        # print(self.number_of_frames_)

        # while cap.isOpened():
        for index_frame in range(self.number_of_frames_):
            self.frames_[index_frame,:,:] = self.cap.read()[1][:,:,0]
            self.blur_vector[index_frame] = calculate_blur(self.frames_[index_frame,:,:])
            try:
                self.progress_load.update_progress(index_frame/self.number_of_frames_)
            except:
                pass


    def get_frame(self,return_frame=1):

        #if self.cap.isOpened(): #fix this, so something happens when video is finished.
        if self.cap_open == False:
            self.cap.open(self.path)
            self.number_of_frames_ = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps_ = int(self.cap.get(cv2.CAP_PROP_FPS)) or 30 #fall back to the recorder's rate when the file reports none
            self.width_ = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height_ = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.resolution_ = int(self.width_ * self.height_)
            self.aspect_ratio_ = self.height_/self.width_
            self.blur_vector = np.zeros([self.number_of_frames_])
            self.pause = 0
            self.cap_open=True
            self.stabilization_vector = np.zeros([self.number_of_frames_,2]) #not used

            self.frame_number = self.get_frame_number()
            current_frame = self.cap.read()[1][:,:,0]
            #self.blur_vector[self.frame_number] = calculate_blur(current_frame)
            return current_frame
        else:
            if self.get_frame_number() < self.number_of_frames_-1:
                self.frame_number = self.get_frame_number()
                try:
                    current_frame = self.cap.read()[1][:,:,0]
                except:
                    print(self.cap.isOpened())
                    current_frame = self.cap.read()[1][:,:,0]
                self.blur_vector[self.frame_number] = calculate_blur(current_frame)
                self.frame = current_frame
                return current_frame
            else:
                self.finished = True
                return self.frame



    def set_frame(self,frame_number):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES,frame_number)
        self.finished = False

    def get_frame_number(self):
        # print(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
        # print(self.test_frame_number)
        return int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))-1

    def go_back_or_forward_n_frames(self,n):

        frame_number = self.get_frame_number()
        if (frame_number+n) > self.number_of_frames_ or (frame_number+n)<0:
            pass
        else:
            self.set_frame(frame_number+n)


class FlowVideo(Video):
    def __init__(self,path):
        Video.__init__(self,path=path)
        self.video_path = path
        self.video = Video(self.video_path)
        self.output_path = path.replace('StabilizedVideos','Flows')
        self.video.get_frame()
        self.p_m = ProgressMonitor()
        self.video.get_frame()
        self.video.set_frame(0)
        self.previous_frame = self.video.get_frame()
        self.frame = cv2.merge((self.previous_frame,self.previous_frame,self.previous_frame))
        self.average = np.zeros_like(self.previous_frame).astype(np.float64)
        self.average_flow = np.zeros_like(self.previous_frame).astype(np.float64)
        self.current_stage = 'processing'

    def _close(self):
        self.destroy_writer()

    def update(self):

        fr_num = self.video.get_frame_number()
        # print(fr_num,self.video.number_of_frames_,self.video.get_frame_number())
        if fr_num < self.video.number_of_frames_ - 1:
            # print('<')
            fr = self.video.get_frame()
            self.average += fr
            flow = cv2.calcOpticalFlowFarneback(self.previous_frame,fr,None,0.5,6,7,7,5,1.2,0)
            self.previous_frame = fr
            mag,ang = cv2.cartToPolar(flow[...,0],flow[...,1])

            # display_flow(mag, ang)
            temp = np.zeros_like(self.frame)
            temp[...,1] = 255
            temp[...,0] = ang * 180 / np.pi / 2

            mag[mag > 10] = 0  # very few values are higher than 10, most are 0.5 or similar, some are up to 5
            mag = mag * 25.5
            self.average_flow += mag.astype(np.float64)
            temp[...,2] = mag

            self.save_frame(temp)
            self.p_m.update_progress(self.video.get_frame_number() / self.video.number_of_frames_)

            if self.video.get_frame_number() % 20 == 0 and fr_num > 20:
                self.create_pickle()
                # print('pickle')
                # print(str(fr_num),' of '+str(self.video.number_of_frames_))
        else:
            # print('>')
            fr_num += 1
            self.create_pickle()
            self._close()
            self.current_stage = 'finished'

    def save_frame(self,frame):
        if self.writer is None:
            self.writer = cv2.VideoWriter(self.output_path,cv2.VideoWriter_fourcc(*'MP4V'),30.0,(640,480))

        self.writer.write(frame.astype(np.uint8))

    def create_pickle(self):
        average_flow_ = (self.average_flow / (self.video.get_frame_number() - 1)).astype(np.uint8)
        average_ = (self.average / (self.video.get_frame_number() - 1)).astype(np.uint8)

        thresholds = threshold_multiotsu(average_flow_[75:350,100:450],classes=2)
        regions2 = np.digitize(average_flow_,bins=thresholds)
        thresholds = threshold_multiotsu(average_[75:350,100:450],classes=3)
        regions1 = np.digitize(average_,bins=[thresholds[1]])
        area = cv2.bitwise_and(regions2,1 - regions1).astype(np.uint8)
        pickle_save(cv2.merge((average_flow_,average_,area)),self.output_path[:-4] + '.pickle')


class FlowVideoMultiple:
    def __init__(self,paths):
        self.object = None
        self.current_stage = 'processing'
        self.paths = paths
        self.number_of_objects = len(self.paths)
        self.current_object = 0
        self.object = FlowVideo(path=self.paths[self.current_object])


    def update(self):

        if self.current_stage == 'processing':
            if self.object.current_stage == 'finished':
                self.current_object +=1

                if self.current_object < len(self.paths):
                    self.object = FlowVideo(path=self.paths[self.current_object])
                else:
                    self.current_stage = 'finished'
            else:
                self.object.update()
        else:
            pass




class ColorVideo(Video):
    # wrapper of class Video for videos with color
    def __init__(self,path):
        Video.__init__(self,path=path)
        self.stack = []
        self.mask = []
        self.file = pickle_load(self.path[:-4] + '.pickle')
        self.mask = self.file[:,:,2].astype(np.uint8)



    def get_frame(self,return_frame=1,rolling_average=0,return_non_average=0):

        #if self.cap.isOpened(): #fix this, so something happens when video is finished.
        if self.cap_open == False:
            self.cap.open(self.path)
            self.number_of_frames_ = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps_ = int(self.cap.get(cv2.CAP_PROP_FPS)) or 30 #fall back to the recorder's rate when the file reports none
            self.width_ = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height_ = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.resolution_ = int(self.width_ * self.height_)
            self.aspect_ratio_ = self.height_/self.width_
            self.blur_vector = np.zeros([self.number_of_frames_])
            self.pause = 0
            self.cap_open=True


            self.frame_number = self.get_frame_number()
            self.current_frame = self.cap.read()[1]
            self.stack.append(self.current_frame)

            return self.current_frame
        else:
            if self.get_frame_number() < self.number_of_frames_-1:
                self.frame_number = self.get_frame_number()
                self.current_frame = self.cap.read()[1]
                #self.blur_vector[self.frame_number] = calculate_blur(current_frame)


                if rolling_average!=0:
                    self.stack.append(self.current_frame)
                    if len(self.stack) > rolling_average:
                        self.stack.pop(0)

                    self.frame=np.mean(np.array(self.stack),axis=0)
                else:
                    self.frame = self.current_frame

                if return_non_average:
                    return self.current_frame,self.frame.astype(np.uint8)
                else:
                    return self.frame.astype(np.uint8)
            else:
                self.finished = True

                if return_non_average:
                    return self.current_frame,self.frame.astype(np.uint8)
                else:
                    return self.frame.astype(np.uint8)


    def load(self,max_frames=None):
        self.cap.open(self.path)

        if max_frames == None:
            self.number_of_frames_ = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        else:
            self.number_of_frames_ = max_frames

        self.fps_ = int(self.cap.get(cv2.CAP_PROP_FPS)) or 30 #fall back to the recorder's rate when the file reports none
        self.width_=int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height_=int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.resolution_ = int(self.width_*self.height_)
        self.aspect_ratio_ = self.height_/self.width_
        self.frames_ = np.zeros([self.number_of_frames_,self.height_,self.width_,3])
        self.pause = 0
        for index_frame in range(self.number_of_frames_):
            self.frames_[index_frame,:,:,:] = self.get_frame()
            try:
                self.progress_load.update_progress(index_frame/self.number_of_frames_)
            except:
                pass


    def set_frame(self,frame_number):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES,frame_number)
        self.finished = False
        self.stack=[]


class VideoStabilization(Video):
    #wrapper of class Video for stabiliation
    def __init__(self,path):
        Video.__init__(self,path=path)
        self.raw_stabilization_vector = None
        self.reference_frames = None
        self.number_of_reference_frames = 3
        self.usfac = 100
        self.current_stage = 'load'

        self.translation_vector = None
        self.load_index = 0
        self.progress_load = ProgressMonitor()
        self.progress_transform = ProgressMonitor()
        self.progress_stabilize = ProgressMonitor()

        self.get_frame()
        self.set_frame(0)

        self.index = 0

    def load_stabilization(self,max_frames=None,index=0,n_steps=1):
        #only for BW right now

        #for debugging, want everything to go fast so only look at a few frames

        if index > 0:
            # while cap.isOpened():
            self.frames_[index,:,:] = self.cap.read()[1][:,:,0]
            self.blur_vector[index] = calculate_blur(self.frames_[index,:,:])
            self.progress_load.update_progress(index / self.number_of_frames_)


        else:
            self.cap.open(self.path)

            if max_frames == None:
                self.number_of_frames_ = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            else:
                self.number_of_frames_ = max_frames

            self.fps_ = int(self.cap.get(cv2.CAP_PROP_FPS)) or 30 #fall back to the recorder's rate when the file reports none
            self.width_=int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height_=int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.resolution_ = int(self.width_*self.height_)
            self.aspect_ratio_ = self.height_/self.width_
            self.frames_ = np.zeros([self.number_of_frames_,self.height_,self.width_])
            self.frames_processed_ = np.zeros([self.number_of_frames_,self.height_,self.width_])
            self.blur_vector = np.zeros([self.number_of_frames_])
            self.pause = 0
            # print(self.number_of_frames_)




    def generate_reference_frames(self):
        self.reference_frames =self.frames_processed_[pd.Series(self.blur_vector).sort_values(ascending=False).index[:self.number_of_reference_frames].values] #returns sharpest images

    def stabilize_frame(self,frame,frame_number):
        # print(self.reference_frames)
        for index,reference_image in enumerate(self.reference_frames):
            self.raw_stabilization_vector[frame_number,index,:] = DFT.register_images(frame,reference_image,usfac=self.usfac)

    def stabilize_video(self,index):
        if self.raw_stabilization_vector is None:
            temp = np.empty([self.number_of_frames_,self.number_of_reference_frames,2])
            temp[:] = np.nan
            self.raw_stabilization_vector = temp #now we can know that all non nan values are calculated

        # for index,frame in enumerate(self.frames_processed_): #parallellize?
        #     self.stabilize_frame(frame,index)
        #     print(self.progress_stabilize.update_progress(index/self.number_of_frames_))

        self.stabilize_frame(self.frames_processed_[index,:,:],index)
        self.progress_stabilize.update_progress(index/self.number_of_frames_)

    def transform(self,index):

        # for index_frame in range(self.number_of_frames_):
        #     current_frame = self.frames_[index_frame,:,:]
        #     clahe_filter_current_frame =clahe(current_frame)
        #     processed_frame = median_filter(clahe_filter_current_frame)
        #     self.frames_processed_[index_frame,:,:] =processed_frame
        #     print(self.progress_transform.update_progress(index_frame/self.number_of_frames_))

        current_frame = self.frames_[index,:,:]
        clahe_filter_current_frame =clahe(current_frame)
        processed_frame = median_filter(clahe_filter_current_frame)
        self.frames_processed_[index,:,:] =processed_frame
        self.progress_transform.update_progress(index/self.number_of_frames_)

    def stabilize(self):
        self.progress_load = ProgressMonitor()
        self.load()
        self.progress_transform = ProgressMonitor()
        self.transform()
        self.generate_reference_frames()
        self.progress_stabilize = ProgressMonitor()
        self.stabilize_video()
        translation = np.mean(self.raw_stabilization_vector,axis=1)
        self.path = self.path.replace('RecordedVideos','StabilizedVideos')

        for frame in range(self.number_of_frames_):
            T = np.float32([[1,0,translation[frame,0]],[0,1,translation[frame,1]]])
            img_translation = cv2.warpAffine(self.frames_[frame,:,:],T,(self.width_,self.height_))
            self.save_frame(img_translation)
        self.destroy_writer()

        #determine ref images

        #start process of stabilizing, with robustness for termination of program, preferably continually saving images to file.

        #idea: make pickle of selected files and save in a "to stabilize" folder. Save videos frame by frame, with update pickle with which frame it was on last.
        #remove the pickle when done
        #make scheduler for this as well, which can be overwritten by user command, and all other program features. Should start by inactive timer.

    def update(self):

        if self.current_stage == 'load':
            self.load_stabilization(max_frames=None,index=self.index)
            self.index+=1
            if self.index==self.number_of_frames_:
                self.index=0
                self.current_stage = 'transform'

        if self.current_stage == 'transform':
            self.transform(index=self.index)
            self.index+=1
            if self.index==self.number_of_frames_:
                self.index=0
                self.current_stage = 'stabilize'
                self.generate_reference_frames()

        if self.current_stage == 'stabilize':
            self.stabilize_video(index=self.index)
            self.index += 1
            if self.index == self.number_of_frames_:
                self.current_stage = 'write'
                self.index=0
                # self.finished = 1

        if self.current_stage == 'write':
            if self.translation_vector is None:
                self.translation_vector = np.mean(self.raw_stabilization_vector,axis=1)
                self.path = self.path.replace('RecordedVideos','StabilizedVideos')


            T = np.float32([[1,0,self.translation_vector[self.index,0]],[0,1,self.translation_vector[self.index,1]]])
            img_translation = cv2.warpAffine(self.frames_[self.index,:,:],T,(self.width_,self.height_))
            self.save_frame(img_translation)

            self.index += 1
            if self.index == self.number_of_frames_:
                self.destroy_writer()
                self.index=0
                self.current_stage = 'finished'

        if self.current_stage == 'finished':
            pass


class VideoStabilizationMultiple:
    def __init__(self,paths):
        self.object = None
        self.current_stage = 'processing'
        self.paths = paths
        self.number_of_objects = len(self.paths)
        self.current_object = 0
        self.object = VideoStabilization(path=self.paths[self.current_object])


    def update(self):
        if self.current_stage == 'processing':
            if self.object.current_stage == 'finished':
                self.current_object +=1

                if self.current_object < len(self.paths):
                    self.object = VideoStabilization(path=self.paths[self.current_object])
                else:
                    self.current_stage = 'finished'
            else:
                self.object.update()
        else:
            pass

class Rectangle:

    def __init__(self,isForward=True):
        self.rectangle_width = 10
        self.rectangle_height = 10
        self.isForward = isForward
        self.click_x = 0
        self.click_y = 0

        if self.isForward:
            self.color = (255,255,255)
        else:
            self.color = (0,0,0)

        self.thickness = 1

        self.top_right = None
        self.top_left = None
        self.lower_right = None
        self.lower_left = None

        self.point1=(0,0)
        self.point2=(10,10)

    def set_clicks(self,x,y):
        self.click_x = x
        self.click_y = y

    def set_width_and_height(self,w,h):
        self.width = w
        self.rectangle_width=w
        self.height = h
        self.rectangle_height=h

    def get_clicks(self):
        return self.click_x,self.click_y

    def move_clicks(self,delta_x,delta_y):
        x,y = self.get_clicks()
        self.set_clicks(x+delta_x,y+delta_y)

    def calculate_corners(self,x,y):
        # Geometry delegated to capillary.roi.ROI so the boxes the GUI samples
        # and the boxes the batch CLI samples are the same boxes. self.width /
        # self.height are the frame extent here (set in draw_rectangle).
        # Corner names keep this class's original orientation, where "top" is
        # the larger y — get_selected_data slices lower_left -> top_left.
        x_start,x_stop,y_start,y_stop = ROI(
            int(x),int(y),self.rectangle_width,self.rectangle_height
        ).bounds((self.height,self.width))

        self.top_right = (x_stop,y_stop)
        self.top_left = (x_start,y_stop)
        self.lower_right = (x_stop,y_start)
        self.lower_left = (x_start,y_start)

    def calculate_corners_drag(self,point1,point2,min_size=5):
        # Normalize the two drag endpoints into an axis-aligned rectangle,
        # independent of drag direction. The previous version only worked for
        # diagonal drags: it left the left-to-right flag unset when the two x
        # (or y) coordinates were equal, which crashed on pure clicks and
        # vertical/horizontal drags. Corner naming follows image coordinates
        # (y grows downward), matching get_selected_data_for_flow/_for_mask.
        x_left,x_right = sorted((int(point1[0]),int(point2[0])))
        y_top,y_bottom = sorted((int(point1[1]),int(point2[1])))

        # guarantee a non-degenerate region so the selection is never empty
        if x_right - x_left < min_size:
            x_right = x_left + min_size
        if y_bottom - y_top < min_size:
            y_bottom = y_top + min_size

        # keep the rectangle inside the frame
        x_left = max(0,min(x_left,self.width - min_size))
        x_right = max(min_size,min(x_right,self.width))
        y_top = max(0,min(y_top,self.height - min_size))
        y_bottom = max(min_size,min(y_bottom,self.height))

        self.top_left = (x_left,y_top)
        self.top_right = (x_right,y_top)
        self.lower_left = (x_left,y_bottom)
        self.lower_right = (x_right,y_bottom)
        return True



    def draw_rectangle(self,frame,**args):
        self.frame = frame
        self.height=self.frame.shape[0]
        self.width= self.frame.shape[1]

        self.calculate_corners(self.click_x,self.click_y)

        frame = cv2.rectangle(self.frame.copy(),self.lower_left,self.top_right,self.color,self.thickness)

        return frame


    def draw_rectangle_drag(self,frame):
        self.frame = frame
        self.height=self.frame.shape[0]
        self.width= self.frame.shape[1]

        if not self.calculate_corners_drag(self.point1,self.point2):
            self.calculate_corners_drag((0,0),(10,10))

        frame = cv2.rectangle(self.frame.copy(),self.lower_left,self.top_right,self.color,self.thickness)

        return frame

    def overlay_image(self,frame,overlay):
        return frame+overlay

    def get_selected_data(self):
        return self.frame[self.lower_left[1]:self.top_left[1],self.lower_left[0]:self.lower_right[0]]  # indexed y,x

    def get_selected_data_for_flow(self,frame):
        return frame[self.top_left[1]:self.lower_left[1],self.lower_left[0]:self.lower_right[0],:]  # indexed y,x

    def get_selected_data_for_mask(self,mask):
        return mask[self.top_left[1]:self.lower_left[1],self.lower_left[0]:self.lower_right[0]]





class CrossCorrelation:
    # firstvec är 0
    # lastvec är 1

    # rect1 motsvarar firstvec
    # rect2 motsvarar lastvec

    # svart är isforward (is först)
    # rectangle1 är isforward

    # vit är not isforward (is last)
    # rectangle2 är not isforward

    # det är vid den som sist stöter på data som vi mäter hastigheten (vit)

    # vad beror fördröjning på?
    # det kan vara att när ett event precis har skett vid den vita så kommer cross correlation kolla på helheten, och det eventet kommer vara mindre viktigt än annan data.

    # blodet rör sig uppåt, så den som ser en "grej" först är den längst ner.
    # därför måste
    # 1an är först, iallafall här, vilket innebär att vi utgår ifrån 1an. 1an ger vid den tidpunkten lagget av

    def __init__(self,video,rectangle1,rectangle2,mm_per_pixel=0.001328903654):
        self.video = video
        self.rectangle_first = rectangle1
        self.rectangle_last = rectangle2

        # use the video's real frame rate; a hardcoded 30 here would bias
        # every velocity estimate for videos recorded at another rate
        self.fps = float(video.fps_) if getattr(video,'fps_',0) else 30.0

        # data first encounters new data
        self.first_vec = dict(
            zip(np.arange(0,self.video.number_of_frames_),[np.nan] * self.video.number_of_frames_))

        # data that last encounters new data
        self.last_vec = dict(
            zip(np.arange(0,self.video.number_of_frames_),[np.nan] * self.video.number_of_frames_))

        self.distance_vector= np.array([np.nan] * self.video.number_of_frames_)

        self.magnificationCoefficient = mm_per_pixel # spatial calibration, configured in settings.csv

    def check_if_enough_data_for_report(self):

        if pd.Series(self.distance_vector).notna().sum()>300:
            return True
        else:
            return False

    def calculate_distance(self,index):
        c1=self.rectangle_first.get_clicks()
        c2=self.rectangle_last.get_clicks()

        self.distance_vector[index] = distance_between_two_points(c1[1],c2[1],c1[0],c2[0])

    def set_cropped_frame_data(self,index,data_first,data_last):
        self.first_vec[index] = data_first
        self.last_vec[index] = data_last

    def get_cropped_frame_data(self,index):
        return self.first_vec[index],self.last_vec[index]

    def get_mean_intensity(self):

        ## for debugging:
        # file1 = self.first_vec
        # file2=self.last_vec
        # with open('file1.pickle','wb') as handle:
        #     pickle.dump(file1,handle,protocol=pickle.HIGHEST_PROTOCOL)
        # with open('file2.pickle','wb') as handle:
        #     pickle.dump(file2,handle,protocol=pickle.HIGHEST_PROTOCOL)

        return np.array(list(zip([[np.nanmean(self.first_vec[i]) for i in range(self.video.number_of_frames_-1) ],[np.nanmean(self.last_vec[i]) for i in range(self.video.number_of_frames_-1)]])))[:,0]

    def get_mean_intensity_in_range(self,range_start,range_end):
        return np.array(list(zip([[np.nanmean(self.first_vec[i]) for i in range(range_start,range_end) ],[np.nanmean(self.last_vec[i]) for i in range(range_start,range_end)]])))[:,0]

    def generate_report(self,path,registered_time_points):
        df = self.calculate_cross_correlation(path)
        df.to_csv(path+'___report.csv')



        path = path.replace('Statistics','Reports')

        f,ax = plt.subplots(figsize=(10,5),dpi=300)
        df.loc[:,df.columns.str.contains('velocity')].mean(axis=1).rolling(30,min_periods=1).mean().plot(ax=ax)
        plt.title('Velocity in mm/s')
        plt.ylabel('mm/s')
        plt.xlabel('Seconds')
        f.savefig(path+ 'velocity.png',dpi=f.dpi,transparent=True,bbox_inches = 'tight')

        f,ax = plt.subplots(figsize=(10,5),dpi=300)




        temp_vec = df.loc[:,df.columns.str.contains('velocity')].mean(axis=1).rolling(30,min_periods=1).mean()
        temp_vec.loc[temp_vec<0]=0
        temp_vec.plot(ax=ax)
        plt.title('Velocity in mm/s')
        plt.ylabel('mm/s')
        plt.xlabel('Seconds')
        f.savefig(path+ 'velocity_above_zero.png',dpi=f.dpi,transparent=True,bbox_inches = 'tight')



        f,ax = plt.subplots(figsize=(10,5),dpi=300)
        df.loc[:,df.columns.str.contains('correlation')].mean(axis=1).rolling(30,min_periods=1).mean().plot(ax=ax)
        plt.title('Correlation')
        plt.ylabel('Percent')
        plt.xlabel('Seconds')
        f.savefig(path+ 'correlation.png',dpi=f.dpi,transparent=True,bbox_inches = 'tight')
        #plt.show()



        f,ax = plt.subplots(figsize=(10,5),dpi=300)
        temp_vec = df.loc[:,df.columns.str.contains('velocity')].mean(axis=1).rolling(30,min_periods=1).mean()
        temp_vec.loc[temp_vec < 0] = 0
        temp_vec.plot(ax=ax,label='velocity')
        plt.title('Velocity in mm/s')
        plt.ylabel('mm/s')
        plt.xlabel('Seconds')

        t = df.loc[:,df.columns.str.contains('correlation')].mean(axis=1).rolling(30,min_periods=1).mean()
        t1 = t

        labels = ["0-25","25-50","50-75","75-100"]
        ix = [10,20,30,50]
        bins = [0,0.25,0.5,0.75,1.0]
        t1.loc[(t1.values > bins[0]) & (t1.values <= bins[1])] = ix[0]
        t1.loc[(t1.values > bins[1]) & (t1.values <= bins[2])] = ix[1]
        t1.loc[(t1.values > bins[2]) & (t1.values <= bins[3])] = ix[2]
        t1.loc[(t1.values > bins[3]) & (t1.values <= bins[4])] = ix[3]
        t1 = t1 * -1

        cdict = {1: 'red',2: 'orange',3: 'blue',4: 'green'}

        print(registered_time_points)
        for point in registered_time_points:
            #plt.axvline(x=int(point), ymin=-0.03, ymax=-0.015,c='r',linewidth=3)
            plt.axvline(x=int(point),c='r',linewidth=1) #,
            print(point)
        for index,label in enumerate(ix):
            t2 = t1.loc[t1.values == label * -1]
            plt.scatter(t2.index,[-0.015] * len(t2),c=cdict[index + 1],s=5,label=labels[index])

        plt.legend()
        f.savefig(path + 'velocity_above_zero_with_correlation.png',dpi=f.dpi,transparent=True,bbox_inches='tight')



        # temp_vec = df.loc[:,df.columns.str.contains('velocity2')].mean(axis=1).rolling(30).mean()
        # temp_vec.loc[temp_vec < 0] = 0
        #
        # t = df.loc[:,df.columns.str.contains('correlation2')].mean(axis=1)
        #
        df2 = df.copy()
        df2['time']= df.index #index is already in seconds (set in calculate_cross_correlation)
        df2['velocity'] = temp_vec.values
        df2['correlation'] = df.loc[:,df.columns.str.contains('correlation')].mean(axis=1).rolling(30,min_periods=1).mean()

        df2=df2.loc[:,['time','velocity','correlation']]
        df2.to_csv(path+'___report_summary.csv')


    def estimate_cross_correlation(self,frame_number):

        window_length = 100

        range_start,range_end = (frame_number - 1) - (window_length+1),frame_number - 1

        if range_start>0:

            df_window=self.get_mean_intensity_in_range(range_start,range_end)

            df_window = pd.DataFrame(df_window).T

            if len(df_window.dropna())>window_length:

                df_window.columns = ['first_vector','last_vector']

                # Same estimator as the batch pipeline (capillary.velocity),
                # including the corrected correlation origin — see the module
                # docstring there for the off-by-one this replaced.
                _lag,cross_correlation_estimation = lag_and_correlation(
                    df_window['first_vector'].to_numpy(),
                    df_window['last_vector'].to_numpy())

                if not np.isfinite(cross_correlation_estimation):
                    return 'N/A'

                return str(np.round(cross_correlation_estimation,1))

        return 'N/A'

    def calculate_cross_correlation(self,path='',st=201,en=311,jump=20):
        # this prepares a dataframe with the largest section of data that all have sequential values
        #
        # def shift_df(df,s=''):
        #
        #     an = pd.DataFrame(df)
        #     adjusted = []
        #     for i in range(an.shape[0]):
        #         adjusted.append(an.loc[i,:].shift(i * jump))
        #     # max_nan=int(pd.DataFrame(adjusted).T.isna().sum().max())
        #     return pd.DataFrame(adjusted,index=[s + str(window) for window in windows])


        df = pd.read_csv(path + '___cross_correlation.csv')
        df = df.T
        df = df.drop(index='Unnamed: 0')
        lookup = dict(df.loc[df[0].notna()].reset_index().loc[:,'index'].astype(int))
        temp = (df.loc[df[0].notna()].reset_index().loc[:,'index'].astype(int).diff() != 1).cumsum()
        index_ = temp.loc[temp == (df.loc[df[0].notna()].reset_index().loc[:,'index'].astype(
            int).diff() != 1).cumsum().value_counts().idxmax()].index
        df_selected = df.iloc[[lookup[i] for i in index_]]
        df_selected_reset_index = df_selected.reset_index(drop=True)

        windows = np.arange(st,en,jump)

        combined = []
        combined_correlation = []
        for window in windows:

            index_starts_at = window
            index_ends_at = len(df_selected_reset_index)

            offset = []
            correlation = []
            for index in range(index_starts_at,index_ends_at):
                # w = df_selected_reset_index.iloc[index-window:index]
                df_window = df_selected_reset_index.iloc[index - window:index]

                # Shared estimator (capillary.velocity.lag_and_correlation):
                # mean-subtracts both windows, takes the lag at the correlation
                # peak, then Pearson r at that alignment. It replaces an inline
                # copy whose correlation origin was one frame off on the odd
                # windows this report uses, which biased every velocity high.
                lag,ccc = lag_and_correlation(
                    np.asarray(df_window[0],dtype=float),
                    np.asarray(df_window[1],dtype=float))

                offset.append(lag)
                #
                #        plt.plot(a0)
                #        plt.plot(a1)
                #        plt.show()
                #        plt.plot(a)
                #        plt.show()
                #        plt.plot(df_window[0])
                #        plt.plot(df_window[1])
                #        plt.show()
                #
                #
                #        print(lag,ccc)

                correlation.append(ccc)

            combined.append(offset)
            combined_correlation.append(correlation)

        # lag = int(np.argmax(a) - np.ceil(len(df3[0]) / 2))

        # result = shift_df(combined,'')

        an = pd.DataFrame(combined)
        s = ''
        adjusted = []
        for i,window in enumerate(windows):
            adjusted.append(an.loc[i,:].shift(((window - st) / 2).astype(int)))
        # max_nan=int(pd.DataFrame(adjusted).T.isna().sum().max())
        result = pd.DataFrame(adjusted,index=[s + str(window) for window in windows])

        result = result.T.set_index(result.T.index + st)
        result.index = [lookup[i] for i in result.index]
        df_selected_reset_index.columns = ['firstvec_white_islast_rect1_0','lastvec_black_isfirst_rect2_1']
        df_selected_reset_index.index = [lookup[i] for i in index_]
        report_data = pd.concat([df_selected_reset_index,result],axis=1)

        an = pd.DataFrame(combined_correlation)
        s = 'correlation'
        adjusted = []
        for i,window in enumerate(windows):
            adjusted.append(an.loc[i,:].shift(((window - st) / 2).astype(int)))
        # max_nan=int(pd.DataFrame(adjusted).T.isna().sum().max())
        co = pd.DataFrame(adjusted,index=[s + str(window) for window in windows])

        co = co.T.set_index(co.T.index + st)
        co['best'] = co.idxmax(axis=1)
        co.index = [lookup[i] for i in co.index]

        report_data = pd.concat([report_data,co],axis=1)

        # this shift is done to push the index to the center of the window
        cols_to_shift = co.columns
        cols_to_shift = cols_to_shift.append(result.columns)
        #cols_to_shift.values
        for col in cols_to_shift.values:
            report_data.loc[:,col] = report_data.loc[:,col].shift(-np.ceil(st / 2).astype(int))

        d_vec = pd.read_csv(path + '___distance_vector.csv')
        d_vec = d_vec.drop('Unnamed: 0',axis=1)
        d_vec = d_vec.loc[[lookup[i] for i in index_]]
        d_vec.columns = ['distance']
        report_data = pd.concat([report_data,d_vec],axis=1)
        magnification_coefficient = self.magnificationCoefficient

        for col in result.columns.values:
            # A zero lag means the plug crossed both boxes inside one frame, not
            # that it moved infinitely fast; leaving the division to produce inf
            # would drag every downstream mean to inf, so it becomes NaN.
            lag_column = report_data[col].replace(0,np.nan)

            report_data['velocity' + col] = ((report_data['distance'] / -lag_column) / (
                        1.0 / self.fps)) * magnification_coefficient

            # distance (pixels) /time (1/30) = pixels per 1/30 seconds.
            # pixels per 1/30 seconds * 30 = pixels per seconds
            # magnificaiton coefficient transforms pixels to mm ->
            # pixels per seconds*magnificaiton coefficient = pixels per second

        print('here mate')
        print(len(df_selected),len(report_data))

        # a = int(df_selected.index.min()) - int(np.floor((len(report_data) - len(df_selected)) / 2))
        # s_indx_ = np.array(list(range(a,a + len(report_data)))) / 30
        #
        # report_data = report_data.set_index(s_indx_)

        report_data = report_data.set_index(np.array(list(report_data.index)) * (1.0 / self.fps))


        return report_data
        # # this prepares a dataframe with the largest section of data that all have sequential values
        # df = pd.read_csv(df_path)
        # df = df.T
        # df = df.drop(index='Unnamed: 0')
        # lookup = dict(df.loc[df[0] != -1].reset_index().loc[:,'index'].astype(int))
        # temp = (df.loc[df[0] != -1].reset_index().loc[:,'index'].astype(int).diff() != 1).cumsum()
        # index = temp.loc[temp == (df.loc[df[0] != -1].reset_index().loc[:,'index'].astype(
        #     int).diff() != 1).cumsum().value_counts().idxmax()].index
        # df_selected = df.iloc[[lookup[i] for i in index]]
        # df_selected_reset_index = df_selected.reset_index(drop=True)
        # st,en,jump = 20,80,10
        # windows = np.arange(st,en,jump)
        #
        # combined = []
        # combined_correlation = []
        # for window in windows:
        #
        #     index_starts_at = window
        #     index_ends_at = len(df_selected_reset_index)
        #
        #     offset = []
        #     correlation = []
        #     for index in range(index_starts_at,index_ends_at):
        #         df_window = (df_selected_reset_index.iloc[index - window:index] - df_selected_reset_index.iloc[
        #                                                                           index - window:index].mean())
        #
        #         a = []
        #
        #         a = signal.correlate(df_window[0],df_window[1],'same')
        #         # np.argmax(a)
        #         # df_window[1].shift(lag),df_window[0]
        #
        #         lag = int(np.ceil(len(df_window[0]) / 2) - np.argmax(a))
        #
        #         offset.append(lag)
        #
        #         ccc = pd.DataFrame(list(zip(df_window[0],df_window[1].shift(lag)))).dropna().corr().loc[0,1]
        #         correlation.append(ccc)
        #
        #     combined.append(offset)
        #     combined_correlation.append(correlation)
        #
        # lag = int(np.argmax(a) - np.ceil(len(df3[0]) / 2))
        #
        # ana = pd.DataFrame(combined)
        # adjusted = []
        # for i in range(ana.shape[0]):
        #     adjusted.append(ana.loc[i,:].shift(i * jump))
        # # max_nan=int(pd.DataFrame(adjusted).T.isna().sum().max())
        # result = pd.DataFrame(adjusted,index=[str(window) for window in windows])
        #
        # result = result.T.set_index(result.T.index + st)
        # df_selected_reset_index.columns = ['firstvec_white_islast_rect1_0','lastvec_black_isfirst_rect2_1']
        # report_data = pd.concat([df_selected_reset_index,result],axis=1)
        # return report_data

    def test(self,current_index):




        search_window = 100

        rectangle_intensities = self.get_mean_intensity_in_range(self,current_index-search_window,current_index)

        ## this code scrubs out blank values, an alternative is to not bother with those values since they are not accurate.
        # max_empty_val_first_vec = np.max(np.arange(len(rectangle_intensities[:,0]))[np.array(rectangle_intensities[:,0] == -1)])
        # max_empty_val_second_vec = np.max(np.arange(len(rectangle_intensities[:,1]))[np.array(rectangle_intensities[:,1] == -1)])
        # highest_empty_index = np.max(max_empty_val_first_vec,max_empty_val_second_vec)
        # number_of_non_blank_measurements = search_window-highest_empty_index
        #
        # rectangle_intensities = self.get_mean_intensity_in_range(self,current_index - number_of_non_blank_measurements,current_index)
        #

        # if any(rectangle_intensities[:,0]==-1) or any(rectangle_intensities[:,1]==-1):
        #     pass
        # else:
        #     pass



class EntryWithSet(tk.Entry):
    """
    A subclass to Entry that has a set method for setting its text to
    a given string, much like a Variable class.
    """

    def __init__(self, master, *args, **kwargs):
        tk.Entry.__init__(self, master, *args, **kwargs)


    def set(self, text_string):
        """
        Sets the object's text to text_string.
        """

        self.delete('0', 'end')
        self.insert('0', text_string)




# class Processing:
#     def __init__(self,master,url,command,*args,**kwargs):
#         self.master = master
#         self.url = url
#         self.command = command
#         self.info = Display_Info_Frame(self.master,self.url)
#
#         self.i = 0
#
#         if command=='stab':
#             self.process = self.master.video
#
#         self.update()
#
#
#     def update(self):
#         self.i+=1
#
#         #do stuff
#         self.info.update(self.command+' '+str(self.i))
#
#
#         #if not finished:
#         self.update()


