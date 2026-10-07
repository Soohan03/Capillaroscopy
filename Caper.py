"""Stabilization and the velocity reports behind the GUI.

The measurement itself — ROI geometry, intensity sampling, the lag estimator,
the space-time diagram — lives in the GUI-free `capillary` package. The code
here writes the stabilized videos and turns a saved data set (see
`capillary.datasets`) into the report CSVs and plots: `CrossCorrelation` for
two boxes, `generate_line_report` for a centre line, and
`generate_validation_report` for the agreement of observers and the estimator
on a reading set (`capillary.validation`). None of this imports tkinter; the
GUI runs it in worker threads.
"""
import math
import os

import cv2
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import SingleStepDFT as DFT
from Utilities import calculate_blur,clahe,median_filter

# The measurement itself lives in the GUI-free `capillary` package so that the
# GUI, the batch CLI and the unit tests all run the same arithmetic.
from capillary.velocity import lag_and_correlation


class Video:
    """Frame-by-frame reader for a grayscale video (channel 0 of the file)."""
    def __init__(self,path=''):
        # path can arrive as None when no video is selected; keep it a string
        # so path manipulation below doesn't crash.
        self.path = path if path is not None else ''
        self.number_of_frames_ = 0
        self.fps_ = 30
        self.height_ = None
        self.width_ = None
        self.frames_ = []
        self.frames_processed_ = []
        self.blur_vector = []
        self.cap = cv2.VideoCapture()
        self.cap_open=False
        self.writer = None
        self.pause=0
        self.finished = False
        self.frame = None

        self.output_path = self.path.replace('RecordedVideos','StabilizedVideos')

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


class CrossCorrelation:
    """The velocity report, built from a saved velocity data set.

    The data set (see capillary.datasets) holds the per-frame mean intensity
    of both boxes and their separation. Box convention (the report's column
    names spell it out, from when the boxes were drawn white and black):
      box 1, column 0: the downstream box, which the blood reaches LAST
      box 2, column 1: the upstream box, which the blood reaches FIRST
    hence velocity = distance / -lag in calculate_cross_correlation. The module
    docstring of capillary.velocity describes the same convention.
    """

    def __init__(self,fps=30.0,mm_per_pixel=0.001328903654):
        # use the video's real frame rate; a hardcoded 30 here would bias
        # every velocity estimate for videos recorded at another rate
        self.fps = float(fps) if fps else 30.0

        self.magnificationCoefficient = mm_per_pixel # spatial calibration, configured in settings.csv

    def generate_report(self,path,registered_time_points,report_path=None,progress=None):
        """Write the report for the data set at `path` and return its table.

        `path` is the data set's prefix in Statistics/ (``<stem>___<name>``);
        the table goes next to it as ``___report.csv``, the plots and the
        summary to `report_path` (by default `path` with Statistics replaced
        by Reports). `registered_time_points` (seconds) become red lines on the
        last plot. `progress` is called with 0..1 while the lags are computed.
        """
        df = self.calculate_cross_correlation(path,progress=progress)
        df.to_csv(path+'___report.csv')

        path = report_path if report_path is not None else path.replace('Statistics','Reports')

        f,ax = plt.subplots(figsize=(10,5),dpi=300)
        df.loc[:,df.columns.str.contains('velocity')].mean(axis=1).rolling(30,min_periods=1).mean().plot(ax=ax)
        plt.title('Velocity in mm/s')
        plt.ylabel('mm/s')
        plt.xlabel('Seconds')
        f.savefig(path+ 'velocity.png',dpi=f.dpi,transparent=True,bbox_inches = 'tight')
        plt.close(f)

        f,ax = plt.subplots(figsize=(10,5),dpi=300)
        temp_vec = df.loc[:,df.columns.str.contains('velocity')].mean(axis=1).rolling(30,min_periods=1).mean()
        temp_vec.loc[temp_vec<0]=0
        temp_vec.plot(ax=ax)
        plt.title('Velocity in mm/s')
        plt.ylabel('mm/s')
        plt.xlabel('Seconds')
        f.savefig(path+ 'velocity_above_zero.png',dpi=f.dpi,transparent=True,bbox_inches = 'tight')
        plt.close(f)

        f,ax = plt.subplots(figsize=(10,5),dpi=300)
        df.loc[:,df.columns.str.contains('correlation')].mean(axis=1).rolling(30,min_periods=1).mean().plot(ax=ax)
        plt.title('Correlation')
        plt.ylabel('Percent')
        plt.xlabel('Seconds')
        f.savefig(path+ 'correlation.png',dpi=f.dpi,transparent=True,bbox_inches = 'tight')
        plt.close(f)

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
        plt.close(f)

        df2 = df.copy()
        df2['time']= df.index #index is already in seconds (set in calculate_cross_correlation)
        df2['velocity'] = temp_vec.values
        df2['correlation'] = df.loc[:,df.columns.str.contains('correlation')].mean(axis=1).rolling(30,min_periods=1).mean()

        df2=df2.loc[:,['time','velocity','correlation']]
        df2.to_csv(path+'___report_summary.csv')
        return df

    def calculate_cross_correlation(self,path='',st=201,en=311,jump=20,progress=None):
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
        total_steps = sum(max(0,len(df_selected_reset_index) - window) for window in windows)
        steps_done = 0

        combined = []
        combined_correlation = []
        for window in windows:

            index_starts_at = window
            index_ends_at = len(df_selected_reset_index)

            offset = []
            correlation = []
            for index in range(index_starts_at,index_ends_at):
                steps_done += 1
                if progress is not None and steps_done % 250 == 0:
                    progress(steps_done / total_steps)
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


def generate_line_report(report_prefix, diagram, blocks, fps, mm_per_pixel, first_frame, time_points=(),
                         summary=None):
    """Plot a centre-line data set and write its summary row (see capillary.datasets).

    `diagram` is the space-time diagram (frames x positions along the line),
    `blocks` the per-block table from capillary.spacetime.analyze_space_time,
    `first_frame` the video frame of the diagram's first row and
    `report_prefix` is ``Reports/<stem>___<name>``. Writes
    ``___line_velocity.png`` (velocity over time), ``___space_time.png`` (the
    diagram with the measured slopes) and ``___line_summary.csv``.
    """
    fps = fps or 30.0
    resolved_mask = blocks['resolved'].astype(bool)
    resolved = blocks[resolved_mask]
    unresolved = blocks[~resolved_mask]

    # velocity over time
    f, ax = plt.subplots(figsize=(10, 5), dpi=300)
    ax.axhline(0, color='#9AA3AF', linewidth=0.6)
    if len(resolved):
        ax.plot(resolved['time_s'], resolved['velocity_mm_s'], 'o', markersize=3, color='#2F6FDE',
                label='3-s blocks')
        median = float(resolved['velocity_mm_s'].median())
        ax.axhline(median, color='#2F6FDE', linestyle='--', linewidth=1, label=f'median {median:.4f} mm/s')
    if len(unresolved):
        low = ax.get_ylim()[0] if len(resolved) else 0.0
        ax.plot(unresolved['time_s'], [low] * len(unresolved), '|', color='#9AA3AF', markersize=8,
                label='unresolved blocks')
    for point in time_points:
        ax.axvline(x=float(point), c='r', linewidth=1)
    ax.set_title('Velocity along the centre line')
    ax.set_ylabel('mm/s (positive: from the first point towards the last)')
    ax.set_xlabel('Seconds')
    ax.legend(loc='best', fontsize=8)
    f.savefig(report_prefix + '___line_velocity.png', dpi=f.dpi, transparent=True, bbox_inches='tight')
    plt.close(f)

    # the space-time diagram, without still structure and same-moment changes, with the measured slopes
    cleaned = np.asarray(diagram, dtype=float)
    cleaned = cleaned - cleaned.mean(axis=0, keepdims=True)
    cleaned = cleaned - cleaned.mean(axis=1, keepdims=True)
    low, high = np.percentile(cleaned, [1, 99]) if cleaned.size else (0, 1)
    length_um = (cleaned.shape[1] - 1) * mm_per_pixel * 1000.0
    start_s, stop_s = first_frame / fps, (first_frame + cleaned.shape[0]) / fps
    f, ax = plt.subplots(figsize=(12, 4), dpi=200)
    ax.imshow(cleaned.T, cmap='gray', vmin=low, vmax=high, aspect='auto', interpolation='nearest',
              extent=[start_s, stop_s, length_um, 0])
    step = max(1, len(resolved) // 40)
    for frame, row in resolved.iloc[::step].iterrows():
        centre = frame / fps
        slope = float(row['velocity_mm_s']) * 1000.0               # um per second along the line
        ax.plot([centre - 1.0, centre + 1.0], [length_um / 2 - slope, length_um / 2 + slope], color='#FF9F1C',
                linewidth=1)
    for point in time_points:
        ax.axvline(x=float(point), c='r', linewidth=1)
    ax.set_xlim(start_s, stop_s)
    ax.set_ylim(length_um, 0)
    ax.set_xlabel('Seconds')
    ax.set_ylabel('um along the line')
    ax.set_title('Space-time diagram along the centre line (orange: measured slope of the streaks)')
    f.savefig(report_prefix + '___space_time.png', dpi=f.dpi, bbox_inches='tight')
    plt.close(f)

    row = dict(summary or {})
    row['line_length_um'] = length_um
    pd.DataFrame([row]).to_csv(report_prefix + '___line_summary.csv', index=False)


def generate_validation_report(report_dir, table, comparisons):
    """Plot the comparisons of a reading set (see capillary.validation); returns the paths written.

    One panel per comparison with at least two pairs of velocities:
    ``bland_altman.png`` (difference against mean, with the bias and the 95%
    limits of agreement) and ``scatter.png`` (first measurement against
    second, with the line of identity). A plot with no panel left is removed,
    so an old one is never shown as if it were current.
    """
    os.makedirs(report_dir, exist_ok=True)
    panels = [c for c in comparisons if c.get('first_column') and (c.get('pairs') or 0) >= 2]
    written = {}
    for kind in ('bland_altman', 'scatter'):
        path = os.path.join(report_dir, kind + '.png')
        if not panels:
            if os.path.exists(path):
                os.remove(path)
            continue
        columns = min(3, len(panels))
        rows = int(math.ceil(len(panels) / columns))
        f, axes = plt.subplots(rows, columns, figsize=(4.8 * columns, 4.1 * rows), dpi=150, squeeze=False)
        for ax, comparison in zip(axes.flat, panels):
            a = table[comparison['first_column']].to_numpy(dtype=float)
            b = table[comparison['second_column']].to_numpy(dtype=float)
            keep = np.isfinite(a) & np.isfinite(b)
            a, b = a[keep], b[keep]
            first, second = comparison['first'], comparison['second']
            if kind == 'bland_altman':
                ax.axhline(0, color='#9AA3AF', linewidth=0.6)
                ax.plot((a + b) / 2, a - b, 'o', markersize=3.5, color='#2F6FDE', alpha=0.8)
                bias, low, high = comparison['bias'], comparison['loa_low'], comparison['loa_high']
                ax.axhline(bias, color='#2F6FDE', linewidth=1.2, label=f'bias {bias:+.4f}')
                ax.axhline(low, color='#E5484D', linestyle='--', linewidth=1,
                           label=f'95% limits {low:+.4f} to {high:+.4f}')
                ax.axhline(high, color='#E5484D', linestyle='--', linewidth=1)
                ax.set_xlabel('mean of both (mm/s)')
                ax.set_ylabel(f'{first} − {second} (mm/s)', fontsize=8)
                ax.legend(loc='best', fontsize=7)
            else:
                ax.plot(b, a, 'o', markersize=3.5, color='#2F6FDE', alpha=0.8)
                low = min(0.0, float(np.min(a)), float(np.min(b)))
                high = max(0.0, float(np.max(a)), float(np.max(b)))
                pad = 0.05 * (high - low or 1.0)
                ax.plot([low - pad, high + pad], [low - pad, high + pad], color='#9AA3AF', linewidth=0.8,
                        label='identity')
                ax.set_xlim(low - pad, high + pad)
                ax.set_ylim(low - pad, high + pad)
                ax.set_aspect('equal')
                ax.set_xlabel(f'{second} (mm/s)', fontsize=8)
                ax.set_ylabel(f'{first} (mm/s)', fontsize=8)
                ax.legend(loc='upper left', fontsize=7)
            ax.set_title(f'{comparison["comparison"]}\n{len(a)} blocks with a velocity from both', fontsize=8)
            ax.tick_params(labelsize=7)
        for ax in list(axes.flat)[len(panels):]:
            ax.axis('off')
        f.tight_layout()
        f.savefig(path, dpi=f.dpi, bbox_inches='tight')
        plt.close(f)
        written[kind] = path
    return written
