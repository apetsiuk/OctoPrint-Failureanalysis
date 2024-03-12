/*
 * View model for OctoPrint-Failureanalysis
 *
 * Author: Aliaksei Petsiuk
 * License: AGPLv3
 */
$(function() {
    function FailureanalysisViewModel(parameters) {
        var self = this;
		
		self.settingsViewModel = parameters[0];
        self.isDetecting = ko.observable(false);
        self.isErrorDetected = ko.observable(false);

        self.onBeforeBinding = function() {
        }
		
		
		self.onStartup= function(){
	
			self.stat_model=$('<span class="stat_model"></span>');
			self.stat_layer=$('<span class="stat_layer"></span>');
			self.stat_nozzle_xyz=$('<span class="stat_nozzle_xyz"></span>');
			self.stat_print_status=$('<span class="stat_print_status"></span>');
			self.stat_detection_status=$('<span class="stat_detection_status"></span>');
			self.stat_similarity=$('<span class="stat_similarity"></span>');
			self.stat_failure=$('<span class="stat_failure"></span>');
			self.stat_failed_area=$('<span class="stat_failed_area"></span>');
			self.stat_failure_location=$('<span class="stat_failure_location"></span>');
			
			
			var stat_container=$('<div class="stat_container"></div>');
			stat_container.insertAfter($('.div_ar_statistics_header'));
			stat_container.append("Model: ", self.stat_model, "<br/>");
			stat_container.append("Layer: ", self.stat_layer, "<br/>");
			stat_container.append("Nozzle XYZ: ", self.stat_nozzle_xyz, "<br/>");
			stat_container.append("Print status: ", self.stat_print_status, "<br/>");
			stat_container.append("Detection status: ", self.stat_detection_status, "<br/>");
			stat_container.append("Similarity: ", self.stat_similarity, "<br/>");
			stat_container.append("Failure: ", self.stat_failure, "<br/>");
			stat_container.append("Failure area: ", self.stat_failed_area, "<br/>");
			stat_container.append("Failure location: ", self.stat_failure_location, "<br/>");
			stat_container.append("<hr/>");
			//stat_container.append(self.stat_model);
			//stat_container.append("</br>")
		}
		
		self.onDataUpdaterPluginMessage = function(plugin, data) {
			if (plugin != "failureanalysis") {
                return;
            }
			
			if (data.type == "error") {
                new PNotify({
                    title: 'Error Detected',
                    text: data.error,
                    type: 'error',
                    hide: false
                });

                $("#detection").text("Start Error Detection");
                self.isDetecting(false);
                self.isErrorDetected(true);
            }
				
			$('.stat_model').css("font-weight", "bold");
			$('.stat_model').text(data.model);
			$('.stat_layer').css("font-weight", "bold");
			$('.stat_layer').text(data.layer);
			$('.stat_nozzle_xyz').css("font-weight", "bold");
			$('.stat_nozzle_xyz').text(data.nozzle_xyz);
			$('.stat_print_status').css("font-weight", "bold");
			$('.stat_print_status').text(data.print_status);
			$('.stat_detection_status').css("font-weight", "bold");
			$('.stat_detection_status').text(data.detection_status);
			$('.stat_similarity').css("font-weight", "bold");
			$('.stat_similarity').text(data.similarity);
			$('.stat_failure').css("font-weight", "bold");
			$('.stat_failure').text(data.failure);
			$('.stat_failed_area').css("font-weight", "bold");
			$('.stat_failed_area').text(data.failed_area);
			$('.stat_failure_location').css("font-weight", "bold");
			$('.stat_failure_location').text(data.failure_location);
		}

        self._headCanvas = document.getElementById('headCanvas');
        self._headCanvas_proc = document.getElementById('headCanvas_proc');
		
		self._drawImage = function (img, canv, break_cache = false) {
            var ctx = canv.getContext("2d");
            var localimg = new Image();
            localimg.onload = function () {
                var w = localimg.width;
                var h = localimg.height;
                var scale = Math.min(ctx.canvas.clientWidth / w, ctx.canvas.clientHeight / h, 1);
				//var scale = 1;
                ctx.drawImage(localimg, 0, 0, w * scale, h * scale);

                // Avoid memory leak. Not certain if this is implemented correctly, but GC seems to free the memory every now and then.
                localimg = undefined;
            };
            if (break_cache) {
                img = img + "?" + new Date().getTime();
		    }
            localimg.src = img;
        };
	
	
	    self._getImage3 = function (imagetype) {
            $.ajax({
                //url: PLUGIN_BASEURL + "visualizer/get-image?imagetype=" + imagetype,
				url: "/plugin/failureanalysis/get-image?imagetype=" + imagetype,
                type: "GET",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                // data: JSON.stringify({"sens_thresh" : self.sens_thresh}),
                success: function (response) {
                    console.log('succ');
                    if (response.hasOwnProperty("src")) {
                        self._drawImage(response.src, self._headCanvas);
                    }
                }
            });
        };
     
        setInterval(function () {
            self._getImage3('BIM');
        }, 1000)
		
		


    }

    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.
     */
    OCTOPRINT_VIEWMODELS.push({
        construct: FailureanalysisViewModel,
        dependencies: [ "settingsViewModel"],
        elements: [ "#settings_plugin_Failureanalysis", "#tab_plugin_Failureanalysis"]
    });
});
