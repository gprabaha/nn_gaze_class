#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jun 22 11:18:08 2024

@author: pg496
"""

import numpy as np
import pandas as pd
from tqdm import tqdm
import util

class EyeMVMFixationDetector:
    def __init__(self, sampling_rate):
        self.sampling_rate = sampling_rate

    def detect_fixations(self, positions, time_vec, session_name):
        fix_timepos_df, fix_vec_entire_session = self.is_fixation(positions, time_vec, session_name)
        fixationtimes = fix_timepos_df[['start_time', 'end_time']].to_numpy().T
        fixations = fix_timepos_df[['fix_x', 'fix_y']].to_numpy().T
        return fixationtimes, fixations

    def is_fixation(self, pos, time, session_name, t1=None, t2=None, minDur=None, maxDur=None):
        """
        Determine fixations based on position and time data.
        Args:
        pos: Position data (x, y).
        time: Time data.
        t1: Spatial parameter t1.
        t2: Spatial parameter t2.
        minDur: Minimum fixation duration.
        sampling_rate: Sampling rate.
        Returns:
        Binary vector indicating fixations (1) and non-fixations (0).
        """
        data = np.column_stack((pos, time))
        if minDur is None:
            minDur = 0.05
        if maxDur is None:
            maxDur = 2
        if t2 is None:
            t2 = 15
        if t1 is None:
            t1 = 30
        fix_vector = np.zeros(data.shape[0])
        fix_list_df, fix_t_inds = self.fixation_detection(data, t1, t2, minDur, maxDur, session_name)
        for t_range in fix_t_inds:
            fix_vector[t_range[0]:t_range[1] + 1] = 1
        return fix_list_df, fix_vector

    def fixation_detection(self, data, t1, t2, minDur, maxDur, session_name):
        """
        Detect fixations based on position and time data.
        Args:
        data: Combined position and time data.
        t1: Spatial parameter t1.
        t2: Spatial parameter t2.
        minDur: Minimum fixation duration.
        Returns:
        List of fixation time ranges.
        """
        n = len(data)
        if n == 0:
            return []  
        x = data[:, 0]
        y = data[:, 1]
        t = data[:, 2]
        fixations = self.get_t1_filtered_fixations(n, x, y, t, t1, session_name)
        number_fixations = fixations[-1, 3]
        fixation_list = []
        for i in tqdm(range(1, int(number_fixations) + 1), desc=f"{session_name}: n fixations t2 filtered"):
            fixation_list.append(self.filter_fixations_t2(i, fixations, t2))
        fixation_list = self.min_duration(fixation_list, minDur)
        fixation_list = self.max_duration(fixation_list, maxDur)
        fix_ranges = []
        for fix in fixation_list:
            s_ind = np.where(data[:, 2] == fix[4])[0][0]
            e_ind = np.where(data[:, 2] == fix[5])[0][-1]
            fix_ranges.append([s_ind, e_ind])
        col_names = ['fix_x', 'fix_y', 'threshold_1', 'threshold_2', 'start_time', 'end_time', 'duration']
        return pd.DataFrame(fixation_list, columns=col_names), fix_ranges

    def get_t1_filtered_fixations(self, n, x, y, t, t1, session_name):
        fixations = np.zeros((n, 4))
        fixid = 0
        fixpointer = 0
        for i in tqdm(range(n), desc='{}: n data points t1 filtered'.format(session_name)):
            if not np.any(x[fixpointer:i + 1]) or not np.any(y[fixpointer:i + 1]):
                fixations = self.update_fixations(i, x, y, t, fixations, fixid)
            else:
                mx = np.mean(x[fixpointer:i + 1])
                my = np.mean(y[fixpointer:i + 1])
                d = util.distance2p(mx, my, x[i], y[i])
                if d > t1:
                    fixid += 1
                    fixpointer = i
                fixations = self.update_fixations(i, x, y, t, fixations, fixid)
        return fixations

    def update_fixations(self, i, x, y, t, fixations, fixid):
        fixations[i, 0] = x[i]
        fixations[i, 1] = y[i]
        fixations[i, 2] = t[i]
        fixations[i, 3] = fixid
        return fixations

    def filter_fixations_t2(self, fixation_id, fixations, t2):
        fixations_id = fixations[fixations[:, 3] == fixation_id]
        number_t1 = len(fixations_id)
        fixx, fixy = np.nanmean(fixations_id[:, :2], axis=0)
        for i in range(number_t1):
            d = util.distance2p(fixx, fixy, fixations_id[i, 0], fixations_id[i, 1])
            if d > t2:
                fixations_id[i, 3] = 0
        fixations_list_t2 = np.empty((0, 4))
        list_out_points = np.empty((0, 4))
        for i in range(number_t1):
            if fixations_id[i, 3] > 0:
                fixations_list_t2 = np.vstack((fixations_list_t2, fixations_id[i, :]))
            else:
                list_out_points = np.vstack((list_out_points, fixations_id[i, :]))
        number_t2 = fixations_list_t2.shape[0]
        if not np.any(fixations_list_t2[:, :2]):
            start_time, end_time, duration = 0, 0, 0
        else:
            fixx, fixy = np.nanmean(fixations_list_t2[:, :2], axis=0)
            start_time = fixations_list_t2[0, 2]
            end_time = fixations_list_t2[-1, 2]
            duration = end_time - start_time
        return fixx, fixy, number_t1, number_t2, start_time, end_time, duration

    def min_duration(self, fixation_list, minDur):
        return [fix for fix in fixation_list if fix[6] >= minDur]

    def max_duration(self, fixation_list, maxDur):
        return [fix for fix in fixation_list if fix[6] <= maxDur]
