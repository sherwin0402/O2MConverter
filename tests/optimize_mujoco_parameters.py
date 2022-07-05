import sys
sys.path.append('/home/sherwin/Desktop/O2MConverter')

from tests.envs import EnvFactory
import mujoco_py
import os
import Utils
import pandas as pd
import random
import math
import numpy as np
import cma
import skvideo
import pickle
import matplotlib.pyplot as pp
import sys
from multiprocessing import Queue, Process
from copy import deepcopy


def get_run_info(run_folder):
    output_file = os.path.join(run_folder, "output")
    if os.path.isfile(output_file):
        run_info = pd.read_csv(output_file, delimiter=", ", header=0, engine="python")
    return run_info


def is_unique(values):
    return (values - values[0] < 1e-6).all()


def collect_data_from_runs(env):

    # Get sub-folders
    runs = os.listdir(env.forward_dynamics_folder)

    # Go through all runs
    data = []
    for run in runs:

        # Get run folder
        run_folder = os.path.join(env.forward_dynamics_folder, run)

        # Make sure both controls and states exist
        if not os.path.exists(os.path.join(run_folder, 'controls.sto')) \
            or not os.path.exists(os.path.join(run_folder, 'FDS_states.sto')):
            continue

        # Get controls
        controls, ctrl_hdr = Utils.parse_sto_file(os.path.join(run_folder, "controls.sto"))

        # Get states
        states, state_hdr = Utils.parse_sto_file(os.path.join(run_folder, "FDS_states.sto"))

        # We're interested only in a subset of states
        state_names = list(states)

        # Parse state names
        parsed_state_names = []
        for state_name in state_names:
            p = state_name.split("/")
            if p[-1] == "value":
                parsed_state_names.append(p[1])
            elif p[-1] == "speed":
                parsed_state_names.append(f"{p[1]}_speed")
            else:
                parsed_state_names.append(state_name)


        # Rename states
        states.columns = parsed_state_names

        # Check that initial states are correct (OpenSim forward tool seems to ignore initial states
        # of locked joints); if initial states do not match, then trajectories in mujoco will start
        # from incorrect states
        if env.initial_states is not None and "joints" in env.initial_states:
            for state_name in env.initial_states["joints"]:
                if abs(states[state_name][0] - env.initial_states["joints"][state_name]["qpos"]) > 1e-5:
                    raise ValueError(f"Initial states do not match for state {state_name}: {states[state_name][0]} vs {env.initial_states['joints'][state_name]['qpos']}")

        # Filter and reorder states
        qpos = states.filter(items=env.target_states)
        qpos = qpos[env.target_states]

        # Filter, reorder, and rename states
        qvel = states.filter(items=[f"{x}_speed" for x in env.target_states])
        qvel = qvel[[f"{x}_speed" for x in env.target_states]]
        qvel.columns = env.target_states

        # Convert into radians if needed
        if state_hdr["inDegrees"] == "yes":
            qvel.values *= np.pi/180


        # Get number of evaluations (forward steps); note that the last timestep isn't simulated
        num_evals = len(qpos) - 1

        # Reindex controls if they were generated with a different timestep
        if env.opensim_timestep is not None and env.opensim_timestep != env.timestep:
            controls = Utils.reindex_dataframe(controls, np.arange(0, controls.index.values[-1], env.timestep))

        # Reindex qpos and qvel
        qpos = Utils.reindex_dataframe(qpos, np.arange(env.timestep, controls.index.values[-1]+2*env.timestep, env.timestep))
        qvel = Utils.reindex_dataframe(qvel, np.arange(env.timestep, controls.index.values[-1]+2*env.timestep, env.timestep))

        # Get state values and state names
        qpos_values = qpos.values
        qvel_values = qvel.values
        state_names = env.target_states

        # Don't use this data if there were nan states
        if np.any(np.isnan(qpos.values)) or np.any(np.isnan(qvel.values)) \
            or np.max(qpos.values) > 20 or np.min(qpos.values) < -20:
            success = 0
            qpos_values = []
            qvel_values = []
            state_names = []
            num_evals = 0
        else:
            success = 1

        data.append({"qpos": qpos_values, "qvel": qvel_values, "controls": controls.values,
                     "state_names": state_names, "muscle_names": list(controls),
                     "timestep": env.timestep, "success": success, "run": run, "num_evals": num_evals})

    return data

class Worker:

    def __init__(self, model_path, input, output, data, params, target_state_indices, initial_states):

        # Initialise MuJoCo with the converted model
        model = mujoco_py.load_model_from_path(model_path)

        # Initialise simulation
        self.sim = mujoco_py.MjSim(model)

        # Check muscle order
        Utils.check_muscle_order(model, data)
        self.data = data

        self.params = params

        # Get indices of target states
        self.target_state_indices = target_state_indices

        # Get initial states
        self.initial_states = initial_states

        self.input = input
        self.output = output

    def process(self):
        while True:

            inp = self.input.get()
            if inp is None:
                break
            else:
                out = self.run_simulation(parameters=inp[1], batch_idxs=inp[2], highest_error_so_far=inp[3])
                self.output.put((inp[0], out))

    def run_simulation(self, parameters, batch_idxs, highest_error_so_far):

        # Set parameters
        self.params.set_values_to_model(self.sim.model, np.exp(parameters))
        params_cost = self.params.get_cost(parameters, np.exp)

        # Go through all simulations in batch
        error = np.zeros((len(batch_idxs),))
        error_qpos = np.zeros_like(error)
        error_qvel = np.zeros_like(error)
        for idx, run_idx in enumerate(batch_idxs):
            qpos = self.data[run_idx]["qpos"]
            qvel = self.data[run_idx]["qvel"]
            controls = self.data[run_idx]["controls"]
            timestep = self.data[run_idx]["timestep"]

            # Initialise sim
            Utils.initialise_simulation(self.sim, self.initial_states, timestep)

            # Run simulation
            sim_success = True
            try:
                sim_states = Utils.run_simulation(self.sim, controls)
            except mujoco_py.builder.MujocoException:
                # Simulation failed
                sim_success = False

            if sim_success:
                # Calculate joint errors
                error_qpos[idx] = np.sum(Utils.estimate_error(qpos, sim_states["qpos"][:, self.target_state_indices]))
                error_qvel[idx] = np.sum(Utils.estimate_error(qvel, sim_states["qvel"][:, self.target_state_indices]))
                error[idx] = error_qpos[idx] + 0.01 * error_qvel[idx]
                if error[idx] > highest_error_so_far:
                    highest_error_so_far = error[idx]
            else:
                error_qpos[idx] = 2 * highest_error_so_far
                error_qvel[idx] = 2 * highest_error_so_far
                error[idx] = error_qpos[idx] + 0.01 * error_qvel[idx]

        return {"errors_qpos": error_qpos, "errors_qvel": error_qvel, "errors": error,
                "highest_error_so_far": highest_error_so_far, "params_cost": params_cost}



def do_optimization(env, data):

    # Initialise MuJoCo with the converted model
    model = mujoco_py.load_model_from_path(env.mujoco_model_file)

    # Initialise simulation
    sim = mujoco_py.MjSim(model)

    # Check muscle order
    Utils.check_muscle_order(model, data)

    # Get indices of target states
    target_state_indices = Utils.get_target_state_indices(model, env)

    # Get initial states
    initial_states = Utils.get_initial_states(model, env)

    #viewer = mujoco_py.MjViewer(sim)

    # Go through training data once to calculate error with default parameters
    default_error_qpos = np.zeros((len(data),))
    default_error_qvel = np.zeros_like(default_error_qpos)
    for run_idx in range(len(data)):
        qpos = data[run_idx]["qpos"]
        qvel = data[run_idx]["qvel"]
        controls = data[run_idx]["controls"]
        timestep = data[run_idx]["timestep"]

        # Initialise sim
        Utils.initialise_simulation(sim, initial_states, timestep)

        # Run simulation
        sim_states = Utils.run_simulation(sim, controls)

        # Calculate joint errors
        default_error_qpos[run_idx] = np.sum(Utils.estimate_error(qpos, sim_states["qpos"][:, target_state_indices]))
        default_error_qvel[run_idx] = np.sum(Utils.estimate_error(qvel, sim_states["qvel"][:, target_state_indices]))

    # Optimize damping and solimp width for all joints that don't depend on another joint or aren't locked, regardless
    # of whether they are limited or not (if they're not limited then solimp width can take any values)
    joint_idxs = list(set(range(len(model.joint_names))) - set(model.eq_obj1id[np.asarray(model.eq_active, dtype=bool)]))
    #njoints = len(joint_idxs)
    muscle_idxs = np.where(model.actuator_trntype==3)[0]
    motor_idxs = np.where(model.actuator_trntype==0)[0]
    assert len(set(model.actuator_trntype) - {0, 3}) == 0, "Unidentified actuators in model"

    # Get initial values for params
    niter = 20000
    sigma = 1.0
    params = Utils.Parameters(motor_idxs, muscle_idxs, joint_idxs, [1, 6, 0.5])
    #params = [5] * nmuscles + [1] * (2 * nmuscles + 2 * njoints)

    # Initialise optimizer
    opts = {"popsize": env.param_optim_pop_size, "maxiter": niter, "CMA_diagonal": True}
    optimizer = cma.CMAEvolutionStrategy(params.get_values(), sigma, opts)
    nbatch = 40#len(data)
    highest_error_so_far = 1e6

    # Keep track of errors
    history = np.empty((niter,))
    history.fill(np.nan)

    # Initialise plots
    pp.ion()
    fig1 = pp.figure(1, figsize=(10, 5))
    fig1.gca().plot([0, len(data)], [1, 1], 'k--')
    bars_qpos = fig1.gca().bar(np.arange(len(data)), [0]*len(data))
    fig1.gca().axis([0, len(data), 0, 1.2])

    fig2 = pp.figure(2, figsize=(10, 5))
    fig2.gca().plot([0, len(data)], [1, 1], 'k--')
    bars_qvel = fig2.gca().bar(np.arange(len(data)), [0]*len(data))
    fig2.gca().axis([0, len(data), 0, 1.2])

    fig3 = pp.figure(3, figsize=(10, 5))
    fig3.gca().plot([0, niter], [default_error_qpos.sum(), default_error_qpos.sum()], 'k--')
    line, = fig3.gca().plot(np.arange(niter), [0]*niter)
    fig3.gca().axis([0, niter, 0, 1.1*default_error_qpos.sum()])

    num_workers = 1
    procs = []
    input_queue = Queue()
    output_queue = Queue()
    for _ in range(num_workers):
        new_worker = Worker(env.mujoco_model_file, input_queue, output_queue, data, deepcopy(params),
                            target_state_indices, initial_states)
        procs.append(Process(target=new_worker.process))

    for proc in procs:
        proc.start()

    while not optimizer.stop():
        solutions = optimizer.ask()

        # Test solutions on a batch of runs
        batch_idxs = random.sample(list(np.arange(len(data))), nbatch)

        errors = np.zeros((len(batch_idxs), len(solutions)))
        errors_qpos = np.zeros_like(errors)
        errors_qvel = np.zeros_like(errors)
        params_cost = np.zeros((len(solutions)))

        for idx, solution in enumerate(solutions):
            input_queue.put((idx, solution, batch_idxs, highest_error_so_far))

        order = []
        while len(order) < opts["popsize"]:
            c = output_queue.get()
            errors[:, c[0]] = c[1]["errors"]
            errors_qpos[:, c[0]] = c[1]["errors_qpos"]
            errors_qvel[:, c[0]] = c[1]["errors_qvel"]
            params_cost[c[0]] = c[1]["params_cost"]
            if c[1]["highest_error_so_far"] > highest_error_so_far:
                highest_error_so_far = c[1]["highest_error_so_far"]
            order.append(c[0])

        # Use sum of errors over runs as fitness, and calculate mean error for each run
        fitness = errors.mean(axis=0) +  0.001*params_cost

        # Plot mean error per run as a percentage of default error
        prc = np.mean(errors_qpos, axis=1) / default_error_qpos[batch_idxs]
        for bar_idx, y in zip(batch_idxs, prc):
            bars_qpos[bar_idx].set_height(y)
        fig1.canvas.draw()
        fig1.canvas.flush_events()

        prc = np.mean(errors_qvel, axis=1) / default_error_qvel[batch_idxs]
        for bar_idx, y in zip(batch_idxs, prc):
            bars_qvel[bar_idx].set_height(y)
        fig2.canvas.draw()
        fig2.canvas.flush_events()

        # Plot history of mean fitness
        history[optimizer.countiter] = np.mean(fitness)
        line.set_ydata(history)
        fig3.gca().axis([0, optimizer.countiter, 0, 1.1*max(history)])
        fig3.canvas.draw()
        fig3.canvas.flush_events()

        # Ignore failed runs / solutions
        #valid_idxs = np.where(np.isfinite(fitness))[0]

        optimizer.tell(solutions, fitness)
        optimizer.disp()

        # Save every now and then
        if optimizer.countiter % 100 == 0:
            params.set_values(np.exp(optimizer.result.xfavorite))
            with open(env.params_file, 'wb') as f:
                pickle.dump([params, history], f)
            fig1.savefig(os.path.join(os.path.dirname(env.params_file), 'percentage.png'))
            fig2.savefig(os.path.join(os.path.dirname(env.params_file), 'history.png'))

    for _ in range(num_workers):
        input_queue.put(None)
    for proc in procs:
        proc.join()

    # One last save
    params.set_values(np.exp(optimizer.result.xfavorite))
    with open(env.params_file, 'wb') as f:
        pickle.dump([params, history], f)
    fig1.savefig(os.path.join(os.path.dirname(env.params_file), 'percentage.png'))
    fig2.savefig(os.path.join(os.path.dirname(env.params_file), 'history.png'))


def main(model_name, data_file=None):

    # Get env
    env = EnvFactory.get(model_name)

    # Collect states and controls from successful runs
    data = collect_data_from_runs(env)

    # Divide successful runs into training and testing sets
    success_idxs = []
    for run_idx in range(len(data)):
        if data[run_idx]["success"]:
            success_idxs.append(run_idx)

    # If data_file is given, use its train and test indices
    if data_file is not None:
        D = Utils.load_data(data_file)
        train_idxs = D["train_idxs"]
        test_idxs = D["test_idxs"]
    else:
        # Use 80% of runs for training
        k = math.ceil(0.8*len(success_idxs))
        train_idxs = random.sample(success_idxs, k)
        test_idxs = list(set(success_idxs) - set(train_idxs))

    # Get training data
    train_set = [data[idx] for idx in train_idxs]

    # Make sure output folder exists
    os.makedirs(os.path.dirname(env.data_file), exist_ok=True)
    with open(env.data_file, 'wb') as f:
        pickle.dump([data, train_idxs, test_idxs], f)

    # Do optimization with CMA-ES
    do_optimization(env, train_set)


if __name__ == "__main__":

    # If we're optimizing mobl_arms_no_wrap, use the same train/test indices as mobl_arms
    model_name = sys.argv[1]
    if model_name == "MoBL_ARMS_no_wrap":
        data_file = EnvFactory.get("MoBL_ARMS").data_file
    else:
        data_file = None

    main(model_name, data_file)
