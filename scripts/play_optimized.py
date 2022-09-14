from tkinter.messagebox import NO
from xml.etree.ElementTree import TreeBuilder
from mujoco_py import load_model_from_path, MjSim, MjViewer
import Utils

# Model File as per EnvTemplate Class
model_file = "models/converted/gait10dof18musc_for_testing_converted/gait10dof18musc_for_testing_converted.xml"
optimized_file = "tests/gait10dof18musc/output/data.pckl"

class simulation():
    def __init__(self):

        self.model = load_model_from_path(model_file)
        self.sim = MjSim(self.model)
        self.viewer = MjViewer(self.sim)

        data_dict = Utils.load_data(optimized_file)

        while True:
            self.sim.step()
            self.viewer.render()

            pass

if __name__ == "__main__":
    sim = simulation()