import time
import threading 
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import ipywidgets as widgets
from IPython.display import display
from cycler import cycler

blues_balanced = [ #a nice color scheme
    '#0F4C81',  
    '#1A7CB0',  
    '#3DB0DD',  
    '#80CFE5',  
    '#B9E6EE'   
]

#configure plotting settings to make nice plots
plt.rcParams['axes.prop_cycle'] = cycler(color=blues_balanced) #set the cycler to the nice blue color scheme
plt.rcParams['font.size'] = 12
plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['figure.figsize'] = (6,4)
plt.rcParams['figure.dpi'] = 96 #the dpi is default because we need to plot quickly! 
plt.rcParams['legend.frameon'] = False

rng = np.random.default_rng()

def noisyGaussian(x, noiseLevel):
    '''A quick function that simulates what a live might look like in the PLQY.'''
    output = np.zeros_like(x)
    center = np.mean(x)
    width = np.std(x)/2
    output += np.exp( -((x-center)/width)**2  )
    output += rng.random(len(x))*noiseLevel
    return output

def increasingNoisyGaussian(x, noiseLevel, timeElapsed):
    '''A quick function that simulates what a live might look like in the PLQY.
    Now also includes a growth factor.'''
    output = np.zeros_like(x)
    center = np.mean(x)
    width = np.std(x)/2
    output += np.exp( -((x-center)/width)**2  )
    output += rng.random(len(x))*noiseLevel
    timeScalar = 5 - (5*np.exp(-timeElapsed))
    return output*timeScalar

xx = np.linspace(200, 800, 1024) #test data

class PL_GUI: #The class that contains the GUI. Currently pairs to X data; will eventually pair to a spectrometer
    #(In the future, this means we can have 2 GUIs easily open for absorbance studies!)
    def __init__(self, xx):
        self.xx = xx

        # initalize variables
        self.live = False 
        self.newDataPresent = False
        self.loop_thread = None
        self.liveCount = 1
        self.staticCount = 1
        self.live_data = [np.insert(self.xx, 0, np.inf)]

        #create the layout parameters
        column_layout = widgets.Layout(flex='1', padding='5px', display='flex', flex_flow='column')
        widget_layout = widgets.Layout(width='100%')
        input_style = {'description_width': '110px'}

        #create the widgets
        self.exposure = widgets.FloatText(
            description='Exposure (ms)', 
            value=200, 
            layout=widget_layout, 
            style=input_style
        )
        self.noOfAv_input = widgets.IntText(
            description='Averages', 
            value=1, 
            layout=widget_layout, 
            style=input_style
        )
        self.modeSelector = widgets.Button(
            description='Start live', 
            layout=widget_layout
        )
        self.saveFig = widgets.Button(
            description='Save current figure', 
            layout=widget_layout
        )
        self.text_output = widgets.Textarea(
            value='GUI Initialized.\n',
            disabled=True,
            layout=widgets.Layout(width='100%', height='100%', min_height='80px')
        )

        # link widgets to their respective functions
        self.modeSelector.on_click(self.onModeSwap)
        self.exposure.observe(self.onExposureUpdate, names='value')
        self.noOfAv_input.observe(self.onAvUpdate, names='value')
        self.saveFig.on_click(self.onFigSaveRequested)

        #create storage variables
        self.exposureTime = self.exposure.value
        self.noOfAv = self.noOfAv_input.value
        
        #create the plot
        plt.ioff() #disable standard behavior; prevents two plots from appearing
        plt.close('all') 
        self.fig, self.ax = plt.subplots(figsize=(10, 4)) #create the plot
        self.ax.set_xlabel('Wavelength (nm)')
        self.ax.set_ylabel('Intensity (a.u.)')
        self.data, = self.ax.plot(self.xx, noisyGaussian(self.xx, 0.1), label='Live', color='#062346') #populate inital data
        self.ax.legend()
        plt.ion() # Restore standard behavior

        #create the widget layout
        col1 = widgets.VBox([self.exposure, self.noOfAv_input], layout=column_layout)
        col2 = widgets.VBox([self.modeSelector, self.saveFig], layout=column_layout)
        col3 = widgets.VBox([self.text_output], layout=column_layout)

        bottom_section = widgets.HBox([col1, col2, col3], layout=widgets.Layout(width='100%')) #area below plot

        self.layout = widgets.VBox([ #stack plot and area
            self.fig.canvas, 
            bottom_section
        ], layout=widgets.Layout(width='100%'))

    def show(self):
        '''Wrapper to display the GUI.'''
        display(self.layout)

    def log(self, message, clear=False):
        '''Helper function to push text to console.'''
        if clear:
            self.text_output.value = ""
        self.text_output.value += f"{message}\n"

    def onModeSwap(self, button):
        '''When the mode swap button is pressed:'''
        if self.live:
            #self.log('Live feed terminating...') #debugging
            self.stopLiveFeed()
            button.description = 'Start live'
        else:
            #self.log('Starting feed...', clear=True) #debugging
            self.startLiveFeed()
            button.description = 'Stop live'

    def startLiveFeed(self):
        '''Function to start the live feed and data writing in the background via Threads.'''
        self.live = True
        self.live_start_time = time.time()
        self.loop_thread = threading.Thread(target=self._live_loop, daemon=True) #the thread must be a daemon to stop it from running in the background
        #self.log("A thread has been initialized.") #debugging
        self.loop_thread.start()

    def stopLiveFeed(self):
        '''For parity with starting, a function that disables the live feed and saves the file.'''
        self.live = False #we let the thread die by itself, to avoid issues with join()
        data_matrix = np.array(self.live_data).transpose()
        self.saveCurrentFigure(data_matrix)
    
    def saveCurrentFigure(self, data, fromLive=True):
        '''Save the current data, either the live dataset or the static CSV.'''
        if fromLive:
            file_name = f'live_data_{self.liveCount}_{self.exposureTime}ms_{self.noOfAv}averages.csv'
            np.savetxt(file_name, data, fmt='%.3f', delimiter=",", comments="",)
            self.log(f"Saved live data as {file_name}")
            self.liveCount += 1
        else:
            file_name = f'static_spectrum_{self.staticCount}_{self.exposureTime}ms_{self.noOfAv}averages.csv'
            np.savetxt(file_name, data, fmt='%.3f', delimiter=",", comments="",)
            self.log(f"Saved live data as {file_name}")
            self.staticCount += 1
    
    def requestData(self):
        '''Function to request data from the spectrometer with the current GUI settings. Currently, simulates data.'''
        out = np.zeros_like(self.xx)
        time.sleep((self.exposureTime/1000)*self.noOfAv) #simulate the time required for the spectrometer to collect the dataset
        if self.live:
            for _ in range(self.noOfAv):
                out += increasingNoisyGaussian(self.xx, 1/(self.exposureTime*0.1), time.time()-self.live_start_time)
            out /= self.noOfAv #simulate averaging
        else:
            for _ in range(self.noOfAv):
                out += noisyGaussian(self.xx, 1/(self.exposureTime*0.1))
            out /= self.noOfAv #simulate averaging
        return out

    def _live_loop(self):
        '''The drawing loop that runs in the background. Eventally, will also request data from the spectrometer and draw it.'''
        while self.live:
            self.newestData = self.requestData() #request data from the spectrometer
            self.data.set_ydata(self.newestData) #draw the new data
            self.currMax = np.max(self.newestData)
            self.ax.set_ylim(-0.05*self.currMax, 1.2*self.currMax)
            self.fig.canvas.draw_idle() #draw the data to the canvas
            self.live_data.append( np.insert(self.newestData, 0, time.time()-self.live_start_time) ) #append the new dataset

    def onExposureUpdate(self, change):
        ''' Function to update the exposure time (.value may cause issues with threading)'''
        self.exposureTime = change['new']
    
    def onAvUpdate(self, change):
        ''' Function to update the number of spectrums averaged (.value may cause issues with threading)'''
        self.noOfAv = change['new']

    def onFigSaveRequested(self, button_object):
        '''Saves the spectrum to a .csv and then pins spectrum to the plot for reference.'''
        if self.live: #if live, take the newest live data
            y_data = self.newestData
        else: #if not live, request data from the spectrometer
            y_data = self.requestData()
        static_data = np.array([self.xx, y_data]).transpose() #create the array to save
        self.ax.plot(self.xx, y_data, label=f"Spectrum {self.staticCount}") #plot the new data
        self.ax.legend()
        self.fig.canvas.draw_idle() #redraw the canvas, including legend
        self.saveCurrentFigure(static_data, fromLive=False) #save the new static figure