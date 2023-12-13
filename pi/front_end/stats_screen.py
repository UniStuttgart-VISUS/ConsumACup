from PyQt5.QtChart import *
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from PyQt5.QtCore import *
from PyQt5.uic import loadUi
import numpy as np
from datetime import datetime, timedelta
import matplotlib

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.ticker import MaxNLocator
import matplotlib.dates as mdates
from matplotlib.transforms import IdentityTransform

from front_end.login_screen import LoginScreen

from PyQt5.uic import loadUi
from PyQt5.QtWidgets import *  

import back_end.session as session
import back_end.coffee_config as coffee_config
from back_end.manage_db import DBManager, convert_str_to_datetime_with_timezone

from scipy.interpolate import make_interp_spline
from scipy import interpolate

from front_end.charts.drilldown_chart import *

# Ensure using PyQt5 backend
matplotlib.use('QT5Agg')

class StatsScreen(QMainWindow):
    rating_list = []
    def __init__(self, stackedPages, nfcThread=None):

        super().__init__()
        loadUi("front_end/ui_files/stats_screen.ui", self)

        self.stackedPages = stackedPages
        self.nfcThread = nfcThread
        
        self.chartContainer.setStyleSheet("background-color: white;")
        self.lay = QHBoxLayout(self.chartContainer)

        self.chartContainer_2.setStyleSheet("background-color: white;")
        self.lay_2 = QHBoxLayout(self.chartContainer_2)
        
        self.cbGlobalStats.activated.connect(lambda: self.change_chart(False))
        self.cbTimeLine.activated.connect(lambda: self.change_chart(True))

        self.tabWidget.currentChanged.connect(self.logged_in)

        self.cbPersonalStats.activated.connect(lambda: self.change_personal_chart(False))
        self.cbPersonalTimeLine.activated.connect(lambda: self.change_personal_chart(True))

        # initial chart when first option in combo box is selected
        self.displayBeanRating()
        self.cbTimeLine.hide()
        self.cbPersonalTimeLine.hide()

    def logged_in(self):
        if session.LOGGED_IN:
            print("LOGGED IN FOR PERSONAL STATS")
            self.change_personal_chart(False)
        else:
            if self.tabWidget.currentIndex() == 1:# if global tab is active
                print("NOT LOGGED IN FOR PERSONAL STATS; PLEASE LOG IN")
                goingTo = "STATS"
                self.login = LoginScreen(stackedPages=self.stackedPages, goingTo=goingTo, nfcThread=self.nfcThread)
                self.stackedPages.addWidget(self.login.loginPage)
                self.stackedPages.setCurrentIndex(self.stackedPages.currentIndex() + 1)
                print("GONE TO LOGIN SCREEN from stats_screen 74")

    def reset_layout(self):
        for i in reversed(range(self.lay.count())): 
            self.lay.itemAt(i).widget().deleteLater()

    def reset_layout_2(self):
        for i in reversed(range(self.lay_2.count())): 
            self.lay_2.itemAt(i).widget().deleteLater()

    def change_personal_chart(self, subchart):
        if not subchart:
            self.cbPersonalTimeLine.hide()
        self.reset_layout_2()
        cb_choice = self.cbPersonalStats.currentText()
        if cb_choice == "Please select ...":
            self.cbPersonalTimeLine.hide()
            self.reset_layout_2()
        elif cb_choice == "My Coffee Over Time":
            print("My Coffee Over Time")
            # hides day option from combobox 
            view = self.cbPersonalTimeLine.view()
            view.setRowHidden(3,True)
            self.cbPersonalTimeLine.show()
            cb_timeline = self.cbPersonalTimeLine.currentText()
            self.displayPersonalCoffeeOverTime(cb_timeline)
        elif cb_choice =="My Coffee Hours":
            print("b")
            self.displayScatterPlot()
        elif cb_choice =="My Debt Compared to Average":
            print("My Debt Compared to Average")
            self.cbPersonalTimeLine.hide()
            self.displayDebtsToAvg()
        elif cb_choice =="My Total Coffee Costs":
            print("My Total Coffee Costs")
            self.cbPersonalTimeLine.hide()
            self.displayTotalCosts()

    def change_chart(self, subchart):
        if not subchart:
            self.cbTimeLine.hide()
        self.reset_layout()
        cb_choice = self.cbGlobalStats.currentText()
        if cb_choice == "Bean Rating":
            print("Bean Rating")
            self.displayBeanRating()
        elif cb_choice =="Earliest and Latest Coffee":
            print("Earliest and Latest Coffee")
            self.displayScatterPlot()
        elif cb_choice =="Coffee Type Trends":
            print("Coffee Type Trends")
            # hides day option from combobox 
            view = self.cbTimeLine.view()
            view.setRowHidden(3,True)
            self.cbTimeLine.show()
            cb_timeline = self.cbTimeLine.currentText()
            self.displayThemeRiver(cb_timeline)
        elif cb_choice =="Peak Hours Visualization":
            print("Peak Hours Visualization")
            self.displayPeakHours()
        elif cb_choice =="Highscore Coffee Consumption":
            print("Highscore Coffee Consumption")
            view = self.cbTimeLine.view()
            view.setRowHidden(3, False)
            self.cbTimeLine.show()
            cb_timeline = self.cbTimeLine.currentText()
            self.displayHighscore(cb_timeline)
        elif cb_choice =="Debt Ranking":
            print("Debt Ranking")
            self.displayDebts()
        elif cb_choice =="Purchase Overview":
            print("Purchase Overview")
            self.displayResourcePurchase()
        elif cb_choice =="Refill Ranking":
            print("Refill Ranking")
            self.displayRefill()


    ### PERSONAL STATS
    def displayPersonalCoffeeOverTime(self, timeline):
        self.fig = plt.figure()
        self.canvas = FigureCanvas(self.fig)
        self.lay_2.addWidget(self.canvas)

        db = DBManager()
        if timeline =="year":
            print("year")
            self.data = db.getPersonalCoffeeOverYear(session.USER_ID)
        elif timeline == "month":
            print("month")
            self.data = db.getPersonalCoffeeOverMonth(session.USER_ID)
        elif timeline == "week":
            print("week")
            self.data = db.getPersonalCoffeeOverWeek(session.USER_ID)
        db.close_connection()

        dict_date_to_string={'01':'Jan','02':'Feb','03':'Mar','04':'Apr',
                             '05':'May','06':'Jun','07':'Jul','08':'Aug',
                             '09':'Sep', '10':'Oct','11':'Nov','12':'Dec'}

        x = []
        y= []
        for entry in self.data:
            print(entry[0])
            x.append(entry[0])
            y.append(entry[1])

        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.set(ylabel='#Coffee')

        if timeline == "year":
            x_ = []
            for v in x:
                x_.append(dict_date_to_string[v[-2:]])

            x_[0] = x_[0] + " "
            ax.set_xticks(np.arange(len(x_)))
            ax.set_xticklabels(x_)
            print(x_)
            print(y)
            ax.plot(x_, y)
            ax.set_ylim(ymin=0)

        elif timeline == "month":
            date = []
            for v in x:
                current_date = datetime.strptime(v, "%Y-%m-%d")
                date.append(current_date)

            # Format the x-axis labels for a clean date display
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.tick_params(axis='x', labelrotation = 45)
            ax.plot(date, y, linestyle='-', marker='o')
            ax.set_ylim(ymin=0)

        elif timeline == "week":
            date = []
            for v in x:
                current_date = datetime.strptime(v, "%Y-%m-%d")
                date.append(current_date)

            ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.plot(date, y)
            ax.set_ylim(ymin=0)
            # ax.set_xlabel('Last 7 Days')

        # ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        self.canvas.draw()

    def displayDebtsToAvg(self):
        self.fig = plt.figure()
        self.canvas = FigureCanvas(self.fig)
        self.lay_2.addWidget(self.canvas)

        db = DBManager()
        self.user_debt = db.getDebts(session.USER_ID)
        db.close_connection()
        db = DBManager()
        self.avg_debt = db.getAvgDebtsWOUser(session.USER_ID)[0]
        db.close_connection()

        self.fig.clear()
        ax = self.fig.add_subplot(111)

        fruits = ['You','Avg']
        counts = [self.user_debt, self.avg_debt]
        bar_labels = ['red', 'blue']
        bar_colors = ['tab:red', 'tab:blue']

        ax.bar(fruits, counts, label=bar_labels, color=bar_colors)

        ax.set_ylabel('Debt in €')

    def displayTotalCosts(self):
        self.fig = plt.figure()
        self.canvas = FigureCanvas(self.fig)
        self.lay_2.addWidget(self.canvas)

        db = DBManager()
        self.total_coffee = db.getTotalUserCoffees(session.USER_ID)
        total_coffee_cost = db.getTotalCoffeesEuro(session.USER_ID)
        db.close_connection()

        total_coffee_str = f"You consumed in total {self.total_coffee} coffees."
        total_coffee_cost_str = f"You totally spend {total_coffee_cost:.2f}€ on coffee. Bravo!"

        self.fig.clear()
        # ax = self.fig.add_subplot(111)
        self.fig.text(20, 200, total_coffee_cost_str, color="red", fontsize=20,
         transform=IdentityTransform())
        
        self.fig.text(20, 300,total_coffee_str, color="red", fontsize=20,
         transform=IdentityTransform())


    ### GLOBAL STATS
    def displayResourcePurchase(self):
        def labelling_func(pct, allvals):
            absolute = int(np.round(pct/100.*np.sum(allvals)))
            return f"{pct:.1f}%\n({absolute:d} €)"

        self.fig = plt.figure()
        self.canvas = FigureCanvas(self.fig)
        self.lay.addWidget(self.canvas)

        db = DBManager()
        self.data = db.getPurchaseOverview()
        db.close_connection()
        
        labels=[]
        sizes=[]
        for entry in self.data:
            labels.append(entry[0])
            sizes.append(entry[1])

        self.fig.clear()
        ax = self.fig.add_subplot(111)

        wedges, texts, autotexts = ax.pie(sizes, autopct=lambda pct: labelling_func(pct, sizes),
                        textprops=dict(color="w"))
        
        ax.legend(wedges, labels,
          title="Buyers",
          loc="center left",
          bbox_to_anchor=(1, 0, 0.5, 1))
        plt.tight_layout()
        plt.setp(autotexts, size=10, weight="bold")

    def displayRefill(self):  
        db = DBManager()
        self.data = db.getRefillPerUser()
        db.close_connection()

        series = QStackedBarSeries()
        i = 0
        names = []
        for entry in self.data:
            zeros_arr = [0]*len(self.data)
            zeros_arr[i]=entry[1]
            if "anonym" in entry[0]:
                n = entry[0]+"_"+str(i)  
            else:
                n = entry[0]
            curr_set = QBarSet(n)
            curr_set.append(zeros_arr)
            series.append(curr_set)
            names.append(n)
            i+=1

        series.setLabelsVisible(True)
        series.labelsPosition()

        chart = QChart()
        chart.addSeries(series)

        chart.setAnimationOptions(QChart.SeriesAnimations)

        axisX = QBarCategoryAxis()
        axisX.append(names)
        chart.addAxis(axisX, Qt.AlignBottom)
        series.attachAxis(axisX)

        axisY = QValueAxis()
        # axisY.setLabelFormat("%d")
        chart.addAxis(axisY, Qt.AlignLeft)
        series.attachAxis(axisY)

        chart.legend().setVisible(False)

        chartView = QChartView(chart)
        self.lay.addWidget(chartView)

    def displayDebts(self):  
        db = DBManager()
        self.bill_data = db.getDebtsRanking()
        db.close_connection()

        series = QStackedBarSeries()
        i = 0
        names = []
        for entry in self.bill_data:
            zeros_arr = [0]*len(self.bill_data)
            zeros_arr[i]= -1.0 * entry[1]
            if "anonym" in entry[0]:
                n = entry[0]+"_"+str(i)  
            else:
                n = entry[0]
            curr_set = QBarSet(n)
            curr_set.append(zeros_arr)
            series.append(curr_set)
            names.append(n)
            i+=1

        series.setLabelsVisible(True)
        series.labelsPosition()

        chart = QChart()
        chart.addSeries(series)

        chart.setAnimationOptions(QChart.SeriesAnimations)

        axisX = QBarCategoryAxis()
        axisX.append(names)
        chart.addAxis(axisX, Qt.AlignBottom)
        series.attachAxis(axisX)

        axisY = QValueAxis()
        # axisY.setLabelFormat("%d")
        chart.addAxis(axisY, Qt.AlignLeft)
        series.attachAxis(axisY)

        chart.legend().setVisible(False)

        chartView = QChartView(chart)
        self.lay.addWidget(chartView)


    def displayHighscore(self, timeline):
        db = DBManager()
        if timeline =="year":
            print("year")
            self.bill_data = db.getHighscoreLast365Days()
        elif timeline == "month":
            print("month")
            self.bill_data = db.getHighscoreLast30Days()
        elif timeline == "week":
            print("week")
            self.bill_data = db.getHighscoreLast7Days()
        elif timeline == "day":
            print("week")
            self.bill_data = db.getHighscoreToday()
        db.close_connection()

        series = QHorizontalStackedBarSeries()
        i = 0
        names = []
        for entry in self.bill_data:
            zeros_arr = [0]*len(self.bill_data)
            zeros_arr[i]=entry[1]
            curr_set = QBarSet(entry[0])
            curr_set.append(zeros_arr)
            series.append(curr_set)
            names.append(entry[0])
            i+=1

        series.setLabelsVisible(True)
        series.labelsPosition()

        # font = QFont()
        # #font.setPixelSize(20)
        # font.setPointSize(30)
        # font.setBold= True
        # series.labelFont = font

        chart = QChart()
        chart.addSeries(series)

        chart.setAnimationOptions(QChart.SeriesAnimations)

        axisY = QBarCategoryAxis()
        axisY.append(names)
        chart.addAxis(axisY, Qt.AlignLeft)
        series.attachAxis(axisY)

        axisX = QValueAxis()
        axisX.setLabelFormat("%d")
        chart.addAxis(axisX, Qt.AlignBottom)
        series.attachAxis(axisX)

        chart.legend().setVisible(False)

        chartView = QChartView(chart)
        self.lay.addWidget(chartView)

    def displayBeanRating(self):
            db = DBManager()
            self.rating_list = db.getBeanProductNameAndRating()
            db.close_connection()

            print(self.rating_list)
            series = QHorizontalStackedBarSeries()

            average_rating_beans = {}
            for bean in self.rating_list:
                try:
                    average_rating_beans[bean[0]].append(bean[1])
                except KeyError:
                    average_rating_beans[bean[0]] = []
                    average_rating_beans[bean[0]].append(bean[1])
            
            pos = 0
            for key,value in average_rating_beans.items():
                avg = round(sum(value)/len(value), 1)
                bean_set = QBarSet(key)
                for j in range(len(average_rating_beans)):
                    if pos == j:
                        bean_set.append(avg)
                    else:
                        bean_set.append(0)
                series.append(bean_set)
                pos += 1
    
            series.setLabelsVisible(True)
            series.labelsPosition()

            chart = QChart()

            font = QFont()
            font.setPixelSize(20)
            chart.setTitleFont(font)

            chart.addSeries(series)
            chart.setTitle("Bean Rating")
            chart.setAnimationOptions(QChart.SeriesAnimations)
            
            axisX = QValueAxis()
            # axisX = QBarCategoryAxis()
            # axisX.append(categories)
            axisX.setLabelFormat("%d")
            axisX.setRange(0,5)
            chart.createDefaultAxes()
            chart.setAxisX(axisX, series)

            categories = []
            for key in average_rating_beans:
                categories.append(key)

            axisY = QBarCategoryAxis()
            axisY.append(categories)
            # axisY.setLabelFormat("%.0f")
            chart.setAxisY(axisY, series)
    
            chart.legend().setVisible(False)
            chart.legend().setAlignment(Qt.AlignBottom)
    
            chartView = QChartView(chart)

            self.lay.addWidget(chartView)

    def displayScatterPlot(self):
        self.fig = plt.figure()
        self.canvas = FigureCanvas(self.fig)
        self.lay.addWidget(self.canvas)

        db = DBManager()
        self.data = db.getEarliestAndLatestDrinkerLast7Days()
        db.close_connection()

        x = []
        x_day_name = []
        earliest_drinker={}
        latest_drinker={}

        for entry in self.data:
            day = datetime.strptime(entry[0], "%Y-%m-%d")
            early_time = convert_str_to_datetime_with_timezone(entry[1])
            late_time = convert_str_to_datetime_with_timezone(entry[3])
            if day.strftime('%m-%d') in x: continue
            x.append(day.strftime('%m-%d'))
            x_day_name.append(day.strftime('%a'))
            # TODO: check if only goes to except case. Maybe not needed
            try:
                earliest_drinker[day].update({early_time:entry[2]})
                latest_drinker[day].update({late_time:entry[4]})
            except KeyError:
                earliest_drinker[day] = {early_time:entry[2]}
                latest_drinker[day] = {late_time:entry[4]}

        hours = set()
        
        y_earliest = []
        y_latest = []
        label_earliest = []
        label_latest =[]

        for key in earliest_drinker:
            for key_inner in earliest_drinker[key]:
                h = key_inner.hour
                hours.add(h)
                y_earliest.append(h)
                label_earliest.append((earliest_drinker[key][key_inner], (key.strftime('%m-%d'),h)))

        for key in latest_drinker:
            for key_inner in latest_drinker[key]:
                h = key_inner.hour
                hours.add(h)
                y_latest.append(h)
                label_latest.append((latest_drinker[key][key_inner], (key.strftime('%m-%d'),h)))

        y_earliest = np.asarray(y_earliest)
        y_latest = np.asarray(y_latest)

        y_range = np.arange(min(hours),max(hours))

        self.fig.clear()
        ax = self.fig.add_subplot(111)

        ax.scatter(x, y_earliest, s=150,c=np.array([[0,0,0.4]]), alpha=0.5, marker="d",
                label="Earliest")
        for entry in label_earliest:
            print(entry[0])
            print(entry[1])
            ax.annotate(entry[0], entry[1])

        ax.scatter(x, y_latest, s=300,c=np.array([[0.9,0.7,0.1]]), alpha=0.5, marker="*",
                label="Latest")
        for entry in label_latest:
            ax.annotate(entry[0], entry[1])
        ax.set_ylabel("Time of Day")
        
        ax.set_xticklabels(x_day_name)

        ax.set_yticks(y_range[::2])

        ax.legend()


    def displayThemeRiver(self, timeline):
        self.figure2 = plt.figure()
        self.canvas2 = FigureCanvas(self.figure2)
        self.lay.addWidget(self.canvas2)

        # monthly
        db = DBManager()
        if timeline =="year":
            self.bill_data = db.getBillCoffeeLast12MonthByCoffeeType()
        elif timeline == "month":
            self.bill_data = db.getBillCoffeeLast30DaysByCoffeeType()
        elif timeline == "week":
            self.bill_data = db.getBillCoffeeLast7DaysByCoffeeType()
        db.close_connection()

        # creating dict of getBillCoffeeLast12MonthByCoffeeType data
        print(self.bill_data)
        key_value={}
        for entry in self.bill_data:
            try:
                if entry[2]!=0:
                    key_value[entry[0]].update({str(entry[1]):entry[2]})
            except KeyError:
                if entry[2]!=0:
                    key_value[entry[0]] = {str(entry[1]):entry[2]}

        # creating x-ais values and labels_set(coffee_types) 
        x_date=[]
        labels_set=set()
        for key in key_value:
            x_date.append(key)
            for key_inner in key_value[key]:
                labels_set.add(key_inner)

        # creating dict of empty y arrays for y-axis
        ys = {}
        for ct in labels_set:
            ys[ct]=[]

        # filling y-axis accordingly
        for key in key_value:
            for coffee_type in labels_set:
                try:
                    ys[coffee_type].append(key_value[key][coffee_type])
                except KeyError:
                    ys[coffee_type].append(0)
        
        # graphic labels and y axis
        labels = []
        y2=[]
        # vstack = []
        for ct in labels_set:
            labels.append(ct)
            y2.append(ys[ct])
            # vstack.append(ys[ct])
            
        #y = np.vstack(vstack)
        
        dict_date_to_string={'01':'Jan','02':'Feb','03':'Mar','04':'Apr',
                             '05':'May','06':'Jun','07':'Jul','08':'Aug',
                             '09':'Sep', '10':'Oct','11':'Nov','12':'Dec'}

        x = []
        if timeline == "year":
            for d in x_date:
                x.append(dict_date_to_string[d[-2:]])
        elif timeline =="month":
            for d in x_date:
                x.append(d[-5:])
        elif timeline =="week":
            for d in x_date:
                x.append(d[-5:])

        x_sp = np.arange(len(x))
        
        self.figure2.clear()
        ax = self.figure2.add_subplot(111)

        X_ = np.linspace(x_sp.min(), x_sp.max(), 500)
        vstack = []
        for y in y2:
            y_sp = np.asarray(y)
            # X_Y_Spline = make_interp_spline(x_sp, y_sp)
            X_Y_Spline = interpolate.PchipInterpolator(x_sp, y_sp)
            # X_Y_Spline = interpolate.interp1d(x_sp, y_sp, kind='cubic')
            # X_Y_Spline = interpolate.BarycentricInterpolator(x_sp, y_sp)
            Y_ = X_Y_Spline(X_)
            vstack.append(Y_)
        
        y_ = np.vstack(vstack)

        ax.stackplot(X_, y_,labels=labels, baseline='sym')

        ax.legend(loc='upper left')
        if timeline == "year":
            ax.set_xticks(x_sp)
            ax.set_xticklabels(x, rotation=45)
            ax.set_xlabel('Months')
        elif timeline == "month":
            ax.set_xticks(x_sp[::5])
            ax.set_xticklabels(x[::5],rotation=45)
            ax.set_xlabel('Last 30 Days')
        elif timeline == "week":
            ax.set_xticks(x_sp)
            ax.set_xticklabels(x, rotation=45)
            ax.set_xlabel('Last 7 Days')
        ax.set_ylabel('Amount of Coffees')
        ax.yaxis.set_major_formatter(lambda x, pos: f'{abs(x):g}')
        self.canvas2.draw()

    def displayPeakHours(self):
        self.fig = plt.figure()
        self.canvas = FigureCanvas(self.fig)
        self.lay.addWidget(self.canvas)

        db = DBManager()
        self.data = db.getPeakHoursData()
        db.close_connection()

        x = []
        y = []
        for entry in self.data:
            x.append(entry[0].strftime('%H:%M'))
            y.append(entry[1])

        x = np.asarray(x)
        y = np.asarray(y)

        self.fig.clear()
        ax = self.fig.add_subplot(111) 

        ax.set_xticks(np.arange(len(x)))
        ax.set_xticklabels(x, rotation=45)

        i = 0
        for label in ax.xaxis.get_ticklabels():
            if i % 4 == 0:
                label.set_visible(True)
            else:
                label.set_visible(False)
            i+=1
        
        ax.set_xlabel("Hour")
        ax.set_ylabel("Amount of Coffees")

        ax.yaxis.set_major_formatter(lambda x, pos: f'{abs(x):g}')

        ax.plot(x, y)
        self.canvas.draw()