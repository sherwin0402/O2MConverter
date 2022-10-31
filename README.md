# RRIS_O2MConverter
## To do:
1. Set joint limits to be true once converted from MSK
2. Remove unecessary joints, bodies and information during simplification process
3. Make actuator limits to be in line with joint limits
4. Set order of actuators to be the same as joints
5. Duplicate the model using torque actuation

## Install
```bash
# Clone this repository
conda env create --name O2M --file=conda_env.yml
```
## How to Use : Converting Model
OSIM -> MJCF (MSK)
```bash
conda activate O2M
export MJLIB_PATH=/home/sherwin/.mujoco/mujoco-2.1.1/lib/libmujoco.so.2.1.1
conda env export | grep -v "^prefix: " > environment.yml

# python O2MConverter.py <OSIM_FILE> <LOCATION_TO_SAVE> <LOCATION_WHERE_GEOM_FILES_ARE>
python O2MConverter.py RRIS/data/Sample_Subject/Opensim_Output/SN475/SN475_Rajagopal_scaled.osim RRIS/data/Sample_Subject/Converted RRIS/data/osim_models/Rajagopal2015/Geometry
```

MJCF (MSK -> SK)
- This process deletes all muscles, sites and all other info related to muscles
- It then reads all joint information to add actuator for each joint.
- Note: Current logic does not work well with arm26 and wrist

```bash
conda activate O2M
export MJLIB_PATH=/home/sherwin/.mujoco/mujoco-2.1.1/lib/libmujoco.so.2.1.1
cd scripts
# Note: Add the intended MJCF MSK file to be edited here
python rmvMuscles.py
```

MJCF (SK -> Simplified SK)
- This process simplifies the model. It removes redundant joints, bodies.
    - Patella body and joints removed. Mass of patella shifted to the knee
    - All joints not classified as important is removed everywhere in the code
    - Joint limits have been set to true
    - Actuator limits follow joint limits
    - Order of actuators changed to match those of the joints
    - Duplicate model with "motor" actuation setup.

## How to Use: Preparing motions
- Just need to store the motion accordingly in the appropriate folder
```bash
cd scripts
python prep_motion.py
```

### Playing Scaled Model & Motion
```bash
conda activate O2M
export LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libGLEW.so
cd scripts
python play_RRISHealthy.py
```

# Not working at the moment: Dynamics Portion of O2M
## Converting model with parameter optimization
```bash
conda env create --name O2MTesting --file=conda_env_for_testing.yml
pip install git+git://github.com/deepmind/dm_control.git
```

**Running**
- Model Geometry is same across, so just refer to a single geometry folder located in osim_models
```bash
conda activate O2MTesting

# Input True as 4th Argument
python O2MConverter.py RRIS/data/Sample_Subject/Opensim_Output/SN475/SN475_Rajagopal_scaled.osim RRIS/data/Sample_Subject/Converted_Testing RRIS/data/osim_models/Rajagopal2015/Geometry true
```

**Sample Run on Parameter Optimization**

gait10dof18musc
- First rename the gait10dof18musc in tests as _old
```bash
# Step 1 - Convert to MJCF from OSIM - 4th argument is True
python O2MConverter.py models/opensim/Gait10dof18musc/gait10dof18musc_for_testing.osim models/converted/gait10dof18musc_for_testing_converted models/opensim/Gait10dof18musc/Geometry true
# Step 2 - Add OpenSim Forward Dynamics Setup XML File
# Step 3 - Add OpenSim Initial States File (Run OpenSim Forward Dynamics and use output file with states)
# Step 4 - Create new template from EnvTemplate Class

# Step 5 - Run tests/generate_controls.py NUM_MUSCLE_EXCITATION_SETS MAX_AMPLITUDE
python generate_controls.py gait10dof18musc 100 1

# Step 6 - Run tests/run_opensim_simulations.py
python run_opensim_simulations.py gait10dof18musc
s
# Step 7 - Run tests/optimize_mujoco_parameters.py
python optimize_mujoco_parameters.py gait10dof18musc

# Step 8 - Load optimized parameters

```