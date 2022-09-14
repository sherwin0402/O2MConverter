# General Math Functions -> Not specific to RL or MuJoCo
import numpy as np
import math as m
from scipy.spatial.transform import Rotation as R
import random

class MATHS():
    RAD_TO_DEG = 57.2957795
    DEG_TO_RAD = 1.0 / RAD_TO_DEG
    INVALID_IDX = -1
    
    #########
    # General
    #########
    def rad_to_deg( data):
        return m.degrees(data)
    def deg_to_rad( data):
        return m.radians(data)
    def phaseShift( data, shiftValue):
        return shiftValue+data
    def m_to_mm( data):
        return float(1000*data)
    def mm_to_m( data):
        return float(0.001*data)
    def global_to_local( globalData, localData):
        return globalData-localData
    def local_to_global( globalData, localData):
        return localData - globalData
    def average( listOfNum):
        return sum(listOfNum)/len(listOfNum)

    # Euler & Quarternion Transformation
    def quat2Eul(x,y,z,w):
        rot = R.from_quat([x,y,z,w])
        rot_euler = rot.as_euler('xyz', degrees=False)
        return rot_euler
    def eul2Quat(x,y,z):
        rot = R.from_euler('xyz', [x,y,z])
        rot_quat = rot.as_quat()
        return rot_quat #xyzw format
    
    def get_num_of_values_of_dict(my_dict):
        count = 0
        for key, value in my_dict.items():
            count = count + len(value)
        return count
    
    def dict_values_to_np_arr(my_dict):
        temp = []
        for value in my_dict.values():
            temp.extend(value)
        return np.array(temp)

    ###########
    # Rotations
    ###########
    # Rotate around X-axis
    def Rx3D( oldX, oldY, oldZ, theta):
        theta = m.radians(theta)
        val = [
            oldX*1 + oldY*0 + oldZ*0,
            oldX*0 + oldY*m.cos(theta) + oldZ*m.sin(theta),
            oldX*0 + oldY*(-m.sin(theta)) + oldZ*m.cos(theta)
        ]
        return val
    # Rotate around Y-axis
    def Ry3D( oldX, oldY, oldZ, theta):
        theta = m.radians(theta)
        val = [
            oldX*m.cos(theta) + oldY*0 + oldZ*(-m.sin(theta)),
            oldX*0 + oldY*1 + oldZ*0,
            oldX*m.sin(theta) + oldY*0 + oldZ*m.cos(theta)
        ]
        return val
    # Rotate around Z-axis
    def Rz3D( oldX, oldY, oldZ, theta):
        theta = m.radians(theta)
        val = [
            oldX*m.cos(theta) + oldY*m.sin(theta) + oldZ*0,
            oldX*(-m.sin(theta)) + oldY*m.cos(theta) + oldZ*0,
            oldX*0 + oldY*0 + oldZ*1
        ]
        return val

    # https://www.gamedev.net/tutorials/programming/general-and-gameplay-programming/a-brief-introduction-to-lerp-r4954/
    def lerp( x, y, t):
        return (1 - t) * x + t * y

    def log_lerp( x, y, t):
        return np.exp(MATHS.lerp(np.log(x), np.log(y), t))

    def flatten( arr_list):
        return np.concatenate([np.reshape(a, [-1]) for a in arr_list], axis=0)

    def flip_coin( p):
        rand_num = np.random.binomial(1, p, 1)
        return rand_num[0] == 1

##############
# Random Seeds
##############
class Rand():
    def __init__(self, seed=None):
        self.set_global_seeds(seed)

    def set_global_seeds(self, seed=None): # Previously from util.py

        if seed == None:
            seed = np.random.randint(np.iinfo(np.int32).max)

        try:
            import tensorflow as tf
        except ImportError:
            pass
        else:
            tf.set_random_seed(seed)
        np.random.seed(seed)
        random.seed(seed)

        print("----------------------")
        print("----------------------")
        print("----------------------")
        print("Setting Global Seeds")
        return

    # Random Floating Point Number a <= Value <= b
    def _RandDouble(self, a, b): 
        self.mRandDoubleDist = random.uniform(a,b)
        return self.mRandDoubleDist
    
    # Normal Distribution of type Float
    def _RandDoubleDistNorm(self, mu, sigma):
        self.mRandDoubleDistNorm = random.normalvariate(mu, sigma)
        return self.mRandDoublmRandDoubleDistNormeDist

    # Random Integer Point Number a <= Value <= b
    def _RandInt(self, a, b):
        self.mRandIntDist = random.randint(a,b)
        return self.mRandIntDist

    # Random Unsigned Integer Point Number 0 <= Value <= b
    def _RandUint(self, b):
        self.mRandUintDist = random.randint(0,b)
        return self.mRandUintDist