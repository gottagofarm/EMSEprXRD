# EMSEprXRD
X-ray diffraction analysis tool for research project

very case-specific project that is based on .xrdml file parsing & analysis


////
PACKAGE INSTALLATION
////

the following packages are used : 
numpy, PySide2, xrdtools

  PySide2 works great on python 3.9, might cause issues on more recent versions (at least PyQT5 didn't work on python 3.11)

  xrdtools requires pip (no conda install)

run the following commands :

  pure pip installation (global):
    pip install xrdtools
    pip install numpy
    pip install PySide2


  conda installation :
    # Best practice, use an environment rather than install in the base env
    conda create -n my-env
    conda activate my-env
  
    conda install pip
    pip install xrdtools
    conda install -c conda-forge pyside2   // or use the pip version (as you installed it for xrdtools) : pip install PySide2
    conda install -c anaconda numpy        // or use the pip version (as you installed it for xrdtools) : pip install numpy
  

////
RUNNING prXRD.py
////

Download both prXRD.py and xrdui.py in the same folder (if you want to modify the ui you need qtDesigner, which can either be found in the pyside2 folder or downloaded)

Before running the program, adjust the default path at the start of prXRD.py to the folder where the xrmdl files will be located (for efficiency reasons)

