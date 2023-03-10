# EMSEprXRD
X-ray diffraction analysis tool for research project

very case-specific project that is based on .xrdml file parsing & analysis


////
PACKAGE INSTALLATION
////

the following packages are used : numpy (contained in xrdtools), PySide2, xrdtools

PySide2 works great on python 3.9, might cause issues on more recent versions (at least PyQT5 didn't work on python 3.11)
to update the python version in anaconda version : https://www.cse.unsw.edu.au/~en1811/resources/getting-started/install-anaconda.html


xrdtools requires pip:

run the following commands (my-env being the name of the environment you want to create):
    
    conda create -n my-env
    conda activate my-env
    conda install pip
    pip install xrdtools
    pip install PySide2



////
RUNNING prXRD.py
////

Download both prXRD.py and xrdui.py in the same folder (if you want to modify the ui you need qtDesigner, which can either be found in the pyside2 folder or downloaded)

Before running the program, adjust the default path at the start of prXRD.py to the folder where the xrmdl files will be located (for efficiency reasons)

to run the program, go to folder in terminal and type :
  
    python prXRD.py
    
there is no point in running xrdui.py, as it shouldnt execute the app
