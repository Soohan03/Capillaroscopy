import datetime
import numpy as np
from Utilities import seconds_to_hms_string

class ProgressMonitor:

    def __init__(self):
        self.start_time = datetime.datetime.now()
        self.latest_iteration_time = datetime.datetime.now()
        self.time_remaining = datetime.timedelta(seconds=0)
        self.time_elapsed = 0
        self.ETA = datetime.timedelta(seconds=0)
        self.time_since_last_iteration = datetime.timedelta(seconds=1)
        # self.accumulated_percentage = 0
        self.latest_recorded_percentage = 0
        # self.diff_in_percent_since_last_iteration = 0
        self.history=[]

        self.output=''

    def update_progress(self,accumulated_percentage = 0):
        if accumulated_percentage<1:
            accumulated_percentage = accumulated_percentage*100
        self.time_since_last_iteration = (datetime.datetime.now()-self.latest_iteration_time).microseconds/1000000
        self.diff_in_percent_since_last_iteration = (accumulated_percentage - self.latest_recorded_percentage)



        if self.diff_in_percent_since_last_iteration>0:
        # try: #if update very small, there are problems with zero division
            self.time_elapsed +=self.time_since_last_iteration
            time_since_last_iteration_in_seconds = self.time_since_last_iteration

            seconds_per_percent  =  time_since_last_iteration_in_seconds/self.diff_in_percent_since_last_iteration
            self.history.append(seconds_per_percent)
            adjusted_seconds_per_percent = np.mean(self.history).astype(float)
            remaining_percentage = 100 - accumulated_percentage
            estimated_seconds_remaining = int(remaining_percentage* adjusted_seconds_per_percent)


            output='\nTime remaining:\n'
            # print('Time remaining:')
            # print(seconds_to_hms_string(estimated_seconds_remaining))
            output += seconds_to_hms_string(estimated_seconds_remaining)
            finish_time = (self.start_time + datetime.timedelta(seconds=int(estimated_seconds_remaining)))
            # print('Estimated finish time:')
            # print(finish_time.strftime('%H:%M:%S'))

            output += '\nEstimated finish time:\n'
            output +=finish_time.strftime('%H:%M:%S')
            output += '\n'


            self.latest_iteration_time = datetime.datetime.now()
            self.latest_recorded_percentage = accumulated_percentage
            self.output = output
            return output
        else:
            pass
        # except:
        #     pass


monitor = ProgressMonitor()
monitor.update_progress(70)