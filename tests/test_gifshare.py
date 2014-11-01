# -*- coding: utf-8 -*-

import unittest
from nose.tools import assert_raises
from mock import MagicMock, patch, call, ANY

from six.moves.configparser import ConfigParser

from .util import *

import gifshare
import gifshare.cli
import gifshare.exceptions


defaults = {
    'aws_access_id': 'dummy-access-id',
    'aws_secret_access_key': 'dummy-secret-access-key',
    'web_root': 'http://dummy.web.root/',
    'region': 'dummy-region',
    'bucket': 'not.a.bucket',
}


class DummyKey(object):
    def __init__(self, name):
        self.name = name


def dummy_get(_, key):
    return defaults[key]


config_stub = MagicMock(spec=ConfigParser)
config_stub.get.side_effect = dummy_get


class TestBucket(unittest.TestCase):
    def setUp(self):
        self.bucket = gifshare.Bucket(config_stub)

    def test_bucket(self):
        # Patch S3Connection and its get_bucket method:
        with patch('gifshare.s3.S3Connection',
                   name='S3Connection') as MockS3Connection:
            mock_get_bucket = MagicMock(name='get_bucket')
            MockS3Connection.return_value.get_bucket = mock_get_bucket

            _ = self.bucket.bucket

            # Ensure the config is passed correctly to S3Connection
            # and get_bucket:
            MockS3Connection.assert_called_with(
                'dummy-access-id', 'dummy-secret-access-key')
            mock_get_bucket.assert_called_with('not.a.bucket')

    def test_key_for(self):
        with patch('gifshare.s3.S3Connection',
                   name='S3Connection'):
            with patch('gifshare.s3.Key') as key_mock:
                k = self.bucket.key_for('abc.gif', 'image/gif')
                key_mock.assert_called_with(self.bucket.bucket, 'abc.gif')
                self.assertEqual(k.content_type, 'image/gif')

    def test_list(self):
        # Patch S3Connection and its get_bucket method:
        with patch('gifshare.s3.S3Connection',
                   name='S3Connection') as MockS3Connection:
            mock_get_bucket = MagicMock(name='get_bucket')
            mock_bucket = MagicMock(name='bucket')
            mock_get_bucket.return_value = mock_bucket
            mock_bucket.list.return_value = [
                DummyKey('image1.jpeg'),
                DummyKey('image2.jpeg')
            ]
            MockS3Connection.return_value.get_bucket = mock_get_bucket

            keys = list(self.bucket.list())

            self.assertEqual(keys, [
                'http://dummy.web.root/image1.jpeg',
                'http://dummy.web.root/image2.jpeg',
            ])

            MockS3Connection.assert_called_with(
                'dummy-access-id', 'dummy-secret-access-key')
            mock_get_bucket.assert_called_with('not.a.bucket')
            mock_bucket.list.assert_called_once_with()

    def test_upload_file(self):
        key_stub = MagicMock(name='Key')
        key_stub.exists.return_value = False
        self.bucket.key_for = MagicMock(name='key_for', return_value=key_stub)

        url = self.bucket.upload_file('test_image.png', 'image/png', image_path('png'))
        key_stub.set_contents_from_filename.assert_called_once_with(
            os.path.abspath(image_path('png')),
            cb=ANY
        )

    def test_upload_contents(self):
        key_stub = MagicMock(name='Key')
        key_stub.exists.return_value = False
        self.bucket.key_for = MagicMock(name='key_for', return_value=key_stub)

        image_data = load_image('png')

        with patch('gifshare.core.download_file', return_value=image_data):
            dest_url = self.bucket.upload_contents(
                'thing.png',
                'image/png',
                image_data
            )
            key_stub.set_contents_from_string.assert_called_once_with(
                image_data,
                cb=ANY
            )
            self.assertEqual(dest_url, 'http://dummy.web.root/thing.png')

    def test_upload_url_existing_file(self):
        key_stub = MagicMock(name='thing.png')
        key_stub.exists.return_value = True
        self.bucket.key_for = MagicMock(name='key_for', return_value=key_stub)

        image_data = load_image('png')

        with patch('gifshare.core.download_file', return_value=image_data):
            with self.assertRaises(gifshare.exceptions.FileAlreadyExists):
                self.bucket.upload_contents(
                    'thing.png', 'image/png', image_data)
        self.assertFalse(key_stub.set_contents_from_string.called)

    def test_upload_existing_file(self):
        key_stub = MagicMock(name='Key')
        key_stub.exists.return_value = True
        self.bucket.key_for = MagicMock(name='key_for', return_value=key_stub)

        with assert_raises(gifshare.exceptions.FileAlreadyExists):
            self.bucket.upload_file('test_image', 'image/png', image_path('png'))

    def test_get_url(self):
        key_stub = MagicMock(name='Key')
        key_stub.exists.return_value = True
        self.bucket.key_for = MagicMock(name='key_for', return_value=key_stub)

        url = self.bucket.get_url('test.png')
        self.bucket.key_for.assert_called_with('test.png')
        self.assertEqual(key_stub.exists.call_count, 1)
        self.assertEqual(url, 'http://dummy.web.root/test.png')

    def test_missing_get_url(self):
        key_stub = MagicMock(name='Key')
        key_stub.exists.return_value = False
        self.bucket.key_for = MagicMock(name='key_for', return_value=key_stub)

        with self.assertRaises(gifshare.exceptions.MissingFile):
            self.bucket.get_url('test.png')

    def test_delete_existing(self):
        key_stub = MagicMock(name='Key')
        key_stub.exists.return_value = True
        self.bucket.key_for = MagicMock(name='key_for', return_value=key_stub)

        self.bucket.delete_file('/non-existant/image')
        key_stub.delete.assert_called_with()

    @patch('sys.stderr')    # Stops test-output polution.
    def test_delete_missing(self, stderr_stub):
        key_stub = MagicMock(name='Key')
        key_stub.exists.return_value = False
        self.bucket.key_for = MagicMock(name='key_for', return_value=key_stub)

        self.bucket.delete_file('/non-existant/image')
        key_stub.delete.assert_not_called()


class TestExtensionDetection(unittest.TestCase):
    def test_jpeg_path(self):
        self.assertEqual(
            gifshare.core.correct_ext(image_path('jpeg')),
            'jpeg')

    def test_gif_path(self):
        self.assertEqual(
            gifshare.core.correct_ext(image_path('gif')),
            'gif')

    def test_png_path(self):
        self.assertEqual(
            gifshare.core.correct_ext(image_path('png')),
            'png')

    def test_jpeg(self):
        self.assertEqual(
            gifshare.core.correct_ext(load_image('jpeg'), True),
            'jpeg')

    def test_gif(self):
        self.assertEqual(
            gifshare.core.correct_ext(load_image('gif'), True),
            'gif')

    def test_png(self):
        self.assertEqual(
            gifshare.core.correct_ext(load_image('png'), True),
            'png')

    def test_unknown_type(self):
        with self.assertRaises(gifshare.core.UnknownFileType):
            gifshare.core.correct_ext(load_image('ico'), True)


class TestMiscellaneousFunctions(unittest.TestCase):
    @patch('gifshare.core.progressbar.ProgressBar')
    @patch('gifshare.core.requests')
    def test_download_file(self, requests_mock, progress_bar_stub):
        pbar_mock = MagicMock()
        progress_bar_stub.return_value.start.return_value = pbar_mock

        response_stub = MagicMock()
        response_stub.headers = {
            'content-length': 197
        }

        def iter_content_stub(_):
            for i in range(3):
                yield ' ' * 64
            yield ' ' * 5
        response_stub.iter_content = iter_content_stub
        requests_mock.get.return_value = response_stub
        gifshare.core.download_file('http://nonsense.url/')
        requests_mock.get.assert_called_with(
            'http://nonsense.url/', stream=True)
        pbar_mock.update.assert_has_calls([
            call(64), call(128), call(192), call(197)
        ])
        pbar_mock.finish.assert_called_once_with()

    def test_get_name_from_url(self):
        self.assertEqual(
            gifshare.core.get_name_from_url('http://some.domain/path/myfile.jpeg'),
            'myfile'
        )

        self.assertEqual(
            gifshare.core.get_name_from_url('http://some.domain/path/myfile.jpeg#.png'),
            'myfile'
        )


@patch('gifshare.s3.progressbar.ProgressBar')
class TestUploadCallback(unittest.TestCase):
    def test_upload_callback(self, progress_bar_mock):
        progress_bar_instance_mock = progress_bar_mock.return_value

        callback = gifshare.s3.upload_callback()
        progress_bar_mock.assert_not_called()
        callback(0, 100)
        progress_bar_mock.assert_called_with(widgets=ANY, maxval=100)

        progress_bar_instance_mock.start.assert_called_with()

    def test_callback_update(self, progress_bar_mock):
        progress_bar_instance_mock = progress_bar_mock.return_value

        callback = gifshare.s3.upload_callback()
        callback(0, 100)
        callback(50, 100)
        progress_bar_instance_mock.update.assert_called_with(50)

    def test_callback_finish(self, progress_bar_mock):
        progress_bar_instance_mock = progress_bar_mock.return_value
        callback = gifshare.s3.upload_callback()
        callback(0, 100)
        callback(100, 100)
        progress_bar_instance_mock.finish.assert_called_with()


class TestMain(unittest.TestCase):
    @patch('gifshare.cli.command_upload')
    def test_main_upload(self, cmd_upload):
        gifshare.cli.main(['upload', 'a-file'])
        self.assertEqual(cmd_upload.call_count, 1)

    @patch('gifshare.cli.command_list')
    def test_main_list(self, cmd_list):
        gifshare.cli.main(['list'])
        self.assertEqual(cmd_list.call_count, 1)

    @patch('gifshare.cli.command_list')
    def test_main_error(self, cmd_list):
        cmd_list.side_effect = gifshare.exceptions.UserException
        result = gifshare.cli.main(['list'])
        self.assertEqual(result, 1)

    @patch('gifshare.cli.load_config', return_value=config_stub)
    @patch('gifshare.cli.Bucket')
    def test_main_list_arguments(self, bucket_mock, load_config_stub):
        bucket_instance = MagicMock()
        bucket_mock.return_value = bucket_instance
        bucket_instance.list.return_value = [
            'http://dummy.web.root/image1.jpeg',
            'http://dummy.web.root/image2.jpeg',
        ]

        gifshare.cli.main(['list'])
        self.assertEqual(bucket_mock.call_args, call(config_stub))
        self.assertEqual(bucket_instance.list.call_count, 1)

    @patch('random.choice')
    @patch('gifshare.cli.load_config', return_value=config_stub)
    @patch('gifshare.cli.Bucket')
    def test_main_list_random(self, bucket_mock, load_config_stub, random_choice):
        bucket_instance = MagicMock()
        bucket_mock.return_value = bucket_instance
        bucket_instance.list.return_value = [
            'http://dummy.web.root/image1.jpeg',
            'http://dummy.web.root/image2.jpeg',
        ]

        gifshare.cli.main(['list', '-r'])
        bucket_init = bucket_mock.call_args
        self.assertEqual(bucket_init, call(config_stub))
        self.assertEqual(bucket_instance.list.call_count, 1)

        self.assertEqual(random_choice.call_count, 1)

    @patch('gifshare.cli.load_config', return_value=config_stub)
    @patch('gifshare.cli.Bucket')
    @patch('gifshare.core.download_file')
    def test_main_upload_url(self, download_file, bucket_mock, load_config_stub):
        download_file.return_value = load_image('png')
        bucket_instance = MagicMock()
        bucket_mock.return_value = bucket_instance

        gifshare.cli.main(['upload', 'http://probably.giphy/kittiez.png'])
        self.assertEqual(bucket_mock.call_args, call(config_stub))
        self.assertEqual(download_file.call_count, 1)

    @patch('gifshare.cli.load_config', return_value=config_stub)
    @patch('gifshare.cli.Bucket')
    def test_main_upload_file(self, bucket_mock, load_config_stub):
        bucket_instance = MagicMock(spec=gifshare.Bucket)
        bucket_mock.return_value = bucket_instance

        gifshare.cli.main(['upload', image_path('png')])
        self.assertEqual(bucket_mock.call_args, call(config_stub))
        self.assertEqual(bucket_instance.upload_file.call_count, 1)

    @patch('gifshare.cli.load_config', return_value=config_stub)
    @patch('gifshare.cli.Bucket')
    def test_main_upload_missing_file(self, bucket_mock, load_config_stub):
        with self.assertRaises(IOError):
            gifshare.cli.main(['upload', '/tmp/non-existent.png'])
            self.assertEqual(bucket_mock.call_count, 0)

    @patch('gifshare.cli.load_config', return_value=config_stub)
    @patch('gifshare.cli.Bucket', spec=gifshare.Bucket)
    def test_main_delete(self, bucket_mock, load_config_stub):
        result = gifshare.cli.main(['delete', 'my/file.png'])
        bucket_mock.return_value.delete_file.assert_called_with('my/file.png')
        self.assertEqual(result, 0)

    @patch('gifshare.cli.load_config', return_value=config_stub)
    @patch('gifshare.cli.Bucket', spec=gifshare.Bucket)
    def test_main_expand(self, bucket_mock, load_config_stub):
        result = gifshare.cli.main(['expand', 'test.png'])
        bucket_mock.return_value.get_url.assert_called_with('test.png')
        self.assertEqual(result, 0)
