# SubmitToSheepItJob.py - Deadline 10.3 style, BlenderSubmission.py structure

from Deadline.Scripting import ClientUtils, FrameUtils, PathUtils, RepositoryUtils, StringUtils
from DeadlineUI.Controls.Scripting.DeadlineScriptDialog import DeadlineScriptDialog
from System.IO import Path, StreamWriter
from System.Text import Encoding
import zipfile
import os
import imp # For Integration UI
imp.load_source( 'IntegrationUI', RepositoryUtils.GetRepositoryFilePath( "submission/Integration/Main/IntegrationUI.py", True ) )
import IntegrationUI
import re

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

    for startFrame, endFrame in ranges_list:
        # Generate unique job name for each range
        job_name = "{}_{}-{}".format(os.path.basename(sceneFile), startFrame, endFrame)
        # Place your code to zip, upload, and submit this range
        # Example: submit_sheepit_job(..., job_name, ..., startFrame, endFrame, ...)
        # ...
        pass  # (submit logic goes here)

    scriptDialog.ShowMessageBox("SheepIt job submit UI test completed. (Integration with API pending.)", "DEBUG")
