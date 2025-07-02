# SubmitToSheepItJob.py - Deadline 10.3 style, BlenderSubmission.py structure

from Deadline.Scripting import ClientUtils, FrameUtils, PathUtils, RepositoryUtils, StringUtils
from DeadlineUI.Controls.Scripting.DeadlineScriptDialog import DeadlineScriptDialog
from System.IO import Path, StreamWriter
from System.Text import Encoding
from html.parser import HTMLParser
import imp # For Integration UI
imp.load_source( 'IntegrationUI', RepositoryUtils.GetRepositoryFilePath( "submission/Integration/Main/IntegrationUI.py", True ) )
import datetime
import os
import re
import requests
import zipfile


scriptDialog = None
DEBUG_PATH = r"C:\Users\Foligraf\Documents\DEV\deadline_sheepit_debug.txt"

class TokenParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.token = ""
    def handle_starttag(self, tag, attrs):
        if tag == "input":
            attrs = dict(attrs)
            if attrs.get("name") == "UPLOAD_IDENTIFIER":
                self.token = attrs.get("value", "")

class AddJobParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.data = {}
    def handle_starttag(self, tag, attrs):
        if tag == "input":
            attrs = dict(attrs)
            name = attrs.get("name")
            value = attrs.get("value", "")
            if name and value:
                self.data[name] = value
        elif tag == "select":
            attrs = dict(attrs)
            name = attrs.get("name")
            if name:
                self.data[name] = "" # for engines, etc.

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
    scriptDialog.AddRangeControlToGrid( "FrameStepBox", "RangeControl", 1, 1, 1000000, 0, 1, 2, 1 )
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

def log_debug(msg):
    with open(DEBUG_PATH, "a", encoding="utf-8") as debugf:
        debugf.write(msg + "\n")

def SubmitButtonPressed(*args):
    global scriptDialog

    open(DEBUG_PATH, "w").close()
    log_debug("==== SheepIt Submit START ====")

    # === Récupération des valeurs UI ===
    sceneFile = scriptDialog.GetValue("SceneBox")
    projectName = scriptDialog.GetValue("NameBox").strip()
    comment = scriptDialog.GetValue("CommentBox").strip()
    frames_input = scriptDialog.GetValue("FramesBox").strip()
    frames_step = scriptDialog.GetValue("FrameStepBox")
    renderType = scriptDialog.GetValue("RenderTypeBox")
    isPublic = scriptDialog.GetValue("IsPublicBox")
    login = scriptDialog.GetValue("LoginBox").strip()
    password = scriptDialog.GetValue("PasswordBox")
    log_debug(f"SceneFile: {sceneFile}, Name: {projectName}, Frames: {frames_input}, Step: {frames_step}, Type: {renderType}, Public: {isPublic}, Login: {login}")

    # === TEST LOGIN ===
    session = requests.Session()
    url = "https://www.sheepit-renderfarm.com/user/authenticate"
    data = {
        "login": login,
        "password": password,
        "do_login": "do_login",
        "timezone": "Europe/Paris",
        "account_login": "account_login"
    }
    try:
        resp = session.post(url, data=data, timeout=10)
        log_debug(f"Login POST status: {resp.status_code}")
        if resp.status_code != 200 or "Incorrect" in resp.text or "incorrect" in resp.text:
            log_debug("Login failed or incorrect credentials.")
            scriptDialog.ShowMessageBox("Invalid SheepIt credentials. Please check your login and password.", "Authentication Error")
            return
    except Exception as e:
        log_debug(f"Login Exception: {e}")
        scriptDialog.ShowMessageBox("Error connecting to SheepIt: %s" % str(e), "Network Error")
        return

    # === ZIP THE BLEND (.blend & .blend1) ===
    files_to_zip = []
    blend1_file = sceneFile + "1"
    if sceneFile and os.path.exists(sceneFile):
        files_to_zip.append(sceneFile)
        if os.path.exists(blend1_file):
            files_to_zip.append(blend1_file)
    else:
        log_debug("Scene file does not exist.")
        scriptDialog.ShowMessageBox("Selected scene file does not exist.", "Error")
        return
    total_size = sum(os.path.getsize(f) for f in files_to_zip if os.path.exists(f))
    log_debug(f"Total size before zip: {total_size}")
    if total_size > 2 * 1024 * 1024 * 1024:
        log_debug("Blend + blend1 size exceeds 2GB.")
        scriptDialog.ShowMessageBox("Total size of .blend and .blend1 exceeds 2GB. Submission aborted.", "Error")
        return
    scene_basename = os.path.splitext(os.path.basename(sceneFile))[0]
    zip_name = scene_basename + ".zip"
    zip_path = os.path.join(ClientUtils.GetDeadlineTempPath(), zip_name)
    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for f in files_to_zip:
                zipf.write(f, os.path.basename(f))
        log_debug(f"Zip created: {zip_path}")
    except Exception as e:
        log_debug(f"Exception during zip creation: {e}")
        scriptDialog.ShowMessageBox("Failed to create zip: %s" % str(e), "ZIP Error")
        return

    # === FRAMES PARSING ===
    frame_ranges = [x.strip() for x in frames_input.split(",") if x.strip()]
    ranges_list = []
    has_non_range = False
    for fr in frame_ranges:
        m = re.match(r"^(\d+)-(\d+)$", fr)
        if m:
            startFrame = int(m.group(1))
            endFrame = int(m.group(2))
            ranges_list.append((startFrame, endFrame))
        else:
            has_non_range = True
    log_debug(f"Frame ranges parsed: {ranges_list}")
    if has_non_range:
        log_debug("Non-range frame detected.")
        scriptDialog.ShowMessageBox(
            "SheepIt requires at least one frame range (ex: '1-100'). Single frames are not supported for remote submission. Please render isolated frames locally.",
            "Invalid Frame List"
        )
        return
    if not ranges_list:
        log_debug("No valid frame range found.")
        scriptDialog.ShowMessageBox(
            "Please enter at least one valid frame range (e.g. '1-100, 150-200').",
            "Frame Range Error"
        )
        return

    # ==== TOKEN STEP ====
    try:
        r = session.get("https://www.sheepit-renderfarm.com/getstarted", timeout=10)
        p = TokenParser()
        p.feed(r.text)
        p.close()
        token = p.token
        log_debug(f"Token obtained: {token}")
        if not token:
            scriptDialog.ShowMessageBox("Unable to get upload token (possible max projects reached).", "SheepIt Error")
            return
    except Exception as e:
        log_debug(f"Token step exception: {e}")
        scriptDialog.ShowMessageBox(f"Error during token request: {e}", "SheepIt Error")
        return

    # ==== UPLOAD ZIP ====
    try:
        with open(zip_path, "rb") as fzip:
            files_payload = {
                "UPLOAD_IDENTIFIER": (None, token),
                "addjob_archive": (os.path.basename(zip_path), fzip, "multipart/form-data")
            }
            resp_upload = session.post(
                "https://www.sheepit-renderfarm.com/project/internal/upload",
                files=files_payload, timeout=60
            )
        log_debug(f"Upload zip status: {resp_upload.status_code}")
        # Pas de check avancé ici, upload = silent if OK
    except Exception as e:
        log_debug(f"Exception during upload: {e}")
        scriptDialog.ShowMessageBox(f"Error uploading archive: {e}", "SheepIt Error")
        return

    # ==== PROJECT ADD (get all variables) ====
    try:
        r = session.get("https://www.sheepit-renderfarm.com/project/add", timeout=10)
        parser = AddJobParser()
        parser.feed(r.text)
        parser.close()
        hidden_data = parser.data
        log_debug(f"Hidden form data: {str(hidden_data)[:400]}")
    except Exception as e:
        log_debug(f"Add job page exception: {e}")
        scriptDialog.ShowMessageBox(f"Error fetching project/add page: {e}", "SheepIt Error")
        return
        log_debug("Champs du formulaire /project/add (parser.data):")
        for k, v in parser.data.items():
            log_debug(f"  {k}: {v}")


    # ==== LOOP FOR EACH RANGE ====
    for startFrame, endFrame in ranges_list:
        try:
            try:
                frame_step_value = int(frames_step)
            except Exception:
                frame_step_value = 1
            compute_method = 1 if renderType.upper() == "CPU" else 3  # 1=CPU, 3=GPU
            job_data = parser.data.copy()
            job_data.update({
                "addproject_animation_start_frame_0": str(startFrame),
                "addproject_animation_end_frame_0": str(endFrame),
                "addproject_animation_step_frame_0": str(frame_step_value),
                "compute_method": str(compute_method),
                "name": f"{projectName}_{startFrame}-{endFrame}",
                "description": comment
            })
            log_debug("job_data final POST vers /project/add_internal :")
            for k, v in job_data.items():
                log_debug(f"  {k}: {v}")
            resp = session.post(
                "https://www.sheepit-renderfarm.com/project/add_internal",
                data=job_data, timeout=60
            )
            log_debug(f"Add_internal status: {resp.status_code}")
            log_debug(f"Add_internal text (first 300): {resp.text[:300]}")
            if resp.status_code != 200 or "Project successfully created" not in resp.text:
                log_debug(f"Project add error: {resp.text[:500]}")
                scriptDialog.ShowMessageBox(f"SheepIt returned error during project creation:\n{resp.text}", "SheepIt Error")
                return
        except Exception as e:
            log_debug(f"Exception while adding job range {startFrame}-{endFrame}: {e}")
            scriptDialog.ShowMessageBox(f"Exception during job creation: {e}", "SheepIt Error")
            return

    # Cleanup zip file
    try:
        if os.path.exists(zip_path):
            os.remove(zip_path)
            log_debug(f"Deleted temp zip file: {zip_path}")
    except Exception as e:
        log_debug(f"Exception deleting zip: {e}")

    scriptDialog.ShowMessageBox("SheepIt job(s) submitted successfully!", "Success")
    log_debug("==== SheepIt Submit END ====")