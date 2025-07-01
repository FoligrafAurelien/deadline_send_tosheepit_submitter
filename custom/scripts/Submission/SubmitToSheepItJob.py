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
    projectName = scriptDialog.GetValue("ProjectNameBox").strip()
    description = scriptDialog.GetValue("DescriptionBox").strip()
    startFrame = scriptDialog.GetValue("StartFrameBox")
    endFrame = scriptDialog.GetValue("EndFrameBox")
    frameStep = scriptDialog.GetValue("FrameStepBox")
    renderType = scriptDialog.GetValue("RenderTypeBox")
    isPublic = scriptDialog.GetValue("IsPublicBox")
    login = scriptDialog.GetValue("LoginBox").strip()
    password = scriptDialog.GetValue("PasswordBox")

    # Checks
    if not sceneFile or not projectName or not login or not password:
        scriptDialog.ShowMessageBox("Please fill all mandatory fields and select a scene file.", "Error")
        return

    files = [sceneFile]
    blend1 = sceneFile + "1"
    if os.path.exists(blend1):
        files.append(blend1)

    total_size = sum(os.path.getsize(f) for f in files if os.path.exists(f))
    if total_size > 2 * 1024 * 1024 * 1024:
        scriptDialog.ShowMessageBox("Total files size exceeds 2GB. Submission aborted.", "Error")
        return

    # Zip files
    zip_path = os.path.join(ClientUtils.GetDeadlineTempPath(), "to_sheepit_upload.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for f in files:
            zipf.write(f, os.path.basename(f))

    if os.path.getsize(zip_path) > 2 * 1024 * 1024 * 1024:
        scriptDialog.ShowMessageBox("Zip file size exceeds 2GB. Submission aborted.", "Error")
        os.remove(zip_path)
        return

    # Place your authentication and POST code here (see messages précédents)
    # Example:
    # try:
    #     sheepit_job_id = submit_sheepit_job(login, password, zip_path, projectName, description, startFrame, endFrame, frameStep, renderType, isPublic)
    #     os.remove(zip_path)
    # except Exception as e:
    #     scriptDialog.ShowMessageBox("Submission to SheepIt failed:\n%s" % str(e), "Error")
    #     if os.path.exists(zip_path):
    #         os.remove(zip_path)
    #     return

    # Script de monitoring comme précédemment

    scriptDialog.ShowMessageBox("SheepIt job submit UI test completed. (Integration with API pending.)", "DEBUG")
