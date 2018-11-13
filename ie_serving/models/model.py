#
# Copyright (c) 2018 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from ie_serving.models.ir_engine import IrEngine
from ie_serving.logger import get_logger
import glob
import os
import re
from urllib.parse import urlparse, urlunparse
from google.cloud import storage

logger = get_logger(__name__)


class Model():

    def __init__(self, model_name: str, model_directory: str,
                 available_versions: list, engines: dict):
        self.model_name = model_name
        self.model_directory = model_directory
        self.versions = available_versions
        self.engines = engines
        self.default_version = max(self.versions)
        logger.info("List of available versions "
                    "for {} model: {}".format(self.model_name, self.versions))
        logger.info("Default version "
                    "for {} model is {}".format(self.model_name,
                                                self.default_version))

    @classmethod
    def build(cls, model_name: str, model_directory: str):
        logger.info("Server start loading model: {}".format(model_name))
        versions = cls.get_all_available_versions(model_directory)
        engines = cls.get_engines_for_model(versions=versions)
        available_versions = [version['version'] for version in versions]
        model = cls(model_name=model_name, model_directory=model_directory,
                    available_versions=available_versions, engines=engines)
        return model

    @classmethod
    def get_all_available_versions(cls, model_directory):
        versions_path = cls.get_versions_path(model_directory)
        logger.info(versions_path)
        versions = []
        for version in versions_path:
            number = cls.get_version_number(version_directory=version)
            if number != 0:
                storage_type, model_xml, model_bin = \
                    cls.get_full_path_to_model(version)
                if model_xml is not None and model_bin is not None:
                    model_info = {'storage': storage_type,
                                  'xml_model_path': model_xml,
                                  'bin_model_path': model_bin,
                                  'version': number}
                    versions.append(model_info)
        return versions

    @staticmethod
    def get_engines_for_model(versions):
        inference_engines = {}
        failures = []
        for version in versions:
            try:
                logger.info("Creating inference engine object "
                            "for version: {}".format(version['version']))
                inference_engines[version['version']] = IrEngine.build(
                    model_bin=version['bin_model_path'],
                    model_xml=version['xml_model_path'])
            except Exception as e:
                logger.error("Error occurred while loading model "
                             "version: {}".format(version))
                logger.error("Content error: {}".format(str(e).rstrip()))
                failures.append(version)

        for failure in failures:
            versions.remove(failure)

        return inference_engines


    @staticmethod
    def get_versions_path(model_directory):
        if model_directory[-1] != os.sep:
            model_directory += os.sep
        return glob.glob("{}/*/".format(model_directory))

    @staticmethod
    def get_version_number(version_directory):
        version_number = re.search('/\d+/$', version_directory).group(0)[1:-1]
        return int(version_number)

    @staticmethod
    def get_full_path_to_model(specific_version_model_path):
        bin_path = glob.glob("{}*.bin".format(specific_version_model_path))
        xml_path = glob.glob("{}*.xml".format(specific_version_model_path))
        if xml_path[0].replace('xml', '') == bin_path[0].replace('bin', ''):
            return xml_path[0], bin_path[0]
        return None, None
