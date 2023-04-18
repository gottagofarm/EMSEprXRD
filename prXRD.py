#this script takes the ui of xrdui and does stuff

from datetime import date
import sys

from PySide2 import QtPrintSupport
from PySide2.QtCharts import QtCharts
from PySide2.QtGui import QColor
#math imports
import numpy as np
import xmltodict

#mac needs a layer?
import os
os.environ['QT_MAC_WANTS_LAYER'] = '1'


from xrdui import *

#setting up the default path for the files to open
path = ''

#setting up default path for files to be saved in
savePath = ''

momentPoints = 500 #setting up the number of points on moment graphs
#having a list of colors for series
colors = [Qt.red,Qt.green,Qt.blue,Qt.yellow,Qt.cyan,Qt.magenta,Qt.darkRed,Qt.darkGreen,Qt.darkBlue,
                Qt.darkCyan,Qt.darkMagenta,Qt.darkYellow,Qt.gray,Qt.darkGray,Qt.lightGray,]
#########################################
#### MainWindow class to be executed
#########################################

class MainWindow(QMainWindow):
    """
    ui & functionalities setup
    """
    def __init__(self,parent=None):
        QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.setWindowTitle('X-ray diffraction analysis tool')
        self.attributeSetup()

        self.setMinimumSize(800,600)

        self.linkActions()

        #mac wont show menubar correctly
        self.setMenuBar(self.ui.menubar)
        self.show

    """
    setting up all attributes that keep data in memory
    """
    def attributeSetup(self):
        self.sheets = [] #saving the different datasets used to create charts and show views
        self.buttons =[] #list of buttons corresponding to the diff views
        self.id = 0 #incrementing id of charts & views
        self.currentSheetId = 0 #keeping track of the view we're in
        self.copiedView = [] #clipboard of copied Sheet

        self.undoPile = [] #saving the actions to undo and redo later
        self.redoPile = [] #saving undone actions to redo
        self.initialZoom = NotImplemented #previous zoom before undoing (not used for now (too bad))

        self.ui.chart_view = NotImplemented #storing the chartview to access chart & plotarea for computing limits
        self.axisX = None #keeping axis stored to add noise filter line (not the case for regression lines that adapt when scale changes)
        self.axisY = None

        self.blockShowView = False #blocking showView in need (actions to be applied before changing view)
        self.noise_coords = [(0,0),(0,0)] #keeping track of the points defining the noise filter

        self.ui.pushButtonNoiseFilter.setCheckable(True)  #setting different buttons to have toggle on mode
        self.ui.pushButtonNoiseFilter.setChecked(False)

        self.status_bar = QStatusBar(self) #having a status bar to display the chart coords
        self.setStatusBar(self.status_bar)
        self.timer = NotImplemented

    """
    links all the different buttons and shortcuts to the corresponding functions
    """
    def linkActions(self):
        #file menu actions
        self.ui.actionOpen.triggered.connect(self.openfiles)
        self.ui.pushButtonPlus.clicked.connect(self.openfiles)
        self.ui.actionCombineCharts.triggered.connect(self.combineCharts)

        self.ui.actionSavePNG.triggered.connect(lambda : self.saveAllViews(True))
        self.ui.actionSaveMultiplePNG.triggered.connect(self.saveAllViews)
        self.ui.actionSaveCurrentData.triggered.connect(self.saveCurrentSheet)
        self.ui.actionSaveSelectedData.triggered.connect(self.saveAllSheets)

        self.ui.actionPrintChart.triggered.connect(self.printCurrent)
        self.ui.actionExit.triggered.connect(app.quit)

        self.ui.actionScroll_left.triggered.connect(lambda: self.scroll(right = False))
        self.ui.actionScroll_Right.triggered.connect(lambda: self.scroll(right = True))

        #edit menu actions
        self.ui.actionDelete_Chart.triggered.connect(lambda : self.removeView(self.currentSheetId))
        self.ui.actionCopy.triggered.connect(self.copyView)
        self.ui.actionPaste.triggered.connect(self.pasteView)
        self.ui.actionCut.triggered.connect(self.cutView)
        self.ui.actionResetZoom.triggered.connect(self.resetZoom)
        self.ui.actionUndo.triggered.connect(self.undoAction)
        self.ui.actionRedo.triggered.connect(self.redoAction)

        #preprocessing menu actions
        self.ui.pushButtonReduceDataset.clicked.connect(self.reduceDataset) #setting up the horizontal reframe button
        self.ui.pushButtonNoiseFilter.clicked.connect(self.noiseFilter)
        #special noiseFilter UI buttons setup
        self.ui.pushButtonLeftMin.clicked.connect(lambda : self.ui.textEditLeftVal.setText(str(float(self.ui.textEditLeftVal.toPlainText())-1)))
        self.ui.pushButtonLeftPlus.clicked.connect(lambda : self.ui.textEditLeftVal.setText(str(float(self.ui.textEditLeftVal.toPlainText())+1)))
        self.ui.pushButtonRightMin.clicked.connect(lambda : self.ui.textEditRightVal.setText(str(float(self.ui.textEditRightVal.toPlainText())-1)))
        self.ui.pushButtonRightPlus.clicked.connect(lambda : self.ui.textEditRightVal.setText(str(float(self.ui.textEditRightVal.toPlainText())+1)))
        self.ui.textEditLeftVal.textChanged.connect(self.updateNoiseLine)
        self.ui.textEditRightVal.textChanged.connect(self.updateNoiseLine)
        #hiding the buttons for now
        self.toggleVisibility(self.ui.frameGrid,False)

        self.ui.actionHorizontalLinear.triggered.connect(lambda : self.scales(None,True)) 
        self.ui.actionHorizontalLogarithmic.triggered.connect(lambda : self.scales(None,False))
        self.ui.comboBoxHorizontalScale.currentIndexChanged.connect(self.comboBoxScale)

        self.ui.actionVerticalLinear.triggered.connect(lambda : self.scales(True,None))
        self.ui.actionVerticalLogarithmic.triggered.connect(lambda : self.scales(False,None))
        self.ui.comboBoxVerticalScale.currentIndexChanged.connect(self.comboBoxScale)

        self.ui.actionMean.triggered.connect(lambda : self.polyreg(0))
        self.ui.pushButtonMean.clicked.connect(lambda : self.polyreg(0))
        self.ui.actionLinear_Regression.triggered.connect(lambda : self.polyreg(1))
        self.ui.pushButtonRegLin.clicked.connect(lambda : self.polyreg(1))

        self.ui.pushButtonUnitToggle.clicked.connect(self.toggleUnit)

        #operations menu actions
        self.ui.actionM1.triggered.connect(lambda : self.kMoment(1,self.currentSheetId,show = False))
        self.ui.actionM2.triggered.connect(lambda : self.kMoment(2,self.currentSheetId,show = False))
        self.ui.actionM3.triggered.connect(lambda : self.kMoment(3,self.currentSheetId,show = False))
        self.ui.actionM4_q.triggered.connect(lambda : self.kMoment(4,self.currentSheetId,show = False))
        self.ui.actionFourier.triggered.connect(lambda : self.fourier(self.currentSheetId,show = False))
        self.ui.actionAll.triggered.connect(self.all)


    ########################################################
    #methods for the "file" menu
    ########################################################

    """
    openfiles is the function linked to open / Ctrl+O
    """
    def openfiles(self):
        #browsing for the file
        #setting up a filter for the correct type of files
        filter = 'xrdml files(*.xrdml *.xml)'
        fname, filter= QFileDialog.getOpenFileName(None, 'Open file', path, filter)
        
        fpath = ''
        for x in fname:
            fpath += x
        try : file = open(fpath)
        except FileNotFoundError:
            self.displayError("Please enter a valid file (.xml created using this program or .xrdml)")
        #getting the values from the file
        if fpath[-4:] == 'rdml':
            data,values = self.parseXrdml(file.name)
            title = f'Chart {self.id}'
            units = ['Angle Theta (°)','log Intensity']
            #setting up the chart view
            self.setupNewChart(data,values,title,units,None,True,False,True)
        #same for .xml files
        elif fpath[-4:] == '.xml':
            self.parseXml(file.name)

    """
    combines multiple sheets into same chart
    """
    def combineCharts(self):
        #creating the dialog to allow for selection of charts
        self.selection_dialog = SelectionDialog(self.buttons)
        self.selection_dialog.setWindowTitle("Select charts to combine")
        result = self.selection_dialog.exec_() #executing dialog
        if result == QDialog.Accepted:
            #creating the new chart data and values
            selected_items = self.selection_dialog.selected_items
            data = []
            values = {'Lambda':'','Theta':'','SD':'','linRegEquations':[],'Type':'combinedChart','numberOfCharts':0}
            units = ['','']
            buttonName = 'Combined '
            title = ''
            for i in range (len(self.sheets)):
                if self.buttons[i] in selected_items:
                    data.append(self.sheets[i][1][0])
                    data.append(self.sheets[i][1][1])
                    values['numberOfCharts']+=1
                    if units ==['','']:
                        units[0] = self.sheets[i][4][0]
                        #the default value is linear, so the unit will be put to linear if it has log in front
                        if units[0][:4] == 'log ':
                            units[0] = units[0][4:]
                        units[1] = 'Normalized units'
                    buttonName+=f'{i},'
                    title += f'{self.sheets[i][3]},'
            if data!=[]:
                title = title[0:-1]
                self.setupNewChart(data,values,title,units,buttonName,True,True,True)

    """
    Saves current view as a png
    """
    def saveCurrentView(self,name = None):
        if self.ui.chart_view == NotImplemented:
            self.displayError('Need open chart to save as PNG')
            return

        pixmap = self.ui.chart_view.grab()
        title = ''
        for sheet in self.sheets:
            if sheet[0] == self.currentSheetId:
                title = sheet[3]
                break
        day = date.today()
        if name != None:
            finalName = savePath +str(name)
        else:
            finalName = savePath +str(day)+'_'+title+'.png'
        pixmap.save(finalName,'PNG')

    """
    saves all sheets as pngs
    """
    def saveAllViews(self, bugfix = False):
        #special case for only one saved item (because it would create false files????)
        if bugfix:
            self.saveCurrentView()
            return
        #creating the dialog to allow for selection of charts
        self.selection_dialog = SelectionDialog(self.buttons)
        self.selection_dialog.setWindowTitle("Select charts to save")
        result = self.selection_dialog.exec_() #executing dialog
        if result == QDialog.Accepted:
            #getting the selected buttons
            selected_items = self.selection_dialog.selected_items
            for i in range(len(self.sheets)):
                if self.buttons[i] in selected_items:
                    self.showView(self.sheets[i][0],False)
                    self.saveCurrentView()
            #adding the animations back on
            self.ui.chart_view.chart().setAnimationOptions(QtCharts.QChart.SeriesAnimations)

    """
    saves current sheet data
    """
    def saveCurrentSheet (self):
        if self.ui.chart_view == NotImplemented:
            self.displayError('Need open chart to save Data')
            return
        dict = self.sheetToDict(self.currentSheetId)
        day = date.today()
        title = dict['title'].replace(' ','').replace(',','_')
        finalName = savePath +str(day)+'_'+title+'.xml'
        finalDict = {f'xrdml':dict} #adding dict layer for xmltodict single root
        xml_data = xmltodict.unparse(finalDict,pretty= True)
        with open(finalName,'w') as f:
            f.write((xml_data))

    """
    saves all sheets in a single xml file
    """
    def saveAllSheets(self):
        #creating the dialog to allow for selection of charts
        self.selection_dialog = SelectionDialog(self.buttons)
        self.selection_dialog.setWindowTitle("Select data to save")
        result = self.selection_dialog.exec_() #executing dialog
        if result == QDialog.Accepted:
            #getting the selected buttons
            selected_items = self.selection_dialog.selected_items
            dict = {}
            for i in range(len(self.sheets)):
                if self.buttons[i] in selected_items:
                    dict[f'sheet{i}'] =self.sheetToDict(self.sheets[i][0])
            day = date.today()
            finalName = savePath+str(day)+'_'+dict['sheet0']['values']['baseFile'][-14:-6].replace(' ','').replace(',','_') +'.xml'
            finalDict = {f'allData':dict}
            xml_data = xmltodict.unparse(finalDict,pretty = True)
            with open(finalName,'w') as f:
                f.write((xml_data))

    """
    prints current view
    """
    def printCurrent(self):
        printer = QtPrintSupport.QPrinter()
        dialog = QtPrintSupport.QPrintDialog(printer, self)
        if not dialog.exec_():
            return  # User canceled

        # Render the chart view widget to a QPainter
        painter = QPainter()
        painter.begin(printer)
        chartView = self.ui.chart_view
        chartView.render(painter)

        # Finish up and cleanup
        painter.end()

    """
    allows to scroll through windows using left and right arrow keys
    """
    def scroll(self,right):
        if self.ui.chart_view == NotImplemented:
            return
        if right: #slide one to the right
            for sheet in self.sheets:
                if sheet[0]>self.currentSheetId:
                    self.showView(sheet[0])
                    break
        else: #slide one to the left (start counting ids from the right)
            n = len(self.sheets)
            for i in range(n):
                if self.sheets[n-i-1][0]<self.currentSheetId:
                    self.showView(self.sheets[n-i-1][0])
                    break

    """
    tracks the mouse coordinates on the graph
    """
    def statusUpdate(self):
        pos = self.mapFromGlobal(QCursor.pos())
        point = self.ui.chart_view.chart().mapToValue(pos)
        units = self.lookForSheet(self.currentSheetId)[3]
        if self.ui.chart_view.chart().plotArea().contains(pos):
            self.status_bar.showMessage(f"{units[0]}: {point.x()}, {units[1]}: {point.y()}")
        else:
            self.status_bar.clearMessage()
        if self.timer!=NotImplemented:
            self.timer.start(100) #checking the mouse position every 100 ms

    ########################################################
    #useful methods
    ########################################################

    """
    takes an xrmdl file and parses it to get the useful data&values
    """
    def parseXrdml(self,file):
        #dummy values 
        values = {'Theta':0,'Lambda':0,'SD':0,'Time':0,'linRegEquations':[],'baseFile':file}
        parsedfile = xmltodict.parse(open(file).read(),xml_attribs = False)
        
        #associating the values with the chart       
        values['SD']=0
        values['Lambda']=float(parsedfile['xrdMeasurements']['xrdMeasurement']['usedWavelength']['kAlpha1'])
        values['Time']=float(parsedfile['xrdMeasurements']['xrdMeasurement']['scan']['dataPoints']['commonCountingTime'])
        values['Type']='baseSheet'
        intensities =parsedfile['xrdMeasurements']['xrdMeasurement']['scan']['dataPoints']['intensities'].split(' ')
        intensities = np.array(list(map(float,intensities)))
        angles = np.linspace(float(parsedfile['xrdMeasurements']['xrdMeasurement']['scan']['dataPoints']['positions'][0]['startPosition']),float(parsedfile['xrdMeasurements']['xrdMeasurement']['scan']['dataPoints']['positions'][0]['endPosition']),len(intensities))/2
        #storing the intensity data (normalized according to time per step), and the angle data
        data = [intensities,angles]
        #computing the first moment to get the bragg angle
        values['Theta']=np.sum(angles*intensities)/np.sum(intensities)

        return (data,values)

    """
    parses .xml files that are given by the saveCurrentSheet method
    """
    def parseXml(self,file):
        parsedfile = xmltodict.parse(open(file).read(),xml_attribs = False)
        if list(parsedfile.keys())[0]=='allData': #checking if the .xml file is for many sheets 
            for sheet in parsedfile['allData'].values():
                #recreating the sheets stored in the data
                values = {}
                for key,value in sheet['values'].items():
                    try : values[key] = float(value)
                    except (ValueError,TypeError): values[key] = value
                values['linRegEquations'] = []
                title = sheet['title']
                units = [sheet['units']['bottomUnit'],sheet['units']['leftUnit']]
                leftValues = sheet['data']['YaxisData'].split(' ')
                bottomValues = sheet['data']['XaxisData'].split(' ')
                data = [np.array(list(map(float,leftValues))),np.array(list(map(float,bottomValues)))]
                self.setupNewChart(data,values,title,units,None,True,True,True)
        elif list(parsedfile.keys())[0] == 'xrdml': #checking if the .xml file is for only one sheet
            #recreating the sheet (data, values, title, units)
            sheet = parsedfile['xrdml']
            values = {}
            for key,value in sheet['values'].items():
                try : values[key] = float(value)
                except (ValueError,TypeError): values[key] = value
            values['linRegEquations'] = []
            title = sheet['title']
            units = [sheet['units']['bottomUnit'],sheet['units']['leftUnit']]
            leftValues = sheet['data']['YaxisData'].split(' ')
            bottomValues = sheet['data']['XaxisData'].split(' ')
            data = [np.array(list(map(float,leftValues))),np.array(list(map(float,bottomValues)))]
            self.setupNewChart(data,values,title,units,None,True,True,True)
        else:
            self.displayError('Please use .xml files created using this program.')

    """
    sets up a new chart
    """
    def setupNewChart(self,data,values = "None",title = "Title",units=["Angle (°)","Intensity"],
            buttonName = None,show = True,vertLin = True,horLin =True):
        id = self.id
        #creating new chart in list
        self.sheets.append([id,data,values,title,units,vertLin,horLin])
        #creating an undo and redo pile associated to that sheet
        self.undoPile.append([])
        self.redoPile.append([])
        #setting up the button to change the chart viewed
        if buttonName is None:
            self.setupSheetButton(f"Sheet {id}",id,Checked= show)
        else : 
            self.setupSheetButton(buttonName,id ,Checked= show)

        #setting up the chart and showing it
        if show:
            self.showView(id)        

        self.id+=1 #incrementing chart id

    """
    shows the view corresponding to set of data and values linked with id
    """
    def showView(self,id,animations = True):
        #checking wether this is available
        if self.blockShowView:
            for i in range(len(self.sheets)):
                if self.sheets[i][0] == self.currentSheetId:
                    self.ui.horizontalLayout_4.itemAt(i).widget().setChecked(True)
                break
            return

        try : self.ui.verticalLayout_7.takeAt(0).widget().deleteLater() #deleting the current view if there is one
        except AttributeError:
            pass
        
        try : data,values,title,units,vertLin,horLin = self.lookForSheet(id) #checking if the id corresponds to a sheet
        except TypeError:
            self.displayError("Error : no chart corresponding to ID found")
            return
        
        #ui setup
        #showing the values:
        self.ui.Lambda.setText('Lambda [A] : '+str(values['Lambda']))
        self.ui.SD.setText('SD [mm] : '+str(values['SD']))
        self.ui.Theta.setText('Theta [°] : '+str(values['Theta']))
        #unit toggle button setup
        if values['Type'] == 'baseSheet':
            if units[0] == 'Angle Theta (°)':
                self.ui.pushButtonUnitToggle.setText('Change theta to Q')
            elif units[0]== 'Q':
                self.ui.pushButtonUnitToggle.setText('Change Q to Theta')
        else :
            self.ui.pushButtonUnitToggle.setText('')
        #axis and comboBox setup
        if horLin : #checking for horizontal linear scale
            axisX = QtCharts.QValueAxis()
            #changing the index in the combobox to the correct one
            self.ui.comboBoxHorizontalScale.currentIndexChanged.disconnect(self.comboBoxScale)
            self.ui.comboBoxHorizontalScale.setCurrentIndex(0)
            self.ui.comboBoxHorizontalScale.currentIndexChanged.connect(self.comboBoxScale)
        else :
            axisX = QtCharts.QLogValueAxis()
            axisX.setBase(10)
            self.ui.comboBoxHorizontalScale.currentIndexChanged.disconnect(self.comboBoxScale)
            self.ui.comboBoxHorizontalScale.setCurrentIndex(1)
            self.ui.comboBoxHorizontalScale.currentIndexChanged.connect(self.comboBoxScale)
        axisX.setTitleText(units[0])

        if vertLin : #checking for vertical linear scale
            axisY = QtCharts.QValueAxis()
            self.ui.comboBoxVerticalScale.currentIndexChanged.disconnect(self.comboBoxScale)
            self.ui.comboBoxVerticalScale.setCurrentIndex(0)
            self.ui.comboBoxVerticalScale.currentIndexChanged.connect(self.comboBoxScale)
        else :
            axisY = QtCharts.QLogValueAxis()
            axisY.setBase(10)
            self.ui.comboBoxVerticalScale.currentIndexChanged.disconnect(self.comboBoxScale)
            self.ui.comboBoxVerticalScale.setCurrentIndex(1)
            self.ui.comboBoxVerticalScale.currentIndexChanged.connect(self.comboBoxScale)
        axisY.setTitleText(units[1])
        if values['Type']!='combinedChart':
            axisY.setRange(np.min(data[0]),np.max(data[0])) #blocking the vertical scale to avoid the regression series going over

        # series creation from data
        #turning the X and Y data into a Qseries for the chart
        series = QtCharts.QScatterSeries() 
        series.setName('mainSeries')

        if values['Type'] =='combinedChart': 
            pass
        else:
            for i in range(len(data[0])):
                if not vertLin and data[0][i]<=0: #avoiding negative values in logarithmic scale
                    pass
                else:
                    series.append(data[1][i],data[0][i])
        series.setMarkerSize(3)
        #chart setup
        chart = QtCharts.QChart()

        chart.setTitle(title)
        if animations:
            chart.setAnimationOptions(QtCharts.QChart.SeriesAnimations)

        chart.addAxis(axisX,Qt.AlignBottom)
        chart.addAxis(axisY,Qt.AlignLeft)
        chart.legend().setVisible(False)

        #adding the main series
        chart.addSeries(series)
        series.attachAxis(axisX)
        series.attachAxis(axisY)

        #widget setup
        self.ui.chart_view = QtCharts.QChartView(chart)
        self.ui.chart_view.setRenderHint(QPainter.Antialiasing)
        self.ui.chart_view.chart().setTheme(QtCharts.QChart.ChartThemeDark)
        
        sizePolicy = QSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
        self.ui.chart_view.setSizePolicy(sizePolicy)
        self.ui.chart_view.setRubberBand(QtCharts.QChartView.HorizontalRubberBand) #allowing for zoom by default
        self.timer = QTimer(self.ui.chart_view)  #adding a timer for the status update or it won't allow for zoom
        self.timer.timeout.connect(self.statusUpdate)
        self.timer.start(100)

        n = len(data)
        #creating a special case for combined charts:
        if values['Type']=='combinedChart':
            for j in range(int(n/2)):
                moreSeries = QtCharts.QScatterSeries()
                moreSeries.setName(f'moreSeries{j}')
                max = np.max(data[2*j])
                normalizedData = data[2*j]/max
                for i in range(len(data[2*j])):
                    moreSeries.append(data[2*j+1][i],normalizedData[i])
                moreSeries.setColor(colors[j])
                moreSeries.setMarkerSize(3)
                moreSeries.setBorderColor(colors[j])
                chart.addSeries(moreSeries)
                moreSeries.attachAxis(axisX)
                moreSeries.attachAxis(axisY)
            axisX.setRange(0,data[1][-1])
        #adding possible line series on top in other case:
        else:
            for j in range(2,n):
                moreSeries = QtCharts.QLineSeries()
                moreSeries.setName(f'moreSeries{j}')
                for i in range(len(data[j])): #linear regressions are added to the end
                    if not vertLin and data[j][i]<=0:    #avoiding any negative value in the linear regressions
                        pass
                    else :
                        moreSeries.append(data[1][i],data[j][i])
                pen = QPen(colors[j-2])
                pen.setWidth(2)
                moreSeries.setPen(pen)
                chart.addSeries(moreSeries)
                moreSeries.attachAxis(axisX)
                moreSeries.attachAxis(axisY)
                #adding the equation on top
                equation  = values['linRegEquations'][j-2]
                moreSeries.setName(equation)
                chart.legend().setVisible(True)
        
        #adding it on the ui
        self.ui.verticalLayout_7.addWidget(self.ui.chart_view)

        #making the current sheet button checked
        for i in range(len(self.sheets)):
            if self.sheets[i][0] == id:
                self.ui.horizontalLayout_4.itemAt(i).widget().setChecked(True)
                break

        if self.currentSheetId!= id:
            #making the button of the old sheet unchecked:
            for i in range(len(self.sheets)):
                if self.sheets[i][0] == self.currentSheetId:
                    self.ui.horizontalLayout_4.itemAt(i).widget().setChecked(False)
                    break

            self.currentSheetId = id #updating the current view id

    """
    looks for sheet according to id and returns data&values
    """
    def lookForSheet(self,id):
        sheet = []
        for x in self.sheets:
            if x[0]==id:
                sheet = x
                break
        
        if sheet == []:
            return None

        data = sheet[1]
        values = sheet[2]
        title = sheet[3]
        units = sheet[4]
        vertLin = sheet[5]
        horLin = sheet[6]
        return(data,values,title,units,vertLin,horLin)

    """
    adds a button in button list under the chart view to change view
    """    
    def setupSheetButton(self,name,id,Checked = True,maxWid = 70,minHei = 35):
        #adding button to button list
        buttonLabel=f"buttonSheet{id}"
        
        button = QPushButton(buttonLabel)
        button.setMaximumWidth(maxWid)
        button.setMinimumHeight(minHei)
        button.setObjectName(buttonLabel)
        button.setText(QCoreApplication.translate("MainWindow", name, None))
        button.setCheckable(True)
        button.setChecked(Checked)
        button.clicked.connect(lambda : self.showView(id))
        self.ui.horizontalLayout_4.addWidget(button)
        self.buttons.append(name)

    """
    displays an error message if issue happens
    """
    def displayError(self, message):
        error_dialog = QMessageBox(self)
        error_dialog.setIcon(QMessageBox.Warning)
        error_dialog.setWindowTitle("Error")
        error_dialog.setText(message)
        error_dialog.exec_()

    """
    displays information msgs
    """
    def displayTip(self,message):
        tip_dialog = QMessageBox(self)
        tip_dialog.setIcon(QMessageBox.Information)
        tip_dialog.setText(message)
        #removing buttons, and border
        tip_dialog.setStandardButtons(QMessageBox.NoButton)
        tip_dialog.setWindowFlags(tip_dialog.windowFlags() | Qt.FramelessWindowHint)
        #setting the message centered top
        parent_rect = self.geometry()
        tip_dialog.move(parent_rect.center().x()-200,parent_rect.top())
        tipTimer = QTimer
        tipTimer.singleShot(1000,tip_dialog.accept)
        tip_dialog.show()

    """
    transforms the sheet list into a dictionary for xmltodict.unparse
    """
    def sheetToDict(self,id):
        data,values,title,units = self.lookForSheet(id)[:4]
        dict = {'title' : title,'units':{'bottomUnit':units[0],'leftUnit':units[1]},'values':values,
            'data':{'YaxisData':' '.join(str(data_point)for data_point in data[0]),
                'XaxisData':' '.join(str(data_point) for data_point in data[1])}}
        return(dict)

    """
    updates the bragg angle (theta0)
    """
    def updateTheta(self, update = True, id = None):
        if id is None: id = self.currentSheetId #default update on current sheet
        try : data,values,_,units = self.lookForSheet(id)[:4]
        except TypeError:
            self.displayError("Error : no chart corresponding to ID found")
            return
        if values['Type'] != 'baseSheet': #only useful on basesheets
            return

        #adapting the theta computation to the bottom unit:
        if units[0] =='Q' or units[0] == 'log Q':
            bottomArray = (np.arcsin(values['Lambda']*data[1]/2)*180/np.pi)
        else:
            bottomArray = data[1]
        leftArray = data[0]

        values['Theta'] = np.sum(bottomArray*leftArray)/np.sum(leftArray)
        if update: #allowing for internal updates without visual changes if necessary
            self.ui.Theta.setText('Theta [°] : '+str(values['Theta']))

    """
    toggles the visibility of all the children of a certain frame or widget container
    """
    def toggleVisibility(self, frame = QWidget, visible = False):
        frame.setVisible(visible)
        for child in frame.findChildren(QWidget):
            self.toggleVisibility(child,visible)


    ########################################################
    #methods for the "edit" menu
    ########################################################

    """
    resets the zoom
    """
    def resetZoom(self):
        self.ui.chart_view.chart().zoomReset()
        self.updateTheta()

    """
    resets the zoom and undoes last memorized action
    """
    def undoAction(self):
        if self.undoPile[self.currentSheetId]:
            function,variables = self.undoPile[self.currentSheetId].pop()
        else:
            return
        if function == self.toggleUnit: #this needs to be part of the undoPile as it changes the behaviour of other actions
            function(True,False)  #false to not append the undoPile while undoing
            self.redoPile[self.currentSheetId].append([function, variables])
        elif function == self.noiseUpdateData: #to remove the noise correction, add an opposite noise correction
            id = int(self.lookForSheet(self.currentSheetId)[2].split(' ')[-1]) #tracking the id of the sheet on which filter applies
            for sheet in self.sheets: #updating the redoPile of each changed sheet
                if int(sheet[3].split(' ')[-1]) == id:
                    self.redoPile[sheet[0]].append([function, variables])
                    if sheet[0] != self.currentSheetId: #removing it from the linked undoPiles
                        self.undoPile[sheet[0]].pop()
            function(-variables[0],-variables[1],True,False)
        elif function == self.scales: #adjusting the variables to change the corresponding scale
            self.redoPile[self.currentSheetId].append([function, variables])
            vertLin,horLin = None,None
            if variables[0] != None:
                vertLin = not variables[0]
            if variables[1] != None:
                horLin = not variables[1]
            function(vertLin,horLin,True,False)
        elif function == self.polyreg: #removing data of previously added linear regression
            for sheet in self.sheets:
                if sheet[0] == self.currentSheetId:
                    if sheet[2]['linRegEquations']!=[]: #this list can be emptied by noise filter
                        dataset  = sheet[1].pop()
                        equation = sheet[2]['linRegEquations'].pop()
                        self.redoPile[self.currentSheetId].append([function, [dataset,equation]])
                        self.showView(self.currentSheetId)
                        break
        elif function == self.reduceDataset: #putting the old data back 
            for sheet in self.sheets:
                if sheet[0] == self.currentSheetId:
                    data = sheet[1].copy()
                    sheet[1] = variables
                    self.redoPile[self.currentSheetId].append([function,data])
                    self.showView(self.currentSheetId)
                    break

    """
    redoes last memorized action
    """
    def redoAction(self):
        if self.redoPile[self.currentSheetId]:
            function,variables = self.redoPile[self.currentSheetId].pop()
        else:
            return
        if function == self.toggleUnit: #this needs to be part of the undoPile as it changes the behaviour of other actions
            function(False, True)
        elif function == self.noiseUpdateData: #to remove the noise correction, add an opposite noise correction
            id = int(self.lookForSheet(self.currentSheetId)[2].split(' ')[-1]) #tracking the id of the sheet on which filter applies
            for sheet in self.sheets:#updating other redoPiles aswell
                if int(sheet[3].split(' ')[-1]) == id and sheet[0]!=self.currentSheetId:
                    self.redoPile[sheet[0]].pop()
            function(variables[0],variables[1],False,True)
        elif function == self.scales: #adjusting the variables to change the corresponding scale
            function(variables[0],variables[1],False,True)
        elif function == self.polyreg:
            for sheet in self.sheets:
                if sheet[0] == self.currentSheetId:
                    sheet[1].append(variables[0])
                    sheet[2]['linRegEquations'].append(variables[1])
                    self.undoPile[self.currentSheetId].append([self.polyreg,None]) #appending undoPile manually because the action function isnt called
                    self.showView(self.currentSheetId)
                    break
        elif function == self.reduceDataset:
            for sheet in self.sheets:
                if sheet[0] == self.currentSheetId:
                    data = sheet[1].copy()
                    sheet[1] = variables
                    self.undoPile[self.currentSheetId].append([self.reduceDataset,data]) #appending undoPile manually because the action function isnt called
                    self.showView(self.currentSheetId)
                    break

    """
    deletes a view and the button associated with it
    """
    def removeView (self,id):
        if self.sheets ==[]:
            return
        
        position = 0 #checking the position of items to remove (suposedly the same)
        for i in range(len(self.sheets)): #finding the corresponding button and sheet to remove
            if self.sheets[i][0]==id:
                position = i
                break
        self.sheets.pop(position)  #deleting the sheet from the sheet list
        self.buttons.pop(position)     #deleting the button from the button list
        self.undoPile[position] = [] #clearing the undopile to keep the id position the same
        self.redoPile[position] = [] #same for redoPile
        self.ui.horizontalLayout_4.takeAt(position).widget().deleteLater() #deleting the button widget

        if self.sheets!= []:
            self.showView(self.sheets[0][0])    #updating the view if there is another view to show
        else : 
            self.ui.verticalLayout_7.takeAt(0).widget().deleteLater() #deleting the current view if there are no others to show
            self.timer = NotImplemented

    """
    copies current view info (data/values)
    """
    def copyView (self):
        data,values,title,units,vertLin,horLin = self.lookForSheet(self.currentSheetId)
        self.copiedView = [data,values,title,units,vertLin,horLin]

    """
    pastes current copied view into a new one
    """
    def pasteView (self):
        if self.copiedView !=[]:
            self.setupNewChart(self.copiedView[0],self.copiedView[1],self.copiedView[2],self.copiedView[3],None,True,self.copiedView[4],self.copiedView[5])

    """
    removes view and saves it in the clipboard
    """
    def cutView (self):
        self.copyView()
        self.removeView(self.currentSheetId)


    ########################################################
    #methods for the "preprocessing" menu
    ########################################################

    """
    locks the current value of the dataset
    """
    def reduceDataset(self,show = True, undoing = False, redoing = False):
        #current sheet data & values
        data,values = self.lookForSheet(self.currentSheetId)[:2]
        if values['Type'] == 'combinedChart':
            self.displayTip('Not available for combined charts')
            return
        #getting the current borders of the plot area
        chart = self.ui.chart_view.chart()
        plot_area = chart.plotArea()
        # Map the plot area to data coordinates, and getting the indices in the data to know the zoom
        left_val = chart.mapToValue(plot_area.topLeft()).x()
        right_val = chart.mapToValue(plot_area.bottomRight()).x()
        left_ind,right_ind = self.subSeries(left_val,right_val,data[1])
        #updating the undoPile before reducing the data
        if not undoing: 
            self.undoPile[self.currentSheetId].append([self.reduceDataset,data.copy()])
            if not redoing: self.redoPile[self.currentSheetId] = []
        #reduce the dataset to the zoomed series
        for i in range(len(data)):
            data[i] = data[i][left_ind:right_ind]
        self.updateTheta()
        if show:
            self.showView(self.currentSheetId) 

    """
    allows for noise filter line toggling and for button control on that line
    """
    def noiseFilter(self):
        if self.ui.pushButtonNoiseFilter.text() == 'Noise Filter':
            values,title = self.lookForSheet(self.currentSheetId)[1:3]
            if values['Type']== 'combinedChart':
                self.displayTip('Noise Filter only applies to base or moment charts')
                return
            self.blockShowView = True #block showView
            #updating text
            self.ui.pushButtonNoiseFilter.setText('Apply filter')
            #setting the base values of the noise line extremities
            #looking for the id of the base sheet linked to current sheet
            id = int(title.split(' ')[-1]) #id of is at the end of the title
            data = self.lookForSheet(id)[0] #getting the data of the baseSheet to apply the noise on
            self.noise_coords = [[np.min(data[1]),np.min(data[0])],[np.max(data[1]),np.min(data[0])]]

            #setting up the ui for the filter buttons
            self.ui.pushButtonReduceDataset.setVisible(False)
            self.toggleVisibility(self.ui.frameGrid,True)
        else:
            #removing the filter buttons from the ui and restoring the other layout
            self.ui.pushButtonReduceDataset.setVisible(True)
            self.toggleVisibility(self.ui.frameGrid,False)  

            #updating the data
            (x1, y1), (x2, y2) = self.noise_coords[0],self.noise_coords[1]
            slope = (y2 - y1) / (x2 - x1)
            intercept = y1 - slope * x1
            if slope == intercept == 0: #avoiding useless computing if no noise line is needed
                self.ui.pushButtonNoiseFilter.setText('Noise Filter')
                self.noise_coords = []
                return
            
            self.noiseUpdateData(slope,intercept) #updating the data of all sheets linked to the one changed

            self.ui.pushButtonNoiseFilter.setText('Noise Filter')
            self.ui.pushButtonNoiseFilter.setChecked(False)
            self.noise_coords = []
            self.resetTextEdit()
            self.blockShowView = False #allowing sheet changes again

    def noiseUpdateData(self,slope,intercept,undoing = False,redoing = False):
        id = self.currentSheetId #tracking the id of the base sheet
        #checking the id of the base sheet
        for sheet in self.sheets:
            if sheet[0]==id:
                if sheet[2]['Type']!='baseSheet':
                    id = int(sheet[3].split(' ')[-1]) #last part of the title is the id of the baseSheet
                break
        for sheet in self.sheets:
            #updating the base sheet
            if sheet[0]==id: 
                for i in range(len(sheet[1][0])):
                    sheet[1][0][i]-=(intercept +slope*sheet[1][1][i])
                self.updateTheta(True,id) 
                theta = sheet[2]['Theta']
                unit = sheet[4][0]
                intensities = sheet[1][0]
                angles = sheet[1][1]
            #updating the values of the charts in link with the base chart
            elif int(sheet[3].split(' ')[-1]) == id and sheet[2]['Type']=='momentChart':
                k = int(sheet[3].split(' ')[0][1:]) #first part of title contains the order of the moment of the chart
                data_series,q_spread = self.momentData(intensities,angles,k,unit,theta,sheet[2]['Lambda'])
                sheet[1] = [data_series,q_spread] #updating the data of the moment chart
                sheet[2]['linRegEquations']=[] #resetting the linear regression equations because the noise has been changed
                sheet[2]['Theta']=theta
            elif int(sheet[3].split(' ')[-1]) == id and sheet[2]['Type']=='fourierChart':
                fftArray,fftFreq = self.fourierData(intensities)
                sheet[1] = [fftArray,fftFreq] #updating the data of the fourier transform
                sheet[2]['linRegEquations']=[] #resetting the linear regression equations because the noise has been changed
                sheet[2]['Theta']=theta
        #updating the undoPiles
        if not undoing: 
            for sheet in self.sheets: #updating each undoPile in relation with the noise filter
                if int(sheet[3].split(' ')[-1]) == id:
                    self.undoPile[sheet[0]].append([self.noiseUpdateData,[slope,intercept]])
                    if not redoing: self.redoPile[sheet[0]] = []
        self.showView(self.currentSheetId)

    """
    updates the noise filter line and the plot according to the new noise
    """
    def updateNoiseLine(self):
        sheetType = self.lookForSheet(self.currentSheetId)[1]['Type']

        self.noise_coords[0][1],self.noise_coords[1][1] = float(self.ui.textEditLeftVal.toPlainText()),float(self.ui.textEditRightVal.toPlainText())
        (x1, y1), (x2, y2) = self.noise_coords[0],self.noise_coords[1]
        # calculate slope and intercept of linear function
        slope = (y2 - y1) / (x2 - x1)
        intercept = y1 - slope * x1
        #case for basesheets (easy to update)
        if sheetType == 'baseSheet':
            newSeries =  []
            for sheet in self.sheets:
                if sheet[0]==self.currentSheetId:
                    for i in range(len(sheet[1][0])):
                        if sheet[1][0][i]-(intercept +slope*sheet[1][1][i])>0: #avoiding log scale conflict
                            newSeries.append(QPointF(sheet[1][1][i],sheet[1][0][i]-(intercept +slope*sheet[1][1][i])))
                    break
            self.updatePlotSeries(newSeries)
        #case for other sheets : have to recalculate everything
        elif sheetType == 'momentChart' : 
            #getting the id of the baseSheet linked to the sheet
            for sheet in self.sheets:
                if sheet[0]==self.currentSheetId:
                    id = int(sheet[3].split(' ')[-1]) #last part of the title is the id of the baseSheet
                    k = int(sheet[3].split(' ')[0][1:]) #first part contains the order of the moment
            data,values,_,units = self.lookForSheet(id)[:4]
            #updating intensity without changing the data yet:
            intensities = data[0].copy()
            angles = data[1].copy()
            for i in range(len(intensities)):
                intensities[i] -= (intercept+slope*angles[i])
            #updating a momentary theta
            if units[0] =='Q' or units[0] == 'log Q':
                bottomArray = (np.arcsin(values['Lambda']*angles/2)*180/np.pi)
                theta = np.sum(bottomArray*intensities)/np.sum(intensities)
            else: theta = np.sum(angles*intensities)/np.sum(intensities)
            #getting the new moment data
            data_series,q_spread = self.momentData(intensities,angles,k,units[0],theta,values['Lambda'])
            #creating new series
            newSeries = []
            for i in range(len(data_series)):
                if data_series[i]>0: #avoiding conflict of negative values in logarithmic scale
                    newSeries.append(QPointF(q_spread[i],data_series[i]))
            self.updatePlotSeries(newSeries)
        elif sheetType == 'fourierChart':
            for sheet in self.sheets:
                if sheet[0]==self.currentSheetId:
                    id = int(sheet[3].split(' ')[-1]) #last part of the title is the id of the baseSheet
            intensities = self.lookForSheet(id)[0][0]
            fftArray,fftFreq = self.fourierData(intensities)
            #creating new series
            newSeries = []
            for i in range(len(fftArray)):
                if fftArray[i]>0: #avoiding conflict of negative values in logarithmic scale
                    newSeries.append(QPointF(fftFreq[i],fftArray[i]))
            self.updatePlotSeries(newSeries)

    def updatePlotSeries(self,newSeries,oldSeries = QtCharts.QScatterSeries):
        chart = self.ui.chart_view.chart()
        for series in chart.series():
            if isinstance(series,oldSeries):
                series.replace(QPolygonF(newSeries))

    """
    resets the text edits to 0 to avoid having base values from the last noise filter
    """
    def resetTextEdit(self):
        self.ui.textEditLeftVal.textChanged.disconnect(self.updateNoiseLine)
        self.ui.textEditRightVal.textChanged.disconnect(self.updateNoiseLine)
        self.ui.textEditLeftVal.setText('0')
        self.ui.textEditRightVal.setText('0')
        self.ui.textEditLeftVal.textChanged.connect(self.updateNoiseLine)
        self.ui.textEditRightVal.textChanged.connect(self.updateNoiseLine)

    """
    reloads the view with the changed scales
    """
    def scales(self,vertLin,horLin,undoing = False, redoing = False):
        #checking for changes to avoid wrongful memorization of actions & view reloading
        curVertlin,curHorlin = self.lookForSheet(self.currentSheetId)[4:6]
        if curVertlin == vertLin:
            vertLin = None
        if curHorlin == horLin:
            horLin = None
        if self.sheets ==[]:
            return                
        for sheet in self.sheets: #looking for the sheet (lookforsheet doesn't allow to change booleans)
            if sheet[0]==self.currentSheetId:
                if vertLin != None:
                    sheet[5]=vertLin
                    if not vertLin and sheet[4][1][:4]!='log ':#adjusting the left unit name
                        sheet[4][1] = 'log ' + sheet[4][1]
                    elif vertLin and sheet[4][1][:4] =='log ':
                        sheet[4][1] = sheet[4][1][4:]
                if horLin != None:
                    sheet[6]=horLin
                    if not horLin and sheet[4][0][:4]!='log ': #adjusting the bottom unit name
                        sheet[4][0] = 'log ' + sheet[4][0]
                    elif horLin and sheet[4][0][:4] =='log ':
                        sheet[4][0] = sheet[4][0][4:]    
                break
        if horLin != None or vertLin != None: #avoiding meaningless updates
            self.showView(self.currentSheetId)
            if not undoing : 
                self.undoPile[self.currentSheetId].append([self.scales,[vertLin,horLin]])
                if not redoing: self.redoPile[self.currentSheetId] = []

    """
    adapts the scale for horizontal combo box
    """
    def comboBoxScale (self):
        horizontalScale = self.ui.comboBoxHorizontalScale.currentText()
        verticalScale = self.ui.comboBoxVerticalScale.currentText()
        if horizontalScale == 'linear': horlin = True
        else : horlin = False
        if verticalScale =='linear': vertlin = True
        else : vertlin = False
        self.scales(vertlin,horlin)

    """
    regression of order k on current zoomed amount   
    """
    def polyreg(self,k,undoing = False, redoing = False):
        data,values,_,_,vertLin,horLin = self.lookForSheet(self.currentSheetId)[:6]
        chart = self.ui.chart_view.chart()
        if chart == NotImplemented:
            return
        if values['Type']=='combinedChart':
            self.displayTip('Not available on combined charts')
            return
        
        #getting the borders of the zoom indices
        plot_area = chart.plotArea()
        
        left_val = chart.mapToValue(plot_area.topLeft()).x()
        right_val = chart.mapToValue(plot_area.bottomRight()).x()
        left_ind,right_ind = self.subSeries(left_val,right_val,data[1])
        
        data_series = np.zeros(len(data[1]))
        equation = ''  #equation of the regression that will be stored to be shown and saved

        #getting the regression coefficients
        if vertLin: #adapting the regression with the scales of the graph
            equation+='y ='
            if horLin: #both scales linear, standard regression
                coefficients = np.polyfit(data[1][left_ind:right_ind],data[0][left_ind:right_ind],deg = k)
                for i in range(k+1):
                    data_series+=coefficients[k-i]*np.power(data[1],i) #coefficients are given in decreasing power order
                    if i ==0:
                        equation += f'{coefficients[k-i]:.3e}'
                    elif i ==1:
                        equation +=f' + {coefficients[k-i]:.3e}*x'
                    else:
                        equation +=f' + {coefficients[k-i]:.3e}*x^{i}'

            else : #horizontal scale logarithmic (as in kmoments)
                coefficients = np.polyfit(np.log(data[1][left_ind:right_ind]),data[0][left_ind:right_ind],deg = k)
                for i in range(k+1):
                    data_series+=coefficients[k-i]*np.power(np.log(data[1]),i)
                    if i ==0:
                        equation += f'{coefficients[k-i]:.3e}'
                    elif i ==1:
                        equation +=f' + {coefficients[k-i]:.3e}*log(x)'
                    else:
                        equation +=f' + {coefficients[k-i]:.3e}*log(x)^{i}'

        else : #vertical logarithmic
            equation+='log(y) ='
            if horLin: #horizontal linear
                coefficients = np.polyfit(data[1][left_ind:right_ind],(np.log10(data[0][left_ind:right_ind])),deg = k)
                for i in range(k+1):
                    data_series+=(coefficients[k-i]*np.power(data[1],i))
                    if i ==0:
                        equation += f'{coefficients[k-i]:.3e}'
                    elif i ==1:
                        equation +=f' + {coefficients[k-i]:.3e}*x'
                    else:
                        equation +=f' + {coefficients[k-i]:.3e}*x^{i}'

            else : #both logarithmic
                coefficients = np.polyfit(np.log(data[1][left_ind:right_ind]),(np.log10(data[0][left_ind:right_ind])),deg = k)
                for i in range(k+1):
                    data_series+=(coefficients[k-i]*np.power(np.log(data[1]),i))
                    if i ==0:
                        equation += f'{coefficients[k-i]:.3e}'
                    elif i ==1:
                        equation +=f' + {coefficients[k-i]:.3e}*log(x)'
                    else:
                        equation +=f' + {coefficients[k-i]:.3e}*log(x)^{i}'
            data_series = np.power(data_series, 10) #adjusting for vertical log scale

        #saving the last linear regression coefficients for data
        values['linRegEquations'].append(equation)
        data.append(data_series)
        self.showView(self.currentSheetId)
        if not undoing :
            self.undoPile[self.currentSheetId].append([self.polyreg,None])
            if not redoing: self.redoPile[self.currentSheetId] = []

    """
    changes the unit from theta to q and viceversa if it is possible
    """
    def toggleUnit(self, undoing = False, redoing = False):
        try : data,values,_,units,_,horlin = self.lookForSheet(self.currentSheetId)[:6]
        except TypeError:
            self.displayError("Error : no chart corresponding to ID found")
            return
        if values['Type']!='baseSheet': #only useful for basesheets
            self.displayTip('Only useful for base data sheets')
            return
        if units[0] =='Angle Theta (°)' or units[0]=='log Angle Theta (°)':
            data[1] = 2*np.sin(data[1]*np.pi/180)/values['Lambda']
            if horlin:
                units[0] = 'Q'
            else:
                units[0] = 'log Q'
        elif units[0] =='Q' or units[0] == 'log Q':
            data[1] = np.arcsin(values['Lambda']*data[1]/2)*180/np.pi
            if horlin:
                units[0] = 'Angle Theta (°)'
            else:
                units[0] = 'log Angle Theta (°)'
        for sheet in self.sheets:
            if sheet[0] == self.currentSheetId:
                sheet[1][1] = data[1]
                sheet[4] = units
                break
        self.showView(self.currentSheetId,animations = False)
        self.ui.chart_view.chart().setAnimationOptions(QtCharts.QChart.SeriesAnimations)
        if not undoing: 
            self.undoPile[self.currentSheetId].append([self.toggleUnit,None]) #updating undo pile if not undoing
            if not redoing: self.redoPile[self.currentSheetId] = [] #if new action, should clear redo pile 

    ########################################################
    #methods for the "Operations" menu
    ########################################################

    """
    computes the k'th order restricted moment of a selected data series
    """
    def kMoment (self,k,id,show = False, addToUndo = True):
        #locking the values of the current zoom
        if id == self.currentSheetId : self.reduceDataset(show = show,undoing = not addToUndo) #theta update + dataset reduction set to be undoable by default
        data,values,title,units = self.lookForSheet(id)[:4]

        if values['Type'] != 'baseSheet':
            self.displayTip('Only use Operation tools on base sheets (extracted from a .xrdml file)')
            return
        
        #adjusting the type of the chart (here to prevent the same operation to be tried on a modified chart)
        new_values = values.copy()
        new_values['Type']='momentChart'
        new_values['linRegEquations'] = [] #linear regression
        #adjusting units (no longer measurement number)
        new_units = ['','']
        new_units[0]= 'log q'
        new_units[1] = 'Computed Intensity'

        #computing moments:        
        data_series,q_spread = self.momentData(data[0],data[1],k,units[0],new_values['Theta'],new_values['Lambda'])

        #setting up the new sheets
        if k == 4: #special case for M4, because we divide by q^2
            new_units[0] = 'q'
            self.setupNewChart([data_series,q_spread],new_values,
                'M'+str(k)+' chart of '+title,new_units,'M4/q² '+str(id),show,True,True)
        else:
            #setting up new chart with the series in mind
            self.setupNewChart([data_series,q_spread],new_values,
                'M'+str(k)+' chart of '+title,new_units,'M'+str(k)+' '+str(id),show,True,False)

    """
    compute the dataseries to be shown for the moment charts
    """
    def momentData(self,intensities,angles,k,unit,theta,lamb):
        #adapting bottom unit
        if unit =='Q' or unit == 'log Q':
            Q0 = np.sin(theta*np.pi/180)*2/lamb
            q_set = angles - Q0
        elif unit == 'Angle Theta (°)' or unit =='log Angle Theta (°)':
            q_set = np.array((2/lamb)*(np.sin(angles*np.pi/180)-np.sin(theta*np.pi/180)))
        #computing the full integral I(s)dq
        integ = np.trapz(intensities,q_set)

        #creating a linearly spread out q dataset 
        q_spread = np.linspace(0,min(np.max(q_set),-np.min(q_set)),momentPoints) #avoiding going out of bounds on the max
        q_spread = q_spread[1:] #avoiding the zero to not cause logarithm scale issues
        data_series = [] #dataset to append that will contain the moment integral on given q in q_spread
        

        #computing the moment on each point of q_spread
        curIntSum = 0 #integral of known q points between -Q and Q to which we add the sides on which we interpolate 
        
        left, right = self.subSeries(0,0,q_set) #getting the first indices over q=0 as a starting point (we move to both sides from the middle)
        for q in q_spread:
            #we integrate on the right side up until we interpolate the last point
            while right+1 < len(q_set) and q_set[right+1] <q:
                #adding the trapezoid to the right times the average q value to the power k
                curIntSum += ((intensities[right+1]*(q_set[right+1]**k)+intensities[right]*(q_set[right]**k))*abs(q_set[right+1]-q_set[right])/2)
                right +=1
            #then on the left side up until we have to interpolate
            while left> 0 and q_set[left-1]>-q:
                curIntSum += ((intensities[left-1]*(q_set[left-1]**k)+intensities[left]*(q_set[left]**k))*abs(q_set[left-1]-q_set[left])/2) #trapezoid to the right
                left -=1
            
            #we interpolate the values of the last 2 points without changing the sum to use it again, while being careful not to overstep
            try : intensQRight = intensities[right]+ ((q-q_set[right])/(q_set[right+1]-q_set[right]))*(intensities[right+1]-intensities[right])
            except IndexError:
                if right<len(intensities):
                    intensQRight = intensities[right]
                else :
                    intensQRight = intensities[len(intensities)]
            try : intensQLeft = intensities[left]- ((q_set[left]+q)/(q_set[left]-q_set[left-1]))*(intensities[left]-intensities[left-1])
            except IndexError:
                if left>0:
                    intensQLeft = intensities[left]
                else:
                    intensQLeft = intensities[0]
            #appending the values to the data_series
            data_series.append(curIntSum +((intensQRight*(q**k)+intensities[right]*(q_set[right]**k))*abs(q-q_set[right])/2)
                        + ((intensQLeft*((-q)**k)+intensities[left]*(q_set[left]**k))*abs(-q-q_set[left])/2))
        data_series = data_series/integ #adjusting to the full integral

        if k == 4: #special case for k == 4
            for i in range(len(data_series)):
                data_series[i]= data_series[i] / q_spread[i]**2 #adjusting for  q^2
        return(data_series,q_spread)

    """
    takes boundaries of a growing series and returns the subseries indices corresponding to the subseries in the boundaries
    """    
    def subSeries(self,left,right,series):
        left_ind=0
        right_ind = 0
        while right_ind <len(series) and right>series[right_ind]:
            right_ind+=1
            if series[left_ind]<left:
                left_ind+=1
        return (left_ind,right_ind)

    """
    computes the fast fourier transform of selected data series
    """
    def fourier(self,id,show = False, addToUndo = True):
        #locking the values of the current zoom
        if id == self.currentSheetId : self.reduceDataset(show = show,undoing = not addToUndo) #this also updates theta

        try :data,values,title = self.lookForSheet(id)[:3]
        except TypeError:
            self.displayError("Error : no chart corresponding to ID found")
            return
        if values['Type'] != 'baseSheet':
            self.displayTip('Only use Operation tools on base sheets (extracted from a .xrdml file)')
            return

        #adjusting the type of the chart (here to prevent the same operation to be tried on a modified chart)
        new_values = values.copy()
        new_values['Type']='fourierChart'
        #adjusting units (no longer measurement number)
        new_units = ['','']
        new_units[0]= 'Freq'
        new_units[1]='FFT/amplitude'

        #computing fft
        fftArray,fftFreq = (self.fourierData(data[0]))

        self.setupNewChart([fftArray,fftFreq],new_values,'Fourier transform of '+title,
            new_units,'Fourier '+str(id),False,True,False)

    def fourierData(self,intensities):
        fftArray = np.abs(np.fft.fft(intensities)) #taking the magnitude
        fftFreq = np.fft.fftfreq(len(fftArray))

        fftArray = fftArray[1:int(len(intensities)/2)]/fftArray[0] # Exclude sampling frequency & normalize
        fftFreq = fftFreq[1:len(intensities)] #removing 0 to avoid log scale conflict
        return(fftArray,fftFreq)

    """
    launches all operations on given base sheet
    """
    def all(self):
        id = self.currentSheetId
        self.kMoment(2,id,False,True) #only adding one data reduction to the undo pile
        self.kMoment(3,id,False,False)
        self.kMoment(4,id,False,False)
        self.fourier(id,False,False)


#########################################
#### Dialog class to get user selection
#########################################

class SelectionDialog(QDialog):
    def __init__(self, items):
        super().__init__()
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.items = items
        self.selected_items = []
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.MultiSelection)
        for item in self.items:
            self.list_widget.addItem(item)
        self.select_button = QPushButton("Select")
        self.select_button.clicked.connect(self.select_items)
        layout = QVBoxLayout()
        layout.addWidget(self.list_widget)
        layout.addWidget(self.select_button)
        self.setLayout(layout)
        
    def select_items(self):
        self.selected_items = [item.text() for item in self.list_widget.selectedItems()]
        self.accept()

if __name__=="__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


