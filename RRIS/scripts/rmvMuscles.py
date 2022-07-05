from distutils.command.build_scripts import first_line_re
from email.policy import default
from ntpath import join
from re import sub

import xml.etree.ElementTree as ET
from dm_control import mjcf

class ConvertMusculoskeletalToJointPD():
    def __init__(self):
        self.mjcf_folder = '/home/sherwin/Desktop/O2MConverter/RRIS/data/Sample_Subject/Converted/SN475_Rajagopal_scaled_converted/'
        self.xml_name = 'SN475_Rajagopal_scaled_converted.xml'
        self.mjcf_file = self.mjcf_folder + self.xml_name
        self.save_path = self.mjcf_folder + 'noMusc_' + self.xml_name

        # Convert Musculoskeletal to Joint PD 
        self.RemoveDefaultClass()
        self.RemoveWorldBody()
        self.RemoveTendon()
        self.RemoveActuators()
        self.tree.write(self.save_path)

        # Add motor to all joints with no actuator for it
        self.AddActuators()

    # dm_control cannot read the MJCF file if the default class attribute is 'muscle' 
    # so the entire class is removed
    def RemoveDefaultClass(self):
        self.tree = ET.parse(self.mjcf_file)
        self.root = self.tree.getroot()

        for child in self.root:

            # Default Tags
            if child.tag == 'default':
                for sub_child in child.findall('tendon'): 
                    print("Removing Default/Tendon")
                    child.remove(sub_child)

                for sub_child in child.findall('site'):
                    print("Removing Default/Site")
                    child.remove(sub_child)

                for sub_child in child.findall('default'):
                    if sub_child.tag == 'default':
                        if sub_child.attrib.get('class') == 'muscle':
                            print("Removing Default/Muscle")
                            child.remove(sub_child)

        
    def RemoveWorldBody(self):
        for child in self.root.findall('worldbody'):
            for sub_child in child.findall('body'):

                # Remove sites in all 1st levels
                for sub2_child in sub_child.findall("site"):
                    sub_child.remove(sub2_child)

                for sub2_child in sub_child.findall("body"):
                    # Remove sites in all 2nd levels
                    for sub3_child in sub2_child.findall('site'):
                        sub2_child.remove(sub3_child)

                    for sub3_child in sub2_child.findall('body'):
                        # Remove sites in all 3nd levels
                        for sub4_child in sub3_child.findall('site'):
                            sub3_child.remove(sub4_child) 

                        for sub4_child in sub3_child.findall('body'):
                            # Remove sites in all 4th levels
                            for sub5_child in sub4_child.findall('site'):
                                sub4_child.remove(sub5_child)

                            for sub5_child in sub4_child.findall('body'):
                                # Remove sites in all 5th levels
                                for sub6_child in sub5_child.findall('site'):
                                    sub5_child.remove(sub6_child)

                                for sub6_child in sub5_child.findall('body'):
                                    # Remove sites in all 6th levels
                                    for sub7_child in sub6_child.findall('site'):
                                        sub6_child.remove(sub7_child)

    def RemoveTendon(self):
        for child in self.root:
            if child.tag == 'tendon':
                print("Removing Tendon")
                self.root.remove(child)

    def RemoveActuators(self):
        for child in self.root:
            if child.tag == 'actuator':                    
                for sub_child in child.findall('muscle'): 
                    child.remove(sub_child)        

    # Add Actuators for each joint
    # Rajagopal, Gait2392, Gait2354, Gait10DoF18Musc
        # Motors only upper limb cause there got no muscle actuators at the start
        # So need to add motors in lowerlimb if converting to joint torque morel

    # Pelvis TX, TY, TZ need to add actuators?
    def AddActuators(self):
        jointNames = []
        mjcf_model = mjcf.from_path(self.save_path)
        joints = mjcf_model.find_all('joint')
        actuator = mjcf_model.find_all('actuator')
        
        jointNames = []
        for i in joints:
            jointNames.append(i.name)

        actuatorJoints = []
        for i in actuator:
            actuatorJoints.append(i.joint.name)

        toBeAdded = list(set(jointNames) - set(actuatorJoints))

        tree = ET.parse(self.save_path)
        root = tree.getroot()
        
        for child in root:
            if child.tag == 'actuator':
                for joint in toBeAdded:
                    sub_child = ET.SubElement(child, 'motor')
                    sub_child.set('name', joint)
                    sub_child.set('joint', joint)
                    sub_child.set('class', 'motor')
                    sub_child.tail = "\n\t\t"
                    ET.dump(child)
        tree.write(self.save_path)

def main():
    rmvMuscle = ConvertMusculoskeletalToJointPD()

if __name__ == "__main__":
    main()