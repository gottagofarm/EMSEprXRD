#this script takes the ui of xrdui and does stuff

import os
import sys

from PySide2.QtGui import QPainter
from PySide2.QtCharts import QtCharts
from PySide2.QtGui import QColor
#math imports
import numpy as np
import xrdtools

from xrdui import *

#setting up the default path for the files to open
path = 'c:/Users/ahtim/Documents/taf/projet_recherche/code'
pathChanged = False #put this to true if you changed the path



class MainWindow(QMainWindow):
    """
    ui & functionalities setup
    """
    def __init__(self,parent=None):
        QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.attributeSetup()

        self.setMinimumSize(800,600)

        self.linkActions()

        self.show

    """
    setting up all attributes that keep data in memory
    """
    def attributeSetup(self):
        self.sheets = [] #saving the different datasets used to create charts and show views
        self.states = [] #saving the states to undo and redo later
        self.buttons =[] #list of buttons corresponding to the diff views
        self.id = 0 #incrementing id of charts & views
        self.currentSheetId = 0 #keeping track of the view we're in
        self.copiedView = [] #clipboard of copied Sheet
        self.initialZoom = NotImplemented #previous zoom before undoing (not used for now (too bad))
        self.ui.chart_view = NotImplemented
        self.momentPoints = 500 #setting up the number of points on moment graphs


        self.ui.pushButtonHorizontalReframe.setCheckable(True)
        self.ui.pushButtonHorizontalReframe.setChecked(False)

    """
    links all the different buttons and shortcuts to the corresponding functions
    """
    def linkActions(self):
        self.ui.actionOpen.triggered.connect(self.openfiles)
        self.ui.pushButtonPlus.clicked.connect(self.openfiles)

        #edit menu actions
        self.ui.actionDelete_Chart.triggered.connect(lambda : self.removeView(self.currentSheetId))
        self.ui.actionCopy.triggered.connect(self.copyView)
        self.ui.actionPaste.triggered.connect(self.pasteView)
        self.ui.actionCut.triggered.connect(self.cutView)
        self.ui.actionUndo.triggered.connect(self.undoAction)
        self.ui.actionRedo.triggered.connect(self.redoAction)

        #preprocessing menu actions
        self.ui.pushButtonHorizontalReframe.clicked.connect(self.horizontalReframe) #setting up the horizontal reframe button
        self.ui.actionHorizontalLinear.triggered.connect(lambda : self.scales(None,True)) 
        self.ui.actionHorizontalLogarithmic.triggered.connect(lambda : self.scales(None,False))
        self.ui.actionVerticalLinear.triggered.connect(lambda : self.scales(True,None))
        self.ui.actionVerticalLogarithmic.triggered.connect(lambda : self.scales(False,None))
        self.ui.actionMean.triggered.connect(lambda : self.polyreg(0))
        self.ui.actionLinear_Regression.triggered.connect(lambda : self.polyreg(1))

        #operations menu actions
        self.ui.actionM1.triggered.connect(lambda : self.kMoment(1,self.currentSheetId))
        self.ui.actionM2.triggered.connect(lambda : self.kMoment(2,self.currentSheetId))
        self.ui.actionM3.triggered.connect(lambda : self.kMoment(3,self.currentSheetId))
        self.ui.actionM4_q.triggered.connect(lambda : self.kMoment(4,self.currentSheetId))
        self.ui.actionFourier.triggered.connect(lambda : self.fourier(self.currentSheetId))
        self.ui.actionAll.triggered.connect(self.all)


    ########################################################
    #methods for the "file" menu
    ########################################################

    """
    openfiles is the function linked to open / Ctrl+O
    """
    def openfiles(self):
        #browsing for the file
        if not pathChanged :
            path = ''
        fname, filter = QFileDialog.getOpenFileName(None, 'Open file', path, 'xrdml files(*.xrdml)')
        
        fpath = ''
        for x in fname:
            fpath += x
        try : file = open(fpath)
        except FileNotFoundError:
            print("Please enter a valid file (.xrdml)")
        #getting the values from the file
        data,values = self.parseXrdml(file.name)
        title = f'Chart {self.id}'
        units = ['Angle 2Theta (°)','log Intensity']
        #setting up the chart view
        self.setupNewChart(data,values,title,units,None,True,False,True)

    ########################################################
    #useful methods
    ########################################################

    """
    takes an xrmdl file and parses it to get the useful data&values
    """
    def parseXrdml(self,file):
        #dummy series & values 
        values = {'Theta':0,'Lambda':0,'SD':0,'time':0}
        data = [1,1]

        parsedfile = xrdtools.read_xrdml(file)
        
        #associating the values with the chart
        values['Theta']=(parsedfile['2Theta'][-1]+parsedfile['2Theta'][0])/4
        values['SD']=0
        values['Lambda']=parsedfile['kAlpha1']
        values['Time']=parsedfile['time'][0]
        values['Type']='baseSheet'
        #storing the intensity data (normalized according to time per step), and the angle data
        data = [np.array(parsedfile['data']),np.array(parsedfile['2Theta']/2)]

        return (data,values)

    """
    sets up a new chart
    """
    def setupNewChart(self,data,values = "None",title = "Title",units=["Angle (°)","Intensity"],
            buttonName = None,show = True,vertLin = True,horLin =True):
            
        #creating new chart in list
        self.sheets.append([self.id,data,values,title,units,vertLin,horLin])
        #setting up the chart and showing it
        if show:
            self.showView(self.id)
        #setting up the button to change the chart viewed
        if buttonName == None:
            self.setupSheetButton("Sheet "+str(self.id),self.id)
        else : 
            self.setupSheetButton(buttonName,self.id)
        #print(self.sheets)

        self.id+=1 #incrementing chart id

    """
    shows the view corresponding to set of data and values
    """
    def showView(self,id):
        try : self.ui.verticalLayout_7.takeAt(0).widget().deleteLater() #deleting the current view if there is one
        except AttributeError:
            pass
        
        try : data,values,title,units,vertLin,horLin = self.lookForSheet(id) #checking if the id corresponds to a sheet
        except TypeError:
            self.displayError("Error : no chart corresponding to ID found")
            return
        

        #showing the values:
        self.ui.Lambda.setText('Lambda [A] : '+str(values['Lambda']))
        self.ui.SD.setText('SD [mm] : '+str(values['SD']))
        self.ui.Theta.setText('Theta [°] : '+str(values['Theta']))


        #axis setup
        if horLin : #checking for horizontal linear scale
            axisX = QtCharts.QValueAxis()
        else :
            axisX = QtCharts.QLogValueAxis()
            axisX.setBase(10)
        axisX.setTitleText(units[0])

        if vertLin : #checking for vertical linear scale
            axisY = QtCharts.QValueAxis()
        else :
            axisY = QtCharts.QLogValueAxis()
            axisY.setBase(10)
        axisY.setTitleText(units[1])
        axisY.setRange(np.min(data[0]),np.max(data[0])) #blocking the vertical scale to avoid the other series going over

        # series creation from data
        #turning the X and Y data into a Qseries for the chart
        series = QtCharts.QScatterSeries() 
        for i in range(len(data[0])):
            series.append(data[-1][i],data[0][i])
        series.setMarkerSize(3)

        #chart setup
        chart = QtCharts.QChart()

        chart.setTitle(title)
        chart.setAnimationOptions(QtCharts.QChart.SeriesAnimations)

        chart.addAxis(axisX,Qt.AlignBottom)
        chart.addAxis(axisY,Qt.AlignLeft)
        chart.legend().setVisible(False)

        #adding the main series
        chart.addSeries(series)
        series.attachAxis(axisX)
        series.attachAxis(axisY)

        #adding possible line series on top:
        for j in range(1,len(data)-1):
            moreSeries = QtCharts.QLineSeries()
            moreSeries.setName(f'moreSeries{j}')
            for i in range(len(data[j])):
                moreSeries.append(data[-1][i],data[j][i])
            moreSeries.setColor(QColor("cyan"))
            chart.addSeries(moreSeries)
            moreSeries.attachAxis(axisX)
            moreSeries.attachAxis(axisY)

        #widget setup
        self.ui.chart_view = QtCharts.QChartView(chart)
        self.ui.chart_view.setRenderHint(QPainter.Antialiasing)
        self.ui.chart_view.chart().setTheme(QtCharts.QChart.ChartThemeDark)
        
        sizePolicy = QSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
        self.ui.chart_view.setSizePolicy(sizePolicy)

        self.ui.verticalLayout_7.addWidget(self.ui.chart_view)
        self.ui.chart_view.setRubberBand(QtCharts.QChartView.HorizontalRubberBand) #allowing for zoom by default

        self.currentSheetId = id #updating the current view

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
    def setupSheetButton(self,name,id,maxWid = 70,minHei = 35):
        #adding button to button list
        buttonLabel=f"buttonSheet{id}"
        
        self.buttons.append(buttonLabel)
        button = QPushButton(buttonLabel)
        button.setMaximumWidth(maxWid)
        button.setMinimumHeight(minHei)
        button.setObjectName(buttonLabel)
        button.setText(QCoreApplication.translate("MainWindow", name, None))
        button.clicked.connect(lambda : self.showView(id))
        self.ui.horizontalLayout_4.addWidget(button)

    """
    displays an error message if issue happens
    """
    def displayError(self, message):
        error_dialog = QMessageBox(self)
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setWindowTitle("Error")
        error_dialog.setText(message)
        error_dialog.exec_()


    ########################################################
    #methods for the "edit" menu
    ########################################################

    """
    resets the zoom
    """
    def undoAction(self):
        #if self.ui.chart_view.chart() != NotImplemented :
        #    chart = self.ui.chart_view.chart()
        #    x_data = [point.x() for series in chart.series() for point in series.pointsVector()]
        #    self.initialZoom =(x_data[0],x_data[-1])
        self.ui.chart_view.chart().zoomReset()
        

    """
    rezooms in
    """
    def redoAction(self):
        self.displayError("Sorry this functionality hasn't been implemented yet (too bad)")
        #if self.initialZoom != NotImplemented:
        #    x_range = self.initialZoom
        #    self.ui.chart_view.chart().zoomInX(x_range)
        #    self.initialZoom = NotImplemented


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
        self.ui.horizontalLayout_4.takeAt(position).widget().deleteLater() #deleting the button widget

        if self.sheets!= []:
            self.showView(self.sheets[0][0])    #updating the view if there is another view to show
        else : 
            self.ui.verticalLayout_7.takeAt(0).widget().deleteLater() #deleting the current view if there are no others to show

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
    allows for a horizontal zoom in (toggles the ability to zoom) and locks the zoom on the chart (sussy business)
    """
    def horizontalReframe(self):
        if self.ui.pushButtonHorizontalReframe.isChecked():
            # Disable zooming
            self.ui.chart_view.setRubberBand(QtCharts.QChartView.NoRubberBand)
            self.ui.pushButtonHorizontalReframe.setText('Enable Zoom')

            #lock the zoom by changing the data in case the sheet is reloaded
            chart = self.ui.chart_view.chart()
            plot_area = chart.plotArea()

            # Map the plot area to data coordinates, and getting the indices in the data to know the zoom
            left_val = chart.mapToValue(plot_area.topLeft()).x()
            right_val = chart.mapToValue(plot_area.bottomRight()).x()
            data = self.lookForSheet(self.currentSheetId)[0]

            left_ind,right_ind = self.subSeries(left_val,right_val,data)
            #reduce the dataset to the zoomed series
            data[0] = data[0][left_ind:right_ind]
            data[-1] = data[-1][left_ind:right_ind]

        else:
            # Enable zooming
            self.ui.chart_view.setRubberBand(QtCharts.QChartView.HorizontalRubberBand)
            self.ui.pushButtonHorizontalReframe.setText('Disable Zoom')

    """
    reloads the view with the changed scales
    """
    def scales(self,vertLin,horLin):
        if self.sheets ==[]:
            return                
        for sheet in self.sheets: #looking for the sheet (lookforsheet doesn't allow to change booleans)
            if sheet[0]==self.currentSheetId:
                if vertLin != None:
                    sheet[5]=vertLin
                    if not vertLin and sheet[4][1][:4]!='log ':
                        sheet[4][1] = 'log ' + sheet[4][1]
                    elif vertLin and sheet[4][1][:4] =='log ':
                        sheet[4][1] = sheet[4][1][4:]
                if horLin != None:
                    sheet[6]=horLin
                    if not horLin and sheet[4][0][:4]!='log ':
                        sheet[4][0] = 'log ' + sheet[4][0]
                    elif horLin and sheet[4][0][:4] =='log ':
                        sheet[4][0] = sheet[4][0][4:]    
                break
        self.showView(self.currentSheetId)

    """
    regression of order k on current zoomed amount   
    """
    def polyreg(self,k):
        data = self.lookForSheet(self.currentSheetId)[0]
        chart = self.ui.chart_view.chart()
        if chart == NotImplemented:
            return
        
        #getting the borders of the zoom indices
        plot_area = chart.plotArea()
        
        left_val = chart.mapToValue(plot_area.topLeft()).x()
        right_val = chart.mapToValue(plot_area.bottomRight()).x()
        left_ind,right_ind = self.subSeries(left_val,right_val,data[-1])

        #getting the regression coefficients
        coefficients = np.polyfit(data[-1][left_ind:right_ind],data[0][left_ind:right_ind],deg = k)

        data_series = np.zeros(len(data[-1]))
        for i in range(k+1):
            data_series+=coefficients[i]*np.power(data[-1],k-i) #coefficients are given in decreasing power order
        data.insert(1,data_series)
        self.showView(self.currentSheetId)

    ########################################################
    #methods for the "Operations" menu
    ########################################################

    """
    computes the k'th order restricted moment of a selected data series
    """
    def kMoment (self,k,id):
        try : data,values,title = self.lookForSheet(id)[:3]
        except TypeError:
            self.displayError("Error : no chart corresponding to ID found")
            return
        if values['Type'] != 'baseSheet':
            self.displayError('Only use Operation tools on base sheets (extracted from a .xrdml file)')
            return
        
        intensities = data[0]

        #adjusting the type of the chart (here to prevent the same operation to be tried on a modified chart)
        new_values = values.copy()
        new_values['Type']='momentChart'
        #adjusting units (no longer measurement number)
        new_units = ['','']
        new_units[0]= 'log Q'
        new_units[1] = 'Computed Intensity'


        # Map the plot area to data coordinates, and getting the indices in the data to know the zoom
        chart = self.ui.chart_view.chart()
        plot_area = chart.plotArea()
        
        left_val = chart.mapToValue(plot_area.topLeft()).x()
        right_val = chart.mapToValue(plot_area.bottomRight()).x()
        left_ind,right_ind = self.subSeries(left_val,right_val,data[-1])

        #computing q for zoomed intensity:
        q_set = np.array((2/values['Lambda'])*(np.sin(data[-1]/2)-np.sin(values['Theta'])))

        #computing the full integral I(s)dq
        integ = np.trapz(intensities[left_ind:right_ind],q_set[left_ind:right_ind])

        #creating a linearly spread out q dataset 
        q_spread = np.linspace(0,np.max(q_set[left_ind:right_ind]),self.momentPoints)
        q_spread = q_spread[1:] #avoiding the zero to not cause logarithm scale issues
        data_series = [] #dataset to append that will contain the moment integral on given q in q_spread
        

        #computing the moment on each point of q_spread
        curIntSum = 0 #integral of known q points between -Q and Q to which we add the sides on which we interpolate 
        
        left, right = self.subSeries(0,0,q_set) #getting the first indices over q=0 as a starting point (we move to both sides from the middle)
        for q in q_spread:
            #we integrate on the right side up until we interpolate the last point
            while q_set[right+1] <q:
                #adding the trapezoid to the right times the average q value to the power k
                curIntSum += ((intensities[right+1]*(q_set[right+1]**k)+intensities[right]*(q_set[right]**k))*abs(q_set[right+1]-q_set[right])/2)
                right +=1
            #then on the left side up until we have to interpolate
            while q_set[left-1]>-q:
                curIntSum += ((intensities[left-1]*(q_set[left-1]**k)+intensities[left]*(q_set[left]**k))*abs(q_set[left-1]-q_set[left])/2) #trapezoid to the right
                left -=1
            
            #we interpolate the values of the last 2 points without changing the sum to use it again, while being careful not to overstep
            try : intensQRight = intensities[right]+ ((q-q_set[right])/(q_set[right+1]-q_set[right]))*(intensities[right+1]-intensities[right])
            except IndexError:intensQRight = intensities[right]
            try : intensQLeft = intensities[left]- ((q_set[left]+q)/(q_set[left]-q_set[left-1]))*(intensities[left]-intensities[left-1])
            except IndexError:intensQLeft = intensities[left]
            
            #appending the values to the data_series
            data_series.append(curIntSum +((intensQRight*(q**k)+intensities[right]*(q_set[right]**k))*abs(q-q_set[right])/2)
                        + ((intensQLeft*((-q)**k)+intensities[left]*(q_set[left]**k))*abs(-q-q_set[left])/2))
        data_series = data_series/integ #adjusting to the full integral

        #setting up the new sheets
        if k == 4: #special case for M4, because we divide by q^2
            for i in range(len(data_series)):
                data_series[i]= data_series[i] / q_spread[i]**2 #adjusting for  q^2
            self.setupNewChart([data_series,q_spread],new_values,
                'M'+str(k)+' chart of '+title,new_units,'M4/q² '+str(id),False,True,False)
        else:
            #setting up new chart with the series in mind
            self.setupNewChart([data_series,q_spread],new_values,
                'M'+str(k)+' chart of '+title,new_units,'M'+str(k)+' '+str(id),False,True,False)

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
    def fourier(self,id):
        #the setup is similar to the kmoments, the details + showing the displayerror and ending the function is  useful so its let as is

        try :data,values,title = self.lookForSheet(id)[:3]
        except TypeError:
            self.displayError("Error : no chart corresponding to ID found")
            return
        if values['Type'] != 'baseSheet':
            self.displayError('Only use Operation tools on base sheets (extracted from a .xrdml file)')
            return

        #adjusting the type of the chart (here to prevent the same operation to be tried on a modified chart)
        new_values = values.copy()
        new_values['Type']='fourierChart'
        #adjusting units (no longer measurement number)
        new_units = ['','']
        new_units[0]= 'Freq'
        new_units[1]='FFT/amplitude'

        chart = self.ui.chart_view.chart()
        plot_area = chart.plotArea()

        # Map the plot area to data coordinates, and getting the indices in the data to know the zoom
        left_val =chart.mapToValue(plot_area.topLeft()).x()
        right_val = chart.mapToValue(plot_area.bottomRight()).x()

        left_ind,right_ind = self.subSeries(left_val,right_val,data[-1])

        #setting up the array for the np.fft.fft
        tempArray = np.zeros(right_ind-left_ind)
        for i in range (len(tempArray)):
            tempArray[i]=data[0][i+left_ind]  #storing the intensities in a np.array for the fft
        fftArray = np.abs(np.fft.fft(tempArray)) #taking the magnitude
        fftFreq = np.fft.fftfreq(len(fftArray))

        fftArray = fftArray[1:int(len(tempArray)/2)]/fftArray[0] # Exclude sampling frequency & normalize
        fftFreq = fftFreq[1:len(tempArray)]

        self.setupNewChart([fftArray,fftFreq],new_values,'Fourier transform of '+title,
            new_units,'Fourier '+str(id),False,True,True)

    """
    launches all operations on given base sheet
    """
    def all(self):
        id = self.currentSheetId
        self.kMoment(2,id)
        self.kMoment(3,id)
        self.kMoment(4,id)
        self.fourier(id)


if __name__=="__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


