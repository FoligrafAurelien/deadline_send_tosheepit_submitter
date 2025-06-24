# SubmitToSheepItJob.py - Deadline 10.3 pattern, FileBrowserControl + auto-blend1

from Deadline.Scripting import ClientUtils
from DeadlineUI.Controls.Scripting.DeadlineScriptDialog import DeadlineScriptDialog
from System.IO import Path, StreamWriter
from System.Text import Encoding
import zipfile
import os

scriptDialog = None

def __main__():
    global scriptDialog
    scriptDialog = DeadlineScriptDialog()
    scriptDialog.SetTitle("Submit To SheepIt")

    # Scene selection (one file, Blender pattern)
    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid("Separator1", "SeparatorControl", "Scene to Submit", 0, 0, colSpan=2)
    scriptDialog.AddControlToGrid("SceneLabel", "LabelControl", "Scene File", 1, 0)
    scriptDialog.AddControlToGrid("SceneBox", "FileBrowserControl", "", 1, 1)
    scriptDialog.EndGrid()

    # Project info
    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid("Separator2", "SeparatorControl", "Project Info", 0, 0, colSpan=2)
    scriptDialog.AddControlToGrid("ProjectNameLabel", "LabelControl", "Project Name", 1, 0)
    scriptDialog.AddControlToGrid("ProjectNameBox", "TextControl", "", 1, 1)
    scriptDialog.AddControlToGrid("DescriptionLabel", "LabelControl", "Description", 2, 0)
    scriptDialog.AddControlToGrid("DescriptionBox", "TextControl", "", 2, 1)
    scriptDialog.EndGrid()

    # SheepIt credentials
    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid("Separator3", "SeparatorControl", "SheepIt Account", 0, 0, colSpan=2)
    scriptDialog.AddControlToGrid("LoginLabel", "LabelControl", "Login", 1, 0)
    scriptDialog.AddControlToGrid("LoginBox", "TextControl", "", 1, 1)
    scriptDialog.AddControlToGrid("PasswordLabel", "LabelControl", "Password", 2, 0)
    scriptDialog.AddControlToGrid("PasswordBox", "PasswordControl", "", 2, 1)
    scriptDialog.EndGrid()

    scriptDialog.AddControl("Separator", "SeparatorControl", "")
    submitButton = scriptDialog.AddControl("SubmitButton", "ButtonControl", "Submit")
    closeButton = scriptDialog.AddControl("CloseButton", "ButtonControl", "Close")

    closeButton.ValueModified.connect(scriptDialog.closeEvent)
    submitButton.ValueModified.connect(SubmitButtonPressed)

    scriptDialog.ShowDialog()

def SubmitButtonPressed(*args):
    global scriptDialog

    sceneFile = scriptDialog.GetValue("SceneBox").strip()
    projectName = scriptDialog.GetValue("ProjectNameBox").strip()
    description = scriptDialog.GetValue("DescriptionBox").strip()
    login = scriptDialog.GetValue("LoginBox").strip()
    password = scriptDialog.GetValue("PasswordBox")

    if not sceneFile or not projectName or not login or not password:
        scriptDialog.ShowMessageBox("Please fill all mandatory fields and select a scene file.", "Error")
        return

    files = [sceneFile]
    blend1 = sceneFile + "1"
    blend1_added = False
    if os.path.exists(blend1):
        files.append(blend1)
        blend1_added = True

    total_size = sum(os.path.getsize(f) for f in files if os.path.exists(f))
    if total_size > 2 * 1024 * 1024 * 1024:
        scriptDialog.ShowMessageBox("Total files size exceeds 2GB. Submission aborted.", "Error")
        return

    zip_path = os.path.join(ClientUtils.GetDeadlineTempPath(), "to_sheepit_upload.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for f in files:
            zipf.write(f, os.path.basename(f))

    zip_size = os.path.getsize(zip_path)
    if zip_size > 2 * 1024 * 1024 * 1024:
        scriptDialog.ShowMessageBox("Zip file size exceeds 2GB. Submission aborted.", "Error")
        os.remove(zip_path)
        return

    if blend1_added:
        scriptDialog.ShowMessageBox("Found and added .blend1 backup to the archive.", "Info")

    # POST to SheepIt API
    try:
        import requests
        url = "https://www.sheepit-renderfarm.com/api/v2/job/"
        with open(zip_path, "rb") as fzip:
            files_payload = {'file': (os.path.basename(zip_path), fzip)}
            data_payload = {
                'login': login,
                'password': password,
                'name': projectName,
                'description': description
            }
            r = requests.post(url, data=data_payload, files=files_payload)
        if r.status_code != 200 or 'id' not in r.json():
            scriptDialog.ShowMessageBox("Error submitting to SheepIt:\n%s" % r.text, "Error")
            os.remove(zip_path)
            return
        sheepit_job_id = r.json()['id']
        os.remove(zip_path)
    except Exception as e:
        scriptDialog.ShowMessageBox("Submission to SheepIt failed:\n%s" % str(e), "Error")
        if os.path.exists(zip_path):
            os.remove(zip_path)
        return

    # Submit Deadline monitoring job
    jobInfoFilename = Path.Combine(ClientUtils.GetDeadlineTempPath(), "tosheepit_monitor_job_info.job")
    pluginInfoFilename = Path.Combine(ClientUtils.GetDeadlineTempPath(), "tosheepit_monitor_plugin_info.job")

    writer = StreamWriter(jobInfoFilename, False, Encoding.Unicode)
    writer.WriteLine("Plugin=ToSheepItMonitor")
    writer.WriteLine("Name=SheepIt Monitor for %s" % projectName)
    writer.WriteLine("Frames=0-0")
    writer.Close()

    writer = StreamWriter(pluginInfoFilename, False, Encoding.Unicode)
    writer.WriteLine("SheepItJobID=%s" % sheepit_job_id)
    writer.WriteLine("Login=%s" % login)
    writer.WriteLine("Password=%s" % password)
    writer.Close()

    arguments = [jobInfoFilename, pluginInfoFilename]
    results = ClientUtils.ExecuteCommandAndGetOutput(arguments)
    scriptDialog.ShowMessageBox("SheepIt job submitted and monitoring started!\n\n%s" % results, "Submission Results")
