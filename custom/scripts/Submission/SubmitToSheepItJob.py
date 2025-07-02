# SubmitToSheepItJob.py - Deadline 10.3 style, BlenderSubmission.py structure

from Deadline.Scripting import ClientUtils, FrameUtils, PathUtils, RepositoryUtils, StringUtils
from DeadlineUI.Controls.Scripting.DeadlineScriptDialog import DeadlineScriptDialog
from System.IO import Path, StreamWriter
from System.Text import Encoding
import imp # For Integration UI
imp.load_source( 'IntegrationUI', RepositoryUtils.GetRepositoryFilePath( "submission/Integration/Main/IntegrationUI.py", True ) )
import datetime
import os
import re
import requests
import zipfile


scriptDialog = None

def __main__():
    global scriptDialog
    scriptDialog = DeadlineScriptDialog()
    scriptDialog.SetTitle("Submit To SheepIt")
    scriptDialog.SetIcon( scriptDialog.GetIcon( 'Sheepit' ) )
    
    # ==== SheepIt Credentials ====
    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid("Separator0", "SeparatorControl", "SheepIt Account", 0, 0, colSpan=2)
    scriptDialog.AddControlToGrid("LoginLabel", "LabelControl", "Login", 1, 0)
    scriptDialog.AddControlToGrid("LoginBox", "TextControl", "", 1, 1)
    scriptDialog.AddControlToGrid("PasswordLabel", "LabelControl", "Password", 2, 0)
    scriptDialog.AddControlToGrid("PasswordBox", "PasswordControl", "", 2, 1)
    scriptDialog.EndGrid()

    scriptDialog.AddTabControl("Tabs", 0, 0)

    scriptDialog.AddTabPage("Job Options")
    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid( "Separator1", "SeparatorControl", "Job Description", 0, 0 )
    scriptDialog.EndGrid()
    
    # === JOB INFO ===#
    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid( "NameLabel", "LabelControl", "Job Name", 0, 0, "The name of your job. This is optional, and if left blank, it will default to 'Untitled'.", False )
    scriptDialog.AddControlToGrid( "NameBox", "TextControl", "Untitled", 0, 1 )

    scriptDialog.AddControlToGrid( "CommentLabel", "LabelControl", "Comment", 1, 0, "A simple description of your job. This is optional and can be left blank.", False )
    scriptDialog.AddControlToGrid( "CommentBox", "TextControl", "", 1, 1 )
    scriptDialog.EndGrid()

    # ==== Scene File ====
    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid("Separator2", "SeparatorControl", "Scene File", 0, 0, colSpan=2)
    scriptDialog.AddControlToGrid("SceneLabel", "LabelControl", "Scene File", 1, 0)
    scriptDialog.AddControlToGrid("SceneBox", "FileBrowserControl", "", 1, 1)
    scriptDialog.EndGrid()

    # ==== Frame Range ====
    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid("Separator4", "SeparatorControl", "Frame Range", 0, 0, colSpan=2)
    scriptDialog.AddControlToGrid( "FramesLabel", "LabelControl", "Frame List", 1, 0, "The list of frames to render.", False )
    scriptDialog.AddControlToGrid( "FramesBox", "TextControl", "", 1, 1 )
    scriptDialog.AddControlToGrid( "ChunkSizeLabel", "LabelControl", "Frames Step", 2, 0, "Define each frames which is render. ", False )
    scriptDialog.AddRangeControlToGrid( "ChunkSizeBox", "RangeControl", 1, 1, 1000000, 0, 1, 2, 1 )
    scriptDialog.EndGrid()

    # ==== Render Type & Access ====
    scriptDialog.AddGrid()
    scriptDialog.AddControlToGrid("Separator5", "SeparatorControl", "Render Options", 0, 0, colSpan=2)
    scriptDialog.AddControlToGrid("RenderTypeLabel", "LabelControl", "Render With", 1, 0)
    scriptDialog.AddComboControlToGrid( "RenderTypeBox", "ComboControl", "GPU", ("GPU", "CPU"), 1, 1 )
    scriptDialog.AddControlToGrid("IsPublicLabel", "LabelControl", "Public Job", 2, 0)
    scriptDialog.AddControlToGrid("IsPublicBox", "CheckBoxControl", True, 2, 1)
    scriptDialog.EndGrid()
    scriptDialog.EndTabPage()
    scriptDialog.EndTabControl()



    # ==== Buttons ====
    scriptDialog.AddControl("Separator", "SeparatorControl", "")
    submitButton = scriptDialog.AddControl("SubmitButton", "ButtonControl", "Submit")
    closeButton = scriptDialog.AddControl("CloseButton", "ButtonControl", "Close")
    closeButton.ValueModified.connect(scriptDialog.closeEvent)
    submitButton.ValueModified.connect(SubmitButtonPressed)

    scriptDialog.ShowDialog()

def SubmitButtonPressed(*args):
    global scriptDialog

    sceneFile = scriptDialog.GetValue("SceneBox")
    projectName = scriptDialog.GetValue("NameBox").strip()
    comment = scriptDialog.GetValue("CommentBox").strip()
    frames_input = scriptDialog.GetValue("FramesBox").strip()  # ex: "1-100,300-450"
    renderType = scriptDialog.GetValue("RenderTypeBox")
    isPublic = scriptDialog.GetValue("IsPublicBox")
    login = scriptDialog.GetValue("LoginBox").strip()
    password = scriptDialog.GetValue("PasswordBox")

    #=== TEST LOGIN ===#

    # Test SheepIt login before proceeding
    url = "https://www.sheepit-renderfarm.com/user/authenticate"
    data = {
        "login": login,
        "password": password,
        "do_login": "do_login",
        "timezone": "Europe/Paris",
        "account_login": "account_login"
    }
    session = requests.Session()
    try:
        resp = session.post(url, data=data, timeout=10)
        if resp.status_code != 200 or "Incorrect" in resp.text or "incorrect" in resp.text:
            scriptDialog.ShowMessageBox("Invalid SheepIt credentials. Please check your login and password.", "Authentication Error")
            return
    except Exception as e:
        scriptDialog.ShowMessageBox("Error connecting to SheepIt: %s" % str(e), "Network Error")
        return

    # === ZIP THE BLEND ===#

    sceneFile = scriptDialog.GetValue("SceneBox")
    files_to_zip = []

    if sceneFile and os.path.exists(sceneFile):
        files_to_zip.append(sceneFile)
        blend1_file = sceneFile + "1"
        if os.path.exists(blend1_file):
            files_to_zip.append(blend1_file)
    else:
        scriptDialog.ShowMessageBox("Selected scene file does not exist.", "Error")
        return

    # Check total size BEFORE zipping (limit: 2GB)
    total_size = sum(os.path.getsize(f) for f in files_to_zip if os.path.exists(f))
    if total_size > 2 * 1024 * 1024 * 1024:
        scriptDialog.ShowMessageBox("Total size of .blend and .blend1 exceeds 2GB. Submission aborted.", "Error")
        return

    # Name the zip after the scene (basename)
    scene_basename = os.path.splitext(os.path.basename(sceneFile))[0]
    zip_name = scene_basename + ".zip"
    zip_path = os.path.join(ClientUtils.GetDeadlineTempPath(), zip_name)

    # Create the ZIP
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for f in files_to_zip:
            zipf.write(f, os.path.basename(f))

    # Parse frames_input to identify all valid ranges
    frame_ranges = [x.strip() for x in frames_input.split(",") if x.strip()]
    ranges_list = []
    has_non_range = False

    for fr in frame_ranges:
        # Regex to match valid range (e.g., "1-250")
        m = re.match(r"^(\d+)-(\d+)$", fr)
        if m:
            startFrame = int(m.group(1))
            endFrame = int(m.group(2))
            ranges_list.append((startFrame, endFrame))
        else:
            has_non_range = True

    if has_non_range:
        scriptDialog.ShowMessageBox(
            "SheepIt requires at least one frame range (ex: '1-100'). Single frames are not supported for remote submission. Please render isolated frames locally.",
            "Invalid Frame List"
        )
        return

    if not ranges_list:
        scriptDialog.ShowMessageBox(
            "Please enter at least one valid frame range (e.g. '1-100, 150-200').",
            "Frame Range Error"
        )
        return

    info_txt_path = r"C:\Users\Foligraf\Documents\DEV\info.txt"
    with open(info_txt_path, "w", encoding="utf-8") as infof:
        infof.write("===== SheepIt Deadline Submitter Variables =====\n")
        infof.write("Datetime: %s\n" % datetime.datetime.now().isoformat())
        infof.write("Scene file: %s\n" % sceneFile)
        infof.write("Blend1 file: %s\n" % (blend1_file if 'blend1_file' in locals() else ""))
        infof.write("Zipped to: %s\n" % zip_path)
        infof.write("Project name: %s\n" % projectName)
        infof.write("Description: %s\n" % comment)
        infof.write("Login: %s\n" % login)
        infof.write("Password: %s\n" % password)
        infof.write("Render type: %s\n" % renderType)
        infof.write("Is public: %s\n" % isPublic)
        infof.write("FramesBox: %s\n" % frames_input)
        infof.write("Frame ranges: %s\n" % str(ranges_list if 'ranges_list' in locals() else ""))
        for startFrame, endFrame in ranges_list:
            infof.write(" - Range: %s-%s\n" % (startFrame, endFrame))
        infof.write("Total zip size (bytes): %s\n" % (os.path.getsize(zip_path) if os.path.exists(zip_path) else "NOT FOUND"))
        infof.write("Total blend+blend1 size (bytes): %s\n" % total_size)
        infof.write("\n")
        pass  
    for startFrame, endFrame in ranges_list:
        try:
            with open(zip_path, "rb") as fzip:
                files_payload = {'file': (os.path.basename(zip_path), fzip)}
                job_data = {
                    'name': "%s_%d-%d" % (projectName, startFrame, endFrame),
                    'description': comment,
                    'start_frame': startFrame,
                    'end_frame': endFrame,
                    'frame_step': scriptDialog.GetValue("ChunkSizeBox"),
                    'renderer': renderType.lower(),
                    'public': "1" if isPublic else "0",
                }
                resp = session.post("https://www.sheepit-renderfarm.com/api/v2/job/", data=job_data, files=files_payload, timeout=60)
            if resp.status_code != 200:
                scriptDialog.ShowMessageBox("SheepIt returned HTTP %d:\n%s" % (resp.status_code, resp.text), "SheepIt Error")
                return
            try:
                resp_json = resp.json()
            except Exception:
                scriptDialog.ShowMessageBox("Invalid JSON from SheepIt:\n%s" % resp.text, "SheepIt Error")
                return
            if "id" not in resp_json:
                scriptDialog.ShowMessageBox("SheepIt error:\n%s" % (resp_json.get("message") or str(resp_json)), "SheepIt Error")
                return
            sheepit_job_id = resp_json["id"]
            # Continue here (monitoring, log, etc.)

        except Exception as e:
            scriptDialog.ShowMessageBox("Exception while submitting job to SheepIt:\n%s" % str(e), "SheepIt Error")
            return

    scriptDialog.ShowMessageBox("SheepIt job submit UI test completed. (Integration with API pending.)", "DEBUG")
