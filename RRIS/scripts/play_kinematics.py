from jinja2 import ModuleLoader
from mujoco_py import load_model_from_path, MjSim, MjViewer
import pandas as pd
import math

if __name__ == "__main__":
    # model_file = "/home/sherwin/Desktop/O2MConverter/RRIS/data/Sample_Subject/Converted/SN475_Rajagopal_scaled_converted/noMusc_SN475_Rajagopal_scaled_converted.xml"
    model_file = "/home/sherwin/Desktop/O2MConverter/RRIS/data/Sample_Subject/Converted/SN475_Rajagopal_scaled_converted/SN475_Rajagopal_scaled_converted.xml"

    # motion_file = "/home/sherwin/Desktop/O2MConverter/RRIS/data/Sample_Subject/Opensim_Output/SN475/10m_05 (Dynamic 25)/IKResults_edited.csv"
    motion_file = "/home/sherwin/Desktop/O2MConverter/RRIS/data/Sample_Subject/Opensim_Output/SN475/10m_06 (Dynamic 26)/IKResults.csv"

    # Init Sim
    model = load_model_from_path(model_file)
    sim = MjSim(model)
    keyboard_callback = lambda key: key
    viewer = MjViewer(sim, keyboard_callback)

    # Init Motion
    df = pd.read_csv(motion_file)
    df.drop(labels="time", axis=1,inplace=True)
    counter = 0

    print("Num Joints: ", sim.model.njnt)
    # Read header, set QPOS of that header as initial pos using first frame

    # knee_angle_r_beta & knee_angle_l_beta deleted from motion dataframe (model motion namne mismatch)

    pelvis_translation = ["pelvis_tx", "pelvis_ty", "pelvis_tz"]

    for column in df:
        pos = df.iloc[counter][column]
        if column not in pelvis_translation:
            pos = math.radians(pos)
        id = sim.model.joint_name2id(column)
        sim.data.qpos[sim.model.jnt_qposadr[id]] = pos
        
    sim.step()

    while True:
        sim.step()
        viewer.render()
        keyboard = viewer.button_pressed
        
        if keyboard == 66:
            if counter == len(df.index):
                counter = 0
                sim.reset()
            else:
                for column in df:
                    pos = df.iloc[counter][column]
                    if column not in pelvis_translation:
                        pos = math.radians(pos)
                    id = sim.model.joint_name2id(column)
                    sim.data.qpos[sim.model.jnt_qposadr[id]] = pos
                counter += 1

        if keyboard == 75:
            sim.reset()