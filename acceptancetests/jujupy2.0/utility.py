from contextlib import contextmanager
import errno
import logging
import os
import re
import sys
from time import (
    datetime,
    timedelta
)
import warnings


class LoggedException(BaseException):
    """Raised in place of an exception that has already been logged.

    This is a wrapper to avoid double-printing real Exceptions while still
    unwinding the stack appropriately.
    """
    def __init__(self, exception):
        self.exception = exception


class AgentsNotStarted(Exception):
    """Raise in place of a timeout when an agent is not started"""


class StatusNotMet(Exception):
    """General error for client not reaching status"""


class until_timeout:

    """Yields remaining number of seconds.  Stops when timeout is reached.

    :ivar timeout: Number of seconds to wait.
    """
    def __init__(self, timeout, start=None):
        self.timeout = timeout
        if start is None:
            start = self.now()
        self.start = start

    def __iter__(self):
        return self

    @staticmethod
    def now():
        return datetime.now()

    def __next__(self):
        return self.next()

    def next(self):
        elapsed = self.now() - self.start
        remaining = self.timeout - elapsed.total_seconds()
        if remaining <= 0:
            raise StopIteration
        return remaining


class GroupReporter:

    def __init__(self, stream, expected):
        self.stream = stream
        self.expected = expected
        self.last_group = None
        self.ticks = 0
        self.wrap_offset = 0
        self.wrap_width = 79

    def _write(self, string):
        self.stream.write(string)
        self.stream.flush()

    def finish(self):
        if self.last_group:
            self._write("\n")

    def update(self, group):
        if group == self.last_group:
            if (self.wrap_offset + self.ticks) % self.wrap_width == 0:
                self._write("\n")
            self._write("." if self.ticks or not self.wrap_offset else " .")
            self.ticks += 1
            return
        value_listing = []
        for value, entries in sorted(group.items()):
            if value == self.expected:
                continue
            value_listing.append('%s: %s' % (value, ', '.join(entries)))
        string = ' | '.join(value_listing)
        lead_length = len(string) + 1
        if self.last_group:
            string = "\n" + string
        self._write(string)
        self.last_group = group
        self.ticks = 0
        self.wrap_offset = lead_length if lead_length < self.wrap_width else 0


def get_bootstrap_args(self, args):
    """Return the bootstrap arguments for the substrate."""
    bs_args = [args.env,
               '--config', generate_testing_config(),
               '--default-model', args.temp_env_name]
    if args.upload_tools:
        if args.agent_version is not None:
            raise ValueError(
                'agent-version may not be given with upload-tools.')
        bs_args.insert(0, '--upload-tools')
    else:
        if args.agent_version is None:
            raise ValueError(
                'agent-version must be specified without upload-tools')
        bs_args.extend(['--agent-version', args.agent_version])
    if args.series is not None:
        bs_args.extend(['--bootstrap-series', args.series])
    if args.to is not None:
        bs_args.extend(['--to', args.to])
    if args.no_gui:
        bs_args.append('--no-gui')
    return bs_args


def generate_testing_config():
    """Generate general config for testing

    Create a temp-dir and temp yaml with config
    Load testing config to yaml
    return path to yaml as string
    """
    config_yaml = ''
    return config_yaml


def generate_default_clean_dir(temp_env_name):
    """Creates a new unique directory for logging and returns name"""
    logging.debug('Environment {}'.format(temp_env_name))
    test_name = temp_env_name.split('-')[0]
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    log_dir = os.path.join('/tmp', test_name, 'logs', timestamp)

    try:
        os.makedirs(log_dir)
        logging.info('Created logging directory {}'.format(log_dir))
    except OSError as e:
        if e.errno == errno.EEXIST:
            logging.warn('"Directory {} already exists'.format(log_dir))
        else:
            raise('Failed to create logging directory: {} ' +
                  log_dir +
                  '. Please specify empty folder or try again')
    return log_dir


def _generate_default_temp_env_name():
    """Creates a new unique name for environment and returns the name"""
    # we need to sanitize the name
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    test_name = re.sub('[^a-zA-Z]', '', _get_test_name_from_filename())
    return '{}-{}-temp-env'.format(test_name, timestamp)


def _get_test_name_from_filename():
    try:
        calling_file = sys._getframe(2).f_back.f_globals['__file__']
        return os.path.splitext(os.path.basename(calling_file))[0]
    except:
        return 'unknown_test'


def _to_deadline(timeout):
    return datetime.utcnow() + timedelta(seconds=int(timeout))


def _clean_dir(maybe_dir):
    """Pseudo-type that validates an argument to be a clean directory path.

    For safety, this function will not attempt to remove existing directory
    contents but will just report a warning.
    """
    try:
        contents = os.listdir(maybe_dir)
    except OSError as e:
        if e.errno == errno.ENOENT:
            # we don't raise this error due to tests abusing /tmp/logs
            warnings.warn('Not a directory {}'.format(maybe_dir))
        if e.errno == errno.EEXIST:
            warnings.warn('Directory {} already exists'.format(maybe_dir))
    else:
        if contents and contents != ["empty"]:
            warnings.warn(
                'Directory {!r} has existing contents.'.format(maybe_dir))
    return maybe_dir


def add_basic_testing_arguments(parser, deadline=True,
                                env=True):
    """Returns the parser loaded with basic testing arguments.

    The basic testing arguments, used in conjuction with boot_context ensures
    a test can be run in any supported substrate in parallel.

    This helper adds 4 positional arguments that defines the minimum needed
    to run a test script.

    These arguments (env, juju_bin, logs, temp_env_name) allow you to specify
    specifics for which env, juju binary, which folder for logging and an
    environment name for your test respectively.

    There are many optional args that either update the env's config or
    manipulate the juju command line options to test in controlled situations
    or in uncommon substrates: --debug, --verbose, --agent-url, --agent-stream,
    --series, --bootstrap-host, --machine, --keep-env. If not using_jes, the
    --upload-tools arg will also be added.

    :param parser: an ArgumentParser.
    :param using_jes: whether args should be tailored for JES testing.
    :param deadline: If true, support the --timeout option and convert to a
        deadline.
    """

    # Optional postional arguments
    if env:
        parser.add_argument(
            'env', nargs='?',
            help='The juju environment to base the temp test environment on.',
            default='lxd')
    add_arg_juju_bin(parser)
    parser.add_argument('logs', nargs='?', type=_clean_dir,
                        help='A directory in which to store logs. By default,'
                        ' this will use the current directory',
                        default=None)
    parser.add_argument('temp_env_name', nargs='?',
                        help='A temporary test environment name. By default, '
                        'this will generate an enviroment name using the '
                        'timestamp and testname. '
                        'test_name_timestamp_temp_env',
                        default=_generate_default_temp_env_name())

    # Optional keyword arguments.
    parser.add_argument('--verbose', action='store_const',
                        default=logging.INFO, const=logging.DEBUG,
                        help='Verbose test harness output.')
    parser.add_argument('--region', help='Override environment region.')
    parser.add_argument('--to', default=None,
                        help='Place the controller at a location.')
    parser.add_argument('--agent-url', action='store', default=None,
                        help='URL for retrieving agent binaries.')
    parser.add_argument('--agent-stream', action='store', default=None,
                        help='Stream for retrieving agent binaries.')
    parser.add_argument('--series', action='store', default=None,
                        help='Name of the Ubuntu series to use.')
    parser.add_argument('--upload-tools', action='store_true',
                        help='upload local version of tools to bootstrap.')
    parser.add_argument('--keep-env', action='store_true',
                        help='Keep the Juju environment after the test'
                        ' completes.')
    parser.add_argument('--existing', action='store_true',
                        help='Test against existing without bootstraping.')
    if deadline:
        parser.add_argument('--timeout', dest='deadline', type=_to_deadline,
                            help="The script timeout, in seconds.")
    return parser


def add_arg_juju_bin(parser):
    parser.add_argument('juju_bin', nargs='?',
                        help='Full path to the Juju binary. By default, this'
                        ' will use $PATH/juju',
                        default=None)


def log_and_wrap_exception(logger, exc):
    """Record exc details to logger and return wrapped in LoggedException."""
    logger.exception(exc)
    stdout = getattr(exc, 'output', None)
    stderr = getattr(exc, 'stderr', None)
    if stdout or stderr:
        logger.info('Output from exception:\nstdout:\n%s\nstderr:\n%s',
                    stdout, stderr)
    return LoggedException(exc)


@contextmanager
def logged_exception(logger):
    """\
    Record exceptions in managed context to logger and reraise LoggedException.

    Note that BaseException classes like SystemExit, GeneratorExit and
    LoggedException itself are not wrapped, except for KeyboardInterrupt.
    """
    try:
        yield
    except (Exception, KeyboardInterrupt) as e:
        raise log_and_wrap_exception(logger, e)


def configure_logging(log_level):
    logging.basicConfig(
        level=log_level, format='%(asctime)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')


class State:
    """Class for tracking desired states within a JujuClient object.

    Methods define desired outcomes from Juju client actions.
    Each returns <something> the GroupReporter class can ingest and print
    Returns None if the desired state is reached
    Raises any appropriate errors
    """

    @staticmethod
    def bootstrapped(status):
        if status:
            return None
        else:
            pass

    @staticmethod
    def started(status):
        """Wait for all agents to reach the 'started' state"""
        applications = status['applications']
        machines = status['machines']
        waiting = {}
        for machine, state in machines.items():
            machine_state = state['juju-status']['current']
            if machine_state != 'foo':
                for state in applications.values():
                    for unit, unit_state in state['units'].items():
                        if unit_state['machine'] == machine:
                            waiting[unit] = machine_state
        return waiting or None

    @staticmethod
    def ready(status, application):
        """Returns applications ready, else returns None"""
        status = status['applications'][application]['units']
        waiting = {}
        for unit, state in status.items():
            app_state = state['workload-status']['current']
            if app_state != 'active':
                waiting[unit] = app_state
        return waiting or None
