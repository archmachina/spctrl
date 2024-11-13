import argparse
import logging
import sys
import logging
import signal
import yaml

import spctrl.core as core


logger = logging.getLogger(__name__)
supervisor = None

def signal_usr1(sig, frame):
    # Reload supervisor configuration on a SIGUSR1 signal
    logger.debug("Received SIGUSR1")
    if supervisor is None:
        return

    logger.debug("Reloading supervisor configuration")
    try:
        supervisor.reload_config()
    except Exception as e:
        logger.error("Error reloading configuration")
        logger.error(e)

def main():
    """ """

    parser = argparse.ArgumentParser(
        prog="spctrl", description="Simple Process Control", exit_on_error=False
    )

    parser.add_argument(
        "-c",
        "--config",
        dest="config",
        help="Config file for spctrl",
    )

    parser.add_argument(
        "-d", action="store_true", dest="debug", help="Enable debug output"
    )

    args = parser.parse_args()

    config_file = args.config
    debug = args.debug

    level = logging.WARNING
    if debug:
        level = logging.DEBUG

    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")

    ret = 0

    try:
        # Configure process to reload configuration on SIGUSR1
        signal.signal(signal.SIGUSR1, signal_usr1)

        logger.debug("Creating supervisor")
        supervisor = core.Supervisor(config_file)

        logger.debug("Waiting on supervisor")
        supervisor.wait()

    except KeyboardInterrupt as e:
        pass

    except BrokenPipeError as e:
        try:
            print("Broken Pipe", file=sys.stderr)
            if not sys.stderr.closed:
                sys.stderr.close()
        except:
            pass

        ret = 1

    except Exception as e:  # pylint: disable=broad-exception-caught
        if debug:
            logger.error(e, exc_info=True, stack_info=True)
        else:
            logger.error(e)

        ret = 1

    try:
        logger.debug("Calling terminate for supervisor")
        supervisor.terminate()
    except Exception as e: # pylint: disable=broad-exception-caught
        ret = 1

    try:
        sys.stdout.flush()
    except Exception as e: # pylint: disable=broad-exception-caught
        ret = 1

    sys.exit(ret)

