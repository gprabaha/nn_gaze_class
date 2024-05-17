#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May 10 12:00:42 2024

@author: pg496
"""

import os
import glob
import scipy.io
import numpy as np
import pandas as pd

import util

import pdb


def get_root_data_dir(is_cluster):
    """
    Returns the root data directory based on whether it's running on a cluster or not.
    Parameters:
    - is_cluster (bool): Boolean flag indicating whether the program is running on a cluster.
    Returns:
    - root_data_dir (str): Root data directory path.
    """
    return "/gpfs/milgram/project/chang/pg496/data_dir/otnal/" if is_cluster \
        else "/Volumes/Stash/changlab/sorted_neural_data/social_gaze_otnal/AllFVProcessed/"


def get_subfolders(root_dir):
    """
    Retrieves subfolders within a given directory.
    Parameters:
    - root_dir (str): Root directory path.
    Returns:
    - subfolders (list): List of subfolder paths.
    """
    return [f.path for f in os.scandir(root_dir) if f.is_dir()]


def get_monkey_and_dose_data(session_path):
    """
    Extracts information data from session path.
    Parameters:
    - session_path (str): Path to the session.
    Returns:
    - info_dict (dict): Dictionary containing information data.
    """
    file_list_info = glob.glob(f"{session_path}/*metaInfo.mat")
    if len(file_list_info) != 1:
        print(f"\nWarning: No metaInfo or more than one metaInfo found in folder: {session_path}.")
        return {}
    try:
        data_info = scipy.io.loadmat(file_list_info[0])
        info = data_info.get('info', [None])[0]
        if info is not None:
            return {
                'monkey_1': info['monkey_1'][0],
                'monkey_2': info['monkey_2'][0],
                'OT_dose': float(info['OT_dose'][0]),
                'NAL_dose': float(info['NAL_dose'][0])
            }
    except Exception as e:
        print(f"\nError loading meta_info for folder: {session_path}: {e}")
    return {}


def get_runs_data(session_path):
    """
    Extracts runs data from session path.
    Parameters:
    - session_path (str): Path to the session.
    Returns:
    - runs_dict (dict): Dictionary containing runs data.
    """
    file_list_runs = glob.glob(f"{session_path}/*runs.mat")
    if len(file_list_runs) != 1:
        print(f"\nWarning: No runs found in folder: {session_path}.")
        return {}
    try:
        data_runs = scipy.io.loadmat(file_list_runs[0])
        runs = data_runs.get('runs', [None])[0]
        if runs is not None:
            startS = [run['startS'][0][0] for run in runs]
            stopS = [run['stopS'][0][0] for run in runs]
            return {'startS': startS, 'stopS': stopS, 'num_runs': len(startS)}
    except Exception as e:
        print(f"\nError loading runs for folder: {session_path}: {e}")
    return {}


def get_m1_roi_bounding_boxes(session_path, map_roi_coord_to_eyelink_space):
    """
    Extracts M1 ROI bounding boxes from session path.
    Parameters:
    - session_path (str): Path to the session.
    - map_roi_coord_to_eyelink_space (bool): Flag to determine if coordinates should be remapped.
    Returns:
    - bbox_dict (dict): Dictionary containing M1 ROI bounding boxes.
    """
    file_list_m1_landmarks = glob.glob(f"{session_path}/*M1_farPlaneCal_regForm.mat")
    if len(file_list_m1_landmarks) != 1:
        print(f"\nWarning: No m1_landmarks or more than one landmarks found in folder: {session_path}.")
        return {'eye_bbox': None, 'face_bbox': None, 'left_obj_bbox': None, 'right_obj_bbox': None}
    try:
        data_m1_landmarks = scipy.io.loadmat(file_list_m1_landmarks[0])
        m1_landmarks = data_m1_landmarks.get('farPlaneCal', None)
        if m1_landmarks is not None:
            eye_bbox, face_bbox, left_obj_bbox, right_obj_bbox = \
                util.calculate_roi_bounding_box_corners(m1_landmarks, map_roi_coord_to_eyelink_space)
            return {'eye_bbox': eye_bbox,
                    'face_bbox': face_bbox,
                    'left_obj_bbox': left_obj_bbox,
                    'right_obj_bbox': right_obj_bbox}
    except Exception as e:
        print(f"\nError loading m1_landmarks for folder: {session_path}: {e}")
    return {'eye_bbox': None, 'face_bbox': None, 'left_obj_bbox': None, 'right_obj_bbox': None}


def get_labelled_gaze_positions_dict_m1(folder_path, meta_info_list, session_categories, idx, map_gaze_pos_coord_to_eyelink_space):
    """
    Process gaze data from a session folder.
    Parameters:
    - folder_path (str): Path to the session folder.
    - meta_info_list (list): List of dictionaries containing meta-information for each session.
    - session_categories (ndarray): Session categories.
    - idx (int): Index to access specific session data.
    - map_gaze_pos_coord_to_eyelink_space (bool): Flag to determine if coordinates should be remapped.
    Returns:
    - gaze_data (tuple): Tuple containing gaze positions and associated metadata.
    """
    mat_files = [f for f in os.listdir(folder_path) if 'M1_gaze_regForm.mat' in f]
    if len(mat_files) != 1:
        print(f"\nError: Multiple or no '*_M1_gaze_regForm.mat' files found in folder: {folder_path}")
        return None
    mat_file_path = os.path.join(folder_path, mat_files[0])
    try:
        mat_data = scipy.io.loadmat(mat_file_path)
        sampling_rate = float(mat_data['M1FS'])
        M1Xpx = mat_data['M1Xpx'].squeeze()
        M1Ypx = mat_data['M1Ypx'].squeeze()
        gaze_positions = np.column_stack((M1Xpx, M1Ypx))
        if map_gaze_pos_coord_to_eyelink_space:
            gaze_positions = np.array([util.map_coord_to_eyelink_space(coord)
                                       for coord in gaze_positions])
        meta_info = meta_info_list[idx]
        meta_info.update({'sampling_rate': sampling_rate, 'category': session_categories[idx]})
        return gaze_positions, meta_info
    except Exception as e:
        print(f"\nError loading file '{mat_files[0]}': {e}")
        return None


def get_spiketimes_and_labels_for_one_session(session_path):
    """
    Extracts spike times and labels from a session.
    Parameters:
    - session_path (str): Path to the session.
    Returns:
    - session_spikeTs_s (list): List of spike times in seconds.
    - session_spikeTs_ms (list): List of spike times in milliseconds.
    - spike_df (DataFrame): DataFrame containing spike labels.
    """
    session_spikeTs_s = []
    session_spikeTs_ms = []
    session_spikeTs_labels = []
    label_cols = ['session_name', 'channel', 'channel_label', 'unit_no_within_channel', 'unit_label', 'uuid', 'n_spikes', 'region']
    session_name = os.path.basename(os.path.normpath(session_path))
    file_list_spikeTs = glob.glob(f"{session_path}/*spikeTs_regForm.mat")
    if len(file_list_spikeTs) != 1:
        print(f"\nWarning: No spikeTs or more than one spikeTs found in folder: {session_path}.")
        return session_spikeTs_s, session_spikeTs_ms, pd.DataFrame(columns=label_cols)
    try:
        data_spikeTs = scipy.io.loadmat(file_list_spikeTs[0])
        spikeTs_struct = data_spikeTs['spikeTs'][0]
        for unit in spikeTs_struct:
            spikeTs_sec = np.squeeze(unit['spikeS'])
            spikeTs_ms = np.squeeze(unit['spikeMs'])
            session_spikeTs_s.append(spikeTs_sec.tolist())  # Append spike times in seconds
            session_spikeTs_ms.append(spikeTs_ms.tolist())  # Append spike times in milliseconds
            chan = unit['chan'][0][0]
            chan_label = unit['chanStr'][0]
            unit_no_in_channel = unit['unit'][0][0]
            unit_label = unit['unitStr'][0]
            uuid = unit['UUID'][0]
            n_spikes = unit['spikeN'][0][0]
            region = unit['region'][0]
            # Append label row to the labels list
            session_spikeTs_labels.append(
                [session_name, chan, chan_label, unit_no_in_channel,
                 unit_label, uuid, n_spikes, region])
        # Create DataFrame
        spike_df = pd.DataFrame(session_spikeTs_labels, columns=label_cols)
        return session_spikeTs_s, session_spikeTs_ms, spike_df
    except Exception as e:
        print(f"An error occurred: {e}")
        return [], [], pd.DataFrame(columns=label_cols)

