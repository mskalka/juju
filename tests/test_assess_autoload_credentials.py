"""Tests for assess_autoload_credentials module."""

import logging
import os
import StringIO
from mock import patch, Mock
from tests import TestCase, parse_error

from utility import temp_dir
import assess_autoload_credentials as aac


class TestParseArgs(TestCase):

    def test_common_args(self):
        args = aac.parse_args(['/bin/juju'])
        self.assertEqual('/bin/juju', args.juju_bin)

    def test_help(self):
        fake_stdout = StringIO.StringIO()
        with parse_error(self) as fake_stderr:
            with patch('sys.stdout', fake_stdout):
                aac.parse_args(['--help'])
        self.assertEqual('', fake_stderr.getvalue())
        self.assertNotIn('TODO', fake_stdout.getvalue())

    def test_verbose_is_set_to_debug_when_passed(self):
        args = aac.parse_args(['/bin/juju', '--verbose'])
        self.assertEqual(logging.DEBUG, args.verbose)

    def test_verbose_defaults_to_INFO(self):
        args = aac.parse_args(['/bin/juju'])
        self.assertEqual(logging.INFO, args.verbose)


class TestHelpers(TestCase):

    def test_get_aws_environment_supplies_all_keys(self):
        access_key = 'access_key'
        secret_key = 'secret_key'

        env = aac.get_aws_environment(access_key, secret_key)

        self.assertDictEqual(
            env,
            dict(
                AWS_ACCESS_KEY_ID=access_key,
                AWS_SECRET_ACCESS_KEY=secret_key
            )
        )

    def test_aws_test_details_returns_correct_expected_details(self):
        access_key = 'test_access_key'
        secret_key = 'test_secret_key'
        env, expected = aac.aws_test_details(access_key, secret_key)

        self.assertDictEqual(
            expected,
            {
                'auth-type': 'access-key',
                'access-key': access_key,
                'secret-key': secret_key
            }
        )
