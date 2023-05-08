#!/usr/bin/env python3
import tkinter
import matplotlib
import matplotlib.animation as anim
import matplotlib.pyplot as plt
import numpy as np


matplotlib.use("TkAgg")


class PlotTest:

    def __init__(self):
        self.plotInit()

    def plotInit(self):
        self.fig = self.createPlot()
        anim.FuncAnimation(self.fig, self.update, frames=1, repeat=True)
        plt.show()

    def createPlot(self) -> plt.figure:
        fig = plt.figure(figsize=(16, 6))
        return fig

    def update(self) -> None:
        self.updatePlot()
        plt.pause(1)

    def updatePlot(self):
        ax1 = self.fig.add_subplot(141)
        ax1.cla()
        ax1.plot(range(0, 100, 1), "r")
        ax1.grid()
        plt.setp(ax1, np.linspace(0, 1025, 7), np.linspace(0, 100, 7, dtype=int),)


if __name__ == "__main__":
    p = PlotTest()
