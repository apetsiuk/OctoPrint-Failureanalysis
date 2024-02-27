# coding=utf-8
from __future__ import absolute_import

import os
import sys
import argparse
import logging

import re
import requests, base64
import urllib.request

import time
import flask
import numpy as np 
import cv2
import threading
import subprocess
import json
from time import sleep
from time import time

import octoprint.plugin
import octoprint.events
import octoprint.util


UPLOAD_FREQ_S = 10
OCTO_AR_DIR = 'C:/devel/OctoPrint/OctoPrint-Failureanalysis/_synth_references/'  
sys.path.append(OCTO_AR_DIR)



class FailureanalysisPlugin(octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin
):

    ##~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        return {
            # put your plugin's default settings here
        }

    ##~~ AssetPlugin mixin

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return {
            "js": ["js/failureanalysis.js"],
            "css": ["css/failureanalysis.css"],
            "less": ["less/failureanalysis.less"]
        }

    ##~~ Softwareupdate hook

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
        # for details.
        return {
            "failureanalysis": {
                "displayName": "Failureanalysis Plugin",
                "displayVersion": self._plugin_version,

                # version check: github repository
                "type": "github_release",
                "user": "apetsiuk",
                "repo": "OctoPrint-Failureanalysis",
                "current": self._plugin_version,

                # update method: pip
                "pip": "https://github.com/apetsiuk/OctoPrint-Failureanalysis/archive/{target_version}.zip",
            }
        }


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "Failureanalysis Plugin"


# Set the Python version your plugin is compatible with below. Recommended is Python 3 only for all new plugins.
# OctoPrint 1.4.0 - 1.7.x run under both Python 3 and the end-of-life Python 2.
# OctoPrint 1.8.0 onwards only supports Python 3.
__plugin_pythoncompat__ = ">=3,<4"  # Only Python 3

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = FailureanalysisPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
