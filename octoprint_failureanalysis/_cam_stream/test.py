from octoprint.settings import Settings

# Get the OctoPrint settings dictionary
octoprint_settings = Settings()
print(octoprint_settings.get(["plugins", "failureanalysis", "aruco_type"]))