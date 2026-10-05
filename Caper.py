"""Video, stabilization, optical-flow, ROI and report classes behind the GUI.

The velocity arithmetic itself lives in the GUI-free `capillary` package; the
classes here read and write videos, draw the ROI boxes and assemble the
report from the CSV files the Analyze tab saves.
"""
import datetime
import os

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from skimage.filters import threshold_multiotsu

import SingleStepDFT as DFT
from Utilities import (pickle_save,pickle_load,calculate_blur,clahe,median_filter,
                       rgb_to_negR_posG,distance_between_two_points)

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

    def destroy_writer(self):
        self.writer.release()

    def save_frame(self,frame):
        if self.writer is None:
            self.writer = cv2.VideoWriter(self.outputfile,cv2.VideoWriter_fourcc(*'MP4V'),30.0,(640,480))
        frame = rgb_to_negR_posG(frame)
        frame = cv2.merge((frame,frame,frame))
        self.writer.write(frame.astype(np.uint8))


class Video:
    """Frame-by-frame reader for a grayscale video (channel 0 of the file)."""
    def __init__(self,path=''):
        # path can arrive as None when no video is selected (e.g. empty Flows/);
        # keep it a string so path manipulation below doesn't crash.
        self.path = path if path is not None else ''
        self.number_of_frames_ = 0
        self.fps_ = 30
        self.height_ = None
        self.width_ = None
        self.frames_ = []
        self.frames_processed_ = []
        self.blur_vector = []
        self.thumbnail_ = None
        self.cap = cv2.VideoCapture()
        self.cap_open=False
        self.writer = None
        self.pause=0
        self.finished = False
        self.frame = None

        self.output_path = self.path.replace('RecordedVideos','StabilizedVideos')

    def generate_thumbnail(self,factor=0.15):
        self.cap.open(self.path)
        self.number_of_frames_ = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps_ = int(self.cap.get(cv2.CAP_PROP_FPS)) or 30 #fall back to the recorder's rate when the file reports none
        self.width_=int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height_=int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        frame =self.get_frame()
        try: # flow videos are stored as HSV; plain videos come back single-channel and raise here
            frame = cv2.cvtColor(frame,cv2.COLOR_HSV2BGR)
        except:
            pass
        self.thumbnail_ = cv2.resize(frame,None,fx=factor,fy=factor)

    def destroy_writer(self):
        self.writer.release()

    def save_frame(self,frame):
        if self.writer is None:
            self.writer = cv2.VideoWriter(self.output_path,cv2.VideoWriter_fourcc(*'MP4V'),30.0,(640,480))

        self.writer.write(cv2.merge((frame,frame,frame)).astype(np.uint8))

    def get_frame(self):
        if self.cap_open == False:
            self.cap.open(self.path)
            self.number_of_frames_ = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps_ = int(self.cap.get(cv2.CAP_PROP_FPS)) or 30 #fall back to the recorder's rate when the file reports none
            self.width_ = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height_ = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.aspect_ratio_ = self.height_/self.width_
            self.blur_vector = np.zeros([self.number_of_frames_])
            self.pause = 0
            self.cap_open=True

            self.frame_number = self.get_frame_number()
            current_frame = self.cap.read()[1][:,:,0]
            return current_frame
        else:
            # at the last frame, keep returning it (and flag the video as finished)
            if self.get_frame_number() < self.number_of_frames_-1:
                self.frame_number = self.get_frame_number()
                try:
                    current_frame = self.cap.read()[1][:,:,0]
                except:
                    current_frame = self.cap.read()[1][:,:,0]
                self.frame = current_frame
                return current_frame
            else:
                self.finished = True
                return self.frame

    def set_frame(self,frame_number):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES,frame_number)
        self.finished = False

    def get_frame_number(self):
        return int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))-1

    def go_back_or_forward_n_frames(self,n):

        frame_number = self.get_frame_number()
        if (frame_number+n) > self.number_of_frames_ or (frame_number+n)<0:
            pass
        else:
            self.set_frame(frame_number+n)


class FlowVideo(Video):
    """Dense optical flow (Farneback) of a stabilized video, one frame per update().

    Writes an HSV-encoded flow video to Flows/ and, every 20 frames and at the
    end, a pickle with the average flow magnitude, average intensity and the
    vessel mask derived from them.
    """
    def __init__(self,path):
        Video.__init__(self,path=path)
        self.video_path = path
        self.video = Video(self.video_path)
        self.output_path = path.replace('StabilizedVideos','Flows')
        self.video.get_frame()
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
        if fr_num < self.video.number_of_frames_ - 1:
            fr = self.video.get_frame()
            self.average += fr
            flow = cv2.calcOpticalFlowFarneback(self.previous_frame,fr,None,0.5,6,7,7,5,1.2,0)
            self.previous_frame = fr
            mag,ang = cv2.cartToPolar(flow[...,0],flow[...,1])

            temp = np.zeros_like(self.frame)
            temp[...,1] = 255
            temp[...,0] = ang * 180 / np.pi / 2

            mag[mag > 10] = 0  # very few values are higher than 10, most are 0.5 or similar, some are up to 5
            mag = mag * 25.5
            self.average_flow += mag.astype(np.float64)
            temp[...,2] = mag

            self.save_frame(temp)

            if self.video.get_frame_number() % 20 == 0 and fr_num > 20:
                self.create_pickle()
        else:
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
        self.current_stage = 'processing'
        self.paths = paths
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


class ColorVideo(Video):
    """Reader for flow videos (3-channel), with the vessel mask from their pickle."""
    def __init__(self,path):
        Video.__init__(self,path=path)
        self.stack = []
        self.file = pickle_load(self.path[:-4] + '.pickle')
        self.mask = self.file[:,:,2].astype(np.uint8)

    def get_frame(self,rolling_average=0,return_non_average=0):

        if self.cap_open == False:
            self.cap.open(self.path)
            self.number_of_frames_ = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps_ = int(self.cap.get(cv2.CAP_PROP_FPS)) or 30 #fall back to the recorder's rate when the file reports none
            self.width_ = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height_ = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.aspect_ratio_ = self.height_/self.width_
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

    def set_frame(self,frame_number):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES,frame_number)
        self.finished = False
        self.stack=[]


class VideoStabilization(Video):
    """Translation-only stabilization, one frame per update() call.

    Stages: load (read frames, score sharpness) -> transform (CLAHE + median
    filter) -> stabilize (sub-pixel registration of every frame against the
    sharpest frames) -> write (shift each raw frame by the mean offset) ->
    finished. The output goes to StabilizedVideos/ under the same name.
    """
    def __init__(self,path):
        Video.__init__(self,path=path)
        self.raw_stabilization_vector = None
        self.reference_frames = None
        self.number_of_reference_frames = 3
        self.usfac = 100
        self.current_stage = 'load'

        self.translation_vector = None

        self.get_frame()
        self.set_frame(0)

        self.index = 0

    def load_stabilization(self,index=0):
        #only for BW right now
        if index > 0:
            self.frames_[index,:,:] = self.cap.read()[1][:,:,0]
            self.blur_vector[index] = calculate_blur(self.frames_[index,:,:])

        else:
            self.cap.open(self.path)
            self.number_of_frames_ = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

            self.fps_ = int(self.cap.get(cv2.CAP_PROP_FPS)) or 30 #fall back to the recorder's rate when the file reports none
            self.width_=int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.height_=int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.aspect_ratio_ = self.height_/self.width_
            self.frames_ = np.zeros([self.number_of_frames_,self.height_,self.width_])
            self.frames_processed_ = np.zeros([self.number_of_frames_,self.height_,self.width_])
            self.blur_vector = np.zeros([self.number_of_frames_])
            self.pause = 0

    def generate_reference_frames(self):
        self.reference_frames =self.frames_processed_[pd.Series(self.blur_vector).sort_values(ascending=False).index[:self.number_of_reference_frames].values] #returns sharpest images

    def stabilize_frame(self,frame,frame_number):
        for index,reference_image in enumerate(self.reference_frames):
            self.raw_stabilization_vector[frame_number,index,:] = DFT.register_images(frame,reference_image,usfac=self.usfac)

    def stabilize_video(self,index):
        if self.raw_stabilization_vector is None:
            temp = np.empty([self.number_of_frames_,self.number_of_reference_frames,2])
            temp[:] = np.nan
            self.raw_stabilization_vector = temp #now we can know that all non nan values are calculated

        self.stabilize_frame(self.frames_processed_[index,:,:],index)

    def transform(self,index):
        current_frame = self.frames_[index,:,:]
        clahe_filter_current_frame =clahe(current_frame)
        processed_frame = median_filter(clahe_filter_current_frame)
        self.frames_processed_[index,:,:] =processed_frame

    def update(self):

        if self.current_stage == 'load':
            self.load_stabilization(index=self.index)
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


class VideoStabilizationMultiple:
    def __init__(self,paths):
        self.current_stage = 'processing'
        self.paths = paths
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


class Rectangle:
    """One ROI box on the video frame, in video pixel coordinates.

    The Analyze tab centres a fixed-size box on a click (calculate_corners); the
    Flow tab spans the box between the two ends of a drag (calculate_corners_drag).
    """

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

    def draw_rectangle(self,frame):
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

        self.calculate_corners_drag(self.point1,self.point2)

        frame = cv2.rectangle(self.frame.copy(),self.lower_left,self.top_right,self.color,self.thickness)

        return frame

    def get_selected_data(self):
        return self.frame[self.lower_left[1]:self.top_left[1],self.lower_left[0]:self.lower_right[0]]  # indexed y,x

    def get_selected_data_for_flow(self,frame):
        return frame[self.top_left[1]:self.lower_left[1],self.lower_left[0]:self.lower_right[0],:]  # indexed y,x

    def get_selected_data_for_mask(self,mask):
        return mask[self.top_left[1]:self.lower_left[1],self.lower_left[0]:self.lower_right[0]]


class CrossCorrelation:
    """Per-frame ROI intensities of the Analyze tab, and the velocity report built from them.

    Box convention (the report's column names spell it out):
      rectangle1 -> first_vec, column 0: the white box, which the blood reaches LAST
      rectangle2 -> last_vec,  column 1: the black box, which the blood reaches FIRST
    hence velocity = distance / -lag in calculate_cross_correlation. The module
    docstring of capillary.velocity describes the same convention.
    """

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
        return pd.Series(self.distance_vector).notna().sum()>300

    def calculate_distance(self,index):
        c1=self.rectangle_first.get_clicks()
        c2=self.rectangle_last.get_clicks()

        self.distance_vector[index] = distance_between_two_points(c1[1],c2[1],c1[0],c2[0])

    def set_cropped_frame_data(self,index,data_first,data_last):
        self.first_vec[index] = data_first
        self.last_vec[index] = data_last

    def get_mean_intensity(self):
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

        f,ax = plt.subplots(figsize=(10,5),dpi=300)
        temp_vec = df.loc[:,df.columns.str.contains('velocity')].mean(axis=1).rolling(30,min_periods=1).mean()
        temp_vec.loc[temp_vec < 0] = 0
        temp_vec.plot(ax=ax,label='velocity')
        plt.title('Velocity in mm/s')
        plt.ylabel('mm/s')
        plt.xlabel('Seconds')

        # correlation quality band drawn as coloured dots under the velocity curve
        t1 = df.loc[:,df.columns.str.contains('correlation')].mean(axis=1).rolling(30,min_periods=1).mean()

        labels = ["0-25","25-50","50-75","75-100"]
        ix = [10,20,30,50]
        bins = [0,0.25,0.5,0.75,1.0]
        t1.loc[(t1.values > bins[0]) & (t1.values <= bins[1])] = ix[0]
        t1.loc[(t1.values > bins[1]) & (t1.values <= bins[2])] = ix[1]
        t1.loc[(t1.values > bins[2]) & (t1.values <= bins[3])] = ix[2]
        t1.loc[(t1.values > bins[3]) & (t1.values <= bins[4])] = ix[3]
        t1 = t1 * -1

        cdict = {1: 'red',2: 'orange',3: 'blue',4: 'green'}

        for point in registered_time_points:
            plt.axvline(x=int(point),c='r',linewidth=1)
        for index,label in enumerate(ix):
            t2 = t1.loc[t1.values == label * -1]
            plt.scatter(t2.index,[-0.015] * len(t2),c=cdict[index + 1],s=5,label=labels[index])

        plt.legend()
        f.savefig(path + 'velocity_above_zero_with_correlation.png',dpi=f.dpi,transparent=True,bbox_inches='tight')

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
                correlation.append(ccc)

            combined.append(offset)
            combined_correlation.append(correlation)

        an = pd.DataFrame(combined)
        adjusted = []
        for i,window in enumerate(windows):
            adjusted.append(an.loc[i,:].shift(((window - st) / 2).astype(int)))
        result = pd.DataFrame(adjusted,index=[str(window) for window in windows])

        result = result.T.set_index(result.T.index + st)
        result.index = [lookup[i] for i in result.index]
        df_selected_reset_index.columns = ['firstvec_white_islast_rect1_0','lastvec_black_isfirst_rect2_1']
        df_selected_reset_index.index = [lookup[i] for i in index_]
        report_data = pd.concat([df_selected_reset_index,result],axis=1)

        an = pd.DataFrame(combined_correlation)
        adjusted = []
        for i,window in enumerate(windows):
            adjusted.append(an.loc[i,:].shift(((window - st) / 2).astype(int)))
        co = pd.DataFrame(adjusted,index=['correlation' + str(window) for window in windows])

        co = co.T.set_index(co.T.index + st)
        co['best'] = co.idxmax(axis=1)
        co.index = [lookup[i] for i in co.index]

        report_data = pd.concat([report_data,co],axis=1)

        # this shift is done to push the index to the center of the window
        cols_to_shift = co.columns
        cols_to_shift = cols_to_shift.append(result.columns)
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

            # distance [pixels] / (lag [frames] / fps) = pixels per second;
            # times mm_per_pixel = mm per second
            report_data['velocity' + col] = ((report_data['distance'] / -lag_column) / (
                        1.0 / self.fps)) * magnification_coefficient

        report_data = report_data.set_index(np.array(list(report_data.index)) * (1.0 / self.fps))

        return report_data
