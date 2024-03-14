# coding=utf-8


# http://127.0.0.1:8081/stream/0/640/480
# http://127.0.0.1:27100/stream/0/640/480


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
#from time import time

import octoprint.plugin
import octoprint.events
import octoprint.util

import fullcontrol as fc


UPLOAD_FREQ_S = 10
OCTO_AR_DIR = 'C:/devel/OctoPrint/OctoPrint-Failureanalysis/_synth_references/'  
sys.path.append(OCTO_AR_DIR)
API_KEY_DIR = 'C:/devel/'



class FailureanalysisPlugin(octoprint.plugin.SettingsPlugin,
                            octoprint.plugin.AssetPlugin,
                            octoprint.plugin.TemplatePlugin,
                            
                            octoprint.plugin.StartupPlugin,
                            octoprint.plugin.ShutdownPlugin,
                            octoprint.plugin.BlueprintPlugin,
                            octoprint.plugin.EventHandlerPlugin,
                            ):
                            
    T1_INTERVAL = 5.0
    T2_INTERVAL = 7.0
    
    
    def __init__(self):
        self._process = None
        self._thread = None
        self._thread_stop = threading.Event()
        self._cam_server_path = "\cam_stream\\ar_cam.py"
        self.api_key = ""
        
        self._timer_print_stats= None
        self._interval_print_stats=None
        
        self.layer_num = -1
        
        self.img = None
        self.img_synth_ref = None
        self.img_real_layer = None
        self.img_heatmap_comparison = None
        self.img_xray_tensor = None
        self.img_detected_error = None
        self.img_generated_patch = None
        
        
    def initialize(self):
        self._interval_print_stats=self._settings.get_float(["T1_INTERVAL"])
        self._timer_print_stats=octoprint.util.RepeatedTimer(self.T1_INTERVAL, self._stats_update)
        self._timer_print_stats.start()


    ##########################################################
    ##~~ StartupPlugin mixin
    def on_startup(self, host, port):
        """
        Starts the AR Cam Flask server on octoprint server startup
        """
        try:
            log_file = open("flask_log.txt", "w")
            print(log_file)
            script_abs_path = os.path.dirname(__file__) + self._cam_server_path
            #script_abs_path = str("c:\devel\octoprint\OctoPrint-Failureanalysis\octoprint_failureanalysis\cam_stream\\ar_cam.py")

            print('\n\nscript_abs_path=\n', os.path.dirname(__file__))
            print('\n\nscript_abs_path=\n', script_abs_path)
            self._process = subprocess.Popen([sys.executable, script_abs_path], stdout=log_file, stderr=log_file)

            time.sleep(2)
            if self._process.poll() is None:
                print("Cam server started successfully.")
            else:
                print("Error while starting the Flask server. Check the log file for details.")
            log_file.close()
        except Exception as e:
            self._logger.info("Failureanalysis failed to start")
            self._logger.info(e)
        return
        
        
    def on_after_startup(self):
        print('on_after_startup')
        self.red_api_key()
        
        
    def on_shutdown(self):
        """
        Stops the AR Cam Flask server on octoprint server shutdown
        """
        if self._process is not None and self._process.poll() is None:
            self._logger.info("Stopping the cam server...")
            self._process.terminate()
            self._process.wait()
    
    
    ##~~ SettingsPlugin mixin
    def get_settings_defaults(self):
        """
        Returns the initial default settings for the plugin. Can't skip it!
        """
        return dict(
            stream="",
            aruco_dict="DICT_6X6_250",
        )
        

    ##~~ TemplatePlugin mixin
    def get_template_configs(self):
        return [
            {
                "type": "settings",
                "template": "Failureanalysis_settings.jinja2",
                "custom_bindings": True
            },
            {
                "type": "tab",
                "template": "Failureanalysis_tab.jinja2",
                "custom_bindings": True
            }
        ]


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
                "displayName": "Failureanalysis",
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

    #################################################
    def red_api_key(self):
        api_key_filename = os.path.join(API_KEY_DIR, 'api-key.txt')
        with open(api_key_filename) as f:
            lines = f.read().splitlines()
        self.api_key = lines[0]
        print('\n\nself.api_key=\n\n')
        print(self.api_key)
        
        
    def get_user_name(self):
        url = "http://localhost:5000/api/access/users"
        # self._logger.info('d')
        r = requests.get(url=url, headers={"X-Api-Key": str(self.api_key)}).json()
        print_state = None
        if 'users' in r:
            print_state = r['users'][0]['name']
        return print_state
        
        
    def get_print_name(self):
        url = "http://localhost:5000/api/job"
        r = requests.get(url=url, headers={"X-Api-Key": str(self.api_key)}).json()
        print_name = None
        if 'job' in r:
            print_name = r['job']['file']['name']
        return print_name
        
        
    def get_printer_state(self):
        url = "http://localhost:5000/api/printer?exclude=temperature,sd"
        # self._logger.info('d')
        r = requests.get(url=url, headers={"X-Api-Key": str(self.api_key)}).json()
        print_state = None
        if 'state' in r:
            print_state = r['state']['text']
        self._logger.info(print_state)
        return print_state
    
    
    def _stats_update(self):
        self._logger.info("_stats_update called")
        print("_stats_update")
        stat_model = None
        stat_layer = self.layer_num
        stat_nozzle_z = None
        stat_print_status = None
        stat_detection_status = "N/A"
        stat_similarity = "N/A"
        stat_failure = "N/A"
        stat_failed_area = "N/A"
        stat_failure_location = "N/A"
        
        try:
            user_name = self.get_user_name()
            stat_model = self.get_print_name()
            stat_print_status = self.get_printer_state()
            
            #self._logger.info(self._printer.get_current_data())
            self._logger.info(self._printer._currentZ)
            stat_nozzle_z = str(self._printer._currentZ)
            
            #read_image_synth_reference()
            print("\n\n\nself.layer_num=", self.layer_num)
            
            #stat_model = "adsdsd"
            #stat_print_status = "sdvsdv"
            
            #stat_nozzle_xyz = self.get_nozzle_xyz()
            #print_name = "print_name"
            #print_state = "state"
            #self.print_state = print_state
            #ret, self.img = self.get_img_stream()
            self._logger.info('got image')
            if stat_print_status == 'Printing':
                #self.s3_full_path_obj = self.upload_img_S3(self.img, user_name, print_name)
                pass
            print(user_name, stat_model, stat_print_status)
            #sleep(UPLOAD_FREQ_S)
        except:
            print('_stats_update error')
            
        self._plugin_manager.send_plugin_message(self._identifier,
        {"model": stat_model, 
         "layer": stat_layer,
         "nozzle_z": stat_nozzle_z,
         "print_status": stat_print_status,
         "detection_status": stat_detection_status,
         "similarity": stat_similarity,
         "failure": stat_failure,
         "failed_area": stat_failed_area,
         "failure_location": stat_failure_location,
         })
         
        '''
        steps = []
        steps.append(fc.Point(x=10, y=10, z=0))
        steps.append(fc.Point(x=20))
        steps.append(fc.Point(x=10, y=20))
        print(fc.transform(steps, 'gcode'))
        '''
        
    #################################################  
    @octoprint.plugin.BlueprintPlugin.route("/set-layer-num", methods=["GET"])
    def set_layer_num(self):
        try:
            self.layer_num = flask.request.values["layer"]
        except Exception as e:
            self._logger.info("Plugin error")
            self._logger.info(e)
        return flask.jsonify(layer=f'{self.layer_num}')


    @octoprint.plugin.BlueprintPlugin.route("/get-layer-num", methods=["GET"])
    def get_layer_num(self):
        return flask.jsonify(layer=f'{self.layer_num}')
    
    
    
    
    @octoprint.plugin.BlueprintPlugin.route("/get-image", methods=["GET"])
    def get_image(self):
        result = ""
        if "imagetype" in flask.request.values:
            im_type = flask.request.values["imagetype"]
            self.img = self.read_img()
            retval, buffer = cv2.imencode('.jpg', self.img)
            try:
                result = flask.jsonify(src="data:image/{0};base64,{1}".format(".jpg",str(base64.b64encode(buffer), "utf-8")))
            except IOError:
                result = flask.jsonify(error="Unable to fetch img")
        return flask.make_response(result, 200)
    
    
    def read_img(self):
        #RESOLUTION_FRONT = (853, 480)
        RESOLUTION_FRONT = (53, 80)
        self.img = cv2.imread('C:/devel/OctoPrint-ARPrintVisualizer/octoprint_ARPrintVisualizer/blender_images/aruco_1.jpg')
        self.img = cv2.resize(self.img, RESOLUTION_FRONT, interpolation=cv2.INTER_AREA)
        return self.img
    #************************************************
    
    
    @octoprint.plugin.BlueprintPlugin.route("/get-image-synth-reference", methods=["GET"])
    def get_image_synth_reference(self):
        result = ""
        if "imagetype" in flask.request.values:
            im_type = flask.request.values["imagetype"]
            self.img = self.read_image_synth_reference()
            retval, buffer = cv2.imencode('.jpg', self.img)
            try:
                result = flask.jsonify(src="data:image/{0};base64,{1}".format(".jpg",str(base64.b64encode(buffer), "utf-8")))
            except IOError:
                result = flask.jsonify(error="Unable to fetch img")
        return flask.make_response(result, 200)
    
    
    def read_image_synth_reference(self):
        self.img = None
        #RESOLUTION_FRONT = (853, 480)
        RESOLUTION_FRONT = (200, 200)
        # Layer number format = L0001
        self.img = cv2.imread('C:/devel/OctoPrint/OctoPrint-Failureanalysis/octoprint_failureanalysis/_synth_layered_references/gcode_001_image_L'+str(self.layer_num).zfill(4) + '.png')
        if(self.img is None):
            
            self.img = cv2.imread('C:/devel/OctoPrint/OctoPrint-Failureanalysis/octoprint_failureanalysis/image_placeholder.png')
        else:
            self.img = cv2.resize(self.img, RESOLUTION_FRONT, interpolation=cv2.INTER_AREA)
        print("\n\n\nself.layer_num=", self.layer_num)
        return self.img
    
    
    #################################################
    


# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "failureanalysis"


# Set the Python version your plugin is compatible with below. Recommended is Python 3 only for all new plugins.
# OctoPrint 1.4.0 - 1.7.x run under both Python 3 and the end-of-life Python 2.
# OctoPrint 1.8.0 onwards only supports Python 3.
__plugin_pythoncompat__ = ">=3,<4"  # Only Python 3
__plugin_implementation__ = FailureanalysisPlugin()


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = FailureanalysisPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
