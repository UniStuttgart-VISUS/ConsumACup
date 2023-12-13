from PyQt5.QtChart import QBarSet, QChart
from PyQt5.QtCore import Qt
from PyQt5.QtChart import QBarCategoryAxis, QValueAxis, QStackedBarSeries
from PyQt5.QtGui import QColor
import random 


class DrilldownBarSeries(QStackedBarSeries):
    def __init__(self, categories, maxValue, parent=None):
        super().__init__(parent)
        self.m_DrilldownSeries = {}
        self.m_categories = categories
        self.m_maxValue = maxValue

    def mapDrilldownSeries(self, index, drilldownSeries):
        self.m_DrilldownSeries[index] = drilldownSeries

    def drilldownSeries(self, index):
        return self.m_DrilldownSeries.get(index)

    def categories(self):
        return self.m_categories

    def maxValue(self):
        return self.m_maxValue
    
    def setMaxValue(self, newMax):
        self.m_maxValue = newMax


class DrilldownChart(QChart):
    def __init__(self, reset_button, name, categorie_list, resources_list, parent=None, wFlags=Qt.WindowFlags()): #legendChart, resources_list
        super().__init__(parent, wFlags)
        self.m_currentSeries = None
        self.m_axisX = QBarCategoryAxis()
        self.m_axisY = QValueAxis()
        

        #first_layer_series = None
        self.name = name
        self.categorie_list = categorie_list
        self.resources_list = resources_list
        self.resetButton= reset_button

        self.addAxis(self.m_axisX, Qt.AlignBottom)
        self.addAxis(self.m_axisY, Qt.AlignLeft)
        self.m_axisY.setTitleText("# in packs")  # Update the Y-axis title

        self.resetButton.clicked.connect(self.genChart)
        self.resetButton.setVisible(False)  # Initially hidden

        self.legend().setVisible(False)
        self.legend().setAlignment(Qt.AlignRight)

        self.m_axisY.setMinorTickCount(1)  # Set the number of minor ticks on the Y-axis
        self.m_axisY.setTickType(QValueAxis.TicksDynamic)  # Set the tick type to dynamic

    def changeSeries(self,series):
        self.m_currentSeries = series
        self.removeAllSeries()
        self.addSeries(series)
        series.attachAxis(self.m_axisY)

        # Set categories for the x-axis
        self.m_axisX.setCategories(series.categories())
        self.m_axisY.setRange(0, series.maxValue())
        if series.maxValue() > 14:
            self.m_axisY.setTickInterval(int(series.maxValue()/7))  # Set the tick interval to 2
        elif series.maxValue() < 7:
            self.m_axisY.setTickInterval(1)
        else:
            self.m_axisY.setTickInterval(2)

    def handleClicked(self, index):
        category = self.m_currentSeries.categories()[index]
        drilldownSeries = self.m_currentSeries.drilldownSeries(index)
        self.legend().setVisible(True)
        self.legend().setMaximumWidth(170)
        
        self.m_axisX.hide()

        if drilldownSeries is not None:
            self.changeSeries(drilldownSeries)
            self.setTitle(category)
            self.resetButton.setVisible(True)

    def genChart(self): #name: chart name as str, categorie_list: 1st layer categories (x-axis), legendChart: legend,resources_list: drill down charts x-Axis
        self.legend().setVisible(False)
        self.m_axisX.show()
        first_layer_series = DrilldownBarSeries(self.categorie_list, 320, self)
        first_layer_series.setName(self.name)
        first_layer_series.setLabelsVisible(True)

        for categorie, specific_resource in enumerate(self.resources_list):
            names_specific_resource= []
            for ele in specific_resource:
                names_specific_resource.append(ele[0])

            second_layer_series = DrilldownBarSeries(names_specific_resource, 80, self)
            second_layer_series.setLabelsVisible(True)
            first_layer_series.mapDrilldownSeries(categorie, second_layer_series) # categorie is a numeric (0,1,2)

        # Enable drilldown from for first layer series
        first_layer_series.clicked.connect(self.handleClicked)

        color_list_reds = [(128,0,0), (165,42,42), (220,20,60), (255,99,71), (205,92,92), (233,150,122), (250,128,114)]
        color_list_yellows = [(255,165,0), 	(255,215,0), (184,134,11), (218,165,32), (189,183,107) ]
        color_list_greens = [(128,128,0), (154,205,50), (85,107,47), (0,100,0), (0,128,0), (46,139,87), (60,179,113)]
        color_list_blues = [(32,178,170), (0,128,128), (70,130,180), (100,149,237), (25,25,112), (0,0,205), (65,105,225) ]
        color_list_violets = [(75,0,130),  (72,61,139), (106,90,205), (139,0,139),(186,85,211), (199,21,133) ]
        color_list = [color_list_reds, color_list_yellows, color_list_greens, color_list_blues, color_list_violets]

        maxR = 0
        for i, specific_resource in enumerate(self.resources_list):

            len_s = len(specific_resource) # second layer
            pos = 0 # second layer and color pick set
            sum_per_res = 0
            max_per_drill = 0

            for entry in specific_resource:
                color_set = color_list[pos % len(color_list)]
                resource_set = QBarSet(entry[0])
                drill_set = QBarSet(entry[0])
                if i == 0:# if coffee or sugar
                    
                    # second layer
                    for j in range(len_s):
                        if j == pos:
                            drill_set.append(round(entry[1] / 1000 , 2))
                        else:
                            drill_set.append(0)
                    
                    resource_set.append(round(entry[1] / 1000 , 2))  # Divide the data by 1000 for coffee and sugar
                    resource_set.append(0)
                    resource_set.append(0)
                    rgb_tuple = random.choice(color_set)
                    color = QColor(rgb_tuple[0], rgb_tuple[1], rgb_tuple[2]) 
                    drill_set.setColor(color)
                    resource_set.setColor(color)
                elif i == 1:

                    # second layer
                    for j in range(len_s):
                        if j == pos:
                            drill_set.append(round(entry[1]/1000 , 2))
                        else:
                            drill_set.append(0)

                    # drill_set.append(entry[1])
                    resource_set.append(0)
                    resource_set.append(round(entry[1]/1000 , 2))
                    resource_set.append(0)
                    rgb_tuple = random.choice(color_set)
                    color = QColor(rgb_tuple[0], rgb_tuple[1], rgb_tuple[2]) 
                    drill_set.setColor(color)
                    resource_set.setColor(color)
                elif i == 2:
                    # second layer
                    for j in range(len_s):
                        if j == pos:
                            drill_set.append(round(entry[1] / 1000 , 2))
                        else:
                            drill_set.append(0)

                    resource_set.append(0)
                    resource_set.append(0)
                    resource_set.append(round(entry[1] / 1000, 2))
                    rgb_tuple = random.choice(color_set)
                    color = QColor(rgb_tuple[0], rgb_tuple[1], rgb_tuple[2]) 
                    drill_set.setColor(color)
                    resource_set.setColor(color)
                first_layer_series.append(resource_set)
                
                # second layer
                first_layer_series.drilldownSeries(i).append(drill_set)

                pos +=1

                max_per_drill =  max(max_per_drill, sum(drill_set))
                sum_per_res = sum_per_res + sum(resource_set)
            first_layer_series.drilldownSeries(i).setMaxValue(max_per_drill)
            maxR = max(maxR, sum_per_res)
        
        first_layer_series.setMaxValue(maxR)

        self.changeSeries(first_layer_series)
        self.setTitle(first_layer_series.name())
        self.resetButton.setVisible(False)