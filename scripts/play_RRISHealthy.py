'''
Simple playback function to play the selected model and motion
- No fanciful random start or anything, its just simple playback loop
1. Specify model file path
2. Specify motion file path
3. Plays motion on model
'''
from mujoco_py import load_model_from_path, MjSim, MjViewer
import pandas as pd
import math

if __name__ == "__main__":
    rris_o2m_path = "/media/sherwin/One Touch/RRIS_O2M"
    model_type = "/Rajagopal_Converted"
    model_file = rris_o2m_path + model_type + "/Models/main.xml"
    motion_file = rris_o2m_path + model_type + "/Motions/Healthy/SN306/csv/10m_01.csv"

    # Init Sim
    model = load_model_from_path(model_file)
    sim = MjSim(model)
    sim.model.opt.timestep = 0.002
    keyboard_callback = lambda key: key
    viewer = MjViewer(sim, keyboard_callback)

    # Init Motion
    df = pd.read_csv(motion_file)
    frame = 0

    print("Num Joints: ", sim.model.njnt)
    pelvis_translation = ["pelvis_tx", "pelvis_ty", "pelvis_tz"]

    for column in df:
        pos = df.iloc[frame][column]
        if column not in pelvis_translation:
            pos = math.radians(pos)
        id = sim.model.joint_name2id(column)
        sim.data.qpos[sim.model.jnt_qposadr[id]] = pos
        
    sim.step()

    while True:
        sim.step()
        viewer.render()
        keyboard = viewer.button_pressed
        
        if keyboard == 66: # Button B
            if frame == len(df.index):
                frame = 0
                sim.reset()
            else:
                for column in df:
                    pos = df.iloc[frame][column]
                    id = sim.model.joint_name2id(column)
                    sim.data.qpos[sim.model.jnt_qposadr[id]] = pos
                frame += 1

        if keyboard == 75:
            sim.reset()

