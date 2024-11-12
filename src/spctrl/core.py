import os
import yaml
import pathlib
import logging
import obslib
import sys
import copy
import enum
import time

logger = logging.getLogger(__name__)

class SupervisorProcessDeps:
    def __init__(self, definition, process_config):
        if not isinstance(definition, dict):
            raise ValueError("Invalid definition passed to SupervisorProcessDeps")

        if not isinstance(process_config, SupervisorProcessConfig):
            raise ValueError("Invalid SupervisorProcessConfig passed to SupervisorProcessDeps")

        # Name of the dependency
        self.name = obslib.extract_property(definition, "name")
        self.name = obslib.coerce_value(self.name, str)

        # Determine if this is a strict dependency
        self.strict = obslib.extract_property(definition, "strict", optional=True, default=False)
        self.strict = obslib.coerce_value(self.strict, bool)

class SupervisorProcessState:
    def __init__(self, config):
        if not isinstance(config, SupervisorProcessConfig):
            raise ValueError("Invalid SupervisorProcessConfig passed to SupervisorProcessState")

        self.config = config

    def stop(self):
        logger.debug(f"Stopping process: {self.config.name}")
        pass

    def start(self):
        logger.debug(f"Starting process: {self.config.name}")
        pass

    def restart(self):
        logger.debug(f"Restarting process: {self.config.name}")
        pass

class SupervisorProcessConfig:
    def __init__(self, name, config, definition):
        if not isinstance(name, str) or name == "":
            raise ValueError("Invalid name passed to SupervisorProcessConfig")

        if not isinstance(config, SupervisorConfig):
            raise ValueError("Invalid SupervisorConfig passed to SupervisorProcessConfig")

        if not isinstance(definition, dict):
            raise ValueError("Invalid definition passed to SupervisorProcessConfig")

        self.name = name

        # Start with the global vars from the SupervisorConfig
        working_vars = copy.deepcopy(config.global_vars)

        # Extract any vars from the current process object and update the working vars
        process_vars = obslib.extract_property(definition, "vars", optional=True, default={})
        process_vars = obslib.coerce_value(process_vars, (dict, type(None)))
        if process_vars is None:
            process_vars = {}

        working_vars.update(obslib.extract_property(definition, "vars", optional=True, default={}))

        # Flatten the vars. i.e. resolve any references
        working_vars = obslib.eval_vars(working_vars)

        # Create a session object, which is used to resolve other references
        session = obslib.Session(template_vars=working_vars)

        # Extract the command to run
        self.command = obslib.extract_property(definition, "command")
        self.command = session.resolve(self.command, str)

        # Extract environment vars

        # Extract shell

        # Extract restart config

        # Extract restart delay

        # Extract failure condition

        # Extract termination command

        # Extract dependencies
        self.dependencies = obslib.extract_property(definition, "dependencies", optional=True, default=[])
        self.dependencies = session.resolve(self.dependencies, list)

        if self.dependencies is None:
            self.dependencies = []

        if not all([isinstance(x, dict) for x in self.dependencies]):
            raise ValueError("Invalid members in process dependencies. Must be dictionaries")

        # Create a dependency object for each dependency
        self.dependencies = [SupervisorProcessDeps(x, self) for x in self.dependencies]

        # Extract log file

        # Make sure there are no remaining keys on the process object. i.e. unknown properties
        if len(definition.keys()) > 0:
            raise ValueError(f"Unknown properties on process: {definition.keys()}")

    def is_equal(self, process_config):
        """
        Compare the current process config against another process configure to
        determine equality
        Return True if both configs are functionally identical
        """
        if not isinstance(process_config, SupervisorProcessConfig):
            raise ValueError("Invalid process config passed to is_equal")

        if self == process_config:
            return True

        # Check the parameters for the current process config against the supplied process config
        # TODO

        return False

class SupervisorConfig:
    def __init__(self, config_path):
        if not isinstance(config_path, str) or config_path == "":
            raise ValueError("Invalid config_path supplied to SupervisorConfig")

        # Read the content of the config file
        with open(config_path, "r") as file:
            new_config = yaml.safe_load(file.read())

        if new_config is None:
            new_config = {}

        # Make sure we have a top level dictionary
        if not isinstance(new_config, dict):
            raise ValueError("Invalid content for configuration. Must be a top level dictionary")

        # Read vars from the configuration
        self.global_vars = obslib.extract_property(new_config, "vars", optional=True, default={})
        self.global_vars = obslib.coerce_value(self.global_vars, (dict, type(None)))
        if self.global_vars is None:
            self.global_vars = {}

        # Flatten vars at this point
        self.global_vars = obslib.eval_vars(self.global_vars)
        
        # Read process configuration
        processes = obslib.extract_property(new_config, "processes")
        processes = obslib.coerce_value(processes, dict)

        # Create SupervisorProcessConfig objects for all processes defined in the configuration
        # SupervisorProcessConfig performs the parsing of the configuration
        self.processes = dict()
        for process_name in processes:
            self.processes[process_name] = SupervisorProcessConfig(process_name, self, processes[process_name])

        logger.debug(f"Processes: {list(self.processes.keys())}")

        # Make sure there are no unknown top level keys in the configuration
        if len(new_config.keys()) > 0:
            raise ValueError(f"Unknown top level keys in configuration: {new_config.keys()}")

        # Create an order for starting of processes, based on dependencies
        self.start_order = list()
        process_names = list(self.processes.keys())
        while len(process_names) > 0:

            # Find processes with met dependencies
            process_match = list()
            for process_name in process_names:
                if all([(x.name in self.start_order) for x in self.processes[process_name].dependencies]):
                    process_match.append(process_name)
                    self.start_order.append(process_name)

            # If matches found, remove from the process_names list
            if len(process_match) > 0:
                for process_name in process_match:
                    process_names.remove(process_name)

                # Restart the loop, if we were able to find something
                continue

            # We iterated through the processes, but none had met dependencies, so
            # raise an error here
            raise ValueError(
                f"Start order for processes cannot be determined. Unsolvable dependencies for: {process_names}"
            )

        logger.debug(f"Calculated start order: {self.start_order}")


class Supervisor:
    def __init__(self, config_path):
        if not isinstance(config_path, str) or config_path is None:
            raise ValueError("Invalid config path passed to Supervisor")

        self.config_path = config_path

        # If the target is a directory, then read from spctrl.yaml
        # in that directory instead.
        if os.path.isdir(self.config_path):
            self.config_path = os.path.join(self.config_path, "spctrl.yaml")

        logger.debug(f"Using '{self.config_path}' for config path")

        # Load the initial configuration
        self.config = SupervisorConfig(self.config_path)
        self._should_reload_config = False

    def reload_config(self):
        # Clear the current config to force a reload
        self._should_reload_config = True

    def _prune(self, config, states):
        # Find any process states that are now out of scope and stop them
        for process_name in states.keys():
            if process_name not in config.processes.keys():
                logger.debug(f"Process out of scope: {process_name}. Stopping")
                states[process_name].stop()
                states.remove(process_name)

    def _process_loop(self, config, states):
        # Reconcile any process state, based on start order
        for process_name in config.start_order:

            # Create a process state if it is missing
            if process_name not in states:
                states[process_name] = SupervisorProcessState(config.processes[process_name])

            # Check if the config for the process has changed
            if not states[process_name].config.is_equal(config.processes[process_name]):
                # Stop the process and replace the state with a new state
                states[process_name].stop()
                states[process_name] = SupervisorProcessState(config.processes[process_name])

            # The configs are either already the same or functionally identical at this point.
            # If the configs are only functionally identical, update it so that it
            # is referencing the correct SupervisorConfig parent
            if states[process_name].config != config.processes[process_name]:
                states[process_name].config = config.processes[process_name]

            # Start the process - ignored if the process is already running
            states[process_name].start()

    def run(self):
        config = None
        states = dict()

        while True:
            # If the configuration is missing, reload it here
            if self._should_reload_config:
                self._should_reload_config = False
                try:
                    self.config = SupervisorConfig(self.config_path)
                except Exception as e:
                    logger.error("Error reloading configuration")
                    logger.error(e)

            # Call prune on out of scope processes, if there is a newer config
            if self.config is not None and self.config != config:
                logger.debug("Running against new configuration")
                config = self.config
                try:
                    self._prune(config, states)
                except Exception as e:
                    logger.error("Error pruning out of scope processes")
                    logger.error(e)

            # Work through the process configuration against the current process state
            if config is not None:
                try:
                    self._process_loop(config, states)
                except Exception as e:
                    logger.error("Error running process loop")
                    logger.error(e)

            # Restart process loop after 5 seconds
            time.sleep(5)

    def terminate(self):
        pass

