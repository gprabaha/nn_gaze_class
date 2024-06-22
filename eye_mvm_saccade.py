#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 17 11:40:06 2024

@author: pg496
"""

import numpy as np
import util

class EyeMVMSaccadeDetector:
    def __init__(self, vel_thresh, min_samples, smooth_func):
        self.vel_thresh = vel_thresh
        self.min_samples = min_samples
        self.smooth_func = smooth_func

    def extract_saccades_for_session(self, session_data):
        positions, info = session_data
        sampling_rate = info['sampling_rate']
        n_samples = positions.shape[0]
        time_vec = util.create_timevec(n_samples, sampling_rate)
        session_saccades = self.extract_saccades(positions, time_vec, info)
        return session_saccades

    def extract_saccades(self, positions, time_vec, info):
        session_saccades = []
        category = info['category']
        session_name = info['session_name']
        n_runs = info['num_runs']
        for run in range(n_runs):
            run_start = info['startS'][run]
            run_stop = info['stopS'][run]
            run_time = (time_vec > run_start) & (time_vec <= run_stop)
            run_positions = positions[run_time, :]
            run_x = util.px2deg(run_positions[:, 0].T)
            run_y = util.px2deg(run_positions[:, 1].T)
            saccade_start_stops = self.find_saccades(run_x, run_y, info['sampling_rate'])
            for start, stop in saccade_start_stops:
                saccade = run_positions[start:stop + 1, :]
                start_time = time_vec[start]
                end_time = time_vec[stop]
                duration = end_time - start_time
                start_roi = self.determine_roi_of_coord(run_positions[start, :2], info['roi_bb_corners'])
                end_roi = self.determine_roi_of_coord(run_positions[stop, :2], info['roi_bb_corners'])
                block = self.determine_block(start_time, end_time, info['startS'], info['stopS'])
                session_saccades.append([start_time, end_time, duration, saccade, start_roi, end_roi, session_name, category, run, block])
        return session_saccades

    def find_saccades(self, x, y, sr):
        assert x.shape == y.shape
        start_stops = []
        x0 = self.smooth_func(x)
        y0 = self.smooth_func(y)
        vx = np.gradient(x0) / sr
        vy = np.gradient(y0) / sr
        vel_norm = np.sqrt(vx ** 2 + vy ** 2)
        above_thresh = (vel_norm >= self.vel_thresh[0]) & (vel_norm <= self.vel_thresh[1])
        start_stops = util.find_islands(above_thresh, self.min_samples)
        return start_stops

    def determine_roi_of_coord(self, position, bbox_corners):
        bounding_boxes = ['eye_bbox', 'face_bbox', 'left_obj_bbox', 'right_obj_bbox']
        inside_roi = [util.is_inside_roi(position, bbox_corners[key]) for key in bounding_boxes]
        if any(inside_roi):
            if inside_roi[0] and inside_roi[1]:
                return bounding_boxes[0]
            return bounding_boxes[inside_roi.index(True)]
        return 'out_of_roi'

    def determine_block(self, start_time, end_time, startS, stopS):
        if start_time < startS[0] or end_time > stopS[-1]:
            return 'discard'
        for i, (run_start, run_stop) in enumerate(zip(startS, stopS), start=1):
            if start_time >= run_start and end_time <= run_stop:
                return 'mon_down'
            elif i < len(startS) and end_time <= startS[i]:
                return 'mon_up'
        return 'discard'
