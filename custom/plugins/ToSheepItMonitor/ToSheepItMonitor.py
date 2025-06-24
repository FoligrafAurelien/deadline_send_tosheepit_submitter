from Deadline.Plugins import DeadlinePlugin, PluginType
import sys
import time

def GetDeadlinePlugin():
    return ToSheepItMonitorPlugin()

def CleanupDeadlinePlugin(deadlinePlugin):
    deadlinePlugin.Cleanup()

class ToSheepItMonitorPlugin(DeadlinePlugin):
    def __init__(self):
        if sys.version_info.major == 3:
            super().__init__()
        else:
            super(ToSheepItMonitorPlugin, self).__init__()

        self.InitializeProcessCallback += self.InitializeProcess
        self.RenderTasksCallback += self.RenderTasks

    def Cleanup(self):
        pass

    def InitializeProcess(self):
        self.PluginType = PluginType.Simple
        self.SingleFramesOnly = True

    def RenderTasks(self):
        job_id = self.GetPluginInfoEntry("SheepItJobID")
        login = self.GetPluginInfoEntry("Login")
        password = self.GetPluginInfoEntry("Password")

        import requests

        sheepit_url = "https://www.sheepit-renderfarm.com/api/v2/job/%s/" % job_id
        progress = 0
        while True:
            try:
                r = requests.get(sheepit_url)
                if r.status_code == 200:
                    data = r.json()
                    progress = int(data.get("progress", 0))
                    self.LogInfo("SheepIt progress: %d%%" % progress)
                    if progress >= 100:
                        self.LogInfo("SheepIt job finished.")
                        break
                else:
                    self.LogInfo("SheepIt API error: %s" % r.text)
            except Exception as e:
                self.LogInfo("Error while checking SheepIt status: %s" % str(e))
            time.sleep(180)  # 3 minutes

        self.LogInfo("SheepIt monitoring completed.")
