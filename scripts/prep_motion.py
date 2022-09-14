'''
Prepares the Motion Files -> Several types of Motion Files
1. AMP Original Motions -> only for AMP Humanoid
2. RRIS Healthy Subjects -> Rajagopal for now
3. RRIS Stroke Subjects

How it works for AMP Motions: 
- Not done yet

How it works for RRIS Healthy Subjects:
1. Reads the input folder
2. Iterates through the subjects in the input folder
3. Enters for the mot_files folder and read each .mot file
4. Converts to csv and save to csv folder
5. Generate datasets txt file for that subject
'''
from logging import root
import numpy
import pandas as pd
import json
import os
from pyquaternion import Quaternion

from maths import MATHS

class PrepareMotion():
    PELVIS_TRANSLATION = ["pelvis_tx", "pelvis_ty", "pelvis_tz"]

    def __init__(self):
        self.motionOrigin = "RRIS"

        self.rris_o2m_path = "/media/sherwin/One Touch/RRIS_O2M"
        self.model_type = "/Rajagopal_Converted/Motions"
        self.subject_category = "/Healthy"
        self.subject_folders = self.rris_o2m_path + self.model_type + self.subject_category
        
        self.iterate_through_subjects()

    def iterate_through_subjects(self):
        for subject in os.listdir(self.subject_folders):
            subject_clean_motions_file = []
            f = os.path.join(self.subject_folders, subject)

            mot_files = os.path.join(f, "mot_files")
            if os.path.exists(mot_files):
                for motion in os.listdir(mot_files):
                    f = os.path.join(mot_files, motion)
                    df = pd.read_csv(f, delimiter="\t", skiprows=6)

                    # Drop the time -> cause not necessary
                    df.drop(labels="time", axis=1, inplace=True)

                    # Drop data from dataframe if name cannot be found in list of joint names for the motion's model
                    # Drop knee_angle_r_beta & knee_angle_l_beta
                    # Cause converted rajagopal model don't have that joint name exactly
                    df.drop(labels="knee_angle_r_beta", axis=1, inplace=True)
                    df.drop(labels="knee_angle_l_beta", axis=1, inplace=True)
                    
                    # Convert angles to radians (excluding translation)
                    for column in df:
                        if column not in self.PELVIS_TRANSLATION:
                            df[column] = df[column].apply(lambda x: x*MATHS.DEG_TO_RAD)
                    
                    # Save cleaned motion data
                    out_folder = os.path.join(self.subject_folders, subject + "/csv")
                    os.makedirs(out_folder, exist_ok=True)
                    save_filename = out_folder + "/" + motion[:-4] + ".csv"
                    df.to_csv(save_filename, index=False)

                    subject_clean_motions_file.append(save_filename)
            
            # Create dataset txt file for each subject and all motion files associated with it
            motion_list = []
            for filepath in subject_clean_motions_file:
                temp_dict = {
                    "Weight": 1,
                    "File": filepath
                }
                motion_list.append(temp_dict)
            dataset = {"Motions": motion_list}
            with open(self.rris_o2m_path + self.model_type + "/Datasets/" + subject + ".txt", 'w') as fp:
                json.dump(dataset, fp, indent=2)

if __name__ == "__main__":
    prep = PrepareMotion()