################################################################################
# SampleEtoDialog.py
# MIT License - Copyright (c) 2017 Robert McNeel & Associates.
# See License.md in the root of this repository for details.
################################################################################
from Rhino.UI import *
from Eto.Forms import *
from Eto.Drawing import *

################################################################################
# Sample dialog
################################################################################
import Eto.Forms as forms
import Rhino.UI
from Eto.Drawing import *

class ErrorDialog(forms.Dialog):
    def __init__(self, error_message):
        self.Title = "Error Dialog"
        self.Padding = Padding(20)
        self.ClientSize = Size(500, 80)
        
        self.layout = forms.DynamicLayout()
        
        self.error_label = forms.Label(Text=error_message)
        self.layout.AddRow(self.error_label)
        
        # Create the OK button and set its size
        self.ok_button = forms.Button(Text="OK")
        self.ok_button.Size = Size(100, 40)  # Set the button size explicitly
        self.ok_button.Click += self.on_ok_button_click
        self.layout.AddRow(None, self.ok_button)  # Align the button to the right
        
        self.Content = self.layout

    def on_ok_button_click(self, sender, e):
        self.Close()

    # Function to display the error dialog
    def display(self):
        rc = self.ShowModal(Rhino.UI.RhinoEtoApp.MainWindow)
        return rc


################################################################################
# Check to see if this file is being executed as the "main" python
# script instead of being used as a module by some other python script
# This allows us to use the module which ever way we want.
################################################################################
